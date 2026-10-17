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


def taker_fee(price: np.ndarray | float, contracts: int | None = None) -> np.ndarray | float:
    """Kalshi taker fee: 7% x C x P x (1-P), rounded up to the next cent per order.

    With `contracts` the exact order fee is returned; without it, the fee per contract before
    rounding (the right number for comparing prices on a typical $20 order, where the
    one-cent rounding is negligible).
    """
    price = np.asarray(price, dtype=float)
    if contracts is None:
        return 0.07 * price * (1 - price)
    return np.ceil(np.round(0.07 * contracts * price * (1 - price) * 100, 6)) / 100


def attach(legs: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Add, for each leg's side ("less" = the No contract):
    kalshi_prob    the market's probability (bid/ask midpoint)
    kalshi_payout  what $1 returns if it wins when bought on Kalshi now at the ask, after the
                   taker fee - directly comparable to Sleeper's multiplier for the same pick.
    """
    legs = legs.copy()
    key = legs["player"].str.replace(r" \(Q\)$", "", regex=True).map(norm_name)
    book = prices.drop_duplicates(["key", "market", "line"]).set_index(["key", "market", "line"])
    idx = list(zip(key, legs["market"], legs["line"]))
    get = lambda col: np.array([book[col].get(i, np.nan) for i in idx], dtype=float)  # noqa: E731
    p_yes, bid, ask = get("kalshi_prob"), get("kalshi_bid"), get("kalshi_ask")
    more = (legs["side"] == "more").to_numpy()
    legs["kalshi_prob"] = np.where(more, p_yes, 1 - p_yes)
    cost = np.where(more, ask, 1 - bid)  # buying No costs 1 - (best Yes bid)
    legs["kalshi_payout"] = 1 / (cost + taker_fee(cost))
    return legs
