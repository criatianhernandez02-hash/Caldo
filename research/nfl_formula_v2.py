"""Caldo NFL win formula v2: points rating + efficiency (EPA per play) + situational terms.

    python research/nfl_formula_v2.py

Inputs per game, all known before kickoff:
  rating_diff   points-rating difference from nfl_formula.py (home - away), incl. nothing else
  off_diff      (home offensive EPA/play) - (away offensive EPA/play), recency-weighted
  def_diff      (home defensive EPA/play allowed) - (away ...), recency-weighted (lower = better)
  rest_diff     home rest days - away rest days, capped at +/- 7
  backup_home / backup_away   1 if that team starts a non-regular QB
  neutral       1 at neutral sites (removes home field)
P(home win) = logistic(b0 + b . features), fit on 2007-2018, checked on 2019-2024 and then
tested once on 2025-2026. EPA ratings use exponentially weighted per-play averages with a
half-life of HL games and carry over seasons shrunk toward league average.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tdmodel.data import DEFAULT_CACHE  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
HL = 8.0           # half-life in games for EPA averages
CARRY = 0.5        # share of last season's EPA level kept at the start of a new season
PRIOR_PLAYS = 300  # pseudo-plays of league average mixed into every team's rating
FEATURES = ["rating_diff", "off_diff", "def_diff", "rest_diff", "backup_home", "backup_away", "home_field"]


def team_weeks() -> pd.DataFrame:
    frames = []
    for y in range(2006, 2027):
        p = DEFAULT_CACHE / f"stats_team_week_{y}.csv"
        if p.exists():
            frames.append(pd.read_csv(p, low_memory=False, usecols=[
                "season", "week", "team", "season_type", "opponent_team", "attempts", "sacks_suffered",
                "passing_epa", "carries", "rushing_epa"]))
    d = pd.concat(frames, ignore_index=True)
    d["plays"] = d["attempts"].fillna(0) + d["sacks_suffered"].fillna(0) + d["carries"].fillna(0)
    d["epa"] = d["passing_epa"].fillna(0) + d["rushing_epa"].fillna(0)
    return d


def epa_features(g: pd.DataFrame, tw: pd.DataFrame) -> pd.DataFrame:
    """Walk forward in kickoff order; before each game read each team's current EPA ratings,
    after it fold in that game's offensive and defensive EPA."""
    tw = tw.set_index(["season", "week", "team"])
    lg_off = (tw["epa"].sum() / tw["plays"].sum())
    state: dict[str, dict] = {}
    season = None
    feats = []
    decay = 0.5 ** (1 / HL)

    def get(t):
        return state.setdefault(t, {"oe": 0.0, "op": 0.0, "de": 0.0, "dp": 0.0})

    def rate(s, kind):
        e, p = s[f"{kind}e"], s[f"{kind}p"]
        return (e + PRIOR_PLAYS * lg_off) / (p + PRIOR_PLAYS)

    for r in g.itertuples():
        if r.season != season:
            season = r.season
            for s in state.values():  # new season: keep CARRY of last year's evidence
                for k in s:
                    s[k] *= CARRY
        h, a = get(r.home_team), get(r.away_team)
        feats.append((rate(h, "o") - rate(a, "o"), rate(h, "d") - rate(a, "d")))
        for team, opp, st in ((r.home_team, r.away_team, h), (r.away_team, r.home_team, a)):
            key = (r.season, r.week, team)
            if key in tw.index:
                row = tw.loc[key]
                row = row.iloc[0] if isinstance(row, pd.DataFrame) else row
                for k in st:
                    st[k] *= decay
                st["oe"] += row["epa"]; st["op"] += row["plays"]
                ok = (r.season, r.week, opp)
                if ok in tw.index:
                    orow = tw.loc[ok]
                    orow = orow.iloc[0] if isinstance(orow, pd.DataFrame) else orow
                    st["de"] += orow["epa"]; st["dp"] += orow["plays"]
    f = pd.DataFrame(feats, columns=["off_diff", "def_diff"], index=g.index)
    return f


def log_loss(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main() -> None:
    g = pd.read_csv(OUT / "nfl_formula_predictions.csv", low_memory=False)
    g = g[g["season"] >= 2006].reset_index(drop=True)
    # recover v1's rating difference from its probability (inverse of the normal model)
    from scipy.stats import norm  # noqa: E402
    sigma, hfa, rest, qb = 12.5, 2.5, 0.2, 3.0
    exp_margin = norm.ppf(np.clip(g["p_model"], 1e-6, 1 - 1e-6)) * sigma
    g["home_field"] = 1 - g["neutral"]
    g["rest_diff"] = np.clip(g["home_rest"].fillna(7) - g["away_rest"].fillna(7), -7, 7)
    g["rating_diff"] = exp_margin - hfa * g["home_field"] - rest * g["rest_diff"] - qb * (g["backup_away"] - g["backup_home"])
    g = pd.concat([g, epa_features(g, team_weeks())], axis=1)
    played = g["home_score"].notna() & (g["y"] != 0.5)
    train = played & g["season"].between(2007, 2018)
    model = LogisticRegression(C=1.0, max_iter=1000).fit(g.loc[train, FEATURES], g.loc[train, "y"])
    print("coefficients:", dict(zip(FEATURES, np.round(model.coef_[0], 4))), "intercept", round(model.intercept_[0], 4))
    g["p_v2"] = model.predict_proba(g[FEATURES])[:, 1]
    rows = []
    for name, lo, hi in (("train 2007-18", 2007, 2018), ("validate 2019-24", 2019, 2024), ("test 2025-26", 2025, 2026)):
        m = played & g["season"].between(lo, hi) & g["p_market"].notna() & np.isfinite(g["p_market"])
        d = g[m]
        rows.append({"period": name, "games": len(d), "v1": log_loss(d.p_model, d.y), "v2": log_loss(d.p_v2, d.y),
                     "market": log_loss(d.p_market, d.y)})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    g.to_csv(OUT / "nfl_formula_v2_predictions.csv", index=False)


if __name__ == "__main__":
    main()
