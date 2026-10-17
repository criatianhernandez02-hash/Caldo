"""The Caldo player-stat formula: receiving yards, rushing yards and receptions, from pre-game info only.

    python research/nfl_player_yards.py      # fits on 2018-2023, reports 2024-2026, writes predictions

Why players produce what they do (research_notes/.../why_players_score.md), in the order it
matters: OPPORTUNITY (targets and carries, and the share of the team's) is sticky week to week;
EFFICIENCY (yards per target/carry) is noisy and regresses hard to the position average;
GAME ENVIRONMENT (the betting total and spread: more expected points means more plays, and
favourites run while underdogs throw) scales both; the OPPONENT matters a little.

So for each player and game:
  usage      exponentially weighted per-game targets/carries/receptions (half-life 6 games,
             half the weight carried into a new season) and team shares
  efficiency yards per target / per carry / catch rate, shrunk to the position average
             (25 targets / 40 carries / 25 targets of prior)
  environment team implied points = total/2 +- spread/2, and the team's spread
  opponent   yards allowed to the position, relative to league average (shrunk, 4 games prior)
mean = exp(linear formula of the logs), fitted by Poisson regression; then
P(stat > strike) = share of past player-games with the same predicted-mean band whose
actual/predicted ratio was above strike/mean (an empirical distribution, fitted on the same years).
Kalshi's "k+" markets have strike k - 0.5, which also handles whole-number counts like receptions.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import PoissonRegressor

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data_cache"
OUT = Path(__file__).resolve().parent / "out"
SEASONS = range(2018, 2027)
HL, CARRY = 6.0, 0.5
FIT_SEASONS = range(2018, 2024)
PRIOR = {"ypt": {"WR": 8.2, "TE": 7.2, "RB": 5.8, "QB": 5.0}, "ypc": {"WR": 6.5, "TE": 4.0, "RB": 4.3, "QB": 5.0},
         "catch": {"WR": 0.63, "TE": 0.70, "RB": 0.76, "QB": 0.5}}
K_T, K_C = 25.0, 40.0
STATS = {
    # target column, positions modelled, feature list
    "receiving_yards": (("WR", "TE", "RB"), ["l_tgt", "l_ypt", "l_tshare", "l_tm_tgt", "l_implied", "spread7",
                                             "l_opp_rec", "l_recyd", "l_n", "is_TE", "is_RB"]),
    "rushing_yards": (("RB", "QB", "WR"), ["l_car", "l_ypc", "l_cshare", "l_tm_car", "l_implied", "spread7",
                                           "l_opp_rush", "l_rushyd", "l_n", "is_QB", "is_WR"]),
    "receptions": (("WR", "TE", "RB"), ["l_tgt", "l_catch", "l_tshare", "l_tm_tgt", "l_implied", "spread7",
                                        "l_opp_rec", "l_rec", "l_n", "is_TE", "is_RB"]),
}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    return re.sub(r"[^a-z]", "", s)


def load_stats() -> pd.DataFrame:
    cols = ["player_id", "player_display_name", "position", "season", "week", "season_type", "game_id", "team",
            "opponent_team", "targets", "receptions", "receiving_yards", "carries", "rushing_yards"]
    s = pd.concat([pd.read_csv(CACHE / f"stats_player_week_{y}.csv", usecols=cols, low_memory=False)
                   for y in SEASONS if (CACHE / f"stats_player_week_{y}.csv").exists()], ignore_index=True)
    s = s[s["season_type"].isin(["REG", "POST"])].copy()
    for c in ("targets", "receptions", "receiving_yards", "carries", "rushing_yards"):
        s[c] = s[c].fillna(0.0)
    return s.sort_values(["season", "week"]).reset_index(drop=True)


def ew_features(df: pd.DataFrame, key: str, cols: list[str], hl: float = HL) -> pd.DataFrame:
    """Pre-game exponentially weighted sums of cols per key (games in order), plus the weight sum n."""
    d = 0.5 ** (1.0 / hl)
    out = np.full((len(df), len(cols) + 1), np.nan)
    vals = df[cols].to_numpy(float)
    state: dict = {}
    for i, (k, season) in enumerate(zip(df[key].to_numpy(), df["season"].to_numpy())):
        st = state.get(k)
        if st is not None:
            sums, n, last = st
            f = d * (CARRY if season != last else 1.0)
            out[i, :-1], out[i, -1] = sums * f, n * f
            state[k] = (sums * f + vals[i], n * f + 1.0, season)
        else:
            out[i, :] = 0.0
            state[k] = (vals[i].copy(), 1.0, season)
    return pd.DataFrame(out, columns=[f"ew_{c}" for c in cols] + ["ew_n"], index=df.index)


def game_context() -> pd.DataFrame:
    g = pd.read_csv(CACHE / "games.csv")
    rows = []
    for r in g.itertuples():
        if pd.isna(r.spread_line) or pd.isna(r.total_line):
            continue
        for team, sign in ((r.home_team, 1), (r.away_team, -1)):
            rows.append({"game_id": r.game_id, "team": team, "implied": r.total_line / 2 + sign * r.spread_line / 2,
                         "spread": sign * r.spread_line})
    return pd.DataFrame(rows)


def build() -> pd.DataFrame:
    s = load_stats()
    team = s.groupby(["game_id", "team", "season", "week"], as_index=False)[["targets", "carries"]].sum()
    team = team.sort_values(["season", "week"]).reset_index(drop=True)
    tf = ew_features(team, "team", ["targets", "carries"])
    team["tm_tgt_pg"] = tf["ew_targets"] / tf["ew_n"]
    team["tm_car_pg"] = tf["ew_carries"] / tf["ew_n"]
    s = s.merge(team[["game_id", "team", "targets", "carries", "tm_tgt_pg", "tm_car_pg"]]
                .rename(columns={"targets": "team_targets", "carries": "team_carries"}), on=["game_id", "team"])
    s = s.sort_values(["season", "week"]).reset_index(drop=True)

    # defence: yards allowed to each position group per game, relative to the league
    s["pg"] = np.where(s["position"].isin(["WR", "TE", "RB", "QB"]), s["position"], "OTHER")
    allowed = s.groupby(["game_id", "opponent_team", "pg", "season", "week"], as_index=False)[
        ["receiving_yards", "rushing_yards"]].sum().sort_values(["season", "week"]).reset_index(drop=True)
    allowed["key"] = allowed["opponent_team"] + "|" + allowed["pg"]
    af = ew_features(allowed, "key", ["receiving_yards", "rushing_yards"], hl=8.0)
    lg = allowed.groupby(["season", "pg"])[["receiving_yards", "rushing_yards"]].transform("mean")
    for c, out in (("receiving_yards", "opp_rec"), ("rushing_yards", "opp_rush")):
        allowed[out] = (af[f"ew_{c}"] + 4 * lg[c]) / ((af["ew_n"] + 4) * lg[c]).clip(lower=1e-6)
    s = s.merge(allowed[["game_id", "opponent_team", "pg", "opp_rec", "opp_rush"]],
                on=["game_id", "opponent_team", "pg"], how="left")
    s = s.sort_values(["season", "week"]).reset_index(drop=True)

    pf = ew_features(s, "player_id", ["targets", "receptions", "receiving_yards", "carries", "rushing_yards",
                                      "team_targets", "team_carries"])
    s = pd.concat([s, pf], axis=1)
    n = s["ew_n"].replace(0, np.nan)
    pos = s["position"].where(s["position"].isin(["WR", "TE", "RB", "QB"]), "WR")
    s["ypt"] = (s["ew_receiving_yards"] + K_T * pos.map(PRIOR["ypt"])) / (s["ew_targets"] + K_T)
    s["ypc"] = (s["ew_rushing_yards"] + K_C * pos.map(PRIOR["ypc"])) / (s["ew_carries"] + K_C)
    s["catch"] = (s["ew_receptions"] + K_T * pos.map(PRIOR["catch"])) / (s["ew_targets"] + K_T)
    s = s.merge(game_context(), on=["game_id", "team"], how="left")
    feats = {
        "l_tgt": np.log(s["ew_targets"] / n + 0.25), "l_car": np.log(s["ew_carries"] / n + 0.25),
        "l_rec": np.log(s["ew_receptions"] / n + 0.25),
        "l_recyd": np.log(s["ew_receiving_yards"].clip(lower=0) / n + 2), "l_rushyd": np.log(s["ew_rushing_yards"].clip(lower=0) / n + 2),
        "l_ypt": np.log(s["ypt"].clip(1, 25)), "l_ypc": np.log(s["ypc"].clip(1, 12)), "l_catch": np.log(s["catch"].clip(0.2, 1)),
        "l_tshare": np.log(s["ew_targets"] / s["ew_team_targets"].replace(0, np.nan) + 0.01),
        "l_cshare": np.log(s["ew_carries"] / s["ew_team_carries"].replace(0, np.nan) + 0.01),
        "l_tm_tgt": np.log(s["tm_tgt_pg"].clip(lower=15)), "l_tm_car": np.log(s["tm_car_pg"].clip(lower=12)),
        "l_implied": np.log(s["implied"].clip(lower=8) / 22), "spread7": s["spread"] / 7,
        "l_opp_rec": np.log(s["opp_rec"].fillna(1).clip(0.5, 2)), "l_opp_rush": np.log(s["opp_rush"].fillna(1).clip(0.5, 2)),
        "l_n": np.log(s["ew_n"] + 1),
        "is_TE": (s["position"] == "TE").astype(float), "is_RB": (s["position"] == "RB").astype(float),
        "is_QB": (s["position"] == "QB").astype(float), "is_WR": (s["position"] == "WR").astype(float),
    }
    s = pd.concat([s, pd.DataFrame(feats)], axis=1)
    s["name_key"] = s["player_display_name"].map(norm_name)
    return s


class StatModel:
    """Poisson mean formula + empirical ratio distribution for one stat."""

    BINS = 10

    def __init__(self, stat: str):
        self.stat = stat
        self.positions, self.features = STATS[stat]

    def usable(self, s: pd.DataFrame) -> pd.Series:
        return s["position"].isin(self.positions) & (s["ew_n"] >= 1) & s[self.features].notna().all(axis=1)

    def fit(self, s: pd.DataFrame) -> "StatModel":
        t = s[self.usable(s) & s["season"].isin(FIT_SEASONS)]
        y = t[self.stat].clip(lower=0)
        self.glm = PoissonRegressor(alpha=1e-4, max_iter=1000).fit(t[self.features], y)
        mu = self.glm.predict(t[self.features])
        self.edges = np.quantile(mu, np.linspace(0, 1, self.BINS + 1)[1:-1])
        b = np.searchsorted(self.edges, mu)
        self.ratios = [np.sort(t[self.stat].to_numpy(float)[b == i] / mu[b == i]) for i in range(self.BINS)]
        return self

    def mean(self, s: pd.DataFrame) -> np.ndarray:
        return self.glm.predict(s[self.features])

    def p_over(self, mu: np.ndarray, strike: np.ndarray) -> np.ndarray:
        """P(stat > strike); a "k+" market has strike k - 0.5."""
        mu, strike = np.asarray(mu, float), np.asarray(strike, float)
        b = np.searchsorted(self.edges, mu)
        out = np.empty(len(mu))
        for i in range(len(mu)):
            r = self.ratios[b[i]]
            out[i] = 1 - np.searchsorted(r, strike[i] / mu[i], side="right") / len(r)
        return np.clip(out, 0.005, 0.995)


def fit_all(s: pd.DataFrame) -> dict[str, StatModel]:
    return {stat: StatModel(stat).fit(s) for stat in STATS}


def ll(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main() -> None:
    pd.set_option("display.width", 200)
    s = build()
    models = fit_all(s)
    thresholds = {"receiving_yards": (25, 40, 50, 60, 75, 100), "rushing_yards": (25, 40, 50, 60, 75, 100),
                  "receptions": (2, 3, 4, 5, 6, 7)}
    for stat, m in models.items():
        print(f"\n== {stat}: formula coefficients ==")
        print(pd.Series(m.glm.coef_, index=m.features).round(3).to_string(), "\n intercept", round(m.glm.intercept_, 3))
        rows = []
        for season in (2024, 2025, 2026):
            t = s[m.usable(s) & (s["season"] == season)]
            mu = m.mean(t)
            naive = t[{"receiving_yards": "ew_receiving_yards", "rushing_yards": "ew_rushing_yards",
                       "receptions": "ew_receptions"}[stat]] / t["ew_n"]
            for k in thresholds[stat]:
                y = (t[stat] >= k).to_numpy(float)
                p = m.p_over(mu, np.full(len(t), k - 0.5))
                pn = m.p_over(naive.clip(lower=0.5).to_numpy(), np.full(len(t), k - 0.5))
                rows.append({"season": season, "k": k, "n": len(t), "hit": y.mean(), "p_formula": p.mean(),
                             "ll_formula": ll(p, y), "ll_recent_avg": ll(pn, y)})
        print(pd.DataFrame(rows).round(4).to_string(index=False))
    keep = ["player_id", "player_display_name", "name_key", "position", "season", "week", "game_id", "team",
            "opponent_team", "receiving_yards", "rushing_yards", "receptions", "targets", "carries", "ew_n"]
    out = s[keep].copy()
    for stat, m in models.items():
        ok = m.usable(s)
        out.loc[ok, f"mu_{stat}"] = m.mean(s[ok])
    OUT.mkdir(exist_ok=True)
    out.to_csv(OUT / "nfl_player_yards_preds.csv", index=False)
    print("\nwrote", OUT / "nfl_player_yards_preds.csv", len(out))


if __name__ == "__main__":
    main()
