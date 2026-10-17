# Why Players Score: Player-Output Drivers and Player-Prop Market Efficiency (NFL / NBA / MLB), as of Oct 2026

Scope note: pre-game projection only. Research date 2026-10-17. Source quality varies a lot. Peer-reviewed or primary sources are rare for player props specifically. Most prop-market evidence comes from vendors, affiliates or self-reported GitHub projects, and each finding below says which kind of source it is. "Inferences" are this researcher's reasoning or arithmetic, not sourced facts.

---

## Q1. For each sport, which few inputs explain most of the variance in a player's game output (opportunity x efficiency, game environment, stabilization points)?

### Takeaway
In all three sports, opportunity/volume stats (targets, minutes and usage, PA/BF) are much more stable and predictive than efficiency stats (YPT, TD rate, 3P%, BABIP). Projections should therefore be built as **opportunity x heavily-regressed efficiency x game-environment scalar**. In MLB, K% and BB% stabilize fastest (60 / 120 PA for hitters, 70 / 170 BF for pitchers). In the NBA, 3P% is the least stable common stat, and over 50% of the between-player variation within a season is luck. In the NFL, WR targets/game (r = 0.66 year over year) and air yards are far stickier than TD rate (r = 0.12) or yards/target (0.22).

### Cited Findings

**MLB: stabilization points (Russell Carleton; cut where split-sample r = 0.70, R^2 ~ 0.49)**
- Hitters: K% 60 PA; BB% 120 PA; HBP 240 PA; 1B rate 290 PA; HR rate 170 PA; ISO 160 AB; SLG 320 AB; OBP 460 PA; AVG 910 AB; GB/FB rate 80 BIP; LD rate 600 BIP; HR/FB 50 FB; BABIP 820 BIP; XBH rate 1610 PA. FanGraphs library page originally dated Feb 18, 2010, updated Aug 2017 — [FanGraphs Library: Sample Size](https://library.fangraphs.com/principles/sample-size/)
- Pitchers: K% 70 BF; BB% 170 BF; GB/FB 70 BIP; HR rate 1320 BF; HR/FB 400 FB; AVG 630 BF; OBP 540 BF; BABIP 2000 BIP; LD 650 BIP — [FanGraphs Library: Sample Size](https://library.fangraphs.com/principles/sample-size/)
- Method: a stat is "stabilized" where the correlation between two equal-size samples reaches 0.7. A reader comment notes the GB/FB/LD denominators were per PA in the original research, not per BIP. The page also shows Dolinar/Pemstein Cronbach's-alpha reliability curves, which have K% crossing 0.49 far faster than other stats — [FanGraphs Library](https://library.fangraphs.com/principles/sample-size/)
- Practitioner caution: a stabilization point is where signal is about 51/49 over noise. It is not a cutoff beyond which a sample becomes the player's "true" level — [RotoWire MLB Barometer](https://www.rotowire.com/baseball/article/mlb-barometer-strong-starts-for-young-outfielders-71656); [FanGraphs: Passing the Whiff Test](https://fantasy.fangraphs.com/passing-the-whiff-test-early-k-improvements/)
- Older (2011) estimates were much larger (about 150 PA for K%, about 200 for BB%), so the method used matters — [River Ave Blues 2011](https://cdn.riveraveblues.com/2011/04/looking-at-the-three-true-outcomes-offense-47227/)

**MLB: opportunity (PA by lineup slot)**
- 2016 data: leadoff 4.65 PA per game started vs. 3.77 for the 9th spot (about 0.88 PA/game, or about 114 PA per 600 PA) — [FanGraphs Ottoneu 101: PA by Lineup Spot](https://fantasy.fangraphs.com/buying-generic-plate-appearances-by-lineup-spot)
- AL parks: leadoff 4.83 vs. 9th 3.90 PA/game — [RotoWire: Constructing an Efficient Lineup](https://www.rotowire.com/baseball/article/umpire-analysis-constructing-an-efficient-lineup-21283)
- The 1st-to-9th gap is about 130 PA per season — [Pitcher List](https://pitcherlist.com/going-deep-using-plate-appearances-to-decipher-hidden-value/). The decline is roughly linear from slots 1 to 7, then steeper, partly because of pinch-hitters — [THT/FanGraphs Hit Rate Observer](https://tht.fangraphs.com/hit-rate-observer-0410/)

**MLB: pitcher K vs. batter K matchup formula**
- Odds-ratio model (Steve Staude, summarized on FanGraphs Community): Expected matchup K% = B*P / (0.84*B*P + 0.16), where B is the batter's K% vs. that pitcher's handedness and P is the pitcher's K% vs. that batter's handedness — [FanGraphs Community (japem)](https://community.fangraphs.com/author/japem/)
- Log5 (Bill James) predicts matchup strikeout probability accurately, and adding variables can improve it (2015 study) — [Journal of Sports Analytics, jsa0025](https://content.iospress.com/articles/journal-of-sports-analytics/jsa0025). Log5 becomes increasingly skewed for asymmetric (extreme) probabilities; the paper proposes the Morey-Z alternative — [J. Sports Analytics, jsa0005](https://content.iospress.com/articles/journal-of-sports-analytics/jsa0005)
- The same odds-ratio logic applies at team level (pitcher K% vs. opposing lineup K%) — [RotoWire Saber's Edge](https://www.rotowire.com/baseball/article/the-sabers-edge-freak-the-mighty-again-20384)

**NFL: stability of opportunity vs. efficiency (WR, 2012–2022, players with 40+ targets in consecutive seasons; 4for4)**
- Year-over-year r: avg targeted air yards 0.68; targets/game 0.66; receptions/game 0.65; rec yards/game 0.65; half-PPR pts/game 0.60; target share 0.55; share of team air yards 0.53; catch rate 0.47; TD/game 0.38; red-zone targets 0.38; yards/target 0.22; TD rate (TD/target) 0.12 — [4for4: Most Predictable WR Stats](https://www.4for4.com/2023/preseason/most-predictable-wide-receiver-stats)
- A top red-zone receiver sees only about 25 red-zone looks per season, too few for TD rates to settle (e.g., DK Metcalf's RZ TD rate went 35% to 47% to 18% from 2020–22) — [4for4](https://www.4for4.com/2023/preseason/most-predictable-wide-receiver-stats)
- Opportunity metrics correlate more with fantasy points than efficiency metrics do and have the highest YoY correlation. Target volume is the "best predictor" — [PlayerProfiler WR advanced stats guide](https://www.playerprofiler.com/article/playerprofilers-guide-to-nfl-advanced-stats-metrics-vol-2-wide-receivers/)
- Expected fantasy points (xFP): the nflverse `ffopportunity` package fits an xgboost model on 2006–2020 nflverse play-by-play to price each opportunity — [ffopportunity GitHub](https://github.com/ffverse/ffopportunity). PFF reported xFP vs. actual FP R^2 of about 0.96 for each main position in 2019, but that is a same-season fit, not out-of-sample prediction — [PFF xFP primer](https://pff.com/news/fantasy-football-expected-fantasy-football-points-primer-week-1-tom-brady-davante-adams-and-other-candidates-for-positive-regression)

**NFL: game environment**
- Implied team total: favorite implied points = (O/U + |spread|)/2, derived from O/U = v - y with spread y negative for the favorite — [FantasyLabs Vegas Score](https://www.fantasylabs.com/?p=3668)
- "Fantasy points are most strongly correlated to team implied totals." This is a practitioner claim with no coefficient given — [Fantasy Footballers Vegas Report](https://www.thefantasyfootballers.com/dfs/nfl-dfs-vegas-report-for-week-16-fantasy-football-3/). FantasyLabs' proprietary QB "Vegas Score" correlates above 0.80 with average actual points and Plus/Minus. It is a composite, not raw implied total, and these are correlations, not R^2 — [FantasyLabs](https://fantasylabs.com/?p=102220)
- Wind: team passing yards average about 227 at 0–7 mph kickoff wind, about 218 at 8–11 mph, and about 206–211 in higher bands (20+ mph not lower still). 8–11 mph games went under more than baseline, and books appear to shade totals down for forecast high wind — [Sharp Football Analysis weather study](https://www.sharpfootballanalysis.com/?p=128473). This conflicts with a claim that the passing drop gets much steeper at 20+ mph — [Covers](https://www.covers.com/nfl/how-weather-affects-betting). Wharton finds a significant linear decline in passing EPA/play with wind; the extreme-wind bucket has a small sample — [Wharton 2022 Football Parks Weather](https://wsb.wharton.upenn.edu/wp-content/uploads/2022/09/2022_Football_Parks_Weather.pdf)

**NBA: stability of rate stats**
- Franks, D'Amour, Cervone & Bornn (2016) assessed 70 NBA metrics, 2000 onward. Rebounds, blocks and assists (per 36) are highly stable and discriminative because they track position. FT% discriminates little within a season but is very stable across seasons. Per-minute/per-game stats are more stable but less discriminative than totals, and totals are driven by minutes and injuries. **Raw 3P% is the least stable and least discriminative metric studied: "over 50% of the variation in three point percentage between players in a given season is due to chance."** Empirical-Bayes-shrunk 3P% improves both stability and discrimination — [Franks et al., "Meta-Analytics," arXiv 1609.09830](https://arxiv.org/pdf/1609.09830)
- It takes about 750 3PA before more than half of the variation in a player's 3P% reflects skill (Blackport 2014, cited secondhand) — [arXiv 1703.07030](https://arxiv.org/pdf/1703.07030). 2P% and rebound rate stabilize quickly by comparison — [bball-index: creating more predictive stats](https://www.bball-index.com/creating-more-predictive-stats/)
- Role-change stability (Neil Paine, Aug 18 2010; 1,036 player-seasons since 1974, ages 24–34, 1,000+ min in back-to-back seasons, top quartile of usage change). YoY r through a role change: OREB% 0.932, AST rate 0.905, FT rate 0.802, TOV rate 0.724, **TS% 0.627** (least consistent, consistent with usage–efficiency "skill curves") — [Basketball-Reference blog (Paine)](https://www.basketball-reference.com/blog/index69a1.html?p=7220)
- Usage–efficiency tradeoff: estimates of about 0.6 pts/100 poss per 1% usage (Dean Oliver 2005) and 1.25 pts/100 poss per 1% usage (Eli Witus 2008, lineup-based) are cited secondhand. A 2009 paper says the skill curve "has never been extracted from data in a generally accepted way" — [arXiv 0908.1801 "Price of Anarchy in Basketball"](https://arxiv.org/pdf/0908.1801). A raw 2017–19 check found no efficiency cliff, only a narrower range at high usage — [Liberty Ballers](https://www.libertyballers.com/2019/1/29/18199824/is-there-an-efficiency-cliff). (Flag: the Oliver and Witus numbers come from a search-result summary and were not verified on the primary page.)

**NBA: minutes, blowouts, injuries/usage redistribution**
- Usage is zero-sum: possessions are finite, so one player's usage reduces teammates' chances — [FiveThirtyEight](https://fivethirtyeight.com/features/the-spurs-were-an-outlier-of-unselfishness)
- When a star sits, the freed usage is not spread evenly; the primary positional backup absorbs the largest share (affiliate guide, unquantified) — [statz.ai usage-rate guide](https://statz.ai/nba/betting/guides/usage-rate-in-basketball-what-it-means-and-why-it-affects-your-props). Example: DeAndre Jordan's usage went from 8% to 12% with Griffin off the floor — [RotoGrinders CourtIQ](https://rotogrinders.com/articles/nba-starting-five-courtiq-wednesday-march-16th-1219802). Raw on/off splits are noisy and context-dependent — [The F5](https://thef5.substack.com/p/down-bad)
- Blowouts: stars lose minutes mainly in the 4th quarter of decided games — [FantasyPros](https://www.fantasypros.com/2020/07/how-should-potential-blowout-games-influence-dfs-lineups-fantasy-basketball/amp/). Coach-specific handling matters — [RotoGrinders: Projecting Minutes](https://rotogrinders.com/lessons/projecting-minutes-1149307). 4th-quarter minutes in started games are a proxy for blowout risk (2014–15 data, dated) — [FantasyLabs: Blowout-Proof](https://www.fantasylabs.com/?p=5245)

### Inferences
- **Core projection formulas (researcher's synthesis):**
  - NFL receiving yards ~ team plays x pass rate (from spread/total/script) x route participation x targets-per-route (or target share) x yards-per-target (regressed hard, since YPT has YoY r = 0.22). TDs ~ team implied total x the player's share of red-zone/end-zone opportunity, regressed toward league TD/opportunity rates (TD rate YoY r = 0.12).
  - NBA points ~ projected minutes x team pace (possessions/48) x usage share x points per used possession (TS-driven, regressed). Rebounds and assists are rate x minutes; their rates are highly stable per Franks et al., so **minutes is the dominant uncertainty for REB/AST**, while threes carry the extra 3P% noise.
  - MLB pitcher Ks ~ expected batters faced (pitch-count leash x pitches/PA x opponent OBP) x matchup K% (odds-ratio of pitcher K% and lineup K% by handedness). Hitter hits/TB ~ expected PA from lineup slot (about 4.65 at 1st to 3.77 at 9th) x regressed per-PA rates, with park factors applied.
- **Regression constants from stabilization points:** if reliability r(n) = n/(n+k), Carleton's r = 0.7 point implies k ~ 0.43 x (stabilization n). That gives roughly K% (hitter) k ~ 26 PA, BB% ~ 51 PA, pitcher K% ~ 30 BF, BABIP ~ 350 BIP. Use regressed rate = (x + k*mu)/(n + k). Using the stabilization point itself as k would over-regress by about 2.3x. (This is the researcher's arithmetic; check it against Tango-style r = 0.5 points before relying on it.)
- Because volume is stickier than efficiency, efficiency-driven outliers (a hot 3P% streak, a high TD rate, high BABIP) are the most likely places for markets that over-weight recent box scores to misprice. That last part is a hypothesis, not tested here.

### Gaps
- No public per-game (not per-season) R^2 decomposition was found for any sport, e.g. "minutes explain X% of game-to-game variance in NBA points." Modelers will need to compute it from their own data.
- No source was found giving per-season NBA stabilization points for usage rate, rebound rate or FT% (Blackport's original tables were not located).
- No published R^2 for QB/WR fantasy points regressed on implied team total; only correlations from proprietary composites.
- No quantified study was found on NBA starters' minutes as a function of pre-game spread, or on back-to-back/rest effects on player minutes.
- MLB pitch-count/leash modeling and park-factor magnitudes for hits/TB props were not researched in depth (not enough tool budget).

---

## Q2. How much predictive value do defensive matchups add after controlling for opportunity and game environment?

### Takeaway
Little, and the evidence is weak. Season-level "fantasy points allowed" by defenses has year-over-year r of only about 0.26–0.30 in the NFL (WR points allowed is close to zero). No rigorous NBA defense-vs-position (DvP) predictive study was found. The matchup effects that are mechanistically grounded are MLB handedness/K% matchups (odds-ratio/log5), which are well validated. Defense-vs-position rankings should be heavily regressed, or replaced by opponent pace and opponent rate stats.

### Cited Findings
- NFL, 2014–2024: fantasy points allowed to QBs had the highest year-to-year correlation of any position, at 0.26. Points allowed to WRs showed very little year-to-year correlation. Top-5 defenses vs. QBs repeated top-5 the next season about 30% of the time — [4for4: Do Defenses Repeat?](https://www.4for4.com/2025/preseason/do-defenses-repeat-fantasy-football-performances)
- Team-defense fantasy points allowed per game: YoY r = 0.295 (8-season median). The offense's own points scored was the most stable measure — [DraftSharks team defense guide](https://www.draftsharks.com/article/2021-team-defense-strategy-guide)
- Friendliest matchups added 20%+ to D/ST scoring and the worst subtracted 20%+ (2010–2020). This is opponent offense quality driving defense scoring, i.e., the offense side of the matchup — [DraftSharks 2022 team defense guide](https://www.draftsharks.com/article/2022-team-defense-strategy-guide?print=1)
- NBA DvP: raw DvP rankings mislead because a team allowing many fantasy points may be giving up rebounds/steals/blocks rather than points/assists. Practitioner view, no measured predictive test — [RotoWire DFS Basketball 101: DvP](https://www.rotowire.com/basketball/article/dfs-basketball-101-defense-vs-position-strategies-31305)
- MLB matchup (validated): log5 accurately predicts matchup K probability, and generalized log5 (logistic regression) improves it but can be unstable with small samples — [J. Sports Analytics jsa0025](https://content.iospress.com/articles/journal-of-sports-analytics/jsa0025); odds-ratio formula — [FanGraphs Community](https://community.fangraphs.com/author/japem/)
- WR1s on the same team as your opposing QB score about 2.4 fewer points relative to that QB in the top-10 QB tier (2013–2024). This is a matchup EV measure, not a correlation — [Fantasy Footballers](https://www.thefantasyfootballers.com/analysis/is-it-smart-to-stack-wrs-against-opposing-qbs/)

### Inferences
- With season-level defensive "points allowed" at YoY r of about 0.26–0.30, a single season of DvP should be regressed about 70% toward the mean. Weekly or partial-season DvP samples are noisier still. Defensive adjustments should come mainly through opponent **pace/plays, pass-rate tendency, and opponent rate stats (e.g., opponent K% in MLB, opponent pace/possessions in the NBA)**, not position-level fantasy points allowed.
- MLB is the exception: batter-vs-pitcher **handedness** and K% matchups have a mechanistic, validated basis and stabilize fast, since K% settles at 60–70 PA/BF.

### Gaps
- No controlled study (academic or practitioner) was found measuring the incremental out-of-sample R^2 of NBA DvP or NFL DvP after controlling for minutes/targets and Vegas totals. This is a key open question; build the test in-house.
- No weekly autocorrelation study of NFL defense-vs-position was found; only season-level.

---

## Q3. How accurate are the best projection systems vs. player-prop lines? Are there documented, repeatable edges, which prop markets are softest, and how fast do lines react to injury news?

### Takeaway
No peer-reviewed study was found that measures player-prop market efficiency directly. Academic work covers spreads, totals and moneylines. Public, out-of-sample evidence that projection models beat prop closing lines is thin to negative: self-reported 2025 NFL ML models beat simple baselines by only 0–9% in MAE and report "no evidence yet of an edge." Commonly cited structural edges (blind unders, early-week lines, slow teammate-prop updates after injury news) rest on vendor or anecdotal evidence. Props carry higher hold (about 6–15%) than sides (about 4.5%). A 2026 vendor study found books' closing lines on high-volume MLB props nearly equally sharp, with exchanges (Kalshi, ProphetX) sharpest.

### Cited Findings

**Academic baseline (non-prop markets)**
- NBA totals lines are significantly biased early in the season (sides are not). A simple strategy against closing totals won 56.72% — [ScienceDirect: Learning, price formation and early season bias in NBA](https://www.sciencedirect.com/science/article/abs/pii/S1544612307000177)
- NBA moneyline markets showed large inefficiencies during COVID-19 while other major sports stayed efficient — [arXiv 2109.07581](https://arxiv.org/pdf/2109.07581)
- NFL bettor biases go beyond favorites and overs; bettors lean against line movement — [Shank, SSRN 3289715](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3289715)
- Model selection by calibration rather than accuracy gave NBA game-betting ROI of +34.69% vs. -35.17% on average (one season, game outcomes not props) — [Walsh & Joshi, arXiv 2303.06021](https://arxiv.org/pdf/2303.06021)
- A systematic review of ML in sports betting exists, but it does not establish an ML edge on player props — [arXiv 2410.21484](https://arxiv.org/pdf/2410.21484)

**Projection accuracy vs. simple baselines (self-reported, GitHub)**
- NFL ML model: trained 2018–2023 (147,227 player-weeks), validated 2024, tested 2025 weeks 3–18. MAE vs. a simple baseline: passing yards 59.98 vs. 65.78 (+8.8%, n = 434); pass TDs 0.87 vs. 0.89 (+2.5%); **receiving yards 21.34 vs. 21.39 (+0.2%, n = 1,974)**; receptions 1.51 vs. 1.52 (+0.3%); rushing yards 25.89 vs. 26.47 (+2.2%). These are projection-error comparisons, not betting results — [traplandlord/nfl-props-stats PR #2](https://github.com/traplandlord/nfl-props-stats/pull/2)
- Another project: receiving-yards MAE 23.2 vs. 24.2 for an 8-game average (2024–25). Its forward test vs. de-vigged closing lines underrated low-end overs ("30% predicted, 35–38% actual"). Author: "There's no evidence yet of an edge over the books." No free historical prop lines were available for backtesting — [zed-uber/betmap PR #5](https://github.com/zed-uber/betmap/pull/5)

**Market sharpness and softness**
- Vendor study (SmartStake, 2026): 600M+ MLB prop line movements, 1.3M closing lines, 75 books/exchanges; markets were total bases, hits, RBIs, HRs, strikeouts and walks; main line only, vig removed, Brier score. **Kalshi and ProphetX were sharpest**, Novig next, DraftKings/FanDuel middle, Pinnacle and Bookmaker softest. On high-volume markets (RBIs, Ks, hits) closing-line Brier scores were nearly identical across books ("a rounding error"). HR props showed the only real separation (Pinnacle Brier 0.140 vs. 0.091–0.110 for most books), which the author attributes to longshot handling. **Conflict of interest:** the author trades on Kalshi/Polymarket and the site sells +EV and arbitrage tools — [SmartStake: Sharpest Sportsbooks for MLB Player Props](https://www.smartstake.app/learn/sharpest-sportsbooks-mlb-player-props)
- Hold: standard -110/-110 is about 4.5% hold — [OddsReference](https://oddsreference.com/sports/learn/what-is-vig). Player props run about 6–10% — [Bodog](https://bodog.com/sports-betting/how-sportsbooks-make-money) — or 8–15% — [Betstamp vig calculator](https://www.betstamp.com/calculators/vig). A -130/-110 prop is about 8.2% hold — [ProfitDuel](https://www.profitduel.com/blog/what-is-hold-percentage-vig-in-sports-betting). Sharp books (Pinnacle, Novig, Sporttrade) reportedly run about 1–3% on spreads/totals vs. 4.5–6% at DK/FD/MGM/Caesars — [propsbot.ai](https://propsbot.ai/tools/hold-vig-calculator/)
- Early-week/opening prop lines: "opening numbers are softer, but limits are lower," and sharps bet early. Example: Trevor Lawrence's passing-yards line moved 225.5 to 234.5 in Week 1 2026. The biggest gaps are said to come after Friday injury designations and in the post-inactives window. These are affiliate guides, not a systematic test, and one source argues closing lines are highly efficient. (Attribution flag: these claims came from a search summary over the three pages below, and which page makes which claim was not confirmed by fetching.) — [BetSmart NFL props guide](https://www.betsmart.co/articles/nfl-player-prop-betting-guide); [SportsBettingDime Week 1 2026](https://www.sportsbettingdime.com/news/nfl/player-props-week1-over-under-lines-odds-2026/); [Boyd's Bets opening vs closing](https://www.boydsbets.com/opening-vs-closing-line/)
- Points props are the most efficiently priced NBA props; less-bet markets are claimed to be softer (affiliate claims from search summaries, pages not fetched) — [OddsIndex NBA player props guide](https://oddsindex.com/guides/nba-player-props-guide); [nbabettingsystem.com](https://nbabettingsystem.com/articles/nba-betting-market-efficiency/)
- Over/under shading: an NFL props writer's record shows unders went 111-64 (63.7%, n = 175) in 2022, then 35-28 (55.6%) in 2023 Weeks 1–6 and 12-24 (33.3%) from Week 7 on. This is personal tracking that shows small-sample swings, not a structural test — [Stealing Lines (Dalton Kates), Dec 24 2023](https://stealinglines.substack.com/p/finding-a-flaw-in-the-process-best)

**Injury-news reaction speed (all affiliate claims, unverified)**
- Some books adjust related props within seconds via automation; others take minutes to hours — [bet-player.com](https://bet-player.com/line-shopping/)
- Slower books may trail faster ones by 10–30 minutes — [statz.ai](https://statz.ai/nba/betting/how-to-read-nba-prop-lines)
- The absent player's props are pulled immediately, but teammates' props may sit unchanged for 30–60 minutes — [nbabettingsystem.com](https://nbabettingsystem.com/articles/nba-injury-impact-on-betting-lines/)
- Major books adjust within minutes of confirmed reports; final NBA status typically comes 60–90 minutes before tip — [OddsIndex injury guide](https://oddsindex.com/guides/injury-impact-betting-guide)

### Inferences
- Break-even at -110 is 52.38%. At typical prop holds of 6–10%, single-side break-even is about 53–55%. Models with only a 0–3% MAE gain over naive baselines (receiving yards, receptions, rush yards) are very unlikely to clear this against closing lines. Passing yards, where ML gained about 9% MAE, may be the more model-sensitive NFL market.
- The most plausible repeatable edges are structural: (a) speed on teammate/usage redistribution after late injury news; (b) early-week/opening lines at low limits; (c) less-bet stat types and players (role players, alt lines, combos), where books spend less effort; (d) systematic over-shading on popular names. Each is supported only by vendor or anecdotal evidence and should be validated with CLV on your own data.
- Measure success with closing-line value (de-vigged) against the sharpest venue. The SmartStake finding suggests Kalshi/ProphetX closes are a better CLV reference for MLB props than Pinnacle, but it has a conflict of interest.

### Gaps
- **No peer-reviewed study of player-prop market efficiency was found** (searched SSRN, arXiv, journal titles).
- Search summaries mentioned (a) an NFL model's 2025 blind test with 6,736 picks at 51.5% vs. a 53.9% break-even (-4.3% ROI), (b) a developer's "blind star-unders hit 55.4% vs model-filtered 55.8%," and (c) an MLB tracker with top overs 42.5% (n = 443) vs. top unders 53.4% (n = 433). The primary URLs for these could not be confirmed, so they are **unverified and should not be cited without locating the originals**.
- No public data on prop bet limits by book/market, or on systematic timestamped injury-reaction latency.
- No documented public accuracy comparison of named projection systems (THE BAT X, Steamer, DARKO, 4for4, ETR, etc.) vs. prop closing lines was found.

---

## Q4. How are player props priced on Kalshi/Polymarket vs. sportsbooks (liquidity, spreads), and are there efficiency studies?

### Takeaway
Kalshi launched football player props/spreads in Aug 2025 under CFTC self-certification and added fee-rebate liquidity incentives for prop markets feeding combos (Sept 2025). Polymarket US went live with NBA player props on May 22 / June 2, 2026. Sports dominate prediction-market volume ($58B on Kalshi and about $22B on Polymarket in June–July 2026). Individual player-prop books are reportedly thin: about $50–500 daily volume and 5–10 cent spreads per one unverified tracker. The only "efficiency" evidence is one conflicted vendor study ranking Kalshi among the sharpest venues for MLB props.

### Cited Findings
- Kalshi filed with the CFTC (Aug 2025) to add football contracts resembling spreads, totals and TD props, live unless the CFTC acted. Kalshi's CEO said it would bring "more liquidity, efficiency, and price competition" — [Covers, Aug 18 2025](https://www.covers.com/industry/kalshi-football-season-sports-betting-spreads-totals-props-august-18-2025); [SBC Americas](https://sbcamericas.com/2025/08/18/kalshi-player-props-new-markets-cftc/)
- Kalshi prop liquidity incentive: up to 25% of fees from each qualifying combo market is distributed monthly as trading credits to liquidity providers in the underlying prop markets. Filed Sept 2, 2025, effective after Sept 16 — [NextPredict](https://nextpredict.io/market-news/industry/kalshi-files-prop-market-liquidity-incentives/)
- Liquidity/spreads (unverified third party): most Kalshi player-prop markets have $50–500 daily volume and 5–10 cent spreads, with far lower volume and wider spreads than other sports markets — [Prediction Pilot](https://predictionpilot.io/markets/sports)
- Kalshi fee (third-party explainer, verify against the official schedule): per-order fee = roundup(0.07 x C x P x (1-P)). That is about 1.75 cents/contract at P = 0.50 and about 0.63 cents at P = 0.10. Some categories, e.g. Sports, may have different rates. The 0.75% figure cited there is Polymarket's sports rate — [pm.wiki](https://pm.wiki/es/learn/prediction-market-arbitrage-after-fees). Kalshi's help page confirms maker fees on some markets (charged only on execution) and special-event fee variation, but defers formulas to a PDF schedule — [Kalshi Help: Fees](https://help.kalshi.com/trading/fees)
- Polymarket US: basketball player props and first-half markets went live May 22, 2026, with additional NBA player props and second-half markets on June 2, 2026 — [Polymarket US changelog](https://docs.polymarket.us/changelog). Polymarket launched multi-leg sports contracts and a Yahoo Sports partnership in May 2026 — [Prediction News](https://predictionnews.com/story/polymarket-adds-multi-leg-contracts-as-it-chases-kalshi-sportsbooks-b354f4cc). In Jan 2026 the API returned prop markets with zero volume — [TheSportsGeek](https://www.thesportsgeek.com/blog/polymarket-to-launch-player-props/)
- Volume: in June–July 2026 sports trading topped $58B on Kalshi and neared $22B on Polymarket (incl. Polymarket US); prediction-market volume doubled May to July, driven by sports — [Pew Research, Sept 23 2026](https://www.pewresearch.org/short-reads/2026/09/23/prediction-markets-trading-volume-doubled-between-may-and-july-largely-driven-by-sports/)
- Efficiency: Kalshi had "the tightest pricing across the board" on MLB props and beat Novig comfortably, while ProphetX edged Kalshi head-to-head; Kalshi's prop markets were described as "newer and thinner" (conflicted vendor) — [SmartStake](https://www.smartstake.app/learn/sharpest-sportsbooks-mlb-player-props)

### Inferences
- On exchanges, the cost of trading is the half-spread plus fees, not the vig. A 5–10 cent spread on a 50-cent contract equals about 5–10% round-trip, comparable to or worse than sportsbook prop hold. That favors **posting resting (maker) orders at model fair value** over crossing the spread, especially given Kalshi's liquidity credits for prop makers.
- Thin books plus a sharp close imply that edges are in price discovery (early or after news) rather than at the close. Exchange prices can also serve as a sharp CLV benchmark.

### Gaps
- Official Kalshi fee coefficients for sports/prop series and the maker formula were not retrieved (the PDF schedule returned HTTP 429).
- No independent order-book depth or spread dataset for Kalshi/Polymarket player props was found, and no academic study of prediction-market prop efficiency.
- Polymarket US NFL/MLB player-prop coverage as of Oct 2026 was not confirmed.

---

## Q5. Which distributions best fit player counting stats, and how do correlations matter for parlays/combos?

### Takeaway
No authoritative published fit comparison was found. The practitioner consensus is negative binomial (overdispersed) for rebounds/assists and similar counts, zero-inflated or Poisson for rare events (blocks, steals, TDs, HRs), and normal or skewed-continuous for yardage. Same-game correlations are material: correlated legs raise joint probability by about 1.3x in worked examples. Books price SGPs with copula-type joint models plus large margins (claims of 15–25%+ hold), so naive independence-based combo pricing is badly wrong in both directions.

### Cited Findings
- Distribution conventions (internal model-design notes of unknown provenance, flagged unverified): NBA rebounds/assists use negative binomial; blocks/steals use zero-inflated Poisson; player-specific dispersion uses Bayesian shrinkage; NHL goals use Poisson and shots use negative binomial due to higher variance — [edge-assist NBA strategy spec](https://edge-assist.duckdns.org/data-status/docs/nba-player-props/strategy); [edge-assist NBA audit ruling](https://edge-assist.duckdns.org/data-status/docs/nba-player-props/ruling/NBA%20Player%20Props%20Data%20Audit%20Council%20Ruling)
- Negative binomial regression applied to NBA 3PT modeling — [squared2020](https://squared2020.com/2017/08/20/basics-in-negative-binomial-regression-predicting-three-point-field-goal-percentages/). Hierarchical Bernoulli/empirical-Bayes 3P% shrinkage improves stability — [Franks et al. arXiv 1609.09830](https://arxiv.org/pdf/1609.09830)
- SGP math (Wizard of Odds, updated Aug 3 2026; illustrative, no external data). Gaussian copula 3-leg example: marginals 58.3/52.4/52.4% give 16.0% joint under independence vs. about 21.2% with correlation (+33%). An unnamed empirical sample (500 NFL games, 3–7 pt favorites, totals 45–51): 15.7% independent vs. 20.4% observed (1.30x). A book-pricing example assumed 1.35x. Negative correlation (rho = -0.30) cuts a 24.8% joint to 19.2%. Typical sports correlations range from -0.4 to +0.6. SGP house edge "15–25% or higher," while worked examples give 14.9% (or 4.6% under the copula estimate) — [Wizard of Odds: SGP Mathematics of Correlation](https://wizardofodds.com/article/same-game-parlays-the-mathematics-of-correlation/)
- Copula approach: models the joint while preserving marginals. Books reportedly shade the joint probability down to cover correlation-estimation error (single blog claim) — [SharpBets Club Substack](https://sharpbetsclub.substack.com/p/the-mathematics-of-same-game-parlays). Patents describe flagging highly correlated combos as "unpriceable" and blocking them — [USPTO 11657680](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11657680)
- (Attribution flag for this bullet, and for the DraftSharks 0.295 / 20% figures in Q2: numbers come from search summaries, and which specific FantasyLabs/DraftSharks page carries each number was not confirmed by fetching.) NFL fantasy correlations (Rotoviz-era, via FantasyLabs): same-team WR2-QB 0.39, WR3-QB 0.35, QB-K 0.35, WR1-QB 0.34 — [FantasyLabs](https://www.fantasylabs.com/?p=66613). WR1-RB1 -0.07 and WR1-TE1 -0.08 — [FantasyLabs NFL Correlation Values](https://www.fantasylabs.com/?p=2732). An independent dataset found only RB1-WR1 statistically significant (r = 0.11) and WR1 vs. opposing QB insignificant; kicker vs. opposing D about -0.36 to -0.47 — [DraftSharks correlation matrix](https://draftsharks.com/article/thoughts-on--the-correlation-matrix-that-answers-every-question-you-ve-ever-had-about-dfs-stacking-)

### Inferences
- **Modeling choices (researcher's recommendation):**
  - MLB pitcher Ks: binomial(BF, matchup K%), with BF itself random (leash, efficiency), giving a negative-binomial-like overdispersed mixture.
  - Hitter hits: binomial(PA, hit rate), with PA by lineup slot.
  - NBA points/rebounds/assists: negative binomial or gamma-Poisson whose mean is minutes x rate. Most overdispersion comes from minutes variance (foul trouble, blowouts), so simulating minutes first and then counts conditional on minutes captures it naturally.
  - NFL yards: mixture of opportunity count (targets/carries, NB) x per-opportunity yards (skewed, heavy right tail). A plain normal is biased for alt lines and longest-reception markets.
  - TDs/HRs: Poisson or Bernoulli with a regressed rate.
- **Simulation beats closed forms for combos:** simulate the game environment first (team plays/possessions, score margin), then player opportunities conditional on it. This builds in the positive QB-WR correlation, the negative intra-team cannibalization (WR1 vs. TE1, about -0.08), and blowout-minutes effects for NBA starters.
- For "P+R+A" and similar combos, correlations between one player's stats (via shared minutes) mean the combo variance exceeds the sum of the individual variances. Combo lines set from independent marginals would misprice tails. (Hypothesis; not tested here.)

### Gaps
- No peer-reviewed goodness-of-fit study comparing Poisson vs. NB vs. normal for NBA/NFL/MLB player game logs was found.
- No published empirical correlation matrix for NBA same-game player stats (e.g., teammate points vs. points, player PRA vs. game total).
- Regulator parlay hold figures: a blog cited New Jersey Sept 2024 parlay hold of 24.2% vs. 4.4% for other bet types, and AGA blended hold of 7.0% (2019) to 10.2% (2025). The primary regulator/AGA reports were not located, so these are unverified.
