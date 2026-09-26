import math

import numpy as np
import pandas as pd
import pytest

from tdmodel.model import Config, implied_points, poisson_sf, project_week
from tdmodel.parlay import Slip, build_slip, default_legs, legs_from_lines, norm_name

TEAMS = ["AAA", "BBB", "CCC", "DDD"]


def test_poisson_sf_matches_closed_form():
    lam = 1.7
    assert poisson_sf(lam, 0.5) == pytest.approx(1 - math.exp(-lam))
    p_le1 = math.exp(-lam) * (1 + lam)
    assert poisson_sf(lam, 1.5) == pytest.approx(1 - p_le1)
    assert poisson_sf(np.array([0.0, lam]), 0.5)[0] == pytest.approx(0.0)


def test_implied_points_home_favored_positive_spread():
    home, away = implied_points(48.0, 6.0)
    assert (home, away) == (27.0, 21.0)


def test_norm_name_strips_suffixes_and_punctuation():
    assert norm_name("Kenneth Walker III") == norm_name("kenneth walker")
    assert norm_name("Amon-Ra St. Brown") == "amon ra st brown"


def _synthetic(season=2026):
    """Four teams play a round robin for two seasons; each team has QB/RB/WR/TE."""
    rows, games = [], []
    rng = np.random.default_rng(0)
    weeks = [(season - 1, w) for w in range(1, 13)] + [(season, 1), (season, 2)]
    for s, w in weeks:
        pairs = [(TEAMS[0], TEAMS[1]), (TEAMS[2], TEAMS[3])] if w % 2 else [(TEAMS[0], TEAMS[2]), (TEAMS[1], TEAMS[3])]
        for home, away in pairs:
            gid = f"{s}_{w:02d}_{away}_{home}"
            games.append({"game_id": gid, "season": s, "game_type": "REG", "week": w,
                          "gameday": f"{s}-09-{w:02d}", "gametime": "13:00", "away_team": away,
                          "home_team": home, "away_score": 20, "home_score": 24, "spread_line": 3.0,
                          "total_line": 44.0, "roof": "outdoors", "away_qb_id": f"{away}-QB",
                          "home_qb_id": f"{home}-QB", "away_qb_name": "", "home_qb_name": ""})
            for team, opp in ((home, away), (away, home)):
                rb_td = rng.poisson(0.9 if team == "AAA" else 0.4)
                wr_td = rng.poisson(0.5)
                te_td = rng.poisson(0.2)
                for pos, extra in (("QB", {"attempts": 32, "passing_tds": wr_td + te_td, "carries": 3}),
                                   ("RB", {"carries": 18, "targets": 4, "rushing_tds": rb_td}),
                                   ("WR", {"targets": 9, "receptions": 6, "receiving_tds": wr_td}),
                                   ("TE", {"targets": 5, "receptions": 4, "receiving_tds": te_td})):
                    base = {"player_id": f"{team}-{pos}", "player_display_name": f"{team} {pos}",
                            "position_group": pos, "season": s, "week": w, "season_type": "REG",
                            "game_id": gid, "team": team, "opponent_team": opp, "attempts": 0,
                            "passing_tds": 0, "carries": 0, "rushing_tds": 0, "targets": 0,
                            "receptions": 0, "receiving_tds": 0}
                    base.update(extra)
                    rows.append(base)
    # upcoming week 3: AAA is a big home favorite in a high total, DDD @ CCC is a low total
    for home, away, spread, total in (("AAA", "BBB", 7.0, 52.0), ("CCC", "DDD", 0.0, 38.0)):
        games.append({"game_id": f"{season}_03_{away}_{home}", "season": season, "game_type": "REG",
                      "week": 3, "gameday": f"{season}-09-20", "gametime": "13:00", "away_team": away,
                      "home_team": home, "away_score": np.nan, "home_score": np.nan,
                      "spread_line": spread, "total_line": total, "roof": "outdoors",
                      "away_qb_id": f"{away}-QB", "home_qb_id": f"{home}-QB",
                      "away_qb_name": "", "home_qb_name": ""})
    return pd.DataFrame(rows), pd.DataFrame(games)


def test_project_week_prefers_high_total_and_bounds_probabilities():
    stats, games = _synthetic()
    proj, env = project_week(stats, games, 2026, 3, Config(), only_unplayed=True)
    assert set(env["team"]) == set(TEAMS)
    assert proj["p_anytime_td"].between(0, 1).all()
    qbs = proj[proj["pos"] == "QB"].set_index("team")
    assert len(qbs) == 4  # exactly one QB per team
    # AAA has the highest implied total, so its QB projects the most passing TDs
    assert qbs["lam_pass_td"].idxmax() == "AAA"
    rbs = proj[proj["pos"] == "RB"].set_index("team")
    assert rbs["p_anytime_td"].idxmax() == "AAA"


def test_history_excludes_target_week():
    stats, games = _synthetic()
    # Inject an absurd week-3 result; it must not leak into the week-3 projection.
    leak = stats[(stats["season"] == 2026) & (stats["week"] == 2)].copy()
    leak["week"] = 3
    leak["rushing_tds"] = 50
    a, _ = project_week(stats, games, 2026, 3)
    b, _ = project_week(pd.concat([stats, leak]), games, 2026, 3)
    assert np.allclose(a["lam_td"].to_numpy(), b["lam_td"].to_numpy())


def _legs():
    return pd.DataFrame([
        {"player": "A1", "pos": "RB", "team": "AAA", "opp": "BBB", "game_id": "g1", "total": 50, "market": "anytime_td", "line": 0.5, "side": "more", "prob": 0.70, "multiplier": np.nan},
        {"player": "A2", "pos": "WR", "team": "AAA", "opp": "BBB", "game_id": "g1", "total": 50, "market": "anytime_td", "line": 0.5, "side": "more", "prob": 0.65, "multiplier": np.nan},
        {"player": "B1", "pos": "QB", "team": "BBB", "opp": "AAA", "game_id": "g1", "total": 50, "market": "pass_tds", "line": 1.5, "side": "less", "prob": 0.60, "multiplier": np.nan},
        {"player": "C1", "pos": "RB", "team": "CCC", "opp": "DDD", "game_id": "g2", "total": 40, "market": "anytime_td", "line": 0.5, "side": "more", "prob": 0.55, "multiplier": np.nan},
        {"player": "D1", "pos": "WR", "team": "DDD", "opp": "CCC", "game_id": "g2", "total": 40, "market": "anytime_td", "line": 0.5, "side": "more", "prob": 0.50, "multiplier": np.nan},
    ])


def test_build_slip_one_leg_per_team():
    slip = build_slip(_legs(), 3)
    assert list(slip["player"]) == ["A1", "B1", "C1"]  # A2 skipped: same team as A1
    assert slip["team"].is_unique


def test_longshot_mode_uses_overs_only_and_slip_math():
    slip = build_slip(_legs(), 3, mode="longshot")
    assert (slip["side"] == "more").all()
    s = Slip("x", slip, stake=20)
    assert s.prob == pytest.approx(0.70 * 0.55 * 0.50)
    assert s.fair_multiplier == pytest.approx(1 / s.prob)


def test_legs_from_lines_matches_names_and_sides():
    stats, games = _synthetic()
    proj, _ = project_week(stats, games, 2026, 3)
    lines = pd.DataFrame([
        {"player": "AAA RB", "market": "anytime_td", "line": 0.5, "side": "more", "multiplier": 1.8},
        {"player": "AAA QB", "market": "pass_tds", "line": 1.5, "side": "less", "multiplier": 1.7},
        {"player": "Nobody", "market": "anytime_td", "line": 0.5, "side": "more", "multiplier": 2.0},
    ])
    legs, unmatched = legs_from_lines(proj, lines)
    assert unmatched == ["Nobody"]
    rb = proj.set_index("name").loc["AAA RB", "p_anytime_td"]
    qb_over = proj.set_index("name").loc["AAA QB", "p_pass_over_1.5"]
    assert legs.iloc[0]["prob"] == pytest.approx(rb)
    assert legs.iloc[1]["prob"] == pytest.approx(1 - qb_over)
    assert len(default_legs(proj)) == (proj["pos"] != "QB").sum() + 2 * (proj["pos"] == "QB").sum()


def test_parse_sleeper_lines():
    from tdmodel.sleeper import parse_lines

    def opt(outcome, value, mult, status="active"):
        return {"outcome": outcome, "outcome_value": value, "payout_multiplier": mult,
                "status": status, "line_type": "normal"}

    raw = [
        {"sport": "nfl", "status": "active", "game_status": "pre_game", "subject_id": "1",
         "wager_type": "anytime_touchdowns", "options": [opt("over", 0.5, "1.79"), opt("under", 0.5, "1.78")]},
        {"sport": "nfl", "status": "active", "game_status": "pre_game", "subject_id": "2",
         "wager_type": "passing_touchdowns", "options": [opt("over", 1.5, "1.54"), opt("under", 1.5, "2.10", "suspended")]},
        {"sport": "nfl", "status": "active", "game_status": "pre_game", "subject_id": "1",
         "wager_type": "receiving_yards", "options": [opt("over", 60.5, "1.8")]},
        {"sport": "mlb", "status": "active", "game_status": "pre_game", "subject_id": "9",
         "wager_type": "hits", "options": [opt("over", 0.5, "1.6")]},
    ]
    players = {"1": {"full_name": "Omarion Hampton", "gsis_id": "00-1", "injury_status": None},
               "2": {"full_name": "Josh Allen", "gsis_id": "00-2", "injury_status": "Questionable"}}
    lines = parse_lines(raw, players)
    assert list(lines["market"]) == ["anytime_td", "anytime_td", "pass_tds"]
    assert list(lines["side"]) == ["more", "less", "more"]
    assert lines.iloc[2]["multiplier"] == 1.54 and lines.iloc[2]["player_id"] == "00-2"


def test_kalshi_parse_and_attach():
    from tdmodel.kalshi import attach, parse_markets

    mk = lambda title, bid, ask: {"title": title, "yes_bid_dollars": bid, "yes_ask_dollars": ask}
    prices = parse_markets([
        mk("Trey McBride: 1+ touchdowns", "0.30", "0.34"),
        mk("Trey McBride: 2+ touchdowns", "0.05", "0.07"),
        mk("Case Keenum: 1+ touchdowns", "0.44", "0.96"),  # spread too wide -> ignored
    ], "anytime_td")
    assert len(prices) == 2 and prices.iloc[0]["kalshi_prob"] == pytest.approx(0.32)
    prices["key"] = prices["player"].map(norm_name)
    legs = pd.DataFrame([
        {"player": "Trey McBride (Q)", "market": "anytime_td", "line": 0.5, "side": "more"},
        {"player": "Trey McBride", "market": "anytime_td", "line": 0.5, "side": "less"},
        {"player": "Case Keenum", "market": "anytime_td", "line": 0.5, "side": "more"},
    ])
    out = attach(legs, prices)
    assert out["kalshi_prob"].iloc[0] == pytest.approx(0.32)
    assert out["kalshi_prob"].iloc[1] == pytest.approx(0.68)
    assert np.isnan(out["kalshi_prob"].iloc[2])
