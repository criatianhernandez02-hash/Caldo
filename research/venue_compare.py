"""Live side-by-side price check: Sleeper vs Kalshi vs Polymarket on the same TD picks.

    python research/venue_compare.py [out.csv]

For every anytime-TD and passing-TD pick that Sleeper offers, finds the same proposition on
Kalshi and Polymarket and reports what $1 returns if the pick wins at each venue:
  Sleeper     the per-pick multiplier
  Kalshi      1 / (ask + taker fee), fee = 7% x P x (1-P) rounded up to the cent
  Polymarket  1 / (ask + taker fee), fee = 5% x P x (1-P) (sports schedule per the venue research)
"Fair" probability = average of the exchange midpoints that have a tight (<=4c) spread.
Note: reading Sleeper's lines endpoint automatically conflicts with Sleeper's Terms of Service.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tdmodel import kalshi, sleeper  # noqa: E402
from tdmodel.parlay import norm_name  # noqa: E402

GAMMA = "https://gamma-api.polymarket.com/events"
TIGHT = 0.04
Q_ATD = re.compile(r"^(?P<name>.+?): Anytime Touchdown$")
Q_PTD = re.compile(r"^(?P<name>.+?): Passing Touchdowns O/U (?P<line>[\d.]+)$")


def polymarket_prices() -> pd.DataFrame:
    events, offset = [], 0
    while True:
        r = requests.get(GAMMA, params={"tag_slug": "nfl", "active": "true", "closed": "false",
                                        "limit": 100, "offset": offset}, timeout=60)
        r.raise_for_status()
        batch = r.json()
        events += batch
        if len(batch) < 100:
            break
        offset += 100
    rows = []
    for e in events:
        for m in e.get("markets", []):
            q = m.get("question", "")
            a, p = Q_ATD.match(q), Q_PTD.match(q)
            if not (a or p) or m.get("bestBid") is None or m.get("bestAsk") is None:
                continue
            market, line = ("anytime_td", 0.5) if a else ("pass_tds", float(p["line"]))
            bid, ask = float(m["bestBid"]), float(m["bestAsk"])
            rows.append({"key": norm_name((a or p)["name"]), "market": market, "line": line,
                         "poly_bid": bid, "poly_ask": ask, "poly_liquidity": m.get("liquidityNum")})
    return pd.DataFrame(rows).drop_duplicates(["key", "market", "line"])


def poly_fee(p):
    return 0.05 * p * (1 - p)


def main(out: str | None) -> None:
    lines = sleeper.fetch_lines()
    lines = lines[lines["line_type"] == "normal"].copy()
    lines["key"] = lines["player"].map(norm_name)
    k = kalshi.fetch_prices()
    poly = polymarket_prices()
    df = lines.merge(k[["key", "market", "line", "kalshi_bid", "kalshi_ask"]], on=["key", "market", "line"], how="left")
    df = df.merge(poly, on=["key", "market", "line"], how="left")
    more = df["side"] == "more"
    # price of the contract that wins if this side wins (Yes for More, No for Less)
    k_cost = np.where(more, df["kalshi_ask"], 1 - df["kalshi_bid"])
    p_cost = np.where(more, df["poly_ask"], 1 - df["poly_bid"])
    df["kalshi_x"] = 1 / (k_cost + kalshi.taker_fee(np.nan_to_num(k_cost, nan=0.5)))
    df["poly_x"] = 1 / (p_cost + poly_fee(p_cost))
    k_mid = (df["kalshi_bid"] + df["kalshi_ask"]) / 2
    p_mid = (df["poly_bid"] + df["poly_ask"]) / 2
    k_ok = (df["kalshi_ask"] - df["kalshi_bid"]) <= TIGHT
    p_ok = (df["poly_ask"] - df["poly_bid"]) <= TIGHT
    yes = pd.concat([k_mid.where(k_ok), p_mid.where(p_ok)], axis=1).mean(axis=1)
    df["fair_p"] = np.where(more, yes, 1 - yes)
    for v, col in (("sleeper", "multiplier"), ("kalshi", "kalshi_x"), ("poly", "poly_x")):
        df[f"ev_{v}"] = df["fair_p"] * df[col] - 1
    df["best_venue"] = df[["multiplier", "kalshi_x", "poly_x"]].rename(
        columns={"multiplier": "Sleeper", "kalshi_x": "Kalshi", "poly_x": "Polymarket"}).idxmax(axis=1, skipna=True)
    if out:
        df.to_csv(out, index=False)
    priced = df.dropna(subset=["fair_p"])
    print(f"Sleeper picks: {len(df)}; with a fair price from at least one tight exchange quote: {len(priced)}")
    print(f"  on Kalshi: {df['kalshi_ask'].notna().sum()}  on Polymarket: {df['poly_ask'].notna().sum()}  "
          f"tight Kalshi: {k_ok.sum()}  tight Polymarket: {p_ok.sum()}")
    full = priced.dropna(subset=["kalshi_x", "poly_x"])
    full = full[np.isfinite(full["poly_x"]) & np.isfinite(full["kalshi_x"])]
    print(f"\nPicks priced on all three venues: {len(full)}")
    summary = pd.DataFrame({
        "avg payout per $1": [full["multiplier"].mean(), full["kalshi_x"].mean(), full["poly_x"].mean()],
        "avg EV per $1": [full["ev_sleeper"].mean(), full["ev_kalshi"].mean(), full["ev_poly"].mean()],
        "share of picks where best": [(full["best_venue"] == v).mean() for v in ("Sleeper", "Kalshi", "Polymarket")],
        "picks with EV > 0": [(full[c] > 0).sum() for c in ("ev_sleeper", "ev_kalshi", "ev_poly")],
    }, index=["Sleeper", "Kalshi (taker)", "Polymarket (taker)"])
    print(summary.round(3).to_string())
    for side in ("more", "less"):
        s = full[full["side"] == side]
        print(f"  {side:>4}: EV Sleeper {s['ev_sleeper'].mean():+.3f}  Kalshi {s['ev_kalshi'].mean():+.3f}  "
              f"Polymarket {s['ev_poly'].mean():+.3f}  (n={len(s)})")
    full = full.assign(b=pd.cut(full["fair_p"], [0, .2, .35, .5, .65, 1]))
    print(full.groupby("b", observed=True)[["ev_sleeper", "ev_kalshi", "ev_poly"]].mean().round(3).to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
