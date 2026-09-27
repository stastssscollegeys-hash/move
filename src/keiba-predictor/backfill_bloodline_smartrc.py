# -*- coding: utf-8 -*-
"""
backfill_bloodline_smartrc.py — 手元のスマート出馬表データから父・母父を埋める（2026-09-25）
=============================================================================================
背景: 累積DBは父・母父が86%欠損で、血統別の仮説がPDCAで判定不能だった。
      既存の backfill_bloodline.py は「馬名→血統登録番号→JV-Linkの血統ファイル」の経路だが、
      血統ファイルが古く6,299件中2,413件しか引けない（31.9%までしか埋まらない）。
      一方 `_cache/smartrc_runners.json`（111MB・手元にある）には **hname と f_name / mf_name** が入っている。
      取得も課金も不要で、残り7,332頭のうち5,541頭（76%）を埋められる。

⚠ 同名馬の可能性があるため、馬名→父名が1対1でない馬は埋めない（衝突として報告する）。
使い方: python backfill_bloodline_smartrc.py [--write]
"""
from __future__ import annotations
import argparse, json, shutil, sys, io, time
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
RESULTS = DB / "race_results.json"
RUNNERS = HERE / "_cache" / "smartrc_runners.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    runners = json.loads(RUNNERS.read_text(encoding="utf-8"))
    ped: dict[str, set] = defaultdict(set)
    for rows in runners.values():
        for r in rows:
            if r.get("hname") and r.get("f_name"):
                ped[r["hname"]].add((r["f_name"], r.get("mf_name") or ""))
    uniq = {k: next(iter(v)) for k, v in ped.items() if len(v) == 1}
    clash = {k for k, v in ped.items() if len(v) > 1}
    print(f"スマート出馬表の馬名→血統: {len(uniq):,}頭（同名で食い違い {len(clash)}頭は使わない）")

    db = json.loads(RESULTS.read_text(encoding="utf-8"))
    before = sum(1 for r in db if not r.get("父"))
    filled = 0
    for r in db:
        if r.get("父") or not r.get("馬名"):
            continue
        p = uniq.get(r["馬名"])
        if not p:
            continue
        r["父"] = p[0]
        if p[1] and not r.get("母父"):
            r["母父"] = p[1]
        filled += 1
    after = sum(1 for r in db if not r.get("父"))
    n = len(db)
    print(f"父なし行: {before:,} → {after:,}（{filled:,}行を補完）")
    print(f"カバー率: {(n-before)/n*100:.1f}% → {(n-after)/n*100:.1f}%")
    sires = defaultdict(int)
    for r in db:
        if r.get("父"):
            sires[r["父"]] += 1
    print(f"種牡馬数: {len(sires)}／出走数150頭以上の種牡馬: {sum(1 for v in sires.values() if v >= 150)}頭")
    if not a.write:
        print("\n※ ドライラン。書き込むには --write")
        return
    bak = RESULTS.with_suffix(f".json.bak_ped_{time.strftime('%Y%m%d_%H%M')}")
    shutil.copy2(RESULTS, bak)
    RESULTS.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
    print("バックアップ:", bak.name, "／ 更新:", RESULTS.name)


if __name__ == "__main__":
    main()
