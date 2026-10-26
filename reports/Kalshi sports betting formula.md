# A Kalshi / Polymarket sports-betting formula: research, my own formulas, and backtests

*Caldo research, data through 17 Oct 2026. Every number below is either from a cited source in `research_notes/Kalshi sports betting formula/` or computed by the scripts in `research/` on real Kalshi, Polymarket and nflverse data, with fees.*

---

## 1. The short answer

**I did not find a formula that makes money on Kalshi or Polymarket after fees, and I tested a lot of them.** I built my own team-win formula and my own player-yards formula, then tested a dozen trading rules on about 5,000 Kalshi game sides, about 2,600 late-game NHL and MLB entries and 19,000 Kalshi player markets, across two seasons wherever the data existed. Every rule that looked profitable in one season either lost in the other season, or was too small to tell apart from luck.

Three reasons, all visible in the data:

1. **The prices are already as accurate as the best forecaster.** On matched NFL games, Kalshi ties the sportsbook closing line (log loss 0.6195 vs 0.6192 over 712 team sides; lower is better), and so does Polymarket (0.6079 vs 0.6070 over 344 games). My formula is clearly worse (0.637 on the Kalshi games), and so is every public model I could find (FiveThirtyEight, nfelo).
2. **The fee eats any small edge.** Kalshi's taker fee is 7% × P × (1 − P) per contract: 1.75¢ on a 50¢ contract. An edge has to be bigger than that just to break even, and real mispricings on these markets are usually 0–2¢.
3. **The edges people talk about don't hold up from season to season.** Late-game hockey favorites, NFL underdogs and posting resting bids all looked good in one sample and reversed in the next.

**One lead survived three separate periods but is not proven:** buying NO on the middle rung of a player's yards or receptions ladder when my player formula says he goes under.
- It returned **+5.0% ± 2.7%** per dollar over 1,111 bets (2025: +4.0%, 2026 Weeks 1–3: +1.3%, Weeks 4–6: +10.5%).
- Blind unders on the same rungs lost 0.9%.
- That is not strong enough to fund, so I built a scanner (`research/props_scan.py`) to paper-trade it (section 6).

**What does hold up is a ranking of which bets lose least.** If you are going to bet anyway (and your earlier "probability play" goal fits this), the cheapest bets were:
- **Buying NO on a long-shot player rung** (e.g. "Player X: 100+ receiving yards", NO at about 96¢) wins about 96% of the time and lost only **−1.5% ± 0.6%** per dollar.
- **Very heavy game favorites (90–100¢)** lost about **−0.6%**.
- **Things to avoid:** contracts under 20¢ (−17% to −59%), Kalshi parlays/combos (retail buyers lose about 15%), and fading line moves (−9% to −25%).

The details, the formulas, and every backtest follow.

---

## 2. What the research says

### 2a. What makes a team win (and what the market already knows)
- **The closing betting line is the best forecaster that exists.** De-vigged NFL closing moneylines, 2006–2025: 66.4% of winners picked, Brier 0.2111, log loss 0.6095 (n = 5,281). The best public models only tie it. FiveThirtyEight's Elo is 0.008 Brier worse, and blending it into the market adds nothing.
- **Inputs ranked by size (NFL):**
  1. Starting quarterback. The market values a starter at about 3–10 points over his backup.
  2. Team efficiency, mainly passing offense (EPA per play).
  3. Home field. Now only about 1.5–1.8 points; the average closing home spread was 1.52 in 2025, down from 2.4–2.6 before 2019. Home teams won 54.5% in 2021–25.
  4. Rest and byes. About 1–1.6 points raw, but only about 0.4 beyond what the spread already prices.
  5. Travel and time zones. Fractions of a point.
- **No public NFL model has a proven out-of-sample edge on closing lines.** nfelo, the best-known one, went about 52.0% against the spread over 2020–25 (~623 bets), below the 52.38% needed to break even.
- **Other leagues.** Predictability ranks NBA > NFL ≫ NHL ≈ MLB. Favorites win about 66–67% in the NFL, 59–61% in the NHL and 57–59% in MLB. Lines were well calibrated in all four leagues.

### 2b. Why players score what they score
- **Opportunity is sticky; efficiency is mostly noise.**
  - A WR's targets per game carry over from year to year (correlation r = 0.66).
  - Yards per target barely does (r = 0.22), and touchdown rate almost not at all (r = 0.12).
  - The same holds in the NBA (minutes and usage vs. 3-point %) and MLB (strikeout and walk rates stabilize fast; BABIP does not).
- **So the right formula is opportunity × heavily regressed efficiency × game environment.** Game environment means the betting total and spread: more expected points mean more plays, favorites run more, and underdogs throw more.
- **Defensive matchups add little.** "Points allowed to WRs" barely carries over between seasons (r ≈ 0.26–0.30, close to zero for WRs). Matchup rankings should be heavily discounted.
- **No peer-reviewed study shows a projection model beating player-prop closing lines.** Public 2025 NFL models beat simple baselines by 0–9% and report no edge.

### 2c. Where prediction markets misprice (and whether you can capture it)
- **Favorite–longshot bias.** Cheap Kalshi contracts (under about 20¢) lose heavily, worst for takers after fees. Contracts above 50–70¢ earn small returns, about +2–3% at best, mostly for makers. Polymarket sports show little of this bias.
- **Makers vs. takers.** Since mid-2024, makers (people whose limit orders get filled) earn about +1.1% per trade before fees on Kalshi sports, and takers lose the mirror image. Since 2025 the main game lines also carry a maker fee (1.75% × P × (1 − P)), which removes much of that edge.
- **No cross-venue arbitrage at retail scale.** Kalshi, Polymarket and the sportsbooks agree within 0–2¢ pre-game, less than the roughly 3–3.5¢ round-trip fee.
- **Parlays/combos are overpriced**, and more so the more legs they have. Retail combo buyers lose about 15% of stake.
- **Late-game distortion.** Published work reports near-certain winners slightly underpriced in the final minutes, worst in the NHL. **My own two-season test below did not confirm it.**
- **Who makes money.** About 31% of Polymarket wallets are net winners, and the top 1% take 76.5% of the profit. Market makers and professionals (Susquehanna and others) take most of it.

---

## 3. My formulas

### 3a. Team win formula (NFL), "points rating"
For each game:

- **Expected margin** = (R_home − R_away) + 2.5 × [not a neutral site] + 0.2 × clip(rest_home − rest_away, ±7 days) + 3.0 × (backup_QB_away − backup_QB_home)
- **P(home wins)** = Φ(expected margin / 12.5), where Φ is the normal curve.
- **After each game:** R_home += 0.08 × (clip(actual margin, ±21) − expected margin), and R_away moves by the same amount the other way.
- **Each new season:** every R shrinks by a third, toward average.
- A starter counts as a backup if he is not the team's most frequent starter over its previous 8 games.

All constants were tuned on 2002–2015 only.

**Version 2** adds recency-weighted offensive and defensive EPA per play and fits a logistic regression on 2007–2018. Coefficients:
- rating difference 0.139
- offensive EPA difference 1.06
- rest 0.034
- backup QB at home −0.35, backup QB away +0.21
- home field 0.79

### 3b. Player formula (NFL receiving yards, rushing yards, receptions)
For each player and game, using only information available before kickoff:

- **Usage:** recency-weighted targets and carries per game (half-life 6 games, half the weight carried into a new season), and his share of the team's targets and carries.
- **Efficiency, shrunk hard to the position average:**
  - yards per target, shrunk with 25 targets of prior (WR 8.2, TE 7.2, RB 5.8)
  - yards per carry, shrunk with 40 carries of prior (RB 4.3)
  - catch rate, shrunk with 25 targets of prior
- **Environment:** team implied points = total/2 ± spread/2, plus the team's spread.
- **Opponent:** yards the defense allowed to that position relative to league average, shrunk with 4 games of prior.
- **Mean:** expected stat = exp(a linear formula of the logs above), fitted by Poisson regression on 2018–2023. For receiving yards:
  - expected yards ∝ targets^0.15 × (yards per target)^0.76 × (target share)^0.78 × (team targets)^0.37 × (implied points)^0.41 × (opponent yards allowed)^0.27
  - Opportunity and environment do most of the work, as the research predicts.
- **Probability of each rung:** P(stat > line) is the share of past player-games with a similar predicted mean whose actual/predicted ratio cleared line/mean.

Out of sample (2024–2026), it is well calibrated and beats a "recent average" baseline at every threshold.

| 2025 season, out of sample | Hit rate | Formula's average prob | Log loss: formula | Log loss: recent average |
|---|---|---|---|---|
| 50+ receiving yards (n = 5,404) | 15.5% | 17.2% | 0.3157 | 0.3202 |
| 50+ rushing yards (n = 4,772) | 9.9% | 10.0% | 0.1719 | 0.1739 |
| 4+ receptions (n = 5,404) | 22.1% | 23.8% | 0.3717 | 0.3756 |

---

## 4. Backtest: team-win formula vs. the markets

**Accuracy on the same games** (log loss; lower is better; a coin flip scores 0.693):

| Games | My formula | Sportsbook close | Polymarket at kickoff | Kalshi at kickoff |
|---|---|---|---|---|
| NFL 2025–26, 344 games | 0.6302 | 0.6070 | 0.6079 | — |
| NFL 2025 + 2026 on Kalshi, ~712 team sides | 0.6367 | 0.6192 | — | 0.6195 |
| NFL 2016–24 validation, 2,475 games | 0.6322 | 0.6093 | — | — |

Blending my formula into the market: the best weight on the formula is **0**. Any weight makes the forecast worse.

**Betting where my formula disagrees with Kalshi** (buy at the ask + fee):

| When | Formula edge | 2025: bets, ROI (± SE) | 2026: bets, ROI (± SE) |
|---|---|---|---|
| 12h before | > 0 | 223, −7.0% (±8.7%) | 70, +10.2% (±16.7%) |
| 12h before | > 3% | 158, −10.0% (±10.7%) | 48, +23.1% (±21.5%) |
| Kickoff | > 0 | 222, −4.7% (±8.7%) | 68, +11.2% (±17.2%) |
| Kickoff | > 3% | 153, −8.5% (±10.5%) | 47, +24.9% (±22.7%) |

The small 2026 sample looked great. The bigger 2025 season shows it is noise. Against the sportsbook closing line (no Kalshi fee, but with vig), the formula's disagreements returned −6.0% over 2,115 bets in 2016–24.

---

## 5. Backtest: trading rules on Kalshi game markets

Data:
- **Kalshi game-winner markets with hourly prices:** 2025–26 NFL + NHL (1,254 team sides), plus 2026–27 college football, MLB, NHL, NFL and NBA (3,744 sides).
- **Minute-by-minute late-game prices:** NHL, both seasons.

Game start = Kalshi's listed time − 3 hours (verified against NFL kickoffs and the volume jump). Fees: taker 7% × P × (1 − P); maker 1.75% × P × (1 − P).

**Kalshi's prices are well calibrated.** Last pre-game price → how often that side actually won:
4.8¢ → 4.5%, 25.7¢ → 25.3%, 45.1¢ → 46.5%, 64.5¢ → 64.1%, 84.8¢ → 82.4%, 95.2¢ → 95.5%.

| Rule (buy at ask + fee, last pre-game hour) | 2025–26 | 2026–27 |
|---|---|---|
| Buy every side | −4.3% (1,216) | −5.4% (3,551) |
| Longshots under 20¢ | −58.9% (40) | −16.8% (361) |
| 20–40¢ | +5.4% ± 8.6% (279) | −5.2% ± 5.6% (648) |
| Coin flips 40–60¢ | −4.2% (602) | −4.4% (1,540) |
| Favorites 60–80¢ | −8.0% (280) | −3.0% (659) |
| Heavy favorites 80–95¢ | +6.2% ± 5.0% (39) | −3.5% ± 2.5% (242) |
| Follow a 4¢+ move from 12h to 1h before | +2.0% (33) | −3.8% (203) |
| Fade that move | −25.2% (32) | −8.9% (186) |
| **Post a bid** on 60–95¢ favorites (maker; fills only when a later trade prints at or below it) | NFL −5.0%, NHL −11.7% | MLB +16.6%, college FB −8.6%, NFL −16.0%, NBA −27.8% |

The resting bid shows why "be the maker" fails for a retail trader. Your bid gets filled mainly when bad news is pushing the price down, so the filled bids are disproportionately losers.

**Late-game favorites (NHL).** Rule: starting 110 minutes after puck drop, buy a side the first minute its ask enters a price band (with a tight spread), and hold.

| Band | 2026–27 (144 games) | 2025–26, independent test (300 games) |
|---|---|---|
| 70–85¢ | +4.3% ± 5.1% | −4.0% ± 3.9% |
| 85–92¢ | +2.9% ± 3.4% | −5.4% ± 3.0% |
| 92–96¢ | +1.0% ± 2.7% | −3.6% ± 2.3% |
| 96–98.5¢ | −0.4% ± 2.0% | −1.4% ± 1.6% |

This was the most promising lead from the research. It reversed on the larger season.

**Late-game favorites (MLB),** same rule from 150 minutes after first pitch:

| Band | 2026 season (1,050 entries) | 2025 season, independent test (300 games) |
|---|---|---|
| 70–85¢ | −2.2% ± 3.6% | −7.6% ± 6.0% |
| 85–92¢ | +0.1% ± 2.2% | −0.8% ± 3.9% |
| 92–96¢ | −0.9% ± 1.6% | +0.9% ± 2.5% |
| 96–98.5¢ | +0.3% ± 1.0% | +1.9% ± 1.0% |

The top band is slightly positive in both seasons (about +0.7% ± 0.7% pooled), but each bet risks $1 to win 2–3¢. That's break-even, not an edge.

**Sportsbook line vs. Kalshi.** Kalshi's NFL kickoff price sits within 0.6 points of the de-vigged sportsbook close in every price band. Only 58 sides in two seasons were cheap enough on Kalshi to bet against the sportsbook line, too few to be a strategy.

---

## 6. Backtest: player formula vs. Kalshi player markets

**Data.**
- **2026:** 18,859 Kalshi player markets, Weeks 1–6, every rung of every ladder (1,189 player-games).
- **2025:** 1,932 middle-rung markets from Weeks 4–18, as an independent test season. Kalshi's NFL player markets only began around Week 6 of 2025, and they were thin: a median of about 600 contracts per market and an average spread of 5¢, versus 1–2¢ in 2026.
- **Price used:** the last quote at or before kickoff.
- **Players included:** players with no stats in the game (active but never touched the ball) are kept, with the formula computed from their history. Leaving them out flattered the "over" bets.
- **Settlement check:** Kalshi's settlement matched the box score in 100% of markets.

**Kalshi's player prices are well calibrated, and buying YES (the over) loses at every price** (2026, all rungs, at kickoff):

| Kalshi price | Markets | Actually hit | Buy YES at ask + fee | Buy NO at ask + fee |
|---|---|---|---|---|
| 0–5¢ | 2,272 | 4.0% | −21.8% | **−1.5% (±0.6%)** |
| 5–10¢ | 2,905 | 8.4% | −7.7% | −2.7% |
| 10–20¢ | 2,877 | 16.0% | −4.4% | −3.5% |
| 20–30¢ | 1,881 | 25.5% | −6.8% | −3.6% |
| 30–40¢ | 1,492 | 34.6% | −7.7% | −3.1% |
| 40–50¢ | 1,297 | 44.3% | −6.9% | −2.8% |
| 50–60¢ | 1,194 | 51.3% | −10.5% | +2.8% (±3.6%) |
| 60–70¢ | 1,122 | 65.2% | −3.3% | −7.3% |
| 70–80¢ | 997 | 73.6% | −5.0% | −3.5% |
| 80–90¢ | 720 | 83.6% | −2.6% | −6.9% |

**Kalshi is more accurate than my formula in every period** (log loss, lower is better):

| Period | Markets | Kalshi | My formula |
|---|---|---|---|
| 2025, Weeks 4–18 (middle rungs) | 1,343 | 0.6749 | 0.6871 |
| 2026, Weeks 1–3 (all rungs) | 9,357 | 0.4561 | 0.4804 |
| 2026, Weeks 4–6 (all rungs) | 7,034 | 0.4824 | 0.4928 |

That holds for receiving yards, rushing yards and receptions separately. The gap narrows as the season goes on, as the formula gets more current-season data. Kalshi's market makers also see injury and depth-chart news that the formula doesn't.

**Betting the formula's disagreements on all rungs:**
- 2026 Weeks 1–3: YES −10.4%, NO −5.1%.
- 2026 Weeks 4–6: YES +2.9%, NO +4.3%.
- Not a strategy.

**The one lead left: NO on the middle rung when the formula says the player goes under.** Every ladder has a middle rung (e.g. a receiver's 60+ in a 30/45/60/75/90 ladder). Buying NO there when the formula's chance of the under beats the NO ask plus the fee:

| Rule (middle rung, buy NO at ask + fee) | 2025 Wk 4–18 | 2026 Wk 1–3 | 2026 Wk 4–6 | All three |
|---|---|---|---|---|
| Formula under by ≥ 3 points | +4.0% (437) | +1.3% (361) | +10.5% (313) | **+5.0% ± 2.7%** (1,111) |
| Formula under by any amount | +2.5% (593) | +1.6% (527) | +6.2% (444) | +3.2% ± 2.2% (1,564) |
| Formula under by ≥ 5 points | +0.6% (348) | −1.3% (266) | +10.9% (250) | +3.0% ± 3.0% (864) |
| Control: blind NO on every middle rung | −0.1% (1,367) | −1.5% (1,364) | −1.2% (975) | −0.9% ± 1.4% (3,706) |
| (YES when the formula says over) | −5.0% (306) | +12.2% (488) | +39.0% (326) | fails in 2025 |

At $20 a bet, the ≥ 3-point rule would have made **+$1,104 on $22,220 staked**, with a worst drawdown of $353 and a longest losing streak of 11.

**Why I still don't call it proven:**
- It is about 1.9 standard errors from zero, and I tested about 40 rule-by-sport cells. One or two cells this strong are expected by luck alone.
- The edge doesn't grow at a stricter threshold (≥ 5 points), which a real edge usually does.
- Much of it comes from 2026 Weeks 4–6.

What makes it worth watching:
- It is positive in all three periods, including the 2025 season it never saw.
- Blind unders on the same rungs lose, so the formula is adding something beyond "bet the under."
- In thin 2025 markets, overs on middle rungs were overpriced: they hit 41.8% against a 45.4% average price.

**Next step: paper-trade it** with `python research/props_scan.py`. On 17 Oct it listed 83 candidates for the Week 6 Sunday and Monday games.

### 6b. Model fix (25 Oct): teaching the formula who is playing

**The problem.** Most big disagreements with Kalshi came from injuries. The formula only knew each player's past usage, so it missed when a starter was out and his backup was taking over.

**The fix.** For every game, the formula now gets:
- **Vacated volume:** the share of the team's recent targets and carries held by regulars who are not active, both team-wide and within the player's own position group.
  - In past games, "not active" means not listed as active on nflverse's weekly roster.
  - For upcoming games, it means Out/Doubtful on the injury report, or not active on the roster.
- **Returning starters:** volume coming back from a player who missed recent games, which trims the backups' shares.
- **Backup QB flag:** whether the usual starting QB is out.
- **Fresh data:** the live scan re-downloads stats, rosters and the schedule before every run.

Separately, the team-win formula now treats a projected starter who is on IR or ruled out as a backup start (the Jalen Hurts case).

**What it changed.** Same data, same tests, log loss (lower is better):

| Period | Kalshi | Formula before | Formula after |
|---|---|---|---|
| 2025 Weeks 4–18 (middle rungs) | 0.6749 | 0.6871 | 0.6843 |
| 2026 Weeks 1–3 (all rungs) | 0.4561 | 0.4804 | 0.4778 |
| 2026 Weeks 4–6 (all rungs) | 0.4824 | 0.4928 | 0.4897 |

- **Closer to Kalshi, still behind it:** the gap shrank by about 10–30% in each period.
- **Fewer big disagreements:** lines where the formula and Kalshi differ by 20+ points fell from 913 to 767 in the backtest.
- **On the 25 Oct slate:** they fell from 110 to 76, and the injury-replacement cases dropped out.
- **What remains:** mostly players stepping into a new role with little history in it. In those cases Kalshi is still the better guide.

**The paper-trade rule after the fix** (NO on a middle rung, formula under by 3–10 points):
- **Result:** +5.5% ± 3.0% over 715 bets.
- **By period:** 2025 +5.9%, 2026 Weeks 1–3 +4.5%, Weeks 4–6 +6.1%.
- **Across versions:** it was positive in every period for every model version (+5.5% to +6.6%).
- **Status:** still not proven, but it held up through the change.

---

## 7. The playbook (if you bet anyway)

1. **Treat it as entertainment with a known cost.** On Kalshi game lines, buying at the ask costs about 4–5% of what you stake on average. At $20 × 3 bets a week over an 18-week season ($1,080 staked), that is roughly **$45–55 a season** expected.
2. **The "probability play" with the smallest cost:**
   - **NO on a player's long-shot rung** (e.g. 100+ yards at 96¢ NO): wins about 96% of the time, costs about 1.5%.
   - **Game sides priced 90¢ or more:** cost about 0.6%.
   - These win often, but one loss wipes out about 10 wins at 90¢ and about 24 wins at 96¢, so size them small.
3. **Never buy contracts under 20¢,** and skip Kalshi combos/parlays. That's where the money goes.
4. **Use limit orders, not market orders,** but don't expect a resting bid to be free money. It saves the spread on fills, and the fills skew toward bad news.
5. **Check against the sportsbook line before you buy.** If Kalshi is more expensive than the de-vigged sportsbook price, don't buy. This avoids paying extra; it doesn't create an edge.
6. **Don't chase a hot rule.** Every rule that looked good in one season here flipped in the next. Anything you want to try, paper-trade it for a season first. The scripts in `research/` make that easy.
7. **The one rule worth paper-trading:** run `python research/props_scan.py` before each slate. It lists middle-rung player markets where the formula's under beats Kalshi's NO price by 3+ points.
   - The scanner flags picks where the player is listed, a same-position teammate or the starting QB is out or questionable, or the player missed recent games.
   - Those are role changes Kalshi has priced and the formula can't see; log them separately and treat the unflagged picks as the real test.
   - Inactives come out 90 minutes before kickoff, so re-run close to game time.
   - Log the picks, record the results, and compare against the +5% backtest after 100+ bets.
   - Only if it is still clearly positive then should real money follow, at small flat stakes.

---

## 8. How this was done, and the limits

- **Data:**
  - Kalshi public API: live and `/historical` endpoints, hourly and minute candles.
  - Polymarket gamma + CLOB price history.
  - nflverse schedules, closing lines, and team and player weekly stats, 2018–2026.
- **Scripts** (all in `research/`):
  - `nfl_formula.py`, `nfl_formula_v2.py`, `nfl_vs_kalshi.py`
  - `fetch_kalshi_games.py`, `kalshi_games.py`, `kalshi_backtest.py`
  - `fetch_kalshi_endgame.py`, `endgame_backtest.py`
  - `nfl_player_yards.py`, `fetch_kalshi_props.py`, `props_backtest.py`, `bankroll_sim.py`
- **No look-ahead.** Formulas use only pre-game data. Rules trigger on prices a trader could have seen. In-sample and out-of-sample periods are kept apart.
- **Prices are hourly candle closes**, not full order books. Real fills could be slightly worse for big orders.
- **Settlement checks:** player markets agreed with the box score 100% of the time; Polymarket NFL settlement matched nflverse in 100% of games.
- **Sampling:** older seasons on Kalshi's historical endpoint are random samples (NFL complete; NHL 300 games; player markets: half the games, middle rung of each ladder).
- **Standard errors:** player-market errors are clustered by player-game.
- **Multiple testing:** about 40 rule-by-sport cells were tested, so one or two "significant" cells are expected by chance alone. That's why every lead had to pass a second season.
- **Fees** are as of Oct 2026. Kalshi taker 0.07 (maker 0.0175 on game lines); Polymarket International sports 0.05; Polymarket US 0.0695.
- **Not covered:** NBA and MLB player markets, in-game (live) trading beyond the late-game rule, and market making with real quoting infrastructure. That last one is where the documented profits on these venues actually go.


---

## 9. Applying Unabated's rules (26 Oct)

**Sources.** Unabated's videos "You're Working Too Hard: Using AI in Betting", "Betting The NFL: Are You Placing The Right Wagers?", "Simplify NFL Betting" and "The 4 Commandments of Injury News". I worked from Unabated's written summaries because YouTube blocks transcript downloads from this server.

### Their rules, and what each one became here

1. **Track your closing line value (CLV): did the price move toward your bet?**
   - **Built:** `research/paper_log.py` logs every scanned pick, grades it from Kalshi, and measures the move from our entry to kickoff.
   - **First reading, 120 picks (Weeks 6–7):** 91–29 and +5.3%. But the price moved toward us by **−0.3¢ ± 0.2¢**, which is zero.
   - **Verdict:** the market isn't confirming an edge yet.
2. **Props are softest midweek; Sunday is the most efficient.**
   - **Tested:** 25,000 Kalshi player markets, priced from 72 hours before kickoff.
   - **Kalshi does sharpen toward kickoff:** log loss falls from 0.4670 to 0.4630, and the spread narrows from 4.7¢ to 1.5¢.
   - **Our rule entered earlier looked better:** +16% at 72 hours vs +5% at kickoff.
   - **But not on the fair test:** players with no team news (the formula otherwise knows inactives the market didn't) came in at only +2% to +8% ± 5–9%. CLV was +0.3¢ to +0.6¢, not significant.
   - **Verdict:** no proven timing edge. Early lines also cost about 3¢ more in spread.
3. **Injury news: redistribute usage, and watch for overreaction ("a bridge too far").**
   - **Overreaction:** not on Kalshi. Backups' lines when a starter is out were priced exactly right (30.8% priced, 30.9% hit).
   - **The opposite effect showed up:** when a regular **returns**, the teammates who filled in stay priced too high.

     | Season | Priced | Hit | NO on the middle rung |
     |---|---|---|---|
     | 2026 | 29% | 21% | +9.8% ± 4.3% (263) |
     | 2025 | 45% | 40% | +3.1% ± 7.5% (187) |

     Pooled, about **+7% ± 4%**. This is now **rule B** in the scanner. It's promising, not proven.
4. **Anticipate the news.**
   - `props_scan.py --scenarios` lists the picks whose status flips if a Questionable regular sits, so you can act the moment inactives post.
5. **Price props with medians, not means.** The formula already prices the whole distribution (P(over the line)), not the average.
6. **Straight props, not same-game parlays.** This matches section 7; the parlay discussion stands.

**Not covered:** the Matt Downs video ("The Bet That Wins 87% of the Time"), whose content was unavailable here.

### Weekly routine now

```bash
python research/props_scan.py --scenarios --log    # Sat night / Sun morning; again ~90 min before kickoff
python research/paper_log.py grade                 # after the games
python research/paper_log.py summary               # record, profit, CLV by rule and week
```
