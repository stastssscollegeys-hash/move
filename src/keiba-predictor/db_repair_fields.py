# -*- coding: utf-8 -*-
"""
db_repair_fields.py — 蓄積DBの既知の欠陥を自前データで修復する（2026-09-27）
==============================================================================
keiba_data_defects_fixed で未修正だったもの:
  ① 中日数 = 0 が約75%残存（過去走キャッシュの古い形式が更新されない）
  ② 着順int が欠けている行が多い（着順が数字なのに int 化されていない）
どちらも蓄積DB自身から復元できる:
  ① 同じ馬の直前の出走日との差（DB内に前走が無い馬は None のまま＝0で埋めない）
  ② 着順が数字なら int、中止/取消/除外/失格は None
使い方: python db_repair_fields.py            # ドライラン（件数だけ）
        python db_repair_fields.py --write    # 書き込み（バックアップ作成）
"""
from __future__ import annotations
import argparse, collections, datetime, json, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
P = DB / "race_results.json"
ap = argparse.ArgumentParser()
ap.add_argument("--write", action="store_true")
a = ap.parse_args()

rows = json.loads(P.read_text(encoding="utf-8"))


def d(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


# ② 着順int
fix2 = bad2 = 0
for r in rows:
    if r.get("着順int"):
        continue
    s = str(r.get("着順") or "").strip()
    if s.isdigit():
        r["着順int"] = int(s)
        fix2 += 1
    else:
        bad2 += 1                                  # 中止・取消・除外・失格など

# ① 中日数
by_horse = collections.defaultdict(list)
for r in rows:
    if r.get("馬名") and r.get("date"):
        by_horse[r["馬名"]].append(r)
zero_before = sum(1 for r in rows if str(r.get("中日数")) in ("0", "0.0"))
fix1 = nofix1 = keep1 = 0
for name, hs in by_horse.items():
    hs.sort(key=lambda r: (r["date"], r.get("競馬場", ""), int(float(r.get("R") or 0))))
    for i, r in enumerate(hs):
        cur = r.get("中日数")
        try:
            cur_v = int(float(cur)) if cur not in (None, "") else None
        except (TypeError, ValueError):
            cur_v = None
        if cur_v not in (None, 0):
            keep1 += 1
            continue                               # 正の値はそのまま（外部取得の正しい値）
        if i == 0:
            nofix1 += 1                            # DB内に前走が無い → 分からない（0のままにはしない）
            if cur_v == 0:
                r["中日数"] = None
                r["中日数_note"] = "DB内に前走なし（旧値0は欠損の意味）"
            continue
        gap = (d(r["date"]) - d(hs[i - 1]["date"])).days
        r["中日数"] = gap
        r["中日数_src"] = "db_repair"
        fix1 += 1

print(f"■ 着順int: {fix2:,}行を補完（数字でない着順 {bad2:,}行は None のまま）")
print(f"■ 中日数: 0だった行 {zero_before:,} → DB内の前走から補完 {fix1:,}行／前走がDBに無く欠損(None)化 {nofix1:,}行／正の値をそのまま {keep1:,}行")
after0 = sum(1 for r in rows if str(r.get("中日数")) in ("0", "0.0"))
print(f"   修復後に『0』が残る行: {after0:,}")
if a.write:
    bak = P.with_suffix(f".json.bak_repair_{datetime.datetime.now():%Y%m%d_%H%M}")
    shutil.copy2(P, bak)
    P.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"書き込み完了（バックアップ: {bak.name}）")
else:
    print("※ ドライラン。--write で書き込む")
