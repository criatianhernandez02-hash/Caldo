"""Download and cache the free nflverse data the model runs on.

Two sources:
  * weekly player stats (one CSV per season) - touches, targets, TDs
  * the schedule, which also carries the Vegas spread and total for each game
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests

PLAYER_WEEKS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_week_{season}.csv"
)
GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

DEFAULT_CACHE = Path(os.environ.get("TDMODEL_CACHE", "data_cache"))

# Files that can still change (current season, schedule/lines) are re-downloaded
# once they are older than this. Finished seasons are cached forever.
FRESH_HOURS = 6

PLAYER_COLS = [
    "player_id", "player_display_name", "position_group", "season", "week",
    "season_type", "game_id", "team", "opponent_team",
    "attempts", "passing_tds", "carries", "rushing_tds",
    "targets", "receptions", "receiving_tds",
]
OFFENSE_POSITIONS = ["QB", "RB", "WR", "TE"]


def _fetch(url: str, path: Path, max_age_hours: float | None, refresh: bool) -> Path:
    if path.exists() and not refresh:
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if max_age_hours is None or age_h < max_age_hours:
            return path
    path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(resp.content)
    tmp.replace(path)
    return path


def load_games(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> pd.DataFrame:
    path = _fetch(GAMES_URL, cache_dir / "games.csv", FRESH_HOURS, refresh)
    games = pd.read_csv(path, low_memory=False)
    return games[[
        "game_id", "season", "game_type", "week", "gameday", "gametime",
        "away_team", "home_team", "away_score", "home_score",
        "spread_line", "total_line", "roof",
        "away_qb_id", "home_qb_id", "away_qb_name", "home_qb_name",
    ]]


def load_player_weeks(
    seasons: list[int],
    current_season: int,
    cache_dir: Path = DEFAULT_CACHE,
    refresh: bool = False,
) -> pd.DataFrame:
    frames = []
    for season in seasons:
        max_age = FRESH_HOURS if season >= current_season else None
        path = _fetch(
            PLAYER_WEEKS_URL.format(season=season),
            cache_dir / f"stats_player_week_{season}.csv",
            max_age,
            refresh and season >= current_season,
        )
        df = pd.read_csv(path, low_memory=False)
        frames.append(df[[c for c in PLAYER_COLS if c in df.columns]])
    stats = pd.concat(frames, ignore_index=True)
    stats = stats[stats["position_group"].isin(OFFENSE_POSITIONS)].copy()
    for col in ["attempts", "passing_tds", "carries", "rushing_tds",
                "targets", "receptions", "receiving_tds"]:
        stats[col] = pd.to_numeric(stats[col], errors="coerce").fillna(0.0)
    return stats
