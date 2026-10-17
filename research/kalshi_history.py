"""Pre-kickoff Kalshi prices for settled NFL touchdown markets.

Kalshi's settled-market listing only shows the post-game price (1c or 99c), so this uses
the hourly candles for each game's event and takes the last candle that closes at or before
kickoff: the bid/ask midpoint when the spread is tight, otherwise the last traded price.

Inputs (produced by the fetch scripts used in the research run):
  <dir>/td_settled.json, <dir>/passtd_settled.json   settled market listings
  <dir>/candles/<event>.json                         event candlesticks (hourly)
  <dir>/event_meta.json                              event -> game_id, kickoff (UTC)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TITLE_RE = re.compile(r"^(?P<name>.+?):\s*(?P<n>\d+)\+")
MAX_SPREAD = 0.10


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def pregame_prices(kdir: Path) -> pd.DataFrame:
    meta = json.load(open(kdir / "event_meta.json"))
    listing = {}
    for path, market in (("td_settled.json", "anytime_td"), ("passtd_settled.json", "pass_tds")):
        for m in json.load(open(kdir / path)):
            t = TITLE_RE.match(m.get("title", ""))
            if t and m.get("result") in ("yes", "no"):
                listing[m["ticker"]] = (market, t["name"].strip(), int(t["n"]) - 0.5, m["result"] == "yes")
    rows = []
    for f in sorted((kdir / "candles").glob("*.json")):
        ev = f.stem
        if ev not in meta:
            continue
        kick = int(pd.Timestamp(meta[ev]["kick"]).timestamp())
        body = json.load(open(f))
        for ticker, candles in zip(body.get("market_tickers", []), body.get("market_candlesticks", [])):
            if ticker not in listing:
                continue
            market, name, line, result = listing[ticker]
            pre = [c for c in candles if c["end_period_ts"] <= kick]
            if not pre:
                continue
            c = pre[-1]
            bid, ask = _f(c.get("yes_bid", {}).get("close_dollars")), _f(c.get("yes_ask", {}).get("close_dollars"))
            last = _f(c.get("price", {}).get("close_dollars"))
            if np.isnan(last):
                last = _f(c.get("price", {}).get("previous_dollars"))
            if bid > 0 and ask < 1 and ask - bid <= MAX_SPREAD:
                p, src = (bid + ask) / 2, "mid"
            elif not np.isnan(last):
                p, src = last, "last"
            else:
                continue
            vol = sum(_f(x.get("volume_fp")) or 0 for x in candles if x["end_period_ts"] <= kick)
            rows.append({"event": ev, "game_id": meta[ev]["game_id"], "market": market, "player": name,
                         "line": line, "kalshi_p": p, "kalshi_bid": bid, "kalshi_ask": ask,
                         "price_source": src, "pregame_volume": vol, "result": result,
                         "hours_before_kick": (kick - c["end_period_ts"]) / 3600})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    kdir = Path(sys.argv[1])
    df = pregame_prices(kdir)
    out = Path(__file__).resolve().parent / "out" / "kalshi_pregame.csv"
    df.to_csv(out, index=False)
    print(len(df), "markets ->", out)
    print(df.groupby(["market", "line"]).size())
    print(df["price_source"].value_counts())
