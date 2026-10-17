"""A simple bet log: record each week's slips, then grade them against final box scores.

Tracking real results is the only way to know whether any approach is working; the
research in this repo found that a season of ~50 slips is still mostly noise, so the log
also reports what the model *expected* to win, for comparison.

One row per leg. Voided legs (player did not play) are dropped from the slip and the payout
is recomputed from the remaining legs' multipliers - check Sleeper's actual rule for your
entry, which may differ.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from .parlay import norm_name

COLS = ["slip_id", "logged_at", "season", "week", "slip", "stake", "slip_prob", "player", "pos", "team",
        "opp", "market", "line", "side", "prob", "multiplier", "kalshi_prob", "leg_result", "slip_result",
        "payout"]


def read(path: str) -> pd.DataFrame:
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame(columns=COLS)


def write(path: str, log: pd.DataFrame) -> None:
    log[COLS].to_csv(path, index=False)


def append(path: str, slips, season: int, week: int) -> int:
    log = read(path)
    start = int(log["slip_id"].max()) + 1 if len(log) else 1
    now = dt.datetime.now().isoformat(timespec="seconds")
    rows = []
    for i, s in enumerate(x for x in slips if len(x.legs)):
        for _, leg in s.legs.iterrows():
            rows.append({"slip_id": start + i, "logged_at": now, "season": season, "week": week,
                         "slip": s.name, "stake": s.stake, "slip_prob": s.prob,
                         "player": str(leg["player"]).replace(" (Q)", ""), "pos": leg["pos"],
                         "team": leg["team"], "opp": leg["opp"], "market": leg["market"], "line": leg["line"],
                         "side": leg["side"], "prob": leg["prob"], "multiplier": leg.get("multiplier", np.nan),
                         "kalshi_prob": leg.get("kalshi_prob", np.nan), "leg_result": "pending",
                         "slip_result": "pending", "payout": np.nan})
    new = pd.DataFrame(rows, columns=COLS)
    write(path, pd.concat([log, new], ignore_index=True) if len(log) else new)
    return new["slip_id"].nunique()


def _leg_result(leg: pd.Series, box: pd.DataFrame, teams_played: set) -> str:
    row = box.get((leg["season"], leg["week"], norm_name(leg["player"]), leg["team"]))
    if row is None:
        return "void" if (leg["season"], leg["week"], leg["team"]) in teams_played else "pending"
    value = row["passing_tds"] if leg["market"] == "pass_tds" else row["rushing_tds"] + row["receiving_tds"]
    hit = value > leg["line"] if leg["side"] == "more" else value < leg["line"]
    return "win" if hit else "loss"


def grade(log: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    log = log.copy()
    box = {(r.season, r.week, norm_name(r.player_display_name), r.team): r
           for r in stats.itertuples(index=False)}
    box = {k: {"passing_tds": v.passing_tds, "rushing_tds": v.rushing_tds, "receiving_tds": v.receiving_tds}
           for k, v in box.items()}
    teams_played = set(zip(stats["season"], stats["week"], stats["team"]))
    log["leg_result"] = [_leg_result(leg, box, teams_played) for _, leg in log.iterrows()]
    for sid, legs in log.groupby("slip_id"):
        res = legs["leg_result"]
        live = legs[res != "void"]
        if (res == "loss").any():
            outcome, payout = "loss", 0.0
        elif (res == "pending").any():
            outcome, payout = "pending", np.nan
        elif live.empty:
            outcome, payout = "refund", legs["stake"].iloc[0]
        else:
            mult = live["multiplier"].prod() if live["multiplier"].notna().all() else np.nan
            outcome, payout = "win", legs["stake"].iloc[0] * mult
        log.loc[legs.index, "slip_result"] = outcome
        log.loc[legs.index, "payout"] = payout
    return log


def summary(log: pd.DataFrame) -> str:
    slips = log.drop_duplicates("slip_id")
    done = slips[slips["slip_result"] != "pending"]
    lines = [f"{len(slips)} slips logged, {len(done)} graded, {len(slips) - len(done)} pending."]
    legs = log[log["leg_result"].isin(["win", "loss"])]
    if len(legs):
        lines.append(f"Legs: {(legs['leg_result'] == 'win').mean():.0%} hit "
                     f"(model expected {legs['prob'].mean():.0%}) over {len(legs)} graded legs.")
    if len(done):
        lines.append(f"Slips: {(done['slip_result'] == 'win').sum()} won of {len(done)} "
                     f"(model expected {done['slip_prob'].sum():.1f} wins).")
        unknown = (done["slip_result"] == "win") & done["payout"].isna()
        if unknown.any():
            lines.append(f"({unknown.sum()} winning slips have no logged multipliers, so their payout is unknown; "
                         "log with --sleeper or --lines to track money.)")
        known = done[~unknown]
        staked, returned = known["stake"].sum(), known["payout"].fillna(0).sum()
        if staked:
            lines.append(f"Staked ${staked:,.2f}, returned ${returned:,.2f}, profit ${returned - staked:+,.2f} "
                         f"({(returned - staked) / staked:+.1%})" + (" on slips with known payouts." if unknown.any() else "."))
        by = done.groupby(done["slip"].str.extract(r"(\d+)-leg")[0].fillna("?") + "-leg")
        for k, g in by:
            unk = ((g["slip_result"] == "win") & g["payout"].isna()).any()
            profit = "profit unknown" if unk else f"profit ${g['payout'].fillna(0).sum() - g['stake'].sum():+,.2f}"
            lines.append(f"   {k:>6}: {len(g)} slips, won {(g['slip_result'] == 'win').sum()}, {profit}")
    return "\n".join(lines)
