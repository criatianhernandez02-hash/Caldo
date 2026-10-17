"""Are near-certain winners underpriced late in games? (Kalshi game markets, 1-minute data)

    python research/endgame_backtest.py <games_dir>

Rule a live trader can follow (no look-ahead): from a fixed time into the game (T minutes
after the estimated start, set per sport so it lands late in the game), take the FIRST
minute in which a side's ask enters a price band (with a tight spread), buy it at the ask plus
the taker fee, and hold to settlement. Every band is reported by sport.

Why not "k minutes before close": Kalshi closes a game market a median ~21 minutes after the
game is decided (checked on NHL), so close-relative snapshots often fall after the final
whistle and leak the result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.kalshi_games import taker_fee  # noqa: E402
from research.fetch_kalshi_games import ts  # noqa: E402

SPORT = {"KXNFLGAME": "NFL", "KXNCAAFGAME": "College FB", "KXNBAGAME": "NBA", "KXNHLGAME": "NHL", "KXMLBGAME": "MLB"}
# minutes after the estimated start (Kalshi time - 3h) from which the rule watches prices
LATE_T = {"NHL": 110, "NBA": 110, "MLB": 150, "NFL": 160, "College FB": 170}
BANDS = ((0.70, 0.85), (0.85, 0.92), (0.92, 0.96), (0.96, 0.985))


def load(games_dir: Path) -> pd.DataFrame:
    """One row per (side, band): the first late-game minute whose ask entered the band."""
    rows = []
    for series, sport in SPORT.items():
        mp, ep = games_dir / f"{series}_markets.json", games_dir / f"{series}_endgame.jsonl"
        if not (mp.exists() and ep.exists()):
            continue
        meta = {m["ticker"]: m for m in json.load(mp.open())}
        for line in ep.open():
            d = json.loads(line)
            m = meta.get(d["ticker"])
            if not m or not m.get("occurrence_datetime"):
                continue
            t0 = ts(m["occurrence_datetime"]) - 3 * 3600 + LATE_T[sport] * 60
            cs = sorted(d["candles"], key=lambda c: c["t"])
            if not cs or cs[0]["t"] > t0:  # our 1-minute window must already cover the trigger time
                continue
            for lo, hi in BANDS:
                for c in cs:
                    if c["t"] < t0 or c["ask"] is None or c["bid"] is None:
                        continue
                    if lo <= c["ask"] < hi and c["ask"] - c["bid"] <= 0.05 and c["bid"] > 0:
                        rows.append({"sport": sport, "ticker": d["ticker"], "band": f"{lo:.2f}-{hi:.3f}",
                                     "bid": c["bid"], "ask": c["ask"], "won": m["result"] == "yes",
                                     "mins_in": (c["t"] - (t0 - LATE_T[sport] * 60)) / 60,
                                     "season": "2026-27 (current)"})
                        break
    rows += load_historical(games_dir)
    return pd.DataFrame(rows)


def load_historical(games_dir: Path) -> list[dict]:
    """Older-season games (fetch_kalshi_endgame.py --historical): one side was downloaded;
    the other team's side is rebuilt as 1 - price (complementary contracts)."""
    rows = []
    for series, sport in SPORT.items():
        mp, ep = games_dir / f"{series}_hist_markets.json", games_dir / f"{series}_hist_endgame.jsonl"
        if not (mp.exists() and ep.exists()):
            continue
        meta = {m["ticker"]: m for m in json.load(mp.open())}
        by_event = {}
        for m in meta.values():
            by_event.setdefault(m["event_ticker"], []).append(m)
        for line in ep.open():
            d = json.loads(line)
            m = meta.get(d["ticker"])
            if not m:
                continue
            others = [o for o in by_event.get(m["event_ticker"], []) if o["ticker"] != m["ticker"]]
            t0 = d["start"] + LATE_T[sport] * 60
            cs = sorted(d["candles"], key=lambda c: c["t"])
            sides = [(d["ticker"], m["result"] == "yes", False)]
            if len(others) == 1:
                sides.append((others[0]["ticker"], others[0]["result"] == "yes", True))
            for ticker, won, flip in sides:
                for lo, hi in BANDS:
                    for c in cs:
                        if c["t"] < t0 or c["ask"] is None or c["bid"] is None:
                            continue
                        bid, ask = (1 - c["ask"], 1 - c["bid"]) if flip else (c["bid"], c["ask"])
                        if lo <= ask < hi and ask - bid <= 0.05 and bid > 0:
                            rows.append({"sport": sport, "ticker": ticker, "band": f"{lo:.2f}-{hi:.3f}", "bid": bid,
                                         "ask": ask, "won": won, "mins_in": (c["t"] - d["start"]) / 60,
                                         "season": "2025-26 (historical)"})
                            break
    return rows


def main(games_dir: str) -> None:
    pd.set_option("display.width", 200)
    df = load(Path(games_dir))
    print("late-game entries:", len(df), df.groupby("sport").ticker.nunique().to_dict())
    rows = []
    for keys, b in df.groupby(["season", "sport", "band"]):
        cost = b.ask + taker_fee(b.ask)
        pnl = np.where(b.won, 1 / cost - 1, -1.0)
        rows.append({"season": keys[0], "sport": keys[1], "band": keys[2], "bets": len(b), "avg_ask": b.ask.mean(),
                     "won": b.won.mean(), "roi": pnl.mean(),
                     "se": pnl.std(ddof=1) / np.sqrt(len(b)) if len(b) > 1 else np.nan,
                     "avg_min_into_game": b.mins_in.mean()})
    print(pd.DataFrame(rows).round(4).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
