"""Backtest betting rules on Kalshi game-winner markets, with fees, split in time.

    python research/kalshi_backtest.py <games_dir>

Rules are judged by realized return per $1 staked (after Kalshi's taker fee of
0.07 x P x (1-P) per contract when buying at the ask; no fee when resting at the bid),
with a standard error, by sport and by period. "In-sample" = games before 2026-07-01
(Kalshi's 2025-26 seasons); "out-of-sample" = games from 2026-07-01 on (the current
seasons), which are only looked at after a rule has been chosen on the earlier data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.kalshi_games import load, maker_fee, taker_fee  # noqa: E402

SPLIT = pd.Timestamp("2026-07-01", tz="UTC")
SPORT = {"KXNFLGAME": "NFL", "KXNCAAFGAME": "College FB", "KXNBAGAME": "NBA", "KXWNBAGAME": "WNBA",
         "KXNHLGAME": "NHL", "KXMLBGAME": "MLB"}


def settle(df: pd.DataFrame, price_col: str, fee: bool) -> pd.Series:
    """Profit per $1 staked buying this side at `price_col` (fee added to cost when taking)."""
    p = df[price_col]
    cost = p + (taker_fee(p) if fee else 0.0)
    return np.where(df["won"], 1.0 / cost - 1.0, -1.0)


def summarize(df: pd.DataFrame, pnl: np.ndarray, label: str) -> dict:
    pnl = np.asarray(pnl, dtype=float)
    n = len(pnl)
    return {"rule": label, "bets": n, "win_rate": float(df["won"].mean()) if n else np.nan,
            "avg_price": float(df["_p"].mean()) if n else np.nan,
            "roi": float(pnl.mean()) if n else np.nan,
            "se": float(pnl.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan}


def calibration(df: pd.DataFrame, col: str = "mid_0") -> pd.DataFrame:
    d = df.dropna(subset=[col])
    d = d.assign(bucket=pd.cut(d[col], [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]))
    return d.groupby("bucket", observed=True).agg(n=("won", "size"), price=(col, "mean"), won=("won", "mean"))


def bucket_returns(df: pd.DataFrame, when: str = "0") -> pd.DataFrame:
    """Return by price bucket for taking (ask + fee) and making (bid, no fee) at snapshot `when`."""
    d = df.dropna(subset=[f"mid_{when}"]).copy()
    d["bucket"] = pd.cut(d[f"mid_{when}"], [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1])
    d["take"] = settle(d, f"ask_{when}", fee=True)
    d["make"] = settle(d, f"bid_{when}", fee=False)
    g = d.groupby("bucket", observed=True)
    return g.agg(n=("won", "size"), mid=(f"mid_{when}", "mean"), won=("won", "mean"),
                 take_roi=("take", "mean"), make_roi=("make", "mean"))


def main(games_dir: str) -> None:
    pd.set_option("display.width", 220)
    df = load(Path(games_dir))
    df["sport"] = df["series"].map(SPORT)
    df["period"] = np.where(df["date"] < SPLIT, "2025-26 (in-sample)", "2026-27 (out-of-sample)")
    print(df.groupby(["sport", "period"]).size().unstack(fill_value=0))
    for period, d in df.groupby("period"):
        print(f"\n=== {period}: calibration of the last pre-game midpoint ===")
        print(calibration(d).round(3).to_string())
        print(f"\n=== {period}: return per $1 by price bucket at the start (take = ask + fee, make = bid) ===")
        print(bucket_returns(d).round(3).to_string())


# ---------------------------------------------------------------------------------------
# Strategy rules. Each returns (rows selected, price column used, fee flag).


def rule_table(df: pd.DataFrame) -> pd.DataFrame:
    """Every rule, evaluated per period and sport. A rule is only trusted if it is positive
    in-sample AND out-of-sample with a return larger than ~2 standard errors."""
    rows = []
    d0 = df.dropna(subset=["mid_0", "ask_0", "bid_0"])
    tests = []
    # 1. Price-level rules at the last pre-game snapshot (taking the ask, paying the fee)
    for lo, hi, name in ((0.0, 0.2, "buy longshots < 20c"), (0.2, 0.4, "buy 20-40c"), (0.4, 0.6, "buy coin flips 40-60c"),
                         (0.6, 0.8, "buy favorites 60-80c"), (0.8, 0.95, "buy heavy favorites 80-95c")):
        tests.append((name, d0[(d0.mid_0 > lo) & (d0.mid_0 <= hi)], "ask_0", True))
    # 2. Same picks resting a bid instead of taking (upper bound: assumes the bid fills)
    tests.append(("rest a bid on favorites 60-95c (if filled)", d0[(d0.mid_0 > .6) & (d0.mid_0 <= .95)], "bid_0", False))
    # 3. Timing: buy the same side 12 hours early instead of at the start
    d12 = df.dropna(subset=["mid_12", "ask_12", "mid_0"])
    tests.append(("buy every side 12h early", d12, "ask_12", True))
    tests.append(("buy every side at the start", d12, "ask_0", True))
    # 4. Momentum: the side whose price rose >= 4c between 12h and 1h before start, bought at 1h
    d1 = df.dropna(subset=["mid_12", "mid_1", "ask_1"])
    tests.append(("follow the move (rose 4c+ from 12h to 1h)", d1[(d1.mid_1 - d1.mid_12) >= 0.04], "ask_1", True))
    tests.append(("fade the move (fell 4c+ from 12h to 1h)", d1[(d1.mid_1 - d1.mid_12) <= -0.04], "ask_1", True))
    for name, sel, col, fee in tests:
        for (period, sport), d in sel.groupby(["period", "sport"]):
            d = d.assign(_p=d[col])
            rows.append(dict(summarize(d, settle(d, col, fee), name), period=period, sport=sport))
        for period, d in sel.groupby("period"):
            d = d.assign(_p=d[col])
            rows.append(dict(summarize(d, settle(d, col, fee), name), period=period, sport="ALL"))
    return pd.DataFrame(rows)


def resting_bid_sim(df: pd.DataFrame, cents_below: float = 0.0, lo: float = 0.0, hi: float = 1.0) -> pd.DataFrame:
    """Realistic maker test: post a bid at (12h bid - cents_below) and keep it until the start.
    It fills only if some later hourly trade prints at or below that price (adverse selection
    included: fills happen when the price is falling). Filled bids pay the maker fee.
    Only sides whose 12h bid is in [lo, hi) are quoted."""
    out = []
    for r in df.dropna(subset=["bid_12", "mid_0"]).itertuples():
        if not lo <= r.bid_12 < hi:
            continue
        limit = r.bid_12 - cents_below
        lasts = [getattr(r, f"last_{h}") for h in (6, 3, 1, 0)]
        filled = any((x is not None) and (not np.isnan(x)) and x <= limit for x in lasts)
        out.append({"period": r.period, "sport": r.sport, "filled": filled, "won": r.won, "limit": limit})
    o = pd.DataFrame(out)
    cost = o["limit"] + maker_fee(o["limit"])
    o["pnl"] = np.where(o["filled"], np.where(o["won"], 1 / cost - 1, -1.0), np.nan)
    return (o[o.filled].groupby(["period", "sport"]).agg(fills=("pnl", "size"), roi=("pnl", "mean"),
                                                        se=("pnl", lambda x: x.std(ddof=1) / np.sqrt(len(x))))
            .join(o.groupby(["period", "sport"])["filled"].mean().rename("fill_rate")))


def run_rules(games_dir: str) -> None:
    pd.set_option("display.width", 220)
    df = load(Path(games_dir))
    df["sport"] = df["series"].map(SPORT)
    df["period"] = np.where(df["date"] < SPLIT, "in-sample 2025-26", "out-of-sample 2026-27")
    t = rule_table(df)
    t = t[t.bets >= 30]
    print(t[t.sport == "ALL"].sort_values(["rule", "period"]).round(4).to_string(index=False))
    print("\nBy sport:")
    print(t[t.sport != "ALL"].sort_values(["rule", "sport", "period"]).round(4).to_string(index=False))
    for lo, hi, below in ((0.0, 1.0, 0.0), (0.6, 0.95, 0.0), (0.6, 0.95, 0.02), (0.05, 0.4, 0.0)):
        print(f"\nResting-bid simulation: sides with a 12h bid in {lo:.2f}-{hi:.2f}, "
              f"bid placed {below * 100:.0f}c under it, maker fee included:")
        print(resting_bid_sim(df, below, lo, hi).round(4).to_string())


if __name__ == "__main__":
    main(sys.argv[1])
    run_rules(sys.argv[1])
