"""Pre-game features. Every feature at row t uses only games before t."""
import numpy as np
import pandas as pd

USAGE = ["targets", "receptions", "carries", "rz_carries", "gl_carries", "rz_targets",
         "i10_targets", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
         "rushing_yards", "receiving_yards", "target_share", "air_yards_share", "skill_tds", "tds"]

HL_SHORT, HL_LONG, HL_USAGE = 3, 10, 5


def _prior_ewm(df, col, halflife):
    """EWMA of a column over previously *played* games, per player."""
    v = df[col].where(df.played == 1)
    return v.groupby(df.player_id).transform(
        lambda s: s.shift().ewm(halflife=halflife, ignore_na=True).mean())


def add_features(panel, scoring="ppr"):
    df = panel.sort_values(["player_id", "season", "week"]).reset_index(drop=True).copy()
    df["pts"] = df[f"pts_{scoring}"]

    df["ewm_pts_s"] = _prior_ewm(df, "pts", HL_SHORT)
    df["ewm_pts_l"] = _prior_ewm(df, "pts", HL_LONG)
    for c in USAGE:
        df[f"u_{c}"] = _prior_ewm(df, c, HL_USAGE)

    gs = df.assign(pp=df.pts * df.played).groupby(["player_id", "season"])
    prior_sum = gs.pp.cumsum() - df.pts * df.played
    prior_n = gs.played.cumsum() - df.played
    df["szn_g"] = prior_n
    df["szn_pts"] = (prior_sum / prior_n).where(prior_n > 0)

    season_avg = (df[df.played == 1].groupby(["player_id", "season"])
                  .agg(prev_pts=("pts", "mean"), prev_g=("pts", "size")).reset_index())
    season_avg["season"] += 1
    df = df.merge(season_avg, on=["player_id", "season"], how="left")
    df["prev_g"] = df.prev_g.fillna(0)

    g = df.groupby("player_id")
    df["career_g"] = g.played.cumsum() - df.played
    df["played_last"] = g.played.shift().fillna(1)
    miss = 1 - df.played
    # consecutive missed team games immediately before this one
    streak_id = (df.played == 1).groupby(df.player_id).cumsum()
    df["miss_streak"] = miss.groupby([df.player_id, streak_id]).cumsum().groupby(df.player_id).shift().fillna(0)
    df["miss_rate8"] = miss.groupby(df.player_id).transform(
        lambda s: s.shift().rolling(8, min_periods=1).mean()).fillna(0)

    # role and availability context known before the game
    df["u_snap"] = _prior_ewm(df, "snap_pct", HL_USAGE)
    prev_team = df[df.played == 1].groupby(["player_id", "season"]).team.last().rename("prev_team").reset_index()
    prev_team["season"] += 1
    df = df.merge(prev_team, on=["player_id", "season"], how="left")
    df["new_team"] = (df.prev_team.notna() & (df.prev_team != df.team)).astype(float)
    df["returning"] = (df.miss_streak >= 2).astype(float)
    # Injured players slide down the depth chart while out; judge their role by
    # the chart from their last game played, and use this week's chart only for
    # players who are healthy and playing.
    played_depth = df.depth_rank.where(df.played == 1)
    last_depth = played_depth.groupby([df.player_id, df.season]).transform(lambda s: s.shift().ffill())
    healthy = (df.on53 == 1) & (df.miss_streak == 0)
    df["depth_eff"] = df.depth_rank.where(healthy | last_depth.isna(), last_depth)
    df["depth1"] = (df.depth_eff == 1).astype(float)
    df["depth3p"] = (df.depth_eff >= 3).astype(float)
    df["depth_na"] = df.depth_eff.isna().astype(float)

    df["rookie"] = (df.draft_year == df.season).astype(float)
    df["log_pick"] = np.log(df.draft_pick.fillna(300).clip(1, 300))
    df["age"] = df.age.fillna(df.groupby("position").age.transform("median"))
    return df
