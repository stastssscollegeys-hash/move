# -*- coding: utf-8 -*-
"""
score_v33_20260912.py — 2026/9/12-13 重賞3本の20因子v3.3（170点満点）採点
==========================================================================
対象: チャレンジC(G3・9/12阪神芝2000) / セントライト記念(G2・9/13中山芝2200) / ローズS(G2・9/13阪神芝1800)

SKILL.md「sc配列」「v3.3 追加3因子」の点数範囲に、手元の実データを規則で当てはめる。
（従来は手採点で根拠が残っていなかったため、同じ入力なら同じ点になるよう規則化した）

  sc[1]  タイム      5〜12  ← エンジンF02_タイム(0-100)を範囲に換算
  sc[2]  ラップ      6〜11  ← エンジンF03_着差
  sc[3]  特性        6〜10  ← そのレース自体（同じ競馬場の年だけ）の脚質別3着内率
  sc[4]  実績        6〜11  ← 近5走複勝率%
  sc[5]  騎手        5〜8   ← エンジンF04＋SKILLのコース別騎手補正（川田×阪神芝+2 等）
  sc[6]  血統        5〜8   ← 外部サイトで「このコースは苦手」と明記された父のみ5点。他は中立6.5
                              （血統は消す理由にだけ使う: keiba_bloodline_analysis）
  sc[7]  枠順        3〜7   ← そのレース自体（同じ競馬場の年だけ）の枠別3着内率
  sc[8]  展開        6〜8   ← 展開想定×脚質（research/*_external の pace_outlook）
  sc[9]  調教        6〜9   ← うましる S=9/A=8/B=7/C以下=6（SKILL既定）
  sc[10] 体重        6〜8   ← 前日は不明 → 中立7
  sc[11] EV乖離      5〜14  ← 実オッズ未確定＋「モデルの妙味判定は逆効果」の実測 → 中立9.5
  sc[12] 前走Lv      6〜11  ← 前走（芝）のレース格と着順
  sc[13] 厩舎        6〜9   ← エンジンF05
  sc[14] 斤量        6〜8   ← エンジンF10（フィールド平均比）
  sc[15] 成長        6〜8   ← エンジンF12（年齢曲線）
  sc[16] 馬場        3〜9   ← エンジンF14（芝ダ×会場適性）。当日の馬場は当日に判断（9/11ユーザー指示）
  sc[17] 輸送        3〜5   ← データなし → 中立4
  sc[18] コース実績  3〜8   ← 同コース同距離の最高着順／同一レースのリピーター。初コースは減点しない(中立5)
  sc[19] 基準タイム・格 3〜7 ← 全戦績（芝）の最高格×着順（G1 3着内=7 …）。格上の検出
  sc[20] 外部指数整合 2〜5  ← jiro8は前日更新で未取得 → 中立3

出力: Desktop/競馬予想レポート/20260912/research/score20_20260911.json
"""
from __future__ import annotations
import json, re, sys, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path.home() / "Desktop" / "競馬予想レポート" / "20260912"
RES = BASE / "research"

RACES = {
    "チャレンジC": dict(date="20260912", venue="阪神", dist=2000, slug="challenge", repeat="チャレンジ",
                        # race_history同条件8回（阪神芝2000）
                        style={"逃げ": 19, "先行": 45, "差し": 28, "追込": 9},
                        waku={1: 25, 2: 44, 3: 20, 4: 27, 5: 7, 6: 44, 7: 19, 8: 12},
                        pace={"逃げ": 7, "先行": 8, "差し": 7, "追込": 6}),   # 逃げ候補複数→先行に展開利
    "セントライト記念": dict(date="20260913", venue="中山", dist=2200, slug="stlite", repeat="セントライト",
                        style={"逃げ": 18, "先行": 25, "差し": 38, "追込": 6},
                        waku={1: 36, 2: 21, 3: 19, 4: 29, 5: 25, 6: 20, 7: 19, 8: 10},
                        pace={"逃げ": 6, "先行": 7, "差し": 8, "追込": 6}),   # 先行過多→3角ロングスパート
    "ローズS": dict(date="20260913", venue="阪神", dist=1800, slug="rose", repeat="ローズ",
                        style={"逃げ": 31, "先行": 15, "差し": 21, "追込": 15},
                        waku={1: 11, 2: 9, 3: 36, 4: 18, 5: 18, 6: 25, 7: 21, 8: 13},
                        pace={"逃げ": 8, "先行": 8, "差し": 7, "追込": 6}),   # 逃げは単騎→前有利
}

# うましる追い切り（oikiri.json に登録済みの内容）
UMASIRU = {
    "チャレンジC": "マリアイリダータ:S ガイアメンテ:A ジーティーアダマン:A ジーティーダーリン:A マテンロウゲイル:A ミッキーゴールド:A レーゼドラマ:A カラマティアノス:B グランヴィノス:B ジョバンニ:B センツブラッド:B タガノデュード:B ピースワンデュック:B フィーリウス:B マテンロウスカイ:B カネフラ:C",
    "セントライト記念": "ゴーイントゥスカイ:S サノノグレーター:S ウェイクフィールド:A サヴォアフェール:A ラディアントスター:A アウダーシア:B エリプティクカーブ:B ジャスティンシカゴ:B ティラーノ:B ミリオンクラウン:B リッツパーティー:B アスクエジンバラ:C バステール:C バドリナート:C フウセン:C ラージアンサンブル:C",
    "ローズS": "モンローウォーク:S タイセイボーグ:A レイクラシック:A アンジュドジョワ:B アンディムジーク:B イクシード:B エンネ:B スウィートハピネス:B スマートプリエール:B ミリタリータトゥー:B ナムラコスモス:C ファストフォワード:C",
}
OIKIRI_PT = {"S": 9, "A": 8, "B": 7}

# 外部サイトで「このコースは苦手」と明記された父（research/*_external.json の bloodline_note）
BAD_SIRE = {
    "チャレンジC": {"カラマティアノス": "父レイデオロ 阪神芝2000複勝率11.1%",
                  "ジーティーダーリン": "父サートゥルナーリア 阪神芝2000複勝率12.5%"},
    "セントライト記念": {"ティラーノ": "ゴールドシップ産駒 当コース勝率低調"},
    "ローズS": {"イクシード": "父キタサンブラック 阪神芝1800複勝率14.3%",
               "アンジュドジョワ": "父キタサンブラック 阪神芝1800複勝率14.3%",
               "レイクラシック": "父キタサンブラック 阪神芝1800複勝率14.3%"},
}

# SKILL v3.2 コース別騎手補正（sc[5]）
JOCKEY_FLAG = [("川田", "阪神", +2), ("ルメール", "中山", +2), ("横山武", "中山", +1)]


def lin(v, lo, hi, vmin=0.0, vmax=100.0):
    """v(vmin〜vmax) を lo〜hi に線形換算"""
    if v is None:
        return (lo + hi) / 2
    x = max(vmin, min(vmax, float(v)))
    return lo + (hi - lo) * (x - vmin) / (vmax - vmin)


def grade_of(name: str) -> str:
    for g in ("GIII", "GII", "GI", "(L)", "(OP)"):
        if g in name:
            return g.strip("()")
    for k in ("3勝", "2勝", "1勝", "未勝利", "新馬"):
        if k in name:
            return k
    return "OP" if re.search(r"(S|ステークス|特別|賞|C|カップ)", name) else "?"


LV = {"GI": 11, "GII": 10, "GIII": 9.5, "L": 8.5, "OP": 8.5, "3勝": 8, "2勝": 7.5, "1勝": 7, "未勝利": 6, "新馬": 6, "?": 7}


def sc12(runs):
    if not runs:
        return 7.0, "前走なし"
    r = runs[0]
    g = grade_of(r["race"])
    v = LV.get(g, 7)
    if r["rank"] <= 3:
        v += 0.5
    elif r["rank"] >= 10:
        v -= 2
    return max(6, min(11, v)), f"{r['race'][:14]} {r['rank']}着"


def sc19(runs):
    best, why = 4.0, "3勝クラス以下"
    for r in runs:
        g, k = grade_of(r["race"]), r["rank"]
        v = None
        if g == "GI" and k <= 3: v = 7
        elif (g == "GI" and k <= 5) or (g in ("GII", "GIII") and k == 1): v = 6.5
        elif g in ("GII", "GIII") and k <= 3: v = 6
        elif (g in ("L", "OP") and k == 1) or (g in ("GI", "GII", "GIII") and k <= 5): v = 5.5
        elif g == "3勝" and k == 1: v = 5
        if v and v > best:
            best, why = v, f"{r['race'][:14]} {k}着"
    return best, why


def sc18(runs, venue, dist, repeat):
    same = [r for r in runs if r["dist"] == dist and venue in r["kaisai"]]
    rep = [r for r in runs if repeat in r["race"] and r["rank"] <= 3]
    if rep:
        return 8.0, f"同レース{rep[0]['date'][:4]}年{rep[0]['rank']}着（リピーター）"
    if not same:
        return 5.0, "初コース（減点しない）"
    b = min(r["rank"] for r in same)
    v = 8.0 if b == 1 else 7.0 if b <= 3 else 6.0 if b <= 5 else 4.5
    return v, f"同コース{len(same)}走・最高{b}着"


def main():
    recs = json.load(open(BASE / "週末ビッグデータ_20260912-0913_records.json", encoding="utf-8"))["records"]
    yoso = json.load(open(BASE / "yoso_odds_20260911.json", encoding="utf-8"))
    baba = json.load(open(RES / "starters_baba_20260911.json", encoding="utf-8"))
    # 9/12更新の合算（土曜収集分を含む）があればそちらを使う
    ens_path = RES / "ensemble_20260912.json"
    if not ens_path.exists():
        ens_path = RES / "ensemble_20260910.json"
    print(f"合算ファイル: {ens_path.name}")
    ens = json.load(open(ens_path, encoding="utf-8"))
    out = {}
    for race, cfg in RACES.items():
        oik = dict(x.split(":") for x in UMASIRU[race].split())
        ymap = {h["name"]: h for h in yoso[race]["horses"] if h.get("name") and h["name"] != "?"}
        emap = {r["name"]: r for r in ens[race]}
        rows = [r for r in recs if r["date"] == cfg["date"] and r["競馬場"] == cfg["venue"] and r["R"] == 11]
        table = []
        for r in rows:
            nm = r["馬名"]
            runs = (baba[race].get(nm) or {}).get("turf_runs", [])
            jk = (ymap.get(nm) or {}).get("jockey", "")
            style = r.get("脚質") or "先行"
            s = {}
            s[1] = lin(r["F02_タイム"], 5, 12)
            s[2] = lin(r["F03_着差"], 6, 11)
            s[3] = lin(cfg["style"].get(style, 20), 6, 10, 0, 45)
            s[4] = lin(r["近5走複勝率%"], 6, 11)
            j = lin(r["F04_騎手"], 5, 8)
            for who, ven, adj in JOCKEY_FLAG:
                if who in jk and ven == cfg["venue"]:
                    j += adj
            s[5] = min(8.0, j)
            s[6] = 5.0 if nm in BAD_SIRE[race] else 6.5
            s[7] = lin(cfg["waku"].get(int(r["枠"] or 0), 20), 3, 7, 0, 44)
            s[8] = cfg["pace"].get(style, 7)
            s[9] = OIKIRI_PT.get(oik.get(nm, "C"), 6)
            s[10] = 7.0
            s[11] = 9.5
            s[12], why12 = sc12(runs)
            s[13] = lin(r["F05_厩舎"], 6, 9)
            s[14] = lin(r["F10_斤量"], 6, 8)
            s[15] = lin(r["F12_年齢"], 6, 8, 60, 100)
            s[16] = lin(r["F14_馬場"], 3, 9)
            s[17] = 4.0
            s[18], why18 = sc18(runs, cfg["venue"], cfg["dist"], cfg["repeat"])
            s[19], why19 = sc19(runs)
            s[20] = 3.0
            raw = round(min(170.0, sum(s.values())), 1)
            adj = (emap.get(nm) or {}).get("adj", 0.0)
            y = ymap.get(nm) or {}
            table.append({"name": nm, "waku": r["枠"], "uma": r["馬番"], "style": style, "jockey": jk,
                          "pop": y.get("pop"), "odds": y.get("odds"), "sogo": r["総合指数"],
                          "sc": {k: round(v, 1) for k, v in s.items()}, "raw170": raw, "ens_adj": adj,
                          "final170": round(raw + adj, 1), "oikiri": oik.get(nm, "C"),
                          "why": {"sc12": why12, "sc18": why18, "sc19": why19, "sc6": BAD_SIRE[race].get(nm, "")}})
        table.sort(key=lambda x: -x["final170"])
        out[race] = table
        print(f"\n### {race}（{cfg['venue']}芝{cfg['dist']}m・{len(table)}頭）  最終=20因子素点＋合算補正")
        print(" 順 枠番 馬名             脚質 追切 素点   補正  最終   総合指数 予想人気(単勝) | sc7枠 sc9 sc12前走 sc18 sc19格 | 根拠")
        for i, x in enumerate(table, 1):
            sc = x["sc"]
            print(f" {i:>2} {x['waku']}-{x['uma']:>2} {x['name']:<12} {x['style']:<2} {x['oikiri']} {x['raw170']:>6} {x['ens_adj']:+5.1f} {x['final170']:>6} {x['sogo']:>6}  {x['pop']}人({x['odds']}) "
                  f"| {sc[7]} {sc[9]} {sc[12]} {sc[18]} {sc[19]} | 前走:{x['why']['sc12']} / {x['why']['sc18']} / 格:{x['why']['sc19']}"
                  + (f" / 血統減点:{x['why']['sc6']}" if x['why']['sc6'] else ""))
    json.dump(out, open(RES / "score20_20260911.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nsaved research/score20_20260911.json")


if __name__ == "__main__":
    main()
