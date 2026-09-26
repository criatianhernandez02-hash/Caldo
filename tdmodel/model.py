"""Touchdown projection model.

For every player the question is: how many touchdowns do we expect this week (lambda)?
Touchdowns are rare, roughly independent events, so the count is modelled as Poisson and

    P(anytime TD)       = 1 - exp(-lambda)
    P(QB over 1.5 TDs)  = 1 - P(0) - P(1)

Lambda is built from four pieces, each estimated from recency-weighted history:

  1. Game environment - the Vegas total and spread give each team's implied points, which
     converts to expected offensive TDs (the high-scoring-game part of the plan).
  2. Team split     - how the offense usually scores: rushing vs passing TDs.
  3. Player share   - the player's share of his team's rush / receiving / passing TDs,
     anchored to his carry / target share so a fluky 2-TD game does not dominate.
  4. Matchup        - how the opposing defense gives up its TDs: e.g. to RBs on the ground
     vs WRs through the air, relative to league average. The total already says *how many*
     points the defense allows, so the matchup term only captures *where* it allows them
     (otherwise a bad defense would be counted twice).

Small samples are shrunk towards league average (empirical-Bayes style pseudo-games), which
matters a lot early in the season.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

POSITIONS = ["QB", "RB", "WR", "TE"]
CATEGORIES = [f"{kind}_{pos}" for pos in POSITIONS for kind in ("rush", "rec")]


@dataclass
class Config:
    half_life_games: float = 8.0       # recency weighting for TD rates and defenses
    usage_half_life_games: float = 6.0  # usage/role (carry & target share) recency weighting
    prior_season_weight: float = 0.6   # extra discount on last season's games
    defense_prior_games: float = 32.0  # shrink defensive splits toward league average
    offense_prior_games: float = 8.0   # shrink team rush/pass split toward league average
    td_share_prior: float = 20.0       # pseudo team-TDs anchoring a player's TD share to his usage
    matchup_clip: tuple[float, float] = (0.6, 1.6)
    # 0 = ignore defensive splits, 1 = full effect. Backtests (2024 tune, 2025 holdout) show the
    # Vegas total already prices most of the matchup, so it is kept as a light tie-breaker.
    matchup_weight: float = 0.25
    use_vegas: bool = True             # False = implied points from recent scoring only (for testing)
    # Calibration multipliers on expected TDs, fitted on 2024-25 walk-forward backtests
    # (the raw model under-projects TEs and QB passing TDs, and slightly over-projects RBs).
    calibration: tuple[tuple[str, float], ...] = (("RB", 0.95), ("WR", 1.05), ("TE", 1.2), ("QB_pass", 1.07))
    shootout_total: float = 48.5       # game total that gets flagged as a shootout
    starter_pass_share: float = 0.97   # share of team passing TDs thrown by a healthy starting QB
    min_touches_rb: float = 6.0
    min_targets_wr: float = 3.0
    min_targets_te: float = 2.0
    min_attempts_qb: float = 15.0


# --------------------------------------------------------------------------------------
# helpers


def _decay(age: pd.Series, half_life: float) -> pd.Series:
    return 0.5 ** (age / half_life)


def _wsum(df: pd.DataFrame, by: str, cols: list[str], w: str) -> pd.DataFrame:
    tmp = df[cols].multiply(df[w], axis=0)
    tmp[by] = df[by]
    out = tmp.groupby(by).sum()
    out["_w"] = df.groupby(by)[w].sum()
    return out


def poisson_sf(lam: np.ndarray | float, line: float) -> np.ndarray | float:
    """P(X > line) for Poisson(lam); line is a half-point prop like 0.5 / 1.5 / 2.5."""
    lam = np.asarray(lam, dtype=float)
    k_max = int(np.floor(line))
    cdf = np.zeros_like(lam)
    term = np.exp(-lam)
    for k in range(k_max + 1):
        if k > 0:
            term = term * lam / k
        cdf = cdf + term
    out = 1.0 - cdf
    return float(out) if out.ndim == 0 else out


def implied_points(total: float, spread: float) -> tuple[float, float]:
    """(home, away) implied points. nflverse spread_line is positive when home is favored."""
    return (total + spread) / 2.0, (total - spread) / 2.0


def history_window(stats: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    """Everything strictly before (season, week), going back one extra season."""
    s = stats
    mask = ((s["season"] == season) & (s["week"] < week)) | (s["season"] == season - 1)
    return s[mask].copy()


# --------------------------------------------------------------------------------------
# team-game table


def team_games(hist: pd.DataFrame, games: pd.DataFrame, season: int, cfg: Config) -> pd.DataFrame:
    """One row per (game, offense) with usage totals and TDs by position category."""
    keys = ["game_id", "season", "week", "team", "opponent_team"]
    tg = hist.groupby(keys, as_index=False)[
        ["attempts", "carries", "targets", "rushing_tds", "receiving_tds", "passing_tds"]
    ].sum()

    by_pos = hist.groupby(["game_id", "team", "position_group"])[["rushing_tds", "receiving_tds"]].sum()
    by_pos = by_pos.unstack("position_group", fill_value=0.0)
    cat = pd.DataFrame(index=by_pos.index)
    for pos in POSITIONS:
        for kind, col in (("rush", "rushing_tds"), ("rec", "receiving_tds")):
            cat[f"{kind}_{pos}"] = by_pos[(col, pos)] if (col, pos) in by_pos.columns else 0.0
    tg = tg.merge(cat.reset_index(), on=["game_id", "team"], how="left")
    tg[CATEGORIES] = tg[CATEGORIES].fillna(0.0)
    tg["off_td"] = tg["rushing_tds"] + tg["receiving_tds"]

    g = games[["game_id", "home_team", "home_score", "away_score"]]
    tg = tg.merge(g, on="game_id", how="left")
    is_home = tg["team"] == tg["home_team"]
    tg["points_for"] = np.where(is_home, tg["home_score"], tg["away_score"])
    tg["points_against"] = np.where(is_home, tg["away_score"], tg["home_score"])
    tg = tg.drop(columns=["home_team", "home_score", "away_score"])

    tg["gkey"] = tg["season"] * 100 + tg["week"]
    season_w = np.where(tg["season"] < season, cfg.prior_season_weight, 1.0)
    off_age = tg.groupby("team")["gkey"].rank(ascending=False, method="first") - 1
    def_age = tg.groupby("opponent_team")["gkey"].rank(ascending=False, method="first") - 1
    tg["w_off"] = _decay(off_age, cfg.half_life_games) * season_w
    tg["w_off_usage"] = _decay(off_age, cfg.usage_half_life_games) * season_w
    tg["w_def"] = _decay(def_age, cfg.half_life_games) * season_w
    return tg


# --------------------------------------------------------------------------------------
# league / team / defense profiles


def league_profile(tg: pd.DataFrame) -> dict:
    scored = tg.dropna(subset=["points_for"])
    lg = {c: tg[c].mean() for c in CATEGORIES}
    lg["off_td"] = tg["off_td"].mean()
    lg["rush_td"] = tg["rushing_tds"].mean()
    lg["pass_td"] = tg["receiving_tds"].mean()
    lg["td_per_point"] = scored["off_td"].sum() / max(scored["points_for"].sum(), 1.0)
    lg["points"] = scored["points_for"].mean()
    return lg


def offense_profile(tg: pd.DataFrame, lg: dict, cfg: Config) -> pd.DataFrame:
    s = _wsum(tg.dropna(subset=["points_for"]), "team", ["points_for", "points_against"], "w_off")
    t = _wsum(tg, "team", ["rushing_tds", "off_td"], "w_off")
    k = cfg.offense_prior_games
    prof = pd.DataFrame(index=t.index)
    prof["rush_frac"] = (t["rushing_tds"] + k * lg["rush_td"]) / (t["off_td"] + k * lg["off_td"])
    prof["pts_for_pg"] = s["points_for"] / s["_w"]
    prof["pts_against_pg"] = s["points_against"] / s["_w"]
    return prof


def defense_profile(tg: pd.DataFrame, lg: dict, cfg: Config) -> pd.DataFrame:
    """Matchup multipliers per TD category, plus readable 'allowed per game' numbers."""
    d = tg.rename(columns={"opponent_team": "defense"})
    d["pass_td"] = d["receiving_tds"]
    cols = CATEGORIES + ["pass_td", "off_td"]
    t = _wsum(d, "defense", cols, "w_def")
    k = cfg.defense_prior_games
    lo, hi = cfg.matchup_clip
    prof = pd.DataFrame(index=t.index)
    denom = t["off_td"] + k * lg["off_td"]
    for c in CATEGORIES + ["pass_td"]:
        lg_c = lg[c] if c in lg else lg["pass_td"]
        share = (t[c] + k * lg_c) / denom
        league_share = lg_c / lg["off_td"] if lg_c > 0 else np.nan
        mult = (share / league_share).clip(lo, hi) ** cfg.matchup_weight if lg_c > 0 else 1.0
        prof[f"mult_{c}"] = mult
    # readable per-game "TDs allowed" figures and ranks (1 = most generous defense)
    for pos in ["RB", "WR", "TE"]:
        prof[f"allowed_{pos}_pg"] = (t[f"rush_{pos}"] + t[f"rec_{pos}"]) / t["_w"]
        prof[f"rank_{pos}"] = prof[f"allowed_{pos}_pg"].rank(ascending=False, method="min").astype(int)
    prof["allowed_passtd_pg"] = t["pass_td"] / t["_w"]
    prof["rank_QB"] = prof["allowed_passtd_pg"].rank(ascending=False, method="min").astype(int)
    prof["allowed_rushtd_RB_pg"] = t["rush_RB"] / t["_w"]
    return prof


def player_profile(hist: pd.DataFrame, tg: pd.DataFrame, season: int, cfg: Config) -> pd.DataFrame:
    team_cols = ["attempts", "carries", "targets", "rushing_tds", "receiving_tds", "passing_tds"]
    p = hist.merge(
        tg[["game_id", "team", "gkey"] + team_cols].rename(columns={c: f"team_{c}" for c in team_cols}),
        on=["game_id", "team"], how="left",
    )
    season_w = np.where(p["season"] < season, cfg.prior_season_weight, 1.0)
    age = p.groupby("player_id")["gkey"].rank(ascending=False, method="first") - 1
    p["w"] = _decay(age, cfg.half_life_games) * season_w
    p["wu"] = _decay(age, cfg.usage_half_life_games) * season_w

    def wsum(col, w):
        return (p[col] * p[w]).groupby(p["player_id"]).sum()

    wu = p.groupby("player_id")["wu"].sum()
    prof = pd.DataFrame(index=wu.index)
    carry_share = wsum("carries", "wu") / wsum("team_carries", "wu").replace(0, np.nan)
    target_share = wsum("targets", "wu") / wsum("team_targets", "wu").replace(0, np.nan)
    att_share = wsum("attempts", "wu") / wsum("team_attempts", "wu").replace(0, np.nan)
    prof["carry_share"] = carry_share.fillna(0.0)
    prof["target_share"] = target_share.fillna(0.0)
    prof["att_share"] = att_share.fillna(0.0)
    prof["carries_pg"] = wsum("carries", "wu") / wu
    prof["targets_pg"] = wsum("targets", "wu") / wu
    prof["attempts_pg"] = wsum("attempts", "wu") / wu

    k = cfg.td_share_prior
    prof["rush_td_share"] = (wsum("rushing_tds", "w") + k * prof["carry_share"]) / (wsum("team_rushing_tds", "w") + k)
    prof["rec_td_share"] = (wsum("receiving_tds", "w") + k * prof["target_share"]) / (wsum("team_receiving_tds", "w") + k)
    prof["pass_td_share"] = (wsum("passing_tds", "w") + k * prof["att_share"]) / (wsum("team_passing_tds", "w") + k)

    last = p.sort_values("gkey").groupby("player_id").tail(1).set_index("player_id")
    prof["name"] = last["player_display_name"]
    prof["pos"] = last["position_group"]
    prof["team"] = last["team"]
    prof["last_gkey"] = last["gkey"]
    prof["games"] = p.groupby("player_id").size()
    prof["tds_last_season_plus_ytd"] = (p["rushing_tds"] + p["receiving_tds"]).groupby(p["player_id"]).sum()
    return prof


# --------------------------------------------------------------------------------------
# weekly projection


def slate(games: pd.DataFrame, season: int, week: int, only_unplayed: bool = False) -> pd.DataFrame:
    g = games[(games["season"] == season) & (games["week"] == week)].copy()
    if only_unplayed:
        g = g[g["home_score"].isna()]
    home_pts, away_pts = implied_points(g["total_line"], g["spread_line"])
    rows = []
    for (_, r), hp, ap in zip(g.iterrows(), home_pts, away_pts):
        sides = ((r.home_team, r.away_team, hp, True, r.home_qb_id), (r.away_team, r.home_team, ap, False, r.away_qb_id))
        for team, opp, pts, is_home, qb_id in sides:
            rows.append({
                "game_id": r.game_id, "gameday": r.gameday, "gametime": r.gametime,
                "team": team, "opp": opp, "home": is_home,
                "total": r.total_line, "spread": r.spread_line if is_home else -r.spread_line,
                "implied_pts": pts, "starting_qb_id": qb_id,
            })
    return pd.DataFrame(rows)


def project_week(stats: pd.DataFrame, games: pd.DataFrame, season: int, week: int,
                 cfg: Config | None = None, only_unplayed: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (player projections, game/team environment)."""
    cfg = cfg or Config()
    hist = history_window(stats, season, week)
    tg = team_games(hist, games, season, cfg)
    lg = league_profile(tg)
    off = offense_profile(tg, lg, cfg)
    dfn = defense_profile(tg, lg, cfg)
    ply = player_profile(hist, tg, season, cfg)

    env = slate(games, season, week, only_unplayed)
    if env.empty:
        raise ValueError(f"No (unplayed) games found for {season} week {week}")
    if not cfg.use_vegas:
        env["implied_pts"] = np.nan
    # No Vegas line yet -> fall back to recent scoring of both sides.
    fallback = (env["team"].map(off["pts_for_pg"]) + env["opp"].map(off["pts_against_pg"])) / 2
    env["line_source"] = np.where(env["implied_pts"].isna(), "form", "vegas")
    env["implied_pts"] = env["implied_pts"].fillna(fallback).fillna(lg["points"])
    env["exp_off_tds"] = env["implied_pts"] * lg["td_per_point"]
    env["rush_frac"] = env["team"].map(off["rush_frac"]).fillna(lg["rush_td"] / lg["off_td"])
    env["shootout"] = env["total"] >= cfg.shootout_total

    # Only players who were part of their team's last two games count as active.
    recent = tg.sort_values("gkey").groupby("team")["gkey"].apply(lambda s: s.iloc[-2] if len(s) > 1 else s.iloc[-1])
    ply = ply[ply["team"].isin(env["team"])]
    ply = ply[ply["last_gkey"] >= ply["team"].map(recent)]
    usage_ok = (
        ((ply["pos"] == "QB") & (ply["attempts_pg"] >= cfg.min_attempts_qb))
        | ((ply["pos"] == "RB") & (ply["carries_pg"] + ply["targets_pg"] >= cfg.min_touches_rb))
        | ((ply["pos"] == "WR") & (ply["targets_pg"] >= cfg.min_targets_wr))
        | ((ply["pos"] == "TE") & (ply["targets_pg"] >= cfg.min_targets_te))
    )
    ply = ply[usage_ok].reset_index()

    # One QB per team: the listed starter if the schedule names one, else the recent attempts leader.
    starters = env.set_index("team")["starting_qb_id"]
    is_qb = ply["pos"] == "QB"
    listed = ply["team"].map(starters)
    keep_qb = np.where(listed.isin(ply["player_id"]), ply["player_id"] == listed, False)
    leader = ply[is_qb].sort_values("attempts_pg").groupby("team").tail(1)["player_id"]
    no_listing = ~listed.isin(ply.loc[is_qb, "player_id"])
    keep_qb = keep_qb | (no_listing & ply["player_id"].isin(leader))
    ply = ply[~is_qb | keep_qb].reset_index(drop=True)

    out = ply.merge(env, on="team", how="left")
    d = dfn.reindex(out["opp"])
    rush_m = np.array([d[f"mult_rush_{p}"].iloc[i] for i, p in enumerate(out["pos"])], dtype=float)
    rec_m = np.array([d[f"mult_rec_{p}"].iloc[i] for i, p in enumerate(out["pos"])], dtype=float)
    rush_m = np.nan_to_num(rush_m, nan=1.0)
    rec_m = np.nan_to_num(rec_m, nan=1.0)
    pass_m = d["mult_pass_td"].fillna(1.0).to_numpy()

    T = out["exp_off_tds"].to_numpy()
    rf = out["rush_frac"].to_numpy()
    out["lam_rush"] = T * rf * out["rush_td_share"] * rush_m
    out["lam_rec"] = T * (1 - rf) * out["rec_td_share"] * rec_m
    cal = dict(cfg.calibration)
    pos_cal = out["pos"].map(cal).fillna(1.0)
    out["lam_rush"] *= pos_cal
    out["lam_rec"] *= pos_cal
    out["lam_td"] = out["lam_rush"] + out["lam_rec"]
    out["p_anytime_td"] = 1 - np.exp(-out["lam_td"])
    neutral = out["lam_rush"] / rush_m + out["lam_rec"] / rec_m  # lambda with an average defense
    out["matchup_mult"] = (out["lam_td"] / neutral.replace(0, np.nan)).fillna(1.0)

    is_qb = out["pos"] == "QB"
    out["lam_pass_td"] = np.where(
        is_qb, T * (1 - rf) * cfg.starter_pass_share * pass_m * cal.get("QB_pass", 1.0), np.nan)
    for line in (0.5, 1.5, 2.5):
        out[f"p_pass_over_{line}"] = np.where(is_qb, poisson_sf(out["lam_pass_td"].fillna(0), line), np.nan)
    out["pass_matchup_mult"] = np.where(is_qb, pass_m, np.nan)

    rank_col = {p: f"rank_{p}" for p in POSITIONS}
    out["def_rank_vs_pos"] = [
        dfn.at[o, rank_col[p]] if o in dfn.index else np.nan for o, p in zip(out["opp"], out["pos"])
    ]
    env = env.merge(
        dfn[["allowed_RB_pg", "allowed_WR_pg", "allowed_TE_pg", "allowed_passtd_pg"]],
        left_on="opp", right_index=True, how="left",
    )
    return out, env
