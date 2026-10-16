"""Trade value: points over replacement, plus a data-driven consolidation discount.

Why a discount: two good players are not worth the sum of their values,
because you can only start so many and the second piece often lands on your
bench. We measure how much each extra piece is really worth by simulating
thousands of trades between realistic rosters and regressing the change in
each team's best starting lineup on the pieces exchanged.
"""
import numpy as np
import pandas as pd

from .config import POSITIONS, League

LINEUP_POS = ["QB", "RB", "WR", "TE"]


def vorp(df, col, league):
    """Points over the replacement-level player at each position."""
    rep_rank = league.replacement_rank()
    out = pd.Series(np.nan, index=df.index)
    for pos, r in rep_rank.items():
        m = df.position == pos
        vals = df.loc[m, col].sort_values(ascending=False)
        rep = vals.iloc[min(r - 1, len(vals) - 1)] if len(vals) else 0
        out[m] = df.loc[m, col] - rep
    return out


def lineup_points(pos, pts, league):
    """Best starting lineup total for one roster (ROS totals)."""
    used = np.zeros(len(pts), bool)
    total = 0.0
    order = np.argsort(-pts)
    for p in LINEUP_POS:
        need = league.starters.get(p, 0)
        for i in order:
            if need == 0:
                break
            if pos[i] == p and not used[i]:
                used[i], need = True, need - 1
                total += pts[i]
    flex = league.starters.get("FLEX", 0)
    for i in order:
        if flex == 0:
            break
        if pos[i] in ("RB", "WR", "TE") and not used[i]:
            used[i], flex = True, flex - 1
            total += pts[i]
    return total


def _draft(pool, league, rng, noise=12.0):
    """Snake draft by noisy value over replacement with sane positional caps."""
    roster_size = sum(league.starters.values()) + league.bench
    caps = {"QB": 2, "TE": 2, "RB": 7, "WR": 7}
    board = pool.assign(score=pool.vorp + rng.normal(0, noise, len(pool))).sort_values("score", ascending=False)
    available = list(board.index)
    teams = [[] for _ in range(league.teams)]
    counts = [dict.fromkeys(POSITIONS, 0) for _ in range(league.teams)]
    for rnd in range(roster_size):
        order = range(league.teams) if rnd % 2 == 0 else reversed(range(league.teams))
        for t in order:
            for j, pid in enumerate(available):
                p = pool.at[pid, "position"]
                if counts[t][p] < caps[p]:
                    teams[t].append(pid)
                    counts[t][p] += 1
                    available.pop(j)
                    break
    return teams, available


def _settle(roster, free_agents, pool, league):
    """After a trade: fill open spots from waivers, drop the worst if over the limit."""
    size = sum(league.starters.values()) + league.bench
    roster = list(roster)
    fa = sorted(free_agents, key=lambda i: -pool.at[i, "proj"])
    while len(roster) < size and fa:
        roster.append(fa.pop(0))
    while len(roster) > size:
        roster.remove(min(roster, key=lambda i: pool.at[i, "proj"]))
    return roster


def simulate_trades(snapshot, league=None, n_leagues=20, trades_per_league=150, seed=7, col="proj"):
    """Random trades between drafted rosters; returns per-trade lineup change and pieces."""
    league = league or League()
    rng = np.random.default_rng(seed)
    pool = snapshot[snapshot.position.isin(POSITIONS)].copy()
    pool["proj"] = pool[col]
    pool["vorp"] = vorp(pool, "proj", league)
    pool = pool[pool.vorp > -60]
    rows = []
    for _ in range(n_leagues):
        teams, fa = _draft(pool, league, rng)
        for _ in range(trades_per_league):
            a, b = rng.choice(league.teams, 2, replace=False)
            na, nb = rng.integers(1, 4), rng.integers(1, 4)
            # trade from the top of rosters: nobody trades two waiver guys
            top_a = sorted(teams[a], key=lambda i: -pool.at[i, "vorp"])[:9]
            top_b = sorted(teams[b], key=lambda i: -pool.at[i, "vorp"])[:9]
            give = list(rng.choice(top_a, na, replace=False))
            get = list(rng.choice(top_b, nb, replace=False))
            before = lineup_points(pool.loc[teams[a], "position"].values, pool.loc[teams[a], "proj"].values, league)
            new_a = _settle([i for i in teams[a] if i not in give] + get, fa, pool, league)
            after = lineup_points(pool.loc[new_a, "position"].values, pool.loc[new_a, "proj"].values, league)
            gv = sorted(pool.loc[give, "vorp"].clip(lower=0), reverse=True) + [0, 0, 0]
            rv = sorted(pool.loc[get, "vorp"].clip(lower=0), reverse=True) + [0, 0, 0]
            rows.append({"delta": after - before, **{f"get{k+1}": rv[k] for k in range(3)},
                         **{f"give{k+1}": gv[k] for k in range(3)}})
    return pd.DataFrame(rows)


def fit_package_weights(trades):
    """delta ~ sum_k a_k*get_k - sum_k b_k*give_k + c, weights normalised to the best piece.

    Received pieces and given pieces get separate weights: an extra player you
    receive may never crack your lineup, but depth you send away is replaced
    by a waiver pickup.
    """
    G = trades[[f"get{k}" for k in (1, 2, 3)]].values
    D = trades[[f"give{k}" for k in (1, 2, 3)]].values
    y = trades.delta.values
    X = np.column_stack([G, -D, np.ones(len(y))])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    a, b = coef[:3], coef[3:6]
    tss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - X @ coef) ** 2).sum() / tss
    plain = np.column_stack([G.sum(1) - D.sum(1), np.ones(len(y))])
    pc, *_ = np.linalg.lstsq(plain, y, rcond=None)
    r2_plain = 1 - ((y - plain @ pc) ** 2).sum() / tss
    return {"get_weights": (a / a[0]).round(3).tolist(), "give_weights": (b / b[0]).round(3).tolist(),
            "raw_get": a.round(3).tolist(), "raw_give": b.round(3).tolist(),
            "r2": float(r2), "r2_plain_sum": float(r2_plain)}


def package_value(values, weights):
    v = sorted(values, reverse=True)
    w = list(weights) + [weights[-1]] * max(0, len(v) - len(weights))
    return float(sum(a * b for a, b in zip(v, w)))
