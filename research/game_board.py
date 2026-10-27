"""Whole Kalshi board for one NFL game: every player ladder's middle rung (formula vs Kalshi), the
moneyline, and anytime-TD prices.

    python research/game_board.py 2026_08_CAR_GB 26OCT29CARGB      # nflverse game_id, Kalshi event code

under_edge = formula P(under) - (NO ask + taker fee); rule A in props_scan.py needs 3+ points.
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import requests
import research.props_scan as ps
from research.fetch_kalshi_props import DEFAULT_SERIES, kickoffs, match
from research.nfl_player_yards import build, fit_all, norm_name
GAME, EV = sys.argv[1], sys.argv[2]
B = "https://api.elections.kalshi.com/trade-api/v2"
ko = kickoffs(); rows = []
for series in DEFAULT_SERIES:
    for m in ps.open_markets(series):
        hit = match(m["event_ticker"], ko)
        if not hit or hit[0] != GAME or m.get("floor_strike") is None: continue
        rows.append({"stat": ps.STAT[series], "ticker": m["ticker"], "game_id": hit[0], "kickoff": hit[1],
                     "name": (m.get("yes_sub_title") or m["title"]).split(":")[0].strip(), "strike": float(m["floor_strike"]),
                     "yes_bid": ps.f(m.get("yes_bid_dollars")), "yes_ask": ps.f(m.get("yes_ask_dollars")), "no_ask": ps.f(m.get("no_ask_dollars"))})
df = pd.DataFrame(rows); df["name_key"] = df["name"].map(norm_name)
df["ladder"] = df.ticker.str.rsplit("-", n=1).str[0]
df = df.sort_values(["ladder", "strike"]); df = df[df.groupby("ladder").cumcount() == (df.groupby("ladder").strike.transform("size") - 1) // 2]
s = build(); models = fit_all(s); inj = ps.injuries(2026); out_keys, active_keys = ps.ruled_out(2026, inj)
d = ps.score(s, models, df, out_keys, active_keys)
d["kalshi_yes"] = (d.yes_bid + d.yes_ask) / 2
d["no_ask"] = d.no_ask.fillna(1 - d.yes_bid); d["no_cost"] = d.no_ask + ps.taker_fee(d.no_ask)
d["under_edge"] = (1 - d.p_over) - d.no_cost
print(f"{len(df)} player ladders open; middle rungs:")
print(d.sort_values("under_edge", ascending=False)[["name", "stat", "strike", "kalshi_yes", "p_over", "formula_mean", "yes_bid", "yes_ask", "under_edge"]].round(3).to_string(index=False))
for ser in ("KXNFLGAME", "KXNFLTD"):
    j = requests.get(B + "/markets", params={"event_ticker": f"{ser}-{EV}", "limit": 200}, timeout=60).json().get("markets", [])
    rows = [((m.get("yes_sub_title") or m["title"]), float(m.get("yes_bid_dollars") or 0), float(m.get("yes_ask_dollars") or 0)) for m in j]
    if ser == "KXNFLTD":
        rows = [r for r in rows if re.search(r":\s*1\+", r[0])]
    rows.sort(key=lambda r: -r[2])
    print(f"\n{ser}:", "; ".join(f"{t} {b:.2f}/{a:.2f}" for t, b, a in rows[:12]))
