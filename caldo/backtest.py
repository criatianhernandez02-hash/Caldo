"""Walk-forward backtest: for each test season, fit only on earlier seasons."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .config import CACHE_DIR, FANTASY_LAST_WEEK, League
from .data import build_panel
from .features import add_features
from .model import CONTEXT_TERMS, Projector, rating_matrix
from .ros import project_ros

POOL = {"QB": 24, "RB": 48, "WR": 60, "TE": 24}       # players a manager would consider
WEEKLY_POOL = {"QB": 24, "RB": 36, "WR": 48, "TE": 18}
TRAIN_START = 2012
DECISION_WEEKS = [3, 5, 7, 9, 11]

VARIANTS = {
    "full": {},
    "no_matchup": {"terms": [t for t in CONTEXT_TERMS if t != "ln_def"]},
    "no_vegas": {"terms": [t for t in CONTEXT_TERMS if t not in ("ln_itt", "spread7")]},
    "no_home_dome": {"terms": [t for t in CONTEXT_TERMS if t not in ("home", "dome")]},
    "no_context": {"terms": []},
    "no_usage": {"use_usage": False},
}


def load_features(last_season, scoring="ppr", refresh=False):
    cache = CACHE_DIR / f"features_{last_season}_{scoring}.parquet"
    if cache.exists() and not refresh:
        return pd.read_parquet(cache), build_panel(last_season)[1]
    panel, tg = build_panel(last_season, use_cache=not refresh)
    feat = add_features(panel, scoring)
    feat.to_parquet(cache)
    return feat, tg


def naive_ppg(df):
    """What most people rank by: this season's average, else last season's."""
    return df.szn_pts.where(df.szn_g >= 1).fillna(df.prev_pts).fillna(df.ewm_pts_l).fillna(0)


def _rank_corr(d, pred, actual, n_by_pos, group):
    out = {}
    for pos, n in n_by_pos.items():
        vals = []
        for _, g in d[d.position == pos].groupby(group):
            pool = g[(g[pred].rank(ascending=False) <= n) | (g["_base"].rank(ascending=False) <= n)]
            if len(pool) > 5:
                vals.append(spearmanr(pool[pred], pool[actual]).statistic)
        out[pos] = np.nanmean(vals)
    return out


def run(feat, tg, seasons, variants=("full",), weeks=DECISION_WEEKS, lgbm=True):
    """Fit each variant once per test season; score weekly games and ROS snapshots."""
    weekly, ros = [], []
    for Y in seasons:
        train = feat[(feat.season >= TRAIN_START) & (feat.season < Y) & (feat.week <= 18)]
        full = feat[feat.season <= Y]
        test = feat[(feat.season == Y) & (feat.played == 1) & (feat.week <= FANTASY_LAST_WEEK)].copy()
        test["_base"] = naive_ppg(test)
        snaps = {}
        for v in variants:
            pr = Projector(**VARIANTS[v]).fit(train, full, tg)
            test[f"m_{v}"] = pr.predict_games(test).proj.values
            for W in weeks:
                out, _ = project_ros(pr, full, tg, Y, W)
                out = out.set_index("player_id")
                if W not in snaps:
                    snaps[W] = out.drop(columns=["ros_pts"])
                snaps[W][f"m_{v}"] = out.ros_pts
        if lgbm:
            test["m_lgbm"] = _lgbm_predict(train, full, test, tg)
        test["b_naive"] = test._base
        test["b_recent3"] = test.ewm_pts_s.fillna(test._base)
        weekly.append(test)
        for W, base in snaps.items():
            snap = full[(full.season == Y) & (full.week >= W)].sort_values("week").groupby("player_id").first()
            base["b_naive"] = naive_ppg(snap).reindex(base.index) * base.games_left
            base["_base"] = base.b_naive
            ros.append(base.reset_index())
        print(f"  season {Y} done", flush=True)
    return pd.concat(weekly), pd.concat(ros, ignore_index=True)


def _lgbm_predict(train, full, test, tg):
    import lightgbm as lgb
    pr = Projector().fit(train, full, tg)

    def mat(d):
        d = pr.attach_def(d)
        parts = []
        for pos in ["QB", "RB", "WR", "TE"]:
            X = rating_matrix(d[d.position == pos], pos)
            parts.append(X)
        X = pd.concat(parts).reindex(d.index)
        C = pr.context_frame(d)
        X = pd.concat([X, C], axis=1)
        X["pos"] = d.position.map({"QB": 0, "RB": 1, "WR": 2, "TE": 3})
        return X.fillna(0)
    tr = train[train.played == 1]
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=50,
                          subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1)
    m.fit(mat(tr), tr.pts)
    return m.predict(mat(test))


def summarize_weekly(res, models):
    out = []
    for pos in ["QB", "RB", "WR", "TE"]:
        d = res[res.position == pos]
        for m in models:
            err = d[m] - d.pts
            out.append({"position": pos, "model": m, "MAE": err.abs().mean(),
                        "RMSE": np.sqrt((err ** 2).mean()),
                        "R2": 1 - (err ** 2).sum() / ((d.pts - d.pts.mean()) ** 2).sum()})
    t = pd.DataFrame(out)
    corr = []
    for m in models:
        c = _rank_corr(res, m, "pts", WEEKLY_POOL, ["season", "week"])
        corr += [{"position": p, "model": m, "rank_corr": v} for p, v in c.items()]
    return t.merge(pd.DataFrame(corr), on=["position", "model"])


def summarize_ros(res, models, league=None):
    league = league or League()
    out = []
    for m in models:
        c = _rank_corr(res, m, "actual_ros", POOL, ["season", "week"])
        for pos in POOL:
            d = res[res.position == pos]
            mae, pair = [], []
            for _, g in d.groupby(["season", "week"]):
                n = POOL[pos]
                pool = g[(g[m].rank(ascending=False) <= n) | (g._base.rank(ascending=False) <= n)]
                mae.append((pool[m] - pool.actual_ros).abs().mean())
                pair.append(_pairwise(pool[m].values, pool.actual_ros.values))
            out.append({"position": pos, "model": m, "rank_corr": c[pos],
                        "MAE_ros": np.mean(mae), "pair_acc": np.mean(pair)})
        out.append({"position": "ALL (1-for-1 trades)", "model": m,
                    "pair_acc": _trade_accuracy(res, m, league)})
    return pd.DataFrame(out)


def _pairwise(pred, actual, min_gap=0.0):
    i, j = np.triu_indices(len(pred), 1)
    gap = actual[i] - actual[j]
    ok = np.abs(gap) > min_gap
    return np.mean(np.sign(pred[i] - pred[j])[ok] == np.sign(gap)[ok])


def vorp(df, col, league):
    """Points over the replacement-level player at each position."""
    rep_rank = league.replacement_rank()
    out = pd.Series(np.nan, index=df.index)
    for pos, r in rep_rank.items():
        m = df.position == pos
        vals = df.loc[m, col].sort_values(ascending=False)
        rep = vals.iloc[min(r - 1, len(vals) - 1)] if len(vals) else 0
        out[m] = df.loc[m, col] - rep
    return out


def _trade_accuracy(res, m, league):
    """Across positions: does the projection pick the side that actually scored more over replacement?"""
    accs = []
    for _, g in res.groupby(["season", "week"]):
        g = g.copy()
        g["v_pred"] = vorp(g, m, league)
        g["v_act"] = vorp(g, "actual_ros", league)
        top = g[(g.v_pred > -15) | (vorp(g, "_base", league) > -15)]
        accs.append(_pairwise(top.v_pred.values, top.v_act.values, min_gap=10))
    return np.mean(accs)
