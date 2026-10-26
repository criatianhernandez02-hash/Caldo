"""When to bet the player-under rule, and does the market move toward it? (Kalshi 2026, all rungs)

    python research/props_timing.py <props_long_dir>

Needs fetch_kalshi_props.py --pre-hours 96 <props_long_dir>. For every settled player market it
takes the last hourly quote at or before 72, 48, 24, 12, 6 and 1 hours before kickoff and at
kickoff, then reports
  1. how accurate Kalshi's midpoint is at each horizon (are lines softer early in the week?)
  2. the rule - buy NO on the middle rung when the formula's P(under) beats the NO ask + fee by
     3-10 points - entered at each horizon: return per $1 (fee and spread included), and CLV =
     how far the NO midpoint moved toward us between entry and kickoff (cents), the market's
     own verdict on the pick.
  3. Unabated's injury rules: when a regular in a player's position group is out, is the
     player's line overpriced ("a bridge too far")? And when a regular returns?
The formula knows game-day absences, which early in the week were not yet public, so every
result is also shown for "no news" players (no teammate out or returning, no backup QB): the
fair test for early entries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.kalshi_games import taker_fee  # noqa: E402
from research.nfl_player_yards import build, fit_all, norm_name, pregame_absent  # noqa: E402
from research.props_backtest import SERIES, cluster_se, ll  # noqa: E402

HOURS = (72, 48, 24, 12, 6, 1, 0)


def snapshots(props_dir: Path) -> pd.DataFrame:
    rows = []
    for series, stat in SERIES.items():
        mp, cp = props_dir / f"{series}_markets.json", props_dir / f"{series}_candles.jsonl"
        if not (mp.exists() and cp.exists()):
            continue
        meta = {m["ticker"]: m for m in json.load(mp.open()) if m.get("floor_strike") is not None and m.get("kickoff")}
        ladders: dict = {}
        for m in meta.values():
            ladders.setdefault(m["ticker"].rsplit("-", 1)[0], []).append(m)
        middle = {sorted(r, key=lambda m: float(m["floor_strike"]))[(len(r) - 1) // 2]["ticker"] for r in ladders.values()}
        for line in cp.open():
            d = json.loads(line)
            m = meta.get(d["ticker"])
            if not m:
                continue
            cs = sorted((c for c in d["candles"] if c["bid"] is not None and c["ask"] is not None), key=lambda c: c["t"])
            row = {"stat": stat, "ticker": m["ticker"], "game_id": m["game_id"], "kickoff": m["kickoff"],
                   "name_key": norm_name((m.get("yes_sub_title") or m["title"]).split(":")[0]),
                   "strike": float(m["floor_strike"]), "won": m["result"] == "yes", "middle_rung": m["ticker"] in middle}
            for h in HOURS:
                t = m["kickoff"] - h * 3600
                last = None
                for c in cs:
                    if c["t"] <= t:
                        last = c
                    else:
                        break
                ok = last is not None and last["bid"] > 0 and last["ask"] - last["bid"] <= 0.10
                row[f"bid_{h}"], row[f"ask_{h}"] = (last["bid"], last["ask"]) if ok else (np.nan, np.nan)
            rows.append(row)
    d = pd.DataFrame(rows)
    d["pg"] = d["game_id"] + "|" + d["name_key"]
    return d


def attach(d: pd.DataFrame) -> pd.DataFrame:
    s = build()
    models = fit_all(s)
    games = s[s["game_id"].isin(d["game_id"].unique())]
    in_box = set(zip(games["game_id"], games["name_key"]))
    want = d[["game_id", "name_key"]].drop_duplicates()
    absent = pregame_absent(s, want[[k not in in_box for k in zip(want["game_id"], want["name_key"])]])
    news_cols = ["l_gvac_t", "l_gvac_c", "l_gret_t", "l_gret_c", "backup_qb"]
    out = []
    for stat, m in models.items():
        part = d[d["stat"] == stat]
        feats = [games.loc[m.usable(games), ["game_id", "name_key"] + list(dict.fromkeys(m.features + news_cols))]]
        if len(absent):
            feats.append(absent.loc[m.usable(absent), ["game_id", "name_key"] + list(dict.fromkeys(m.features + news_cols))])
        part = part.merge(pd.concat(feats, ignore_index=True).drop_duplicates(["game_id", "name_key"]), on=["game_id", "name_key"])
        part["p_formula"] = m.p_over(m.mean(part), part["strike"].to_numpy())
        part["no_news"] = (part[news_cols].abs().sum(axis=1) < 1e-9)
        k = "c" if stat == "rushing_yards" else "t"
        part["own_gvac"], part["own_gret"] = part[f"l_gvac_{k}"], part[f"l_gret_{k}"]  # his group's volume gained / lost
        out.append(part[[c for c in part.columns if c not in m.features]])
    return pd.concat(out, ignore_index=True)


def main(props_dir: str) -> None:
    pd.set_option("display.width", 200)
    d = attach(snapshots(Path(props_dir)))
    print(f"{len(d)} markets, {d.pg.nunique()} player-games, {d.no_news.mean():.0%} with no team news")

    print("\n== 1. Kalshi accuracy by time before kickoff (same markets quoted at every horizon) ==")
    full = d.dropna(subset=[f"bid_{h}" for h in HOURS])
    rows = []
    for h in HOURS:
        mid = (full[f"bid_{h}"] + full[f"ask_{h}"]) / 2
        rows.append({"hours_before": h, "markets": len(full), "kalshi_logloss": ll(mid, full.won),
                     "formula_logloss": ll(full.p_formula, full.won), "avg_spread_cents": 100 * (full[f"ask_{h}"] - full[f"bid_{h}"]).mean()})
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    print("\n== 2. NO on the middle rung when the formula is 3-10 points under, by entry time ==")
    rows = []
    for subset, x in (("all players", d), ("no-news players", d[d.no_news])):
        x = x[x.middle_rung]
        for h in HOURS[:-1] + (0,):
            e = x.dropna(subset=[f"bid_{h}", "bid_0"]).copy()
            no_ask = 1 - e[f"bid_{h}"]
            cost = no_ask + taker_fee(no_ask)
            edge = (1 - e.p_formula) - cost
            b = e[(edge >= 0.03) & (edge < 0.10)].copy()
            if len(b) < 20:
                continue
            c = cost[b.index]
            pnl = np.where(~b.won, 1 / c - 1, -1.0)
            entry_mid = 1 - (b[f"bid_{h}"] + b[f"ask_{h}"]) / 2
            close_mid = 1 - (b["bid_0"] + b["ask_0"]) / 2
            move = 100 * (close_mid - entry_mid)
            rows.append({"players": subset, "enter_hours_before": h, "bets": len(b), "player_games": b.pg.nunique(),
                         "roi": pnl.mean(), "roi_se": cluster_se(pnl, b.pg), "clv_move_cents": move.mean(),
                         "clv_se": cluster_se(move.to_numpy(), b.pg), "moved_our_way": (move > 0).mean(),
                         "moved_against": (move < 0).mean()})
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    print("\n== 3. Injury news: are lines of players whose position group lost a regular overpriced? (at kickoff) ==")
    k = d.dropna(subset=["bid_0"]).copy()
    k["mid"] = (k["bid_0"] + k["ask_0"]) / 2
    no_ask = 1 - k["bid_0"]
    k["no_pnl"] = np.where(~k.won, 1 / (no_ask + taker_fee(no_ask)) - 1, -1.0)
    k["yes_pnl"] = np.where(k.won, 1 / (k["ask_0"] + taker_fee(k["ask_0"])) - 1, -1.0)
    rows = []
    for name, x in (("group lost a regular (backup's line)", k[k.own_gvac > 0.10]),
                    ("group got a regular back", k[k.own_gret > 0.10]), ("no team news", k[k.no_news])):
        for rung, y in (("all rungs", x), ("middle rung", x[x.middle_rung])):
            rows.append({"case": name, "rungs": rung, "markets": len(y), "player_games": y.pg.nunique(),
                         "kalshi_said": y["mid"].mean(), "actually_hit": y.won.mean(), "formula_said": y.p_formula.mean(),
                         "kalshi_logloss": ll(y["mid"], y.won), "formula_logloss": ll(y.p_formula, y.won),
                         "buy_NO_roi": y.no_pnl.mean(), "no_se": cluster_se(y.no_pnl.to_numpy(), y.pg),
                         "buy_YES_roi": y.yes_pnl.mean()})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    d.to_csv(Path(__file__).resolve().parent / "out" / "props_timing.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
