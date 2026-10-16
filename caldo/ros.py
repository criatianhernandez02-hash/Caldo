"""Rest-of-season projections: the number the trade calculator runs on."""
import numpy as np
import pandas as pd


def team_itt_model(tg, season, week, alpha=4.0, prev_weight=0.35, hl_weeks=6.0):
    """Market-implied team strength from past Vegas lines.

    Fits implied_total = mu + offense[team] + defense[opp] + hfa*home on games
    before `week` (plus last season, down-weighted), so future games without a
    posted line still get an implied total.
    """
    past = tg[((tg.season == season) & (tg.week < week)) | (tg.season == season - 1)]
    past = past[past.itt.notna()]
    teams = sorted(set(tg[tg.season == season].team) | set(past.team))
    ti = {t: i for i, t in enumerate(teams)}
    n, T = len(past), len(teams)
    X = np.zeros((n, 2 * T + 1))
    X[np.arange(n), past.team.map(ti).values] = 1
    X[np.arange(n), T + past.opp.map(ti).values] = 1
    X[:, -1] = past.home.values - 0.5
    weeks_ago = np.where(past.season == season, week - past.week, week + 18 - past.week)
    w = 0.5 ** (weeks_ago / hl_weeks) * np.where(past.season == season, 1.0, prev_weight)
    w = np.maximum(w, 0.02)
    y = past.itt.values
    mu = np.average(y, weights=w)
    W = np.sqrt(w)[:, None]
    pen = np.eye(2 * T + 1) * alpha
    pen[-1, -1] = 1e-3
    beta = np.linalg.solve((X * W).T @ (X * W) + pen, (X * W).T @ (W[:, 0] * (y - mu)))
    off, dfn, hfa = beta[:T], beta[T:2 * T], beta[-1]

    def predict(team, opp, home):
        t = np.array([ti.get(x, -1) for x in team])
        o = np.array([ti.get(x, -1) for x in opp])
        return mu + np.where(t >= 0, off[t], 0) + np.where(o >= 0, dfn[o], 0) + hfa * (np.asarray(home) - 0.5)

    predict.ratings = pd.DataFrame({"team": teams, "off": off, "def": dfn})
    return predict


def project_ros(proj, feat, tg, season, week, last_week=17, live=False):
    """Project every active player's points from `week` through `last_week`.

    In backtest mode, games with week >= `week` are the future. In live mode the
    future is every game not yet completed (so Thursday games already played
    this week are excluded).
    """
    s = feat[feat.season == season]
    future = (~s.completed) if live else (s.week >= week)
    started = s[~future].groupby("player_id").size()
    fut = s[future & (s.week <= last_week) & s.player_id.isin(started.index)].copy()
    fut = fut.sort_values(["player_id", "week"])
    fut["k"] = fut.groupby("player_id").cumcount()

    # snapshot: features at the next game hold everything known today
    snap = fut[fut.k == 0].set_index("player_id")
    rating = proj.rating(snap).rename("rating")
    td_rating = proj.rating(snap, "td").rename("td_rating")
    fut = fut.join(rating, on="player_id").join(td_rating, on="player_id")

    # context known today: posted line for the upcoming week, market ratings beyond
    itt_hat = team_itt_model(tg, season, week)
    est = itt_hat(fut.team.values, fut.opp.values, fut.home.values)
    known_line = fut.itt.notna() & (fut.week == fut.groupby("player_id").week.transform("min"))
    if not live:
        known_line &= fut.week == week
    fut["itt_used"] = np.where(known_line, fut.itt, est)
    est_opp = itt_hat(fut.opp.values, fut.team.values, 1 - fut.home.values)
    fut["spread_used"] = np.where(known_line, fut.spread, est - est_opp)
    dfac = proj.defense_as_of(season, week)
    fut["def_factor"] = [dfac.get((o, p), 1.0) for o, p in zip(fut.opp, fut.position)]

    itt_avg = tg[tg.season == season].itt.mean()
    if np.isnan(itt_avg):
        itt_avg = tg[tg.season == season - 1].itt.mean()
    C = pd.DataFrame({
        "ln_itt": np.log((fut.itt_used / itt_avg).clip(0.4, 2.0)),
        "ln_def": np.log(fut.def_factor.clip(0.5, 2.0)),
        "home": fut.home.fillna(0.5) - 0.5,
        "dome": fut.dome.fillna(0) - 0.25,
        "spread7": (fut.spread_used / 7).clip(-3, 3),
    }, index=fut.index)
    fut["mult"] = np.nan
    fut["td_mult"] = np.nan
    fut["sched_mult"] = np.nan  # matchup + venue only, for a schedule-ease readout
    for pos in proj.positions:
        m = (fut.position == pos).values
        if not m.any():
            continue
        coef = proj.context[pos]
        fut.loc[m, "mult"] = proj.multiplier(C[m], coef)
        fut.loc[m, "td_mult"] = proj.multiplier(C[m], proj.td_context[pos])
        sched = {"intercept": 0.0, **{t: coef.get(t, 0.0) for t in ("ln_def", "home", "dome")}}
        fut.loc[m, "sched_mult"] = proj.multiplier(C[m][[c for c in sched if c != "intercept"]], sched)
        sn = snap.loc[fut.player_id[m]]
        fut.loc[m, "p_play"] = proj.availability(pos, sn.miss_streak.values, sn.miss_rate8.values,
                                                 sn.played_last.values, fut.rating[m].values,
                                                 sn.u_attempts.fillna(0).values, fut.k[m].values)

    fut["xpts"] = fut.p_play * fut.rating * fut.mult
    fut["xtd"] = fut.p_play * fut.td_rating * fut.td_mult
    fut["proj_if_plays"] = fut.rating * fut.mult
    out = fut.groupby("player_id").agg(
        name=("player_display_name", "first"), position=("position", "first"),
        team=("team", "last"), ros_pts=("xpts", "sum"), ros_td=("xtd", "sum"),
        games_left=("k", "size"), exp_games=("p_play", "sum"),
        sched_ease=("sched_mult", "mean"), actual_ros=("pts", "sum"),
        actual_games=("played", "sum"),
        next_opp=("opp", "first"), next_proj=("proj_if_plays", "first"))
    out["rating"] = rating
    out["ros_ppg"] = out.ros_pts / out.exp_games.clip(lower=0.5)
    out["szn_pts"] = snap.szn_pts
    out["szn_g"] = snap.szn_g
    out["prev_pts"] = snap.prev_pts
    out["miss_streak"] = snap.miss_streak
    out["season"], out["week"] = season, week
    # weekly detail for lineup math in the trade calculator
    weekly = fut[["player_id", "week", "opp", "home", "xpts", "proj_if_plays", "p_play"]]
    return out.reset_index(), weekly
