"""The ranking formula.

    Projected points (one game) = Player Rating x Game Multiplier

    Player Rating   = what the player scores in a neutral game, from a ridge
                      regression on recent form, last season, usage and
                      red-zone opportunity (fit per position).
    Game Multiplier = exp(b0 + b1*ln(implied team total / league avg)
                           + b2*ln(defense factor) + b3*home + b4*dome
                           + b5*spread/7)
    Defense factor  = points a defense allows to a position relative to what
                      those same players were rated to score (opponent-
                      adjusted, shrunk toward 1.0 early in the season).

Rest-of-season value = sum over remaining games of
    P(plays that game) x Player Rating x Game Multiplier.
"""
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from sklearn.linear_model import Ridge

USAGE_BY_POS = {
    "QB": ["attempts", "passing_yards", "passing_tds", "passing_interceptions", "carries",
           "rushing_yards", "rz_carries", "gl_carries"],
    "RB": ["carries", "rushing_yards", "targets", "receptions", "receiving_yards",
           "rz_carries", "gl_carries", "rz_targets", "skill_tds"],
    "WR": ["targets", "receptions", "receiving_yards", "target_share", "air_yards_share",
           "rz_targets", "i10_targets", "skill_tds", "carries"],
    "TE": ["targets", "receptions", "receiving_yards", "target_share", "air_yards_share",
           "rz_targets", "i10_targets", "skill_tds"],
}
TD_USAGE = {
    "QB": ["passing_tds", "attempts", "rz_carries", "gl_carries", "carries"],
    "RB": ["rz_carries", "gl_carries", "rz_targets", "carries", "targets", "skill_tds"],
    "WR": ["rz_targets", "i10_targets", "targets", "skill_tds", "air_yards_share"],
    "TE": ["rz_targets", "i10_targets", "targets", "skill_tds"],
}
CONTEXT_TERMS = ["ln_itt", "ln_def", "home", "dome", "spread7"]
ROLE_TERMS = ["u_snap", "no_snap", "depth1", "depth3p", "depth_na", "new_team", "returning", "rep_quest"]
TRANSIENT = ["returning", "rep_quest"]  # describe the next game only, not the rest of the season
AVAIL_FLAGS = ["res_inj", "res_dtr", "res_other", "pup", "ps", "cut", "rep_out", "rep_doubt", "rep_quest",
               "prac_dnp", "prac_lim", "depth1", "depth3p", "depth_na", "returning"]


def rating_matrix(df, pos, kind="pts", use_usage=True, use_history=True, use_role=True):
    """Design matrix for the player rating regression."""
    X = pd.DataFrame(index=df.index)
    has_hist = df.ewm_pts_l.notna()
    if kind == "pts":
        if use_history:
            X["ewm_pts_s"] = df.ewm_pts_s.fillna(0)
            X["ewm_pts_l"] = df.ewm_pts_l.fillna(0)
            X["szn_pts"] = df.szn_pts.fillna(df.ewm_pts_l).fillna(0)
            X["prev_pts"] = df.prev_pts.fillna(df.ewm_pts_l).fillna(0)
        usage = USAGE_BY_POS[pos] if use_usage else []
    else:
        X["td_ewm"] = df[f"u_{'tds' if pos == 'QB' else 'skill_tds'}"].fillna(0)
        usage = TD_USAGE[pos]
    for c in usage:
        X[f"u_{c}"] = df[f"u_{c}"].fillna(0)
    X["no_hist"] = (~has_hist).astype(float)
    X["no_prev"] = df.prev_pts.isna().astype(float)
    X["szn_g"] = np.log1p(df.szn_g)
    X["career_g"] = np.log1p(df.career_g)
    X["age"] = df.age - 26
    X["age2"] = (df.age - 26) ** 2
    X["rookie_pick"] = df.rookie * (np.log(300) - df.log_pick)
    X["miss_rate8"] = df.miss_rate8
    if use_role:
        X["u_snap"] = df.u_snap.fillna(0)
        X["no_snap"] = df.u_snap.isna().astype(float)
        for c in ROLE_TERMS[2:]:
            X[c] = df[c].fillna(0).astype(float)
    return X


class Projector:
    def __init__(self, positions=("QB", "RB", "WR", "TE"), alpha=10.0, def_halflife=8.0,
                 def_prior=3.0, def_season_carry=0.4, terms=CONTEXT_TERMS,
                 use_usage=True, use_history=True, use_role=True, use_status=True):
        self.positions = positions
        self.alpha = alpha
        self.def_halflife = def_halflife
        self.def_prior = def_prior
        self.def_season_carry = def_season_carry
        self.terms = list(terms)
        self.use_usage = use_usage
        self.use_history = use_history
        self.use_role = use_role
        self.use_status = use_status
        self.rating_models, self.td_models, self.context, self.td_context = {}, {}, {}, {}
        self.avail = {}

    # ---------- stage A: player rating ----------
    def _fit_ridge(self, df, pos, kind):
        X = rating_matrix(df, pos, kind, self.use_usage, self.use_history, self.use_role)
        y = df.pts if kind == "pts" else (df.tds if pos == "QB" else df.skill_tds)
        m = Ridge(alpha=self.alpha).fit(X, y)
        m.feature_names = list(X.columns)
        return m

    def rating(self, df, kind="pts"):
        out = pd.Series(np.nan, index=df.index)
        models = self.rating_models if kind == "pts" else self.td_models
        for pos in self.positions:
            idx = df.position == pos
            if idx.any():
                X = rating_matrix(df[idx], pos, kind, self.use_usage, self.use_history, self.use_role)
                out[idx] = models[pos].predict(X)
        floor = 0.3 if kind == "pts" else 0.005
        return out.clip(lower=floor)

    # ---------- defense factor (strength of schedule) ----------
    def defense_factors(self, df, schedule):
        """Opponent-adjusted points-allowed factor per (defense, position) before each game.

        Built on the full schedule so future games carry the latest estimate.
        """
        played = df[(df.played == 1)]
        agg = (played.assign(rating=self.rating(played))
               .groupby(["season", "week", "opp", "position"])
               .agg(actual=("pts", "sum"), rated=("rating", "sum")))
        sk = schedule[schedule.season.between(df.season.min(), df.season.max())]
        sk = sk[["season", "week", "team", "completed"]].rename(columns={"team": "opp"})
        sk = sk.merge(pd.DataFrame({"position": list(self.positions)}), how="cross")
        sk = sk.join(agg, on=["season", "week", "opp", "position"]).fillna({"actual": 0.0, "rated": 0.0})
        sk = sk.sort_values(["opp", "position", "season", "week"])
        decay = 0.5 ** (1 / self.def_halflife)
        res = []
        for (team, pos), g in sk.groupby(["opp", "position"], sort=False):
            a_sum = r_sum = 0.0
            done = g.completed.values & (g.rated.values > 0)
            prior = self.def_prior * max(g.rated.values[done].mean() if done.any() else 1.0, 1e-6)
            last_season = None
            vals = np.empty(len(g))
            for i, (season, a, r, ok) in enumerate(zip(g.season.values, g.actual.values, g.rated.values, done)):
                if last_season is not None and season != last_season:
                    a_sum *= self.def_season_carry
                    r_sum *= self.def_season_carry
                vals[i] = (a_sum + prior) / (r_sum + prior)
                if ok:
                    a_sum = a_sum * decay + a
                    r_sum = r_sum * decay + r
                last_season = season
            res.append(g[["season", "week", "opp", "position"]].assign(def_factor=vals))
        return pd.concat(res, ignore_index=True)

    def defense_as_of(self, season, week):
        """Each defense's factor using only games before `week` (for ROS projections)."""
        t = self.def_table
        t = t[(t.season == season) & (t.week >= week)].sort_values("week")
        return t.groupby(["opp", "position"]).def_factor.first()

    # ---------- stage B: game multiplier ----------
    @staticmethod
    def context_frame(df):
        itt_avg = df.groupby("season").itt.transform("mean")
        return pd.DataFrame({
            "ln_itt": np.log((df.itt / itt_avg).fillna(1.0).clip(0.4, 2.0)),
            "ln_def": np.log(df.def_factor.fillna(1.0).clip(0.5, 2.0)),
            "home": df.home.fillna(0.5) - 0.5,
            "dome": df.dome.fillna(0) - 0.25,
            "spread7": (df.spread.fillna(0) / 7).clip(-3, 3),
        }, index=df.index)

    def _fit_context(self, y, base, C):
        cols = [t for t in CONTEXT_TERMS if t in self.terms]
        Xc = C[cols].values

        def resid(b):
            return base * np.exp(b[0] + Xc @ b[1:]) - y
        sol = least_squares(resid, np.zeros(1 + len(cols)), loss="soft_l1", f_scale=8.0)
        coef = dict(zip(["intercept"] + cols, sol.x))
        return coef

    def multiplier(self, C, coef):
        z = np.full(len(C), coef["intercept"])
        for t, b in coef.items():
            if t != "intercept":
                z = z + b * C[t].values
        return np.exp(z)

    # ---------- availability ----------
    HORIZONS = [0, 1, 2, 3, 5, 7, 10, 13, 16]

    def _avail_matrix(self, d, k, pos):
        """Features for P(plays the game k team-games ahead) from a frame of pre-game rows."""
        streak = d.miss_streak.values.astype(float)
        lk = np.log1p(np.asarray(k, float))
        cols = {
            "s1": streak == 1, "s2": streak == 2, "s3": (streak >= 3) & (streak < 6), "s6": streak >= 6,
            "lk": lk, "miss_rate8": d.miss_rate8.values.astype(float),
            "played_last": d.played_last.values.astype(float), "ln_rating": np.log(d.rating.values.astype(float)),
        }
        for c in ("s1", "s2", "s3", "s6"):
            cols[f"{c}_lk"] = cols[c] * lk
        cols["mr_lk"] = cols["miss_rate8"] * lk
        if pos == "QB":  # starters throw; backups who mopped up don't keep playing
            att = d.u_attempts.fillna(0).values.astype(float)
            cols["att"] = np.minimum(att, 40) / 10
            cols["att_lk"] = cols["att"] * lk
        if self.use_status:  # roster designation, injury report, practice and depth chart this week
            for c in AVAIL_FLAGS:
                v = d[c].fillna(0).values.astype(float)
                cols[c] = v
                cols[f"{c}_lk"] = v * lk
        return np.column_stack([np.asarray(v, float) for v in cols.values()])

    def _fit_availability(self, df):
        """P(player plays the game k team-games ahead), logistic per position.

        (A gradient-boosted version was tested and did no better out of sample.)
        """
        from sklearn.linear_model import LogisticRegression
        d = df[df.completed].sort_values(["player_id", "season", "week"]).copy()
        d["rating"] = self.rating(d)
        g = d.groupby(["player_id", "season"]).played
        for pos in self.positions:
            X, y = [], []
            m = (d.position == pos).values
            sub = d[m]
            for k in self.HORIZONS:
                fut = g.shift(-k)[m]
                ok = fut.notna().values
                X.append(self._avail_matrix(sub[ok], np.full(ok.sum(), k), pos))
                y.append(fut.values[ok])
            self.avail[pos] = LogisticRegression(C=1.0, max_iter=3000).fit(np.vstack(X), np.concatenate(y))

    def availability(self, pos, d, k):
        """P(plays) for rows d (one per player, pre-game features of the next game) k games ahead."""
        return self.avail[pos].predict_proba(self._avail_matrix(d, k, pos))[:, 1]

    # ---------- fit / predict ----------
    def fit(self, train, full, schedule):
        """train: rows used to fit; full: all rows up to the test point (for defense factors)."""
        tr = train[(train.played == 1)]
        for pos in self.positions:
            sub = tr[tr.position == pos]
            self.rating_models[pos] = self._fit_ridge(sub, pos, "pts")
            self.td_models[pos] = self._fit_ridge(sub, pos, "td")
        self.def_table = self.defense_factors(full, schedule)
        tr = self.attach_def(tr)
        C = self.context_frame(tr)
        base = self.rating(tr)
        td_base = self.rating(tr, "td")
        for pos in self.positions:
            m = (tr.position == pos).values
            self.context[pos] = self._fit_context(tr.pts.values[m], base.values[m], C[m])
            ytd = (tr.tds if pos == "QB" else tr.skill_tds).values[m]
            td_terms = self.terms
            self.terms = [t for t in td_terms if t in ("ln_itt", "ln_def", "home")]
            self.td_context[pos] = self._fit_context(ytd, td_base.values[m], C[m])
            self.terms = td_terms
        self._fit_availability(train)
        return self

    def attach_def(self, df):
        out = df.drop(columns=[c for c in ["def_factor"] if c in df.columns])
        return out.merge(self.def_table, on=["season", "week", "opp", "position"], how="left") \
                  .set_axis(df.index)

    def predict_games(self, df):
        """Per-game projection assuming the player plays (used for weekly start/sit)."""
        df = self.attach_def(df)
        C = self.context_frame(df)
        base, td_base = self.rating(df), self.rating(df, "td")
        proj = pd.Series(np.nan, index=df.index)
        proj_td = pd.Series(np.nan, index=df.index)
        for pos in self.positions:
            m = (df.position == pos).values
            if m.any():
                proj[m] = base.values[m] * self.multiplier(C[m], self.context[pos])
                proj_td[m] = td_base.values[m] * self.multiplier(C[m], self.td_context[pos])
        return df.assign(rating=base, proj=proj, proj_td=proj_td)

    def formula(self):
        """Human-readable coefficients."""
        rows = []
        for pos in self.positions:
            m = self.rating_models[pos]
            for f, c in zip(m.feature_names, m.coef_):
                rows.append(("rating", pos, f, c))
            rows.append(("rating", pos, "intercept", m.intercept_))
            for t, c in self.context[pos].items():
                rows.append(("multiplier", pos, t, c))
        return pd.DataFrame(rows, columns=["part", "position", "term", "coef"])
