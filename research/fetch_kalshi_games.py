"""Download settled Kalshi game-winner markets and their hourly pre-game price history.

    python research/fetch_kalshi_games.py <out_dir> [SERIES ...]
    python research/fetch_kalshi_games.py --historical <out_dir> [SERIES ...]

For each series (default: NFL, NBA, MLB, NHL, college football, WNBA) this saves
  <out_dir>/<SERIES>_markets.json   every settled market (ticker, event, team, result, start time, volume)
  <out_dir>/<SERIES>_candles.jsonl  hourly candles from 26h before to 1h after each game's start
                                    (yes bid/ask close, last trade, volume) - one line per market
It uses Kalshi's public API (no account), batches markets that start on the same day into
one candlestick request (the API caps a request at 100 markets and 10,000 candles), backs off
on HTTP 429, and skips markets already downloaded, so it can be re-run to resume.

--historical reads markets settled before Kalshi's historical cutoff (older seasons) from
/historical/markets. Those records have no start time and their candles must be fetched one
market at a time, so only one side of each game is fetched (the other side is ~1 - price),
over the 40 hours before the market's expected expiration (a few hours after the start).
--max-games=N caps each non-NFL series at a reproducible random sample of N games.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

API = "https://api.elections.kalshi.com/trade-api/v2"
DEFAULT_SERIES = ["KXNFLGAME", "KXNBAGAME", "KXMLBGAME", "KXNHLGAME", "KXNCAAFGAME", "KXWNBAGAME"]
KEEP = ("ticker", "event_ticker", "yes_sub_title", "result", "occurrence_datetime", "open_time",
        "close_time", "volume_fp", "settlement_value_dollars")
PRE_HOURS, POST_HOURS, MAX_CANDLES, MAX_MARKETS = 26, 1, 9000, 100
HIST_HOURS = 40


def get(path: str, params: dict) -> requests.Response:
    for attempt in range(10):
        try:
            r = requests.get(f"{API}{path}", params=params, timeout=120)
        except requests.RequestException:  # dropped connection / TLS hiccup: wait and retry
            time.sleep(min(60, 4 * (attempt + 1)))
            continue
        if r.status_code != 429:
            return r
        time.sleep(2 + attempt)  # rate limited: short pauses recover fastest
    return requests.get(f"{API}{path}", params=params, timeout=120)


def settled_markets(series: str, historical: bool = False) -> list[dict]:
    out, cursor = [], None
    while True:
        params = {"series_ticker": series, "limit": 200}
        if not historical:
            params["status"] = "settled"
        if cursor:
            params["cursor"] = cursor
        r = get("/historical/markets" if historical else "/markets", params)
        r.raise_for_status()
        body = r.json()
        out += [{k: m.get(k) for k in KEEP + ("expected_expiration_time",)} for m in body.get("markets", [])]
        cursor = body.get("cursor")
        if not cursor:
            return out
        time.sleep(0.8)


def ts(iso: str) -> int:
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def slim(c: dict) -> dict:
    def g(block):
        b = c.get(block) or {}
        v = b.get("close_dollars", b.get("close"))  # live API vs historical API field names
        return float(v) if v not in (None, "") else None
    return {"t": c["end_period_ts"], "bid": g("yes_bid"), "ask": g("yes_ask"), "last": g("price"),
            "vol": float(c.get("volume_fp") or c.get("volume") or 0)}


def fetch_candles(series: str, markets: list[dict], out: Path) -> None:
    done = set()
    if out.exists():
        done = {json.loads(line)["ticker"] for line in out.open()}
    todo = [m for m in markets if m["ticker"] not in done and m.get("occurrence_datetime")
            and m.get("result") in ("yes", "no")]
    by_day = defaultdict(list)
    for m in todo:
        by_day[m["occurrence_datetime"][:10]].append(m)
    print(f"{series}: {len(todo)} markets to fetch over {len(by_day)} days", flush=True)
    with out.open("a") as fh:
        for day, ms in sorted(by_day.items()):
            starts = [ts(m["occurrence_datetime"]) for m in ms]
            lo, hi = min(starts) - PRE_HOURS * 3600, max(starts) + POST_HOURS * 3600
            hours = (hi - lo) // 3600 + 1
            per = max(1, min(MAX_MARKETS, MAX_CANDLES // hours))
            for i in range(0, len(ms), per):
                chunk = ms[i:i + per]
                r = get("/markets/candlesticks", {"market_tickers": ",".join(m["ticker"] for m in chunk),
                                                  "start_ts": lo, "end_ts": hi, "period_interval": 60})
                if not r.ok:
                    print("  fail", series, day, r.status_code, r.text[:150], flush=True)
                    continue
                got = {x["market_ticker"]: x.get("candlesticks", []) for x in r.json().get("markets", [])}
                for m in chunk:
                    fh.write(json.dumps({"ticker": m["ticker"], "candles": [slim(c) for c in got.get(m["ticker"], [])]}) + "\n")
                time.sleep(0.9)
            print(f"  {series} {day}: {len(ms)} markets", flush=True)


def fetch_hist_candles(series: str, markets: list[dict], out: Path, max_games: int | None = None) -> None:
    done = {json.loads(line)["ticker"] for line in out.open()} if out.exists() else set()
    first = {}
    for m in markets:  # one side per game: the alphabetically first ticker of each event
        if m.get("result") in ("yes", "no") and float(m.get("volume_fp") or 0) > 0 and m.get("expected_expiration_time"):
            if m["event_ticker"] not in first or m["ticker"] < first[m["event_ticker"]]["ticker"]:
                first[m["event_ticker"]] = m
    todo = [m for m in first.values() if m["ticker"] not in done]
    if max_games is not None:  # reproducible random sample of games (hash of the event ticker)
        import hashlib
        todo.sort(key=lambda m: hashlib.md5(m["event_ticker"].encode()).hexdigest())
        todo = todo[:max(0, max_games - len(done))]
    print(f"{series} (historical): {len(todo)} games to fetch", flush=True)
    with out.open("a") as fh:
        for i, m in enumerate(sorted(todo, key=lambda m: m["expected_expiration_time"])):
            end = ts(m["expected_expiration_time"])
            r = get(f"/historical/markets/{m['ticker']}/candlesticks",
                    {"start_ts": end - HIST_HOURS * 3600, "end_ts": end, "period_interval": 60})
            if not r.ok:
                print("  fail", m["ticker"], r.status_code, r.text[:120], flush=True)
                continue
            fh.write(json.dumps({"ticker": m["ticker"], "candles": [slim(c) for c in r.json().get("candlesticks", [])]}) + "\n")
            if i % 200 == 0:
                print(f"  {series} {i}/{len(todo)}", flush=True)
            time.sleep(0.35)


def main(out_dir: Path, series_list: list[str], historical: bool = False, max_games: int | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if historical:
        for series in series_list:
            mpath = out_dir / f"{series}_hist_markets.json"
            markets = json.load(mpath.open()) if mpath.exists() else settled_markets(series, historical=True)
            json.dump(markets, mpath.open("w"))
            print(f"{series}: {len(markets)} historical markets", flush=True)
            fetch_hist_candles(series, markets, out_dir / f"{series}_hist_candles.jsonl",
                               None if series == "KXNFLGAME" else max_games)
        print("DONE", flush=True)
        return
    for series in series_list:
        mpath = out_dir / f"{series}_markets.json"
        if mpath.exists():
            markets = json.load(mpath.open())
        else:
            markets = settled_markets(series)
            json.dump(markets, mpath.open("w"))
        print(f"{series}: {len(markets)} settled markets", flush=True)
        fetch_candles(series, markets, out_dir / f"{series}_candles.jsonl")
    print("DONE", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    hist = "--historical" in args
    cap = next((int(a.split("=")[1]) for a in args if a.startswith("--max-games=")), None)
    args = [a for a in args if a != "--historical" and not a.startswith("--max-games=")]
    main(Path(args[0]), args[1:] or DEFAULT_SERIES, historical=hist, max_games=cap)
