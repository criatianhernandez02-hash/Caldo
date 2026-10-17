"""Download Kalshi's settled NFL touchdown markets and their hourly price history.

    python research/fetch_kalshi.py <out_dir>

Writes <out_dir>/td_settled.json, passtd_settled.json, candles/<event>.json and
event_meta.json, which research/kalshi_history.py turns into pre-kickoff prices.
Kalshi's public market-data API needs no account but rate-limits (HTTP 429), so this
backs off and pauses between requests; a full season takes ~10 minutes.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tdmodel.data import load_games  # noqa: E402

API = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = {"KXNFLTD": "td_settled.json", "KXNFLPASSTDS": "passtd_settled.json"}
ALIAS = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS", "LVR": "LV", "ARZ": "ARI", "LAS": "LV"}


def get(url: str, params: dict) -> requests.Response:
    for attempt in range(8):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code != 429:
            return r
        time.sleep(5 * (attempt + 1))
    return r


def fetch_settled(series: str) -> list[dict]:
    markets, cursor = [], None
    while True:
        params = {"series_ticker": series, "status": "settled", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        r = get(f"{API}/markets", params)
        r.raise_for_status()
        body = r.json()
        markets += body.get("markets", [])
        cursor = body.get("cursor")
        if not cursor:
            return markets
        time.sleep(1.5)


def match_game(event_code: str, games: pd.DataFrame):
    """'26OCT11NYGWAS' -> (game_id, kickoff UTC) by date and team pair."""
    date = dt.datetime.strptime(event_code[:7], "%y%b%d").date()
    teams = event_code[7:]
    for _, g in games[games["date"] == date].iterrows():
        for a in (2, 3):
            pair = {ALIAS.get(teams[:a], teams[:a]), ALIAS.get(teams[a:], teams[a:])}
            if pair == {g.away_team, g.home_team}:
                return g.game_id, g.kick
    return None, None


def main(out: Path) -> None:
    (out / "candles").mkdir(parents=True, exist_ok=True)
    games = load_games()
    games = games[games["home_score"].notna()].copy()
    games["date"] = pd.to_datetime(games["gameday"]).dt.date
    games["kick"] = (pd.to_datetime(games["gameday"] + " " + games["gametime"])
                     .dt.tz_localize("America/New_York").dt.tz_convert("UTC"))
    events = {}
    for series, name in SERIES.items():
        markets = fetch_settled(series)
        json.dump(markets, open(out / name, "w"))
        print(series, len(markets), "settled markets", flush=True)
        events.update({m["event_ticker"]: series for m in markets})
    meta = {}
    for ev, series in sorted(events.items()):
        gid, kick = match_game(ev.split("-")[1], games)
        if gid is None:
            continue  # preseason / unmatched
        meta[ev] = {"game_id": gid, "kick": kick.isoformat(), "series": series}
        path = out / "candles" / f"{ev}.json"
        if path.exists():
            continue
        r = get(f"{API}/series/{series}/events/{ev}/candlesticks",
                {"start_ts": int((kick - pd.Timedelta(days=3)).timestamp()),
                 "end_ts": int((kick + pd.Timedelta(hours=1)).timestamp()), "period_interval": 60})
        if r.ok:
            json.dump(r.json(), open(path, "w"))
            print("candles", ev, flush=True)
        time.sleep(1.2)
    json.dump(meta, open(out / "event_meta.json", "w"), indent=1)
    print("done:", len(meta), "events")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
