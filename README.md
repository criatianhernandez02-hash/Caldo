# Caldo: NFL touchdown picks model for Sleeper

A small model that projects each week's **anytime touchdowns** (RB / WR / TE) and **QB passing
touchdowns**, then builds a weekly parlay card: a 3-leg "anchor", a 5-leg "core" and an 8-leg
"longshot", $20 each by default.

It uses free [nflverse](https://github.com/nflverse) data (weekly player stats plus the schedule
with Vegas spreads and totals) and [ffopportunity](https://github.com/ffverse/ffopportunity)
expected-touchdown data. You don't need an API key.

## Read this first: what the October 2026 deep dive found

Full report: [`reports/Sleeper Picks profitability deep dive.md`](reports/Sleeper%20Picks%20profitability%20deep%20dive.md).
Reproduce it with the scripts in [`research/`](research/README.md).

* **Sleeper keeps about 12-14% of every TD leg, and it compounds.** Its multipliers track Kalshi's
  prices almost exactly (correlation 0.998) plus a fixed markup. On 2026-10-17, none of 214
  pickable TD sides were positive value against the market. Expected return per $20 slip: about
  -17% for 2 legs, -26% for 3, -42% for 5, and -58% for 8.
* **No model we built beats the market.** Kalshi's pre-kickoff price was at least as accurate as the
  best model (2026, 699 player-games), and no betting rule showed a real profit in the replay.
* **The only clearly +EV picks were Sleeper's promo lines** (discounted "free pick" lines and some
  boosts) and the sign-up deposit match. `--sleeper` now lists the promo lines.
* **The 3/5/8 probability-play plan** is expected to lose about $25 a week ($427 over a 17-week
  season) and finishes a season ahead only about 10% of the time.

## Kalshi / Polymarket formula study (October 2026)

Full report: [`reports/Kalshi sports betting formula.md`](reports/Kalshi%20sports%20betting%20formula.md).
It covers my own team-win and player-yards formulas, plus backtests on real Kalshi and Polymarket
prices with fees.

* **No formula or rule beat Kalshi after fees.** Kalshi, Polymarket and the sportsbook close are
  equally accurate on NFL games; the formulas trail them. Every pre-game, resting-bid and late-game
  rule that looked good in one season lost in the other.
* **The cheapest bets:** NO on long-shot player rungs (about −1.5%) and game sides at 90¢ or more
  (about −0.6%). Contracts under 20¢ and parlays/combos lose the most.
* **One unproven lead:** NO on a player's middle rung when the formula says he goes under.
  It returned +5.0% ± 2.7% over 1,111 bets, positive in 2025 and in both halves of 2026.
  Paper-trade it with `python research/props_scan.py`.

## Weekly routine

```bash
pip install -r requirements.txt

# 1. Projections + parlay card for the next unplayed week
python -m tdmodel week

# 2. Drop anyone ruled out / questionable you don't trust
python -m tdmodel week --exclude "Christian McCaffrey,Puka Nacua"

# 3. Pull Sleeper's live lines, promo lines and multipliers, and the Kalshi market as a check
python -m tdmodel week --sleeper --kalshi
python -m tdmodel week --sleeper --overs-only --min-edge 0.05

# Probability play: the most likely "More" picks, ignoring value
python -m tdmodel week --sleeper --kalshi --probability-play

# 4. Keep score: log the card, then grade it after the games
python -m tdmodel week --sleeper --kalshi --probability-play --log bets.csv
python -m tdmodel grade --log bets.csv

# (or type the lines in yourself)
python -m tdmodel week --lines my_lines.csv
```

### `--kalshi`

```bash
python -m tdmodel week --sleeper --kalshi
```

Pulls [Kalshi](https://kalshi.com) prediction-market prices for the same props from Kalshi's public
market-data API, which doesn't need an account. `Player: 1+ touchdowns` is used for anytime TD, and
`2+` / `3+ passing touchdowns` for pass TDs over 1.5 and 2.5. The Kalshi probability is the midpoint
of the bid and ask, and markets with a bid/ask spread wider than 15¢ are ignored. Then:

* each leg's win % becomes a blend: 25% model, 75% Kalshi (`--kalshi-weight` changes it). The
  backtest found the market at least as accurate as the model, so it gets most of the weight.
* the value board adds `kalshi_x`: what the same pick pays per $1 bought on Kalshi right now (at the
  ask, after Kalshi's 7% × P × (1−P) taker fee), next to Sleeper's multiplier
* each slip shows a **market-only view**: its win chance and expected profit using Kalshi's prices
  alone, i.e. the house edge on that slip
* it prints the **biggest model vs Kalshi disagreements**. These usually mean the model is missing
  news, so check them before betting.
* the value board shows model %, Kalshi %, and the blend side by side

In the first live comparison (2026 week 3), Kalshi disagreed with most of the model's apparent
Sleeper edges. Once blended, only a handful of legs were at break-even or better. Treat that as the
realistic view: Sleeper's prices are close to fair minus its margin, and big edges are rare.

### `--sleeper`

Pulls every NFL **Anytime TD** and **Pass TDs** pick currently on Sleeper, with the payout multiplier
for each side, from the same endpoint the Sleeper app uses. It also reads Sleeper's player database
(cached for 24 hours), then:

* drops players listed Out / Doubtful / IR, and marks Questionable players with `(Q)`
* prints a **value board**: the model's win % vs. the % Sleeper's multiplier needs to break even
  (`1 / multiplier`), sorted by edge
* builds the card only from legs with edge ≥ `--min-edge` (default 0). `--allow-negative` turns
  that filter off.

QB anytime-TD picks (QB rushing TDs) are skipped. The model hasn't been backtested on them and
underrates goal-line QBs.

It also lists Sleeper's **promo lines** (boosted multipliers and discounted "free pick" lines) with
an expected-value estimate from the de-vigged regular line. These were the only positive-value picks
the research found. Account-specific promos don't appear in the public feed, so check the app too.

**Terms of Service:** Sleeper's Terms (updated Oct 6, 2026, §11) prohibit automated data access,
scrapers and bots, and §5.20 lets Sleeper restrict accounts and claw back prizes for using them.
`--sleeper` reads Sleeper's public endpoints automatically, so it falls under that. Use it at your
own risk, or type the lines in yourself with `--lines`.

Caveats: this endpoint is undocumented and may change or be blocked at any time. The card's slip payout is the product of the
leg multipliers. That's an assumption, so check the payout Sleeper shows before you enter, because
Sleeper may cap big payouts. A big "edge" often means the model is missing news (an injury or a
role change) rather than Sleeper being wrong, so look into those before you trust them.

Useful flags: `--overs-only` (no QB "less" legs), `--sizes 3,5,7`, `--stake 20`,
`--overlap` (let one player appear in several slips), `--out out/` (save CSVs),
`--season 2026 --week 4`.

### Lines file (`lines_example.csv`)

```
player,market,line,side,multiplier
Jahmyr Gibbs,anytime_td,0.5,more,1.45
Jared Goff,pass_tds,1.5,more,1.75
```

`market` is `anytime_td` (Rush+Rec TDs) or `pass_tds`, and `side` is `more` or `less`. The
`multiplier` column is optional: it's the payout Sleeper shows for that pick. When it's filled in,
the card shows the actual payout and the model's expected profit. The example numbers are made up,
so copy yours from the app.

## How the model works

For each player it estimates **expected touchdowns (λ)**. It treats TDs as a Poisson count, so
`P(anytime TD) = 1 − e^(−λ)` and `P(QB over 1.5) = 1 − P(0) − P(1)`.

| Piece | What it captures | Source |
|---|---|---|
| **Game environment** | High-total games have more TDs to go around. Team implied points come from `(total ± spread) / 2` and are converted to expected offensive TDs. | Vegas lines |
| **Team split** | How the offense scores: rushing vs passing TDs | Last season plus this season, recency-weighted |
| **Player share** | The player's share of team rush / receiving TDs, half from actual TDs and half from *expected* TDs (ffopportunity, based on where on the field his carries and targets happen), anchored to carry and target share | Same |
| **Matchup** | Where the defense gives up TDs (to RBs on the ground, to WRs, to TEs) compared with league average | Same, heavily shrunk |
| **Calibration** | Small per-position correction fitted on backtests (TEs and QB pass TDs ran low; RBs slightly high) | 2024–25 backtests |

For QBs, the tool uses the starter listed in the schedule. Small samples, like early in the
season, are pulled toward league average.

## Does it work? (walk-forward backtests, weeks 3–18)

Each week is predicted using only data from before that week, plus the closing Vegas lines. These
numbers are for the original actual-TD version. The current default (50/50 actual + expected TDs)
scores 0.1875 anytime-TD and 0.2391 QB over 1.5 in 2025. [`research/compare_models.py`](research/compare_models.py)
compares it with logistic regression, gradient boosting and simple baselines.

| | 2024 | 2025 |
|---|---|---|
| Anytime TD Brier (lower is better): model / base rate | 0.190 / 0.204 | 0.188 / 0.201 |
| QB over 1.5 Brier: model / base rate | 0.246 / 0.250 | 0.240 / 0.248 |
| Top 10 anytime TD picks per week: predicted / actual hit rate | 53% / 58% | 55% / 58% |
| Same model **without Vegas lines** (anytime TD Brier) | 0.192 | 0.190 |
| Same model **without the defensive matchup** (anytime TD Brier) | 0.190 | 0.188 |

What this shows:

* **Game totals matter.** Removing the Vegas lines makes every projection worse, most of all for
  QB passing TDs, where the model without them is no better than guessing the league average.
* **"This defense gives up a lot of rushing TDs" adds almost nothing on its own.** Vegas already
  prices defensive quality into the total and spread. The matchup term is kept at 25% weight as
  a tie-breaker, and the tables still show each defense's rank against the position for context.
* The settings were tuned on 2024 and checked on 2025. The calibration factors use both seasons,
  so the 2025 numbers are slightly optimistic.

### Parlay reality check (32 backtested weeks, same card-building rules)

| Slip | Model's average win chance | Actually hit |
|---|---|---|
| 3-leg anchor | ~34% | 9 / 32 (28%) |
| 5-leg core | ~11% | 3 / 32 (9%) |
| 8-leg longshot | ~1% | 1 / 32 (3%) |

There is no "sure hit." Even the model's best legs land around 60–70%, and three of them together
land about a third of the time. A slip is only worth playing when Sleeper's payout is **higher than
the "fair payout"** the card prints.

## Limitations

* **Injuries and inactives are not in the data.** Check the injury report and use `--exclude`.
  Role changes (a new starter at RB, a trade) show up only after a game or two.
* The schedule's starting QB and Vegas lines update over the week. Run it again on game day
  (`--refresh` forces a fresh download).
* Win chances assume the legs are independent. The builder allows only one leg per team to limit
  correlation, but it isn't perfect.
* Sleeper's leg availability and payouts change. The lines file is how you make the card match
  what you can actually play.
* Sleeper Picks is not offered for real money in about 20 states (including AZ, CO, MD, MI, NJ, NY,
  OH and PA as of Aug 2026), and Kalshi sports contracts are restricted in some states.

Bet only what you're fine losing. 1-800-GAMBLER if it stops being fun.

## Development

```bash
python -m pytest -q                         # unit tests (synthetic data, no network)
python -m tdmodel backtest --season 2025    # full walk-forward backtest
```
