# Pricing Biases, Inefficiencies and Retail +EV in Sports Prediction Markets (Kalshi, Polymarket; Betfair/sportsbooks for comparison), as of Oct 2026

Note on evidence grades used below: [WP] = academic working paper or preprint (none of the Kalshi/Polymarket sports papers found are peer-reviewed yet); [OFFICIAL] = exchange docs, API output or regulatory filing; [JOURNALISM] = press or think-tank analysis; [ANECDOTE/VENDOR] = blogs, vendor pages, unreviewed GitHub projects. Research date: 2026-10-17.

## Q1. Which price buckets of Kalshi/Polymarket sports contracts have had positive or least-negative returns, before and after fees? (numbers, sample sizes)

### Takeaway
On Kalshi there is a clear favorite-longshot bias (FLB). Cheap contracts (<10-20c) lose heavily, and the loss is worst for takers after fees. Contracts above about 50-70c earn small positive returns, about +2-3% at best, and mostly for makers. Most of this evidence is cross-category, not sports-only. Kalshi sports moneylines are well calibrated from about 48h before the game to about 30 min before settlement. On Polymarket the classic two-sided FLB is absent in Sports: longshots are roughly break-even and ≥90c favorites are slightly negative even before fees. So no price bucket on either venue offers a robust, sizeable positive return to a taker after fees.

### Cited Findings
**Kalshi, all categories (Bürgi, Deng & Whelan) [WP]**
- Sample: 46,282 Yes contracts from 12,403 events, 2021 to April 2025. The filters were final volume ≥$1,000, final spread ≤20c, and markets open ≥24h. Prices run from close back to 10 days before, giving 156,986 Yes prices and 313,972 Yes+No prices. Sports only started in Jan 2025, and the authors say the results are "not sensitive to cutting the data off in December 2024 or to excluding the category containing sports bets." So this is mostly non-sports evidence. — [Bürgi, Deng & Whelan, GWU CER WP 2026-001 (Jan/Feb 2026)](https://www2.gwu.edu/~forcpgm/2026-001.pdf); also [SSRN 5502658](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5502658), [CEPR DP20631](https://cepr.org/publications/dp20631)
- Prices are heavily concentrated in the tails. 1-10c: 106,209 (33.8%). 90-99c: 106,209 (33.8%). 50-59c: only 8,351 (2.7%). — [Bürgi et al. Table 2](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- "Average loss rates for contracts costing 10c and under are over 60%" (taker fees included). Returns are "small positive" above 50c. Above 70c the paper finds "statistically significant, though small, positive post-fee returns." The equal-weighted average pre-fee return per contract is about -20%. — [Bürgi et al. §3.3](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Worked arithmetic from the paper: a 5c contract that wins 3% of the time returns -40% pre-fee, and a 95c contract that wins 98% returns +3.1% pre-fee. — [Bürgi et al.](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- The FLB holds in every volume quintile. The Mincer-Zarnowitz slope ψ is 0.045 in the lowest-volume quintile and 0.032 in the highest. Bigger average trade size does not reduce it (top trade-size quintile ψ = 0.043). The bias weakened in 2025 (ψ = 0.021, significant only at 10%) versus 2024 (ψ = 0.048). — [Bürgi et al. Tables 6, 7, 9](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Contract-level liquidity is small. Median total volume per contract is $8,982, top-decile average volume is $526,245, mean transaction $100, median transaction $35. — [Bürgi et al. §3.1, Table 3](https://www2.gwu.edu/~forcpgm/2026-001.pdf)

**Kalshi, larger sample with sports dominant (Becker) [WP/blog-paper, gross of fees]**
- Sample: 72.1M trades, 7.68M markets, $18.26B volume, 2021 to 2025-11-25. Resolved markets only, markets under $100 notional excluded. Sports is 72% of notional volume. — [Becker, "The Microstructure of Wealth Transfer in Prediction Markets"](https://www.jbecker.dev/research/prediction-market-microstructure)
- 1c contracts: takers win 0.43% against 1% implied (-57%), makers win 1.57%. 5c contracts win 4.18% (-16.36% mispricing). 95c contracts win 95.83%. Everything below 20c underperforms and everything above 80c outperforms. — [Becker](https://www.jbecker.dev/research/prediction-market-microstructure)
- Buying NO beats buying YES at 69 of 99 price levels. Dollar-weighted returns are YES -1.02% and NO +0.83%. The share of taker volume at 91-99c fell from 40-50% (2021-23) to under 20% (2025). — [Becker](https://www.jbecker.dev/research/prediction-market-microstructure)

**Kalshi, sports moneylines only (Moshrefi) [WP]**
- Sample: about 23M executed moneyline trades from early March to mid-May 2026. NBA 13,009,643, MLB 7,148,254, NHL 2,819,289. Canceled and voided markets are excluded and prices exclude fees. Calibration parameters "sit at their perfect-calibration reference values" from hours before settlement down to about 30 minutes. A mild distortion appears at 10-30 min. In the final 10 minutes the curve becomes step-like: in the 5-min bucket γ is 1.27-1.31 and α is 1.62 (NBA), 2.05 (MLB) and 4.56 (NHL). In that bucket "contracts trading at prices near 0 resolve favorably less often than those prices suggest, and contracts trading at prices near 1 resolve favorably more often". For the NHL, a 40c contract near expiry "has an empirical win rate near zero." — [Moshrefi, arXiv 2607.14430 (Jul 2026)](https://arxiv.org/abs/2607.14430)

**Kalshi + Polymarket, by domain and horizon (Le) [WP, replication code public]**
- Sample: 353M trades on 429k binary contracts, cutoff 2025-12-31. Kalshi Sports: 55,637 markets, 43.2M trades, 12.7B contracts, base rate 41.3%. Polymarket Sports: 31,636 markets, 49.1M trades, base rate 35.3%. — [Le, arXiv 2602.19520](https://arxiv.org/abs/2602.19520)
- Sports calibration slopes are 0.90-1.10 from 0 to 48 hours, i.e. near calibrated. Beyond one month the slope is 1.74, meaning strong underconfidence: favorites underpriced and longshots overpriced in long-dated sports futures. Sports has among the lowest calibration error of any domain, and trade size has no effect in Sports. — [Le, arXiv 2602.19520](https://arxiv.org/abs/2602.19520)

**Polymarket, sports vs other categories (Cardozo & Rivero-Wildemauwe) [WP]**
- Sample: the Polymarket Users dataset v1.3, Nov 11, 2022 to Mar 29, 2026, 588M trades by 2.48M wallets. Sports is 94.6M purchases and $8.72B (36.8% of dollars paid). Returns exclude trading fees and maker rewards. — [Cardozo & Rivero-Wildemauwe, arXiv 2609.12878 (Sep 2026)](https://arxiv.org/abs/2609.12878)
- Platform-wide, pooled purchases below 10c lose 19.3c per $ and purchases at ≥90c earn 0.83c per $. — [arXiv 2609.12878](https://arxiv.org/abs/2609.12878)
- **Sports** (longshot = <10c, favorite = ≥90c):

| Weighting | Longshots | Favorites |
|---|---|---|
| Equal child-market weights | **+2.43%** [95% CI -0.93, 5.79] | **-0.230%** [-0.285, -0.174] |
| Pooled purchases | +18.11% [-74.68, 110.91] | +0.137% [-0.100, 0.373] |

  For comparison, Politics favorites earn +1.044% and Crypto favorites +0.643% (equal-weighted). The authors' summary: "the two-sided pattern is robust in Crypto and Politics but surprisingly absent in Sports." — [arXiv 2609.12878, Table 8](https://arxiv.org/abs/2609.12878)

### Inferences
- Fee drag by bucket, computed from the formulas in Q6. A Kalshi taker (0.07·p·(1-p)) pays about 0.63c on a 10c contract, which is 6.3% of stake. At 50c the fee is 1.75c (3.5% of stake); at 90c it is 0.63c (0.7%); at 95c about 0.33c (0.35%). Break-even win rates are about 10.63% at 10c, 51.75% at 50c and 90.63% at 90c. Fees therefore magnify the longshot losses and only lightly dent the favorite edge, so the "least negative" place to take liquidity is the 70-95c range. Even there the documented pre-fee edge (+0.5 to +3%) is about the same size as the fee plus spread for a taker.
- For sports specifically on Kalshi, the cross-category FLB numbers (Bürgi) probably overstate the bias. Le and Moshrefi both find sports moneylines near-calibrated from about 48h to 30 min pre-settlement. The remaining sports FLB sits in (a) long-dated futures and (b) the final minutes of games.
- On Polymarket sports the evidence argues against blindly buying ≥90c favorites: they are slightly negative pre-fee in the equal-weighted measure. A taker now pays a 0.05 sports fee, so it would be worse after fees.
- Bürgi's -20% average and Becker's ±1.12% are not in conflict. Bürgi equal-weights percentage returns per contract-price observation, which is dominated by 1-10c contracts. Becker reports average per-trade excess returns (win rate minus price). Use bucket-level numbers, not headline averages.

### Gaps
- No public study gives post-fee returns by 10c bucket restricted to Kalshi sports with sample sizes. Becker reports a sports aggregate only, and Bürgi's sample is mostly pre-sports.
- Moshrefi gives calibration parameters but not dollar returns by bucket or the size of the near-expiry favorite edge in percentage points.
- No bucket-level return study was found for Polymarket US (the CFTC-regulated venue).

## Q2. Do makers earn positive returns on Kalshi sports markets? How much of the spread is captured, and what is adverse selection?

### Takeaway
Yes on average, and only since about mid-2024. Makers earn about +1.1% per trade gross across Kalshi and on sports specifically, and takers lose the mirror image. Before Kalshi's institutional market-making era (2021-2023), makers lost about 2%. Makers still lose on cheap contracts, and their edge is concentrated in buying higher-priced contracts and NO. Since 2025 most major sports game lines on Kalshi carry a maker fee (0.0175 coefficient), which removes a large share of that roughly 1% gross edge at mid prices. Direct measures of spread capture versus adverse selection on Kalshi sports were not found.

### Cited Findings
- Kalshi through April 2025 (makers paid no fees then): the average maker return was **-9.64%** and the average taker return **-31.46%** (equal-weighted, takers net of fees). Makers buying contracts ≥50c earned **+2.6%**, with a return standard deviation of 33%. Makers buy 43.5% of 1-10c contracts and 56.5% of 90-99c contracts. On closing-day prices, makers' losses on low-price contracts look like takers' losses, which the paper reads as a "Yogi Berra effect". — [Bürgi et al. §4, §6](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Mean excess return per trade (gross of fees), whole Kalshi: taker **-1.12%** (95% CI -1.13, -1.11), maker **+1.12%**. At 50c: taker -2.65%, maker +2.66%. Takers are negative at 80 of 99 price levels. **Sports**: taker -1.11%, maker +1.12%, gap 2.23pp, 43.6M trades, about $6.1B of sports taker volume. Other categories: Finance gap 0.17pp, Politics 1.02pp, Crypto 2.69pp, Entertainment 4.79pp. Makers buying NO earn +1.25% versus +0.77% buying YES. — [Becker](https://www.jbecker.dev/research/prediction-market-microstructure)
- Time trend: in 2021-2023 takers averaged +2.0% and makers -2.0%. The gap crossed zero in 2024 Q2. It moved from -2.9pp (takers ahead) before the 2024 election to +2.5pp (makers ahead) after. Volume went from $30M (2024 Q3) to $820M (2024 Q4). — [Becker](https://www.jbecker.dev/research/prediction-market-microstructure)
- A Roosevelt Institute analysis estimated that takers lost **$584M** to makers from July 2021 to mid-May 2026. [JOURNALISM, secondary] — [American Prospect, Aug 26, 2026](https://prospect.org/2026/08/26/house-always-wins-kalshi-prediction-markets/)
- Kalshi began charging maker fees after April 2025. Before that it charged takers only, at $0.07·P·(1-P) per contract rounded up. — [Bürgi et al. §2.2](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Live API check on 2026-10-17: 107 of 4,007 Kalshi Sports series have `fee_type = quadratic_with_maker_fees`. These include the main game lines: KXNFLGAME/SPREAD/TOTAL, KXNBAGAME/SPREAD/TOTAL, KXNCAAFGAME/SPREAD/TOTAL, KXNCAAMBGAME/SPREAD/TOTAL, KXNHLGAME, KXWNBAGAME, KXMLBGAME (multiplier 0.5), EPL/La Liga/Bundesliga/Serie A/Ligue 1/UCL/World Cup games, KXATPMATCH/KXWTAMATCH, F1, NASCAR, PGA, NFL anytime/first/2+ TD props, and most championship and award futures. The other 3,882 series are taker-fee-only with multiplier 1, and 18 MLB prop/spread/total/first-5-innings series are taker-only with multiplier 0.5. NFL yardage props (e.g. KXNFLPASSTDS, KXNFLRSHYDS) and all UFC series carry no maker fee. [OFFICIAL] — [Kalshi public API, GET /trade-api/v2/series?category=Sports](https://api.elections.kalshi.com/trade-api/v2/series?category=Sports)
- Maker coefficient: resting orders "pay less (0.0175 rate) or nothing, by market". The taker rate is 0.07. The S&P 500 and Nasdaq-100 series pay half (0.035). Fees were checked against Kalshi's Sep 22, 2026 schedule. [VENDOR summarizing official PDF] — [DeFi Rate fee page (Oct 2, 2026)](https://defirate.com/prediction-markets/fees/)
- In-game adverse selection signal on Kalshi NBA live markets: price changes absorb only about **0.64** of a one-minute change in an out-of-sample win-probability model. The missing adjustment predicts drift over the next 5-15 minutes and is larger when liquidity is thin. However, "executable-style returns that buy at the ask and sell at the bid are negative." The pre-game sample is 2,839 contracts from 1,421 games. — [Angelini & De Angelis, arXiv 2606.07811 (Jun 2026)](https://arxiv.org/abs/2606.07811)
- On Polymarket NBA, market makers reprice within seconds after live shocks: single-market arbitrage episodes last a median of 3.6s. In one blowout game "market makers ... withdr[e]w their quotes, leaving stale mispriced orders." — [Cheng, Yang & Zou, arXiv 2605.00864](https://arxiv.org/abs/2605.00864)
- Polymarket: "Successful traders provide liquidity using limit orders that resolve favorably ... while unsuccessful traders take liquidity using market orders" (Akey, Grégoire, Harvie & Martineau; abstract via search). — [SSRN 6443103](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103)

### Inferences
- Rough maker economics on a Kalshi maker-fee series, computed from the fee formula: at 50c the maker fee is 0.0175 × 0.25 = 0.4375c, which is 0.875% of stake. Against Becker's gross maker edge (about +1.1% on average, +2.66% at 50c), that removes roughly a third to most of the edge. On series without maker fees (most props, smaller leagues, UFC) the gross maker edge is kept in full, but those books are thinner and probably more exposed to informed flow.
- Becker's 2021-23 numbers (makers -2%) show that a naive retail maker who quotes stale prices loses. The positive maker edge appeared with professional market makers who cancel and reprice fast. A retail maker competes with those desks for queue position and will be picked off on news (injuries, lineup changes, in-game scoring) unless quotes are pulled faster than the 3-10 second windows above.
- The FLB pattern suggests the most defensible retail maker strategy is to rest bids on favorites or NO sides at 70-95c in pre-game sports markets, preferably on series without maker fees. This needs out-of-sample testing on post-2025 sports data.

### Gaps
- No study decomposes Kalshi sports maker P&L into spread capture versus adverse selection (realized spread or markouts by horizon). The Kalshi public trade feed gives `taker_side`, so this could be computed (see Q5).
- No Kalshi sports maker returns net of the 0.0175 maker fee have been published.
- Spreads quoted by Susquehanna or other market makers on Kalshi sports are not public (see Q8).

## Q3. How accurate are Kalshi/Polymarket game prices vs sportsbook closing lines (Brier, calibration)? Does one lead the other?

### Takeaway
Pre-game, Kalshi, Polymarket and a de-vigged sportsbook consensus are statistically indistinguishable in accuracy: Brier differences are about 0.0002-0.0003 across thousands of games. No consistent lead-lag direction has been shown. The only credible evidence comes from unreviewed student or independent projects. No peer-reviewed head-to-head with Pinnacle closing lines was found.

### Cited Findings
- 5,333 games across six leagues, May 2025 to July 2026, home-side Brier. Kalshi **0.2196** (calibration slope 0.956), Polymarket Global **0.2198** (0.954), 11-US-book de-vigged consensus **0.2196** (1.002). Every pairwise difference has a 90% CI within ±0.001. Pinnacle used as an alternative benchmark gives the same equivalence conclusion. On lead-lag, "some specifications detect lagged predictability ... in both directions", but "no consistent directional leader emerges". A Polymarket US subsample (2,631 games) scores 0.2307 versus Kalshi 0.2303. The README says the work is not peer-reviewed. [ANECDOTE: Northwestern undergraduate project] — [calibrating-the-crowd (GitHub)](https://github.com/dylanmryan/calibrating-the-crowd)
- MLB, Jul 6 to Oct 15, 2026, 1,003 games, last pre-first-pitch price (median 15 min before). Kalshi Brier **0.2380**, Polymarket 0.2383. On a like-for-like subset of 463 games: Kalshi 0.2385, Polymarket 0.2388, book median 0.2386. Kalshi was "closer" in 55.2% of the 348 games with any disagreement (p = 0.06, not significant). [ANECDOTE/independent blog] — [Nebula Insights](https://nebulainsights.net/blog/kalshi-vs-polymarket-mlb-prices.html)
- Polymarket NBA 2024-25 versus bookmakers (Brier and calibration): the analysis concludes Polymarket aggregates information "as effectively as professional bookmakers". This is from a search summary only, as the page returned HTTP 429. [VENDOR] — [Polymarket Analytics](https://polymarketanalytics.com/research/nba-sportsbooks-vs-prediction-markets)
- Kalshi's self-published calibration study covers about 2.2M resolved markets in all categories. Brier falls from about 0.08-0.09 at three months to about 0.02 at close. [OFFICIAL/marketing] — [Kalshi Research, Calibration](https://kalshi.com/research/publications/calibration)
- In-game: Kalshi NBA prices "respond rapidly to public signals" but under-react (0.64-for-one). Underreaction is larger for salient events in thin markets, with predictable drift over several minutes that is not tradable after the spread. — [Angelini & De Angelis, arXiv 2606.07811](https://arxiv.org/abs/2606.07811)
- Weak claims: a GitHub PR reports Polymarket beating Pinnacle's close on a 185-match subset [ANECDOTE] — [pointless-repo PR #14](https://github.com/pointlessbassmusic-byte/pointless-repo/pull/14). SmartStake claims Kalshi MLB player-prop lines were sharper than Pinnacle's [VENDOR] — [SmartStake](https://www.smartstake.app/learn/kalshi-vs-sportsbook).

### Inferences
- A model that cannot beat the de-vigged sportsbook consensus will not beat Kalshi or Polymarket closing prices either. The exchanges appear to price off the same information set, probably with sportsbook-informed market makers. Any pre-game edge has to come from information or modeling better than the market, not from the venue being "soft".
- Calibration slopes of about 0.955 on both exchanges (versus 1.002 for books) hint that exchange prices are slightly too extreme at the home-side level. The intervals include 1, so this is not established.

### Gaps
- No study measures closing-line value (CLV) for bets placed on Kalshi or Polymarket at earlier times against their own close or the Pinnacle close.
- No peer-reviewed lead-lag (Granger or minute-level) study of Kalshi versus Pinnacle or Betfair was found.
- Per-league and per-market-type (spread/total/props) Brier comparisons are not reported.

## Q4. Are there documented, repeatable cross-venue arbitrage or stale-price opportunities, and what are the practical limits?

### Takeaway
Pre-game cross-venue gaps between Kalshi and Polymarket sports moneylines are usually 0-2c, rarely 2-3c and essentially never 5c. That is below the roughly 3-3.5c round-trip taker fee at mid prices. Real but tiny opportunities exist in-game: combinatorial moneyline/spread dislocations in the final minutes on Polymarket. These last seconds, have shallow depth (about 15 shares) and earn about 1% median. Across all categories, the largest documented arbitrage profits on Polymarket came from intra-venue structural arbitrage (negRisk baskets) captured by a few bots, not from retail cross-venue trading.

### Cited Findings
- Kalshi vs Polymarket MLB pre-game (last observation, 1,003 games, Jul-Oct 2026): 65.3% identical prices, 32.0% differ by 1-2c, 0.8% by 2-5c, 0% by ≥5c. The maximum gap was 3.0c and the mean 0.3c. The two venue observations were a median of 0.27 min apart. — [Nebula Insights](https://nebulainsights.net/blog/kalshi-vs-polymarket-mlb-prices.html)
- Polymarket NBA, 173 games, 75,088,497 order-book snapshots, 3,042 markets (data spans Oct 2024 to Feb 2026). Single-market arbitrage (YES+NO <$1): only **7** executable episodes, all in-game, median duration **3.6s**. Capped at $100 per episode, aggregate profit was **$210.19**, skewed by one stale-book blowout. Combinatorial moneyline-versus-spread arbitrage: **290** episodes (279 in-game, 11 pre-game), **median return 101 bp**. Capped aggregate profit was **$559.59** versus $2,032.75 uncapped. In **76.9%** of episodes the $100 budget could not be deployed, with an average executable size of about **14.8 shares**. The "middle" jackpot was never realized. Polymarket charged no fees on NBA markets during the sample. Polling latency was about 171 ms round trip. — [Cheng, Yang & Zou, arXiv 2605.00864](https://arxiv.org/abs/2605.00864)
- Across 10 venues and 100k+ events (2018-2025), about 6% of events are listed concurrently on several platforms. Semantically equivalent markets show "persistent execution-aware price deviations of 2-4% on average". Fees, spreads, gas, tick size and differing resolution semantics sustain these gaps, and "regulatory segmentation contributes ... but does not fully account for them". This is not sports-specific. — [Gebele & Matthes, arXiv 2601.01706](https://arxiv.org/abs/2601.01706)
- Polymarket intra-venue arbitrage (all categories, Apr 2024 to Apr 2025): about **$40M** of realized profit across market-rebalancing and combinatorial arbitrage, detected partly with LLM dependency matching. A sports breakdown was not verified. — [Saguillo et al., arXiv 2508.03474 / AFT 2025](https://arxiv.org/abs/2508.03474v1)
- Polymarket negRisk (multi-outcome) arbitrage: about $1.12M reconstructed profit, of which $1.086M came from converter-enabled strategies. One cluster made 381,748 USDC in seven minutes. Settlement-basket profit is highly concentrated, with one actor taking about 76% (text truncated in extraction). — [Gebele, Mutzel & Matthes, arXiv 2608.00666 (Aug 2026)](https://arxiv.org/abs/2608.00666)
- Kalshi live NBA: the predictable post-news drift "does not translate into a simple arbitrage opportunity once bid-ask costs are imposed." — [Angelini & De Angelis](https://arxiv.org/abs/2606.07811)
- Practitioner claims (unverified): all-in fees "typically eat 3-5 cents per cross-platform pair". Sharp-book-versus-prediction-market sports edges are described as about 1-3%. [VENDOR] — [Odds-API blog](https://odds-api.io/blog/polymarket-kalshi-arbitrage-sports-betting-api); [NYC Servers guide](https://newyorkcityservers.com/blog/prediction-market-arbitrage-guide)

### Inferences
- Fee hurdle for taker-taker cross-venue arbitrage at 50c, computed from Q6 formulas: Kalshi 1.75c plus Polymarket US 1.74c (θ = 0.0695) is about 3.5c. Kalshi plus Polymarket International sports (0.05) is about 3.0c. With a maker leg on a Kalshi series without maker fees, the hurdle is about 1.25-1.74c. Given the MLB gap distribution (max 3c), taker-taker pre-game arbitrage was essentially never available in that sample. Maker-taker "legging" exposes the trader to fill risk.
- Execution risks beyond fees:
  - Settlement non-equivalence. Kalshi settles a game not played within 48h at a "last fair price", while Polymarket keeps the market open or resolves 50-50 (see Q6). A void on one side can turn a hedge into a naked position.
  - Capital is locked on two venues. Polymarket International is not open to US persons.
  - Position limits apply, e.g. Kalshi's $25k position-accountability level per strike per member on NFL games.
- The most realistic edge for a small retail bot is not riskless arbitrage. It is a stale-quote snipe in thin in-game books right after scoring events, competing against professional market makers with sub-second latency. Documented sizes are retail-scale only (tens of dollars per episode).

### Gaps
- No study measures how long Kalshi-vs-Polymarket, or exchange-vs-sportsbook, sports gaps persist intraday, or their size distribution in-game.
- No study of exchange-vs-Betfair or exchange-vs-offshore-book arbitrage frequency was found.
- The "IMDEA study" that vendors cite is presumably Saguillo et al. Its sports-specific profits were not confirmed.

## Q5. What are the best data sources for historical Kalshi and Polymarket sports prices?

### Takeaway
For Kalshi, use the official REST API. It splits data into live and historical tiers (`/historical/*` for trades, markets and candlesticks) and exposes `taker_side`, which allows maker/taker analysis. Becker's public GitHub dataset covers 72.1M trades through Nov 2025. For Polymarket, use the CLOB `/prices-history` endpoint (by token ID), the Data API for trades, and the Hugging Face "Polymarket Users" dataset (588M trades, maker flag, CC-BY 4.0). Sportsbook closing odds still need a paid provider.

### Cited Findings
- Kalshi live versus historical endpoints. Markets: `GET /historical/markets` (cutoff `market_settled_ts`). Candlesticks for settled markets: `GET /historical/markets/{ticker}/candlesticks`. Trades: `GET /historical/trades` (cutoff `trades_created_ts`). Own fills, orders and positions also have historical endpoints. `GET /historical/cutoff` returns the moving cutoffs. Series and events stay on their original endpoints. [OFFICIAL] — [Kalshi docs: Historical data](https://docs.kalshi.com/getting_started/historical_data)
- The Kalshi series endpoint returns `fee_type`, `fee_multiplier`, `settlement_sources`, `contract_terms_url` and tags for every series. It worked without authentication on 2026-10-17. [OFFICIAL] — [Kalshi API series endpoint](https://api.elections.kalshi.com/trade-api/v2/series?category=Sports)
- Kalshi transaction data identify maker and taker directly, avoiding Lee-Ready misclassification. Researchers pulled it via the API with Python. — [Bürgi et al. §4](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Becker dataset: 72.1M Kalshi trades and 7.68M markets, 2021 to 2025-11-25, at GitHub `jon-becker/prediction-market-analysis`. — [Becker](https://www.jbecker.dev/research/prediction-market-microstructure)
- Polymarket Users dataset (Akey et al.; Grégoire): Hugging Face `vgregoire/polymarket-users` v1.3 (2026-07-06), CC-BY 4.0. It covers Nov 11, 2022 to Mar 29, 2026, with 588M trades and 2.48M wallets. It includes buyer and seller wallets, which side was maker, market category (incl. "Sports"), parent event and winning token. — [Cardozo & Rivero-Wildemauwe, arXiv 2609.12878 (data section and references)](https://arxiv.org/abs/2609.12878)
- Polymarket price history: CLOB `GET /prices-history` and `POST /batch-prices-history` (with `start_ts`, `end_ts`, `fidelity`), keyed by CLOB token IDs from the market's `clobTokenIds`. Trades come from the Data API (`data-api.polymarket.com`). [OFFICIAL docs via search snippets] — [Polymarket docs: prices history](https://docs.polymarket.com/api-reference/markets/get-prices-history.md); [batch prices history](https://docs.polymarket.com/cn/api-reference/markets/get-batch-prices-history)
- Replication code for the Kalshi + Polymarket calibration-by-domain study: `github.com/namanhzz/prediction-market-calibration`. — [Le, arXiv 2602.19520](https://arxiv.org/abs/2602.19520)
- Kalshi-vs-sportsbook study: its sportsbook data came from a paid provider and cannot be redistributed, and its access lapses Sep 2026. — [calibrating-the-crowd](https://github.com/dylanmryan/calibrating-the-crowd)
- High-frequency order book: Cheng et al. built 75M Polymarket order-book snapshots by polling. This implies there is no free historical order-book archive and you must record your own. — [arXiv 2605.00864](https://arxiv.org/abs/2605.00864)
- The American Prospect mentions a Dune dataset "behind a $40,000 paywall" in its Kalshi coverage. The context is unclear. [JOURNALISM] — [American Prospect](https://prospect.org/2026/08/26/house-always-wins-kalshi-prediction-markets/)

### Inferences
- For a Kalshi sports backtest:
  - Pull settled game series (KXNFLGAME, KXNBAGAME, KXMLBGAME, etc.) from `/historical/markets`.
  - Get trades with `taker_side` from `/historical/trades`, and minute or hour candlesticks for bid/ask history.
  - Join `fee_type` and `fee_multiplier` per series.
  - Handle non-binary "last fair price" settlements (see Q6).
- Candlestick midpoints overstate tradability. Backtest at the ask for takers, and model queue position and fill probability for makers.

### Gaps
- How far back Kalshi's historical endpoints go and their rate limits are not stated in the docs page reviewed.
- No free historical order-book (depth) archive was found for either venue.
- No vetted free source of historical sportsbook or Pinnacle closing lines was identified in this pass.

## Q6. What are the exact current fee schedules and the settlement/void rules that matter for backtesting?

### Takeaway
All three venues use the same p·(1-p) "quadratic" fee shape with different coefficients:

| Venue | Taker coefficient | Maker side |
|---|---|---|
| Kalshi | 0.07 (some series × 0.5) | 0.0175 maker fee on about 107 sports series, mostly main game lines |
| Polymarket International | Sports 0.05 | Makers free; 15% (or 20%) rebate of taker fees |
| Polymarket US | 0.0695 (since Sep 17, 2026; combos carry an extra term) | Maker rebate of θ = 0.0125 |

Kalshi game contracts settle at a discretionary "last fair price" when a game is postponed beyond 48h, abandoned early or forfeited pre-game. Ties pay 50c when no tie strike is listed.

### Cited Findings
**Kalshi**
- Fees through April 2025: takers paid $0.07·P·(1-P) per contract, rounded up to the cent, and makers paid nothing. Maker fees started after April 2025. With round-up on 100 contracts, the 50c fee is 1.77% of price versus 1.75% nominal. — [Bürgi et al.](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Current fees: taker 0.07·C·p·(1-p) "rounded up to the cent; some markets charge less". Maker 0.0175 rate "or nothing, by market". S&P 500 and Nasdaq-100 pay 0.035. There is no settlement fee. Kalshi "rounds each fill up to the cent but carries the overpayment across an order's fills and refunds it". [VENDOR citing Kalshi schedule of Sep 22, 2026] — [DeFi Rate](https://defirate.com/prediction-markets/fees/). The official PDF ([kalshi.com/docs/kalshi-fee-schedule.pdf](https://kalshi.com/docs/kalshi-fee-schedule.pdf), "Fee Schedule for July 2026 - 7.7.26 Update") was behind a bot checkpoint and could not be read directly.
- Rounding mechanics: each fill has a trade fee (model fee rounded up to 6 decimals), a rounding fee and a rebate. Rounding fees go into a per-order accumulator and are rebated, and the net fee is never below $0. Direct members' balances align to $0.0001 and non-direct members' to $0.01. [OFFICIAL] — [Kalshi docs: fee rounding](https://docs.kalshi.com/getting_started/fee_rounding)
- Maker fees apply "only when a trade is ultimately executed", and there is no fee to cancel. Some markets have different fees "due to special events (such as the election, awards ceremony, or a large sporting championship)". [OFFICIAL] — [Kalshi Help: Fees](https://help.kalshi.com/trading/fees)
- Which sports series carry maker fees: 107 of 4,007, as of 2026-10-17 (full list summarized in Q2). MLB game moneyline (KXMLBGAME) has maker fees with multiplier 0.5. 18 MLB prop/spread/total/F5 series are taker-only with multiplier 0.5. [OFFICIAL API] — [Kalshi series API](https://api.elections.kalshi.com/trade-api/v2/series?category=Sports). That the multiplier scales both the 0.07 and 0.0175 coefficients is an inference, consistent with the 0.035 index series.

**Polymarket International**
- Fee = C × feeRate × p × (1-p). Taker rates: **Sports 0.05**, Crypto 0.07, Politics/Finance/Tech/Mentions 0.04, Economics/Culture/Weather/Other 0.05, Geopolitics 0. "Makers are never charged fees". Maker rebates (share of taker fees) are **Sports 15%**, Crypto 20%, others 25%. There is a tiered taker rebate program, and fees are rounded to 5 decimals (minimum 0.00001 USDC). [OFFICIAL] — [Polymarket docs: Fees](https://docs.polymarket.com/trading/fees)
- Conflict: the Polymarket Help Center Maker Rebates page (Jul 21, 2026) lists Sports at **20%** per search snippet — [Polymarket Help: Maker Rebates Program](https://help.polymarket.com/en/articles/13364471-maker-rebates-program). Third-party guides say sports went from 0.03 to 0.05 in July 2026, and that NFL and college football games moved to 0.03 in Oct 2026 (unverified) — [startpolymarket fee calculator](https://startpolymarket.com/tools/fee-calculator/).
- Historical note for backtests: Polymarket charged **zero** fees on NBA markets during Oct 2024 to Feb 2026 — [Cheng et al.](https://arxiv.org/abs/2605.00864) — and ran a "zero-fee" order book during the 2018-2025 observation window of Gebele & Matthes — [arXiv 2601.01706](https://arxiv.org/abs/2601.01706).

**Polymarket US (QCX LLC, CFTC-regulated)**
- Fee = Θ × C × p × (1-p). Taker Θ went from 0.05 to **0.06**, effective Jul 1, 2026 (max $1.50 per 100 contracts at 50c). Maker rebate Θ = **-0.0125** (max $0.31 per 100). [OFFICIAL] — [CFTC filing, Jul 7, 2026](https://www.cftc.gov/filings/orgrules/rules0707269057.pdf)
- Taker Θ went from 0.06 to **0.0695**, effective Sep 17, 2026. The maker rebate, the tiered taker rebate and block-trade fees are unchanged. [OFFICIAL] — [CFTC filing, Sep 21, 2026](https://www.cftc.gov/filings/orgrules/rules09212628660.pdf)
- Combos: the taker fee is C × p × [0.0695(1-p) + 0.04(1-p)^4], effective Sep 25, 2026. Straight trades stay at 0.0695·C·p·(1-p). [OFFICIAL] — [CFTC filing, Sep 29, 2026](https://www.cftc.gov/filings/orgrules/rules09292630356.pdf)
- A volume rebate gives takers above $250k monthly volume 10/25/50% back, from Oct 1, 2026. Fills round to the nearest cent, ties to even. [VENDOR] — [DeFi Rate](https://defirate.com/prediction-markets/fees/)
- Robinhood (for comparison): a 10% × p(1-p) commission (5% with Gold) capped at 1c, plus an exchange fee up to 1c, charged on open and on close. [VENDOR] — [DeFi Rate](https://defirate.com/prediction-markets/fees/)

**Settlement rules: Kalshi (contract terms) [OFFICIAL]**
- **NFL/football (FOOTBALLGAMEWIN)**:
  - Ties pay "Yes" holders $0.50 and "No" holders $0.50 if no "Tie" strike is listed. Overtime is included.
  - A game postponed but started within 48h stays open. Otherwise it resolves at "last fair market price as determined by Kalshi".
  - Suspended before 55 minutes of play and not resumed within 48h: last fair price, except periods already concluded. After 55 minutes, or if the league declares the game final: settles on the result so far.
  - Forfeit before kickoff: last fair price. Home/away reversal or a move outside 48h: last fair price.
  - Settlement uses the first official result unless clearly erroneous. Position accountability level is $25,000 per strike per member. Settlement is no later than the day after expiration.
  - — [Kalshi FOOTBALLGAMEWIN terms](https://assets.kalshi.com/contract_terms/FOOTBALLGAMEWIN.pdf)
- **MLB (BASEBALLGAMEWIN)**:
  - The 48h postponement and suspension rule applies, otherwise last fair price.
  - Unneeded series games (e.g. Game 6 when the series ends 4-1) resolve at last fair price.
  - There are explicit doubleheader make-up sequencing rules.
  - A forfeit after first pitch resolves "No" for the forfeiting team.
  - — [Kalshi BASEBALLGAMEWIN terms](https://assets.kalshi.com/contract_terms/BASEBALLGAMEWIN.pdf)

**Settlement rules: Polymarket (per-market rules; aggregator copies)**
- Postponed games: the "market will remain open until the game has been completed". MLB canceled with no make-up: "resolve 50-50". Some soccer markets resolve "No" on cancellation instead. Esports resolve 50-50 if delayed more than 7 days. Official stats come first; if none are published within 24h, a consensus of credible reporting is used. [ANECDOTE: third-party mirror of market rules; check each market] — [polyguana market rule examples](https://polyguana.com/market/2406030)

### Inferences
- Backtest fee code:
  - Kalshi taker = ceil-ish(0.07·m·C·p(1-p)). Maker = 0.0175·m·C·p(1-p) only on `quadratic_with_maker_fees` series, with m = `fee_multiplier`.
  - Polymarket International taker = 0.05·C·p(1-p) for sports (0 before the 2026 fee rollout on many sports markets). Makers get a rebate share.
  - Polymarket US taker = 0.06 (Jul 1 to Sep 16, 2026), then 0.0695. Maker rebate = 0.0125·C·p(1-p).
  - Date-stamp fee regimes. Applying today's fees to 2025 data, or vice versa, misstates returns by up to about 1-2% of stake at mid prices.
- The Polymarket US combo surcharge bites at low prices. At p = 0.10 the combo fee is about 0.89c (8.9% of stake) versus 0.63c (6.3%) for a straight bet. At p = 0.02 it is about 10.5% of stake (my arithmetic from the filed formula).
- "Last fair price" settlements are discretionary and non-binary. Backtests must drop them (as Moshrefi does for voided/canceled markets) or model them explicitly. Cross-venue hedges must account for Polymarket's different postponement treatment.

### Gaps
- The official Kalshi fee-schedule PDF text was not read directly, so the maker coefficient 0.0175 and the series list rely on a vendor summary plus API fee-type fields.
- Polymarket International's per-sport (NFL/NCAAF) rates and the effective date of the sports fee introduction were not confirmed from an official source.
- Polymarket's general sports postponement and void policy was not found in an official rulebook. Only per-market rule text was seen.

## Q7. Timing, line movement and in-game effects: days before vs at game start, late information, live markets

### Takeaway
Accuracy rises steadily toward close. Sports moneylines are well calibrated from about 48h out to about 30 min before settlement. Two timing anomalies are documented on Kalshi: (1) a strong FLB in long-dated sports futures (more than one month out), and (2) a step-like distortion in the final minutes of games, where losing sides stay overpriced and near-certain winners underpriced ("Yogi Berra" effect), worst in the NHL, then MLB, then NBA. In-game, Kalshi NBA prices under-react to scoring news, but the drift is not tradable after the spread.

### Cited Findings
- Kalshi MAE "declines with each day as the market gets closer to closing", with a "steep drop" on the final day. The FLB remains significant at every horizon from 0 to 10 days: ψ = 0.036 at day 0 and 0.017-0.041 at days 1-10. — [Bürgi et al. Fig. 4, Table 5](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Sports slopes are 0.90-1.10 at 0-48h and 1.74 beyond one month. The large-trade compression gap in Sports is 0.35 at 1 month+ and "near zero elsewhere". — [Le, arXiv 2602.19520](https://arxiv.org/abs/2602.19520)
- Final 10 minutes of NBA/MLB/NHL moneylines: a Prelec curvature above 1, "the opposite sign of the canonical lottery-choice fit". The paper attributes it to insurance demand by traders holding losing positions, or possibly to liquidity withdrawal or late uninformed traders. Distortion order is NHL > MLB > NBA. — [Moshrefi, arXiv 2607.14430](https://arxiv.org/abs/2607.14430)
- An earlier literature finding: InTrade prices for losing teams in the final 15 minutes were too high (Page 2012, the "Yogi Berra bias"). Bürgi et al. see a similar final-day effect on Kalshi. — [Bürgi et al. §2.1, §4](https://www2.gwu.edu/~forcpgm/2026-001.pdf)
- Kalshi NBA live: one net point scored in the prior minute raises the midpoint by a measurable amount. Prices absorb about 0.64 of the benchmark change on impact and drift over the following 5-15 minutes. The drift is stronger for salient events in thin markets, but executable returns are negative. — [Angelini & De Angelis](https://arxiv.org/abs/2606.07811)
- Polymarket NBA: 279 of 290 combinatorial arbitrage episodes occurred in-game, "overwhelmingly concentrated in the final minutes of live play". — [Cheng et al.](https://arxiv.org/abs/2605.00864)
- Two MLB venues converge pre-game: the median last observation was 15 min before first pitch and 65% of games had identical prices. — [Nebula Insights](https://nebulainsights.net/blog/kalshi-vs-polymarket-mlb-prices.html)

### Inferences
- Candidate retail angles are in the tails of time:
  - (a) Sell (buy NO on) longshots in long-dated sports futures, where slope 1.74 means overpriced longshots. Capital lockup is long and fees apply.
  - (b) Buy near-certain winners, or sell trailing teams, in the last minutes of NHL/MLB games. The probability edge is large per Moshrefi, but the per-contract dollar edge at 95-99c is small, and fees plus spread plus tail risk (late goals) must be modeled.
  - Neither has a published post-fee P&L.
- Closing-line value on these exchanges is unmeasured. Given the near-perfect pre-game calibration, early-market "line shopping" edges are likely small.

### Gaps
- No published returns exist for Kalshi or Polymarket sports by hours-before-start, and no CLV study exists.
- No direct dollar-return estimate exists for the final-minutes S-shape (Moshrefi reports calibration parameters only).

## Q8. Who makes money on these venues (leaderboards, share of profitable users, market makers)?

### Takeaway
A small minority of liquidity providers and professionals take most of the profit. On Polymarket, about 31% of wallets are net winners and the top 1% of profitable users take 76.5% of profits. On Kalshi, takers as a group have lost hundreds of millions to makers, and retail combo (parlay) buyers lose about 15% of stake to market makers plus Kalshi fees. Susquehanna and other institutions (Kalshi's own affiliate, Flutter/FanDuel, DraftKings-side professionals) dominate liquidity provision.

### Cited Findings
- Polymarket, 588M trades and $67B volume: the top 1% of users with positive PnL capture **76.5%** of profits (an earlier draft said 84%). Winners use limit orders and losers use market orders. Monthly performance is "modestly persistent". Insider trading is "unlikely to explain" the largest winners. — [Akey, Grégoire, Harvie & Martineau, SSRN 6443103 (rev. Jun 12, 2026)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103); [CEPR DP21615](https://cepr.org/publications/dp21615); [Slashdot summary](https://science.slashdot.org/story/26/05/11/0055243/most-polymarket-users-lose-money-while-top-1-claim-765-of-gains-study-finds)
- Washington Post analysis of the same data (Nov 2022 to Mar 29, 2026): **1,704,601** wallets lost money and **764,988** won (about 31% winners). [JOURNALISM; wallets ≠ people] — [Washington Post (2026)](https://www.washingtonpost.com/technology/interactive/2026/polymarket-online-gambling-winners-and-losers/)
- Polymarket wallets that habitually buy longshots trade far more Sports (22.2% vs 7.0% share). They have a similar maker share (13.2% vs 12.0%) and earn returns similar to others. — [arXiv 2609.12878, Table 22](https://arxiv.org/abs/2609.12878)
- Kalshi takers lost $584M to makers (Jul 2021 to mid-May 2026; Roosevelt Institute). Flutter reported $6M of prediction-market market-making revenue in Q2 2026 and expects about $50M in 2026. DraftKings' CEO said 80-90% of its prediction-market volume in betting states is institutional or professional. Kalshi has over 80% of weekly prediction-market volume. [JOURNALISM] — [American Prospect](https://prospect.org/2026/08/26/house-always-wins-kalshi-prediction-markets/)
- Kalshi combos (RFQ parlays), Jan 1 to Apr 30, 2026: retail risked about **$800M** and lost about **$117M** (about 15% of cost basis). At least **$35M** went to Kalshi as estimated fees and about $82M to makers. Institutional firms such as Susquehanna take the other side via RFQ. A Bloomberg measure put net combo losses at about $294M year-to-date (different period and method). [JOURNALISM] — [Sportico (paywalled; via search)](https://www.sportico.com/business/sports-betting/2026/kalshi-parlays-retail-bettor-losses-rfq-1234894471/); [predicted newsletter summary](https://predicted.beehiiv.com/p/do-parlays-pay-the-bills); [Casino.org](https://www.casino.org/news/kalshi-claims-it-isnt-a-sportsbook-but-has-made-35-million-in-parlay-fees-this-year-alone/)
- Reported but unverified: Kalshi's API gives combo makers user-identifying information that lets them decline consistent winners. [JOURNALISM, secondary] — [CasinoBeats](https://casinobeats.com/2026/05/21/polymarket-to-launch-parlays-under-combinatoric-athletic-outcome-contracts/)
- Citizens analyst Jordan Bender, using Juice Reel data: the bottom quartile of prediction-market users lost about **28c per $** in their first three months, versus about 11c at FanDuel/DraftKings. The bottom 10% lost about 44%, and the average prediction-market trader lost about 7% versus 1% for traditional bettors. Kalshi disputes these figures. [JOURNALISM] — [Bloomberg, Feb 4, 2026](https://bloomberg.com/news/articles/2026-02-04/kalshi-claims-extortion-then-recants-in-prediction-markets-gambling-feud); [GamblingNews summary](https://www.gamblingnews.com/news/kalshi-disputes-report-claiming-that-prediction-markets-users-lose-money-faster/)
- Susquehanna launched a dedicated event-contract desk and became Kalshi's first institutional market maker in April 2024. — [Bloomberg, Apr 3, 2024](https://www.bloomberg.com/news/articles/2024-04-03/susquehanna-starts-trading-desk-for-event-contracts-on-kalshi). Professional market makers receive reduced fees and higher position limits [VENDOR, weak] — [Tradermath](https://www.tradermath.org/articles/prediction-markets-trading-at-quant-firms). Kalshi's co-founder said its in-house trading arm is "not profitable" [headline only] — [Yahoo Finance](https://finance.yahoo.com/news/kalshi-co-founder-says-house-174507266.html).

### Inferences
- The structural winners are fast, well-capitalized liquidity providers and combo market makers, plus Kalshi itself via fees. Small retail traders who take liquidity, especially on longshots and parlays, are the funding source.
- Data showing that a minority of Polymarket wallets profit persistently, with winners skewed toward limit orders, implies a retail trader's best odds come from (i) posting limit orders rather than crossing the spread, (ii) avoiding longshots and combos, and (iii) specializing where an information edge exists.

### Gaps
- Kalshi has not published the share of profitable users. No Kalshi equivalent of the Polymarket wallet study exists because accounts are not public.
- No Susquehanna or Kalshi-affiliate spread or P&L data on sports specifically is public.
- No Polymarket leaderboard analysis restricted to sports wallets was found.

## Q9. Bias by sport/league, by liquidity, by contract type (moneyline/spread/total/props/parlays), home/popular-team bias, and Betfair/sportsbook comparison

### Takeaway
Bias evidence varies by product. Single-game moneylines are close to fair pre-game. Parlays are systematically overpriced and the overpricing grows with leg count. Futures show a strong FLB. Late-game distortion is largest in hockey. Bias is stronger in thin markets in some studies but not others. No Kalshi or Polymarket study of home-team or fan bias was found. Betting-exchange literature (tennis on Betfair-type exchanges) and soccer bookmaker studies also find FLB, while competitive markets such as Asian handicaps show little.

### Cited Findings
- Kalshi cross-game parlays, Apr 29 to May 13, 2026, 12,639 parlays whose legs were all 30-240 min from expiry: median overpricing ratio R = P_exec / ∏(leg prices):

| Legs | n | Median R |
|---|---|---|
| 2 | 5,846 | 0.991 |
| 3 | 3,111 | 0.995 |
| 4 | 1,523 | 0.999 |
| 5 | 928 | 1.005 |
| 6 | 584 | 1.013 |
| 7 | 371 | 1.037 |
| 8 | 140 | 1.066 |
| 9 | 67 | 1.105 |
| 10 | 57 | 1.223 |
| 11 | 12 | 1.305 |

  The parlay calibration curve sits "between two and ten percentage points below" the diagonal, consistent with an additive markup. — [Moshrefi, arXiv 2607.14430, Table I](https://arxiv.org/abs/2607.14430)
- Combo hold on Kalshi was about 15% (Jan to Apr 2026). Sportsbook parlay hold often exceeds 18%. — [Sportico via search](https://www.sportico.com/business/sports-betting/2026/kalshi-parlays-retail-bettor-losses-rfq-1234894471/)
- League differences in late-game miscalibration: α in the 5-min bucket is NHL 4.56 > MLB 2.05 > NBA 1.62. The paper notes literature documenting a *reverse* FLB in MLB and NHL moneylines and some US point-spread markets. — [Moshrefi](https://arxiv.org/abs/2607.14430)
- Polymarket NBA spread markets yielded disproportionately more arbitrage profit than moneylines (3 episodes each). Combinatorial moneyline-spread mispricings are the main in-game inefficiency. — [Cheng et al.](https://arxiv.org/abs/2605.00864)
- Liquidity: the Kalshi FLB slope is largest in the lowest-volume quintile (0.045 vs 0.032 at the top). Trade-size quintiles show no reduction. — [Bürgi et al.](https://www2.gwu.edu/~forcpgm/2026-001.pdf). Underreaction to live news is larger in illiquid Kalshi NBA markets. — [Angelini & De Angelis](https://arxiv.org/abs/2606.07811). The Sports trade-size effect is null. — [Le](https://arxiv.org/abs/2602.19520)
- Polymarket Sports shows no two-sided FLB at the tails (see Q1). — [arXiv 2609.12878](https://arxiv.org/abs/2609.12878)
- Tennis betting exchanges show FLB similar to bookmakers. It is stronger in matches between lower-ranked players, later rounds and high-profile tournaments, and it is linked to trading activity and uncertainty. — [Abinzano, Muga & Santamaría (UPNA repository)](https://academica-e.unavarra.es/handle/2454/18748); [Hidden power of trading activity: the FLB in tennis betting exchanges](https://academica-e.unavarra.es/xmlui/handle/2454/25857)
- Soccer: in 1X2 bookmaker markets (more than 80,000 European games), demand for longshots is less price-sensitive, so monopolistic bookmakers build in FLB. Competitive Asian-handicap markets show little. — [Hegarty & Whelan, Oxford Economic Papers 2026 (author page)](https://karlwhelan.com/sports-betting-how-bookmakers-set-odds/); [CEPR DP18144](https://cepr.org/publications/dp18144)
- Bookmaker-versus-exchange price disparity "increases rapidly as the implied probability of the event decreases" (Metsola 2010). — [Journal of Prediction Markets via IDEAS](https://ideas.repec.org/a/buc/jpredm/v4y2010i1p59-77.html)
- Volume concentration: since July 2024 sports have been about 80% of Kalshi volume and 39% of Polymarket volume (Pew Research, via search snippet; not verified at source). — [CEI blog citing Pew](https://cei.org/blog/sports-dominate-prediction-markets-but-dont-bet-on-that-being-the-whole-story/)
- Player props: Kalshi NFL anytime, first and 2+ TD props carry maker fees, while yardage props do not. MLB props have a 0.5 multiplier. — [Kalshi series API](https://api.elections.kalshi.com/trade-api/v2/series?category=Sports). Vendor claim that Kalshi MLB prop lines are sharper than Pinnacle's: [SmartStake](https://www.smartstake.app/learn/sharpest-sportsbooks-mlb-player-props).

### Inferences
- Product ranking for a retail buyer, from most to least fairly priced pre-game: single-game moneylines and spreads, then totals, then props (unmeasured), then long-dated futures (FLB), then 5+ leg parlays (markup). Retail can rarely be the seller of Kalshi combos, since RFQ quotes come from institutional makers, so the actionable lesson is avoidance.
- Late-game hockey and baseball favorites are the most promising documented in-game anomaly. It is unquantified in dollars.
- On Polymarket sports the longshot side is not systematically overpriced. "Fade the longshot" FLB strategies from Kalshi or sportsbooks do not transfer automatically.

### Gaps
- No Kalshi or Polymarket study of home-team, popular-team or fan bias was found. Sportsbook literature on this was not reviewed in this pass.
- No league-level FLB or return tables exist for NFL vs college vs NBA vs MLB vs soccer vs tennis on Kalshi or Polymarket. Moshrefi covers NBA/MLB/NHL calibration only.
- No study of returns on Kalshi spread, total or player-prop contracts was found.
- No published commission-adjusted Betfair returns by odds band for US sports were located.
