# Caldo: NFL touchdown picks model for Sleeper

A small model that projects each week's **anytime touchdowns** (RB / WR / TE) and **QB passing
touchdowns**, then builds a weekly parlay card: a 3-leg "anchor", a 5-leg "core" and an 8-leg
"longshot", $20 each by default.

It uses free [nflverse](https://github.com/nflverse) data (weekly player stats plus the schedule
with Vegas spreads and totals). You don't need an API key.

## Weekly routine

```bash
pip install -r requirements.txt

# 1. Projections + parlay card for the next unplayed week
python -m tdmodel week

# 2. Drop anyone ruled out / questionable you don't trust
python -m tdmodel week --exclude "Christian McCaffrey,Puka Nacua"

# 3. Best: pull Sleeper's live lines + payout multipliers and drop injured players
python -m tdmodel week --sleeper
python -m tdmodel week --sleeper --overs-only --min-edge 0.05

# Probability play: the most likely "More" picks, ignoring value
python -m tdmodel week --sleeper --kalshi --probability-play

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

* each leg's win % becomes a blend: 50% model, 50% Kalshi (`--kalshi-weight` changes it)
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

Caveats: this endpoint is undocumented and may change or be blocked at any time, and pulling data
from it may go against Sleeper's terms of service. The card's slip payout is the product of the
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
| **Player share** | The player's share of team rush / receiving TDs, anchored to carry share and target share so one fluky game doesn't dominate | Same |
| **Matchup** | Where the defense gives up TDs (to RBs on the ground, to WRs, to TEs) compared with league average | Same, heavily shrunk |
| **Calibration** | Small per-position correction fitted on backtests (TEs and QB pass TDs ran low; RBs slightly high) | 2024–25 backtests |

For QBs, the tool uses the starter listed in the schedule. Small samples, like early in the
season, are pulled toward league average.

## Does it work? (walk-forward backtests, weeks 3–18)

Each week is predicted using only data from before that week, plus the closing Vegas lines.

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

Bet only what you're fine losing. 1-800-GAMBLER if it stops being fun.

## Development

```bash
python -m pytest -q                         # unit tests (synthetic data, no network)
python -m tdmodel backtest --season 2025    # full walk-forward backtest
```
