# -*- coding: utf-8 -*-
"""
course_trends.py — コース・距離・馬場・ペース・年齢・性別・斤量などの傾向を10年分で集計する（2026-10-02新規）
===========================================================================================================
「このコース・条件でどんな馬が走るか」を、**人気の偏りを除いて**測る。
  各条件の馬について 3着内の実測数 ÷ 同じ人気帯から期待される3着内数（全体の人気別3着内率から計算）。
  1.0なら人気どおり。1.10なら人気より1割多く3着内に来る。z は偶然のばらつきで割った大きさ。
  前半期間（2016〜2022）と後半期間（2023〜2026）の両方で同じ向きの条件だけを「安定」と呼ぶ。
出力: docs/keiba_course_trends.md（人が読む）／ daily_pdca/db/course_trends.json（予想・SNS文の素材）
使い方: python course_trends.py
"""
from __future__ import annotations
import collections, json, math, statistics, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history_target"
OUT_JSON = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "course_trends.json"
OUT_MD = Path(__file__).resolve().parents[2] / "docs" / "keiba_course_trends.md"
SPLIT = "20230101"


def meters(d):
    n = "".join(c for c in str(d or "") if c.isdigit())
    return int(n) if n else None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


rows = []
for f in sorted(SRC.glob("results_*.json")):
    rows += json.loads(f.read_text(encoding="utf-8"))
rows = [r for r in rows if r.get("着順int") and r.get("人気")]
by_race = collections.defaultdict(list)
for r in rows:
    by_race[(r["date"], r["競馬場"], r["R"])].append(r)

# 人気別の3着内率（全体）
pr = collections.defaultdict(lambda: [0, 0])
for r in rows:
    p = min(int(r["人気"]), 14)
    pr[p][0] += 1
    pr[p][1] += r["着順int"] <= 3
EXP = {p: v[1] / v[0] for p, v in pr.items()}

# 属性づけ
for key, hs in by_race.items():
    n = len(hs)
    kins = [r["斤量_kg"] for r in hs if r.get("斤量_kg")]
    ka = statistics.mean(kins) if kins else None
    for r in hs:
        r["_e"] = EXP[min(int(r["人気"]), 14)]
        r["_hit"] = r["着順int"] <= 3
        r["_win"] = r["着順int"] == 1
        m = meters(r["距離"])
        r["_surf"], r["_m"] = r["距離"][:1], m
        r["_band"] = "短距離(〜1300)" if m <= 1300 else "マイル(1400〜1600)" if m <= 1600 else "中距離(1700〜2200)" if m <= 2200 else "長距離(2300〜)"
        r["_course"] = f"{r['競馬場']}{r['距離']}"
        r["_baba"] = "良" if r["馬場状態"] == "良" else "稍重" if r["馬場状態"] == "稍重" else "重・不良"
        r["_style"] = r.get("脚質") or "?"
        w = r.get("枠")
        r["_waku"] = "内(1-3枠)" if w and w <= 3 else "中(4-5枠)" if w and w <= 5 else "外(6-8枠)" if w else "?"
        sa = str(r.get("性齢") or "")
        r["_sex"] = {"牡": "牡", "牝": "牝", "セ": "セ"}.get(sa[:1], "?")
        try:
            a = int(sa[1:])
        except ValueError:
            a = None
        r["_age"] = "?" if a is None else "2歳" if a == 2 else "3歳" if a == 3 else "4歳" if a == 4 else "5歳" if a == 5 else "6歳" if a == 6 else "7歳以上"
        kd = (r["斤量_kg"] - ka) if (r.get("斤量_kg") and ka) else 0.0
        r["_kin"] = "軽い(平均-1.5kg以下)" if kd <= -1.5 else "重い(平均+1.5kg以上)" if kd >= 1.5 else "平均的"
        wd = None
        import re
        mm = re.search(r"\(([+-]?\d+)\)", str(r.get("馬体重") or ""))
        if mm:
            wd = int(mm.group(1))
        r["_wt"] = "?" if wd is None else "10kg以上減" if wd <= -10 else "10kg以上増" if wd >= 10 else "増減小"
        t = r["条件"]
        r["_class"] = ("G1" if "G1" in t else "G2" if "G2" in t else "G3" if "G3" in t else "新馬" if "新馬" in t else "未勝利" if "未勝利" in t else
                       "1勝" if "1勝" in t else "2勝" if "2勝" in t else "3勝" if "3勝" in t else "オープン/L" if ("オープン" in t or "(L)" in t) else "他")
        f3, b3 = r.get("前3F_レース"), r.get("後3F_レース")
        r["_pace"] = "?" if not (f3 and b3) else "ハイ(前半が0.6秒以上速い)" if f3 - b3 <= -0.6 else "スロー(後半が0.6秒以上速い)" if f3 - b3 >= 0.6 else "平均"


def cell(sub):
    n = len(sub)
    obs = sum(r["_hit"] for r in sub)
    exp = sum(r["_e"] for r in sub)
    var = sum(r["_e"] * (1 - r["_e"]) for r in sub)
    z = (obs - exp) / math.sqrt(var) if var > 0 else 0.0
    return dict(n=n, obs=obs, exp=round(exp, 1), ratio=round(obs / exp, 3) if exp else None, z=round(z, 2),
                win=round(sum(r["_win"] for r in sub) / n * 100, 1) if n else None)


def dim_table(sub_rows, dim):
    g = collections.defaultdict(list)
    for r in sub_rows:
        g[r[dim]].append(r)
    return {k: cell(v) for k, v in g.items() if k != "?"}


def stable(sub_rows, dim, min_n=400):
    """全体＋前半・後半で同じ向きに出た条件だけ返す"""
    a = [r for r in sub_rows if r["date"] < SPLIT]
    b = [r for r in sub_rows if r["date"] >= SPLIT]
    full, ta, tb = dim_table(sub_rows, dim), dim_table(a, dim), dim_table(b, dim)
    out = {}
    for k, c in full.items():
        if c["n"] < min_n or abs(c["z"]) < 2.0:
            continue
        ra, rb = ta.get(k), tb.get(k)
        same = bool(ra and rb and ra["n"] >= 100 and rb["n"] >= 100 and (ra["ratio"] - 1) * (rb["ratio"] - 1) > 0 and (c["ratio"] - 1) * (ra["ratio"] - 1) > 0)
        out[k] = dict(c, 前半=ra["ratio"] if ra else None, 後半=rb["ratio"] if rb else None, stable=same)
    return out


DIMS = [("_style", "脚質"), ("_waku", "枠"), ("_age", "年齢"), ("_sex", "性別"), ("_kin", "斤量"), ("_wt", "馬体重の増減"), ("_class", "クラス"), ("_baba", "馬場"), ("_pace", "ペース")]
result = {"generated": "2026-10-02", "span": f"{min(r['date'] for r in rows)}〜{max(r['date'] for r in rows)}", "n_rows": len(rows), "global": {}, "course": {}, "pace": {}, "lap": {}}
md = [f"# 競馬 傾向分析（コース・距離・馬場・ペース・年齢・斤量）\n",
      f"対象: {result['span']}・{len(by_race):,}レース・{len(rows):,}頭（TARGET frontier JV 由来の10年分）。",
      "指標は「3着内の実測÷人気から期待される3着内」。1.00なら人気どおり、1.10なら人気より1割多く3着内に来る。人気の偏りは除いてある。",
      "**安定**＝前半（〜2022）と後半（2023〜）の両方で同じ向きに出た条件。安定でないものは偶然の可能性が高いので予想の根拠にしない。\n"]

# ── 全体（距離帯別に、脚質・枠・年齢・性別・斤量…）──
md.append("## 1. 距離帯ごとの傾向（芝・ダート別）\n")
for surf in ("芝", "ダ"):
    for band in ("短距離(〜1300)", "マイル(1400〜1600)", "中距離(1700〜2200)", "長距離(2300〜)"):
        sub = [r for r in rows if r["_surf"] == surf and r["_band"] == band]
        if len(sub) < 3000:
            continue
        lines = []
        for dim, label in DIMS:
            for k, c in stable(sub, dim, 1500).items():
                if c["stable"]:
                    lines.append((label, k, c))
        result["global"][f"{surf}|{band}"] = {f"{l}|{k}": c for l, k, c in lines}
        md.append(f"### {surf}・{band}（{len(sub):,}頭）")
        if lines:
            md.append("| 項目 | 条件 | 頭数 | 比 | z | 前半 | 後半 | 勝率 |\n|---|---|---|---|---|---|---|---|")
            for l, k, c in sorted(lines, key=lambda x: -abs(x[2]["z"])):
                md.append(f"| {l} | {k} | {c['n']:,} | {c['ratio']:.2f} | {c['z']:+.1f} | {c['前半']:.2f} | {c['後半']:.2f} | {c['win']}% |")
        else:
            md.append("安定して人気から外れる傾向はなし。")
        md.append("")

# ── コース別 ──
md.append("## 2. コース別（開催場×芝ダ×距離）の傾向\n")
courses = collections.defaultdict(list)
for r in rows:
    courses[r["_course"]].append(r)
for name, sub in sorted(courses.items(), key=lambda kv: -len(kv[1])):
    if len(sub) < 4000:
        continue
    lines = []
    for dim, label in DIMS:
        if dim in ("_class",):
            continue
        for k, c in stable(sub, dim, 500).items():
            if c["stable"]:
                lines.append((label, k, c))
    races = len({(r["date"], r["R"]) for r in sub})
    f3 = [r["前3F_レース"] - r["後3F_レース"] for r in sub if r.get("前3F_レース") and r.get("後3F_レース")]
    laps = [r["ラップ"] for r in sub if r.get("ラップ")]
    L = max(set(len(x) for x in laps), key=[len(x) for x in laps].count) if laps else 0
    avg_lap = [round(statistics.mean(x[i] for x in laps if len(x) == L), 2) for i in range(L)] if L else []
    result["course"][name] = {"races": races, "pace_diff_mean": round(statistics.mean(f3), 2) if f3 else None,
                              "lap_mean": avg_lap, "stable": {f"{l}|{k}": c for l, k, c in lines}}
    md.append(f"### {name}（{races:,}レース・{len(sub):,}頭／前3F−後3Fの平均 {statistics.mean(f3):+.2f}秒・ラップ平均 {avg_lap}）")
    if lines:
        md.append("| 項目 | 条件 | 頭数 | 比 | z | 前半 | 後半 |\n|---|---|---|---|---|---|---|")
        for l, k, c in sorted(lines, key=lambda x: -abs(x[2]["z"]))[:10]:
            md.append(f"| {l} | {k} | {c['n']:,} | {c['ratio']:.2f} | {c['z']:+.1f} | {c['前半']:.2f} | {c['後半']:.2f} |")
    else:
        md.append("安定した傾向なし。")
    md.append("")

# ── ペース ──
md.append("## 3. ペースごとの脚質の有利不利（全コース）\n")
md.append("| 距離帯 | ペース | 脚質 | 頭数 | 比 | z |\n|---|---|---|---|---|---|")
for band in ("短距離(〜1300)", "マイル(1400〜1600)", "中距離(1700〜2200)", "長距離(2300〜)"):
    for pace in ("ハイ(前半が0.6秒以上速い)", "平均", "スロー(後半が0.6秒以上速い)"):
        for st in ("逃げ", "先行", "差し", "追込"):
            sub = [r for r in rows if r["_band"] == band and r["_pace"] == pace and r["_style"] == st]
            if len(sub) >= 800:
                c = cell(sub)
                result["pace"][f"{band}|{pace}|{st}"] = c
                md.append(f"| {band} | {pace} | {st} | {c['n']:,} | {c['ratio']:.2f} | {c['z']:+.1f} |")
md.append("\n⚠ 脚質とペースは**結果から付けた**値（そのレースの通過順位とラップ）。レース前には分からない。説明・振り返り用で、そのまま予想の入力にはならない。"
          "予想に使うのは「過去走の脚質の割合」「前走のペース」など、レース前に確定している形に直したもの（ev_engine の特徴量）。\n")

# ── 年齢×距離帯、斤量の効き方 ──
md.append("## 4. 年齢・性別・斤量・馬体重の全体傾向\n")
for dim, label in (("_age", "年齢"), ("_sex", "性別"), ("_kin", "斤量"), ("_wt", "馬体重の増減"), ("_class", "クラス")):
    t = dim_table(rows, dim)
    md.append(f"**{label}**: " + " ／ ".join(f"{k} 比{c['ratio']:.2f}（n={c['n']:,}）" for k, c in sorted(t.items(), key=lambda kv: -kv[1]["n"])))
md.append("")
OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
OUT_MD.write_text("\n".join(md), encoding="utf-8")
print(f"保存: {OUT_MD}\n保存: {OUT_JSON}\nコース数 {len(result['course'])} ／ 距離帯 {len(result['global'])}")
