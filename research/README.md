# Research scripts

Reproduces the numbers in `reports/Sleeper Picks profitability deep dive.md`. Outputs go to
`research/out/` (git-ignored).

| Step | Command | What it does |
|---|---|---|
| 1 | `python research/build_features.py` | Walk-forward feature table, 2023–2026: runs the model on data strictly before each week (actual-TD, expected-TD and 50/50 versions) and joins what actually happened. |
| 2 | `python research/compare_models.py` | Head-to-head: position base rate, naive TD rates, three Poisson variants, logistic regression, gradient boosting. Brier, log loss, AUC, calibration, weekly-bootstrap CIs, top-10 hit rates. |
| 3 | `python research/fetch_kalshi.py <dir>` | Downloads Kalshi's settled NFL TD / passing-TD markets and hourly price history (public API, ~10 min). |
| 4 | `python research/kalshi_history.py <dir>` | Pre-kickoff Kalshi price for every settled market. |
| 5 | `python research/market_test.py <snapshot.csv>` | Model vs market accuracy, Sleeper's pricing rule fitted from a same-day Sleeper+Kalshi snapshot, and a replay of betting strategies. |
| 6 | `python research/venue_compare.py [out.csv]` | Live side-by-side: what the same TD pick pays on Sleeper, Kalshi and Polymarket after fees, and each venue's expected value against the exchange midpoint. |

The snapshot CSV for step 5 needs columns `player, market, line, m_over, m_under, kalshi_prob`
(Sleeper multipliers and the Kalshi midpoint for the same props, taken at the same time).

## Kalshi / Polymarket sports formula study

Reproduces `reports/Kalshi sports betting formula.md`. `<games>` and `<props>` are any download
folders. Everything uses public APIs with no account. Downloads resume if re-run.

| Step | Command | What it does |
|---|---|---|
| 1 | `python research/nfl_formula.py` | NFL team-win formula v1 (points rating + home field + rest + backup QB), tuned on 2002–15; accuracy vs the de-vigged sportsbook close, blend test, betting the disagreements. |
| 2 | `python research/nfl_formula_v2.py` | v2: adds recency-weighted offensive/defensive EPA per play, logistic regression fitted on 2007–18. |
| 3 | `python research/fetch_kalshi_games.py <games> [SERIES]` | Settled Kalshi game-winner markets and hourly prices around each start. `--historical [--max-games=N]` does older seasons from `/historical`. |
| 4 | `python research/nfl_vs_kalshi.py <games>` | Formula vs sportsbook vs Kalshi on the same NFL games; bets the formula's disagreements 12h before and at kickoff. |
| 5 | `python research/kalshi_backtest.py <games>` | Calibration, price-bucket returns (taker and maker), rule table split 2025-26 (in-sample) / 2026-27 (out-of-sample), and the resting-bid simulation with maker fee. |
| 6 | `python research/fetch_kalshi_endgame.py [--historical] <games> [SERIES]` then `python research/endgame_backtest.py <games>` | Minute prices late in games; tests buying late-game favorites by price band. |
| 7 | `python research/nfl_player_yards.py` | Player formula for receiving yards, rushing yards and receptions (usage × shrunk efficiency × game environment × opponent), fitted on 2018–23, scored on 2024–26. |
| 8 | `python research/fetch_kalshi_props.py [--historical] <props>` then `python research/props_backtest.py <props>` | Kalshi NFL player ladders at kickoff vs the player formula: calibration, bucket returns, accuracy, betting the disagreements (SE clustered by player-game). |

`research/kalshi_games.py` holds the shared loaders and fee functions, and `research/bankroll_sim.py` the flat-stake / fractional-Kelly
simulator. Kalshi's listed game time (`occurrence_datetime`, or `expected_expiration_time` on
historical markets) is about 3 hours after the actual start; the scripts subtract 3 hours.
