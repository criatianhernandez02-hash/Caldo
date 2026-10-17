"""The Caldo NFL win formula: a points-based team rating, tuned and tested walk-forward.

Formula (home team's perspective, before kickoff):

    expected_margin = (R_home - R_away)               # team ratings, in points
                    + HFA                             # home-field advantage (0 at neutral sites)
                    + REST  * (rest_home - rest_away) # capped at +/- 7 days
                    + QBADJ * (backup_away - backup_home)   # 1 if that team starts a non-regular QB
    P(home wins)    = Phi(expected_margin / SIGMA)

After each game both ratings move toward what happened:
    error = clip(actual_margin, -CAP, CAP) - expected_margin
    R_home += K * error ; R_away -= K * error
Between seasons every rating shrinks toward 0: R *= (1 - REGRESS).

Parameters are chosen by grid search on 2002-2015 log loss, then checked on 2016-2024 and
finally on 2025-2026, which is never used for fitting. Each game's prediction uses only
games played before it.

    python research/nfl_formula.py        # tune, evaluate vs closing moneyline, save predictions
"""

from __future__ import annotations

import itertools
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tdmodel.data import DEFAULT_CACHE, _fetch, GAMES_URL  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


@dataclass(frozen=True)
class Params:
    K: float = 0.10
    HFA: float = 1.8
    REST: float = 0.25
    QBADJ: float = 4.0
    REGRESS: float = 0.33
    CAP: float = 21.0
    SIGMA: float = 13.5


def load_games() -> pd.DataFrame:
    path = _fetch(GAMES_URL, DEFAULT_CACHE / "games.csv", 6, False)
    g = pd.read_csv(path, low_memory=False)
    g = g[g["game_type"].isin(["REG", "WC", "DIV", "CON", "SB"])].copy()
    g["kick"] = pd.to_datetime(g["gameday"] + " " + g["gametime"].fillna("13:00"))
    g = g.sort_values(["kick", "game_id"]).reset_index(drop=True)
    g["neutral"] = (g["location"] == "Neutral").astype(int)
    return g


def regular_qb_flags(g: pd.DataFrame) -> pd.DataFrame:
    """backup_x = 1 when the starting QB is not the team's most frequent starter over its
    previous 8 games (known before kickoff)."""
    rows = []
    for side in ("home", "away"):
        rows.append(pd.DataFrame({"idx": g.index, "team": g[f"{side}_team"], "qb": g[f"{side}_qb_id"],
                                  "kick": g["kick"], "side": side}))
    long = pd.concat(rows).sort_values(["team", "kick"])
    flags = {}
    for team, d in long.groupby("team"):
        hist = []
        for r in d.itertuples():
            recent = hist[-8:]
            if len(recent) >= 3 and pd.notna(r.qb):
                regular = max(set(recent), key=recent.count)
                flags[(r.idx, r.side)] = int(r.qb != regular)
            else:
                flags[(r.idx, r.side)] = 0
            if pd.notna(r.qb):
                hist.append(r.qb)
    out = g.copy()
    out["backup_home"] = [flags[(i, "home")] for i in g.index]
    out["backup_away"] = [flags[(i, "away")] for i in g.index]
    return out


def run(g: pd.DataFrame, p: Params) -> np.ndarray:
    """Walk forward through every game; returns the pre-game P(home win) for each row."""
    R: dict[str, float] = {}
    season = None
    probs = np.empty(len(g))
    home_t, away_t = g["home_team"].to_numpy(), g["away_team"].to_numpy()
    rh, ra = g["home_rest"].fillna(7).to_numpy(), g["away_rest"].fillna(7).to_numpy()
    bh, ba = g["backup_home"].to_numpy(), g["backup_away"].to_numpy()
    neutral = g["neutral"].to_numpy()
    margin = (g["home_score"] - g["away_score"]).to_numpy()
    seasons = g["season"].to_numpy()
    for i in range(len(g)):
        if seasons[i] != season:
            season = seasons[i]
            for t in R:
                R[t] *= 1 - p.REGRESS
        h, a = home_t[i], away_t[i]
        exp = (R.get(h, 0.0) - R.get(a, 0.0) + p.HFA * (1 - neutral[i])
               + p.REST * float(np.clip(rh[i] - ra[i], -7, 7)) + p.QBADJ * (ba[i] - bh[i]))
        probs[i] = 0.5 * (1 + math.erf(exp / (p.SIGMA * math.sqrt(2))))
        if not np.isnan(margin[i]):
            err = float(np.clip(margin[i], -p.CAP, p.CAP)) - exp
            R[h] = R.get(h, 0.0) + p.K * err
            R[a] = R.get(a, 0.0) - p.K * err
    return probs


def log_loss(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def devig(home_ml: pd.Series, away_ml: pd.Series) -> pd.Series:
    def imp(ml):
        return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))
    ph, pa = imp(home_ml.to_numpy(float)), imp(away_ml.to_numpy(float))
    return pd.Series(ph / (ph + pa), index=home_ml.index)


def tune(g: pd.DataFrame, mask: np.ndarray, y: np.ndarray) -> tuple[Params, float]:
    grid = {"K": [0.06, 0.08, 0.10, 0.12], "HFA": [1.5, 2.0, 2.5], "REST": [0.0, 0.2, 0.4],
            "QBADJ": [0.0, 3.0, 5.0, 7.0], "REGRESS": [0.25, 0.33, 0.45], "SIGMA": [12.5, 13.5, 14.5]}
    best, best_ll = None, 1e9
    for vals in itertools.product(*grid.values()):
        p = Params(**dict(zip(grid, vals)))
        ll = log_loss(run(g, p)[mask], y[mask])
        if ll < best_ll:
            best, best_ll = p, ll
    return best, best_ll


def main() -> None:
    OUT.mkdir(exist_ok=True)
    g = regular_qb_flags(load_games())
    played = g["home_score"].notna().to_numpy()
    y = (g["home_score"] > g["away_score"]).astype(float).to_numpy().copy()
    tie = (g["home_score"] == g["away_score"]).to_numpy()
    y[tie] = 0.5
    train = played & (g["season"].between(2002, 2015)).to_numpy()
    params, ll = tune(g, train, y)
    print("tuned on 2002-2015:", params, "log loss", round(ll, 4))
    g["p_model"] = run(g, params)
    g["p_market"] = devig(g["home_moneyline"], g["away_moneyline"])
    g["y"] = y
    rows = []
    for name, lo, hi in (("train 2002-15", 2002, 2015), ("validate 2016-24", 2016, 2024), ("test 2025-26", 2025, 2026)):
        m = played & g["season"].between(lo, hi).to_numpy() & g["p_market"].notna().to_numpy()
        d = g[m]
        rows.append({"period": name, "games": len(d),
                     "model_logloss": log_loss(d.p_model, d.y), "market_logloss": log_loss(d.p_market, d.y),
                     "model_brier": brier(d.p_model, d.y), "market_brier": brier(d.p_market, d.y),
                     "model_acc": float(((d.p_model > .5) == (d.y > .5)).mean()),
                     "market_acc": float(((d.p_market > .5) == (d.y > .5)).mean())})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    g.to_csv(OUT / "nfl_formula_predictions.csv", index=False)


if __name__ == "__main__":
    main()
