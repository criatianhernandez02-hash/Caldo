"""Bundle rankings + backtest results into the single-file calculator web/index.html."""
import json
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
    (ROOT / "web" / "index.html").write_text(tpl.replace("/*__DATA__*/", payload))
    print("wrote web/index.html")


if __name__ == "__main__":
    main()
