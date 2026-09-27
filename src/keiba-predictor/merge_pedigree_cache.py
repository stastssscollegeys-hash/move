# -*- coding: utf-8 -*-
"""
merge_pedigree_cache.py — 取得済みの血統キャッシュを累積DBに反映する（2026-09-25）
====================================================================================
fetch_pedigree_netkeiba.py は最後にまとめて書き込む作りなので、
途中で止めた場合（netkeiba側の速度制限など）はこのスクリプトでキャッシュ分だけ反映する。
"""
from __future__ import annotations
import json, shutil, sys, io, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RESULTS = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "race_results.json"
CACHE = HERE / "_cache" / "pedigree_netkeiba.json"

ped = json.loads(CACHE.read_text(encoding="utf-8"))
by_name = {v["name"]: v for v in ped.values()}
db = json.loads(RESULTS.read_text(encoding="utf-8"))
before = sum(1 for r in db if not r.get("父"))
filled = 0
for r in db:
    if r.get("父") or not r.get("馬名"):
        continue
    p = by_name.get(r["馬名"])
    if not p:
        continue
    r["父"] = p["father"]
    if p.get("mf") and not r.get("母父"):
        r["母父"] = p["mf"]
    filled += 1
after = sum(1 for r in db if not r.get("父"))
bak = RESULTS.with_suffix(f".json.bak_pedmerge_{time.strftime('%Y%m%d_%H%M')}")
shutil.copy2(RESULTS, bak)
RESULTS.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
n = len(db)
print(f"キャッシュ {len(ped):,}頭 → {filled:,}行を補完")
print(f"父なし: {before:,} → {after:,}／カバー率 {(n-after)/n*100:.1f}%")
print("バックアップ:", bak.name)
