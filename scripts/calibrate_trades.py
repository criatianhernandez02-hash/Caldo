"""Measure how much 2nd/3rd pieces in a trade package are really worth.

Uses the backtest's week-7 rest-of-season projections for every season,
drafts simulated leagues from them, makes random trades and fits the
consolidation weights. Writes output/package_weights.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from caldo.config import OUT_DIR, League
from caldo.trade import fit_package_weights, simulate_trades


def main(scoring="ppr", week=7, leagues_per_season=4, trades_per_league=250):
    ros = pd.read_parquet(OUT_DIR / "backtest" / f"ros_detail_{scoring}.parquet")
    trades = []
    for season, snap in ros[ros.week == week].groupby("season"):
        t = simulate_trades(snap.reset_index(drop=True), League(scoring=scoring), leagues_per_season,
                            trades_per_league, seed=int(season), col="m_full")
        trades.append(t)
    trades = pd.concat(trades, ignore_index=True)
    res = fit_package_weights(trades)
    res.update({"n_trades": len(trades), "n_leagues": leagues_per_season * ros.season.nunique()})
    (OUT_DIR / "package_weights.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
