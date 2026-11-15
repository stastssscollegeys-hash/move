# -*- coding: utf-8 -*-
"""raceday_refresh.py — 開催日の「今日の予想」を1回で更新する（2026-11-15 新設）
ユーザー指示（2026-11-15）: 「予想をアップデートして。アップデートできる形で」。
順に: 結果（web_results）→ 今日の傾向（web_today_trends・朝版と直前版の答え合わせ・今日の学び）→ [--live なら確率を最新オッズで取り直す web_live 約8分]
     → まだ発走していないレースの買い目（web_compose）→ 馬ごとの材料（web_facts）→ 全レースの表（all_races_sheet）
  python raceday_refresh.py --date 20261115 --prev 20261114 --seed 2608050411 [--live] [--margin 10]
--margin: 発走まで何分未満のレースは外すか（既定10分）。出力: {日付}_今日の傾向.md と {日付}_全レース_印と買い目.md"""
import argparse, datetime, json, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path("C:/Users/User/Desktop/競馬予想レポート"); OUT = ROOT / "daily_pdca/web_live"; PY = sys.executable


def run(args, log=None, timeout=1200):
    print(">", " ".join(args), flush=True)
    r = subprocess.run([PY] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if log: Path(log).write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode: print(r.stderr[-800:]); raise SystemExit(f"失敗: {args[0]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--prev", default="")
    ap.add_argument("--seed", default=""); ap.add_argument("--live", action="store_true"); ap.add_argument("--margin", type=int, default=10)
    a = ap.parse_args(); R = ROOT / a.date / "research"; R.mkdir(parents=True, exist_ok=True)
    prev = ["--prev", a.prev] if a.prev else []
    run(["web_results.py", "--date", a.date])
    run(["web_today_trends.py", "--date", a.date] + prev)
    if a.live:
        if not a.seed: raise SystemExit("--live には --seed（その日のどれか1レースのYahoo ID）が要る")
        f = OUT / f"{a.date}_web_probs.json"; bk = OUT / f"{a.date}_web_probs_prev{datetime.datetime.now():%H%M}.json"
        if f.exists(): bk.write_bytes(f.read_bytes())
        run(["web_live.py", "--date", a.date, "--seed", a.seed], log=R / "web_live_refresh.log", timeout=1800)
    P = json.load(open(OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"]
    now = datetime.datetime.now(); lim = now + datetime.timedelta(minutes=a.margin)
    todo = []
    for k, v in sorted(P.items(), key=lambda x: x[1]["start"].zfill(5)):
        h, m = map(int, v["start"].split(":")); st = now.replace(hour=h, minute=m, second=0)
        if st > lim and v["horses"]: todo.append(f"{v['venue']}{int(v['R'])}")
    if not todo: print("これから発走するレースがない"); return
    print("対象:", " ".join(todo))
    raw = R / f"web_compose_refresh_{now:%H%M}.txt"
    raw.write_text(run(["web_compose.py", "--date", a.date, "--race"] + todo), encoding="utf-8")
    run(["web_facts.py", "--date", a.date, "--race"] + todo, log=R / "web_facts_all.txt")
    print(run(["all_races_sheet.py", "--date", a.date, "--raw", str(raw)] + prev))


if __name__ == "__main__":
    main()
