"""NFL: the Caldo win formula vs Kalshi prices vs the sportsbook closing line, same games.

    python research/nfl_vs_kalshi.py <games_dir>

Needs research/out/nfl_formula_predictions.csv (from nfl_formula.py) and the Kalshi game
download (fetch_kalshi_games.py). Reports accuracy of each forecaster and the results of
betting the formula's disagreements with Kalshi, 12 hours before and at kickoff, with fees.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.kalshi_games import load, taker_fee  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
ALIAS = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS", "LVR": "LV", "ARZ": "ARI"}


def team_codes(event: str) -> str:
    return event.split("-")[1][7:]


def own_abbr(row) -> str:
    teams = team_codes(row.event)
    if not str(row.ticker).endswith("~flip"):
        return row.ticker.split("-")[-1]
    other = row.ticker.replace("~flip", "").split("-")[-1]
    return teams[len(other):] if teams.startswith(other) else teams[: len(teams) - len(other)]


def join(games_dir: str) -> pd.DataFrame:
    k = load(Path(games_dir))
    k = k[k["series"] == "KXNFLGAME"].copy()
    k["abbr"] = [ALIAS.get(a, a) for a in (own_abbr(r) for r in k.itertuples())]
    f = pd.read_csv(OUT / "nfl_formula_predictions.csv")
    f = f[f["home_score"].notna()].copy()
    f["kick_date"] = pd.to_datetime(f["gameday"]).dt.date
    k["kick_date"] = (k["date"].dt.tz_convert("America/New_York")).dt.date
    rows = []
    idx = {}
    for r in f.itertuples():
        for side, team in (("home", r.home_team), ("away", r.away_team)):
            idx.setdefault((team, r.kick_date), []).append((r, side))
    for r in k.itertuples():
        hits = idx.get((r.abbr, r.kick_date)) or idx.get((r.abbr, r.kick_date - pd.Timedelta(days=1)))
        if not hits:
            continue
        g, side = hits[0]
        home = side == "home"
        rows.append({**r._asdict(), "game_id": g.game_id, "season": g.season, "side": side,
                     "p_model": g.p_model if home else 1 - g.p_model,
                     "p_book": g.p_market if home else 1 - g.p_market,
                     "won_check": (g.y == 1) if home else (g.y == 0)})
    return pd.DataFrame(rows)


def ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main(games_dir: str) -> None:
    pd.set_option("display.width", 200)
    d = join(games_dir)
    print("matched Kalshi NFL sides:", len(d), " result agreement:", float((d.won == d.won_check).mean()))
    d = d[d.game_id.str.contains("_") & d.won.eq(d.won_check)]
    for col in ("mid_12", "mid_0"):
        x = d.dropna(subset=[col, "p_book"])
        print(f"\nAccuracy on {len(x)} sides with a Kalshi {col}: "
              f"formula {ll(x.p_model, x.won):.4f} | sportsbook close {ll(x.p_book, x.won):.4f} | Kalshi {ll(x[col], x.won):.4f}")
    rows = []
    for when in ("12", "0"):
        x = d.dropna(subset=[f"ask_{when}", f"mid_{when}"])
        cost = x[f"ask_{when}"] + taker_fee(x[f"ask_{when}"])
        for thr in (0.0, 0.03, 0.06):
            b = x[x.p_model - cost > thr]
            pnl = np.where(b.won, 1 / (b[f"ask_{when}"] + taker_fee(b[f"ask_{when}"])) - 1, -1.0)
            for season, s in b.assign(pnl=pnl).groupby("season"):
                rows.append({"when": f"{when}h before", "edge>": thr, "season": season, "bets": len(s),
                             "win_rate": s.won.mean(), "roi": s.pnl.mean(),
                             "se": s.pnl.std(ddof=1) / np.sqrt(len(s)) if len(s) > 1 else np.nan})
    print("\nBetting the formula's disagreements with Kalshi (buy at the ask + fee):")
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    d.to_csv(OUT / "nfl_vs_kalshi.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
