"""Fit on every completed season and publish live rest-of-season rankings + trade values.

Writes output/rankings_<season>_wk<week>.csv and web/data.json (read by the trade calculator).
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from caldo.backtest import TRAIN_START, load_features
from caldo.config import FANTASY_LAST_WEEK, OUT_DIR, ROOT, League
from caldo.data import fetch
from caldo.model import Projector
from caldo.ros import project_ros
from caldo.tiers import assign_tiers
from caldo.trade import vorp

KEEP = {"QB": 40, "RB": 90, "WR": 120, "TE": 45}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--refresh", action="store_true", help="re-download this season's data first")
    args = ap.parse_args()
    if args.refresh:
        fetch(args.season)

    league = League()
    tables, weeklies, formulas = {}, {}, {}
    for scoring in ["ppr", "half", "std"]:
        feat, tg = load_features(args.season, scoring, refresh=args.refresh)
        cur = feat[(feat.season == args.season) & ~feat.completed]
        week = int(cur.week.min())
        train = feat[(feat.season >= TRAIN_START) & (feat.season < args.season)]
        full = feat[feat.season <= args.season]
        pr = Projector().fit(train, full, tg)
        out, weekly = project_ros(pr, full, tg, args.season, week, FANTASY_LAST_WEEK, live=True)
        tables[scoring], weeklies[scoring] = out.set_index("player_id"), weekly
        formulas[scoring] = pr.formula()
        print(f"{scoring}: projected {len(out)} players from week {week}", flush=True)

    base = tables["ppr"].copy()
    for s in ["half", "std"]:
        base[f"ros_{s}"] = tables[s].ros_pts
    base = base.rename(columns={"ros_pts": "ros_ppr"})
    base["vorp_ppr"] = vorp(base.reset_index(), "ros_ppr", league).values
    keep = []
    for pos, n in KEEP.items():
        keep += list(base[base.position == pos].sort_values("ros_ppr", ascending=False).index[:n])
    base = base.loc[keep].copy()
    for s in ["ppr", "half", "std"]:
        base[f"tier_{s}"] = 0
        for pos in KEEP:
            m = base.position == pos
            base.loc[m, f"tier_{s}"] = assign_tiers(base.loc[m, f"ros_{s}"].values)

    OUT_DIR.mkdir(exist_ok=True)
    csv = OUT_DIR / f"rankings_{args.season}_wk{week}.csv"
    cols = ["name", "position", "team", "tier_ppr", "ros_ppr", "ros_half", "ros_std", "vorp_ppr", "ros_td",
            "ros_ppg", "games_left", "exp_games", "sched_ease", "next_opp", "next_proj", "szn_pts", "szn_g"]
    base.sort_values("vorp_ppr", ascending=False)[cols].round(2).to_csv(csv)
    for s, f in formulas.items():
        f.to_csv(OUT_DIR / f"formula_{s}.csv", index=False)

    weeks = list(range(week, FANTASY_LAST_WEEK + 1))
    players = []
    for pid, r in base.iterrows():
        wk = {}
        for s in ["ppr", "half", "std"]:
            w = weeklies[s][weeklies[s].player_id == pid].set_index("week").xpts
            wk[s] = [round(float(w.get(x, 0.0)), 2) for x in weeks]
        players.append({
            "id": pid, "name": r["name"], "pos": r.position, "team": r.team,
            "ros": {s: round(float(r[f"ros_{s}"]), 1) for s in ["ppr", "half", "std"]},
            "tier": {s: int(r[f"tier_{s}"]) for s in ["ppr", "half", "std"]},
            "td": round(float(r.ros_td), 1), "ppg": round(float(r.ros_ppg), 1),
            "szn_ppg": None if pd.isna(r.szn_pts) else round(float(r.szn_pts), 1),
            "gl": int(r.games_left), "xg": round(float(r.exp_games), 1),
            "sched": round(float(r.sched_ease), 3), "next": r.next_opp,
            "next_proj": round(float(r.next_proj), 1), "weekly": wk,
        })
    meta = {"season": args.season, "week": week, "weeks": weeks, "generated": date.today().isoformat()}
    pw = OUT_DIR / "package_weights.json"
    if pw.exists():
        meta["package"] = json.loads(pw.read_text())
    bt = OUT_DIR / "backtest" / "summary.json"
    if bt.exists():
        meta["backtest"] = json.loads(bt.read_text())
    (ROOT / "web").mkdir(exist_ok=True)
    (ROOT / "web" / "data.json").write_text(json.dumps({"meta": meta, "players": players}, separators=(",", ":")))
    print(f"wrote {csv} and web/data.json ({len(players)} players)")
    print(base.sort_values("vorp_ppr", ascending=False)[cols].head(40).round(1).to_string())


if __name__ == "__main__":
    main()
