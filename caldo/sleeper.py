"""Sleeper integration: player-ID mapping and league snapshots.

Sleeper's API (https://docs.sleeper.com) is public and read-only; no login or
token is needed. The web app calls it live from the browser. This module
handles what is better done ahead of time: mapping Sleeper player IDs onto the
nflverse IDs the model uses, and saving a league snapshot to bundle into a
page that cannot reach the internet itself (the claude.ai artifact).
"""
import json
import re
import urllib.request

import pandas as pd

from .config import RAW_DIR

API = "https://api.sleeper.app/v1"
CROSSWALK = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_playerids.csv"
TEAM_FIX = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS"}


def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "caldo-trade-calculator"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def players(refresh=False):
    """Sleeper's full player directory (~15 MB), cached under data/raw."""
    path = RAW_DIR / "sleeper_players.json"
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(get("/players/nfl")))
    return json.loads(path.read_text())


def _norm(name):
    name = re.sub(r"[^a-z ]", "", str(name).lower().replace("-", " "))
    return re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name).replace(" ", "")


def id_map(refresh=False):
    """nflverse gsis_id -> Sleeper player_id.

    Uses, in order: the DynastyProcess crosswalk, the gsis_id Sleeper itself
    carries, then name + position matching for anyone still unmatched.
    """
    path = RAW_DIR / "db_playerids.csv"
    if refresh or not path.exists():
        urllib.request.urlretrieve(CROSSWALK, path)
    cw = pd.read_csv(path, usecols=["gsis_id", "sleeper_id"], dtype=str).dropna()
    out = dict(zip(cw.gsis_id, cw.sleeper_id.str.replace(r"\.0$", "", regex=True)))
    sp = players(refresh)
    for sid, p in sp.items():
        g = (p.get("gsis_id") or "").strip()
        if g and g not in out:
            out[g] = sid
    out["_by_name"] = {}
    for sid, p in sp.items():
        if p.get("position") in ("QB", "RB", "WR", "TE") and p.get("full_name"):
            out["_by_name"].setdefault((_norm(p["full_name"]), p["position"]), sid)
    return out


def attach_sleeper_ids(df, ids, name_col="name", pos_col="position"):
    by_name = ids["_by_name"]
    sid = [ids.get(pid) or by_name.get((_norm(n), pos)) for pid, n, pos in zip(df.index, df[name_col], df[pos_col])]
    return pd.Series(sid, index=df.index)


def directory(exclude_ids, limit=1600):
    """Slim name/position/team list so rostered players without a projection still display."""
    sp = players()
    rows = []
    for sid, p in sp.items():
        if sid in exclude_ids or p.get("position") not in ("QB", "RB", "WR", "TE", "K", "DEF"):
            continue
        if not p.get("active") and p.get("position") != "DEF":
            continue
        rank = p.get("search_rank") or 99999
        name = p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        if p.get("position") == "DEF":
            name, rank = f"{sid} Defense", 5000
        rows.append((rank, sid, name, p["position"], TEAM_FIX.get(p.get("team"), p.get("team") or "FA")))
    rows.sort()
    return {sid: [name, pos, team] for _, sid, name, pos, team in rows[:limit]}


def injuries(sleeper_ids):
    sp = players()
    out = {}
    for sid in sleeper_ids:
        p = sp.get(sid) or {}
        if p.get("injury_status"):
            out[sid] = p["injury_status"]
    return out


def league_snapshot(username, season):
    """Everything the web app needs for one user's leagues, for offline bundling."""
    user = get(f"/user/{username}")
    if not user:
        raise ValueError(f"No Sleeper user named {username!r}")
    leagues = get(f"/user/{user['user_id']}/leagues/nfl/{season}")
    snap = {"user": {"user_id": user["user_id"], "display_name": user.get("display_name")},
            "leagues": [], "taken": pd.Timestamp.now(tz="UTC").isoformat(timespec="minutes")}
    for lg in leagues:
        lid = lg["league_id"]
        snap["leagues"].append({"league": lg, "rosters": get(f"/league/{lid}/rosters"),
                                "users": get(f"/league/{lid}/users")})
    return snap
