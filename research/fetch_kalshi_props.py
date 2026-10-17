"""Download settled Kalshi NFL player-stat ladder markets and their prices around kickoff.

    python research/fetch_kalshi_props.py <out_dir> [SERIES ...]

For each series (default: receiving yards, rushing yards, receptions) this saves
  <out_dir>/<SERIES>_markets.json   every settled market (ticker, event, title, strike, result)
  <out_dir>/<SERIES>_candles.jsonl  hourly candles from 8h before to 1h after kickoff - one line per market
Kickoff comes from the nflverse schedule (data_cache/games.csv), matched on the date and the
two team codes in the event ticker (e.g. KXNFLRECYDS-26SEP13DALNYG), so preseason games and
anything without a schedule match are skipped. Markets whose game is on the same day share
one candlestick request (100 markets max). Re-running resumes.
"""

from __future__ import annotations

import datetime as dt
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


def settled(series: str) -> list[dict]:
    out, cursor = [], None
    while True:
        params = {"series_ticker": series, "limit": 1000, "status": "settled"}
        if cursor:
            params["cursor"] = cursor
        r = get("/markets", params)
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


def main(out_dir: Path, series_list: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
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
                for i in range(0, len(group), 100):
                    chunk = group[i:i + 100]
                    lo = min(m["kickoff"] for m in chunk) - PRE_H * 3600
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


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:] or DEFAULT_SERIES)
