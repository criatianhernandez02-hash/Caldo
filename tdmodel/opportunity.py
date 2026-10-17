"""Expected touchdowns ("xTD") from the ffopportunity project (ffverse).

ffopportunity fits play-level models on nflverse play-by-play and reports, for every
player-week, how many touchdowns an average player would have scored given the same
opportunities (carries by field position, targets by depth/location, etc.). Actual
touchdowns are noisy; expected touchdowns are the signal underneath them, so a player's
share of his team's xTD should predict future TDs better than his share of actual TDs.

Files: https://github.com/ffverse/ffopportunity/releases/tag/latest-data
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data import DEFAULT_CACHE, FRESH_HOURS, _fetch

EP_URL = "https://github.com/ffverse/ffopportunity/releases/download/latest-data/ep_weekly_{season}.csv"

EP_COLS = {
    "player_id": "player_id", "season": "season", "week": "week", "posteam": "team",
    "rush_attempt": "ep_carries", "rec_attempt": "ep_targets", "pass_attempt": "ep_attempts",
    "rush_touchdown_exp": "x_rush_td", "rec_touchdown_exp": "x_rec_td", "pass_touchdown_exp": "x_pass_td",
    "rush_touchdown": "ep_rush_td", "rec_touchdown": "ep_rec_td", "pass_touchdown": "ep_pass_td",
}


def load_expected(seasons: list[int], current_season: int, cache_dir: Path = DEFAULT_CACHE,
                  refresh: bool = False) -> pd.DataFrame:
    frames = []
    for season in seasons:
        max_age = FRESH_HOURS if season >= current_season else None
        path = _fetch(EP_URL.format(season=season), cache_dir / f"ep_weekly_{season}.csv",
                      max_age, refresh and season >= current_season)
        df = pd.read_csv(path, low_memory=False, usecols=list(EP_COLS))
        frames.append(df.rename(columns=EP_COLS))
    ep = pd.concat(frames, ignore_index=True)
    # ffopportunity has a few duplicate player-week rows (position changes); sum them.
    num = [c for c in ep.columns if c not in ("player_id", "season", "week", "team")]
    ep = ep.groupby(["player_id", "season", "week"], as_index=False).agg({**{c: "sum" for c in num}, "team": "first"})
    return ep


def attach_expected(stats: pd.DataFrame, ep: pd.DataFrame) -> pd.DataFrame:
    """Join xTD columns onto the nflverse weekly table; missing rows fall back to actual TDs."""
    out = stats.merge(ep.drop(columns=["team"]), on=["player_id", "season", "week"], how="left")
    for x, actual in (("x_rush_td", "rushing_tds"), ("x_rec_td", "receiving_tds"), ("x_pass_td", "passing_tds")):
        out[x] = out[x].fillna(out[actual])
    return out
