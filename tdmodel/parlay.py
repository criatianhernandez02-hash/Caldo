"""Turn projections into Sleeper-style legs and build parlays from them.

A leg is one pick: e.g. "Jahmyr Gibbs - Rush+Rec TDs - More than 0.5".
Without a lines file the candidate legs are:
  * Anytime TD (Rush+Rec TDs more than 0.5) for RB / WR / TE
  * Pass TDs more / less than 1.5 for each starting QB
With a lines file (what Sleeper actually offers this week, optionally with the per-pick
multipliers it shows) only those legs are used and expected value can be computed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .model import poisson_sf

MARKET_LAMBDA = {"anytime_td": "lam_td", "rush_rec_tds": "lam_td", "pass_tds": "lam_pass_td"}
MARKET_LABEL = {"anytime_td": "Rush+Rec TDs", "rush_rec_tds": "Rush+Rec TDs", "pass_tds": "Pass TDs"}


def norm_name(name: str) -> str:
    name = re.sub(r"[^a-z ]", "", str(name).lower().replace("-", " "))
    return " ".join(w for w in name.split() if w not in {"jr", "sr", "ii", "iii", "iv", "v"})


def _leg(row: pd.Series, market: str, line: float, side: str, prob: float, mult: float = np.nan) -> dict:
    return {
        "player": row["name"], "pos": row["pos"], "team": row["team"], "opp": row["opp"],
        "game_id": row["game_id"], "total": row["total"], "market": market, "line": line,
        "side": side, "prob": float(prob), "multiplier": mult,
    }


def default_legs(proj: pd.DataFrame) -> pd.DataFrame:
    legs = []
    for _, r in proj.iterrows():
        if r["pos"] == "QB":
            p = r["p_pass_over_1.5"]
            legs.append(_leg(r, "pass_tds", 1.5, "more", p))
            legs.append(_leg(r, "pass_tds", 1.5, "less", 1 - p))
        else:
            legs.append(_leg(r, "anytime_td", 0.5, "more", r["p_anytime_td"]))
    return pd.DataFrame(legs)


def load_lines(path: str) -> pd.DataFrame:
    """CSV columns: player, market, line, side[, multiplier].

    market: anytime_td | rush_rec_tds | pass_tds     side: more | less
    multiplier: the per-pick payout Sleeper shows for that side (optional).
    """
    lines = pd.read_csv(path)
    lines.columns = [c.strip().lower() for c in lines.columns]
    missing = {"player", "market", "line", "side"} - set(lines.columns)
    if missing:
        raise ValueError(f"lines file is missing columns: {sorted(missing)}")
    if "multiplier" not in lines.columns:
        lines["multiplier"] = np.nan
    lines["market"] = lines["market"].str.strip().str.lower()
    lines["side"] = lines["side"].str.strip().str.lower()
    bad = set(lines["market"]) - set(MARKET_LAMBDA)
    if bad:
        raise ValueError(f"unknown market(s) {sorted(bad)}; use one of {sorted(MARKET_LAMBDA)}")
    return lines


def legs_from_lines(proj: pd.DataFrame, lines: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Price each line with the model. Matches on nflverse player_id when the lines carry
    one (the Sleeper feed does), otherwise on the player's name."""
    by_name = {norm_name(n): i for i, n in proj["name"].items()}
    by_id = {pid: i for i, pid in proj["player_id"].items()} if "player_id" in proj else {}
    legs, unmatched = [], []
    for _, ln in lines.iterrows():
        if ln["market"] in ("anytime_td", "rush_rec_tds") and idx_is_qb(proj, by_id, by_name, ln):
            continue  # QB rushing TDs are not modelled well enough (never backtested)
        idx = by_id.get(ln.get("player_id")) if pd.notna(ln.get("player_id")) else None
        if idx is None:
            idx = by_name.get(norm_name(ln["player"]))
        lam = proj.at[idx, MARKET_LAMBDA[ln["market"]]] if idx is not None else np.nan
        if idx is None or pd.isna(lam):
            unmatched.append(str(ln["player"]))
            continue
        p_more = poisson_sf(lam, float(ln["line"]))
        prob = p_more if ln["side"] == "more" else 1 - p_more
        legs.append(_leg(proj.loc[idx], ln["market"], float(ln["line"]), ln["side"], prob, ln["multiplier"]))
    return pd.DataFrame(legs), unmatched


def idx_is_qb(proj: pd.DataFrame, by_id: dict, by_name: dict, ln: pd.Series) -> bool:
    idx = by_id.get(ln.get("player_id")) if pd.notna(ln.get("player_id")) else None
    idx = idx if idx is not None else by_name.get(norm_name(ln["player"]))
    return idx is not None and proj.at[idx, "pos"] == "QB"


@dataclass
class Slip:
    name: str
    legs: pd.DataFrame
    stake: float
    prob: float = field(init=False)
    fair_multiplier: float = field(init=False)
    multiplier: float = field(init=False)

    def __post_init__(self):
        self.prob = float(np.prod(self.legs["prob"])) if len(self.legs) else 0.0
        self.fair_multiplier = 1 / self.prob if self.prob > 0 else math.inf
        m = self.legs["multiplier"] if len(self.legs) else pd.Series(dtype=float)
        self.multiplier = float(np.prod(m)) if len(m) and m.notna().all() else np.nan

    @property
    def expected_return(self) -> float:
        return self.stake * self.multiplier * self.prob if not np.isnan(self.multiplier) else np.nan


def build_slip(legs: pd.DataFrame, n: int, mode: str = "safe", exclude_players: set | None = None,
               max_per_team: int = 1, max_per_game: int = 2) -> pd.DataFrame:
    """Greedy pick of n legs.

    mode="safe":     highest win probability (any side).
    mode="longshot": touchdown "more" legs only, ranked by probability (legs below the
                     edge threshold are already filtered out by weekly_card).
    At most `max_per_team` legs per team keeps one bad offensive game from sinking several
    legs at once (legs on the same team are correlated).
    """
    exclude_players = exclude_players or set()
    pool = legs[~legs["player"].isin(exclude_players)].copy()
    if mode == "longshot":
        pool = pool[pool["side"] == "more"]
    pool = pool.sort_values("prob", ascending=False)

    chosen, teams, games_used, players = [], {}, {}, set()
    for _, leg in pool.iterrows():
        if leg["player"] in players:
            continue
        if teams.get(leg["team"], 0) >= max_per_team or games_used.get(leg["game_id"], 0) >= max_per_game:
            continue
        chosen.append(leg)
        players.add(leg["player"])
        teams[leg["team"]] = teams.get(leg["team"], 0) + 1
        games_used[leg["game_id"]] = games_used.get(leg["game_id"], 0) + 1
        if len(chosen) == n:
            break
    return pd.DataFrame(chosen).reset_index(drop=True)


DEFAULT_PLAN = [("Anchor", 3, "safe"), ("Core", 5, "safe"), ("Longshot", 8, "longshot")]


def weekly_card(legs: pd.DataFrame, stake: float = 20.0, plan=DEFAULT_PLAN, overlap: bool = False,
                overs_only: bool = False, min_edge: float | None = 0.0) -> list[Slip]:
    """Build the weekend's slips. By default no player appears in two slips, so one
    player's dud game can't bust the whole card.

    When legs carry Sleeper multipliers, legs whose model edge (prob x multiplier - 1) is
    below `min_edge` are dropped: a leg the model thinks is overpriced makes every parlay
    it is in worse. Pass min_edge=None to keep them."""
    if overs_only:
        legs = legs[legs["side"] == "more"]
    if min_edge is not None and legs["multiplier"].notna().any():
        edge = legs["prob"] * legs["multiplier"] - 1
        legs = legs[legs["multiplier"].isna() | (edge >= min_edge)]
    used: set = set()
    slips = []
    for name, n, mode in plan:
        chosen = build_slip(legs, n, mode, exclude_players=None if overlap else used)
        label = f"{name} ({n}-leg)" if len(chosen) == n else \
            f"{name} ({n}-leg wanted, only {len(chosen)} eligible legs - add more lines or use --overlap)"
        slips.append(Slip(label, chosen, stake))
        used |= set(chosen["player"]) if len(chosen) else set()
    return slips
