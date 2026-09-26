"""Walk-forward backtest: for each past week, project using only data available before
kickoff (plus that week's closing Vegas lines) and score the predictions against what
actually happened."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .model import Config, project_week
from .parlay import default_legs, weekly_card


def _log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def run(stats: pd.DataFrame, games: pd.DataFrame, season: int, weeks: list[int],
        cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    variants = {
        "full model": cfg,
        "no matchup": replace(cfg, matchup_clip=(1.0, 1.0)),
        "no vegas lines": replace(cfg, use_vegas=False),
    }
    preds = {k: [] for k in variants}
    slips = []
    for week in weeks:
        actual = stats[(stats["season"] == season) & (stats["week"] == week)]
        actual = actual.assign(any_td=(actual["rushing_tds"] + actual["receiving_tds"]) > 0)
        actual = actual.set_index("player_id")[["any_td", "passing_tds"]]
        for name, c in variants.items():
            try:
                proj, _ = project_week(stats, games, season, week, c)
            except ValueError:
                continue
            proj = proj.join(actual, on="player_id", how="inner")  # only players who suited up
            proj["week"] = week
            preds[name].append(proj)
            if name == "full model":
                legs = default_legs(proj)
                legs = legs.merge(proj[["name", "any_td", "passing_tds"]], left_on="player", right_on="name")
                legs["hit"] = np.where(
                    legs["market"] == "pass_tds",
                    np.where(legs["side"] == "more", legs["passing_tds"] > legs["line"],
                             legs["passing_tds"] < legs["line"]),
                    legs["any_td"],
                )
                for slip in weekly_card(legs):
                    slips.append({"week": week, "slip": slip.name, "pred": slip.prob,
                                  "hit": bool(slip.legs["hit"].all()),
                                  "legs_hit": int(slip.legs["hit"].sum()), "legs": len(slip.legs)})

    report = {}
    for name, frames in preds.items():
        df = pd.concat(frames, ignore_index=True)
        skill = df[df["pos"] != "QB"]
        y, p = skill["any_td"].astype(float).to_numpy(), skill["p_anytime_td"].to_numpy()
        base = np.full_like(p, y.mean())
        qb = df[df["pos"] == "QB"]
        yq = (qb["passing_tds"] >= 2).astype(float).to_numpy()
        pq = qb["p_pass_over_1.5"].to_numpy()
        report[name] = {
            "n_player_games": len(skill),
            "atd_brier": float(np.mean((p - y) ** 2)),
            "atd_brier_baseline": float(np.mean((base - y) ** 2)),
            "atd_logloss": _log_loss(p, y),
            "n_qb_games": len(qb),
            "qb_over1.5_brier": float(np.mean((pq - yq) ** 2)),
            "qb_over1.5_brier_baseline": float(np.mean((np.full_like(pq, yq.mean()) - yq) ** 2)),
            "frame": df,
        }
    report["slips"] = pd.DataFrame(slips)
    return report


def calibration(df: pd.DataFrame, prob_col: str, outcome: pd.Series,
                bins=(0, .2, .3, .4, .5, .6, .7, 1.0)) -> pd.DataFrame:
    b = pd.cut(df[prob_col], bins)
    return (pd.DataFrame({"bucket": b, "pred": df[prob_col], "actual": outcome.astype(float)})
            .groupby("bucket", observed=True)
            .agg(n=("pred", "size"), predicted=("pred", "mean"), actual=("actual", "mean")))


def top_pick_hit_rate(df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """How often the model's top-k anytime-TD picks each week actually scored."""
    skill = df[df["pos"] != "QB"]
    top = skill.sort_values("p_anytime_td", ascending=False).groupby("week").head(k)
    return pd.DataFrame({
        "picks": [len(top)],
        "avg_predicted": [top["p_anytime_td"].mean()],
        "actual_hit_rate": [top["any_td"].mean()],
    })
