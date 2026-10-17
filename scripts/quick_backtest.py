"""Fast walk-forward check of a few model variants (no LightGBM, no full ablation set)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from caldo.backtest import load_features, run, summarize_ros, summarize_weekly
from caldo.config import BACKTEST_SEASONS, OUT_DIR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="full,no_status,no_role")
    ap.add_argument("--tag", default="v2")
    args = ap.parse_args()
    variants = tuple(args.variants.split(","))
    feat, tg = load_features(2026, "ppr")
    weekly, ros = run(feat, tg, BACKTEST_SEASONS, variants, lgbm=False)
    out = OUT_DIR / "backtest" / args.tag
    out.mkdir(parents=True, exist_ok=True)
    wk_models = [f"m_{v}" for v in variants] + ["b_naive", "b_recent3"]
    ros_models = [f"m_{v}" for v in variants] + ["b_naive"]
    ws, rs = summarize_weekly(weekly, wk_models), summarize_ros(ros, ros_models)
    ws.to_csv(out / "weekly_summary_ppr.csv", index=False)
    rs.to_csv(out / "ros_summary_ppr.csv", index=False)
    ros.to_parquet(out / "ros_detail_ppr.parquet")
    weekly[["player_id", "player_display_name", "position", "season", "week", "pts", "_base"] + wk_models].to_parquet(out / "weekly_detail_ppr.parquet")
    pd.set_option("display.width", 200)
    print(ws.round(3).to_string())
    print(rs.round(3).to_string())


if __name__ == "__main__":
    main()
