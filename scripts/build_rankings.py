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

from caldo import sleeper
from caldo.backtest import TRAIN_START, load_features
from caldo.config import FANTASY_LAST_WEEK, OUT_DIR, RAW_DIR, ROOT, League
from caldo.data import fetch
from caldo.external import blend_weekly, load_sleeper_projections
from caldo.model import Projector
from caldo.ros import project_ros
from caldo.tiers import assign_tiers
from caldo.trade import vorp

KEEP = {"QB": 64, "RB": 130, "WR": 170, "TE": 75}


def load_blend(season, refresh):
    """Blend config (output/blend.json) plus Sleeper's current weekly projections, if available."""
    cfg_path = OUT_DIR / "blend.json"
    proj = RAW_DIR / "ext" / "sleeper_proj.parquet"
    if not cfg_path.exists() or not proj.exists():
        print("note: no blend config or Sleeper projections; using the model alone")
        return None
    if refresh:
        from scripts.fetch_external import main as fetch_ext
        fetch_ext(first=season, last=season)
    sp = load_sleeper_projections()
    cfg = json.loads(cfg_path.read_text())
    ids = sleeper.id_map()
    return {"cfg": cfg, "sp": sp[sp.season == season], "known": {g for g in ids if g != "_by_name"}}


def apply_blend(weekly, out, b, scoring):
    col = {"ppr": "sl_ppr", "half": "sl_half", "std": "sl_std"}[scoring]
    cfg = {p: {"w_ours": c["w_ours"], "sleeper_scale": c[f"scale_{scoring}"] if f"scale_{scoring}" in c else c["sleeper_scale"]}
           for p, c in b["cfg"]["weights"].items()}
    w = blend_weekly(weekly, b["sp"], cfg, b["cfg"]["availability"], col, b["known"])
    agg = w.groupby("player_id").agg(ros_pts=("xpts_blend", "sum"), exp_games=("p_blend", "sum"), ros_td=("xtd_blend", "sum"))
    first = w[w.k == 0].set_index("player_id").if_plays
    out = out.copy()
    out[["ros_pts", "exp_games", "ros_td"]] = agg.reindex(out.index)[["ros_pts", "exp_games", "ros_td"]]
    out["next_proj"] = first.reindex(out.index).fillna(out.next_proj)
    out["ros_ppg"] = out.ros_pts / out.exp_games.clip(lower=0.5)
    w = w.assign(xpts=w.xpts_blend)
    return w, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--refresh", action="store_true", help="re-download this season's data first")
    ap.add_argument("--sleeper-user", help="bundle this Sleeper user's leagues (for pages without internet)")
    ap.add_argument("--no-blend", action="store_true", help="model only, without Sleeper's projections")
    args = ap.parse_args()
    if args.refresh:
        fetch(args.season)

    league = League()
    tables, weeklies, formulas = {}, {}, {}
    blend_cfg = None if args.no_blend else load_blend(args.season, args.refresh)
    for scoring in ["ppr", "half", "std"]:
        feat, tg = load_features(args.season, scoring, refresh=args.refresh)
        cur = feat[(feat.season == args.season) & ~feat.completed]
        week = int(cur.week.min())
        train = feat[(feat.season >= TRAIN_START) & (feat.season < args.season)]
        full = feat[feat.season <= args.season]
        pr = Projector().fit(train, full, tg)
        out, weekly = project_ros(pr, full, tg, args.season, week, FANTASY_LAST_WEEK, live=True)
        out = out.set_index("player_id")
        out["ros_model"] = out.ros_pts
        if blend_cfg:
            weekly, out = apply_blend(weekly, out, blend_cfg, scoring)
        tables[scoring], weeklies[scoring] = out, weekly
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
    try:
        ids = sleeper.id_map(refresh=args.refresh)
        base["sid"] = sleeper.attach_sleeper_ids(base, ids)
    except OSError as e:  # Sleeper unreachable: the calculator still works without league sync
        print(f"warning: no Sleeper id mapping ({e})")
        base["sid"] = None
    players = []
    for pid, r in base.iterrows():
        wk = {}
        for s in ["ppr", "std"]:  # any reception value is std + rec * (ppr - std)
            w = weeklies[s][weeklies[s].player_id == pid].set_index("week").xpts
            wk[s] = [round(float(w.get(x, 0.0)), 2) for x in weeks]
        players.append({
            "id": pid, "sid": r.sid if isinstance(r.sid, str) else None,
            "name": r["name"], "pos": r.position, "team": r.team,
            "ros": {s: round(float(r[f"ros_{s}"]), 1) for s in ["ppr", "half", "std"]},
            "td": round(float(r.ros_td), 1),
            "ros_model": round(float(r.ros_model), 1),
            "szn_ppg": None if pd.isna(r.szn_pts) else round(float(r.szn_pts), 1),
            # season-to-date points per game in both formats: the "box score" view most managers trade on
            "szn": None if pd.isna(r.szn_pts) else {
                "ppr": round(float(r.szn_pts), 2),
                "std": round(float(np.nan_to_num(tables["std"].szn_pts.get(pid, np.nan), nan=r.szn_pts)), 2)},
            "sg": int(r.szn_g),
            "gl": int(r.games_left), "xg": round(float(r.exp_games), 2),
            "sched": round(float(r.sched_ease), 3), "next": r.next_opp,
            "weekly": wk,
        })
    meta = {"season": args.season, "week": week, "weeks": weeks, "generated": date.today().isoformat()}
    data = {"meta": meta, "players": players}
    try:
        mapped = {p["sid"] for p in players if p["sid"]}
        data["sleeper_dir"] = sleeper.directory(mapped)
        data["injuries"] = sleeper.injuries(list(mapped) + list(data["sleeper_dir"]))
        if args.sleeper_user:
            data["sleeper_snapshot"] = sleeper.league_snapshot(args.sleeper_user, args.season)
    except OSError as e:
        print(f"warning: Sleeper data skipped ({e})")
    (ROOT / "web").mkdir(exist_ok=True)
    (ROOT / "web" / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    n_map = sum(1 for p in players if p["sid"])
    print(f"Sleeper ids mapped for {n_map}/{len(players)} players")
    print(f"wrote {csv} and web/data.json ({len(players)} players)")
    print(base.sort_values("vorp_ppr", ascending=False)[cols].head(40).round(1).to_string())


if __name__ == "__main__":
    main()
