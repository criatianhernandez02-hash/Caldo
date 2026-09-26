"""Kalshi prediction-market prices for NFL player touchdown props.

Kalshi's public market-data API needs no account. Each contract pays $1 if it resolves Yes, so
its price is the market's probability. Used here as an outside "sharp" opinion to check both
the model and Sleeper's multipliers against.

  KXNFLTD      "Player: 1+ touchdowns"          -> anytime TD (over 0.5)
  KXNFLPASSTDS "Player: 2+ passing touchdowns"  -> pass TDs over 1.5 (3+ -> over 2.5)
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import requests

from .parlay import norm_name

API = "https://api.elections.kalshi.com/trade-api/v2/markets"
SERIES = {"KXNFLTD": "anytime_td", "KXNFLPASSTDS": "pass_tds"}
TITLE_RE = re.compile(r"^(?P<name>.+?):\s*(?P<n>\d+)\+")
MAX_SPREAD = 0.15  # ignore markets whose bid/ask are too far apart to mean anything


def _fetch_series(series: str) -> list[dict]:
    markets, cursor = [], None
    while True:
        params = {"series_ticker": series, "status": "open", "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(API, params=params, timeout=60)
        resp.raise_for_status()
        body = resp.json()
        markets += body.get("markets", [])
        cursor = body.get("cursor")
        if not cursor:
            return markets


def parse_markets(markets: list[dict], market: str) -> pd.DataFrame:
    rows = []
    for m in markets:
        hit = TITLE_RE.match(m.get("title", ""))
        if not hit:
            continue
        bid = float(m.get("yes_bid_dollars") or 0)
        ask = float(m.get("yes_ask_dollars") or 0)
        if ask <= 0 or bid <= 0 or ask - bid > MAX_SPREAD:
            continue
        rows.append({
            "player": hit["name"].strip(), "market": market, "line": int(hit["n"]) - 0.5,
            "kalshi_bid": bid, "kalshi_ask": ask, "kalshi_prob": (bid + ask) / 2,
        })
    return pd.DataFrame(rows, columns=["player", "market", "line", "kalshi_bid", "kalshi_ask", "kalshi_prob"])


def fetch_prices() -> pd.DataFrame:
    frames = [parse_markets(_fetch_series(s), mkt) for s, mkt in SERIES.items()]
    prices = pd.concat(frames, ignore_index=True)
    prices["key"] = prices["player"].map(norm_name)
    return prices


def attach(legs: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Add the Kalshi probability for each leg's side ("less" = 1 - yes price)."""
    legs = legs.copy()
    key = legs["player"].str.replace(r" \(Q\)$", "", regex=True).map(norm_name)
    lookup = prices.drop_duplicates(["key", "market", "line"]).set_index(["key", "market", "line"])["kalshi_prob"]
    p_yes = [lookup.get((k, m, l), np.nan) for k, m, l in zip(key, legs["market"], legs["line"])]
    legs["kalshi_prob"] = np.where(legs["side"] == "more", p_yes, 1 - np.asarray(p_yes, dtype=float))
    return legs
