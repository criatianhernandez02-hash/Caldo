"""Download nflverse data and build the player-game panel the model trains on.

Panel = one row per (player, team game) from the player's first appearance in
a season through the end of that regular season. Rows where the player did
not record a stat have played=0 and 0 points, so rest-of-season totals reflect
injuries, benchings and byes exactly as a fantasy manager would feel them.
"""
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

from . import status
from .config import CACHE_DIR, FIRST_SEASON, POSITIONS, RAW_DIR, SCORING, SOURCES

STAT_COLS = [
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
    "carries", "rushing_yards", "rushing_tds", "receptions", "targets",
    "receiving_yards", "receiving_tds", "target_share", "air_yards_share",
    "receiving_air_yards", "fantasy_points", "fantasy_points_ppr",
]


def _download(url, dest, force=False):
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)
    return dest


def fetch(last_season, refresh_current=True):
    """Download every raw file needed for FIRST_SEASON..last_season."""
    for season in range(FIRST_SEASON, last_season + 1):
        force = refresh_current and season == last_season
        _download(SOURCES["stats"].format(season=season), RAW_DIR / f"stats_player_week_{season}.csv", force)
        _download(SOURCES["pbp"].format(season=season), RAW_DIR / "pbp" / f"play_by_play_{season}.parquet", force)
    _download(SOURCES["games"], RAW_DIR / "games.csv", refresh_current)
    _download(SOURCES["players"], RAW_DIR / "players.csv", refresh_current)
    for season in range(FIRST_SEASON, last_season + 1):
        for rel, url in status.EXTRA_SOURCES.items():
            try:
                _download(url.format(season=season), RAW_DIR / rel.format(season=season), refresh_current and season == last_season)
            except urllib.error.HTTPError:  # snap counts start in 2013, etc.
                pass


def load_games():
    """One row per team per regular-season game, with Vegas context."""
    g = pd.read_csv(RAW_DIR / "games.csv", low_memory=False)
    g = g[(g.game_type == "REG") & (g.season >= FIRST_SEASON)].copy()
    neutral = g.location.eq("Neutral")
    # spread_line > 0 means the home team is favored
    home_itt = g.total_line / 2 + g.spread_line / 2
    away_itt = g.total_line / 2 - g.spread_line / 2
    dome = g.roof.isin(["dome", "closed"]).astype(float)
    common = ["game_id", "season", "week", "gameday"]
    home = g[common].assign(
        team=g.home_team, opp=g.away_team, home=np.where(neutral, 0.0, 1.0),
        itt=home_itt, spread=g.spread_line, total=g.total_line,
        pts_for=g.home_score, pts_against=g.away_score, rest=g.home_rest, dome=dome)
    away = g[common].assign(
        team=g.away_team, opp=g.home_team, home=0.0,
        itt=away_itt, spread=-g.spread_line, total=g.total_line,
        pts_for=g.away_score, pts_against=g.home_score, rest=g.away_rest, dome=dome)
    tg = pd.concat([home, away], ignore_index=True)
    tg["completed"] = tg.pts_for.notna()
    return tg.sort_values(["season", "week", "team"]).reset_index(drop=True)


def _redzone_usage(season):
    """Red-zone and goal-line opportunities per player-game from play-by-play."""
    cols = ["game_id", "season_type", "play_type", "yardline_100", "rusher_player_id",
            "receiver_player_id", "pass_attempt", "rush_attempt", "two_point_attempt"]
    p = pd.read_parquet(RAW_DIR / "pbp" / f"play_by_play_{season}.parquet", columns=cols)
    p = p[(p.season_type == "REG") & p.play_type.isin(["run", "pass"]) & (p.two_point_attempt != 1)]
    rush = p[(p.rush_attempt == 1) & p.rusher_player_id.notna()]
    rec = p[(p.pass_attempt == 1) & p.receiver_player_id.notna()]
    r = rush.assign(rz_carries=rush.yardline_100 <= 20, gl_carries=rush.yardline_100 <= 5) \
        .groupby(["game_id", "rusher_player_id"])[["rz_carries", "gl_carries"]].sum()
    r.index.names = ["game_id", "player_id"]
    t = rec.assign(rz_targets=rec.yardline_100 <= 20, i10_targets=rec.yardline_100 <= 10) \
        .groupby(["game_id", "receiver_player_id"])[["rz_targets", "i10_targets"]].sum()
    t.index.names = ["game_id", "player_id"]
    return r.join(t, how="outer").fillna(0).reset_index()


def load_player_games(last_season):
    """Played games (one row per player-game with a recorded stat)."""
    frames = []
    for season in range(FIRST_SEASON, last_season + 1):
        s = pd.read_csv(RAW_DIR / f"stats_player_week_{season}.csv", low_memory=False)
        s = s[(s.season_type == "REG")]
        s["position"] = s.position.replace({"FB": "RB"})
        s = s[s.position.isin(POSITIONS)]
        s = s[["player_id", "player_display_name", "position", "season", "week", "game_id", "team"] + STAT_COLS]
        s = s.merge(_redzone_usage(season), on=["game_id", "player_id"], how="left")
        frames.append(s)
    pg = pd.concat(frames, ignore_index=True)
    rz = ["rz_carries", "gl_carries", "rz_targets", "i10_targets"]
    pg[rz] = pg[rz].fillna(0)
    pg[STAT_COLS] = pg[STAT_COLS].fillna(0)
    pg["pts_std"] = pg.fantasy_points
    pg["pts_ppr"] = pg.fantasy_points_ppr
    pg["pts_half"] = (pg.pts_std + pg.pts_ppr) / 2
    pg["tds"] = pg.rushing_tds + pg.receiving_tds + pg.passing_tds * (pg.position == "QB")
    pg["skill_tds"] = pg.rushing_tds + pg.receiving_tds
    return pg.drop(columns=["fantasy_points", "fantasy_points_ppr"])


def build_panel(last_season, use_cache=True):
    """Player x team-game panel.

    A player is in the panel from the first week he either records a stat or
    sits on an NFL roster (active, inactive, IR, PUP), so injured starters are
    projected while they are out. Rows where he did not play have played=0.
    """
    cache = CACHE_DIR / f"panel_{last_season}.parquet"
    if use_cache and cache.exists():
        return pd.read_parquet(cache), load_games()
    tg = load_games()
    pg = load_player_games(last_season)
    seasons = list(range(FIRST_SEASON, last_season + 1))
    rs = status.roster_status(seasons)
    rostered = rs[rs.on53 | rs.res_inj | rs.res_dtr | rs.pup]

    sched = tg[["season", "week", "team", "game_id"]]
    rows = []
    for season in seasons:
        weeks = sched[sched.season == season]
        all_weeks = np.sort(weeks.week.unique())
        p = pg[pg.season == season][["player_id", "week", "team"]].drop_duplicates(["player_id", "week"])
        r = rostered[rostered.season == season][["player_id", "week", "team"]].drop_duplicates(["player_id", "week"])
        first = pd.concat([p, r]).groupby("player_id").week.min().rename("first_week").reset_index()
        grid = first.loc[first.index.repeat(len(all_weeks))].assign(week=np.tile(all_weeks, len(first)))
        grid = grid[grid.week >= grid.first_week]
        grid = grid.merge(p.rename(columns={"team": "team_g"}), on=["player_id", "week"], how="left") \
                   .merge(r.rename(columns={"team": "team_r"}), on=["player_id", "week"], how="left")
        grid["team"] = grid.team_g.fillna(grid.team_r)
        grid = grid.sort_values(["player_id", "week"])
        grid["team"] = grid.groupby("player_id").team.ffill()
        grid["season"] = season
        grid = grid.merge(weeks, on=["season", "week", "team"], how="inner")  # drops byes
        rows.append(grid[["player_id", "season", "week", "team", "game_id"]])
    panel = pd.concat(rows, ignore_index=True)

    meta = pg.sort_values(["season", "week"]).groupby("player_id")[["player_display_name", "position"]].last()
    rmeta = rs.sort_values(["season", "week"]).groupby("player_id")[["full_name", "position"]].last() \
              .rename(columns={"full_name": "player_display_name"})
    meta = pd.concat([rmeta[~rmeta.index.isin(meta.index)], meta])
    panel = panel.merge(meta, left_on="player_id", right_index=True)
    keep = [c for c in pg.columns if c not in ("player_display_name", "position", "season", "week", "team")]
    panel = panel.merge(pg[keep], on=["player_id", "game_id"], how="left")
    panel["played"] = panel.pts_ppr.notna().astype(int)
    num = [c for c in keep if c not in ("player_id", "game_id")]
    panel[num] = panel[num].fillna(0)

    ctx = tg[["game_id", "team", "opp", "home", "itt", "spread", "total", "rest", "dome", "gameday", "completed"]]
    panel = panel.merge(ctx, on=["game_id", "team"], how="left")

    # roster designation for the week; future weeks carry the latest known one
    panel = panel.merge(rs[["season", "week", "player_id"] + status.STATUS_FLAGS], on=["season", "week", "player_id"], how="left")
    last_week = rs.groupby("season").week.max()
    known = panel.week <= panel.season.map(last_week)
    missing = panel.on53.isna()
    for c in status.STATUS_FLAGS:
        panel.loc[missing & known, c] = (c == "cut")
    panel = panel.sort_values(["player_id", "season", "week"]).reset_index(drop=True)
    panel[status.STATUS_FLAGS] = panel.groupby(["player_id", "season"])[status.STATUS_FLAGS].ffill()
    panel["on53"] = panel.on53.fillna(True)
    panel[status.STATUS_FLAGS] = panel[status.STATUS_FLAGS].fillna(False).astype(float)

    inj = status.injury_reports(seasons)
    panel = panel.merge(inj, on=["season", "week", "player_id"], how="left")
    panel[status.REPORT_FLAGS] = panel[status.REPORT_FLAGS].fillna(False).astype(float)

    depth = status.depth_ranks(seasons, tg)
    panel = panel.merge(depth, on=["season", "week", "player_id"], how="left")
    panel["depth_rank"] = panel.groupby(["player_id", "season"]).depth_rank.ffill()

    snaps = status.snap_shares(seasons)
    panel = panel.merge(snaps, on=["game_id", "player_id"], how="left")

    players = pd.read_csv(RAW_DIR / "players.csv", low_memory=False,
                          usecols=["gsis_id", "birth_date", "draft_pick", "draft_year", "rookie_season"])
    players = players.rename(columns={"gsis_id": "player_id"}).drop_duplicates("player_id")
    panel = panel.merge(players, on="player_id", how="left")
    panel["age"] = panel.season - pd.to_datetime(panel.birth_date, errors="coerce").dt.year
    panel = panel.drop(columns=["birth_date"]).sort_values(["player_id", "season", "week"]).reset_index(drop=True)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(cache)
    return panel, tg


def points_col(scoring):
    if scoring not in SCORING:
        raise ValueError(f"scoring must be one of {list(SCORING)}")
    return f"pts_{scoring}"
