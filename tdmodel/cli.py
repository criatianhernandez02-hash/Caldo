"""Command line entry point.

    python -m tdmodel week                      # next unplayed week, projections + parlay card
    python -m tdmodel week --lines lines.csv    # use the exact Sleeper lines/multipliers you see
    python -m tdmodel backtest --season 2025    # how the model did on a past season
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest as bt
from .data import DEFAULT_CACHE, load_games, load_player_weeks
from .model import Config, project_week
from .parlay import DEFAULT_PLAN, default_legs, legs_from_lines, load_lines, weekly_card
from . import kalshi, sleeper

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def next_week(games: pd.DataFrame) -> tuple[int, int]:
    reg = games[games["game_type"] == "REG"]
    today = dt.date.today().isoformat()
    season = int(reg[reg["gameday"] <= today]["season"].max()) if (reg["gameday"] <= today).any() else int(reg["season"].min())
    upcoming = reg[(reg["season"] == season) & reg["home_score"].isna()]
    if upcoming.empty:
        return season + 1, 1
    return season, int(upcoming["week"].min())


def _pct(x):
    return "" if pd.isna(x) else f"{100 * x:.0f}%"


def print_week(proj: pd.DataFrame, env: pd.DataFrame, top: int) -> None:
    print("\n=== GAME ENVIRONMENT (Vegas) - high totals = more TDs to go around ===")
    games_tbl = (env.sort_values("total", ascending=False)
                 .groupby("game_id", sort=False)
                 .apply(lambda g: pd.Series({
                     "kickoff": f"{g['gameday'].iloc[0]} {g['gametime'].iloc[0]}",
                     "total": g["total"].iloc[0],
                     "implied": "  ".join(f"{t} {p:.1f}" for t, p in zip(g["team"], g["implied_pts"])),
                     "shootout": "YES" if g["shootout"].iloc[0] else "",
                 }), include_groups=False))
    print(games_tbl.to_string())

    cols = {"name": "player", "pos": "pos", "team": "tm", "opp": "vs", "total": "total",
            "implied_pts": "tm_pts", "carry_share": "carry%", "target_share": "tgt%",
            "def_rank_vs_pos": "def_rank", "matchup_mult": "matchup", "lam_td": "exp_TDs",
            "p_anytime_td": "P(TD)"}
    for label, pos in (("RUNNING BACKS", ["RB"]), ("WIDE RECEIVERS / TIGHT ENDS", ["WR", "TE"])):
        t = proj[proj["pos"].isin(pos)].sort_values("p_anytime_td", ascending=False).head(top)
        t = t[list(cols)].rename(columns=cols)
        for c in ("carry%", "tgt%", "P(TD)"):
            t[c] = t[c].map(_pct)
        print(f"\n=== ANYTIME TD - {label} (def_rank 1 = defense allowing the most TDs to that position) ===")
        print(t.round(2).to_string(index=False))

    q = proj[proj["pos"] == "QB"].sort_values("lam_pass_td", ascending=False)
    q = q[["name", "team", "opp", "total", "implied_pts", "def_rank_vs_pos", "lam_pass_td",
           "p_pass_over_0.5", "p_pass_over_1.5", "p_pass_over_2.5"]].rename(columns={
        "name": "qb", "team": "tm", "opp": "vs", "implied_pts": "tm_pts", "def_rank_vs_pos": "def_rank",
        "lam_pass_td": "exp_passTD", "p_pass_over_0.5": "1+", "p_pass_over_1.5": "2+ (o1.5)",
        "p_pass_over_2.5": "3+ (o2.5)"})
    for c in ("1+", "2+ (o1.5)", "3+ (o2.5)"):
        q[c] = q[c].map(_pct)
    print("\n=== QB PASSING TDs ===")
    print(q.round(2).to_string(index=False))


def print_card(slips, stake: float) -> None:
    print(f"\n=== PARLAY CARD (${stake:.0f} per slip, ${stake * len(slips):.0f} total) ===")
    print("Win % assumes legs are independent. 'Fair payout' = the multiplier Sleeper must pay for the")
    print("slip to break even by this model; if Sleeper shows MORE than that, the slip is +EV.")
    for s in slips:
        if s.legs.empty:
            print(f"\n--- {s.name}: no legs cleared the edge filter (try --min-edge -0.05 or --allow-negative)")
            continue
        print(f"\n--- {s.name}:  model win chance {s.prob:.1%}  |  fair payout {s.fair_multiplier:.1f}x")
        for _, leg in s.legs.iterrows():
            mkt = "Anytime TD (Rush+Rec)" if leg["market"] != "pass_tds" else "Pass TDs"
            mult = "" if pd.isna(leg["multiplier"]) else f"  [{leg['multiplier']}x]"
            k = ""
            if "kalshi_prob" in leg and pd.notna(leg["kalshi_prob"]):
                k = f"  (model {leg['model_prob']:.0%}, Kalshi {leg['kalshi_prob']:.0%})"
            print(f"   {leg['player']:<24} {leg['pos']:<3} {leg['team']:>3} vs {leg['opp']:<3} "
                  f"{mkt} {leg['side'].upper()} {leg['line']}  ->  {leg['prob']:.0%}{mult}{k}")
        if not np.isnan(s.multiplier):
            ev = s.expected_return - s.stake
            print(f"   Sleeper payout {s.multiplier:.2f}x -> ${s.stake * s.multiplier:.0f} if it hits; "
                  f"model expected profit {ev:+.2f}")


def print_value_board(legs: pd.DataFrame, top: int) -> None:
    v = legs.dropna(subset=["multiplier"]).copy()
    v["breakeven"] = 1 / v["multiplier"]
    v["edge"] = v["prob"] * v["multiplier"] - 1
    v = v.sort_values("edge", ascending=False).head(top)
    v["pick"] = [f"{'Anytime TD' if m != 'pass_tds' else 'Pass TDs'} {s.upper()} {l}"
                 for m, s, l in zip(v["market"], v["side"], v["line"])]
    cols = ["player", "pos", "team", "opp", "pick", "multiplier", "breakeven"]
    pct = ["breakeven", "prob"]
    if "kalshi_prob" in v:
        cols += ["model_prob", "kalshi_prob"]
        pct += ["model_prob", "kalshi_prob"]
    t = v[cols + ["prob", "edge"]].copy()
    for c in pct:
        t[c] = t[c].map(_pct)
    t["edge"] = t["edge"].map(lambda e: f"{e:+.0%}")
    t = t.rename(columns={"model_prob": "model", "kalshi_prob": "kalshi", "prob": "used"})
    what = "blend of model + Kalshi" if "kalshi_prob" in v else "model win %"
    print(f"\n=== SLEEPER VALUE BOARD ({what} vs the % Sleeper's payout needs; edge = expected profit per $1) ===")
    print(t.to_string(index=False))


def print_disagreements(legs: pd.DataFrame, n: int = 10) -> None:
    d = legs.dropna(subset=["kalshi_prob"])
    d = d[d["side"] == "more"].assign(diff=lambda x: x["model_prob"] - x["kalshi_prob"])
    d = d.reindex(d["diff"].abs().sort_values(ascending=False).index).head(n)
    if d.empty:
        return
    t = d[["player", "team", "market", "line", "model_prob", "kalshi_prob", "diff"]].copy()
    t["market"] = t["market"].map({"anytime_td": "Anytime TD", "pass_tds": "Pass TDs"}) + " o" + t["line"].astype(str)
    for c in ("model_prob", "kalshi_prob"):
        t[c] = t[c].map(_pct)
    t["diff"] = t["diff"].map(lambda x: f"{x:+.0%}")
    print("\n=== BIGGEST MODEL vs KALSHI DISAGREEMENTS (check news on these) ===")
    print(t.drop(columns="line").rename(columns={"model_prob": "model", "kalshi_prob": "kalshi"}).to_string(index=False))


def cmd_week(args) -> None:
    if args.probability_play:
        args.allow_negative = args.overs_only = args.overlap = True
    games = load_games(args.cache, args.refresh)
    season, week = (args.season, args.week) if args.season and args.week else next_week(games)
    stats = load_player_weeks([season - 1, season], season, args.cache, args.refresh)
    proj, env = project_week(stats, games, season, week, Config(), only_unplayed=not args.include_played)
    if args.exclude:
        out = {n.strip().lower() for n in args.exclude.split(",")}
        proj = proj[~proj["name"].str.lower().isin(out)]

    injured = pd.DataFrame(columns=["name", "injury_status"])
    if args.sleeper:
        inj = sleeper.injury_report(args.cache, args.refresh).drop_duplicates("player_id")
        proj = proj.merge(inj, on="player_id", how="left")
        skip = proj["injury_status"].isin(sleeper.SKIP_STATUSES)
        injured = proj.loc[skip, ["name", "injury_status"]]
        proj = proj[~skip].reset_index(drop=True)
    print(f"Season {season}, week {week}: {env['game_id'].nunique()} games, {len(proj)} players projected")
    if len(injured):
        print("Dropped (Sleeper injury status): " +
              ", ".join(f"{n} ({s})" for n, s in zip(injured["name"], injured["injury_status"])))
    print_week(proj, env, args.top)

    unmatched = []
    if args.sleeper:
        lines = sleeper.fetch_lines(args.cache, args.refresh)
        if lines.empty:
            print("\nSleeper has no NFL touchdown lines up right now; using model-only legs.")
            legs = default_legs(proj)
        else:
            legs, unmatched = legs_from_lines(proj, lines)
    elif args.lines:
        legs, unmatched = legs_from_lines(proj, load_lines(args.lines))
    else:
        legs = default_legs(proj)
    if unmatched:
        print(f"\n(no projection for: {', '.join(sorted(set(unmatched)))})")
    if "injury_status" in proj:
        q = set(proj.loc[proj["injury_status"] == "Questionable", "name"])
        legs["player"] = [f"{p} (Q)" if p in q else p for p in legs["player"]]
    if args.kalshi:
        legs = kalshi.attach(legs, kalshi.fetch_prices())
        legs["model_prob"] = legs["prob"]
        has_k = legs["kalshi_prob"].notna()
        w = args.kalshi_weight
        legs.loc[has_k, "prob"] = (1 - w) * legs.loc[has_k, "model_prob"] + w * legs.loc[has_k, "kalshi_prob"]
        print(f"\nKalshi prices found for {has_k.sum()} of {len(legs)} legs "
              f"(win % = {1 - w:.0%} model + {w:.0%} Kalshi where available).")
        print_disagreements(legs)
    if legs["multiplier"].notna().any():
        print_value_board(legs, args.top)
    sizes = [int(x) for x in args.sizes.split(",")]
    plan = [(name, n, mode) for (name, _, mode), n in zip(DEFAULT_PLAN, sizes)]
    slips = weekly_card(legs, args.stake, plan, overlap=args.overlap, overs_only=args.overs_only,
                        min_edge=None if args.allow_negative else args.min_edge)
    print_card(slips, args.stake)

    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        proj.to_csv(Path(args.out) / f"projections_{season}_w{week}.csv", index=False)
        legs.to_csv(Path(args.out) / f"legs_{season}_w{week}.csv", index=False)
        print(f"\nSaved CSVs to {args.out}/")


def cmd_backtest(args) -> None:
    games = load_games(args.cache, args.refresh)
    stats = load_player_weeks([args.season - 1, args.season], args.season, args.cache, args.refresh)
    lo, hi = (int(x) for x in args.weeks.split("-"))
    r = bt.run(stats, games, args.season, list(range(lo, hi + 1)))
    print(f"Backtest {args.season} weeks {lo}-{hi} (lower Brier = better)\n")
    for name in ("full model", "no matchup", "no vegas lines"):
        m = r[name]
        print(f"{name:<15} anytime-TD Brier {m['atd_brier']:.4f} (base rate {m['atd_brier_baseline']:.4f})   "
              f"QB o1.5 Brier {m['qb_over1.5_brier']:.4f} (base rate {m['qb_over1.5_brier_baseline']:.4f})")
    df = r["full model"]["frame"]
    skill = df[df["pos"] != "QB"]
    print("\nAnytime TD calibration (predicted vs actual):")
    print(bt.calibration(skill, "p_anytime_td", skill["any_td"]).round(3).to_string())
    qb = df[df["pos"] == "QB"]
    print("\nQB over 1.5 pass TDs calibration:")
    print(bt.calibration(qb, "p_pass_over_1.5", qb["passing_tds"] >= 2, bins=(0, .3, .4, .5, .6, .7, 1)).round(3).to_string())
    print("\nModel's top-10 anytime TD picks each week:")
    print(bt.top_pick_hit_rate(df, 10).round(3).to_string(index=False))
    sl = r["slips"]
    print("\nWeekly parlay card results:")
    print(sl.groupby("slip", sort=False).agg(weeks=("hit", "size"), predicted=("pred", "mean"),
                                            hit_rate=("hit", "mean"), avg_legs_hit=("legs_hit", "mean"))
          .round(3).to_string())


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="tdmodel", description="NFL touchdown prop model for Sleeper picks")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--refresh", action="store_true", help="force re-download of current data")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("week", help="project a week and build the parlay card")
    w.add_argument("--season", type=int)
    w.add_argument("--week", type=int)
    w.add_argument("--sleeper", action="store_true",
                   help="pull live Sleeper Picks lines + payouts and drop injured players")
    w.add_argument("--kalshi", action="store_true",
                   help="blend in Kalshi prediction-market prices as a second opinion")
    w.add_argument("--kalshi-weight", type=float, default=0.5, help="weight on Kalshi in the blend (0-1)")
    w.add_argument("--lines", help="CSV of Sleeper lines: player,market,line,side[,multiplier]")
    w.add_argument("--min-edge", type=float, default=0.0,
                   help="with payouts known, only use legs with at least this edge (0.05 = +5%%)")
    w.add_argument("--probability-play", action="store_true",
                   help="just the most likely 'More' picks, ignoring value (= --allow-negative --overs-only --overlap)")
    w.add_argument("--allow-negative", action="store_true", help="keep legs the model rates below breakeven")
    w.add_argument("--stake", type=float, default=20.0)
    w.add_argument("--sizes", default="3,5,8", help="legs per slip: anchor,core,longshot")
    w.add_argument("--overs-only", action="store_true", help="only 'more' legs (no QB unders)")
    w.add_argument("--overlap", action="store_true", help="allow a player in more than one slip")
    w.add_argument("--exclude", help="comma-separated players to drop (injured/inactive)")
    w.add_argument("--include-played", action="store_true", help="keep games already played")
    w.add_argument("--top", type=int, default=20)
    w.add_argument("--out", help="directory to save projection CSVs")
    w.set_defaults(func=cmd_week)

    b = sub.add_parser("backtest", help="walk-forward backtest of a past season")
    b.add_argument("--season", type=int, default=2025)
    b.add_argument("--weeks", default="3-18")
    b.set_defaults(func=cmd_backtest)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
