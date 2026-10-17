"""Head-to-head comparison of touchdown models (walk-forward, no peeking).

Input: research/out/features.csv from build_features.py (+ optional Kalshi pre-kickoff prices).

Anytime TD (RB/WR/TE) and QB 2+ passing TDs are scored with Brier score, log loss, AUC and
calibration. Learned models (logistic regression, gradient boosting) are retrained every
week on all earlier weeks only. Weekly-clustered bootstrap gives a confidence interval for
each model's Brier difference vs the current production model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

OUT = Path(__file__).resolve().parent / "out"
EPS = 1e-6

TD_FEATURES = ["implied_pts", "total", "spread", "rush_frac", "carry_share", "target_share",
               "carries_pg", "targets_pg", "rush_td_share", "rec_td_share", "x_rush_td_share",
               "x_rec_td_share", "td_pg", "xtd_pg", "games", "matchup_mult", "home",
               "log_lam_act", "log_lam_x", "is_RB", "is_WR", "is_TE"]
QB_FEATURES = ["implied_pts", "total", "spread", "rush_frac", "attempts_pg", "pass_matchup_mult", "home",
               "log_lam_pass", "log_lam_pass_x", "games"]


def logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def log_loss(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calib(p, y):
    """Calibration intercept & slope: logistic regression of y on logit(p). Ideal = (0, 1)."""
    lr = LogisticRegression(C=1e6).fit(logit(p).reshape(-1, 1), y)
    return float(lr.intercept_[0]), float(lr.coef_[0][0])


def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["y_td"] = (df["td"] > 0).astype(float)
    df["y_pass2"] = (df["passing_tds"] >= 2).astype(float)
    df["y_pass1"] = (df["passing_tds"] >= 1).astype(float)
    df["home"] = df["home"].astype(float)
    for pos in ("RB", "WR", "TE"):
        df[f"is_{pos}"] = (df["pos"] == pos).astype(float)
    df["log_lam_act"] = np.log(df["lam_td"].clip(lower=1e-3))
    df["log_lam_x"] = np.log(df["lam_td_x"].clip(lower=1e-3))
    df["log_lam_pass"] = np.log(df["lam_pass_td"].clip(lower=1e-3))
    df["log_lam_pass_x"] = np.log(df["lam_pass_td_x"].clip(lower=1e-3))
    df["xtd_pg"] = df["xtd_pg"].fillna(df["td_pg"])
    for c in ("x_rush_td_share", "x_rec_td_share"):
        df[c] = df[c].fillna(df[c.replace("x_", "")])
    df["wk"] = df["season"] * 100 + df["week"]
    return df


def walk_forward(df: pd.DataFrame, feats: list[str], target: str, eval_mask: pd.Series,
                 make_model, min_train: int = 1500) -> pd.Series:
    """Predict each eval week with a model trained on all strictly earlier weeks."""
    pred = pd.Series(np.nan, index=df.index)
    X = df[feats].fillna(0.0).to_numpy()
    y = df[target].to_numpy()
    for wk in sorted(df.loc[eval_mask, "wk"].unique()):
        train = (df["wk"] < wk).to_numpy()
        test = ((df["wk"] == wk) & eval_mask).to_numpy()
        if train.sum() < min_train or test.sum() == 0:
            continue
        model = make_model().fit(X[train], y[train])
        pred[test] = model.predict_proba(X[test])[:, 1]
    return pred


def poisson_from_lambda(lam, line):
    from tdmodel.model import poisson_sf
    return poisson_sf(np.asarray(lam, dtype=float), line)


def score_table(df: pd.DataFrame, models: list[str], y: str, ref: str, n_boot: int = 2000,
                seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    weeks = df["wk"].unique()
    yv = df[y].to_numpy()
    rows = []
    sq = {m: (df[m].to_numpy() - yv) ** 2 for m in models}
    by_week = {m: pd.Series(sq[m]).groupby(df["wk"].to_numpy()).agg(["sum", "count"]) for m in models}
    for m in models:
        p = df[m].to_numpy()
        ci, cs = calib(p, yv)
        diff_week = by_week[m]["sum"] - by_week[ref]["sum"]
        cnt = by_week[m]["count"]
        boots = []
        for _ in range(n_boot):
            idx = rng.choice(len(weeks), len(weeks), replace=True)
            boots.append(diff_week.iloc[idx].sum() / cnt.iloc[idx].sum())
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({"model": m, "n": len(p), "brier": brier(p, yv), "log_loss": log_loss(p, yv),
                     "auc": roc_auc_score(yv, p), "cal_intercept": ci, "cal_slope": cs,
                     f"brier_vs_{ref}": brier(p, yv) - brier(df[ref].to_numpy(), yv),
                     "ci95_lo": lo, "ci95_hi": hi})
    return pd.DataFrame(rows)


def top_k(df: pd.DataFrame, models: list[str], y: str, k: int = 10) -> pd.DataFrame:
    rows = []
    for m in models:
        top = df.sort_values(m, ascending=False).groupby("wk").head(k)
        rows.append({"model": m, "picks": len(top), "avg_pred": top[m].mean(), "hit_rate": top[y].mean()})
    return pd.DataFrame(rows)


def run(df: pd.DataFrame, kalshi: pd.DataFrame | None = None) -> dict:
    out = {}
    skill = df[df["pos"].isin(["RB", "WR", "TE"])].copy()
    eval_mask = skill["season"] >= 2024

    # --- baselines
    hist_rate = {}
    for wk in sorted(skill["wk"].unique()):
        past = skill[skill["wk"] < wk]
        hist_rate[wk] = past.groupby("pos")["y_td"].mean() if len(past) else None
    skill["base_pos"] = [hist_rate[w][p] if hist_rate[w] is not None and p in hist_rate[w] else np.nan
                         for w, p in zip(skill["wk"], skill["pos"])]
    skill["naive_td_rate"] = 1 - np.exp(-skill["td_pg"].clip(lower=0))
    skill["naive_xtd_rate"] = 1 - np.exp(-skill["xtd_pg"].clip(lower=0))
    skill["poisson_actual"] = skill["p_anytime_td"]
    skill["poisson_xtd"] = skill["p_anytime_td_x"]
    skill["poisson_mix"] = skill["p_anytime_td_mix"]

    # --- learned models (walk-forward)
    skill["logistic"] = walk_forward(
        skill, TD_FEATURES, "y_td", eval_mask,
        lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)))
    skill["gbm"] = walk_forward(
        skill, TD_FEATURES, "y_td", eval_mask,
        lambda: HistGradientBoostingClassifier(max_iter=250, learning_rate=0.04, max_leaf_nodes=15,
                                               min_samples_leaf=60, l2_regularization=1.0, random_state=0))
    skill["ens_logit_gbm"] = sigmoid((logit(skill["logistic"]) + logit(skill["gbm"])) / 2)

    models = ["base_pos", "naive_td_rate", "naive_xtd_rate", "poisson_actual", "poisson_xtd", "poisson_mix",
              "logistic", "gbm", "ens_logit_gbm"]
    ev = skill[eval_mask].dropna(subset=models)
    out["atd_all"] = score_table(ev, models, "y_td", "poisson_actual")
    out["atd_by_season"] = pd.concat([
        score_table(ev[ev["season"] == s], models, "y_td", "poisson_actual").assign(season=s)
        for s in sorted(ev["season"].unique())])
    out["atd_by_pos"] = pd.concat([
        score_table(ev[ev["pos"] == p], models, "y_td", "poisson_actual").assign(pos=p)
        for p in ("RB", "WR", "TE")])
    out["atd_topk"] = top_k(ev, models, "y_td")
    out["skill_preds"] = skill

    # --- QB passing TDs (2+)
    qb = df[df["pos"] == "QB"].copy()
    qmask = qb["season"] >= 2024
    hist_q = {}
    for wk in sorted(qb["wk"].unique()):
        past = qb[qb["wk"] < wk]
        hist_q[wk] = past["y_pass2"].mean() if len(past) else np.nan
    qb["base_rate"] = qb["wk"].map(hist_q)
    qb["poisson_actual"] = qb["p_pass_over_1.5"]
    qb["poisson_xtd"] = poisson_from_lambda(qb["lam_pass_td_x"], 1.5)
    qb["logistic"] = walk_forward(
        qb, QB_FEATURES, "y_pass2", qmask,
        lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)), min_train=300)
    qb["gbm"] = walk_forward(
        qb, QB_FEATURES, "y_pass2", qmask,
        lambda: HistGradientBoostingClassifier(max_iter=150, learning_rate=0.04, max_leaf_nodes=7,
                                               min_samples_leaf=40, l2_regularization=1.0, random_state=0),
        min_train=300)
    qmodels = ["base_rate", "poisson_actual", "poisson_xtd", "logistic", "gbm"]
    qev = qb[qmask].dropna(subset=qmodels)
    out["qb_all"] = score_table(qev, qmodels, "y_pass2", "poisson_actual")
    out["qb_preds"] = qb
    return out


def main() -> None:
    df = prep(pd.read_csv(OUT / "features.csv"))
    res = run(df)
    pd.set_option("display.width", 220)
    for key in ("atd_all", "atd_by_season", "atd_by_pos", "atd_topk", "qb_all"):
        print(f"\n=== {key} ===")
        print(res[key].round(4).to_string(index=False))
    res["skill_preds"].to_csv(OUT / "skill_preds.csv", index=False)
    res["qb_preds"].to_csv(OUT / "qb_preds.csv", index=False)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
