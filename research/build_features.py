"""Build a walk-forward feature table: one row per (player, game) with only pre-game info.

For every evaluation week the existing model is run on data strictly before that week, in
three flavours (actual-TD shares, expected-TD shares, 50/50 blend). Their outputs plus the
raw usage features become the inputs for every model compared in compare_models.py.

    python research/build_features.py            # writes research/out/features.parquet-ish CSV
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tdmodel.data import load_games, load_player_weeks  # noqa: E402
from tdmodel.model import Config, project_week  # noqa: E402
from tdmodel.opportunity import attach_expected, load_expected  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
SEASONS = [2022, 2023, 2024, 2025, 2026]
EVAL = [(2023, w) for w in range(3, 19)] + [(2024, w) for w in range(3, 19)] + \
       [(2025, w) for w in range(3, 19)] + [(2026, w) for w in range(2, 7)]

KEEP = ["player_id", "name", "pos", "team", "opp", "game_id", "home", "total", "spread", "implied_pts",
        "exp_off_tds", "rush_frac", "carry_share", "target_share", "att_share", "carries_pg", "targets_pg",
        "attempts_pg", "rush_td_share", "rec_td_share", "x_rush_td_share", "x_rec_td_share", "td_pg",
        "xtd_pg", "games", "matchup_mult", "def_rank_vs_pos", "lam_td", "p_anytime_td", "lam_pass_td",
        "p_pass_over_0.5", "p_pass_over_1.5", "p_pass_over_2.5", "pass_matchup_mult"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    games = load_games()
    stats = load_player_weeks(SEASONS, 2026)
    stats = attach_expected(stats, load_expected(SEASONS, 2026))
    base = Config()
    variants = {"act": base, "x": replace(base, td_signal=1.0), "mix": replace(base, td_signal=0.5)}
    rows = []
    for season, week in EVAL:
        actual = stats[(stats["season"] == season) & (stats["week"] == week)]
        if actual.empty:
            continue
        actual = actual.assign(td=actual["rushing_tds"] + actual["receiving_tds"])
        actual = actual.set_index("player_id")[["td", "passing_tds", "x_rush_td", "x_rec_td"]]
        frames = {}
        for name, cfg in variants.items():
            proj, _ = project_week(stats, games, season, week, cfg)
            frames[name] = proj.set_index("player_id")
        df = frames["act"][[c for c in KEEP if c != "player_id" and c in frames["act"].columns]].copy()
        for name in ("x", "mix"):
            df[f"lam_td_{name}"] = frames[name]["lam_td"]
            df[f"p_anytime_td_{name}"] = frames[name]["p_anytime_td"]
            df[f"lam_pass_td_{name}"] = frames[name]["lam_pass_td"]
        df = df.join(actual, how="inner")  # players who actually suited up
        df["season"], df["week"] = season, week
        rows.append(df.reset_index())
        print(season, week, len(df), flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(OUT / "features.csv", index=False)
    print("saved", len(out), "rows to", OUT / "features.csv")


if __name__ == "__main__":
    main()
