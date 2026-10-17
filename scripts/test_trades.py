"""Test the trade-odds formula and the trade calculator against real Sleeper trades.

For every completed 2-team, player-only trade collected by collect_trades.py:
  * rebuild both rosters at the moment of the trade (draft + every earlier move),
  * value every player with the walk-forward backtest snapshot taken before the
    trade (so no later information leaks in),
  * score the deal the way the app does: each side's starting-lineup change,
    and how fair it looks by this season's points per game ("box score"),
  * draw random trades the same two teams could have made the same week
    (same number of players each way, from the top of each roster).

Questions answered:
  1. Do real trades look different from random ones in the way the app's
     odds assume? (AUC of real vs. random, by score.)
  2. Refit the odds from the trades people actually made (conditional on the
     same teams, week and shape) and compare out of sample by season.
  3. Who won real trades? Does the model's projected winner match the side
     that actually scored more the rest of the season, vs. a box-score guess?
Writes output/trade_test/*.csv and output/trade_odds.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from caldo import sleeper
from caldo.config import OUT_DIR, RAW_DIR

SNAPS = [3, 5, 7, 9, 11]
GET_W = [1.0, 0.71, 0.48]
ELIG = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"}, "FLEX": {"RB", "WR", "TE"},
        "WRRB_FLEX": {"RB", "WR"}, "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
ORDER = ["QB", "RB", "WR", "TE", "REC_FLEX", "WRRB_FLEX", "FLEX", "SUPER_FLEX"]
N_NULL = 25
rng = np.random.default_rng(11)


def lineup(players, slots, val, pos):
    """Best lineup total from rest-of-season values (byes ignored)."""
    ps = sorted((p for p in players if p in val), key=lambda p: -val[p])
    used, tot = set(), 0.0
    for s in slots:
        for p in ps:
            if p not in used and pos[p] in ELIG[s]:
                used.add(p)
                tot += val[p]
                break
    return tot


def pk(ids, v):
    xs = sorted((max(0.0, v.get(i, 0.0)) for i in ids), reverse=True)
    return sum(x * GET_W[min(k, 2)] for k, x in enumerate(xs))


def rosters_at(lg, created):
    """Rosters just before a transaction: draft, then every completed move made earlier."""
    owner = {str(p["player_id"]): p["roster_id"] for p in lg["draft"] if p.get("roster_id")}
    for t in sorted(lg["transactions"], key=lambda x: x.get("status_updated") or x["created"]):
        if (t.get("status_updated") or t["created"]) >= created:
            break
        for p, r in (t.get("drops") or {}).items():
            if owner.get(p) == r:
                owner.pop(p, None)
        for p, r in (t.get("adds") or {}).items():
            owner[p] = r
    out = {}
    for p, r in owner.items():
        out.setdefault(r, set()).add(p)
    return out


def side_features(give, get, roster, slots, proj, act, mkt, rep, mrep, pos):
    """One team's view of a trade."""
    before = roster
    after = (roster - set(give)) | set(get)
    pv = {p: proj[p] for p in before | after if p in proj}
    av = {p: act[p] for p in before | after if p in act}
    vorp = {p: proj[p] - rep.get(pos[p], 0) for p in pv}
    mvorp = {p: mkt[p] - mrep.get(pos[p], 0) for p in pv}
    return {
        "lineup": lineup(after, slots, pv, pos) - lineup(before, slots, pv, pos),
        "lineup_actual": lineup(after, slots, av, pos) - lineup(before, slots, av, pos),
        "box_fair": pk(get, mvorp) - pk(give, mvorp),
        "value_fair": pk(get, vorp) - pk(give, vorp),
    }


def build(seasons):
    ids = sleeper.id_map()
    rev = {s: g for g, s in ids.items() if g != "_by_name"}
    snap = pd.read_parquet(OUT_DIR / "backtest" / "v4" / "ros_detail_ppr.parquet")
    w_box = np.minimum(1, snap.szn_g.fillna(0) / 4)
    snap["mkt"] = w_box * snap.szn_pts.fillna(0) * snap.exp_games + (1 - w_box) * snap.m_full
    snap["sid"] = snap.player_id.map(ids)
    tables = {k: g.dropna(subset=["sid"]).set_index("sid") for k, g in snap.groupby(["season", "week"])}
    rows = []
    for season in seasons:
        f = RAW_DIR / "trades" / f"leagues_{season}.jsonl"
        if not f.exists():
            continue
        for line in open(f):
            lg = json.loads(line)
            slots = sorted([s for s in (lg["roster_positions"] or []) if s in ELIG], key=ORDER.index)
            if not slots:
                continue
            for t in lg["transactions"]:
                if t["type"] != "trade" or len(t["roster_ids"] or []) != 2 or not t.get("adds"):
                    continue
                leg = t["leg"]
                W = max([w for w in SNAPS if w <= leg], default=None)
                if W is None or leg > 13 or (lg.get("trade_deadline") and leg > lg["trade_deadline"]):
                    continue
                tab = tables.get((season, W))
                if tab is None:
                    continue
                proj, act, mkt, pos = tab.m_full.to_dict(), tab.actual_ros.to_dict(), tab.mkt.to_dict(), tab.position.to_dict()
                ros = rosters_at(lg, t.get("status_updated") or t["created"])
                rostered = set().union(*ros.values()) if ros else set()
                fa = tab[~tab.index.isin(rostered)]
                rep, mrep = fa.groupby("position").m_full.max().to_dict(), fa.groupby("position").mkt.max().to_dict()
                a, b = t["roster_ids"]
                drops = t.get("drops") or {}
                give = {r: [p for p, rr in drops.items() if rr == r and p in t["adds"]] for r in (a, b)}
                get = {r: [p for p, rr in t["adds"].items() if rr == r] for r in (a, b)}
                if not all(get.values()) or not all(give.values()):
                    continue
                if not all(p in proj for p in get[a] + get[b]):
                    continue  # a traded player we can't value (K, DEF, unmatched id)
                ra, rb = ros.get(a, set()) | set(give[a]), ros.get(b, set()) | set(give[b])

                def score(ga, gb, kind, k=0):
                    fa_ = side_features(ga, gb, ra, slots, proj, act, mkt, rep, mrep, pos)
                    fb_ = side_features(gb, ga, rb, slots, proj, act, mkt, rep, mrep, pos)
                    return {"season": season, "league": lg["league_id"], "trade": t["created"], "leg": leg, "kind": kind, "k": k,
                            "n_a": len(ga), "n_b": len(gb), "rec": lg["rec"], "teams": lg["total_rosters"],
                            **{f"{c}_a": v for c, v in fa_.items()}, **{f"{c}_b": v for c, v in fb_.items()}}
                rows.append(score(give[a], give[b], "real"))
                # random trades the same two teams could have made that week, same shape
                top = lambda r: sorted([p for p in r if p in proj], key=lambda p: -max(proj[p] - rep.get(pos[p], 0), mkt[p] - mrep.get(pos[p], 0)))[:10]
                ta, tb = top(ra), top(rb)
                if len(ta) < len(give[a]) or len(tb) < len(give[b]):
                    continue
                for k in range(N_NULL):
                    ga = list(rng.choice(ta, len(give[a]), replace=False))
                    gb = list(rng.choice(tb, len(give[b]), replace=False))
                    rows.append(score(ga, gb, "random", k + 1))
        print(f"  {season}: {sum(1 for r in rows if r['kind'] == 'real' and r['season'] == season)} trades scored", flush=True)
    return pd.DataFrame(rows)


def app_odds(lineup_delta, box_fair):
    return 1 / (1 + np.exp(-(0.12 * lineup_delta + 0.04 * box_fair)))


def features(d):
    """Order the two sides as 'worse off' / 'better off' by projected lineup change."""
    swap = d.lineup_a > d.lineup_b
    out = pd.DataFrame(index=d.index)
    for c in ["lineup", "box_fair", "value_fair"]:
        lo = np.where(swap, d[f"{c}_b"], d[f"{c}_a"])
        hi = np.where(swap, d[f"{c}_a"], d[f"{c}_b"])
        out[f"{c}_worse"], out[f"{c}_better"] = lo, hi
    out["abs_box"] = d.box_fair_a.abs()
    out["abs_value"] = d.value_fair_a.abs()
    return out


def main():
    seasons = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "2022,2023,2024,2025").split(",")]
    d = build(seasons)
    out = OUT_DIR / "trade_test"
    out.mkdir(parents=True, exist_ok=True)
    d.to_parquet(out / "scored.parquet")
    real, rnd = d[d.kind == "real"], d[d.kind == "random"]
    y = (d.kind == "real").astype(int)
    X = features(d)

    # 1. how well do simple scores pick out real trades from same-team, same-week random ones?
    scores = {
        "App odds (both sides)": app_odds(d.lineup_a, d.box_fair_a) * app_odds(d.lineup_b, d.box_fair_b),
        "Lineup only (worse-off side)": X.lineup_worse,
        "Box-score fairness": -X.abs_box,
        "Projected-value fairness": -X.abs_value,
        "Both lineups combined": d.lineup_a + d.lineup_b,
    }
    auc = pd.DataFrame([{"score": k, "AUC": roc_auc_score(y, v)} for k, v in scores.items()])

    # 2. refit the odds on real trades, out of sample by season
    cols = ["lineup_worse", "lineup_better", "box_fair_worse", "abs_box", "abs_value"]
    cv = []
    for s in seasons:
        tr, te = d.season != s, d.season == s
        if y[te].sum() == 0 or y[tr].sum() == 0:
            continue
        m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(X.loc[tr, cols], y[tr])
        cv.append({"season": s, "AUC_refit": roc_auc_score(y[te], m.predict_proba(X.loc[te, cols])[:, 1]),
                   "AUC_app": roc_auc_score(y[te], scores["App odds (both sides)"][te])})
    cv = pd.DataFrame(cv)
    final = LogisticRegression(max_iter=2000, class_weight="balanced").fit(X[cols], y)
    coefs = dict(zip(cols, np.round(final.coef_[0], 4)))

    # per-side acceptance refit: the side that gave something up still said yes
    side = pd.DataFrame({
        "lineup": np.r_[d.lineup_a, d.lineup_b], "box_fair": np.r_[d.box_fair_a, d.box_fair_b],
        "value_fair": np.r_[d.value_fair_a, d.value_fair_b], "y": np.r_[y, y], "season": np.r_[d.season, d.season]})
    sm = LogisticRegression(max_iter=2000, class_weight="balanced").fit(side[["lineup", "box_fair"]], side.y)
    side_auc_app = roc_auc_score(side.y, app_odds(side.lineup, side.box_fair))
    side_cv = []
    for s in seasons:
        tr, te = side.season != s, side.season == s
        if side.y[te].sum() and side.y[tr].sum():
            m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(side.loc[tr, ["lineup", "box_fair"]], side.y[tr])
            side_cv.append(roc_auc_score(side.y[te], m.predict_proba(side.loc[te, ["lineup", "box_fair"]])[:, 1]))

    # 3. describe real trades vs random
    desc = pd.DataFrame({
        "real": [((real.lineup_a > 0) & (real.lineup_b > 0)).mean(),
                 ((real.lineup_a < -5) | (real.lineup_b < -5)).mean(),
                 (real.box_fair_a.abs() <= 15).mean(), (real.value_fair_a.abs() <= 15).mean(),
                 real[["lineup_a", "lineup_b"]].min(axis=1).median(), real.box_fair_a.abs().median(), real.value_fair_a.abs().median()],
        "random": [((rnd.lineup_a > 0) & (rnd.lineup_b > 0)).mean(), ((rnd.lineup_a < -5) | (rnd.lineup_b < -5)).mean(),
                   (rnd.box_fair_a.abs() <= 15).mean(), (rnd.value_fair_a.abs() <= 15).mean(),
                   rnd[["lineup_a", "lineup_b"]].min(axis=1).median(), rnd.box_fair_a.abs().median(), rnd.value_fair_a.abs().median()],
    }, index=["Both lineups improve (projected)", "One side loses 5+ lineup pts", "Box-score values within 15 pts",
              "Projected values within 15 pts", "Median lineup change, worse-off side", "Median box-score gap", "Median projected-value gap"])

    # 4. who won? projected vs actual, on real trades with a clear winner
    r = real.copy()
    r["diff_actual"] = r.lineup_actual_a - r.lineup_actual_b
    clear = r[r.diff_actual.abs() >= 10]
    win = pd.DataFrame([
        {"predictor": "Model: projected lineup change", "accuracy": (np.sign(clear.lineup_a - clear.lineup_b) == np.sign(clear.diff_actual)).mean()},
        {"predictor": "Model: projected value over replacement", "accuracy": (np.sign(clear.value_fair_a) == np.sign(clear.diff_actual)).mean()},
        {"predictor": "Box score: points per game so far", "accuracy": (np.sign(clear.box_fair_a) == np.sign(clear.diff_actual)).mean()},
    ])
    win["n_trades"] = len(clear)
    disagree = clear[np.sign(clear.value_fair_a) != np.sign(clear.box_fair_a)]
    win_dis = (np.sign(disagree.value_fair_a) == np.sign(disagree.diff_actual)).mean() if len(disagree) else np.nan

    # within-trade test: where does each real trade rank among its own random alternatives?
    d["grp"] = d.league.astype(str) + "_" + d.trade.astype(str)
    pct = []
    for name, v in {**scores, "Refit (out of sample)": None}.items():
        if v is None:
            continue
        tmp = d.assign(v=np.asarray(v, float))
        r_ = tmp.groupby("grp").apply(lambda g: (g.v[g.kind == "random"] < g.v[g.kind == "real"].iloc[0]).mean() if (g.kind == "real").any() else np.nan)
        pct.append({"score": name, "avg_percentile": float(np.nanmean(r_)), "top_quarter": float(np.nanmean(r_ >= .75))})
    # conditional (within-trade) refit: demean features inside each trade's group, test by season
    Xd = X[cols].sub(X[cols].groupby(d.grp).transform("mean"))
    cond = []
    for s in seasons:
        tr, te = d.season != s, d.season == s
        if y[te].sum() == 0 or y[tr].sum() == 0:
            continue
        m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xd[tr], y[tr])
        tmp = d[te].assign(v=m.decision_function(Xd[te]))
        r_ = tmp.groupby("grp").apply(lambda g: (g.v[g.kind == "random"] < g.v[g.kind == "real"].iloc[0]).mean())
        cond.append({"season": s, "avg_percentile_refit": float(r_.mean())})
    mc = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xd, y)
    cond_coefs = dict(zip(cols, np.round(mc.coef_[0], 4)))
    pct = pd.DataFrame(pct)
    pct.to_csv(out / "within_trade.csv", index=False)
    pd.DataFrame(cond).to_csv(out / "within_trade_refit.csv", index=False)
    # where do real trades fall on the refit utility, for turning it into app labels
    util = pd.Series(Xd.values @ mc.coef_[0], index=d.index)
    raw_util = pd.Series(X[cols].values @ mc.coef_[0], index=d.index)
    q = raw_util[d.kind == "random"].quantile([.5, .75, .9]).round(4).to_dict()
    deciles = [round(float(x), 4) for x in raw_util[d.kind == "random"].quantile(np.linspace(0.05, 0.95, 19))]
    real_pct = [float((raw_util[d.kind == "random"] < u).mean()) for u in raw_util[d.kind == "real"]]
    # labels anchored on real trades: "Likely yes" = at least as good as the typical accepted trade,
    # "Worth a try" = within the range of 4 in 5 accepted trades, "Long shot" = below that
    odds_out = {"coefs": cond_coefs, "random_quantiles": deciles, "quantile_levels": [round(x, 2) for x in np.linspace(0.05, 0.95, 19)],
                "real_trade_median_percentile": float(np.median(real_pct)), "n_real": int(len(real)),
                "n_leagues": int(real.league.nunique()), "seasons": seasons,
                "label_thresholds": {"likely": round(float(np.quantile(real_pct, .5)), 3), "try": round(float(np.quantile(real_pct, .2)), 3)}}
    (OUT_DIR / "trade_odds.json").write_text(json.dumps(odds_out, indent=2))

    auc.to_csv(out / "auc.csv", index=False); cv.to_csv(out / "auc_by_season.csv", index=False)
    desc.to_csv(out / "real_vs_random.csv"); win.to_csv(out / "who_won.csv", index=False)
    summary = {"n_real": int(len(real)), "n_random": int(len(rnd)), "n_leagues": int(real.league.nunique()),
               "seasons": seasons, "trade_coefs": coefs, "side_coefs": dict(zip(["lineup", "box_fair"], np.round(sm.coef_[0], 4))),
               "side_intercept": round(float(sm.intercept_[0]), 4), "side_auc_app": side_auc_app,
               "side_auc_refit_cv": float(np.mean(side_cv)) if side_cv else None, "model_right_when_box_disagrees": win_dis,
               "n_box_disagree": int(len(disagree)), "conditional_coefs": cond_coefs,
               "random_utility_quantiles": q, "real_utility_pct_above_random_median": float((raw_util[d.kind == "real"] > q[.5]).mean())}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pd.set_option("display.width", 200)
    print(f"\n{len(real)} real trades from {real.league.nunique()} leagues; {len(rnd)} random comparisons")
    print(auc.round(3).to_string(index=False)); print(cv.round(3).to_string(index=False))
    print(pct.round(3).to_string(index=False)); print(pd.DataFrame(cond).round(3).to_string(index=False))
    print(desc.round(3).to_string()); print(win.round(3).to_string(index=False))
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
