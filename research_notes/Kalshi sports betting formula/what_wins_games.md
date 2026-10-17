# What quantitatively predicts who wins a pro game: NFL first, then NBA, MLB and NHL (as of Oct 2026)

Notes for building a pre-game win-probability formula and setting realistic accuracy targets. Many numbers below are **my own calculations [own calc]** from public game-level datasets, because public models rarely publish Brier or log-loss scores against the closing line. The datasets are:
- **nflverse games.csv** (NFL 1999 to 2026 wk 6; closing spread, closing moneylines from 2006, rest days, roof, wind, division): https://github.com/nflverse/nfldata/blob/master/data/games.csv
- **FiveThirtyEight nfl-elo-game** (538's *base* Elo win probabilities by game, 1920 to 2020, with no QB adjustment): https://github.com/fivethirtyeight/nfl-elo-game
- **nflverse stats_team weekly** (team passing and rushing EPA, 2006 to 2025): https://github.com/nflverse/nflverse-data/releases/tag/stats_team

Conventions: "devig" means the moneyline's implied probabilities rescaled to sum to 1 (multiplicative). Brier and log loss are computed on non-tie games. Accuracy means the team favored by the model won.

---

## Q1. What is the most accurate publicly documented NFL pre-game win model, and how close does it get to the closing moneyline or spread?

### Takeaway
The **closing market is the best documented NFL forecaster**. My calculation for the devigged closing moneyline over 2006 to 2025 gives **Brier 0.2111, log loss 0.6095, 66.4% straight-up accuracy (n = 5,281)**. The best public models at most tie it. nfelo, which is itself partly regressed toward the market, reports 66.52% straight-up (0.17 points below the close) and margin MAE 10.1 (0.01 points worse than the close). FiveThirtyEight's base Elo is about 0.008 Brier worse than the close on the same games (0.2180 vs 0.2099, n = 3,707), and blending it into the market adds nothing. Realistic targets for a good NFL model are therefore Brier ~0.211 to 0.218, log loss ~0.607 to 0.625 and accuracy ~64.5 to 67%. A coin flip scores 0.250 / 0.693.

### Cited Findings

**Market benchmark: closing lines [own calc]**
- Devigged closing moneyline, 2006 to 2025: n = 5,281, **Brier 0.2111, log loss 0.6095, accuracy 66.4%**. A coin flip scores Brier 0.2500 and log loss 0.6931 — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- Same closing moneyline by sub-period. 2006 to 2019: n = 3,593, Brier 0.2117, log loss 0.6106, 66.3%. 2020 to 2025: n = 1,688, Brier 0.2100, log loss 0.6070, 66.7%. 2023 to 2025: n = 854, Brier 0.2102, log loss 0.6077, 68.1% — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- **Spread-only normal model** P(home win) = Φ(closing spread / σ), 2006 to 2025, n = 5,417. σ = 13.5 gives Brier 0.2116 and log loss 0.6109. σ = 13.0 gives 0.2114 and 0.6102. σ = 14.0 gives 0.2119 and 0.6116. The Brier-optimal σ is about **11.75** (Brier 0.2113), and the score is nearly flat between 11.75 and 13.5. The spread alone comes within about 0.0003 to 0.0005 Brier of the devigged moneyline — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- Average closing-moneyline overround was **2.75%** over 2006 to 2025 [own calc] — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv). Lopez et al. report an average vig of 1.93% across 2006 to 2016 NFL, NBA, MLB and NHL lines from Sports Insights — [Lopez, Matthews & Baumer, arXiv 1701.05976](https://arxiv.org/pdf/1701.05976)
- **Closing-spread favorites win 66.5%** (n = 7,230, 1999 to 2025), 66.1% (2015 to 2025, n = 3,014) and 66.6% (2020 to 2025, n = 1,688) [own calc] — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv). OpticOdds independently reports that moneyline favorites went **66.6% (1,013-508-7) over 2018 to 2024** — [OpticOdds](https://opticodds.com/blog/explore-exploring-the-relationship-between-nfl-spreads-and-moneyline-odds-using-historical-data)
- Favorite win rate by size of the closing spread, 1999 to 2025, with the Φ(s/13.5) prediction in brackets [own calc] — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv):

  | Spread | n | Favorite won | Φ(s/13.5) |
  |---|---|---|---|
  | 1 to 2.5 | 1,465 | 52.9% | 55.1% |
  | 3 to 3.5 | 1,860 | 60.2% | 59.3% |
  | 4 to 6.5 | 1,769 | 67.9% | 65.2% |
  | 7 to 9.5 | 1,309 | 75.9% | 71.9% |
  | 10 to 13.5 | 691 | 83.1% | 79.6% |
  | 14 or more | 215 | 91.2% | 87.0% |

  So σ = 13.5 **understates favorites of 4 to 14 points by about 3 to 4 percentage points** and overstates small favorites.

**Converting spreads to win probability**
- Stern's original result: the margin minus the spread is approximately normal with mean 0 and **SD 13.86**. Neil Paine re-estimated it at **13.45** on 1978 to 2012 lines, and Pro-Football-Reference's win-probability model uses 13.45 with a ±0.5 continuity correction — [PFR win-probability model](https://www.pro-football-reference.com/about/win_prob.htm); [arXiv 2212.08116](https://arxiv.org/pdf/2212.08116)
- The SD of the margin minus the closing spread has fallen: **13.44** (1999 to 2009, n = 2,913), **13.27** (2010 to 2019, n = 2,670) and **12.66** (2020 to 2025, n = 1,693) [own calc] — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- A 2022 arXiv paper argues the normal model is structurally wrong because NFL margins are discrete and cluster on key numbers. It notes that recent SD estimates are about 13.5 — [arXiv 2212.08116](https://arxiv.org/pdf/2212.08116)
- **Key numbers** (share of games decided by exactly N points), 2015 to 2025 (n = 3,108) vs 1999 to 2014 (n = 4,248): **3: 14.9% vs 15.3%. 7: 8.7% vs 9.3%.** 6: 6.9% vs 5.3%. 10: 4.7% vs 6.0%. 14: 5.1% vs 4.7%. 4: 4.7% vs 5.1%. 1: 4.4% vs 3.9%. 2: 4.6% vs 3.7% [own calc] — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)

**nfelo (nfeloapp.com)**
- nfelo's performance page, covering 2009 to 2026 (2026 partial), reports **straight-up accuracy 66.52% (0.17 points below the closing line, 0.30 points above the opener)** and **MAE 10.1 points (0.01 worse than the close, 0.12 worse than the opener)**. It also reports ATS 56.99% against the opener and **54.23% against the close**, +175.8 units since 2009 and average closing-line value 6.01% per play — [nfelo model performance](https://nfeloapp.com/games/nfl-model-performance/)
- The same page by season, straight-up accuracy and MAE relative to the close: 2023 67.3% (-0.2), MAE 10.1 (+0.06). 2024 70.5% (0.0), MAE 9.8 (+0.13). 2025 64.4% (-1.1), MAE 9.7 (+0.04) — [nfelo model performance](https://nfeloapp.com/games/nfl-model-performance/)
- nfelo's November 2020 method article says the base model "surpasses" FiveThirtyEight's but "only slightly underperforms the market in predicting margin". The market alone beats base nfelo on Brier. **Regressing nfelo 65% toward the market** was optimal on Brier, and that blend beat the market on Brier. The article reports this through charts only, with no numeric Brier values or sample sizes, so it counts as **an unaudited, in-sample claim** — [nfelo market regression](https://www.nfeloapp.com/analysis/using-market-regression-to-improve-prediction-accuracy-in-the-nfl/)
- nfelo's performance page publishes **no Brier score or log loss** — [nfelo model performance](https://nfeloapp.com/games/nfl-model-performance/)

**FiveThirtyEight Elo [own calc on 538's published base-Elo probabilities]**
- 538's base Elo (no QB adjustment) uses HFA = 65 Elo, K = 20, keeps 2/3 of the rating between seasons (REVERT = 1/3), applies a margin-of-victory multiplier ln(|PD|+1) × 2.2/(EloDiff × 0.001 + 2.2), and converts to probability as 1/(10^(−diff/400)+1) — [538 nfl-elo-game forecast.py](https://github.com/fivethirtyeight/nfl-elo-game)
- On 3,707 games from 2006 to 2020 matched to closing moneylines: **538 base Elo Brier 0.2180, log loss 0.6249, accuracy 64.7%**. The **devigged close scores 0.2099, 0.6068 and 66.6%** on the same games. The two correlate at 0.86 and pick the same winner 85.8% of the time. Blending Elo into the market with weight w gives the best Brier at w = 0 to 0.1 (0.2098 to 0.2099), and the blend gets worse as w rises (w = 0.5: 0.2117). 2006 to 2012 (n = 1,662): Elo 0.2183 vs market 0.2099. 2013 to 2020 (n = 2,045): Elo 0.2178 vs market 0.2099 — [538 nfl-elo-game data](https://github.com/fivethirtyeight/nfl-elo-game); [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- 538's later methodology, now defunct and redirecting to ABC News, used: home field of about **48 Elo** on a rolling 10-year average (replacing the flat 65), **33 Elo** for games without fans, **+4 Elo per 1,000 miles traveled**, **+25 Elo coming off a bye**, playoff Elo differences ×1.2, and a QB adjustment from rolling QB ratings. The QB "VALUE" coefficients are only available from a secondary source and are unverified — [538 methodology (archived URL, now redirects)](https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work)

**Silver Bulletin ELWAY (2025 to 2026, the successor to 538's model)**
- Uses about **21.5 Elo per point** of projected margin, home field of **1 to 3.5 points** by venue, playoff HFA +0.75 points, bye +1 point, +0.3 points per extra day of rest, and QBs at about 30% of player value. Preseason ratings blend prior-season ratings 50/50 with roster ratings. The page publishes **no Brier, log-loss or market comparison** — [ELWAY methodology](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)

**Other rating systems: accuracy documentation**
- Pythagorean expectation for the NFL uses an exponent of about **2.37**. Sources disagree on whether it was fitted by Daryl Morey or Football Outsiders, and practitioners use 2.30 to 2.50 — [Frontiers 2025](https://public-pages-files-2025.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2025.1638446/pdf); [Metricgate](https://metricgate.com/docs/pythagorean-wins-nfl/)
- Of teams that underperformed their Pythagorean record by 2 or more wins since 1989 (n = 42), the next season's record improved by an average of **2.6 wins** — [Grantland (Barnwell)](https://grantland.com/features/bill-barnwell-breaks-2012-numbers-get-feel-2013/)
- A Bayesian state-space model fitted to betting lines across NFL, NBA, MLB and NHL (2006 to 2016) found that ratings from sequential fits are "nearly as accurate for predictive purposes as the observed game probabilities". Glickman & Stern (1998) is the original NFL state-space model, with autoregressive team strength — [Lopez et al., arXiv 1701.05976](https://arxiv.org/pdf/1701.05976)

### Inferences
- For Kalshi-style pricing, the practical "most accurate model" is the devigged closing moneyline, or Φ(spread/σ) with σ ≈ 12 to 13 (12.7 matches recent-era dispersion). Any independent model should be judged on whether it **adds information when blended with the market**, not on standalone accuracy. In my test, a classic Elo adds about zero.
- A Brier gap of about 0.008 (0.218 vs 0.210) is roughly the distance between a respectable public rating system and the market. nfelo's MAE gap of +0.01 points suggests it has essentially converged to the market, which is expected since it regresses toward market lines.
- Use an empirical or logistic mapping from spread to probability rather than σ = 13.5. Empirically a 3-point favorite wins about 60%, a 7-point favorite about 76% and a 10-point favorite about 83%.

### Gaps
- I could not obtain Brier or log loss for 538's **QB-adjusted** Elo (the `qbelo_prob1` file now redirects), for ESPN FPI, or for DVOA or EPA-based public models against the close.
- nfelo publishes no Brier or log-loss figures. Its 2009 to 2019 results are presumably backtests, because the model was documented in 2020.
- The 25-Elo-per-point conversion often used for 538's model was not confirmed in an accessible primary source. ELWAY's documented figure is 21.5.

---

## Q2. What is the incremental value of each input (QB, rest, travel, weather, home field, EPA and others), in points or probability?

### Takeaway
Ranked by size: **starting QB** (market values starters at about 3 to 10 points over their backup) ≫ **team efficiency** (pass offense matters most) > **home field** (~1.5 to 2.5 points now) > **bye or rest** (~1 to 1.6 points raw, but only ~0.4 points beyond the closing spread) > **travel or time zone** (fractions of a point) ≈ **division game** (−0.5 points of HFA). Once the closing spread is known, rest and bye add almost nothing, because the market already prices them. Weather mainly moves totals.

### Cited Findings

**Quarterback**
- Oddsmakers have valued individual starting QBs at roughly 2 to 10 points. Aaron Rodgers was 7.5 points in a 2019 BetOnline list and about 10 points in a 2021 ESPN piece. Garoppolo was valued only about 2 points above Mullens. The adjustment **shrinks at larger spreads**, because points matter more at low numbers. These figures came via a search summary, and I did not check which of the two pages carries each one — [ESPN Chalk](https://www.espn.com/chalk/story/_/id/28162566/how-much-every-nfl-qb-worth-spread); [Action Network](https://www.actionnetwork.com/nfl/nfl-playoffs-qb-starters-backups-spreads-most-valuable-2021)
- ELWAY uses QBs at about 30% of total player value and says a QB change can be worth "a touchdown or more" in extreme cases. A questionable-tagged starter plays about **70%** of the time and a doubtful one about **7%**. League-wide, starters get injured about **4 to 5% per game** — [ELWAY methodology](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)

**Rest, bye and short weeks**
- 538 gave **+25 Elo for a bye**, about 1.0 to 1.2 points at 21.5 to 25 Elo per point — [538 methodology](https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work). ELWAY uses **bye ≈ +1 point** and **+0.3 points per extra rest day** — [ELWAY](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)
- [own calc] 2006 to 2025 home-site games, n = 5,422. Raw regression: margin ≈ 2.17 + **0.245 points per day of rest advantage**, and a bye-vs-no-bye edge (n = 610) is worth **+1.64 points**. **Controlling for the closing spread**, the residual effect is only **+0.07 points per day** and **+0.41 points** for a bye. The spread coefficient is 1.04 — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)

**Travel, time zones and surface**
- 538: **+4 Elo per 1,000 miles**, about 0.16 to 0.19 points per 1,000 miles — [538 methodology](https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work)
- nfelo's game-level HFA model adds bye, time-zone, surface and divisional adjustments to a smoothed league base. Its author reports that the accuracy gain over a **flat 2.5-point HFA is "minimal"** — [nfelohfa GitHub](https://github.com/greerreNFL/nfelohfa)
- 2024 nfelo examples, in Elo points:
  - SEA at NYJ: base +41.3, total +75.3 including a **+22.1 time-zone** adjustment — [nfelo game page](https://www.nfeloapp.com/games/seahawks-vs-jets-box-score-week-13-2024/)
  - SF at SEA: base +45.6, total +41.0 after a **−20.6 divisional** and **+15.9 surface** adjustment — [nfelo game page](https://www.nfeloapp.com/games/49ers-vs-seahawks-box-score-week-06-2024)
- ELWAY penalizes late local kickoffs relative to a team's home time zone, most for East Coast teams playing night games on the West Coast, and treats a 1 p.m. ET start as only a slight disadvantage for West Coast teams — [ELWAY](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)

**Division games and playoffs**
- [own calc] 2015 to 2025: home margin in **division games 1.55** (n = 1,086) vs **non-division 2.08** (n = 1,957). Average closing spreads were 1.74 vs 1.99 — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- [own calc] Playoffs 1999 to 2025: home margin +5.26 and home win rate 64.4% (n = 281). This is confounded by seeding, since the better team hosts — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv). ELWAY adds +0.75 points of HFA in the playoffs — [ELWAY](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)

**Weather and altitude**
- ELWAY says cold, wind and altitude raise HFA, cold especially, and turf adds a little. It rates fan avidity 1 to 5 (GB and BUF 5, the two LA teams 1). Wind is "especially harmful to offense". **No point values are published** — [ELWAY](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)
- [own calc] Totals vs the closing total by wind speed, on games with wind data:
  - 0 to 9 mph: +1.11 (n = 3,343)
  - 10 to 14 mph: +0.12 (n = 1,224)
  - **15 to 19 mph: −1.59** (n = 497)
  - 20+ mph: −0.99 (n = 185)

  This is evidence about totals, not about who wins. Wind coverage in the dataset is incomplete — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- Tuttle, Pion & Bumpass (2024) find that precipitation creates opportunities to profit by betting favorites on NFL moneylines (2007 to 2016). No magnitudes appear in the abstract — [Journal of Economic Insight](https://journalofeconomicinsight.com/index.php/joei/article/view/1335)

**Efficiency stats: EPA, success rate and point differential [own calc]**
- I used weeks 1 to 8 to predict point margin per game in weeks 9 to 18, over 605 team-seasons from 2006 to 2025, using raw EPA that is not opponent- or garbage-time-adjusted. Single-variable R²:

  | Predictor | R² |
  |---|---|
  | Point differential per game | **0.242** |
  | Win % | 0.200 |
  | Offensive EPA per play | **0.187** |
  | Offensive pass EPA per dropback | 0.185 |
  | Defensive pass EPA allowed | 0.046 |
  | Defensive EPA per play allowed | **0.044** |
  | Offensive rush EPA per carry | 0.036 |
  | Defensive rush EPA allowed | 0.015 |

- Leave-one-season-out R² by model:

  | Model | Out-of-sample R² |
  |---|---|
  | Point differential | 0.240 |
  | Offense + defense EPA | 0.235 |
  | Pass-only EPA (offense + defense) | 0.208 |
  | Rush-only EPA | 0.054 |
  | Four EPA splits + point differential | **0.253** |

  Fitted coefficients: 1.0 offensive EPA per play ≈ **31.7 points per game** of future margin, versus **18.9** for defense — [nflverse stats_team](https://github.com/nflverse/nflverse-data/releases/tag/stats_team); [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- nfelo reports that down-weighting random plays (such as fumble recoveries) and garbage time raised the out-of-sample R² of EPA by **14%** over half-season splits. It says offense is more predictive than defense and that elite offenses sustain **+0.10 to +0.20 EPA per play**. This comes from the search snippet; a direct fetch returned 404 — [nfelo weighted EPA](https://www.nfeloapp.com/analysis/weighted-epa-methodology-and-performance)

**Regression to the mean and preseason priors**
- Season-to-season autoregression of team strength estimated from betting lines, 2006 to 2016: **NFL γ = 0.69**, NBA 0.618, MLB 0.618, NHL 0.542. So NFL teams keep about 69% of their deviation from average between seasons — [Lopez et al.](https://arxiv.org/pdf/1701.05976)
- 538's base Elo reverts one-third to the mean (1505) each offseason — [538 nfl-elo-game](https://github.com/fivethirtyeight/nfl-elo-game). ELWAY starts each season from a 50/50 blend of last season's final rating and a roster-based rating — [ELWAY](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)

### Inferences
- A practical pre-game formula:

  margin_hat = (Rating_home − Rating_away) + HFA (≈1.5 to 2.0 now) + QB delta (starter vs backup value) + 0.3 × rest-day difference (or ±1 for a bye) + time-zone and late-kick adjustment (≤ about 1)

  then p = Φ(margin_hat / ~12.5). Shrink the result heavily toward the market; nfelo found 65% weight on the market optimal, and my 538 test suggests ≥ 90% on the market.
- Build the rating from **opponent-adjusted offensive pass EPA plus point differential**, with defense and rush regressed hard toward zero. Defensive and rushing stats carry little forward signal.
- The biggest edge opportunity is **information timing**: QB injury status, given the 70% / 7% play rates for questionable / doubtful, and weather. Static inputs such as rest and travel are already in the closing spread.

### Gaps
- No public, backtested point value was found for short weeks (Thursday games), altitude (Denver) or temperature. ELWAY lists them without numbers.
- No accessible study isolated DVOA's out-of-sample game-level accuracy against the market.
- No backtest was found of preseason market win totals used as Elo priors.

---

## Q3. How big is NFL home-field advantage in 2023 to 2026, and how has it changed?

### Takeaway
The market now prices NFL HFA at about **1.5 to 1.8 points**: the average closing home spread was **1.52 in 2025**, against **2.4 to 2.6 points before 2019**. Home teams won **54.5% in 2021 to 2025**, versus about 57 to 58% before 2019. The realized home margin since 2021 (**+2.25 points**) has actually run about 0.5 points above the market's implied HFA, while ATS results stayed near 50%. Season-level HFA is noisy, with a standard error of about 0.9 points per season.

### Cited Findings
- [own calc] Home-site regular and postseason games — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv):

  | Period | n | Home win % | Mean home margin (SE) | Mean closing spread | Home ATS cover % |
  |---|---|---|---|---|---|
  | 1999 to 2009 | 2,896 | 57.6 | 2.71 (0.27) | 2.60 | 48.9 |
  | 2010 to 2019 | 2,629 | 57.2 | 2.34 (0.28) | 2.37 | 48.8 |
  | 2020 (mostly no fans) | 265 | 50.4 | 0.17 (0.87) | 1.17 | 49.4 |
  | 2021 to 2025 | 1,392 | **54.5** | **2.25** (0.38) | **1.74** | 49.7 |
  | 2023 to 2025 | 834 | 54.6 | 2.40 (0.50) | 1.66 | 50.4 |

- [own calc] By season, home win % / mean home margin / mean closing spread — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv):

  | Season | Home win % | Margin | Spread |
  |---|---|---|---|
  | 2018 | 60.1 | 2.32 | 2.45 |
  | 2019 | 52.3 | 0.09 | 1.95 |
  | 2020 | 50.4 | 0.17 | 1.17 |
  | 2021 | 51.4 | 1.81 | 1.87 |
  | 2022 | 57.4 | 2.25 | 1.82 |
  | 2023 | 56.6 | 2.95 | 1.82 |
  | 2024 | 53.6 | 2.03 | 1.64 |
  | 2025 | 53.6 | 2.20 | **1.52** |
  | 2026 (through wk 6, n = 76) | 54.6 | 0.83 | 1.76 |

- Sharp Football Analysis showed home point differential per game falling from 2.6 in 2016 to −0.1 in 2019, the first season in which home teams were outscored — [Sharp Football Analysis](https://www.sharpfootballanalysis.com/?p=15429)
- nfelo's HFA model says the long-run decline is "fairly small (.5 to 1 points)" and observed HFA is very noisy. Its 2024 base HFA was about +41 to +46 Elo, roughly 1.7 to 1.9 points at 24 to 25 Elo per point — [nfelohfa GitHub](https://github.com/greerreNFL/nfelohfa); [nfelo BUF@SEA 2024](https://www.nfeloapp.com/games/bills-vs-seahawks-box-score-week-08-2024)
- ELWAY uses 1 to 3.5 points by venue, says the decline is "somewhat overstated" given noise, and notes home teams had a negative point differential in fanless 2020 games — [ELWAY](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology)
- 538 moved from a flat 65 Elo (about 2.6 points) to a rolling ~48 Elo (about 1.9 to 2.2 points), with 33 Elo for fanless games — [538 methodology](https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work)
- Lopez et al. (2006 to 2015 NFL, n = 2,560): observed home win rate 56.3% vs market-implied 58.9% (including vig). They found significant between-franchise differences in HFA in the NBA, NHL and NFL, but no individual MLB or NFL team except Colorado (MLB) has a clearly significant home effect — [Lopez et al.](https://arxiv.org/pdf/1701.05976)
- The traditional rule of thumb was 3 points; Covers frames it as now outdated — [Covers](https://www.covers.com/nfl/home-field-advantage)

### Inferences
- Use **HFA ≈ 1.75 ± 0.5 points** for 2026, with venue tweaks (dome vs cold outdoor, time-zone crossings) and about −0.5 points for division games. The realized 2.25 since 2021 suggests the market may have slightly overcorrected. With a season-level SE of about 0.9 points and a 5-season SE of 0.38, that gap is roughly 1.3 SE and **not statistically reliable**.

### Gaps
- No public HFA estimate for the full 2025 season beyond my calculation. The nfelo HFA tracker page was not retrieved.

---

## Q4. Has any public model beaten closing lines out of sample, and what do market-efficiency studies find?

### Takeaway
**No public NFL model has a well-documented, statistically significant out-of-sample edge over closing lines.** nfelo's long-run 54.2% ATS against the close includes years that are likely backtests. Its seasons since it was published (2020 to 2025) are about **52.0% ATS against the close on ~623 bets**, below the 52.38% break-even. The academic literature finds markets close to efficient at the close. Small biases exist (home underdogs historically, favorite-longshot effects, open-to-close momentum), but they are unstable or too small to beat the vig.

### Cited Findings
- **nfelo against the close by season** (bets, ATS%): 2020 126, 56.1%. 2021 93, 51.1%. 2022 102, 54.0%. 2023 109, 50.5%. 2024 101, 45.9%. 2025 92, 53.3% — [nfelo model performance](https://nfeloapp.com/games/nfl-model-performance/). My arithmetic on these figures gives about **324-299 (52.0%) and −5.3 units over 2020 to 2025**, against 54.2% and +175.8 units across all of 2009 to 2026.
- [own calc] Blending 538 base Elo into the devigged close does not improve Brier (best weight on Elo 0 to 0.1, n = 3,707, 2006 to 2020) — [538 nfl-elo-game](https://github.com/fivethirtyeight/nfl-elo-game); [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- **Levitt (2004, *Economic Journal*)** used 19,770 bets by 285 entrants on 242 games in a 2001-02 online-bookmaker contest. Bookmakers do not balance their books. Instead they set prices, take positions and exploit predictable bettor biases (bettors favor favorites, and home underdogs are underbet). Contest entrants may not represent typical bettors — [Levitt 2004 PDF](https://www.stat.berkeley.edu/users/aldous/157/Papers/Levitt_Gambling_2004.pdf); [NBER w9422](https://www.nber.org/papers/w9422)
- Paul & Weinbach (2008), using 2006 sportsbook data, found betting volume was **not balanced**, with favorites (especially road favorites) drawing more volume — [Paul & Weinbach 2008](https://kylewoodward.com/blog-data/pdfs/references/paul+weinbach-international-journal-of-sport-finance-2008A.pdf)
- **Home underdogs** have faded as an edge:
  - Inpredictable: they covered **53.3%** in 1980 to 2001 (n = 1,483) but **47.8%** in 2004 to 2012 (n = 766) — [Inpredictable](https://www.inpredictable.com/2013/08/home-underdogs-are-no-longer-good-bet.html)
  - Another study (2,560 games, 2002 to 2011) reports home teams covered 47% and home underdogs 53.5% — [arXiv 1211.4000](https://arxiv.org/abs/1211.4000)
  - My own calculation (nflverse closing lines) gives home underdog ATS of **50.1%** (1999 to 2009, n = 915), **50.1%** (2010 to 2019, n = 893) and **51.6%** (2020 to 2025, n = 651) — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)

  The sources conflict, likely because they use different line sources and periods.
- **Moskowitz (2021, *Journal of Finance*)**, with 100,000+ contracts across the NFL, NBA, MLB and NHL, found momentum (and weaker value) effects that move prices from open to close and then **reverse by game outcome**. The effects are smaller than in financial markets and **not large enough to overcome transaction costs** — [NBER conference paper](https://conference.nber.org/conf_papers/f92072/f92072.pdf); [Yale Insights](https://insights.som.yale.edu/insights/what-sports-betting-teaches-us-about-financial-markets)
- **Favorite-longshot bias:**
  - NFL moneylines, 2007 to 2016, show a *reverse* favorite-longshot bias (favorites overbet), with inefficiencies that are "unpredictable and vary by season" — [Tuttle, Pion & Bumpass 2024](https://journalofeconomicinsight.com/index.php/joei/article/view/1335)
  - NHL moneylines show a standard favorite-longshot bias — [Aalto thesis](https://aaltodoc.aalto.fi/items/570d1fbc-1342-41b6-a233-6bf5f7042b7c)
  - For MLB, Gandar et al. (2002) found that apparent underdog underbetting is not a robust inefficiency once test statistics are revised — [Applied Economics 2002](https://ideas.repec.org/a/taf/applec/v34y2002i10p1309-1317.html)
- [own calc] Calibration of the devigged NFL closing moneyline, 2006 to 2025 (predicted vs actual home win rate):

  | Implied home prob | n | Predicted | Actual |
  |---|---|---|---|
  | 0.1 to 0.2 | 108 | 0.163 | 0.194 |
  | 0.5 to 0.6 | 883 | 0.555 | 0.530 |
  | 0.6 to 0.7 | 1,108 | 0.648 | 0.617 |
  | 0.7 to 0.8 | 971 | 0.748 | 0.759 |
  | 0.8 to 0.9 | 455 | 0.842 | 0.862 |

  Moderate home favorites ran about 2.5 to 3 percentage points below their implied rate in-sample. No significance test was run — [nflverse games.csv](https://github.com/nflverse/nfldata/blob/master/data/games.csv)
- Lopez et al.: Hosmer-Lemeshow tests on 10 bins found **no lack of calibration** for closing moneylines in any of the four leagues, 2006 to 2016 — [Lopez et al.](https://arxiv.org/pdf/1701.05976)
- Devig method matters at the extremes. Seven common moneyline-to-probability methods reduce to **three distinct estimators**, and one is **biased for heavy favorites** — [Berkowitz, Depken & Gandar 2018, JSE](https://ideas.repec.org/a/sae/jospec/v19y2018i7p990-1015.html)
- MLB, 2010 to 2019, 25,165 games: Vegas closing odds reportedly beat 538 by an average Brier margin of (0.00062, 0.00265) per game, and no forecaster tested beat Vegas. This is **secondhand**; the arXiv abstract only mentions "baseball forecasters" — [benchmarks mirror](https://159-203-178-90.sslip.io/docs/BENCHMARKS.html); [Choe & Ramdas arXiv 2110.00115](https://arxiv.org/abs/2110.00115)

### Inferences
- Plan for a model that, at best, **matches** the close. Edges are more likely from (a) pricing **before** the market fully absorbs news (CLV, as nfelo's ~6% average CLV against the opener suggests), (b) venues whose prices lag sharp books, and (c) small calibration quirks in moderate home favorites, which need out-of-sample confirmation.
- When converting Kalshi or sportsbook prices into probabilities, use the devig method consistently, and be careful with heavy favorites.

### Gaps
- I did not verify Choe & Ramdas's MLB figures in the paper body.
- No peer-reviewed out-of-sample test of any named public NFL model (nfelo, FPI, DVOA, ELWAY) against closing moneylines was found.
- The later Woodland & Woodland update reportedly found a persistent reverse favorite-longshot bias in MLB, but the source URL was not confirmed.

---

## Q5. NBA, MLB and NHL: how often favorites win, the strongest predictors, and market efficiency

### Takeaway
Predictability ranks **NBA > NFL ≫ NHL ≈ MLB**. Closing favorites win about 66 to 67% in the NFL, about 57 to 59% in MLB and about 59 to 61% in the NHL. The NBA has the widest talent spread and the strongest home edge. Public NHL models top out near 60 to 64% accuracy and log loss about 0.65 to 0.66, against a theoretical ceiling near 62%. MLB public models have the lowest skill scores. Betting lines in all four leagues were well calibrated over 2006 to 2016.

### Cited Findings

**Cross-sport randomness**
- Lopez, Matthews & Baumer, closing moneylines 2006 to 2016 (observed home win % vs market-implied home %) — [Lopez et al.](https://arxiv.org/pdf/1701.05976):

  | League | Games | Observed home win % | Market-implied |
  |---|---|---|---|
  | MLB | 26,728 | 54.1 | 54.8 |
  | NBA | 13,290 | 59.5 | 61.5 |
  | NFL | 2,560 | 56.3 | 58.9 |
  | NHL | 13,020 | 54.8 | 56.5 |

  - Regular-season parity index (1 = every game a coin flip), neutral site: **MLB 0.87, NHL 0.84, NFL 0.70, NBA 0.66**. With the better team at home: MLB 0.79, NHL 0.73, NFL 0.55, NBA 0.47.
  - The NBA home edge is equivalent to a **62.0%** chance against an equal opponent.
  - Game-level noise (logit SD): NBA 0.274, NFL 0.233, MLB 0.201, NHL 0.105. Between-team season SD: NBA 0.44, NFL 0.331, NHL 0.121, MLB 0.093.
- Ben-Naim, Vazquez & Redner: long-run **upset frequency** (team with the worse record wins) — [JQAS / arXiv physics/0608007](https://ar5iv.arxiv.org/html/physics/0608007):

  | League | Period | Games | Upset frequency |
  |---|---|---|---|
  | MLB | 1901 to 2005 | 163,720 | 0.441 |
  | NHL | 1917 to 2004 | 39,563 | 0.414 |
  | NBA | 1946 to 2005 | 43,254 | 0.365 |
  | NFL | 1922 to 2004 | 11,770 | 0.364 |
  | English soccer | 1888 to 2005 | 43,350 | 0.452 |

**MLB**
- Moneyline favorites won **57.1%** of about 13,000 games (TeamRankings, 2012). Favorites from **−200 to −415 won 68.3%**, and those from −103 to −109 won 49.9% — [TeamRankings blog](https://www.teamrankings.com/blog/?p=8173)
- 538's MLB game forecasts had the **lowest skill score** of all its forecasts because of baseball's randomness — [538 Checking Our Work](https://projects.fivethirtyeight.com/checking-our-work). A reproduced pooled MLB Brier of about **0.2401** for 2016 to 2020 is secondhand — [benchmarks mirror](https://159-203-178-90.sslip.io/docs/BENCHMARKS.html)
- Tango's regression for MLB: observed win% SD 0.070, luck SD over 162 games 0.039, talent SD about 0.058. That is equivalent to regressing a record by **adding 74 games of .500**. These figures came via a search summary and were not checked on the page — [Columbia stat blog](https://statmodeling.stat.columbia.edu/2014/06/27/quantifying-luck-vs-skill-sports/)
- On starting pitchers, an older FanGraphs/THT analysis found the home team about 19% more likely to win but a home starting pitcher only about 6% more likely to get the win — [THT FanGraphs](https://tht.fangraphs.com/it-is-good-to-get-away/)

**NHL**
- 2024-25, first half of the season: home favorites **61.2% (227-144)**, away favorites 56.6% (137-105), home teams about 54% overall. Combined, that is about 59.4% (my arithmetic) — [Daily Faceoff](https://www.dailyfaceoff.com/news/2024-25-nhl-betting-trends)
- MoneyPuck's pre-game model, by season (model favorite win %, log loss): 2020-21 60.1%, 0.6596. 2021-22 64.1%, 0.648. 2022-23 60.6%, 0.656. 2023-24 61.1%, 0.661. These are **secondhand** quotes of MoneyPuck's about page — [Reddit mirror](https://reddit.fabiomanganiello.com/r/rangers/comments/1glwvc0/nhl_power_rankings_moneypuck_nhl_power_rankings)
- Weissbock (2014, uOttawa thesis) estimated a **theoretical ceiling of about 62%** for NHL single-game accuracy, from about 76% of outcome variance being "chance" via (1−c)+c/2. The best model reached **59.8%** — [uOttawa thesis](https://ruor.uottawa.ca/handle/10393/31553); [CanAI 2014 paper](https://www.eecs.uottawa.ca/~diana/publications/josh_CanAI2014_84360251.pdf)
- About 25% of NHL regular-season games go to overtime or a shootout, which is close to a coin flip — [Lopez et al.](https://arxiv.org/pdf/1701.05976)

**NBA**
- 2023-24 home win rate was **54.3%**, the lowest in league history. Home win rates have been at or below .544 in four of five recent seasons (2022-23 was about 58%) — [Marc Stein](https://marcstein.substack.com/p/baseball-might-have-left-us-until); [Boston 25 News](https://www.boston25news.com/news/national/fact-or-fiction-is/NVE32FOQOEVRYBXQSAJNA6OTJA/)
- On rest, Inpredictable estimated the **back-to-back penalty at about 1.25 points** (corrected from 0.75) over 2003 to 2010 and found no extra spread effect for 3-games-in-4-nights — [Inpredictable](https://www.inpredictable.com/2012/02/nba-home-court-advantage-and-rest.html). A 2026 preprint finds teams win **44%** of back-to-back games against an expected 50%, amplified by star rest — [arXiv 2606.27957](https://arxiv.org/pdf/2606.27957)
- An NBA underdog-win probability of **0.36** and a home-advantage increment of **0.09** were reported in a cross-sport study — [arXiv 1706.02447](https://arxiv.org/abs/1706.02447v1)

### Inferences
Realistic targets:

| League | Accuracy | Brier | Log loss | Strongest predictors |
|---|---|---|---|---|
| NFL | ~66% | ~0.21 | | QB, pass efficiency |
| NBA | likely ~67 to 70% | | | Star availability, rest |
| MLB | ~57 to 59% | ~0.24 | | Starting pitcher dominates |
| NHL | ~59 to 61% | | ~0.65 to 0.66 | Goalie |

- In MLB and the NHL, single-game edges are small relative to noise, so many games are needed to detect any skill.
- The NBA has the widest talent spread, so star availability and rest are worth the most there.

### Gaps
- No verified league-wide **closing-favorite win %** for NBA or NHL in 2023 to 2026 was found.
- No sourced point or probability values were found for NBA net rating, for the share of win variance explained by MLB starting pitchers, bullpen or park, or for NHL goalie (GSAx) and xG predictive weight.
- No public accuracy figures were obtained for Kenpom/Torvik-style NBA models, FanGraphs MLB game odds, or Evolving-Hockey against closing lines.
