# -*- coding: utf-8 -*-
"""
check_umaban.py — オッズの馬番→馬名 と records の馬番→馬名 が全レース一致するか確かめる（2026-09-25）
=====================================================================================================
2026-09-12と09-19に「出馬表が仮馬番（五十音順）のままで、別の馬のオッズで買い目を組む」事故が起きた。
9/19は日曜の平場334頭中297頭がずれていた。出力前に必ずこれを通す。

使い方: python check_umaban.py 20260926 20260927
"""
from __future__ import annotations
import glob, json, os, sys, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
SNAP = ROOT / "daily_pdca" / "db" / "odds_snapshots"

ng_total = 0
for date in sys.argv[1:]:
    rec = {}
    for f in glob.glob(str(ROOT / "*" / "週末ビッグデータ_*_records.json")):
        for r in json.loads(Path(f).read_text(encoding="utf-8"))["records"]:
            if r["date"] == date:
                rec.setdefault((r["競馬場"], int(r["R"])), {})[int(r["馬番"])] = r["馬名"]
    latest = {}
    for f in sorted(glob.glob(str(SNAP / date / "*.json"))):
        latest[os.path.basename(f).split("_")[0]] = f
    n = ng = 0
    for rid, f in latest.items():
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        key = (d["venue"], int(d["R"]))
        for h in d["horses"].values():
            n += 1
            if rec.get(key, {}).get(h["umaban"]) != h["horse_name"]:
                ng += 1
                if ng <= 5:
                    print(f"  NG {key} {h['umaban']}番 オッズ側={h['horse_name']} / records側={rec.get(key, {}).get(h['umaban'])}")
    ng_total += ng
    print(f"{date}: {len(latest)}レース {n}頭 → 不一致 {ng}" + ("  ✅" if ng == 0 else "  ❌ 出馬表を --force で取り直すこと"))
sys.exit(1 if ng_total else 0)
