"""Turn downloaded Kalshi game markets into a tidy table of pre-game prices and results.

One row per (game, team side) with the yes bid / ask / midpoint at several times before the
game starts, the market's 24h-before and at-start prices, volume and the result.

Kalshi's occurrence_datetime (current markets) and expected_expiration_time (historical
markets) both sit about 3 hours after the actual start in every league checked: hourly volume
and price swings jump in the hour that ends 2 hours before it (NFL, college football, NBA, NHL,
MLB), and NFL kickoffs from the schedule confirm +3h. So start = that time - 3h, and the
"0h" snapshot is the last candle that closed before the game began.

Current-season markets have both teams' order books. Historical markets were fetched for one
side per game; the other side is reconstructed as 1 - price (the two team contracts are
complementary).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

SERIES = ("KXNFLGAME", "KXNCAAFGAME", "KXNBAGAME", "KXWNBAGAME", "KXNHLGAME", "KXMLBGAME")
START_OFFSET_H = 3.0
SNAP_HOURS = (24, 12, 6, 3, 1, 0)
MAX_SPREAD = 0.10


def _ts(iso: str) -> int:
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def _snap(candles: list[dict], t: int) -> dict:
    """Last candle that closed at or before t (prices are 'as of' that time)."""
    best = None
    for c in candles:
        if c["t"] <= t:
            best = c
        else:
            break
    if best is None:
        return {"bid": np.nan, "ask": np.nan, "last": np.nan}
    return {"bid": best["bid"] if best["bid"] is not None else np.nan,
            "ask": best["ask"] if best["ask"] is not None else np.nan,
            "last": best["last"] if best["last"] is not None else np.nan}


def _rows(series: str, markets: list[dict], candle_path: Path, historical: bool) -> list[dict]:
    if not candle_path.exists():
        return []
    candles = {}
    for line in candle_path.open():
        d = json.loads(line)
        candles[d["ticker"]] = sorted(d["candles"], key=lambda c: c["t"])
    by_ticker = {m["ticker"]: m for m in markets}
    events: dict[str, list[dict]] = {}
    for m in markets:
        events.setdefault(m["event_ticker"], []).append(m)
    out = []
    for ticker, cs in candles.items():
        m = by_ticker.get(ticker)
        if not m or m.get("result") not in ("yes", "no") or not cs:
            continue
        ref = m.get("expected_expiration_time") if historical else m.get("occurrence_datetime")
        start = _ts(ref) - int(START_OFFSET_H * 3600)
        base = {"series": series, "event": m["event_ticker"], "start": start, "historical": historical,
                "volume": float(m.get("volume_fp") or 0), "n_sides": len(events.get(m["event_ticker"], []))}
        snaps = {h: _snap(cs, start - h * 3600) for h in SNAP_HOURS}
        first = cs[0]
        sides = [(m["yes_sub_title"], m["result"] == "yes", 1.0)]
        if historical:  # reconstruct the other team's side from this book
            others = [o for o in events.get(m["event_ticker"], []) if o["ticker"] != ticker]
            if len(others) == 1:
                sides.append((others[0]["yes_sub_title"], others[0]["result"] == "yes", -1.0))
        for team, won, sign in sides:
            row = dict(base, team=team, won=won, ticker=ticker if sign > 0 else ticker + "~flip")
            for h, s in snaps.items():
                bid, ask = (s["bid"], s["ask"]) if sign > 0 else (1 - s["ask"], 1 - s["bid"])
                last = s["last"] if sign > 0 else 1 - s["last"]
                ok = (bid > 0) & (ask < 1) & ((ask - bid) <= MAX_SPREAD)
                row[f"bid_{h}"], row[f"ask_{h}"] = bid, ask
                row[f"mid_{h}"] = (bid + ask) / 2 if ok else np.nan
                row[f"last_{h}"] = last
            fb, fa = (first["bid"], first["ask"]) if sign > 0 else (
                1 - first["ask"] if first["ask"] is not None else None, 1 - first["bid"] if first["bid"] is not None else None)
            row["first_t"] = first["t"]
            row["mid_first"] = (fb + fa) / 2 if (fb and fa and 0 < fb and fa < 1 and fa - fb <= MAX_SPREAD) else np.nan
            out.append(row)
    return out


def load(games_dir: Path) -> pd.DataFrame:
    rows = []
    for series in SERIES:
        cur = games_dir / f"{series}_markets.json"
        if cur.exists():
            rows += _rows(series, json.load(cur.open()), games_dir / f"{series}_candles.jsonl", historical=False)
        hist = games_dir / f"{series}_hist_markets.json"
        if hist.exists():
            rows += _rows(series, json.load(hist.open()), games_dir / f"{series}_hist_candles.jsonl", historical=True)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["start"], unit="s", utc=True)
    # drop events that also appear in the current-season pull (the historical copy is redundant)
    cur_events = set(df.loc[~df["historical"], "event"])
    df = df[~(df["historical"] & df["event"].isin(cur_events))]
    return df.reset_index(drop=True)


def taker_fee(p):
    return 0.07 * p * (1 - p)


def maker_fee(p):
    """Kalshi charges resting (maker) orders on the game-line series a quarter of the taker rate."""
    return 0.0175 * p * (1 - p)


if __name__ == "__main__":
    import sys
    d = load(Path(sys.argv[1]))
    print(d.groupby(["series", "historical"]).size())
    print(d[[c for c in d.columns if c.startswith("mid_")]].notna().mean().round(2))
