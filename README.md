# Caldo

A fantasy football ranking formula and trade calculator, in the spirit of RotoBot's trade tool. It's fit on NFL data from 2012 onward and backtested walk-forward over the 2016–2025 seasons.

* **Ranks players** by projected rest-of-season (ROS) points. The projection accounts for recent form, usage, red-zone touches, Vegas implied totals, the defense each player faces, home/away, dome games, byes and the chance of missing games.
* **Tiers** each position with optimal 1-D clustering (Jenks natural breaks).
* **Values trades** as ROS points above a waiver-wire replacement. Extra players you receive in a package are discounted by weights measured in simulated leagues. A roster mode rebuilds your best weekly lineup before and after the trade.

## Sleeper integration

Open the **Sleeper league** tab and enter your Sleeper username. The app reads your leagues through Sleeper's public, read-only API, so it needs no password or token. Then:

* **Your league's rules.** Any reception value and per-position catch bonuses (TE premium) are applied exactly: `std + (rec + bonus) × (PPR − std)`, because the gap between the PPR and standard projections is projected receptions. Starting slots are read from the league (QB, RB, WR, TE, FLEX, W/R, W/T and superflex).
* **Free-agent replacement level.** A player's value is measured against the best player nobody in *your* league rosters.
* **Power rankings.** Every team's projected starting-lineup points for the rest of the season.
* **Both sides of a trade.** Your lineup change and your partner's, with a "likely to accept / decline" read.
* **Trade finder tab.** Searches 1-for-1, 2-for-1, 1-for-2 and 2-for-2 deals with every team for trades that raise your starting lineup *and* have a fair chance of a yes. Your gain uses the model; their odds weigh (a) how much the deal changes their starting lineup and (b) how fair it looks by this season's box scores (points per game so far), which is how most managers size up an offer. It labels each deal Likely yes / Worth a try / Long shot. You can filter by partner, position wanted and deal size, mark players to keep, and see Sell high / Buy low lists where box scores and projections disagree. The odds are a heuristic: `sigmoid(0.12 × their lineup change + 0.04 × box-score value gap)`, not yet calibrated on real accepted trades.
* **Rankings.** Shows who rosters each player, has a free-agents filter, and shows Sleeper injury tags.

Sleeper player IDs are mapped to nflverse IDs through the DynastyProcess crosswalk, with name matching as a fallback (474 of 475 projected players map).

## Your own app

`python scripts/build_web.py` writes two builds:

* `web/index.html` is a single file. It works offline and in the claude.ai artifact. Sandboxed pages there can't call outside sites, so live Sleeper sync needs the hosted app. Alternatively, bundle a league snapshot with `build_rankings.py --sleeper-user <name>`.
* `site/` is an installable web app with a manifest, offline cache and home-screen icon. Live Sleeper sync works from any normal web host.

`.github/workflows/refresh.yml` refits the model on the latest NFL data every Tuesday and Friday during the season and deploys `site/` to GitHub Pages. To turn it on, push the repo, set **Settings → Pages → Source** to **GitHub Actions**, and run the workflow once by hand. On a phone, open the Pages URL and choose **Add to Home Screen**.

## Model v2: injuries, roles, and a blend with the market

Comparing against ESPN, Sleeper and FantasyPros exposed one big gap. The model only saw missed games, so it couldn't tell an injured starter who'll return (A.J. Brown, IR-designated to return) from a backup who lost his job. It ranked Brown WR63 while the expert consensus had him WR23. v2 fixes that and adds three things:

* **Roster status and injury reports** (nflverse weekly rosters + injury reports, 2011–2026). Each week a player is tagged IR, IR-designated to return, PUP, practice squad, cut, or on the 53. He also gets that week's Out/Doubtful/Questionable designation and practice participation. These feed the availability model, and injured rostered players now stay in the player pool while they're out.
* **Role.** Depth-chart rank (from the last game played, so injured players aren't judged by where they sit on the chart while hurt), snap share, and whether he changed teams.
* **Next-game-only tags.** "Questionable" and "first game back" only affect the next game, not the whole rest of the season.
* **A blend with Sleeper's projections** (the Rotowire numbers in the Sleeper app). Their weekly projections are available back to 2018 exactly as they stood before kickoff, so the blend is fit and tested walk-forward.

**Rest-of-season backtest, 2016–2025 (walk-forward):**

| | Original | v2 without injury status | **v2** | Season avg × games left |
|---|---|---|---|---|
| QB rank correlation | 0.463 | 0.563 | **0.598** | 0.324 |
| RB | 0.569 | 0.614 | **0.652** | 0.437 |
| WR | 0.552 | 0.595 | **0.626** | 0.360 |
| TE | 0.495 | 0.537 | **0.576** | 0.372 |
| Right side of a 1-for-1 trade | 70.0% | 71.9% | **73.2%** | 63.5% |

**Head-to-head with Sleeper, weekly, test seasons 2020–2025** (same player pool; blend weights learned only from earlier seasons):

| Avg miss / rank correlation | QB | RB | WR | TE |
|---|---|---|---|---|
| Our model | 6.19 / 0.332 | 4.51 / 0.376 | 4.69 / 0.321 | 3.67 / 0.246 |
| Sleeper | 6.05 / 0.328 | 4.37 / 0.449 | 4.65 / 0.347 | 3.67 / 0.286 |
| **Blend** | **5.98 / 0.345** | **4.33 / 0.451** | **4.60 / 0.353** | **3.59 / 0.292** |

**Blind spots** (`output/compare/blind_spots.csv`):
* **Sleeper beats us** on news-driven situations: backups thrust into a starting role, first games back from injury, and rookies at RB/WR.
* **We beat Sleeper** on QBs (they run about 3 points high) and on players listed Questionable, whom they overproject.

Sleeper's projections are also an availability signal. When Sleeper projected an established player for a game, he played 99% of the time; when it left him out, 16%.

**What the app uses:**
* **Points per game when he plays:** 20–50% our model and the rest Sleeper, depending on position.
* **Availability for the next game:** Sleeper's signal.
* **Availability for later weeks:** an average of ours and theirs.

**Agreement with the experts now:** the rest-of-season rank correlation with the FantasyPros consensus rose from 0.77–0.91 to 0.89–0.93 by position. That's about the same agreement ESPN has with FantasyPros (0.78–0.95). A.J. Brown went from WR63 to WR23, matching the consensus.

## Trade odds, tested on real trades

The odds of a yes started as a guess. They're now fit on **1,645 completed player-for-player trades from 434 public Sleeper redraft leagues (2022–2025)**, collected with `scripts/collect_trades.py`.

For each trade, `scripts/test_trades.py`:
1. Rebuilds both rosters at that moment, from the draft plus every earlier move.
2. Values every player with the walk-forward backtest snapshot taken before the trade.
3. Compares the trade with 25 random trades the same two teams could have made that week, with the same number of players.

Sleeper only exposes accepted trades, so the test asks: **does a deal look like the trades real managers accept?**

| Average rank of the real trade among its random alternatives | |
|---|---|
| Original odds (lineup change + "looks like a win for them by box score") | 76.1% |
| Lineup change only | 75.4% |
| Box-score fairness only | 64.3% |
| Projected-value fairness only | 65.1% |
| **New odds, refit on real trades (each season scored by a model fit on the other three)** | **77.5%** |

**What real trades look like:**
* **Lineup change matters most.** The side that gives up more loses about 12 projected lineup points at the median, vs. 38 in random trades.
* **Values stay close.** The median box-score gap is 21 points (37 in random trades), and the median projected-value gap is 17 (29).
* **"Looks like a win for them by box score" doesn't make a trade more likely.** The original formula assumed it did, so that term was dropped.
* Only 9% of real trades help both projected lineups.

**App labels are anchored on real trades:**
* **Likely yes:** at least as good as the median accepted trade (above 81% of random alternatives).
* **Worth a try:** within the range of 80% of accepted trades.
* **Long shot:** below that.

**Who won:** on 1,410 real trades where one lineup ended at least 10 points better, the model's projected lineup winner was right **56.4%** of the time; points per game so far was right 49.0%. When the two disagreed, the model was right 55% of the time. The edge is modest because most real trades are close calls.

## The formula

```
Game projection = Player rating × Game multiplier

Player rating   = ridge regression per position on
                  recent form (EWMA, half-life 3 and 10 games), season average,
                  last season, usage EWMAs (targets, carries, receptions,
                  target share, air-yard share, pass attempts/yards/TDs),
                  red-zone & goal-line touches, age, draft capital, missed games

Game multiplier = exp(b0 + a·ln(implied team total / league avg)
                       + b·ln(defense factor) + c·home + d·dome + e·spread/7)

Defense factor  = points a defense allowed to the position ÷ what those same players
                  were rated to score (opponent-adjusted), with a decay of 8 games
                  and shrinkage toward 1.0

ROS points      = Σ over remaining games of P(plays) × rating × multiplier
                  P(plays) is a logistic model on missed-game streak, recent
                  missed rate, player quality and weeks ahead

Trade value     = ROS points − replacement-level ROS points at the position
```

Future weeks have no Vegas lines yet, so their implied totals come from a market-based team rating. This is a ridge fit of past implied totals on offense, defense and home terms.

### Fitted game multipliers (PPR, trained 2012–2025)

| Effect on a player's points          | QB    | RB    | WR    | TE    |
|--------------------------------------|-------|-------|-------|-------|
| Team implied total +10%              | +3.1% | +3.3% | +2.6% | +4.1% |
| Defense allows 20% more to position  | +6.4% | +5.6% | +4.1% | +4.6% |
| Home vs. away                        | +5.5% | +3.5% | +1.4% | −1.0% |
| Dome / closed roof                   | +4.2% | +2.0% | +6.4% | +0.1% |

## Backtest (walk-forward, 2016–2025, PPR)

Each season is projected only with models fit on the seasons before it. ROS snapshots are taken at weeks 3, 5, 7, 9 and 11, and actual points run from the snapshot week through week 17. Missed games count as 0, the same way they hurt a fantasy roster.

**Rest-of-season ranking accuracy** (Spearman rank correlation; pairwise = share of player pairs ordered correctly)

| Position | Formula ρ | Naive ρ* | Formula pairwise | Naive pairwise | Formula MAE | Naive MAE |
|---|---|---|---|---|---|---|
| QB | **0.463** | 0.329 | **66.7%** | 61.7% | **48.0** | 63.4 |
| RB | **0.569** | 0.444 | **70.7%** | 65.6% | **39.4** | 53.1 |
| WR | **0.552** | 0.377 | **70.1%** | 63.1% | **36.6** | 54.3 |
| TE | **0.495** | 0.375 | **68.0%** | 63.1% | **30.6** | 45.8 |
| 1-for-1 trades, any positions | | | **70.0%** | 63.5% | | |

\*Naive = this season's points per game × games left (last season's average before week 1). That's how most people rank players.

**Weekly projections** (rank correlation within position-week)

| Position | Formula | LightGBM (black box, same inputs) | Season avg |
|---|---|---|---|
| QB | **0.344** | 0.338 | 0.254 |
| RB | **0.426** | 0.417 | 0.364 |
| WR | **0.349** | 0.348 | 0.269 |
| TE | **0.329** | 0.321 | 0.236 |

The transparent formula matches or beats LightGBM, so very little accuracy is lost by keeping it interpretable.

### What the ablations say

Each ingredient was removed, then all 10 seasons were refit (`output/backtest/*_summary_ppr.csv`).

* **Usage and red-zone touches matter most for ROS.** Removing them drops ROS rank correlation by 0.013–0.024 at RB, WR and TE.
* **Game context (Vegas, matchup, home, dome) matters for weekly start/sit**, especially at QB (0.344 → 0.306 without it). It barely moves rest-of-season rankings. Over 8–12 games, schedules even out and the projectable part of strength of schedule is about ±5%.
* **Past touchdowns are a trap.** Once red-zone usage is in the model, last-few-games TDs get a *negative* weight (TD regression to the mean). Projected TDs come from red-zone and goal-line opportunity.

### Multi-player trades

We simulated 40 leagues (12 teams, drafted from each season's week-7 projections) and 10,000 random trades. Then we regressed each team's change in starting-lineup points on the pieces exchanged:

* Pieces you **receive** count at **100% / 71% / 48%** (best, second, third), because extra bodies often sit on your bench.
* Pieces you **send away** count at about 100% each, because a waiver pickup fills the open spot.
* Generic weights explain ~56% of a trade's lineup impact. The rest depends on the roster you already have, so the roster mode in the calculator is the better read for your own team.

## Usage

```bash
pip install -r requirements.txt
python scripts/build_rankings.py --refresh   # download data, fit, project current season
python scripts/build_rankings.py --sleeper-user <name>   # also bundle a Sleeper league snapshot
python scripts/run_backtest.py               # 10-season backtest + ablations (~25 min)
python scripts/run_backtest.py --quick       # full model only
python scripts/calibrate_trades.py           # package weights (needs backtest output)
python scripts/fetch_external.py             # Sleeper weekly projections 2018-now (for the blend)
python scripts/quick_backtest.py --tag v4    # walk-forward backtest of the current model (~25 min)
python scripts/fit_blend.py --tag v4         # head-to-head vs Sleeper, blind spots, blend weights
python scripts/compare_models.py             # live agreement with Sleeper, ESPN, FantasyPros
python scripts/collect_trades.py             # real trades from public Sleeper redraft leagues (~40 min)
python scripts/test_trades.py                # test + refit the trade odds -> output/trade_odds.json
python scripts/build_web.py                  # bundle web/index.html
```

Data comes from [nflverse](https://github.com/nflverse): weekly player stats, play-by-play (for red-zone usage), schedules with closing lines, and player bios. It downloads into `data/` (git-ignored).

## Layout

| Path | What it does |
|---|---|
| `caldo/data.py` | Downloads data; builds the player × team-game panel (missed games included) |
| `caldo/features.py` | Pre-game features (each row uses only earlier games) |
| `caldo/model.py` | Player rating, defense factor, game multiplier, availability, TD model |
| `caldo/ros.py` | Market-implied team totals for future weeks; rest-of-season projection |
| `caldo/backtest.py` | Walk-forward backtest, baselines, ablations, LightGBM benchmark |
| `caldo/tiers.py` | Jenks tiers |
| `caldo/trade.py` | VORP, lineup math, league simulation, package weights |
| `caldo/sleeper.py` | Sleeper API client, player-ID mapping, league snapshots |
| `caldo/status.py` | Weekly roster status, injury reports, depth charts, snap counts |
| `caldo/external.py` | Head-to-head scoring vs. Sleeper, blind spots, the blend |
| `web/template.html` | Calculator UI (trade, Sleeper league, rankings, backtest); `build_web.py` bundles it |
| `web/pwa/` | Manifest, service worker and icons for the installable app |
| `.github/workflows/refresh.yml` | Scheduled refit and GitHub Pages deploy |
| `output/` | Current rankings CSV, fitted formula coefficients, backtest summaries |

## Known limits

* Injury severity still isn't modeled. The model knows a player is Out or on IR, but not whether it's a one-week hamstring or a broken leg. The Sleeper blend covers part of this, but a star listed Out this week (e.g. Lamar Jackson) can still project below the consensus.
* The blend's availability signal is validated for the next game only. For later weeks it averages our estimate with Sleeper's current projections, which can't be backtested because only final pre-game projections are archived.
* Redraft only: no K/DST projections and no dynasty or keeper age curves. K, DEF and IDP slots in Sleeper leagues are ignored.
* Passing TDs are projected at 4 points. Leagues with 6-point passing TDs undervalue QBs a little (the app says so).
* The trade finder doesn't model the free agent a team could add with a roster spot freed by a 2-for-1.
* The trade odds are fit on trades that happened. Sleeper doesn't expose rejected offers, so they measure how much an offer looks like an accepted trade, not an exact chance of a yes. Low-stakes bench swaps look like typical trades and can score "Likely yes" even when neither side has much reason to bother.
