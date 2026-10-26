# Own quantitative results (Caldo repo, research/ folder; data pulled 2026-10-17)

All first-party. Data: nflverse schedules/closing lines/team stats (1999-2026), Kalshi public API
(current + /historical endpoints), Polymarket gamma + CLOB price history. Scripts:
research/nfl_formula.py, nfl_formula_v2.py, nfl_vs_kalshi.py, fetch_kalshi_games.py,
kalshi_games.py, kalshi_backtest.py, fetch_kalshi_endgame.py, endgame_backtest.py.

## A. The Caldo NFL win formula (my own)

v1 (points rating, "points Elo"):
- expected_margin = (R_home − R_away) + HFA·(not neutral) + REST·clip(rest_home − rest_away, ±7) + QBADJ·(backup_away − backup_home)
- P(home win) = Φ(expected_margin / SIGMA)
- after each game: R_home += K·(clip(margin, ±CAP) − expected_margin), R_away −= same; each new season R ← (1 − REGRESS)·R
- backup_x = 1 if the starting QB is not the team's most frequent starter in its previous 8 games
- tuned by grid search on 2002–2015 log loss: K = 0.08, HFA = 2.5 pts, REST = 0.2 pts/day, QBADJ = 3.0 pts, REGRESS = 0.33, CAP = 21, SIGMA = 12.5

v2 adds recency-weighted offensive and defensive EPA per play (nflverse team stats, half-life 8 games, 50% carry-over between seasons, 300 pseudo-plays of league average) and fits a logistic regression on [rating_diff, off_diff, def_diff, rest_diff, backup_home, backup_away, home_field] on 2007–2018. Coefficients: rating 0.139, off EPA diff 1.06, def EPA diff 0.61 (wrong sign; collinear with rating), rest 0.034, backup_home −0.35, backup_away +0.21, home field 0.79, intercept −0.42.

| Period (games with closing moneyline) | v1 log loss | v2 log loss | Sportsbook closing line (de-vigged) |
|---|---|---|---|
| 2002/07–2015/18 (fit) | 0.6179 (n=2,535) | 0.6157 (2007–18, n=3,107) | 0.6108 / 0.6059 |
| Validation 2016–24 (v1) / 2019–24 (v2) | 0.6322 (n=2,475) | 0.6346 (n=1,670) | 0.6093 / 0.6085 |
| Test 2025–26 (never used for fitting) | 0.6352 (n=365) | 0.6355 (n=363) | 0.6180 / 0.6171 |

Accuracy (picking the winner), v1 vs market: 65.6% vs 66.1% (2002–15), 64.1% vs 66.6% (2016–24), 63.3% vs 65.5% (2025–26).

Blend test (logit-average of market and v1, weight chosen on 2016–24): optimal weight on the formula = 0.00; every positive weight made validation log loss worse (0.6093 at 0 → 0.6163 at 0.5). The formula carries no information the closing line lacks.

Betting v1's disagreements with the sportsbook closing moneyline (with vig), flat $1:
| Period | Edge filter | Bets | Win rate | ROI (± SE) |
|---|---|---|---|---|
| 2016–24 | > 0 | 2,115 | 40.4% | −6.0% (±2.9%) |
| 2016–24 | > 10% | 1,252 | 32.7% | −9.6% (±4.1%) |
| 2025–26 | > 0 | 293 | 39.6% | −5.7% (±7.8%) |
| 2025–26 | > 10% | 182 | 34.1% | −4.5% (±11.0%) |

Favorite–longshot pattern, NFL closing moneylines 2007–2026 (flat $1 on every side, with vig):
| Fair win prob | Sides | Won vs fair | ROI |
|---|---|---|---|
| < 20% | 574 | 13.2% vs 15.3% | −19.6% |
| 20–30% | 1,309 | 24.4% vs 25.3% | −6.0% |
| 30–40% | 1,702 | 36.2% vs 35.2% | −0.3% |
| 40–50% | 1,581 | 45.4% vs 44.7% | −1.0% |
| 50–60% | 1,529 | 54.7% vs 55.5% | −4.1% |
| 60–70% | 1,702 | 63.8% vs 64.8% | −4.2% |
| 70–80% | 1,314 | 75.6% vs 74.7% | −1.5% |
| > 80% | 569 | 86.6% vs 84.8% | −0.7% |

## B. Three-way accuracy on the same NFL games

2025–26 regular season + playoffs, Polymarket kickoff price (CLOB hourly history) vs sportsbook close vs formula, 344 games:
| Forecaster | Log loss | Brier |
|---|---|---|
| Sportsbook close (de-vigged) | 0.6070 | 0.2105 |
| Polymarket 12h before kickoff | 0.6077 | 0.2108 |
| Polymarket at kickoff | 0.6079 | 0.2109 |
| Caldo formula v1 | 0.6302 | 0.2209 |
Polymarket minus sportsbook (home win prob): mean +0.3 pts, mean absolute gap 1.0 pt, gaps > 3 pts in 1.5% of games. Polymarket settlement matched nflverse results in 100% of games.

2026 season so far, Kalshi NFL (158 matched team sides): log loss formula 0.6530, sportsbook 0.6536, Kalshi 12h before 0.6510; at kickoff formula 0.6515, sportsbook 0.6522, Kalshi 0.6505.
Betting the formula's disagreements with Kalshi in 2026 (taker, with fee): edge > 0: 70 bets, +10.2% (±16.7%); edge > 3%: 48 bets, +23.1% (±21.5%) — noise at this sample size (to be re-checked with the 2025 season).

## C. Kalshi game markets: when does a game actually start?

Kalshi's occurrence_datetime (current markets) and expected_expiration_time (historical markets) sit about 3 hours AFTER the start in every league checked. Median hourly volume and mean absolute hourly price move jump in the hour ending 2h before that time (NFL: 194k → 872k contracts, move 0.012 → 0.137; MLB 0.038 → 0.172; NHL 0.016 → 0.152; NBA 0.034 → 0.144; college football 0.017 → 0.091), and NFL kickoffs from the schedule confirm +3h. Pre-game snapshots therefore use start = that time − 3h.
Kalshi closes a game market a median ~21 minutes after the game is decided (NHL, 354 sides: bid ≥ 97¢ or ask ≤ 3¢ → close; p10 1.4 min, p90 69.6 min), so any "minutes before close" analysis leaks the result.

## D. Kalshi pre-game prices, 2026-27 current seasons (out-of-sample period; 3,410 team sides so far: college FB 1,672, MLB 994, NHL 360, NFL 250, NBA preseason 134)

Calibration of the last pre-game midpoint (price → actual win rate): 4.8¢ → 4.5%; 15.5¢ → 17.1%; 25.7¢ → 25.3%; 35.6¢ → 36.7%; 45.1¢ → 46.5%; 54.9¢ → 53.3%; 64.5¢ → 64.1%; 74.6¢ → 74.2%; 84.8¢ → 82.4%; 95.2¢ → 95.5%. Well calibrated.

Return per $1 by price bucket at the last pre-game hour (take = buy at ask + taker fee 0.07·P·(1−P); make = buy at bid, assumes the order fills, no fee):
| Mid | n | Won | Take ROI | Make ROI (upper bound) |
|---|---|---|---|---|
| 0–10¢ | 202 | 4.5% | −32.1% | −7.7% |
| 10–20¢ | 158 | 17.1% | −0.1% | +15.7% |
| 20–30¢ | 217 | 25.3% | −3.4% | +6.7% |
| 30–40¢ | 379 | 36.7% | −3.7% | +3.7% |
| 40–50¢ | 658 | 46.5% | −1.7% | +4.5% |
| 50–60¢ | 658 | 53.3% | −6.6% | −1.8% |
| 60–70¢ | 390 | 64.1% | −4.1% | −0.1% |
| 70–80¢ | 217 | 74.2% | −2.7% | +0.8% |
| 80–90¢ | 153 | 82.4% | −4.6% | −2.3% |
| 90–100¢ | 198 | 95.5% | −0.6% | +0.8% |

Rules (out-of-sample period, all sports pooled, taker with fee; in-sample 2025-26 NFL+NHL figures in section G): buy every side 12h early −4.5% (±2.3%) vs at the start −5.4% (±2.2%) (3,527 sides); longshots < 20¢ −18.0% (±15.7%); 20–40¢ −4.9% (±5.6%); 40–60¢ −4.4% (±2.5%); favorites 60–80¢ −3.1% (±2.6%); heavy favorites 80–95¢ −3.1% (±2.5%); follow a ≥4¢ move from 12h to 1h before: −3.3% (±7.1%, 202 bets); fade it: −9.7% (±8.4%, 185); resting bids on 60–95¢ favorites (if filled, no fee): +0.3% (±2.1%, 898).

## E. Late-game favorites (1-minute data, rule without look-ahead)

Rule: from T minutes after the estimated start (NHL/NBA 110, MLB 150, NFL 160, college FB 170), buy the first minute a side's ask enters a band (spread ≤ 5¢), hold to settlement, taker fee included. Current-season NHL so far (144 games):
| Band | Bets | Avg ask | Won | ROI (± SE) |
|---|---|---|---|---|
| 70–85¢ | 97 | 77.0¢ | 81.4% | +4.3% (±5.1%) |
| 85–92¢ | 96 | 87.3¢ | 90.6% | +2.9% (±3.4%) |
| 92–96¢ | 87 | 92.8¢ | 94.3% | +1.0% (±2.7%) |
| 96–98.5¢ | 88 | 96.7¢ | 96.6% | −0.4% (±2.0%) |
Direction matches the published finding that late-game leaders are underpriced in the NHL; not statistically significant.

Independent test, 2025-26 NHL season (historical endpoint, reproducible random sample of 300 games, both sides; same rule, same fee):
| Band | Bets | Avg ask | Won | ROI (± SE) |
|---|---|---|---|---|
| 70–85¢ | 201 | 77.0¢ | 75.1% | −4.0% (±3.9%) |
| 85–92¢ | 197 | 87.3¢ | 83.3% | −5.4% (±3.0%) |
| 92–96¢ | 195 | 93.2¢ | 90.3% | −3.6% (±2.3%) |
| 96–98.5¢ | 182 | 96.8¢ | 95.6% | −1.4% (±1.6%) |
The earlier, larger season reverses the sign in every band: late-game NHL leaders were OVERpriced in 2025-26. Pooled over both seasons the rule loses in three of four bands (−1% to −3%). Not a usable edge.

MLB, same rule from 150 minutes after the estimated start:
| Band | 2026 bets | ROI (± SE) | 2025 bets (300-game sample) | ROI (± SE) |
|---|---|---|---|---|
| 70–85¢ | 221 | −2.2% (±3.6%) | 92 | −7.6% (±6.0%) |
| 85–92¢ | 252 | +0.1% (±2.2%) | 90 | −0.8% (±3.9%) |
| 92–96¢ | 274 | −0.9% (±1.6%) | 92 | +0.9% (±2.5%) |
| 96–98.5¢ | 303 | +0.3% (±1.0%) | 106 | +1.9% (±1.0%) |
Break-even. The top band is mildly positive in both seasons (~+0.7% ± 0.7% pooled), which is not exploitable at $1 risked per 2–3¢ won.

## F. NFL formula vs Kalshi over two seasons (2025 historical + 2026 to date; 712-714 matched team sides)

Log loss: formula 0.6371 | sportsbook close 0.6196 | Kalshi 12h before 0.6201 (12h snapshot); at kickoff formula 0.6367 | sportsbook 0.6192 | Kalshi 0.6195. Kalshi and the sportsbook close are equally accurate; the formula trails both by ~0.017.

Betting the formula's disagreements with Kalshi (buy at the ask + taker fee):
| When | Edge filter | 2025 bets | 2025 ROI (± SE) | 2026 bets | 2026 ROI (± SE) |
|---|---|---|---|---|---|
| 12h before | > 0 | 223 | −7.0% (±8.7%) | 70 | +10.2% (±16.7%) |
| 12h before | > 3% | 158 | −10.0% (±10.7%) | 48 | +23.1% (±21.5%) |
| 12h before | > 6% | 102 | −15.2% (±12.5%) | 29 | +12.6% (±28.3%) |
| at kickoff | > 0 | 222 | −4.7% (±8.7%) | 68 | +11.2% (±17.2%) |
| at kickoff | > 3% | 153 | −8.5% (±10.5%) | 47 | +24.9% (±22.7%) |
| at kickoff | > 6% | 94 | −18.6% (±12.5%) | 29 | +12.1% (±28.2%) |
The larger, earlier season reverses the small 2026 sample: no evidence the formula beats Kalshi.

## G. Pre-game rules on two seasons (2025-26 in-sample: NFL 654 + NHL 600 team sides from /historical; 2026-27 out-of-sample: 3,744 sides)

| Rule (taker at ask + fee, last pre-game hour) | 2025-26 bets | ROI (± SE) | 2026-27 bets | ROI (± SE) |
|---|---|---|---|---|
| Buy every side at the start | 1,216 | −4.3% (±3.0%) | 3,551 | −5.4% (±2.2%) |
| Buy every side 12h early | 1,216 | −4.2% (±3.0%) | 3,551 | −4.6% (±2.3%) |
| Longshots < 20¢ | 40 | −58.9% (±23.5%) | 361 | −16.8% (±15.7%) |
| 20–40¢ | 279 | +5.4% (±8.6%) | 648 | −5.2% (±5.6%) |
| Coin flips 40–60¢ | 602 | −4.2% (±4.0%) | 1,540 | −4.4% (±2.5%) |
| Favourites 60–80¢ | 280 | −8.0% (±4.2%) | 659 | −3.0% (±2.6%) |
| Heavy favourites 80–95¢ | 39 | +6.2% (±5.0%) | 242 | −3.5% (±2.5%) |
| Follow a ≥4¢ move 12h→1h | 33 | +2.0% (±15.3%) | 203 | −3.8% (±7.1%) |
| Fade a ≥4¢ move 12h→1h | 32 | −25.2% (±17.8%) | 186 | −8.9% (±8.4%) |
NFL underdogs 20–40¢ were positive in both periods (+13.6% ±11.3% on 182; +15.6% ±18.7% on 62), but NHL 20–40¢ was negative in both (−10.1%, −33.2%), the sportsbook history for NFL 20–40% sides is −0.3% to −6.0% over 7,300+ games, and this is one of ~40 rule×sport cells — treat as noise.

Resting bids (post a limit at the 12h bid, filled only if a later hourly trade prints at or below it; maker fee 0.0175·P·(1−P) included):
| Quoted sides | 2025-26 fills, ROI (± SE) | 2026-27 fills, ROI (± SE) |
|---|---|---|
| All sides, at the bid | NFL 446: +4.5% (±5.7%); NHL 326: −6.0% (±5.7%) | CFB 618 −5.8%; MLB 609 +3.9% (±4.2%); NFL 119 +6.7% (±10.6%); NHL 154 −13.5%; NBA 76 −16.3% |
| Favourites 60–95¢, at the bid | NFL 151: −5.0%; NHL 42: −11.7% | CFB 235 −8.6% (±3.8%); MLB 77 +16.6% (±7.7%); NFL 31 −16.0%; NBA 29 −27.8% |
| Favourites 60–95¢, 2¢ under the bid | NFL 32: −17.5%; NHL 11: −40.8% | CFB 76 −5.2%; MLB 26 +20.0%; NBA 20 −41.9% |
Fill rates 40–70% at the bid, ~15% two cents under. Adverse selection dominates: a resting bid gets filled mostly when news pushes the price down, so filled bids lose. No sport is positive in both periods.

## H. Sportsbook close vs Kalshi, NFL 2025 + 2026 (720 matched sides)
Kalshi's kickoff mid minus the de-vigged sportsbook closing probability, by sportsbook bucket: <20%: −0.1 pt; 20–30%: −0.3; 30–40%: −0.6; 40–50%: −0.2; 50–60%: +0.2; 60–70%: +0.6; 70–80%: +0.3; >80%: +0.1. Kalshi tilts very slightly toward favourites but tracks the sportsbook to within a point. Sides where the sportsbook's fair probability beat Kalshi's ask + fee at kickoff: 47 in 2025 (+18.3% ±19.8%) and 11 in 2026 — too rare and too noisy to be a strategy.

## I. Player formula vs Kalshi NFL player markets (receiving yards, rushing yards, receptions)

Formula: research/nfl_player_yards.py (usage × shrunk efficiency × environment × opponent, Poisson mean fitted on 2018–23, empirical ratio distribution). Out of sample 2025: 50+ receiving yards hit 15.5% vs formula 17.2% (log loss 0.3157 vs recent-average 0.3202); 50+ rushing 9.9% vs 10.0% (0.1719 vs 0.1739); 4+ receptions 22.1% vs 23.8% (0.3717 vs 0.3756).

Kalshi data:
- 2026 weeks 1–6: 18,859 settled markets (every rung), 1,189 player-games, last hourly quote at or before kickoff.
- 2025 weeks 4–18: half the games, middle rung only, 1,932 markets. Kalshi's NFL player markets started ~week 6 of 2025: median ~600 contracts per market, average middle-rung spread 5.2¢, vs 1.3–2.3¢ in 2026.
- Settlement matched the box score in 100% of markets.
- Players with no box-score line are kept, with the formula computed from their history. This matters: 49 veterans priced normally at kickoff recorded no stats, and every YES on them lost. Dropping them inflated YES returns.

2026 bucket returns at kickoff (all rungs):
| Price | n | Hit | YES at ask + fee | NO at ask + fee |
|---|---|---|---|---|
| 0–5¢ | 2,272 | 4.0% | −21.8% | −1.5% ± 0.6% |
| 5–10¢ | 2,905 | 8.4% | −7.7% | −2.7% |
| 10–20¢ | 2,877 | 16.0% | −4.4% | −3.5% |
| 30–40¢ | 1,492 | 34.6% | −7.7% | −3.1% |
| 50–60¢ | 1,194 | 51.3% | −10.5% | +2.8% ± 3.6% |
| 80–90¢ | 720 | 83.6% | −2.6% | −6.9% |

Accuracy (log loss), Kalshi vs formula:
- 2025 middle rungs: 0.6749 vs 0.6871 (1,343).
- 2026 weeks 1–3 all rungs: 0.4561 vs 0.4804 (9,357).
- 2026 weeks 4–6 all rungs: 0.4824 vs 0.4928 (7,034).
- Kalshi is better for every stat in every period except 2026 weeks 4–6 rushing middle rungs (0.6261 vs 0.6162, n = 191).
- Blend weight on the formula fitted on weeks 1–3 = 0.

Betting disagreements, all rungs, 2026: weeks 1–3 YES −10.4%, NO −5.1%; weeks 4–6 YES +2.9%, NO +4.3%.

Middle rungs (buy at ask + fee; SE clustered by player-game):
| Rule | 2025 wk 4–18 | 2026 wk 1–3 | 2026 wk 4–6 | Pooled |
|---|---|---|---|---|
| NO, formula under by ≥ 3 pts | +4.0% (437) | +1.3% (361) | +10.5% (313) | +5.0% ± 2.7% (1,111) |
| NO, formula under by > 0 | +2.5% (593) | +1.6% (527) | +6.2% (444) | +3.2% ± 2.2% (1,564) |
| NO, formula under by ≥ 5 pts | +0.6% (348) | −1.3% (266) | +10.9% (250) | +3.0% ± 3.0% (864) |
| YES, formula over by > 0 | −5.0% (306) | +12.2% (488) | +39.0% (326) | +15.3% ± 7.5%, fails in 2025 |
| Blind NO on every middle rung | −0.1% (1,367) | −1.5% (1,364) | −1.2% (975) | −0.9% ± 1.4% (3,706) |

Flat $20 on the ≥ 3-pt NO rule: 1,111 bets, $22,220 staked, +$1,104, max drawdown $353, longest losing streak 11.

Status: the only lead positive in all three periods, but ~1.9 SE after ~40 tests and not monotonic in the threshold. Paper-trade it with research/props_scan.py (17 Oct 2026: 83 candidates for week 6 Sun/Mon).


## J. Unabated's rules applied (26 Oct): CLV, timing, injury news

**CLV on the paper log** (120 picks, Weeks 6–7, entry 1–3 days before kickoff):
- Record 91–29, +$124.50 on $2,350 (+5.3%).
- Mid-to-mid price move toward our side: −0.27¢ ± 0.24. Half-spread paid at entry: 1.35¢.
- Moved our way 42% of the time, against us 44%.

**Timing** (25,025 markets in 2026, 1,543 player-games; 8,646 markets quoted at every horizon):
- Kalshi log loss by hours before kickoff: 72h 0.4670, 48h 0.4672, 24h 0.4655, 12h 0.4641, 6h 0.4642, 1h 0.4631, 0h 0.4630. The formula scores 0.4737 on the same markets.
- Spread by hours before kickoff: 4.7¢, 3.7¢, 3.0¢, 1.9¢, 1.8¢, 1.5¢, 1.7¢.

**Rule A** (NO on the middle rung, formula under by 3–10 points), by entry time:

| Entry | All players: bets, ROI (± SE), CLV | No-news players: bets, ROI (± SE), CLV |
|---|---|---|
| 72h | 165, +15.8% (±4.7), +0.30¢ | 48, +8.3% (±8.6), +0.59¢ |
| 48h | 359, +11.1% (±3.4), +0.24¢ | 103, +5.3% (±6.2), +0.30¢ |
| 24h | 442, +7.5% (±3.3), +0.02¢ | 120, +2.2% (±6.5), +0.27¢ |
| 12h | 535, +5.2% (±3.0) | 153, −0.0% (±5.6) |
| 6h | 575, +3.7% (±2.9) | 159, +3.1% (±5.5) |
| 1h | 626, +5.9% (±2.8) | 178, +3.0% (±5.5) |
| Kickoff | 623, +5.2% (±2.8) | 181, +1.8% (±4.9) |

The early-entry gains in the all-players column use injury knowledge the market lacked at the time (look-ahead). The no-news column is the fair test.

**Injury cases at kickoff (2026, all rungs):**
- Position group lost a regular (backup's line): priced 30.8%, hit 30.9%; buy NO −1.8% (4,478 markets, 312 player-games). Priced right.
- Group got a regular back: priced 30.3%, hit 26.3%; buy NO +4.8% (±4.0). Kalshi log loss 0.4480 vs formula 0.4397: the formula beats Kalshi here.
  - The returning player himself: 15 player-games; noise.
  - A teammate is returning: priced 30.3%, hit 25.4%; NO +7.0% (±4.2); middle rung +9.8% (±4.3), 263 markets.
- No team news: NO −5.2% (±2.4).
- 2025 replication (middle rungs): a teammate returning was priced 44.6%, hit 39.6%; NO +3.1% (±7.5), 187 markets, 124 player-games. No team news: NO −3.2%.

This became rule B in props_scan.py (skill positions only; the returning player must be confirmed active on the roster).


## K. Kalshi NFL total-points and spread ladders vs the sportsbook close (2026 Weeks 1–7; research/ladders_backtest.py)

**Data:** 4,719 priced rungs in 106 games (2,705 spread rungs, 2,014 totals), last quote at kickoff, spread ≤ 10¢. Sportsbook-fair probability = the closing line plus the empirical 2012–2025 distribution of actual minus line.

**Accuracy (log loss):**

| Ladder | Kalshi | Sportsbook-implied |
|---|---|---|
| Spreads | 0.5138 | 0.5115 |
| Totals | 0.5084 | 0.5078 |

**Calibration:** close in most buckets. Spreads priced 65–80¢ (93 rungs): Kalshi said 71%, book said 67%, hit 56%. Small sample.

**Sides priced 85–90¢:**

| Ladder | Bets | Avg price | Won | ROI (± SE) |
|---|---|---|---|---|
| Spreads | 385 | 87.5¢ | 86.5% | −2.5% (±2.7%) |
| Totals | 231 | 87.6¢ | 87.0% | −2.2% (±2.4%) |

**Buying the side cheaper on Kalshi than the book's fair probability (taker + fee), clustered by game:**

| Edge filter | Bets | ROI (± SE) | By ladder |
|---|---|---|---|
| > 0 | 2,004 | +3.8% (±8.7%) | totals −2.5%; spreads +6.8% |
| > 2 points | 409 | +9.3% (±9.9%) | — |
| > 4 points | 93 | +6.7% (±15.7%) | — |

**By volume (rung median contracts):**

| Band | Median contracts | Kalshi said | Hit | +EV bets | ROI (± SE) |
|---|---|---|---|---|---|
| Thin | 13k | 31.6% | 25.9% | 638 | −47.6% (±4.7%) |
| Mid | 73k | — | — | 682 | +18.2% (±13.7%) |
| Deep | 344k | — | — | 684 | +37.2% (±13.9%) |

**By distance from the main line:**

| Distance | ROI |
|---|---|
| Within 3 points | −0.8% |
| 4–7 points | +13.7% (±7.8%) |
| 8–14 points | +0.5% |
| 15+ points | +1.6% |

**Caveats:**
- The book fair price for alternate rungs is modelled from the main line, not real alternate-line odds.
- League-wide scoring moves rungs and games together within a week, so these standard errors are optimistic.

**Matt Downs, "Kalshi NFL Strategy: The Bet That Wins 87% of the Time" (posted 2026-08-20).** Sources: channel RSS description and thumbnail.
- The 87% bet is presented as one to avoid: a Kalshi Over total at 87¢, stamped "mispriced".
- His method: devigged sharp-book consensus as the fair price; edge = fair − price − fee; target thin alternate lines and props.
- He sells Upside's +EV Sniper. His performance figures are unaudited and inconsistent across his pages.
