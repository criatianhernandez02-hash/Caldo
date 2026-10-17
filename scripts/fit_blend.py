"""Score our weekly projections against Sleeper's (2018-2025), find blind spots, fit the blend.

Writes output/blend.json (weights, scaling, availability rates) and
output/compare/{head_to_head,blind_spots}.csv for the app and README.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from caldo.backtest import load_features
from caldo.config import OUT_DIR
from caldo.external import availability_rates, blind_spots, fit_blend, head_to_head, load_sleeper_projections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v4")
    args = ap.parse_args()
    feat, tg = load_features(2026, "ppr")
    sp = load_sleeper_projections()
    wk = pd.read_parquet(OUT_DIR / "backtest" / args.tag / "weekly_detail_ppr.parquet")
    d, _ = head_to_head(wk[wk.season >= 2018], sp[sp.season <= 2025])
    cfg, scores, history = fit_blend(d, feat)
    spots = blind_spots(d, feat)
    rates = availability_rates(feat, sp[sp.season <= 2025])
    # Sleeper's points rescaled to our scoring for each format
    x = feat[(feat.season.between(2018, 2025)) & (feat.played == 1)][["player_id", "season", "week", "position", "pts_ppr", "pts_half", "pts_std"]]
    x = x.merge(sp, on=["season", "week", "player_id"])
    for pos in cfg:
        t = x[x.position == pos]
        for sc in ["ppr", "half", "std"]:
            cfg[pos][f"scale_{sc}"] = round(float(t[f"pts_{sc}"].sum() / t[f"sl_{sc}"].sum()), 4)
    out = OUT_DIR / "compare"
    out.mkdir(parents=True, exist_ok=True)
    scores.to_csv(out / "head_to_head.csv", index=False)
    spots.to_csv(out / "blind_spots.csv", index=False)
    (OUT_DIR / "blend.json").write_text(json.dumps({"weights": cfg, "availability": rates, "weights_by_test_season": history,
                                                    "seasons": "2018-2025", "test_seasons": "2020-2025"}, indent=2))
    pd.set_option("display.width", 200)
    print(scores.pivot(index="model", columns="position", values=["MAE", "rank_corr"]).round(3).to_string())
    print(json.dumps(cfg, indent=1)); print(json.dumps(rates, indent=1))
    print(spots.pivot_table(index="segment", columns="position", values="edge").round(2).to_string())


if __name__ == "__main__":
    main()
