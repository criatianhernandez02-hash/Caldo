"""Roster status, injury reports, depth charts and snap counts (all from nflverse).

Everything here is known before the game it is attached to: the Friday injury
report, the weekly roster designation (active, IR, IR-designated to return,
PUP, suspended, cut), the depth chart published that week, and the snap
counts of earlier games.
"""
import glob

import numpy as np
import pandas as pd

from .config import POSITIONS, RAW_DIR

NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
EXTRA_SOURCES = {
    "status/roster_weekly_{season}.csv": NFLVERSE + "/weekly_rosters/roster_weekly_{season}.csv",
    "status/injuries_{season}.csv": NFLVERSE + "/injuries/injuries_{season}.csv",
    "depth/depth_charts_{season}.csv": NFLVERSE + "/depth_charts/depth_charts_{season}.csv",
    "snaps/snap_counts_{season}.csv": NFLVERSE + "/snap_counts/snap_counts_{season}.csv",
}
SKILL = POSITIONS + ["FB"]
STATUS_FLAGS = ["on53", "res_inj", "res_dtr", "res_other", "pup", "ps", "cut"]
REPORT_FLAGS = ["rep_out", "rep_doubt", "rep_quest", "prac_dnp", "prac_lim", "prac_full"]


def roster_status(seasons):
    """One row per player-week with a roster designation."""
    frames = []
    for season in seasons:
        path = RAW_DIR / f"status/roster_weekly_{season}.csv"
        if not path.exists():
            continue
        r = pd.read_csv(path, low_memory=False,
                        usecols=["season", "week", "gsis_id", "full_name", "position", "status", "status_description_abbr", "team", "game_type"])
        r = r[(r.game_type == "REG") & r.position.isin(SKILL) & r.gsis_id.notna()]
        frames.append(r)
    r = pd.concat(frames, ignore_index=True).rename(columns={"gsis_id": "player_id"})
    abbr = r.status_description_abbr.fillna("")
    st = r.status
    r["on53"] = st.isin(["ACT", "INA", "TRC", "TRD", "TRT"])    # INA is the game-day inactive list: on the 53, not dressed
    r["res_dtr"] = abbr.eq("R48")                                 # IR, designated to return
    r["res_inj"] = (st.eq("RES") & ~abbr.isin(["R48", "R02", "R59", "R62"])) | st.eq("PUP")
    r["res_other"] = (st.eq("RES") & abbr.isin(["R02", "R59", "R62"])) | st.isin(["RET", "SUS", "NWT", "EXE", "RSN", "RSR"])
    r["pup"] = st.eq("PUP")
    r["ps"] = st.eq("DEV")
    r["cut"] = st.isin(["CUT", "UFA", "RFA"])
    # one row per player-week: prefer the roster he is active on
    pri = r.on53.astype(int) * 3 + r.res_dtr.astype(int) * 2 + r.res_inj.astype(int)
    r = r.assign(_p=pri).sort_values("_p", ascending=False).drop_duplicates(["season", "week", "player_id"])
    r["position"] = r.position.replace({"FB": "RB"})
    return r[["season", "week", "player_id", "full_name", "team", "position"] + STATUS_FLAGS].reset_index(drop=True)


def injury_reports(seasons):
    frames = []
    for season in seasons:
        path = RAW_DIR / f"status/injuries_{season}.csv"
        if not path.exists():
            continue
        i = pd.read_csv(path, low_memory=False,
                        usecols=["season", "week", "gsis_id", "game_type", "report_status", "practice_status"])
        frames.append(i[(i.game_type == "REG") & i.gsis_id.notna()])
    i = pd.concat(frames, ignore_index=True).rename(columns={"gsis_id": "player_id"})
    rs, ps = i.report_status.fillna(""), i.practice_status.fillna("")
    i["rep_out"] = rs.eq("Out")
    i["rep_doubt"] = rs.eq("Doubtful")
    i["rep_quest"] = rs.eq("Questionable")
    i["prac_dnp"] = ps.str.startswith("Did Not") | ps.str.startswith("Out")
    i["prac_lim"] = ps.str.startswith("Limited")
    i["prac_full"] = ps.str.startswith("Full")
    i = i.drop_duplicates(["season", "week", "player_id"])
    return i[["season", "week", "player_id"] + REPORT_FLAGS].reset_index(drop=True)


def depth_ranks(seasons, games):
    """Depth-chart rank at the player's own position (1 = listed starter) per team-week.

    Through 2024 nflverse publishes one chart per week; from 2025 it publishes
    daily snapshots, so the latest snapshot before the team's game is used.
    """
    frames = []
    gd = games[["season", "week", "team", "gameday"]].drop_duplicates()
    gd["gameday"] = pd.to_datetime(gd.gameday)
    for season in seasons:
        path = RAW_DIR / f"depth/depth_charts_{season}.csv"
        if not path.exists():
            continue
        d = pd.read_csv(path, low_memory=False)
        if "depth_team" in d.columns:
            d = d[(d.game_type == "REG") & (d.formation == "Offense") & d.position.isin(SKILL) & d.gsis_id.notna()]
            d = d.assign(position=d.position.replace({"FB": "RB"}), depth_rank=d.depth_team.astype(float),
                         team=d.club_code, week=d.week.astype(int)).rename(columns={"gsis_id": "player_id"})
            d = d.groupby(["season", "week", "team", "player_id", "position"], as_index=False).depth_rank.min()
            d["season"] = season
        else:
            d = d[d.pos_abb.isin(SKILL) & d.gsis_id.notna() & ~d.pos_grp.str.contains("D|Special", regex=True)]
            d = d.assign(dt=pd.to_datetime(d.dt).dt.tz_localize(None).dt.normalize(),
                         position=d.pos_abb.replace({"FB": "RB"}), depth_rank=d.pos_rank.astype(float)) \
                 .rename(columns={"gsis_id": "player_id"})
            snaps = d[["team", "dt"]].drop_duplicates()
            tw = gd[gd.season == season].sort_values("gameday")
            # latest snapshot on or before each team's game day (the chart teams play with)
            pick = pd.merge_asof(tw, snaps.sort_values("dt"), left_on="gameday", right_on="dt", by="team", direction="backward")
            pick = pick.dropna(subset=["dt"])
            d = d.merge(pick[["season", "week", "team", "dt"]], on=["team", "dt"])
            d = d.groupby(["season", "week", "team", "player_id", "position"], as_index=False).depth_rank.min()
        frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    # a player can be charted at two spots (e.g. WR and RB); keep his best rank
    return out.groupby(["season", "week", "player_id"], as_index=False).depth_rank.min()


def snap_shares(seasons):
    """Offensive snap share per player-game, keyed by gsis id."""
    players = pd.read_csv(RAW_DIR / "players.csv", low_memory=False, usecols=["gsis_id", "pfr_id"]).dropna()
    pfr = dict(zip(players.pfr_id, players.gsis_id))
    frames = []
    for season in seasons:
        path = RAW_DIR / f"snaps/snap_counts_{season}.csv"
        if not path.exists():
            continue
        s = pd.read_csv(path, low_memory=False, usecols=["game_id", "season", "week", "game_type", "pfr_player_id", "position", "offense_pct"])
        s = s[(s.game_type == "REG") & s.position.isin(SKILL)]
        s["player_id"] = s.pfr_player_id.map(pfr)
        frames.append(s.dropna(subset=["player_id"])[["game_id", "player_id", "offense_pct"]])
    if not frames:
        return pd.DataFrame(columns=["game_id", "player_id", "snap_pct"])
    s = pd.concat(frames, ignore_index=True).rename(columns={"offense_pct": "snap_pct"})
    return s.groupby(["game_id", "player_id"], as_index=False).snap_pct.max()
