"""Paper-trading scanner for the one lead left: buy NO on a player's middle rung when the formula is lower.

    python research/props_scan.py [--edge 0.03] [--stake 20]

Pulls the open Kalshi NFL player ladders (receiving yards, rushing yards, receptions) for games that
have not kicked off, computes the Caldo player formula from each player's history
(nfl_player_yards.py), and lists the middle rung of each ladder where
    formula P(under) - (NO ask + taker fee) >= edge.

Backtest (props_backtest.py, edge 3 points, middle rungs, buying at the ask with the fee): +5.0% per $1
(± 2.7%) over 1,111 bets — 2025 weeks 4-18: +4.0%, 2026 weeks 1-3: +1.3%, weeks 4-6: +10.5% — while
blind NO on the same rungs lost 0.9%. That is about 1.9 standard errors after ~40 tests, and the
edge does not grow at a 5-point threshold, so it is NOT proven: log the picks and check them
before putting money on it.

Before scoring, the scan re-downloads this season's stats, weekly rosters and schedule, and
tells the formula who is out (Out/Doubtful on nflverse's injury report, or not active on the
roster), so the volume of missing teammates is shifted to the players left. Picks are still
flagged when the player is listed, a same-position teammate or the starting QB is out or
questionable, or the player missed recent games: those are the formula's least-tested cases.
Unflagged picks are the cleanest paper trades. Writes research/out/props_scan_<date>.csv.
"""

from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.fetch_kalshi_games import get  # noqa: E402
from research.fetch_kalshi_props import DEFAULT_SERIES, kickoffs, match  # noqa: E402
from research.kalshi_games import taker_fee  # noqa: E402
from research.nfl_player_yards import build, fit_all, norm_name, pregame_absent  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
STAT = {"KXNFLRECYDS": "receiving_yards", "KXNFLRSHYDS": "rushing_yards", "KXNFLREC": "receptions"}
INJURIES_URL = "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv"
LIVE_FILES = {  # refreshed on every scan so the formula sees last week's games and this week's news
    "stats_player_week_{season}.csv": "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv",
    "roster_weekly_{season}.csv": "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_{season}.csv",
    "games.csv": "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
}


def open_markets(series: str) -> list[dict]:
    out, cursor = [], None
    while True:
        params = {"series_ticker": series, "status": "open", "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        r = get("/markets", params)
        r.raise_for_status()
        body = r.json()
        out += body.get("markets", [])
        cursor = body.get("cursor")
        if not cursor:
            return out
        time.sleep(0.5)


def refresh(season: int) -> None:
    """Re-download this season's stats, rosters and the schedule (keeps the cached copy on failure)."""
    for name, url in LIVE_FILES.items():
        path = ROOT / "data_cache" / name.format(season=season)
        try:
            r = requests.get(url.format(season=season), timeout=120)
            r.raise_for_status()
            if len(r.content) > 10_000:
                path.write_bytes(r.content)
        except requests.RequestException as e:
            print(f"(could not refresh {path.name}: {e}; using the cached copy)")


def ruled_out(season: int, inj: pd.DataFrame) -> dict:
    """(week, team) -> name keys not available: Out/Doubtful on the injury report, or anything but
    ACT on the weekly roster (game-day inactives once posted, IR, cut, traded)."""
    out: dict = {}
    for r in inj[inj["report_status"].isin(["Out", "Doubtful"])].itertuples():
        out.setdefault((int(r.week), r.team), set()).add(r.name_key)
    path = ROOT / "data_cache" / f"roster_weekly_{season}.csv"
    if path.exists():
        ros = pd.read_csv(path, usecols=["week", "team", "full_name", "status"], low_memory=False)
        for r in ros[ros["status"] != "ACT"].itertuples():
            out.setdefault((int(r.week), r.team), set()).add(norm_name(r.full_name))
    return out


def injuries(season: int) -> pd.DataFrame:
    path = ROOT / "data_cache" / f"injuries_{season}.csv"
    try:
        r = requests.get(INJURIES_URL.format(season=season), timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
    except requests.RequestException as e:
        if not path.exists():
            print(f"(no injury report available: {e})")
            return pd.DataFrame(columns=["team", "week", "position", "full_name", "report_status"])
    inj = pd.read_csv(path)
    inj = inj[inj["report_status"].notna()].copy()
    inj["name_key"] = inj["full_name"].map(norm_name)
    return inj


def news_flags(picks: pd.DataFrame) -> list[str]:
    """Why the formula might be missing something for each pick (empty when nothing is listed)."""
    season = int(picks["game_id"].str[:4].iloc[0])
    inj = injuries(season)
    reported = set(zip(inj["week"], inj["team"]))
    out = []
    for r in picks.itertuples():
        week = int(r.game_id[5:7])
        if (week, r.team) not in reported:
            out.append("no injury report posted yet")
            continue
        rep = inj[(inj["week"] == week) & (inj["team"] == r.team) & (inj["name_key"] != r.name_key)]
        notes = []
        own = inj[(inj["week"] == week) & (inj["team"] == r.team) & (inj["name_key"] == r.name_key)]
        if len(own):
            notes.append(f"he is listed {own['report_status'].iloc[0]}")
        group, label = (("RB",), "RB") if r.position == "RB" else (("WR", "TE"), "pass catcher") \
            if r.position in ("WR", "TE") else (("QB",), "QB")
        for status in ("Out", "Doubtful", "Questionable"):
            mates = rep[rep["position"].isin(group) & (rep["report_status"] == status)]
            if len(mates):
                notes.append(f"{label} {status.lower()}: " + ", ".join(mates["full_name"].head(2)))
        qb = rep[(rep["position"] == "QB") & rep["report_status"].isin(["Out", "Doubtful"])]
        if len(qb) and r.position != "QB":
            notes.append("QB out: " + qb["full_name"].iloc[0])
        if r.games_missed > 0:
            notes.append(f"missed his team's last {r.games_missed} game(s)")
        out.append("; ".join(notes))
    return out


def f(x) -> float:
    return float(x) if x not in (None, "") else np.nan


def scan(edge: float = 0.03, stake: float = 20.0) -> pd.DataFrame:
    ko, now = kickoffs(), time.time()
    rows = []
    for series in DEFAULT_SERIES:
        for m in open_markets(series):
            hit = match(m["event_ticker"], ko)
            if not hit or hit[1] <= now or m.get("floor_strike") is None:
                continue
            rows.append({"series": series, "stat": STAT[series], "ticker": m["ticker"], "game_id": hit[0],
                         "kickoff": hit[1], "name": (m.get("yes_sub_title") or m["title"]).split(":")[0].strip(),
                         "strike": float(m["floor_strike"]), "yes_bid": f(m.get("yes_bid_dollars")),
                         "yes_ask": f(m.get("yes_ask_dollars")), "no_ask": f(m.get("no_ask_dollars"))})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ladder"] = df["ticker"].str.rsplit("-", n=1).str[0]
    df = df.sort_values(["ladder", "strike"])
    df = df[df.groupby("ladder").cumcount() == (df.groupby("ladder")["strike"].transform("size") - 1) // 2]
    df["name_key"] = df["name"].map(norm_name)

    season = int(df["game_id"].str[:4].iloc[0])
    refresh(season)
    s = build()
    models = fit_all(s)
    feats = pregame_absent(s, df[["game_id", "name_key"]], out=ruled_out(season, injuries(season)))
    out = []
    for stat, m in models.items():
        part = df[df["stat"] == stat].merge(feats.loc[m.usable(feats), ["game_id", "name_key", "position", "team", "games_missed"] + m.features],
                                            on=["game_id", "name_key"])
        if part.empty:
            continue
        part["formula_mean"] = m.mean(part)
        part["p_over"] = m.p_over(part["formula_mean"].to_numpy(), part["strike"].to_numpy())
        out.append(part.drop(columns=m.features))
    d = pd.concat(out, ignore_index=True)
    d["no_ask"] = d["no_ask"].fillna(1 - d["yes_bid"])
    d["no_cost"] = d["no_ask"] + taker_fee(d["no_ask"])
    d["edge"] = (1 - d["p_over"]) - d["no_cost"]
    ok = (d["yes_bid"] > 0) & (d["yes_ask"] - d["yes_bid"] <= 0.10)
    picks = d[ok & (d["edge"] >= edge)].sort_values("edge", ascending=False).copy()
    picks["contracts"] = np.floor(stake / picks["no_cost"]).astype(int)
    picks["news"] = news_flags(picks) if len(picks) else []
    picks["kickoff_et"] = pd.to_datetime(picks["kickoff"], unit="s", utc=True).dt.tz_convert("America/New_York").dt.strftime("%a %H:%M")
    return picks


def main(argv: list[str]) -> None:
    edge = float(argv[argv.index("--edge") + 1]) if "--edge" in argv else 0.03
    stake = float(argv[argv.index("--stake") + 1]) if "--stake" in argv else 20.0
    picks = scan(edge, stake)
    pd.set_option("display.width", 200)
    print("PAPER TRADE ONLY - unproven lead (see docstring). Injury flags use nflverse's report;\n"
          "inactives are announced 90 minutes before kickoff, so re-run close to game time.\n")
    if picks.empty:
        print("No middle rungs clear the edge right now.")
        return
    show = picks.assign(market=picks["name"] + " " + (picks["strike"] + 0.5).astype(int).astype(str) + "+ "
                        + picks["stat"].str.replace("_", " "),
                        kalshi_yes=(picks["yes_bid"] + picks["yes_ask"]) / 2)
    cols = ["kickoff_et", "game_id", "market", "kalshi_yes", "p_over", "formula_mean", "no_ask", "edge", "contracts"]
    clean = show[show["news"] == ""]
    print(f"== No injury news ({len(clean)}): the cleanest paper trades ==")
    print(clean[cols].round(3).to_string(index=False) if len(clean) else "(none)")
    flagged = show[show["news"] != ""]
    print(f"\n== Flagged ({len(flagged)}): role or QB change - the formula now adjusts for who is out, "
          "but these are its least-tested cases; log separately ==")
    print(flagged[cols[:3] + ["edge", "news"]].round(3).to_string(index=False) if len(flagged) else "(none)")
    OUT.mkdir(exist_ok=True)
    path = OUT / f"props_scan_{dt.date.today().isoformat()}.csv"
    picks.to_csv(path, index=False)
    print(f"\n{len(picks)} candidates; buy NO at or below the listed ask. Saved to {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
