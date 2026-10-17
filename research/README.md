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

The snapshot CSV for step 5 needs columns `player, market, line, m_over, m_under, kalshi_prob`
(Sleeper multipliers and the Kalshi midpoint for the same props, taken at the same time).
