# -*- coding: utf-8 -*-
"""
chokyo.py — 調教タイム（TARGET frontier JV の CK_DATA・JRA-VAN の HC/WC）を読む（2026-10-05新規・提案2）
==================================================================================================
C:/TFJV/CK_DATA/{年}/{年月}/HC{トレセン}{日付}.DAT … 坂路（2003〜）  1行47字: トレセン1 日付8 時刻4 血統登録番号10 4F4 ラップ3 3F4 ラップ3 2F4 ラップ3 1F(ラップ)3
                              WC{トレセン}{日付}.DAT … ウッド（2021/07〜） 1行92字: トレセン1 日付8 時刻4 血統登録番号10 コース1 回り1 予備1 10F〜2F(4+3)×9 1F3
  タイムは0.1秒単位（0000＝その距離は計測なし）。トレセン 0=美浦 1=栗東
作るもの: db/chokyo_index.pkl = {血統登録番号: [(日付, 種別, 主タイム, 終い1F, 日差, 終い日差, トレセン), ...]}（日付順）
   主タイム = 坂路は4F、ウッドは6F（なければ5F）。日差 = その日・そのトレセン・その種別の中央値との差（馬場の重さを消す）
使い方: python chokyo.py --build
"""
from __future__ import annotations
import argparse, collections, glob, pickle, statistics, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path("C:/TFJV/CK_DATA")
OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "chokyo_index.pkl"


def t(s):
    return int(s) / 10.0 if s.isdigit() and int(s) > 0 else None


def parse_hc(ln):
    if len(ln) < 47:
        return None
    tc, d, hid = ln[0], ln[1:9], ln[13:23]
    f4, f1 = t(ln[23:27]), t(ln[44:47])
    if not f4 or not (40 <= f4 <= 80):
        return None
    return tc, d, hid, "坂路", f4, f1


def parse_wc(ln):
    if len(ln) < 92:
        return None
    tc, d, hid = ln[0], ln[1:9], ln[13:23]
    hs = {}
    for j, fl in enumerate(range(10, 1, -1)):
        hs[fl] = t(ln[26 + j * 7:30 + j * 7])
    f1 = t(ln[89:92])
    main = hs.get(6) or hs.get(5)
    if not main or not (55 <= main <= 100):
        return None
    return tc, d, hid, "ウッド6F" if hs.get(6) else "ウッド5F", main, f1


def build(first="2015"):
    recs = []
    for f in sorted(glob.glob(str(SRC / "*" / "*" / "*.DAT"))):
        name = Path(f).name
        y = Path(f).parent.parent.name
        if y < first:
            continue
        kind = name[:2]
        if kind not in ("HC", "WC"):
            continue
        for ln in Path(f).read_bytes().decode("ascii", "ignore").split("\r\n"):
            x = parse_hc(ln) if kind == "HC" else parse_wc(ln)
            if x:
                recs.append(x)
    # JV-Link の通常読み（jv_extract.ps1 -Spec SLOP/WOOD -Keep HC,WC）: 先頭11字（ID2・区分1・作成日8）を除くと TARGET と同じ並び
    seen = {(x[1], x[2], x[0], x[3]) for x in recs[-400000:]} if recs else set()
    for sub, kind in (("SLOP", "HC"), ("WOOD", "WC")):
        for f in sorted((Path("C:/keiba_db/jv_raw") / sub).glob(f"{kind}_*.txt")):
            for ln in f.read_bytes().decode("ascii", "ignore").splitlines():
                if ln[:2] != kind:
                    continue
                x = parse_hc(ln[11:]) if kind == "HC" else parse_wc(ln[11:])
                if x and (x[1], x[2], x[0], x[3]) not in seen:
                    recs.append(x)
                    seen.add((x[1], x[2], x[0], x[3]))
    day, day1 = collections.defaultdict(list), collections.defaultdict(list)
    for tc, d, hid, k, m, f1 in recs:
        day[(tc, d, k)].append(m)
        if f1:
            day1[(tc, d, k)].append(f1)
    med = {k: statistics.median(v) for k, v in day.items() if len(v) >= 10}
    med1 = {k: statistics.median(v) for k, v in day1.items() if len(v) >= 10}
    idx = collections.defaultdict(list)
    for tc, d, hid, k, m, f1 in recs:
        md, m1 = med.get((tc, d, k)), med1.get((tc, d, k))
        idx[hid].append((d, k, m, f1, (m - md) if md else None, (f1 - m1) if (f1 and m1) else None, tc))
    for v in idx.values():
        v.sort()
    OUT.write_bytes(pickle.dumps(dict(idx)))
    print(f"■ 調教 {len(recs):,}本・{len(idx):,}頭 → {OUT}")


def load():
    return pickle.loads(OUT.read_bytes()) if OUT.exists() else {}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    if a.build:
        build()
