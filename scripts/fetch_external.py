"""Download outside projections for comparison and blending.

Sleeper's projection endpoint (Rotowire numbers, the ones shown in the Sleeper
app) keeps every week's final pre-game projection back to 2018, so it can be
scored against what happened. Saved compactly to data/raw/ext/sleeper_proj.parquet.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from caldo.config import RAW_DIR

URL = "https://api.sleeper.com/projections/nfl/{season}/{week}?season_type=regular&position[]=QB&position[]=RB&position[]=WR&position[]=TE"


def fetch(season, week):
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL.format(season=season, week=week), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"could not fetch {season} week {week}")


def main(first=2018, last=2026, last_week=18):
    out = RAW_DIR / "ext" / "sleeper_proj.parquet"
    old = pd.read_parquet(out) if out.exists() else pd.DataFrame()
    rows = []
    for season in range(first, last + 1):
        for week in range(1, last_week + 1):
            if not old.empty and season < last and ((old.season == season) & (old.week == week)).any():
                continue
            for x in fetch(season, week):
                st = x.get("stats") or {}
                if st.get("pts_ppr") is None:
                    continue
                rows.append({"season": season, "week": week, "sid": x["player_id"], "pos": x["player"].get("position"),
                             "name": f"{x['player'].get('first_name', '')} {x['player'].get('last_name', '')}".strip(),
                             "team": x.get("team"), "sl_ppr": st.get("pts_ppr"), "sl_half": st.get("pts_half_ppr"),
                             "sl_std": st.get("pts_std"), "sl_rec": st.get("rec"), "proj_date": x.get("date")})
        print(f"  sleeper {season} done", flush=True)
    new = pd.DataFrame(rows)
    if not old.empty:
        old = old[~old.set_index(["season", "week"]).index.isin(new.set_index(["season", "week"]).index)]
    pd.concat([old, new], ignore_index=True).to_parquet(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
