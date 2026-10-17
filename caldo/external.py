"""Outside projections: head-to-head scoring, blind-spot analysis, and a learned blend.

Sleeper's in-app projections (Rotowire) are available for every week since
2018 as they stood before kickoff, so they can be scored exactly like our own
walk-forward projections. The blend weights are learned walk-forward too: each
season's weights come only from earlier seasons.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression, LogisticRegression

from . import sleeper
from .config import RAW_DIR

POOL = {"QB": 24, "RB": 36, "WR": 48, "TE": 18}


def load_sleeper_projections():
    sp = pd.read_parquet(RAW_DIR / "ext" / "sleeper_proj.parquet")
    ids = sleeper.id_map()
    rev = {v: k for k, v in ids.items() if k != "_by_name"}
    sp["player_id"] = sp.sid.map(rev)
    by_name = ids["_by_name"]
    miss = sp.player_id.isna()
    sp.loc[miss, "player_id"] = [rev.get(by_name.get((sleeper._norm(n), p))) for n, p in zip(sp.name[miss], sp.pos[miss])]
    return sp.dropna(subset=["player_id"]).drop_duplicates(["season", "week", "player_id"])


def _rank_corr(d, col, n):
    vals = []
    for _, g in d.groupby(["season", "week"]):
        top = g[g[col].rank(ascending=False) <= n]
        if len(top) > 5:
            vals.append(spearmanr(top[col], top.pts).statistic)
    return np.nanmean(vals)


def head_to_head(weekly, sp, scoring="ppr", model_col="m_full"):
    """Score our weekly projections against Sleeper's on the same player-games."""
    d = weekly.merge(sp[["season", "week", "player_id", f"sl_{scoring}"]], on=["season", "week", "player_id"])
    d = d.rename(columns={f"sl_{scoring}": "sleeper", model_col: "ours"})
    rows = []
    for pos, n in POOL.items():
        x = d[d.position == pos]
        for m in ["ours", "sleeper", "blend"] if "blend" in d else ["ours", "sleeper"]:
            rows.append({"position": pos, "model": m, "MAE": (x[m] - x.pts).abs().mean(), "rank_corr": _rank_corr(x, m, n),
                         "bias": (x[m] - x.pts).mean(), "n": len(x)})
    return d, pd.DataFrame(rows)


def blind_spots(d, feat):
    """Where each model misses: error by situation (rookies, new team, back from injury, early weeks)."""
    keep = ["player_id", "season", "week", "rookie", "new_team", "returning", "career_g", "szn_g", "depth_eff", "rep_quest", "age"]
    x = d.merge(feat[keep], on=["player_id", "season", "week"], how="left")
    segs = {
        "Rookies": x.rookie == 1,
        "Changed teams this year": x.new_team == 1,
        "First game back from 2+ missed": x.returning == 1,
        "Listed Questionable": x.rep_quest == 1,
        "Weeks 1-3": x.week <= 3,
        "Weeks 4-17": x.week >= 4,
        "Backups (depth 2+)": x.depth_eff >= 2,
        "Starters (depth 1)": x.depth_eff == 1,
        "Age 30+": x.age >= 30,
        "Everyone": x.week > 0,
    }
    rows = []
    for name, m in segs.items():
        s = x[m.fillna(False)]
        for pos in POOL:
            t = s[s.position == pos]
            if len(t) < 150:
                continue
            e_o, e_s = (t.ours - t.pts).abs().mean(), (t.sleeper - t.pts).abs().mean()
            rows.append({"segment": name, "position": pos, "n": len(t), "MAE_ours": e_o, "MAE_sleeper": e_s,
                         "edge": e_s - e_o, "bias_ours": (t.ours - t.pts).mean(), "bias_sleeper": (t.sleeper - t.pts).mean()})
    return pd.DataFrame(rows)


class Blend:
    """pts ~ a*ours + b*sleeper + c, per position, plus situation interactions."""

    TERMS = ["rookie", "new_team", "returning", "early"]

    def __init__(self):
        self.models = {}

    def _X(self, d):
        early = (d.week <= 3).astype(float)
        X = pd.DataFrame({"ours": d.ours, "sleeper": d.sleeper}, index=d.index)
        for t in self.TERMS:
            v = early if t == "early" else d[t].fillna(0).astype(float)
            X[f"ours_{t}"] = d.ours * v
            X[f"sl_{t}"] = d.sleeper * v
        return X

    def fit(self, d):
        for pos in POOL:
            x = d[d.position == pos]
            self.models[pos] = LinearRegression().fit(self._X(x), x.pts)
        return self

    def predict(self, d):
        out = pd.Series(np.nan, index=d.index)
        for pos, m in self.models.items():
            k = d.position == pos
            if k.any():
                out[k] = m.predict(self._X(d[k]))
        return out

    def weights(self):
        return {pos: dict(zip(["ours", "sleeper"], np.round(m.coef_[:2], 3))) for pos, m in self.models.items()}


def walk_forward_blend(d, feat, first_test=2020):
    """Blend each test season using weights fit only on earlier seasons."""
    keep = ["player_id", "season", "week", "rookie", "new_team", "returning"]
    d = d.merge(feat[keep], on=["player_id", "season", "week"], how="left")
    d["blend"] = np.nan
    weights = {}
    for Y in sorted(d.season.unique()):
        if Y < first_test:
            continue
        b = Blend().fit(d[d.season < Y])
        m = d.season == Y
        d.loc[m, "blend"] = b.predict(d[m])
        weights[Y] = b.weights()
    return d[d.blend.notna()], weights


def availability_signal(feat, sp, pr_avail_col="p0"):
    """Is a missing Sleeper projection for a player's game a sign he won't play?

    Returns the historical play rate for established players by whether Sleeper
    projected them that week.
    """
    x = feat[(feat.season >= 2018) & feat.completed & (feat.ewm_pts_l >= 8)][["player_id", "season", "week", "position", "played", "rep_out", "rep_quest", "res_inj", "res_dtr"]]
    teams_proj = sp.groupby(["season", "week"]).size()
    x = x[x.set_index(["season", "week"]).index.isin(teams_proj.index)]
    x = x.merge(sp[["season", "week", "player_id"]].assign(sl_has=1), on=["season", "week", "player_id"], how="left")
    x["sl_has"] = x.sl_has.fillna(0)
    return x.groupby(["sl_has", "rep_out"]).played.agg(["mean", "size"]).round(3)


# ---------------------------------------------------------------------------
# Live blend: our rest-of-season projection + Sleeper's weekly projections
# ---------------------------------------------------------------------------

def common_rank_corr(x, col, n):
    """Rank correlation on the same player pool for every model (top-n by either model)."""
    vals = []
    for _, g in x.groupby(["season", "week"]):
        pool = g[(g.ours.rank(ascending=False) <= n) | (g.sleeper.rank(ascending=False) <= n)]
        if len(pool) > 5:
            vals.append(spearmanr(pool[col], pool.pts).statistic)
    return np.mean(vals)


def fit_blend(d, feat, grid=(0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0), first_test=2020):
    """Choose our weight per position walk-forward; return config + out-of-sample scores.

    Sleeper's points are first rescaled per position (their default scoring
    differs from ours, e.g. QBs come out ~3 points high).
    """
    test_rows, chosen = [], {}
    seasons = sorted(d.season.unique())
    for Y in [y for y in seasons if y >= first_test] + [max(seasons) + 1]:
        tr, te = d[d.season < Y], d[d.season == Y]
        cfg = {}
        for pos, n in POOL.items():
            t = tr[tr.position == pos]
            scale = t.pts.sum() / t.sleeper.sum()
            best = max(grid, key=lambda w: common_rank_corr(t.assign(b=w * t.ours + (1 - w) * t.sleeper * scale), "b", n))
            cfg[pos] = {"w_ours": best, "sleeper_scale": round(float(scale), 4)}
        chosen[int(Y)] = cfg
        if len(te):
            for pos, n in POOL.items():
                x = te[te.position == pos].copy()
                c = cfg[pos]
                x["sleeper_adj"] = x.sleeper * c["sleeper_scale"]
                x["blend"] = c["w_ours"] * x.ours + (1 - c["w_ours"]) * x.sleeper_adj
                for m in ["ours", "sleeper_adj", "blend"]:
                    test_rows.append({"season": Y, "position": pos, "model": m.replace("_adj", ""),
                                      "MAE": (x[m] - x.pts).abs().mean(), "rank_corr": common_rank_corr(x, m, n), "n": len(x)})
    scores = pd.DataFrame(test_rows).groupby(["position", "model"]).agg(MAE=("MAE", "mean"), rank_corr=("rank_corr", "mean"), n=("n", "sum")).reset_index()
    return chosen[max(chosen)], scores, chosen


def availability_rates(feat, sp, first=2018):
    """Historical play rates used to read Sleeper's projections as an availability signal."""
    x = feat[(feat.season >= first) & feat.completed & (feat.ewm_pts_l >= 8)]
    x = x[x.set_index(["season", "week"]).index.isin(sp.set_index(["season", "week"]).index.unique())]
    x = x.merge(sp[["season", "week", "player_id", "sl_ppr"]], on=["season", "week", "player_id"], how="left")
    has = x.sl_ppr.fillna(0) > 0.3
    healthy = feat[(feat.season >= first) & feat.completed & (feat.ewm_pts_l >= 8) & (feat.played == 1)].sort_values(["player_id", "season", "week"])
    g = healthy.groupby(["player_id", "season"]).played
    full = feat[(feat.season >= first) & feat.completed].sort_values(["player_id", "season", "week"])
    gf = full.groupby(["player_id", "season"]).played
    curve = {}
    played_now = (full.played == 1) & (full.ewm_pts_l >= 8)
    for k in range(1, 13):
        fut = gf.shift(-k)[played_now]
        curve[k] = round(float(fut.mean()), 4)
    return {"present": round(float(x[has].played.mean()), 4), "absent": round(float(x[~has & (x.rep_out == 0)].played.mean()), 4),
            "absent_n": int((~has).sum()), "present_n": int(has.sum()), "healthy_curve": curve}


def blend_weekly(weekly, sp_now, cfg, rates, scoring_col="sl_ppr", sid_known=None):
    """Blend a live per-week projection table with Sleeper's current weekly projections.

    weekly: rows from project_ros (player_id, position, week, k, proj_if_plays, p_play).
    Per game we mix the points-if-he-plays; for availability, Sleeper publishing a
    projection for the next game is a strong signal (players they project play
    ~99% of the time, those they leave out ~15%), and for later weeks their
    projection is averaged with our own estimate.
    """
    w = weekly.merge(sp_now[["player_id", "week", scoring_col]].rename(columns={scoring_col: "sl"}), on=["player_id", "week"], how="left")
    covered = set(sp_now.week.unique())
    tracked = w.player_id.isin(sid_known) if sid_known is not None else pd.Series(True, index=w.index)
    scale = w.position.map({p: c["sleeper_scale"] for p, c in cfg.items()})
    wo = w.position.map({p: c["w_ours"] for p, c in cfg.items()})
    has = w.sl.fillna(0) > 0.3
    use = tracked & w.week.isin(covered)
    w["if_plays"] = np.where(use & has, wo * w.proj_if_plays + (1 - wo) * w.sl * scale, w.proj_if_plays)
    curve = rates["healthy_curve"]
    sl_p = np.where(has, [curve.get(int(k), curve[max(curve)]) if k > 0 else rates["present"] for k in w.k], rates["absent"])
    p_next = np.where(has, np.maximum(w.p_play, rates["present"]), np.minimum(w.p_play, rates["absent"]))
    p_later = 0.5 * w.p_play + 0.5 * sl_p
    w["p_blend"] = np.where(use, np.where(w.k == 0, p_next, p_later), w.p_play)
    w["xpts_blend"] = w.p_blend * w.if_plays
    w["xtd_blend"] = w.xtd * np.where(w.p_play > 0, w.p_blend / w.p_play.clip(lower=1e-6), 1)
    return w
