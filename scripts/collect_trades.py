"""Collect completed trades from public Sleeper redraft leagues, for testing trade odds.

Sleeper exposes every league's completed transactions (trades, waivers, free
agent moves) and its draft. Starting from a few seed users, this walks from
league to league through shared managers and saves, per league: settings,
draft picks, and every completed transaction through week 14, which is enough
to rebuild both rosters at the moment of any trade.

Only aggregate results are reported; the raw files stay in data/ (git-ignored).
"""
import argparse
import json
import random
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from caldo.config import RAW_DIR

API = "https://api.sleeper.app/v1"
OUT = RAW_DIR / "trades"
_lock = threading.Lock()
_last = [0.0]


def get(path, rate=14.0):
    with _lock:  # stay well under Sleeper's 1000 calls/minute guidance
        wait = _last[0] + 1.0 / rate - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
    for attempt in range(4):
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 ** attempt)
    return None


def eligible(lg):
    s, sc = lg.get("settings") or {}, lg.get("scoring_settings") or {}
    return (lg.get("status") == "complete" and s.get("type", 0) == 0 and 8 <= (lg.get("total_rosters") or 0) <= 14
            and (sc.get("rec") or 0) >= 0.5 and lg.get("draft_id"))


def fetch_league(lg, max_week=14):
    lid = lg["league_id"]
    tx = []
    for w in range(1, max_week + 1):
        t = get(f"/league/{lid}/transactions/{w}") or []
        tx += [x for x in t if x.get("status") == "complete"]
    trades = [x for x in tx if x["type"] == "trade" and not x.get("draft_picks") and (x.get("adds") or {})]
    users = get(f"/league/{lid}/users") or []
    if not trades:
        return None, [u["user_id"] for u in users]
    picks = get(f"/draft/{lg['draft_id']}/picks") or []
    rosters = get(f"/league/{lid}/rosters") or []
    keep = ["type", "status", "leg", "created", "status_updated", "roster_ids", "adds", "drops", "waiver_budget"]
    rec = {
        "league_id": lid, "season": int(lg["season"]), "total_rosters": lg["total_rosters"],
        "roster_positions": lg.get("roster_positions"), "rec": lg["scoring_settings"].get("rec"),
        "bonus_rec_te": lg["scoring_settings"].get("bonus_rec_te"), "pass_td": lg["scoring_settings"].get("pass_td"),
        "trade_deadline": (lg.get("settings") or {}).get("trade_deadline"),
        "draft": [{"player_id": p["player_id"], "roster_id": p.get("roster_id"), "pick_no": p.get("pick_no")} for p in picks],
        "roster_owner": {r["roster_id"]: r.get("owner_id") for r in rosters},
        "transactions": [{k: x.get(k) for k in keep} for x in tx],
    }
    return rec, [u["user_id"] for u in users]


def crawl(season, seeds, target, workers=14):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"leagues_{season}.jsonl"
    seen_leagues = set()
    if path.exists():
        seen_leagues = {json.loads(l)["league_id"] for l in open(path)}
    seen_users, queue = set(), list(seeds)
    if seen_leagues:  # resuming: restart the walk from managers in leagues already saved
        with ThreadPoolExecutor(workers) as ex:
            for us in ex.map(lambda lid: get(f"/league/{lid}/users") or [], list(seen_leagues)[:60]):
                queue += [u["user_id"] for u in us]
        random.shuffle(queue)
    fetched = with_trades = len(seen_leagues)
    f = open(path, "a")
    with ThreadPoolExecutor(workers) as ex:
        while queue and fetched < target:
            batch, queue = queue[:workers * 4], queue[workers * 4:]
            batch = [u for u in batch if u not in seen_users]
            seen_users.update(batch)
            leagues = []
            for ls in ex.map(lambda u: get(f"/user/{u}/leagues/nfl/{season}") or [], batch):
                for lg in ls:
                    if lg["league_id"] not in seen_leagues and eligible(lg):
                        seen_leagues.add(lg["league_id"])
                        leagues.append(lg)
            leagues = leagues[: max(0, target - fetched)]
            for rec, users in ex.map(fetch_league, leagues):
                fetched += 1
                queue += [u for u in users if u not in seen_users]
                if rec:
                    with_trades += 1
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
            random.shuffle(queue)
            print(f"  {season}: {fetched} leagues checked, {with_trades} with trades, {len(queue)} managers queued", flush=True)
    f.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default="2022,2023,2024,2025")
    ap.add_argument("--target", type=int, default=300, help="leagues to check per season")
    ap.add_argument("--seed-users", default="RamRiderz,jjzachariason")
    args = ap.parse_args()
    seeds = []
    for name in args.seed_users.split(","):
        u = get(f"/user/{name}")
        if u:
            seeds.append(u["user_id"])
    for season in map(int, args.seasons.split(",")):
        crawl(season, seeds, args.target)


if __name__ == "__main__":
    main()
