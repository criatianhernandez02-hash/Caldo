"""Kalshi NFL player markets (receiving yards, rushing yards, receptions) vs the Caldo player formula.

    python research/props_backtest.py <props_dir>

Needs the download from fetch_kalshi_props.py and research/out/nfl_player_yards_preds.csv
(nfl_player_yards.py). For every settled "Player: k+" market it takes the last hourly quote at or
before kickoff and 1 hour before, then reports
  1. how well Kalshi's prices are calibrated, and returns by price bucket (taker at the ask + fee,
     maker at the bid), YES and NO sides;
  2. accuracy of the formula vs Kalshi on the same markets;
  3. betting the formula's disagreements (YES when formula > ask + fee, NO when 1 - formula > NO ask + fee).
2025 (historical, weeks 4-18, half the games, middle rung of each ladder) is the independent
test season; 2026 is split into weeks 1-3 and 4-6. Standard errors are clustered by player-game (the rungs of one player's ladder move together).
Only players who appear in that game's box score are scored ("active" - inactives are announced
90 minutes before kickoff, and Kalshi's price already reflects them).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.kalshi_games import taker_fee  # noqa: E402
from research.nfl_player_yards import build, fit_all, norm_name  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
SERIES = {"KXNFLRECYDS": "receiving_yards", "KXNFLRSHYDS": "rushing_yards", "KXNFLREC": "receptions"}


def snap(candles: list[dict], t: int) -> dict:
    best = None
    for c in candles:
        if c["t"] <= t and (best is None or c["t"] > best["t"]):
            best = c
    return best or {}


def load(props_dir: Path) -> pd.DataFrame:
    rows = []
    for series, stat in SERIES.items():
        for suffix in ("", "_hist"):
            mp, cp = props_dir / f"{series}{suffix}_markets.json", props_dir / f"{series}{suffix}_candles.jsonl"
            if not (mp.exists() and cp.exists()):
                continue
            meta = {m["ticker"]: m for m in json.load(mp.open()) if m.get("floor_strike") is not None}
            ladders: dict[str, list] = {}
            for m in meta.values():
                ladders.setdefault(m["ticker"].rsplit("-", 1)[0], []).append(m)
            middle = set()
            for rungs in ladders.values():
                rungs.sort(key=lambda m: float(m["floor_strike"]))
                middle.add(rungs[(len(rungs) - 1) // 2]["ticker"])
            for line in cp.open():
                d = json.loads(line)
                m = meta.get(d["ticker"])
                if not m:
                    continue
                row = {"series": series, "stat": stat, "ticker": m["ticker"], "game_id": m["game_id"],
                       "kickoff": m["kickoff"], "name": m["title"].split(":")[0].strip(),
                       "strike": float(m["floor_strike"]), "won": m["result"] == "yes",
                       "volume": float(m.get("volume_fp") or 0), "middle_rung": m["ticker"] in middle}
                for label, t in (("0", m["kickoff"]), ("1", m["kickoff"] - 3600)):
                    c = snap(d["candles"], t)
                    row[f"bid_{label}"], row[f"ask_{label}"] = c.get("bid"), c.get("ask")
                rows.append(row)
    df = pd.DataFrame(rows)
    df["name_key"] = df["name"].map(norm_name)
    df["pg"] = df["game_id"] + "|" + df["name_key"]
    week = df["game_id"].str[5:7].astype(int)
    df["period"] = np.where(df["game_id"].str[:4] == "2025", "2025 wk4-18",
                            np.where(week <= 3, "2026 wk1-3", "2026 wk4-6"))
    return df


def attach_formula(df: pd.DataFrame) -> pd.DataFrame:
    s = build()
    models = fit_all(s)
    s = s[s["game_id"].isin(df["game_id"].unique())]
    out = []
    for stat, m in models.items():
        part = df[df["stat"] == stat].merge(
            s.loc[m.usable(s), ["game_id", "name_key", "position", stat] + m.features], on=["game_id", "name_key"], how="left")
        if part.empty:
            continue
        ok = part[m.features].notna().all(axis=1)
        if not ok.any():
            continue
        part.loc[ok, "mu"] = m.mean(part[ok])
        part.loc[ok, "p_formula"] = m.p_over(part.loc[ok, "mu"].to_numpy(), part.loc[ok, "strike"].to_numpy())
        part = part.rename(columns={stat: "actual"})
        out.append(part[[c for c in part.columns if c not in m.features]])
    d = pd.concat(out, ignore_index=True)
    d["active"] = d["actual"].notna()
    # sanity: settlement should agree with the box score for active players
    d["won_check"] = d["actual"] > d["strike"]
    return d


def cluster_se(x: np.ndarray, groups: pd.Series) -> float:
    x = np.asarray(x, float)
    dev = pd.Series(x - x.mean()).groupby(groups.to_numpy()).sum()
    return float(np.sqrt((dev ** 2).sum()) / len(x)) if len(x) > 1 else np.nan


def ll(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def bucket_table(d: pd.DataFrame, when: str) -> pd.DataFrame:
    x = d.dropna(subset=[f"bid_{when}", f"ask_{when}"]).copy()
    x = x[(x[f"ask_{when}"] - x[f"bid_{when}"] <= 0.10) & (x[f"bid_{when}"] > 0)]
    x["mid"] = (x[f"bid_{when}"] + x[f"ask_{when}"]) / 2
    x["b"] = pd.cut(x["mid"], [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, 1])
    yes_take = np.where(x.won, 1 / (x[f"ask_{when}"] + taker_fee(x[f"ask_{when}"])) - 1, -1.0)
    no_ask = 1 - x[f"bid_{when}"]
    no_take = np.where(~x.won, 1 / (no_ask + taker_fee(no_ask)) - 1, -1.0)
    yes_make = np.where(x.won, 1 / x[f"bid_{when}"] - 1, -1.0)
    x = x.assign(yes_take=yes_take, no_take=no_take, yes_make=yes_make)
    rows = []
    for b, g in x.groupby("b", observed=True):
        rows.append({"mid": str(b), "n": len(g), "avg_mid": g["mid"].mean(), "won": g.won.mean(),
                     "YES_take_roi": g.yes_take.mean(), "YES_take_se": cluster_se(g.yes_take, g.pg),
                     "NO_take_roi": g.no_take.mean(), "NO_take_se": cluster_se(g.no_take, g.pg),
                     "YES_make_roi(upper bound)": g.yes_make.mean()})
    return pd.DataFrame(rows)


def bet_table(d: pd.DataFrame, when: str) -> pd.DataFrame:
    x = d[d.active & d.p_formula.notna()].dropna(subset=[f"bid_{when}", f"ask_{when}"])
    x = x[(x[f"ask_{when}"] - x[f"bid_{when}"] <= 0.10) & (x[f"bid_{when}"] > 0)]
    yes_cost = x[f"ask_{when}"] + taker_fee(x[f"ask_{when}"])
    no_ask = 1 - x[f"bid_{when}"]
    no_cost = no_ask + taker_fee(no_ask)
    rows = []
    for thr in (0.0, 0.03, 0.05, 0.10):
        for side in ("YES", "NO"):
            if side == "YES":
                sel = x.p_formula - yes_cost > thr
                pnl = np.where(x.won[sel], 1 / yes_cost[sel] - 1, -1.0)
            else:
                sel = (1 - x.p_formula) - no_cost > thr
                pnl = np.where(~x.won[sel], 1 / no_cost[sel] - 1, -1.0)
            g = x[sel]
            for stat in ["ALL"] + sorted(g.stat.unique()):
                k = np.ones(len(g), bool) if stat == "ALL" else (g.stat == stat).to_numpy()
                if k.sum() < 10:
                    continue
                rows.append({"edge>": thr, "side": side, "stat": stat, "bets": int(k.sum()),
                             "player_games": g.pg[k].nunique(), "avg_price": float((yes_cost if side == "YES" else no_cost)[sel][k].mean()),
                             "win_rate": float((g.won[k] if side == "YES" else ~g.won[k]).mean()),
                             "roi": float(pnl[k].mean()), "se": cluster_se(pnl[k], g.pg[k])})
    return pd.DataFrame(rows)


def main(props_dir: str) -> None:
    pd.set_option("display.width", 220)
    d = attach_formula(load(Path(props_dir)))
    print("markets:", len(d), "| by stat:", d.groupby("stat").size().to_dict(), "| periods:", d.period.value_counts().to_dict())
    print("player-games:", d.pg.nunique(), "| matched to box score (active):", round(d.active.mean(), 3),
          "| formula available:", round(d.p_formula.notna().mean(), 3))
    a = d[d.active]
    print("settlement agrees with box score:", round(float((a.won == a.won_check).mean()), 4))
    cur = d[d.period != "2025 wk4-18"]
    for when in ("0", "1"):
        print(f"\n== 2026 Kalshi price buckets, last quote {'at kickoff' if when == '0' else '1h before'} (all rungs) ==")
        print(bucket_table(cur, when).round(4).to_string(index=False))
    when = "0"
    for period in sorted(d.period.unique()):
        for rungs in ("middle rung only", "all rungs"):
            p = d[d.period == period]
            if rungs == "middle rung only":
                p = p[p.middle_rung]
            elif period.startswith("2025"):
                continue  # only middle rungs were downloaded for 2025
            x = p[p.active & p.p_formula.notna()].dropna(subset=[f"bid_{when}", f"ask_{when}"])
            x = x[(x[f"ask_{when}"] - x[f"bid_{when}"] <= 0.10) & (x[f"bid_{when}"] > 0)]
            if x.empty:
                continue
            mid = (x[f"bid_{when}"] + x[f"ask_{when}"]) / 2
            print(f"\n######## {period}, {rungs}: {len(x)} active-player markets at kickoff ########")
            print(f"Accuracy (log loss): Kalshi mid {ll(mid, x.won):.4f} | formula {ll(x.p_formula, x.won):.4f}")
            for stat, g in x.groupby("stat"):
                m = (g[f"bid_{when}"] + g[f"ask_{when}"]) / 2
                print(f"   {stat:16s} n={len(g):5d}  Kalshi {ll(m, g.won):.4f}  formula {ll(g.p_formula, g.won):.4f}")
            print("Betting the formula's disagreements at kickoff (taker, fee included):")
            print(bet_table(p, when).round(4).to_string(index=False))
    d.to_csv(OUT / "props_kalshi_joined.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
