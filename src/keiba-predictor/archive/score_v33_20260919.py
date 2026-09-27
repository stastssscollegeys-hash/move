# -*- coding: utf-8 -*-
"""
score_v33_20260919.py — 2026/9/20 オールカマー(G2・中山芝2200) の20因子v3.3（170点満点）採点
==========================================================================
score_v33_20260912.py と同じ規則。変更点はレース設定と入力ファイルだけ。
  - sc[3]脚質・sc[7]枠: オールカマー過去10回の自前集計（research/allcomers_pre_draw_20260916.md）
  - sc[12]/sc[18]/sc[19]: _cache/allcomers_2026_form.json（馬柱の近走・格つき）
  - sc[9]: うましる（9/17公開・oikiri.json 登録済み）
  - 合算補正: 今週はインフルエンサー収集をしていないので0
出力: Desktop/競馬予想レポート/20260920/research/score20_20260918.json
"""
from __future__ import annotations
import json, sys, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent
ROOT = Path.home() / "Desktop" / "競馬予想レポート"
BASE = ROOT / "20260920"
RES = BASE / "research"
RECORDS = ROOT / "20260920" / "週末ビッグデータ_20260920-0920_records.json"   # 9/19夜: 日曜分は仮馬番だったため単日ファイルで作り直した

RACE = "オールカマー"
CFG = dict(date="20260920", venue="中山", dist=2200, repeat="オールカマー",
           style={"逃げ": 34.8, "先行": 25.0, "差し": 30.4, "追込": 6.5},
           waku={1: 46, 2: 27, 3: 27, 4: 25, 5: 28, 6: 11, 7: 11, 8: 14},
           pace={"逃げ": 8, "先行": 8, "差し": 7, "追込": 6})   # はっきりした逃げはセイウンプラチナ1頭→緩い流れ・前有利

# sc[9]は oikiri.json（source付き）から2ソースの平均で取る（2026-09-25改定・ユーザー承認）
#   昇格は「両ソースともS/A」のときだけ。詳細は oikiri_factor.py / SKILL.md
from oikiri_factor import load_oikiri
JOCKEY_FLAG = [("川田", "阪神", +2), ("ルメール", "中山", +2), ("横山武", "中山", +1)]
LV = {"GI": 11, "GII": 10, "GIII": 9.5, "L": 8.5, "OP": 8.5, "3勝": 8, "2勝": 7.5, "1勝": 7, "未勝利": 6, "新馬": 6, "?": 7}


def lin(v, lo, hi, vmin=0.0, vmax=100.0):
    if v is None:
        return (lo + hi) / 2
    x = max(vmin, min(vmax, float(v)))
    return lo + (hi - lo) * (x - vmin) / (vmax - vmin)


def grade(r):
    g = r.get("grade") or ""
    if g in LV:
        return g
    return "3勝" if r["race"].endswith("S") or "特別" in r["race"] else "?"


def sc12(runs):
    runs = [r for r in runs if r["surf"] == "芝"]
    if not runs:
        return 7.0, "芝の前走なし"
    r = runs[0]
    v = LV.get(grade(r), 7)
    v += 0.5 if r["fin"] <= 3 else (-2 if r["fin"] >= 10 else 0)
    return max(6, min(11, v)), f"{r['race'][:10]}({grade(r)}) {r['fin']}着"


def sc19(runs):
    best, why = 4.0, "3勝クラス以下"
    for r in runs:
        if r["surf"] != "芝":
            continue
        g, k = grade(r), r["fin"]
        v = None
        if g == "GI" and k <= 3: v = 7
        elif (g == "GI" and k <= 5) or (g in ("GII", "GIII") and k == 1): v = 6.5
        elif g in ("GII", "GIII") and k <= 3: v = 6
        elif (g in ("L", "OP") and k == 1) or (g in ("GI", "GII", "GIII") and k <= 5): v = 5.5
        elif g == "3勝" and k == 1: v = 5
        if v and v > best:
            best, why = v, f"{r['race'][:10]}({g}) {k}着"
    return best, why


def sc18(runs):
    rep = [r for r in runs if CFG["repeat"] in r["race"] and r["fin"] <= 3]
    if rep:
        return 8.0, f"同レース{rep[0]['date'][:4]}年{rep[0]['fin']}着（リピーター）"
    same = [r for r in runs if r["surf"] == "芝" and r["dist"] == CFG["dist"] and r["ven"] == CFG["venue"]]
    if not same:
        return 5.0, "近走に同コースなし（減点しない）"
    b = min(r["fin"] for r in same)
    return (8.0 if b == 1 else 7.0 if b <= 3 else 6.0 if b <= 5 else 4.5), f"同コース{len(same)}走・最高{b}着"


def main():
    recs = json.load(open(RECORDS, encoding="utf-8"))["records"]
    yoso = {h["name"]: h for h in json.load(open(BASE / "yoso_odds_20260918.json", encoding="utf-8"))[RACE]["horses"]}
    form = {h["name"]: h for h in json.load(open(SRC / "_cache" / "allcomers_2026_form.json", encoding="utf-8"))}
    oik = load_oikiri(CFG["date"], CFG["venue"], 11)
    rows = [r for r in recs if r["date"] == CFG["date"] and r["競馬場"] == CFG["venue"] and r["R"] == 11]
    table = []
    for r in rows:
        nm = r["馬名"]
        runs = [x for x in (form.get(nm) or {}).get("runs", []) if x.get("race") and x.get("fin") and x.get("surf")]
        y = yoso.get(nm) or {}
        jk = y.get("jockey", "")
        style = r.get("脚質") or "先行"
        s = {}
        s[1] = lin(r["F02_タイム"], 5, 12)
        s[2] = lin(r["F03_着差"], 6, 11)
        s[3] = lin(CFG["style"].get(style, 20), 6, 10, 0, 45)
        s[4] = lin(r["近5走複勝率%"], 6, 11)
        j = lin(r["F04_騎手"], 5, 8)
        for who, ven, adj in JOCKEY_FLAG:
            if who in jk and ven == CFG["venue"]:
                j += adj
        s[5] = min(8.0, j)
        s[6] = 6.5
        s[7] = lin(CFG["waku"].get(int(r["枠"] or 0), 20), 3, 7, 0, 46)
        s[8] = CFG["pace"].get(style, 7)
        s[9] = oik.point(nm)
        s[10] = 7.0
        s[11] = 9.5
        s[12], why12 = sc12(runs)
        s[13] = lin(r["F05_厩舎"], 6, 9)
        s[14] = lin(r["F10_斤量"], 6, 8)
        s[15] = lin(r["F12_年齢"], 6, 8, 60, 100)
        s[16] = lin(r["F14_馬場"], 3, 9)
        s[17] = 4.0
        s[18], why18 = sc18(runs)
        s[19], why19 = sc19(runs)
        s[20] = 3.0
        raw = round(min(170.0, sum(s.values())), 1)
        table.append({"name": nm, "waku": r["枠"], "uma": r["馬番"], "style": style, "jockey": jk,
                      "pop": y.get("pop"), "odds": y.get("odds"), "sogo": r["総合指数"],
                      "sc": {k: round(v, 1) for k, v in s.items()}, "raw170": raw, "ens_adj": 0.0,
                      "final170": raw, "oikiri": (oik.by_horse.get(nm, {}).get("umasiru")
                                                  or next(iter(oik.by_horse.get(nm, {}).values()), "—")),
                      "oikiri_detail": oik.detail(nm), "oikiri_sources": oik.sources(nm),
                      "oikiri_promote": oik.can_promote(nm),
                      "why": {"sc12": why12, "sc18": why18, "sc19": why19, "sc6": ""}})
    table.sort(key=lambda x: -x["final170"])
    print(f"### {RACE}（{CFG['venue']}芝{CFG['dist']}m・{len(table)}頭）")
    print(" 順 枠番 馬名             脚質 追切 最終   総合指数 予想人気(単勝) | sc5騎手 sc7枠 sc9 sc12前走 sc18 sc19格 | 根拠")
    for i, x in enumerate(table, 1):
        sc = x["sc"]
        print(f" {i:>2} {x['waku']}-{x['uma']:>2} {x['name']:<10} {x['style']:<2} {x['oikiri']} {x['final170']:>6} {x['sogo']:>6}  {x['pop']}人({x['odds']}) "
              f"| {sc[5]} {sc[7]} {sc[9]} {sc[12]} {sc[18]} {sc[19]} | 前走:{x['why']['sc12']} / {x['why']['sc18']} / 格:{x['why']['sc19']}")
    RES.mkdir(parents=True, exist_ok=True)
    json.dump({RACE: table}, open(RES / "score20_20260918.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nsaved research/score20_20260918.json")


if __name__ == "__main__":
    main()
