"""Bundle rankings + backtest results into the calculator.

Writes two builds from web/template.html:
  web/index.html  single file, for the claude.ai artifact or opening locally
  site/           installable web app (manifest, offline cache, icons) for GitHub Pages or any static host
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from caldo.config import BACKTEST_SEASONS, OUT_DIR, ROOT

ABLATION_LABELS = {
    "no_vegas": "Vegas implied total & spread",
    "no_matchup": "Matchup (defense vs position)",
    "no_home_dome": "Home/away & dome",
    "no_context": "All game context",
    "no_usage": "Usage & red-zone stats",
}


def backtest_summary(scoring="ppr"):
    bt = OUT_DIR / "backtest"
    wk = pd.read_csv(bt / f"weekly_summary_{scoring}.csv")
    ros = pd.read_csv(bt / f"ros_summary_{scoring}.csv")
    pos = ["QB", "RB", "WR", "TE"]
    abl = []
    for v, label in ABLATION_LABELS.items():
        m = f"m_{v}"
        if m not in set(wk.model):
            continue
        dw = (wk[(wk.model == m) & wk.position.isin(pos)].rank_corr.mean()
              - wk[(wk.model == "m_full") & wk.position.isin(pos)].rank_corr.mean())
        dr = (ros[(ros.model == m) & ros.position.isin(pos)].rank_corr.mean()
              - ros[(ros.model == "m_full") & ros.position.isin(pos)].rank_corr.mean())
        abl.append({"label": label, "weekly": round(float(dw), 4), "ros": round(float(dr), 4)})
    clean = lambda d: json.loads(d.round(4).to_json(orient="records"))
    return {"seasons": f"{BACKTEST_SEASONS[0]}–{BACKTEST_SEASONS[-1]}", "weekly": clean(wk), "ros": clean(ros),
            "ablation": abl}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", help="JSON file with a sleeper_snapshot to bundle (kept out of the repo)")
    ap.add_argument("--out", help="with --snapshot: where to write the single-file page")
    args = ap.parse_args()
    data = json.loads((ROOT / "web" / "data.json").read_text())
    if (OUT_DIR / "backtest" / "weekly_summary_ppr.csv").exists():
        data["meta"]["backtest"] = backtest_summary()
    f = pd.read_csv(OUT_DIR / "formula_ppr.csv")
    mult = f[f.part == "multiplier"].pivot(index="position", columns="term", values="coef")
    data["meta"]["formula"] = {"multipliers": json.loads(mult.round(4).to_json(orient="index"))}
    pw = OUT_DIR / "package_weights.json"
    if pw.exists():
        data["meta"]["package"] = json.loads(pw.read_text())
    tpl = (ROOT / "web" / "template.html").read_text()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = tpl.replace("/*__DATA__*/", payload)
    if args.snapshot:
        data["sleeper_snapshot"] = json.loads(Path(args.snapshot).read_text())
        bundled = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
        Path(args.out).write_text(tpl.replace("/*__DATA__*/", bundled).replace("<!--__PWA__-->\n", ""))
        print(f"wrote {args.out} with a bundled Sleeper league")
        return
    (ROOT / "web" / "index.html").write_text(page.replace("<!--__PWA__-->\n", ""))

    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    head = ('<link rel="manifest" href="manifest.webmanifest">\n'
            '<meta name="theme-color" content="#22603f">\n'
            '<link rel="icon" href="icon-192.png">\n<link rel="apple-touch-icon" href="icon-192.png">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">')
    body = page.replace("<!--__PWA__-->", head)
    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
           '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
           'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n')
    (site / "index.html").write_text(doc + body + "\n</body></html>\n")
    for f in (ROOT / "web" / "pwa").iterdir():
        shutil.copy(f, site / f.name)
    print("wrote web/index.html and site/")


if __name__ == "__main__":
    main()
