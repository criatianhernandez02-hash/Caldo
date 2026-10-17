"""Pull live Sleeper Picks lines (with payout multipliers) and injury statuses.

Uses the endpoints the Sleeper app itself calls. `lines/available` is undocumented, so it
can change without notice; the player database is Sleeper's public API, which asks callers
to fetch it at most once a day (it is cached for 24h here).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .data import DEFAULT_CACHE

LINES_URL = "https://api.sleeper.app/lines/available"
PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
HEADERS = {"User-Agent": "Mozilla/5.0 (tdmodel)"}

WAGER_TO_MARKET = {"anytime_touchdowns": "anytime_td", "passing_touchdowns": "pass_tds"}
SIDE = {"over": "more", "under": "less"}
SKIP_STATUSES = {"Out", "Doubtful", "IR", "PUP", "Sus", "NA", "COV"}


def load_players(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> dict:
    path = cache_dir / "sleeper_players_nfl.json"
    if refresh or not path.exists() or time.time() - path.stat().st_mtime > 24 * 3600:
        resp = requests.get(PLAYERS_URL, headers=HEADERS, timeout=120)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    return json.loads(path.read_text())


def fetch_raw_lines() -> list[dict]:
    resp = requests.get(LINES_URL, headers=HEADERS, timeout=60,
                        params={"dynamic": "true", "include_pregame": "true"})
    resp.raise_for_status()
    return resp.json()


def parse_lines(raw: list[dict], players: dict) -> pd.DataFrame:
    """One row per pickable side: player, market, line, side, multiplier (+ ids, injury)."""
    rows = []
    for mkt in raw:
        if mkt.get("sport") != "nfl" or mkt.get("status") != "active":
            continue
        market = WAGER_TO_MARKET.get(mkt.get("wager_type"))
        if market is None or mkt.get("game_status") != "pre_game":
            continue
        info = players.get(str(mkt.get("subject_id")), {})
        for opt in mkt.get("options", []):
            if opt.get("status") != "active" or opt.get("outcome") not in SIDE:
                continue
            rows.append({
                "player": info.get("full_name") or opt.get("subject_id"),
                "player_id": info.get("gsis_id"),
                "market": market,
                "line": float(opt["outcome_value"]),
                "side": SIDE[opt["outcome"]],
                "multiplier": float(opt["payout_multiplier"]),
                "line_type": opt.get("line_type", "normal"),
                "injury_status": info.get("injury_status"),
            })
    cols = ["player", "player_id", "market", "line", "side", "multiplier", "line_type", "injury_status"]
    return pd.DataFrame(rows, columns=cols)


def fetch_lines(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> pd.DataFrame:
    return parse_lines(fetch_raw_lines(), load_players(cache_dir, refresh))


def injury_report(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> pd.DataFrame:
    """gsis_id -> Sleeper injury status, for every NFL player that has one."""
    players = load_players(cache_dir, refresh)
    rows = [{"player_id": p.get("gsis_id"), "injury_status": p.get("injury_status")}
            for p in players.values() if p.get("gsis_id") and p.get("injury_status")]
    return pd.DataFrame(rows, columns=["player_id", "injury_status"])


PROMOS_URL = "https://api.sleeper.app/lines/promos"


def parse_promos(raw: list[dict], players: dict, sport: str = "nfl") -> pd.DataFrame:
    """Promo lines next to the regular line for the same prop, with an expected-value estimate.

    Same line, boosted multiplier: EV = fair P(side) from the de-vigged regular line x promo
    multiplier - 1 (exact up to the regular line's own error).
    Discounted line (e.g. passing yards More 0.5 instead of 227.5): the promo side is at least as
    likely as at the regular line, so EV >= fair P(regular) x promo multiplier - 1; huge discounts
    are near-certain and worth far more than that floor.
    """
    regular, promos = {}, []
    for mkt in raw:
        if mkt.get("sport") != sport or mkt.get("status") != "active":
            continue
        opts = {o["outcome"]: o for o in mkt.get("options", []) if o.get("status") == "active"}
        if "over" not in opts or "under" not in opts:
            continue
        key = (str(mkt.get("subject_id")), mkt.get("wager_type"))
        if mkt.get("line_type") == "normal":
            regular[key] = opts
        else:
            promos.append((key, mkt.get("line_type"), opts))
    rows = []
    for key, line_type, opts in promos:
        reg = regular.get(key)
        info = players.get(key[0], {})
        for side, other in (("over", "under"), ("under", "over")):
            o = opts[side]
            row = {"player": info.get("full_name") or key[0], "team": info.get("team"), "prop": key[1],
                   "side": SIDE[side], "line": float(o["outcome_value"]), "multiplier": float(o["payout_multiplier"]),
                   "promo": (o.get("metadata") or {}).get("promotion_type") or line_type,
                   "free_pick": bool((o.get("metadata") or {}).get("display_as_free_pick")),
                   "regular_line": np.nan, "regular_multiplier": np.nan, "ev_estimate": np.nan, "ev_is_floor": False}
            if reg:
                r_line = float(reg[side]["outcome_value"])
                imp = 1 / float(reg[side]["payout_multiplier"])
                fair = imp / (imp + 1 / float(reg[other]["payout_multiplier"]))
                easier = row["line"] < r_line if side == "over" else row["line"] > r_line
                row.update(regular_line=r_line, regular_multiplier=float(reg[side]["payout_multiplier"]))
                if row["line"] == r_line:
                    row["ev_estimate"] = fair * row["multiplier"] - 1
                elif easier:
                    row["ev_estimate"], row["ev_is_floor"] = fair * row["multiplier"] - 1, True
                    if side == "over" and row["line"] <= 0.1 * r_line:
                        row["promo"] = "line_discount (near-certain)"
                else:
                    continue  # the side made harder by a line discount is never the promo
            rows.append(row)
    return pd.DataFrame(rows)


def fetch_promos(cache_dir: Path = DEFAULT_CACHE, refresh: bool = False) -> pd.DataFrame:
    resp = requests.get(PROMOS_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    return parse_promos(resp.json(), load_players(cache_dir, refresh))
