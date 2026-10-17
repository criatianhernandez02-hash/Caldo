"""Minute-by-minute Kalshi prices for the last hour of each game (current-season markets).

    python research/fetch_kalshi_endgame.py <games_dir> [SERIES ...]

Reads <games_dir>/<SERIES>_markets.json (from fetch_kalshi_games.py) and writes
<games_dir>/<SERIES>_endgame.jsonl: 1-minute candles from 70 minutes before each market's
close_time (Kalshi closes a game market minutes after the final whistle) to the close.
Used to test whether near-certain winners are underpriced late in games.

    python research/fetch_kalshi_endgame.py --historical <games_dir> [SERIES ...]
fetches the same 1-minute data for older seasons (one request per game, sampled).
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.fetch_kalshi_games import get, slim, ts  # noqa: E402

WINDOW_MIN = 70
BATCH = 100


def main(games_dir: Path, series_list: list[str]) -> None:
    for series in series_list:
        mpath = games_dir / f"{series}_markets.json"
        if not mpath.exists():
            continue
        out = games_dir / f"{series}_endgame.jsonl"
        done = {json.loads(line)["ticker"] for line in out.open()} if out.exists() else set()
        ms = [m for m in json.load(mpath.open()) if m.get("result") in ("yes", "no") and m.get("close_time")
              and m["ticker"] not in done]
        by_day = defaultdict(list)
        for m in ms:
            by_day[m["close_time"][:10]].append(m)
        print(f"{series}: {len(ms)} markets over {len(by_day)} days", flush=True)
        with out.open("a") as fh:
            for day, group in sorted(by_day.items()):
                group.sort(key=lambda m: m["close_time"])
                for i in range(0, len(group), BATCH):
                    chunk = group[i:i + BATCH]
                    closes = [ts(m["close_time"]) for m in chunk]
                    # one window per chunk must cover every market's last hour: split if too wide
                    lo, hi = min(closes) - WINDOW_MIN * 60, max(closes)
                    if (hi - lo) / 60 * len(chunk) > 9500:
                        subs = [[m] for m in chunk]
                    else:
                        subs = [chunk]
                    for sub in subs:
                        c = [ts(m["close_time"]) for m in sub]
                        r = get("/markets/candlesticks", {"market_tickers": ",".join(m["ticker"] for m in sub),
                                                          "start_ts": min(c) - WINDOW_MIN * 60, "end_ts": max(c),
                                                          "period_interval": 1})
                        if not r.ok:
                            print("  fail", series, day, r.status_code, r.text[:120], flush=True)
                            continue
                        got = {x["market_ticker"]: x.get("candlesticks", []) for x in r.json().get("markets", [])}
                        for m in sub:
                            fh.write(json.dumps({"ticker": m["ticker"], "close": m["close_time"],
                                                 "candles": [slim(x) for x in got.get(m["ticker"], [])]}) + "\n")
                        time.sleep(0.9)
                print(f"  {series} {day}: {len(group)}", flush=True)
    print("DONE", flush=True)




def main_historical(games_dir: Path, series_list: list[str], max_games: int = 600) -> None:
    """Older seasons: 1-minute candles from 90 to 230 minutes after the estimated start
    (expected_expiration - 3h), one side per game, a reproducible sample of max_games games."""
    import hashlib
    for series in series_list:
        mpath = games_dir / f"{series}_hist_markets.json"
        if not mpath.exists():
            continue
        out = games_dir / f"{series}_hist_endgame.jsonl"
        done = {json.loads(line)["ticker"] for line in out.open()} if out.exists() else set()
        first = {}
        for m in json.load(mpath.open()):
            if m.get("result") in ("yes", "no") and float(m.get("volume_fp") or 0) > 0 and m.get("expected_expiration_time"):
                if m["event_ticker"] not in first or m["ticker"] < first[m["event_ticker"]]["ticker"]:
                    first[m["event_ticker"]] = m
        todo = sorted(first.values(), key=lambda m: hashlib.md5(m["event_ticker"].encode()).hexdigest())
        todo = [m for m in todo[:max_games] if m["ticker"] not in done]
        print(f"{series} (historical endgame): {len(todo)} games", flush=True)
        with out.open("a") as fh:
            for i, m in enumerate(todo):
                start = ts(m["expected_expiration_time"]) - 3 * 3600
                r = get(f"/historical/markets/{m['ticker']}/candlesticks",
                        {"start_ts": start + 90 * 60, "end_ts": start + 230 * 60, "period_interval": 1})
                if r.ok:
                    fh.write(json.dumps({"ticker": m["ticker"], "event": m["event_ticker"], "start": start,
                                         "candles": [slim(c) for c in r.json().get("candlesticks", [])]}) + "\n")
                if i % 100 == 0:
                    print(f"  {series} {i}/{len(todo)}", flush=True)
                time.sleep(0.3)
    print("DONE", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--historical":
        main_historical(Path(args[1]), args[2:] or ["KXNHLGAME", "KXMLBGAME", "KXNBAGAME"])
    else:
        main(Path(args[0]), args[1:] or ["KXNHLGAME", "KXMLBGAME", "KXNBAGAME", "KXNFLGAME", "KXNCAAFGAME"])
