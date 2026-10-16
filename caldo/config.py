"""Shared settings: paths, scoring formats, league shape, data sources."""
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = DATA_DIR / "cache"
OUT_DIR = ROOT / "output"

FIRST_SEASON = 2011          # first season loaded (feature history only)
BACKTEST_SEASONS = list(range(2016, 2026))   # 10 seasons, walk-forward
FANTASY_LAST_WEEK = 17       # fantasy playoffs end in week 17
POSITIONS = ["QB", "RB", "WR", "TE"]

NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
SOURCES = {
    "stats": NFLVERSE + "/stats_player/stats_player_week_{season}.csv",
    "pbp": NFLVERSE + "/pbp/play_by_play_{season}.parquet",
    "players": NFLVERSE + "/players/players.csv",
    "games": "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
}

# Points per reception by scoring format. Everything else is standard
# (0.04/pass yd, 4/pass TD, -2/INT, 0.1/rush+rec yd, 6/TD, -2/fumble lost).
SCORING = {"ppr": 1.0, "half": 0.5, "std": 0.0}


@dataclass
class League:
    teams: int = 12
    # starters per team at each position; FLEX accepts RB/WR/TE
    starters: dict = field(default_factory=lambda: {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1})
    bench: int = 6
    scoring: str = "ppr"

    def replacement_rank(self) -> dict:
        """Rank of the first replacement-level player at each position.

        FLEX spots are split across RB/WR/TE in proportion to how often each
        position fills a flex in practice (roughly 45% RB, 50% WR, 5% TE).
        """
        flex = self.starters.get("FLEX", 0) * self.teams
        share = {"RB": 0.45, "WR": 0.50, "TE": 0.05}
        out = {}
        for pos in POSITIONS:
            n = self.starters.get(pos, 0) * self.teams + share.get(pos, 0) * flex
            out[pos] = int(round(n)) + 1
        return out
