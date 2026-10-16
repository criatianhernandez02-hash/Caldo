"""Run the 10-season walk-forward backtest and write results to output/backtest/."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from caldo.backtest import VARIANTS, load_features, run, summarize_ros, summarize_weekly
from caldo.config import BACKTEST_SEASONS, OUT_DIR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scoring", default="ppr", choices=["ppr", "half", "std"])
    ap.add_argument("--quick", action="store_true", help="full model only, no ablations/LightGBM")
    args = ap.parse_args()

    feat, tg = load_features(2026, args.scoring)
    variants = ("full",) if args.quick else tuple(VARIANTS)
    weekly, ros = run(feat, tg, BACKTEST_SEASONS, variants, lgbm=not args.quick)

    out = OUT_DIR / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    wk_models = [f"m_{v}" for v in variants] + ([] if args.quick else ["m_lgbm"]) + ["b_naive", "b_recent3"]
    ros_models = [f"m_{v}" for v in variants] + ["b_naive"]
    ws = summarize_weekly(weekly, wk_models)
    rs = summarize_ros(ros, ros_models)
    ws.to_csv(out / f"weekly_summary_{args.scoring}.csv", index=False)
    rs.to_csv(out / f"ros_summary_{args.scoring}.csv", index=False)
    ros.to_parquet(out / f"ros_detail_{args.scoring}.parquet")
    weekly[["player_id", "player_display_name", "position", "season", "week", "pts", "_base"]
           + wk_models].to_parquet(out / f"weekly_detail_{args.scoring}.parquet")
    pd.set_option("display.width", 200)
    print(ws.round(3).to_string())
    print(rs.round(3).to_string())


if __name__ == "__main__":
    main()
