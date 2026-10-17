# Own quantitative analysis (data pulled 2026-10-17)

All numbers below come from first-party data pulls and code in the Caldo repo (`research/` folder):
Sleeper's live lines feed (api.sleeper.app/lines/available), Kalshi's public market-data API,
nflverse weekly stats, and ffopportunity expected-TD data. Scripts: research/build_features.py,
research/compare_models.py, research/kalshi_history.py, research/market_test.py.

## 1. Sleeper's built-in margin (two live snapshots)

Overround = 1/mult_over + 1/mult_under for the same prop (1.00 would be fair).

| Market | 2026-09-26 (wk 3) | 2026-10-17 (wk 6) | Payback per leg (1/overround) |
|---|---|---|---|
| Anytime TD | 1.140 (n=112, range 1.120–1.159) | 1.139 (n=88) | 0.877–0.878 |
| Passing TDs | 1.130 (n=30) | 1.130 (n=24) | 0.885 |
| Yardage/receptions/attempts props | 1.123 | 1.123 | 0.890 |
| First TD scorer | 1.153 | 1.150 | 0.867 |

So Sleeper keeps roughly 11–12% of every leg on yardage props and ~12–13% on TD props, before
any compounding across legs. TD props carry the highest margin of the major prop types.
Sleeper also shades longshot "More" prices hardest: the overround is 1.152 on legs with
fair probability under 30% vs 1.126 near 50%.

Public pick split (Sleeper pick_stats, wk 6): 84–98% of entries take the "More" side of
anytime-TD props in every probability bucket (e.g. Kenneth Walker: 11,809 picks, 99.5% More).

## 2. Sleeper vs Kalshi, same day (wk 6, 107 matched TD/pass-TD props)

- Sleeper's de-vigged probability vs the Kalshi bid/ask midpoint: correlation 0.998, mean absolute
  gap 1.6 percentage points, Sleeper on average 1.2 pp higher on the "More" side. Sleeper's prices
  are effectively the market price plus a margin.
- Using the Kalshi midpoint as the true probability, the expected value of every pickable side:
  - "More" legs: mean -15.8% per $1 (range -26% to -7.6%), 0 of 107 positive.
  - "Less" legs: mean -10.6% per $1 (range -21.5% to -6.2%), 0 of 107 positive.
  - Best single leg on the whole board: -6.2% (Terry McLaurin "Less" 0.5 TD).
- By probability bucket (EV of More / Less): <30%: -22% / -10%; 30–40%: -15% / -10%;
  40–50%: -13% / -10%; 50–60%: -11% / -12%; 60–70%: -11% / -14%.

## 3. Parlay compounding (wk 6 board, Kalshi midpoint as truth, Sleeper payout = product of multipliers)

Expected return on a $20 slip:

| Legs | Probability play (most likely "More" legs) | Safest legs, any side | Least-bad-EV legs | Random legs (avg of 20k) |
|---|---|---|---|---|
| 2 | win 49.0%, 1.69x, -17.2% | win 61.6%, 1.33x, -17.8% | win 49.3%, 1.76x, -13.4% | -24.6% |
| 3 | win 33.3%, 2.21x, -26.2% | win 48.4%, 1.53x, -25.8% | win 26.4%, 3.02x, -20.3% | -34.5% |
| 5 | win 14.3%, 4.06x, -41.9% | win 29.1%, 2.10x, -39.0% | win 8.5%, 7.89x, -32.5% | -50.7% |
| 8 | win 3.6%, 11.72x, -57.5% | win 13.5%, 3.36x, -54.5% | win 2.6%, 20.11x, -48.0% | -67.7% |

## 4. Season simulation (20,000 simulated 17-week seasons, wk-6 board as the weekly menu)

| Weekly plan ($60/week, $1,020/season) | Expected season P&L | Median | 5th pct | 95th pct | P(up for season) |
|---|---|---|---|---|---|
| User's plan: probability play 3/5/8 legs (stacked) | -$427 | -$466 | -$843 | +$128 | 10% |
| Probability play 3/5/8, no repeated players | -$439 | -$525 | -$799 | +$136 | 10% |
| Least-bad-EV legs 3/5/8 | -$364 | -$391 | -$778 | +$164 | 12% |
| Three 2-leg slips, least-bad-EV legs | -$151 | -$153 | -$404 | +$110 | 17% |

## 5. Head-to-head model comparison (walk-forward; every prediction uses only earlier weeks)

Population: RB/WR/TE who played, anytime TD; 2024 (n=2,617), 2025 (n=2,587), 2026 wks 2–6 (n=714).
Brier score (lower = better; base rate ≈ 0.20). CI = weekly-clustered bootstrap of the difference vs
the production model ("poisson_actual").

| Model | 2024 | 2025 | 2026 | Notes |
|---|---|---|---|---|
| Position base rate | 0.2010 | 0.1987 | 0.1937 | no player info |
| Player's own TD rate (naive) | 0.1969 | 0.1986 | 0.1933 | badly overconfident: calibration slope 0.11–0.15 |
| Player's expected-TD rate (naive xTD) | 0.1946 | 0.1919 | 0.1820 | better than actual TDs, still overconfident (slope ~0.7) |
| Production model (Vegas + usage + actual-TD share) | 0.1898 | 0.1880 | 0.1820 | calibration slope ~0.98 |
| Same, expected-TD shares | 0.1905 | 0.1874 | 0.1808 | 2026: -0.0012 vs production, CI [-0.0026, -0.0004] |
| Same, 50/50 actual+expected | 0.1899 | 0.1875 | 0.1812 | 2026: -0.0008, CI [-0.0015, -0.0004] |
| Logistic regression (22 features) | 0.1908 | 0.1888 | 0.1805 | best in 2026 (-0.0016), worse in 2024–25 |
| Gradient boosting | 0.1984 | 0.1941 | 0.1827 | overfits; worst learned model |
| Logistic+GBM ensemble | 0.1926 | 0.1903 | 0.1807 | |

AUC of the best models ≈ 0.65–0.66. Top-10 anytime-TD picks per week (2024–26, 370 picks):
actual hit rate 57.3% (production), 58.7% (50/50 mix), 57.0% (logistic), 53.0% (GBM),
51.1% (naive actual-TD rate).

QB 2+ passing TDs (2024–26, n=990): base rate 0.2501, production Poisson 0.2378, xTD Poisson
0.2375, logistic 0.2368, GBM 0.2445. AUC ≈ 0.62–0.63.

Takeaways: (a) Vegas implied totals + usage-based shares are the core signal, (b) expected-TD
(red-zone/usage quality) beats actual TDs as the "who gets the TDs" signal, but only by ~0.001
Brier, (c) more flexible ML (GBM) overfits on this sample size, (d) the ceiling is low: even the
best model's top picks hit ~57–59%, which is roughly the price-implied probability of those picks.

## 6. Kalshi as a venue (wk 6 quotes, 354 TD / pass-TD markets)

Assuming Kalshi's standard taker fee of ceil(0.07 × P × (1−P)) per contract (to verify), the cost of
buying "Yes" at the ask relative to the fair midpoint:

| Fair probability | Spread cost | Fee | Total cost |
|---|---|---|---|
| < 20% | 7.3% | 11.2% | 18.5% |
| 20–35% | 2.1% | 7.6% | 9.6% |
| 35–50% | 1.3% | 4.8% | 6.1% |
| 50–65% | 0.9% | 3.5% | 4.4% |
| > 65% | 1.7% | 2.1% | 3.8% |

So on mid-to-high-probability TD props a single Kalshi contract costs ~4–6% vs Sleeper's
~11–16% per leg, but the cost is still negative EV without a real edge, and Kalshi singles do
not give parlay-style payouts.

## 7. The Week 3 cards we gave the user (graded with nflverse box scores)

- First "value" card (model-only): 3-leg lost (Bhayshul Tuten scored); 5-leg of five "no TD" picks
  (Andrews, Montgomery, Hubbard, Barkley, Kyren Williams) ALL HIT at ~15.15x; 7-leg lost (1 of 7).
- Kalshi-blend card: 2-leg (Montgomery no TD + Hubbard no TD) hit at ~3.09x; 3- and 4-leg versions
  lost (McBride, RJ Harvey did not score).
- Probability play (final card): 3-leg lost (Winston and Willis threw 0 TDs; Gibbs scored 3);
  5-leg and 8-leg lost. Of the 8 legs, 5 hit (Gibbs, Henry, Cam Ward, McCaffrey, Mahomes 2 pass TDs).
- One week is noise; it illustrates how a single miss sinks a long slip.

## 8. Model vs the market (Kalshi pre-kickoff prices, 2026 weeks 1–6)

Data: hourly Kalshi candlesticks for every settled NFL anytime-TD and passing-TD event in 2026
(160 events, 4,256 markets). Price = bid/ask midpoint of the last hourly candle closing at or
before kickoff when the spread is ≤10¢ (3,571 markets), else last trade. Kalshi settlement agreed
with nflverse box scores on 100% of matched player-games.

Anytime TD, 699 player-games where both the model and a tight Kalshi quote exist:

| Predictor | Brier | Log loss | Calibration slope |
|---|---|---|---|
| Position base rate | 0.1953 | 0.5791 | 0.74 |
| Production model | 0.1835 | 0.5512 | 0.96 |
| Model, 50/50 actual+expected TD | 0.1827 | 0.5489 | 1.04 |
| Logistic regression | 0.1819 | 0.5481 | 0.94 |
| Kalshi pre-kickoff price | 0.1813 | 0.5465 | 0.86 |
| 25% model + 75% Kalshi (logit blend) | 0.1810 | 0.5452 | 0.93 |
| 50/50 blend | 0.1811 | 0.5451 | 0.99 |

Brier(Kalshi) − Brier(model) = −0.0014, 95% CI [−0.006, +0.004] (weekly-clustered bootstrap): the
market is at least as accurate as our best model; the difference is not statistically significant
on 6 weeks. QB 2+ passing TDs (n=119): model 0.2170, Kalshi 0.2166, blend 0.2161.

Kalshi calibration (2026, all positions, mid quotes): 1+ TD markets well calibrated
(331 expected vs 324 observed yes, z = −0.48). 2+ TD markets underpriced: 63 observed vs 45.9
expected overall; in the 5–30% band 43 vs 28.8 (z = 2.84). 3+ passing TDs: 34 vs 26.1 (z = 1.74).
Historical check with our model (2024–26): 2+ TD outcomes run 6.5% above a Poisson model
(z = 1.19), i.e. mild TD clustering. 2026 games are scoring 1.5 pts above the Vegas total
(SE 1.46; 2024: +1.48, 2025: +1.15). Interpretation: a possible, not established, underpricing
of multi-TD outcomes; Sleeper offers only 0.5 anytime-TD lines (and pass TDs 0.5/1.5/2.5), so it
is not a Sleeper angle.

## 9. Sleeper's pricing rule (fitted)

From the wk-6 same-day snapshot (107 props), Sleeper's implied probabilities are a near-exact
linear function of the market probability p:
- 1/multiplier("More") = 1.005·p + 0.065
- 1/multiplier("Less") = 1.060·(1−p) + 0.034
- residual SD 0.84 percentage points.
So Sleeper adds ~6.5 points of implied probability to every "More" side and ~3.4 points plus 6%
to every "Less" side. Lines are effectively market price + fixed margin; stale/mispriced lines are
rare at a snapshot (none of 107 were positive EV vs Kalshi on 2026-10-17).

## 10. Strategy replay (2026 anytime-TD legs with Kalshi quotes, synthetic Sleeper multipliers from §9, flat $1/leg)

| Strategy | Bets | Hit rate | Avg multiplier | Realized ROI (± SE) | Market-expected ROI |
|---|---|---|---|---|---|
| Bet every side | 1,398 | 50.0% | 2.41 | −14.9% (±3.0%) | −16.4% |
| Model "value" (model p × mult > 1) | 157 | 32.5% | 3.73 | −10.6% (±12.6%) | −24.3% |
| Model value, edge > 5% | 98 | 26.5% | 4.26 | −15.0% (±17.1%) | −27.6% |
| Logistic "value" | 148 | 38.5% | 3.59 | +1.1% (±13.1%) | −23.6% |
| 50/50 blend "value" | 18 | 27.8% | 4.11 | −52% (±19%) | −26.7% |
| Top-5 most likely "More" legs per week | 25 | 68.0% | 1.63 | −1.2% (±14.7%) | −11.0% |

No strategy is distinguishable from the market's expectation; the model's "value" picks are
concentrated in longshot overs that the market rates as the worst bets on the board (−24% to −28%).
Realized Sleeper-equivalent ROI by market-probability bucket (2026, all 1+ TD markets): "More" on
<20% players −42%, 20–30% −27%; "Less" on <20% players −8.6%, 20–30% −7.2%.

## 11. The user's plan replayed on 2026 weeks 2–5 (model-only probability-play cards, graded)

- 64 legs, 80% hit (model expected 59%) — an unusually lucky stretch for favorites.
- Slips: 3-leg won 3 of 4, 5-leg won 1 of 4, 8-leg won 0 of 4.
- Estimated Sleeper payouts (market prices + fitted pricing rule): about +$10 on $240 staked,
  while the market-expected result for the same slips was −$96.
- Week 5 alone: 12 of 16 legs hit (75%) and all three slips lost.

## 12. Sleeper promo lines (api.sleeper.app/lines/promos, pulled 2026-10-17 ~21:30 UTC)

8 promo lines across all sports (NFL: 2 props). Two kinds observed:
- "line_promotion" with a drastically lowered line: an NFL QB's passing yards More 0.5 at 1.78x
  (regular line 227.5 at 1.78/1.78). A starting QB clears 0.5 passing yards ~98%+ of the time, so
  this leg alone is worth roughly +70% EV per dollar (0.98 × 1.78 − 1 ≈ +0.74). Paired in a 2-pick
  entry with the least-bad regular leg (EV −6%), the entry is still ≈ +60% EV.
- Boosted multiplier on the regular line: receptions More 6.5 boosted 2.03x → 2.20x (Less 1.58x
  → 1.60x). De-vigging the regular line gives fair P(More) ≈ 0.438, so the boost is ≈ −3.7% EV —
  a smaller loss, not a profit.
Promo lines are rare (the mechanics research found 8 of ~9,120 lines on one probe) and Sleeper's
promos carry entry/usage limits (amounts are typically small); they are the only clearly
positive-EV picks observed on Sleeper in this research.

## 13. Sleeper Terms of Service caveat

Per the mechanics research (ToS updated 2026-10-06, §11.1/§11.3, §5.20): scraping, bots and
automated data access are prohibited, and accounts using scripts can be restricted with prizes
clawed back. The Caldo tool's `--sleeper` option reads Sleeper's public lines endpoints
automatically, which falls under that prohibition; manual entry (`--lines`) avoids it.
