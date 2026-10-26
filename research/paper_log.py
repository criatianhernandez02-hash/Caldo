"""Paper-trade log for the player-under rule: record picks, grade them, and measure closing line value.

    python research/paper_log.py add research/out/props_scan_<date>.csv [--stake 20]
    python research/paper_log.py grade
    python research/paper_log.py summary

The log lives in research/paper_trades.csv (committed, so the track record survives sessions).
`add` appends a scan's picks with the price at the time of the scan. `grade` fills in, for picks
whose game has started, Kalshi's settlement and the closing price (the last quote at or before
kickoff). `summary` reports, overall / by week / clean vs flagged picks:
  - record and profit at a flat stake (fees included)
  - CLV: closing NO midpoint minus the NO price we got, in cents. Positive = the market moved
    toward our side after we bet - the fastest honest signal that a pick was good (Unabated's
    "track your CLV" rule), needing far fewer bets than wins and losses.
  - closing-line EV: what the bet was worth at the closing price (close NO mid / our cost - 1)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.fetch_kalshi_games import get, slim  # noqa: E402

LOG = Path(__file__).resolve().parent / "paper_trades.csv"
COLS = ["logged_at", "week", "game_id", "kickoff", "ticker", "player", "stat", "line", "side", "entry_price",
        "entry_cost", "contracts", "stake", "formula_p_side", "kalshi_mid_at_entry", "edge", "news", "group",
        "result", "won", "profit", "close_side_mid", "clv_cents", "close_ev"]


def load() -> pd.DataFrame:
    log = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=COLS)
    for c in ("result", "won", "news", "group"):
        log[c] = log[c].astype(object)
    return log


def add(scan_csv: str, stake: float = 20.0) -> None:
    p = pd.read_csv(scan_csv)
    p["news"] = p.get("news", pd.Series("", index=p.index)).fillna("")
    logged = pd.Timestamp.now(tz="UTC").isoformat(timespec="minutes")
    rows = pd.DataFrame({
        "logged_at": logged, "week": p["game_id"].str[:7], "game_id": p["game_id"], "kickoff": p["kickoff"],
        "ticker": p["ticker"], "player": p["name"], "stat": p["stat"], "line": (p["strike"] + 0.5).astype(int),
        "side": "NO", "entry_price": p["no_ask"], "entry_cost": p["no_cost"],
        "contracts": np.floor(stake / p["no_cost"]).astype(int), "stake": stake,
        "formula_p_side": 1 - p["p_over"], "kalshi_mid_at_entry": 1 - (p["yes_bid"] + p["yes_ask"]) / 2,
        "edge": p["edge"], "news": p["news"],
        "group": np.where(p["news"] == "", "clean", np.where(p["news"].str.contains("no injury report"), "no report yet", "flagged")),
    })
    log = load()
    rows = rows[~rows["ticker"].isin(log["ticker"])]  # a market is logged once, at its first scan
    out = pd.concat([log, rows], ignore_index=True)[COLS]
    out.to_csv(LOG, index=False)
    print(f"added {len(rows)} picks ({(rows['group'] == 'clean').sum()} clean); log has {len(out)}")


def market_result(ticker: str) -> str | None:
    for path in (f"/markets/{ticker}", f"/historical/markets/{ticker}"):
        r = get(path, {})
        if r.ok:
            return r.json().get("market", {}).get("result") or None
    return None


def closing_mids(rows: pd.DataFrame) -> dict:
    """YES midpoint of the last hourly quote at or before kickoff, per ticker."""
    out = {}
    for kick, g in rows.groupby("kickoff"):
        tickers = g["ticker"].tolist()
        for i in range(0, len(tickers), 100):
            chunk = tickers[i:i + 100]
            r = get("/markets/candlesticks", {"market_tickers": ",".join(chunk), "start_ts": int(kick) - 4 * 3600,
                                              "end_ts": int(kick), "period_interval": 60})
            if not r.ok:
                continue
            for m in r.json().get("markets", []):
                cs = [slim(c) for c in m.get("candlesticks", [])]
                cs = [c for c in cs if c["t"] <= kick and c["bid"] is not None and c["ask"] is not None]
                if cs:
                    last = max(cs, key=lambda c: c["t"])
                    out[m["market_ticker"]] = (last["bid"] + last["ask"]) / 2
            time.sleep(0.4)
    return out


def grade() -> None:
    log = load()
    todo = log[log["result"].isna() & (log["kickoff"] < time.time())]
    if todo.empty:
        print("nothing to grade")
        return
    res = {t: market_result(t) for t in todo["ticker"]}
    close = closing_mids(todo)
    for i, r in todo.iterrows():
        result = res.get(r["ticker"])
        if r["ticker"] in close:
            side_close = 1 - close[r["ticker"]] if r["side"] == "NO" else close[r["ticker"]]
            log.at[i, "close_side_mid"] = side_close
            log.at[i, "clv_cents"] = round(100 * (side_close - r["entry_price"]), 1)
            log.at[i, "close_ev"] = side_close / r["entry_cost"] - 1
        if result in ("yes", "no"):
            won = (result == "no") == (r["side"] == "NO")
            log.at[i, "result"], log.at[i, "won"] = result, won
            cost = r["contracts"] * r["entry_cost"]
            log.at[i, "profit"] = round((r["contracts"] - cost) if won else -cost, 2)
    log.to_csv(LOG, index=False)
    print(f"graded {log.loc[todo.index, 'result'].notna().sum()} of {len(todo)} picks")


def summary() -> None:
    log = load()
    g = log[log["result"].notna()].copy()
    if g.empty:
        print("no graded picks yet")
        return
    g["won"] = g["won"].astype(str).str.lower().eq("true")
    g["staked"] = g["contracts"] * g["entry_cost"]

    def block(d: pd.DataFrame) -> dict:
        return {"picks": len(d), "won": int(d["won"].sum()), "win_rate": d["won"].mean(), "staked": d["staked"].sum(),
                "profit": d["profit"].sum(), "roi": d["profit"].sum() / d["staked"].sum(),
                "avg_clv_cents": d["clv_cents"].mean(), "beat_close": (d["clv_cents"] > 0).mean(),
                "close_ev": d["close_ev"].mean()}

    pd.set_option("display.width", 200)
    rows = {"ALL": block(g)}
    rows.update({f"group: {k}": block(d) for k, d in g.groupby("group")})
    rows.update({f"week: {k}": block(d) for k, d in g.groupby("week")})
    print(pd.DataFrame(rows).T.round(3).to_string())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "add":
        add(sys.argv[2], float(sys.argv[sys.argv.index("--stake") + 1]) if "--stake" in sys.argv else 20.0)
    elif cmd == "grade":
        grade()
    else:
        summary()
