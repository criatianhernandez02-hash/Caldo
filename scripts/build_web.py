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
    # ablations were run on the original model (v1); compare like with like
    v1 = bt / "v1" / f"ros_summary_{scoring}.csv"
    ros_abl = pd.read_csv(v1) if v1.exists() else ros
    for v, label in ABLATION_LABELS.items():
        m = f"m_{v}"
        if m not in set(wk.model):
            continue
        dw = (wk[(wk.model == m) & wk.position.isin(pos)].rank_corr.mean()
              - wk[(wk.model == "m_full") & wk.position.isin(pos)].rank_corr.mean())
        dr = (ros_abl[(ros_abl.model == m) & ros_abl.position.isin(pos)].rank_corr.mean()
              - ros_abl[(ros_abl.model == "m_full") & ros_abl.position.isin(pos)].rank_corr.mean())
        if pd.isna(dr) or pd.isna(dw):
            continue
        abl.append({"label": label, "weekly": round(float(dw), 4), "ros": round(float(dr), 4)})
    clean = lambda d: json.loads(d.round(4).to_json(orient="records"))
    return {"seasons": f"{BACKTEST_SEASONS[0]}–{BACKTEST_SEASONS[-1]}", "weekly": clean(wk), "ros": clean(ros),
            "ablation": abl}


def _clean_nan(x):
    """JSON has no NaN; the page's JSON.parse would reject the whole payload."""
    if isinstance(x, float) and x != x:
        return None
    if isinstance(x, dict):
        return {k: _clean_nan(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean_nan(v) for v in x]
    return x


def compare_summary():
    """Head-to-head vs. Sleeper, blind spots, blend config and live agreement, for the app."""
    c = OUT_DIR / "compare"
    out = {}
    clean = lambda d: json.loads(d.round(4).to_json(orient="records"))
    for name in ["head_to_head", "blind_spots", "weekly_accuracy", "ros_agreement"]:
        f = c / f"{name}.csv"
        if f.exists():
            out[name] = clean(pd.read_csv(f))
    b = OUT_DIR / "blend.json"
    if b.exists():
        cfg = json.loads(b.read_text())
        out["blend"] = {"weights": cfg["weights"], "availability": {k: v for k, v in cfg["availability"].items() if k != "healthy_curve"}}
    old, new = OUT_DIR / "backtest" / "v1" / "ros_summary_ppr.csv", OUT_DIR / "backtest" / "ros_summary_ppr.csv"
    if old.exists() and new.exists():
        a, b2 = pd.read_csv(old), pd.read_csv(new)
        pick = lambda d, m: d[d.model == m].set_index("position")
        imp = pick(a, "m_full")[["rank_corr", "pair_acc"]].join(pick(b2, "m_full")[["rank_corr", "pair_acc"]], rsuffix="_new")
        imp = imp.join(pick(b2, "m_no_status")[["rank_corr", "pair_acc"]].add_suffix("_nostatus"))
        out["improvement"] = clean(imp.reset_index())
    return out


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
    data["meta"]["compare"] = compare_summary()
    to = OUT_DIR / "trade_odds.json"
    if to.exists():
        data["meta"]["trade_odds"] = json.loads(to.read_text())
    tt = OUT_DIR / "trade_test"

    def read(name, **kw):
        try:
            return json.loads(pd.read_csv(tt / name, **kw).round(4).reset_index(drop="index_col" not in kw).to_json(orient="records"))
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return []
    if (tt / "summary.json").exists():
        data["meta"]["trade_test"] = {
            "summary": json.loads((tt / "summary.json").read_text()),
            "within": read("within_trade.csv"),
            "refit": read("within_trade_refit.csv"),
            "won": read("who_won.csv"),
            "real_vs_random": read("real_vs_random.csv", index_col=0),
        }
    pw = OUT_DIR / "package_weights.json"
    if pw.exists():
        data["meta"]["package"] = json.loads(pw.read_text())
    tpl = (ROOT / "web" / "template.html").read_text()
    payload = json.dumps(_clean_nan(data), separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    page = tpl.replace("/*__DATA__*/", payload)
    if args.snapshot:
        data["sleeper_snapshot"] = json.loads(Path(args.snapshot).read_text())
        bundled = json.dumps(_clean_nan(data), separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
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
