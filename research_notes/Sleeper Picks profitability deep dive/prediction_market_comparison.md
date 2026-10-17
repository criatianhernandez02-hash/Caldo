# Sleeper vs prediction markets (Kalshi, Polymarket) on the same picks — live snapshot 2026-10-17 (~21:45 UTC, week 6 slate)

Source: research/venue_compare.py in the Caldo repo (first-party pull of Sleeper's lines endpoint,
Kalshi's public market API and Polymarket's gamma + CLOB APIs). Novig and ProphetX expose no
public price feed reachable from this environment (Novig /v1/markets → 404; ProphetX → 502), so
they could not be compared with data.

## Coverage
- Sleeper TD/pass-TD picks (both sides): 244. Found on Kalshi: 234 (all with spreads ≤ 4¢).
  Found on Polymarket: 220, but only 6 with a spread ≤ 4¢ — most Polymarket player-TD books are thin.
- Polymarket lists ~254 "Anytime Touchdown", ~202 "2+ Touchdowns" and passing-TD O/U markets this
  weekend. Depth is real on popular players (e.g. Woody Marks: 8,137 shares bid at 40¢ / 6,139 offered
  at 43¢; Derrick Henry: 4,100 bid at 57¢ / 4,000 offered at 60¢) and near-empty on others
  (Jalen Coker: 2¢ bid / 26¢ ask).

## Payout per $1 and expected value on the same pick (220 picks priced on all three)
Fair probability = Kalshi midpoint (plus Polymarket midpoint when its spread ≤ 4¢). Exchange payouts
assume buying now at the ask and paying the taker fee (Kalshi 0.07·P·(1−P) per contract, rounded up
per order — negligible on a $20 order; Polymarket sports 0.05·P·(1−P) per the venue research).

| Venue | Avg payout per $1 | Avg EV per $1 | Best price on | Picks with EV > 0 |
|---|---|---|---|---|
| Sleeper | 1.947 | −13.1% | 0% | 0 |
| Kalshi (taker) | 2.167 | −4.5% | 66% | 0 |
| Polymarket (taker) | 1.906 | −19.2% | 34% | 19 (see below) |

By side: "More" — Sleeper −15.5%, Kalshi −5.4%, Polymarket −4.2%; "Less" — Sleeper −10.6%, Kalshi −3.6%,
Polymarket −34.3% (buying "No" into thin books at 1 − a 1–2¢ bid). By fair probability: 20–35%:
Sleeper −19.9% / Kalshi −6.5%; 35–50%: −12.9% / −5.1%; 50–65%: −10.2% / −3.7%; 65%+: −9.6% / −2.6%.

The 19 "positive-EV" Polymarket asks were all 5-share orders (about $1) resting 1–2¢ below Kalshi;
the next level of the book was at or above Kalshi's price, so nothing was +EV at a $20 stake.

## Kalshi cost to buy a TD contract (corrected for per-order fee rounding; wk-6 quotes, 354 markets)
| Fair probability | Spread cost | Fee | Total |
|---|---|---|---|
| < 20% | 7.3% | 6.2% | 12.7% |
| 20–35% | 2.1% | 5.1% | 6.8% |
| 35–50% | 1.3% | 4.1% | 5.1% |
| 50–65% | 0.9% | 2.9% | 3.75% |
| > 65% | 1.7% | 1.4% | 3.1% |
(Supersedes the per-contract-rounded table in own_quant_analysis.md §6, which overstated fees on
cheap contracts, e.g. 18.5% for < 20%.)
Posting a limit order at the bid instead avoids the spread and (on most Kalshi sports series) the
fee, but only fills if someone sells to you — typically when the price is moving against you.

## Parlays: the probability-play slips on Sleeper vs an estimated Kalshi Combo
Same legs (this week's most likely "More" picks: McCaffrey, J. Taylor, Bijan Robinson TD; Cam Ward,
Tanner McKee, Jalon Daniels 1+ pass TD; Kyren Williams TD; Jordan Love 2+ pass TD). Kalshi combo
quotes are request-for-quote and were not observable, so the combo price is modeled as
product of fair probabilities × (1 + markup)^legs, markup 0% or 3% per leg (range from the
modeling research), plus the taker fee on the combo price.

| Legs | Win chance | Sleeper payout | Sleeper EV per $20 | Kalshi combo payout (0% / 3% markup) | Kalshi EV per $20 (0% / 3%) |
|---|---|---|---|---|---|
| 2 | 49.0% | 1.69x | −$3.44 | 1.97x / 1.86x | −$0.69 / −$1.76 |
| 3 | 34.1% | 2.18x | −$5.15 | 2.81x / 2.57x | −$0.88 / −$2.47 |
| 5 | 15.4% | 3.88x | −$8.05 | 6.13x / 5.30x | −$1.12 / −$3.69 |
| 8 | 4.1% | 10.50x | −$11.47 | 23.05x / 18.21x | −$1.26 / −$5.20 |

Weekly 3/5/8 card: Sleeper ≈ −$24.7/week (≈ −$419 over 17 weeks); Kalshi combos ≈ −$3.3 to −$11.4/week
(≈ −$55 to −$193 per season). Cheaper, not profitable: without an edge over the market, every venue
loses at the rate of its fee/margin. Kalshi sports contracts are restricted or contested in some
states (see venue_landscape.md), and Kalshi combos' real RFQ markups are unmeasured.
