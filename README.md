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
| `web/template.html` | Calculator UI (trade, Sleeper league, rankings, backtest); `build_web.py` bundles it |
| `web/pwa/` | Manifest, service worker and icons for the installable app |
| `.github/workflows/refresh.yml` | Scheduled refit and GitHub Pages deploy |
| `output/` | Current rankings CSV, fitted formula coefficients, backtest summaries |

## Known limits

* No depth charts or injury reports yet. A backup QB who started while the starter was hurt can project too high (e.g. Joe Flacco, Justin Fields in 2024). Adding nflverse depth charts and injury designations is the next step.
* Players who haven't played a snap this season aren't projected (rookies before their debut, players on season-opening IR).
* Redraft only: no K/DST projections and no dynasty or keeper age curves. K, DEF and IDP slots in Sleeper leagues are ignored.
* Passing TDs are projected at 4 points. Leagues with 6-point passing TDs undervalue QBs a little (the app says so).
* The trade finder doesn't model the free agent a team could add with a roster spot freed by a 2-for-1.
