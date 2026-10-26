"""Kalshi NFL total-points and spread ladders vs the sportsbook closing line (2026 season).

    python research/ladders_backtest.py <dir>      # dir from: fetch_kalshi_props.py <dir> KXNFLTOTAL KXNFLSPREAD

Kalshi lists every game's total as a ladder ("Over 40.5 points", "Over 43.5", ...) and its spread as
"<Team> wins by over X". The sportsbook closing total and spread (nflverse games.csv) plus how far
real results landed from those lines in 2012-2025 give a fair probability for every rung, key
numbers included:
    P(total > X)          = share of past games with (total - closing total) > X - closing total
    P(team wins by > X)   = same with the margin vs the closing spread, from that team's side
Then, with the last hourly Kalshi quote at or before kickoff:
  1. calibration and returns by price bucket (YES and NO, taker at the ask + fee)
  2. accuracy of Kalshi vs the sportsbook-implied probability on the same rungs
  3. Matt Downs-style +EV rule: buy whichever side Kalshi sells cheaper than the sportsbook's
     fair probability (after fee), by edge threshold
  4. the "~87%" zone: rungs priced 85-90 cents on either side
Standard errors are clustered by game (the rungs of one ladder move together).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.kalshi_games import taker_fee  # noqa: E402

ALIAS = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS", "LVR": "LV", "ARZ": "ARI"}
FIT = (2012, 2025)


def snap(candles: list[dict], t: int) -> dict:
    best = None
    for c in candles:
        if c["t"] <= t and c.get("bid") is not None and c.get("ask") is not None and (best is None or c["t"] > best["t"]):
            best = c
    return best or {}


def load(d: Path) -> pd.DataFrame:
    rows = []
    for series, kind in (("KXNFLTOTAL", "total"), ("KXNFLSPREAD", "spread")):
        mp, cp = d / f"{series}_markets.json", d / f"{series}_candles.jsonl"
        if not (mp.exists() and cp.exists()):
            continue
        meta = {m["ticker"]: m for m in json.load(mp.open())}
        for line in cp.open():
            c = json.loads(line)
            m = meta.get(c["ticker"])
            if not m or m.get("floor_strike") is None or not m.get("game_id"):
                continue
            k = snap(c["candles"], m["kickoff"])
            team = None
            if kind == "spread":
                code = m["ticker"].rsplit("-", 1)[1].rstrip("0123456789")
                team = ALIAS.get(code, code)
            rows.append({"kind": kind, "ticker": m["ticker"], "game_id": m["game_id"], "team": team,
                         "strike": float(m["floor_strike"]), "won": m["result"] == "yes",
                         "bid": k.get("bid"), "ask": k.get("ask")})
    return pd.DataFrame(rows)


def book_probs(df: pd.DataFrame) -> pd.DataFrame:
    g = pd.read_csv(ROOT / "data_cache" / "games.csv")
    played = g[g["home_score"].notna() & g["total_line"].notna() & g["spread_line"].notna()]
    hist = played[played["season"].between(*FIT)]
    r_total = np.sort((hist["home_score"] + hist["away_score"] - hist["total_line"]).to_numpy(float))
    r_margin = np.sort((hist["home_score"] - hist["away_score"] - hist["spread_line"]).to_numpy(float))
    gi = g.set_index("game_id")
    p = []
    for r in df.itertuples():
        if r.game_id not in gi.index or pd.isna(gi.at[r.game_id, "total_line"]):
            p.append(np.nan)
            continue
        if r.kind == "total":
            x = r.strike - gi.at[r.game_id, "total_line"]
            p.append(1 - np.searchsorted(r_total, x, side="right") / len(r_total))
        else:
            s = gi.at[r.game_id, "spread_line"]
            if r.team == gi.at[r.game_id, "home_team"]:      # home margin > X
                p.append(1 - np.searchsorted(r_margin, r.strike - s, side="right") / len(r_margin))
            elif r.team == gi.at[r.game_id, "away_team"]:    # away margin > X  <=>  home margin < -X
                p.append(np.searchsorted(r_margin, -r.strike - s, side="left") / len(r_margin))
            else:
                p.append(np.nan)
    df = df.copy()
    df["p_book"] = np.clip(p, 0.003, 0.997)
    return df


def cluster_se(x: np.ndarray, groups) -> float:
    x = np.asarray(x, float)
    dev = pd.Series(x - x.mean()).groupby(np.asarray(groups)).sum()
    return float(np.sqrt((dev ** 2).sum()) / len(x)) if len(x) > 1 else np.nan


def ll(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main(d: str) -> None:
    pd.set_option("display.width", 220)
    df = book_probs(load(Path(d)))
    df = df[df["bid"].notna() & (df["bid"] > 0) & (df["ask"] - df["bid"] <= 0.10) & df["p_book"].notna()].copy()
    df["mid"] = (df["bid"] + df["ask"]) / 2
    yes_cost = df["ask"] + taker_fee(df["ask"])
    no_ask = 1 - df["bid"]
    no_cost = no_ask + taker_fee(no_ask)
    df["yes_pnl"] = np.where(df["won"], 1 / yes_cost - 1, -1.0)
    df["no_pnl"] = np.where(~df["won"], 1 / no_cost - 1, -1.0)
    print(f"{len(df)} priced rungs in {df.game_id.nunique()} games ({df.groupby('kind').size().to_dict()})")

    print("\n== 1. Calibration and taker returns by Kalshi price (at kickoff) ==")
    df["bucket"] = pd.cut(df["mid"], [0, .05, .1, .2, .35, .5, .65, .8, .85, .9, .95, 1])
    rows = []
    for (kind, b), x in df.groupby(["kind", "bucket"], observed=True):
        rows.append({"kind": kind, "price": str(b), "rungs": len(x), "kalshi_said": x["mid"].mean(), "book_said": x["p_book"].mean(),
                     "actually_hit": x["won"].mean(), "buy_YES": x["yes_pnl"].mean(), "yes_se": cluster_se(x["yes_pnl"], x["game_id"]),
                     "buy_NO": x["no_pnl"].mean(), "no_se": cluster_se(x["no_pnl"], x["game_id"])})
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    print("\n== 2. Accuracy on the same rungs (log loss, lower is better) ==")
    for kind, x in df.groupby("kind"):
        print(f"  {kind:6s} {len(x):5d} rungs: Kalshi {ll(x['mid'], x['won']):.4f} | sportsbook-implied {ll(x['p_book'], x['won']):.4f}")

    print("\n== 3. Buy whichever side Kalshi sells cheaper than the sportsbook's fair probability ==")
    rows = []
    for thr in (0.0, 0.02, 0.04, 0.06):
        yes = df[df["p_book"] - yes_cost > thr]
        no = df[(1 - df["p_book"]) - no_cost > thr]
        for kind in ("total", "spread", "ALL"):
            y = yes if kind == "ALL" else yes[yes["kind"] == kind]
            n = no if kind == "ALL" else no[no["kind"] == kind]
            pnl = np.concatenate([y["yes_pnl"].to_numpy(), n["no_pnl"].to_numpy()])
            grp = np.concatenate([y["game_id"].to_numpy(), n["game_id"].to_numpy()])
            if len(pnl) < 10:
                continue
            rows.append({"edge>": thr, "kind": kind, "bets": len(pnl), "games": len(set(grp)), "roi": pnl.mean(), "se": cluster_se(pnl, grp)})
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    print("\n== 4. The ~87% zone: the side priced 85-90 cents ==")
    rows = []
    for kind, x in df.groupby("kind"):
        hi_yes = x[(x["mid"] >= .85) & (x["mid"] < .90)]
        hi_no = x[(1 - x["mid"] >= .85) & (1 - x["mid"] < .90)]
        pnl = np.concatenate([hi_yes["yes_pnl"].to_numpy(), hi_no["no_pnl"].to_numpy()])
        won = np.concatenate([hi_yes["won"].to_numpy(), ~hi_no["won"].to_numpy()])
        price = np.concatenate([hi_yes["mid"].to_numpy(), 1 - hi_no["mid"].to_numpy()])
        book = np.concatenate([hi_yes["p_book"].to_numpy(), 1 - hi_no["p_book"].to_numpy()])
        grp = np.concatenate([hi_yes["game_id"].to_numpy(), hi_no["game_id"].to_numpy()])
        rows.append({"kind": kind, "bets": len(pnl), "avg_price": price.mean(), "book_fair": book.mean(), "won": won.mean(),
                     "roi": pnl.mean(), "se": cluster_se(pnl, grp)})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    df.to_csv(ROOT / "research" / "out" / "ladders_backtest.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
