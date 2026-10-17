"""Play a rule's bets in date order with real stakes: flat $20 and fractional Kelly.

Used on whatever survives the backtests. Each bet needs: time, cost per contract (price + fee)
and whether it won. Kelly needs a win probability; we use the rule's in-sample win rate for its
price band (never the outcome itself), so the sizing is something a trader could have known.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def flat(bets: pd.DataFrame, stake: float = 20.0) -> dict:
    b = bets.sort_values("t")
    pnl = np.where(b["won"], stake * (1 / b["cost"] - 1), -stake)
    curve = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.concatenate([[0.0], curve]))[1:]
    streak = run = 0
    for w in b["won"]:
        run = 0 if w else run + 1
        streak = max(streak, run)
    return {"bets": len(b), "staked": stake * len(b), "profit": float(curve[-1]) if len(b) else 0.0,
            "roi": float(pnl.mean() / stake) if len(b) else np.nan, "max_drawdown": float((peak - curve).max()) if len(b) else 0.0,
            "longest_losing_streak": streak}


def kelly(bets: pd.DataFrame, p_col: str = "p_est", bankroll: float = 500.0, frac: float = 0.25,
          cap: float = 0.05) -> dict:
    """Stake frac * Kelly of the current bankroll (capped at `cap` of it) on each bet."""
    b = bets.sort_values("t")
    bank, low = bankroll, bankroll
    for r in b.itertuples():
        odds = 1 / r.cost - 1  # net payout per $1
        f = max(0.0, (getattr(r, p_col) * (odds + 1) - 1) / odds) * frac
        stake = min(f, cap) * bank
        bank += stake * odds if r.won else -stake
        low = min(low, bank)
    return {"start": bankroll, "end": round(bank, 2), "lowest": round(low, 2), "kelly_fraction": frac}
