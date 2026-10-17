"""Model vs market, and a replay of betting strategies on 2026 weeks 1-6.

1. Joins pre-kickoff Kalshi prices (kalshi_history.py) to the walk-forward model predictions
   (compare_models.py) for the same player-games and scores model, market and blends.
2. Fits Sleeper's pricing rule (multiplier as a function of the market probability) from a
   live snapshot of Sleeper multipliers + Kalshi prices taken on the same day.
3. Replays strategies against real outcomes using the fitted Sleeper multipliers.

    python research/market_test.py <sleeper_vs_kalshi_snapshot.csv>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.compare_models import brier, calib, log_loss, logit, sigmoid  # noqa: E402
from tdmodel.parlay import norm_name  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def join_market(preds: pd.DataFrame, kal: pd.DataFrame, market: str, line: float) -> pd.DataFrame:
    k = kal[(kal["market"] == market) & (kal["line"] == line)].copy()
    k["key"] = k["player"].map(norm_name)
    p = preds.copy()
    p["key"] = p["name"].map(norm_name)
    return p.merge(k[["game_id", "key", "kalshi_p", "price_source", "pregame_volume", "result"]],
                   on=["game_id", "key"], how="inner")


def fit_sleeper_pricing(snap: pd.DataFrame) -> dict:
    """Sleeper implied prob (1/multiplier) as a linear function of the market probability."""
    k = snap["kalshi_prob"].to_numpy()
    a = np.polyfit(k, 1 / snap["m_over"].to_numpy(), 1)
    b = np.polyfit(1 - k, 1 / snap["m_under"].to_numpy(), 1)
    return {"over": a, "under": b}


def sleeper_mult(pricing: dict, p_market: np.ndarray, side: str) -> np.ndarray:
    coef = pricing["over"] if side == "more" else pricing["under"]
    q = p_market if side == "more" else 1 - p_market
    return 1 / np.clip(np.polyval(coef, q), 0.05, 0.99)


def score(df: pd.DataFrame, cols: list[str], y: str) -> pd.DataFrame:
    rows = []
    for c in cols:
        p = df[c].to_numpy(); yy = df[y].to_numpy()
        ci, cs = calib(p, yy)
        rows.append({"model": c, "n": len(p), "brier": brier(p, yy), "log_loss": log_loss(p, yy),
                     "cal_intercept": ci, "cal_slope": cs})
    return pd.DataFrame(rows)


def replay(legs: pd.DataFrame, rule: str, prob_col: str, threshold: float = 0.0) -> dict:
    """Flat $1 per leg. rule: 'value' = bet when prob*mult-1 > threshold; 'likely' = top-5 'more' per week."""
    if rule == "value":
        bets = legs[legs[prob_col] * legs["mult"] - 1 > threshold]
    elif rule == "likely":
        bets = legs[legs["side"] == "more"].sort_values(prob_col, ascending=False).groupby("wk").head(5)
    else:
        bets = legs
    if bets.empty:
        return {"rule": rule, "prob": prob_col, "thr": threshold, "bets": 0}
    pnl = np.where(bets["win"], bets["mult"] - 1, -1.0)
    return {"rule": rule, "prob": prob_col, "thr": threshold, "bets": len(bets), "hit_rate": bets["win"].mean(),
            "avg_mult": bets["mult"].mean(), "roi": pnl.mean(),
            "roi_se": pnl.std(ddof=1) / np.sqrt(len(pnl)) if len(pnl) > 1 else np.nan,
            "market_ev": (bets["p_mkt"] * bets["mult"] - 1).mean()}


def main(snapshot_csv: str) -> None:
    kal = pd.read_csv(OUT / "kalshi_pregame.csv")
    skill = pd.read_csv(OUT / "skill_preds.csv")
    qb = pd.read_csv(OUT / "qb_preds.csv")
    pd.set_option("display.width", 220)

    # ---- 1. accuracy on the overlap
    s = join_market(skill[skill["season"] == 2026], kal, "anytime_td", 0.5)
    s = s[s["price_source"] == "mid"].copy()
    s["blend_50"] = sigmoid((logit(s["poisson_mix"]) + logit(s["kalshi_p"])) / 2)
    s["blend_25"] = sigmoid(0.25 * logit(s["poisson_mix"]) + 0.75 * logit(s["kalshi_p"]))
    print(f"\nAnytime TD, 2026 player-games with a tight Kalshi pre-kickoff quote: {len(s)}")
    print("result agreement check (Kalshi settlement vs nflverse):", (s["result"] == (s["y_td"] > 0)).mean().round(4))
    cols = ["base_pos", "poisson_actual", "poisson_mix", "logistic", "kalshi_p", "blend_25", "blend_50"]
    print(score(s, cols, "y_td").round(4).to_string(index=False))
    # paired weekly bootstrap: market minus model
    rng = np.random.default_rng(0)
    d = ((s["kalshi_p"] - s["y_td"]) ** 2 - (s["poisson_mix"] - s["y_td"]) ** 2).groupby(s["wk"]).agg(["sum", "count"])
    boots = [d["sum"].iloc[i].sum() / d["count"].iloc[i].sum()
             for i in (rng.integers(0, len(d), len(d)) for _ in range(4000))]
    print("Brier(market) - Brier(model) =", round(d["sum"].sum() / d["count"].sum(), 4),
          " 95% CI", np.percentile(boots, [2.5, 97.5]).round(4))

    q = join_market(qb[qb["season"] == 2026], kal, "pass_tds", 1.5)
    q = q[q["price_source"] == "mid"].copy()
    if len(q):
        q["blend_50"] = sigmoid((logit(q["poisson_actual"]) + logit(q["kalshi_p"])) / 2)
        print(f"\nQB 2+ pass TDs, 2026 with Kalshi quote: {len(q)}")
        print(score(q, ["base_rate", "poisson_actual", "logistic", "kalshi_p", "blend_50"], "y_pass2").round(4).to_string(index=False))

    # ---- 2. Sleeper pricing rule from a same-day snapshot
    snap = pd.read_csv(snapshot_csv)
    pricing = fit_sleeper_pricing(snap)
    print("\nSleeper pricing fit: 1/mult_over = %.3f*p + %.3f ; 1/mult_under = %.3f*(1-p) + %.3f"
          % (*pricing["over"], *pricing["under"]))
    resid = 1 / snap["m_over"] - np.polyval(pricing["over"], snap["kalshi_prob"])
    print("fit residual sd (implied prob):", resid.std().round(4))

    # ---- 3. replay strategies on 2026 anytime-TD legs (both sides)
    legs = []
    for side in ("more", "less"):
        t = s.copy()
        t["side"] = side
        t["mult"] = sleeper_mult(pricing, t["kalshi_p"].to_numpy(), side)
        flip = (lambda c: t[c]) if side == "more" else (lambda c: 1 - t[c])
        t["p_mkt"], t["p_model"], t["p_blend"] = flip("kalshi_p"), flip("poisson_mix"), flip("blend_50")
        t["p_logit"] = flip("logistic")
        t["win"] = (t["y_td"] > 0) if side == "more" else (t["y_td"] == 0)
        legs.append(t)
    legs = pd.concat(legs, ignore_index=True)
    rows = [replay(legs, "all", "p_mkt")]
    for prob in ("p_model", "p_logit", "p_blend"):
        for thr in (0.0, 0.05, 0.10):
            rows.append(replay(legs, "value", prob, thr))
    rows.append(replay(legs, "likely", "p_mkt"))
    rows.append(replay(legs, "likely", "p_model"))
    print("\nStrategy replay, 2026 weeks with Kalshi coverage (flat $1 per leg, synthetic Sleeper multipliers):")
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    legs.to_csv(OUT / "replay_legs_2026.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
