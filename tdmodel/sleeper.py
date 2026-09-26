"""Pull live Sleeper Picks lines (with payout multipliers) and injury statuses.

Uses the endpoints the Sleeper app itself calls. `lines/available` is undocumented, so it
can change without notice; the player database is Sleeper's public API, which asks callers
to fetch it at most once a day (it is cached for 24h here).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

from .data import DEFAULT_CACHE

LINES_URL = "https://api.sleeper.app/lines/available"
PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
HEADERS = {"User-Agent": "Mozilla/5.0 (tdmodel)"}

WAGER_TO_MARKET = {"anytime_touchdowns": "anytime_td", "passing_touchdowns": "pass_tds"}
SIDE = {"over": "more", "under": "less"}
SKIP_STATUSES = {"Out", "Doubtful", "IR", "PUP", "Sus", "NA", "COV"}


def load_players(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> dict:
    path = cache_dir / "sleeper_players_nfl.json"
    if refresh or not path.exists() or time.time() - path.stat().st_mtime > 24 * 3600:
        resp = requests.get(PLAYERS_URL, headers=HEADERS, timeout=120)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    return json.loads(path.read_text())


def fetch_raw_lines() -> list[dict]:
    resp = requests.get(LINES_URL, headers=HEADERS, timeout=60,
                        params={"dynamic": "true", "include_pregame": "true"})
    resp.raise_for_status()
    return resp.json()


def parse_lines(raw: list[dict], players: dict) -> pd.DataFrame:
    """One row per pickable side: player, market, line, side, multiplier (+ ids, injury)."""
    rows = []
    for mkt in raw:
        if mkt.get("sport") != "nfl" or mkt.get("status") != "active":
            continue
        market = WAGER_TO_MARKET.get(mkt.get("wager_type"))
        if market is None or mkt.get("game_status") != "pre_game":
            continue
        info = players.get(str(mkt.get("subject_id")), {})
        for opt in mkt.get("options", []):
            if opt.get("status") != "active" or opt.get("outcome") not in SIDE:
                continue
            rows.append({
                "player": info.get("full_name") or opt.get("subject_id"),
                "player_id": info.get("gsis_id"),
                "market": market,
                "line": float(opt["outcome_value"]),
                "side": SIDE[opt["outcome"]],
                "multiplier": float(opt["payout_multiplier"]),
                "line_type": opt.get("line_type", "normal"),
                "injury_status": info.get("injury_status"),
            })
    cols = ["player", "player_id", "market", "line", "side", "multiplier", "line_type", "injury_status"]
    return pd.DataFrame(rows, columns=cols)


def fetch_lines(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> pd.DataFrame:
    return parse_lines(fetch_raw_lines(), load_players(cache_dir, refresh))


def injury_report(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> pd.DataFrame:
    """gsis_id -> Sleeper injury status, for every NFL player that has one."""
    players = load_players(cache_dir, refresh)
    rows = [{"player_id": p.get("gsis_id"), "injury_status": p.get("injury_status")}
            for p in players.values() if p.get("gsis_id") and p.get("injury_status")]
    return pd.DataFrame(rows, columns=["player_id", "injury_status"])
