"""Download settled Kalshi NFL player-stat ladder markets and their prices around kickoff.

    python research/fetch_kalshi_props.py <out_dir> [SERIES ...]

For each series (default: receiving yards, rushing yards, receptions) this saves
  <out_dir>/<SERIES>_markets.json   every settled market (ticker, event, title, strike, result)
  <out_dir>/<SERIES>_candles.jsonl  hourly candles from 8h before to 1h after kickoff - one line per market
Kickoff comes from the nflverse schedule (data_cache/games.csv), matched on the date and the
two team codes in the event ticker (e.g. KXNFLRECYDS-26SEP13DALNYG), so preseason games and
anything without a schedule match are skipped. Markets whose game is on the same day share
one candlestick request (100 markets max). Re-running resumes.

    python research/fetch_kalshi_props.py --historical <out_dir> [SERIES ...]

does the same for an older season (default 2025, weeks 4-18) from Kalshi's /historical
endpoints, which serve candles one market per request. To keep that affordable it takes
half of the games (a reproducible hash sample) and, for each player in them, only the middle
rung of his ladder (the strikes are set before the game, so this uses no outcome information).
Files are named <SERIES>_hist_markets.json / <SERIES>_hist_candles.jsonl.

    python research/fetch_kalshi_props.py --pre-hours 96 <out_dir> [SERIES ...]

fetches the current-season candles from 96 hours (or any N) before kickoff, for timing and
closing-line-value tests.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.fetch_kalshi_games import get, slim  # noqa: E402

DEFAULT_SERIES = ["KXNFLRECYDS", "KXNFLRSHYDS", "KXNFLREC"]
KEEP = ("ticker", "event_ticker", "title", "yes_sub_title", "floor_strike", "result", "close_time", "volume_fp")
PRE_H, POST_H = 8, 1
ALIAS = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS", "LVR": "LV", "ARZ": "ARI"}
MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def settled(series: str, historical: bool = False) -> list[dict]:
    out, cursor = [], None
    while True:
        params = {"series_ticker": series, "limit": 1000}
        if not historical:
            params["status"] = "settled"
        if cursor:
            params["cursor"] = cursor
        r = get("/historical/markets" if historical else "/markets", params)
        r.raise_for_status()
        body = r.json()
        out += [{k: m.get(k) for k in KEEP} for m in body.get("markets", [])]
        cursor = body.get("cursor")
        if not cursor:
            return out
        time.sleep(0.5)


def kickoffs() -> dict[tuple, tuple[str, int]]:
    """(date, frozenset(teams)) -> (nflverse game_id, kickoff unix time), regular season and playoffs."""
    g = pd.read_csv(ROOT / "data_cache" / "games.csv")
    g = g[g["gametime"].notna()]
    out = {}
    for r in g.itertuples():
        t = pd.Timestamp(f"{r.gameday} {r.gametime}", tz="America/New_York")
        day = dt.date.fromisoformat(r.gameday)
        out[(day, frozenset((r.away_team, r.home_team)))] = (r.game_id, int(t.timestamp()))
    return out


def match(event: str, ko: dict) -> tuple[str, int] | None:
    code = event.split("-")[1]  # 26SEP13DALNYG
    day = dt.date(2000 + int(code[:2]), MONTHS[code[2:5]], int(code[5:7]))
    teams = code[7:]
    for cut in range(2, 4):  # team codes are 2-3 letters
        for a, h in ((teams[:cut], teams[cut:]), (teams[:-cut], teams[-cut:])):
            pair = frozenset((ALIAS.get(a, a), ALIAS.get(h, h)))
            for d in (day, day - dt.timedelta(days=1), day + dt.timedelta(days=1)):
                if (d, pair) in ko:
                    return ko[(d, pair)]
    return None


def main(out_dir: Path, series_list: list[str], pre_hours: int = PRE_H) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    per = max(1, min(100, 9500 // (pre_hours + POST_H + 14)))  # a day's kickoffs span up to ~14h; 10,000-candle cap
    ko = kickoffs()
    for series in series_list:
        ms = settled(series)
        for m in ms:
            hit = match(m["event_ticker"], ko)
            m["game_id"], m["kickoff"] = hit if hit else (None, None)
        json.dump(ms, (out_dir / f"{series}_markets.json").open("w"))
        cpath = out_dir / f"{series}_candles.jsonl"
        done = {json.loads(line)["ticker"] for line in cpath.open()} if cpath.exists() else set()
        todo = [m for m in ms if m["kickoff"] and m["result"] in ("yes", "no") and m["ticker"] not in done]
        print(f"{series}: {len(ms)} settled, {sum(1 for m in ms if m['kickoff'])} matched to a game, "
              f"{len(todo)} to fetch", flush=True)
        by_day = defaultdict(list)
        for m in todo:
            by_day[dt.datetime.utcfromtimestamp(m["kickoff"] - 6 * 3600).date()].append(m)
        with cpath.open("a") as fh:
            for day, group in sorted(by_day.items()):
                group.sort(key=lambda m: m["kickoff"])
                for i in range(0, len(group), per):
                    chunk = group[i:i + per]
                    lo = min(m["kickoff"] for m in chunk) - pre_hours * 3600
                    hi = max(m["kickoff"] for m in chunk) + POST_H * 3600
                    r = get("/markets/candlesticks", {"market_tickers": ",".join(m["ticker"] for m in chunk),
                                                      "start_ts": lo, "end_ts": hi, "period_interval": 60})
                    if not r.ok:
                        print("  fail", series, day, r.status_code, r.text[:120], flush=True)
                        continue
                    got = {x["market_ticker"]: x.get("candlesticks", []) for x in r.json().get("markets", [])}
                    for m in chunk:
                        fh.write(json.dumps({"ticker": m["ticker"], "candles": [slim(c) for c in got.get(m["ticker"], [])]}) + "\n")
                    time.sleep(0.5)
                print(f"  {series} {day}: {len(group)}", flush=True)
    print("DONE", flush=True)


def main_historical(out_dir: Path, series_list: list[str], season: int = 2025, weeks: tuple = (4, 18)) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ko = kickoffs()
    h = lambda x: hashlib.md5(x.encode()).hexdigest()
    for series in series_list:
        ms = settled(series, historical=True)
        for m in ms:
            hit = match(m["event_ticker"], ko)
            m["game_id"], m["kickoff"] = hit if hit else (None, None)
        ms = [m for m in ms if m["game_id"] and int(m["game_id"][:4]) == season
              and weeks[0] <= int(m["game_id"][5:7]) <= weeks[1] and m["result"] in ("yes", "no")
              and m.get("floor_strike") is not None and h(m["game_id"]) < "8"]  # half of the games
        json.dump(ms, (out_dir / f"{series}_hist_markets.json").open("w"))
        ladders = defaultdict(list)
        for m in ms:
            ladders[m["ticker"].rsplit("-", 1)[0]].append(m)
        picks = []
        for rungs in ladders.values():
            rungs.sort(key=lambda m: float(m["floor_strike"]))
            picks.append(rungs[(len(rungs) - 1) // 2])
        cpath = out_dir / f"{series}_hist_candles.jsonl"
        done = {json.loads(line)["ticker"] for line in cpath.open()} if cpath.exists() else set()
        todo = sorted((m for m in picks if m["ticker"] not in done), key=lambda m: m["kickoff"])
        print(f"{series} (historical {season}): {len(ms)} markets in sampled games, {len(picks)} ladders, "
              f"{len(todo)} to fetch", flush=True)
        with cpath.open("a") as fh:
            for i, m in enumerate(todo):
                r = get(f"/historical/markets/{m['ticker']}/candlesticks",
                        {"start_ts": m["kickoff"] - 2 * 3600, "end_ts": m["kickoff"], "period_interval": 60})
                if r.ok:
                    fh.write(json.dumps({"ticker": m["ticker"], "candles": [slim(c) for c in r.json().get("candlesticks", [])]}) + "\n")
                if i % 200 == 0:
                    print(f"  {series} {i}/{len(todo)}", flush=True)
                time.sleep(0.3)
    print("DONE", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--pre-hours":
        main(Path(sys.argv[3]), sys.argv[4:] or DEFAULT_SERIES, pre_hours=int(sys.argv[2]))
    elif sys.argv[1] == "--historical":
        main_historical(Path(sys.argv[2]), sys.argv[3:] or DEFAULT_SERIES)
    else:
        main(Path(sys.argv[1]), sys.argv[2:] or DEFAULT_SERIES)
