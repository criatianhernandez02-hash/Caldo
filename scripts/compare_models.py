"""Compare our projections with Sleeper (Rotowire), ESPN and the FantasyPros expert consensus.

Two comparisons:
  1. Weekly accuracy on this season's completed weeks: each site's weekly
     projection (as it stood before the game) vs. what players scored.
  2. Rest-of-season agreement right now: rank correlation between models per
     position, and the players they disagree about most.

Inputs: data/raw/ext/sleeper_proj_<season>_<week>.json, sleeper_stats_*.json,
espn_<season>.json, fantasypros_ros_ecr.csv (fetched by fetch_external.py),
plus web/data.json (our current rankings).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from caldo.backtest import TRAIN_START, load_features
from caldo.config import OUT_DIR, RAW_DIR, ROOT
from caldo.model import Projector

EXT = RAW_DIR / "ext"
ESPN_POS = {1: "QB", 2: "RB", 3: "WR", 4: "TE"}
POOL = {"QB": 24, "RB": 36, "WR": 48, "TE": 18}


def _norm(name):
    name = re.sub(r"[^a-z ]", "", str(name).lower().replace("-", " "))
    return re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name).replace(" ", "")


def sleeper_weekly(season, weeks):
    rows = []
    for w in weeks:
        f = EXT / f"sleeper_proj_{season}_{w}.json"
        if not f.exists():
            continue
        for x in json.load(open(f)):
            if x["stats"].get("pts_ppr") is not None:
                rows.append({"sid": x["player_id"], "week": w, "sleeper": x["stats"]["pts_ppr"],
                             "pos": x["player"]["position"], "name": f"{x['player']['first_name']} {x['player']['last_name']}"})
    return pd.DataFrame(rows)


def sleeper_actual(season, weeks):
    rows = []
    for w in weeks:
        f = EXT / f"sleeper_stats_{season}_{w}.json"
        if f.exists():
            rows += [{"sid": x["player_id"], "week": w, "actual_sl": x["stats"].get("pts_ppr", 0.0)} for x in json.load(open(f))]
    return pd.DataFrame(rows)


def espn(season):
    d = json.load(open(EXT / f"espn_{season}.json"))
    weekly, ros = [], []
    for p in d["players"]:
        pl = p["player"]
        pos = ESPN_POS.get(pl.get("defaultPositionId"))
        if not pos:
            continue
        for s in pl.get("stats", []):
            if s.get("seasonId") != season or s.get("statSourceId") != 1:
                continue
            if s.get("statSplitTypeId") == 1 and s.get("scoringPeriodId", 0) > 0:
                weekly.append({"espn_id": pl["id"], "name": pl["fullName"], "pos": pos, "week": s["scoringPeriodId"],
                               "espn": s.get("appliedTotal", 0.0), "injury": pl.get("injuryStatus")})
    return pd.DataFrame(weekly)


def main(season=2026):
    data = json.loads((ROOT / "web" / "data.json").read_text())
    ours = pd.DataFrame(data["players"])
    week = data["meta"]["week"]
    weeks_done = list(range(1, week))
    players = pd.read_csv(RAW_DIR / "players.csv", low_memory=False, usecols=["gsis_id", "espn_id"]).dropna()
    espn_to_gsis = dict(zip(players.espn_id.astype(int), players.gsis_id))
    sid_to_gsis = dict(zip(ours.sid, ours.id))

    # ---- 1. weekly accuracy on completed weeks ----
    feat, tg = load_features(season, "ppr")
    pr = Projector().fit(feat[(feat.season >= TRAIN_START) & (feat.season < season)], feat[feat.season <= season], tg)
    test = feat[(feat.season == season) & feat.week.isin(weeks_done)].copy()
    test["ours"] = pr.predict_games(test).proj.values
    test = test[test.played == 1][["player_id", "player_display_name", "position", "week", "pts", "ours"]]
    sl = sleeper_weekly(season, weeks_done)
    sl["player_id"] = sl.sid.map(sid_to_gsis)
    es = espn(season)
    es["player_id"] = es.espn_id.map(espn_to_gsis)
    m = test.merge(sl[["player_id", "week", "sleeper"]], on=["player_id", "week"], how="left") \
            .merge(es[["player_id", "week", "espn"]], on=["player_id", "week"], how="left")
    both = m.dropna(subset=["sleeper", "espn"])
    rows = []
    for pos, n in POOL.items():
        d = both[both.position == pos]
        for model in ["ours", "sleeper", "espn"]:
            cs, maes = [], []
            for _, g in d.groupby("week"):
                top = g[g[model].rank(ascending=False) <= n]
                if len(top) > 5:
                    cs.append(spearmanr(top[model], top.pts).statistic)
                maes.append((g[model] - g.pts).abs().mean())
            rows.append({"position": pos, "model": model, "rank_corr": np.nanmean(cs), "MAE": np.mean(maes), "n_player_weeks": len(d)})
    weekly_summary = pd.DataFrame(rows)

    # ---- 2. rest-of-season agreement now ----
    sl_ros = sleeper_weekly(season, range(week, 18)).groupby("sid").sleeper.sum().rename("sleeper_ros")
    es_ros = es[es.week >= week].groupby("espn_id").espn.sum().rename("espn_ros")
    fp = pd.read_csv(EXT / "fantasypros_ros_ecr.csv")
    fp["key"] = fp.name.map(_norm) + fp.pos
    ours["key"] = ours.name.map(_norm) + ours.pos
    ours["sleeper_ros"] = ours.sid.map(sl_ros)
    gsis_to_espn = {v: k for k, v in espn_to_gsis.items()}
    ours["espn_ros"] = ours.id.map(gsis_to_espn).map(es_ros)
    ours = ours.merge(fp[["key", "fp_rank"]], on="key", how="left")
    ours["ours_ros"] = ours.ros.map(lambda r: r["ppr"])
    ours["model_ros"] = ours.ros_model if "ros_model" in ours else ours.ours_ros
    agree, disagree = [], []
    for pos in POOL:
        d = ours[ours.pos == pos].copy()
        d["ours_rank"] = d.ours_ros.rank(ascending=False)
        d["sleeper_rank"] = d.sleeper_ros.rank(ascending=False)
        d["espn_rank"] = d.espn_ros.rank(ascending=False)
        top = d[(d.ours_rank <= POOL[pos] * 1.5) | (d.fp_rank <= POOL[pos] * 1.5)]
        for a, b in [("ours_ros", "sleeper_ros"), ("ours_ros", "espn_ros"), ("ours_ros", "fp_rank"), ("model_ros", "espn_ros"),
                     ("model_ros", "fp_rank"), ("sleeper_ros", "espn_ros"), ("sleeper_ros", "fp_rank"), ("espn_ros", "fp_rank")]:
            t = top.dropna(subset=[a, b])
            r = spearmanr(t[a], t[b]).statistic
            if b == "fp_rank" or a == "fp_rank":
                r = -r
            agree.append({"position": pos, "pair": f"{a.replace('_ros', '')} vs {b.replace('_ros', '').replace('_rank', '')}", "rank_corr": r, "n": len(t)})
        top = top.copy()
        cons = top[["sleeper_rank", "espn_rank", "fp_rank"]].mean(axis=1)
        top = top.assign(consensus_rank=cons, gap=top.ours_rank - cons)
        for _, r in top.dropna(subset=["gap"]).sort_values("gap", key=abs, ascending=False).head(8).iterrows():
            disagree.append({"position": pos, "name": r["name"], "team": r.team, "ours_rank": int(r.ours_rank), "sleeper": r.sleeper_rank,
                             "espn": r.espn_rank, "fantasypros": r.fp_rank, "ours_ros": r.ours_ros, "exp_games": r.xg, "games_left": r.gl,
                             "ppg_ours": r.ours_ros / max(r.xg, .5), "sleeper_ros": r.sleeper_ros, "espn_ros": r.espn_ros})
    out = OUT_DIR / "compare"
    out.mkdir(parents=True, exist_ok=True)
    weekly_summary.to_csv(out / "weekly_accuracy.csv", index=False)
    pd.DataFrame(agree).to_csv(out / "ros_agreement.csv", index=False)
    pd.DataFrame(disagree).to_csv(out / "ros_disagreements.csv", index=False)
    pd.set_option("display.width", 220)
    print(f"Weekly accuracy, {season} weeks {weeks_done[0]}-{weeks_done[-1]} (players projected by all three):")
    print(weekly_summary.round(3).to_string())
    print("\nRest-of-season rank agreement (top of each position):")
    print(pd.DataFrame(agree).pivot(index="pair", columns="position", values="rank_corr").round(3).to_string())
    print("\nBiggest disagreements (our rank vs. average of the other three):")
    print(pd.DataFrame(disagree).round(1).to_string())


if __name__ == "__main__":
    main()
