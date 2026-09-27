# -*- coding: utf-8 -*-
"""
style_forecast_audit.py — レース前の脚質予測はどこまで当たるか（2026-09-27）
=================================================================================
context_audit.py で、レース前records の『脚質』と実際の位置取りの一致率が **27.6%**（4分類・偶然25%）
と判明した。脚質を使う層（L1コース実測・L2当日・L3前日・sc[8]）は全部この予測の上に立っているので、
予測が当たらなければ層が効かないのは当然になる。

ここでは蓄積DB（race_results.json・29,627頭に実際の脚質あり）だけで、
「その馬の **それより前の** 出走の実際の脚質」から今回の脚質を予測し、一致率を測る。
リークなし（自分より前の日付の出走だけ使う）。
予測方式:
  A. 直近1走の脚質
  B. 直近3走の多数決（同数は直近優先）
  C. 直近5走の多数決
  D. 直近3走の 1角位置/頭数 の平均 → 4分位で分類（コーナー通過から）
  E. D に「距離が変わったら先行寄りにずらす」等は入れない（まず素の精度）
使い方: python style_forecast_audit.py
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
STYLES = ("逃げ", "先行", "差し", "追込")


def corner1_ratio(r):
    """1角（無ければ最初のコーナー）の位置 / 頭数。0=先頭 1=最後方"""
    s = str(r.get("コーナー通過") or "")
    parts = [p for p in s.split("-") if p.isdigit()]
    n = r.get("頭数")
    try:
        n = int(float(n))
    except (TypeError, ValueError):
        n = None
    if not parts or not n or n < 2:
        return None
    return (int(parts[0]) - 1) / (n - 1)


# 馬ごとに時系列
by_horse = collections.defaultdict(list)
for r in rows:
    if r.get("脚質") in STYLES and r.get("馬名") and r.get("date"):
        by_horse[r["馬名"]].append(r)
for v in by_horse.values():
    v.sort(key=lambda r: (r["date"], r["競馬場"], int(float(r["R"]))))

# 頭数が無い行のために、レースの頭数を数える
field = collections.Counter((r["date"], r["競馬場"], int(float(r["R"]))) for r in rows)
for r in rows:
    r.setdefault("頭数", field[(r["date"], r["競馬場"], int(float(r["R"])))])


def majority(hist):
    c = collections.Counter(h["脚質"] for h in hist)
    top = max(c.values())
    cands = [s for s, n in c.items() if n == top]
    for h in reversed(hist):          # 同数なら直近
        if h["脚質"] in cands:
            return h["脚質"]


def by_corner(hist):
    xs = [corner1_ratio(h) for h in hist]
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    m = sum(xs) / len(xs)
    return "逃げ" if m < 0.12 else "先行" if m < 0.40 else "差し" if m < 0.72 else "追込"


methods = {"A 直近1走": lambda h: h[-1]["脚質"], "B 直近3走多数決": lambda h: majority(h[-3:]),
           "C 直近5走多数決": lambda h: majority(h[-5:]), "D 直近3走の1角位置": lambda h: by_corner(h[-3:]),
           "D5 直近5走の1角位置": lambda h: by_corner(h[-5:])}
hit = {m: [0, 0] for m in methods}
conf = {m: collections.Counter() for m in methods}
n_eval = 0
for name, hist in by_horse.items():
    for i in range(1, len(hist)):
        prev, cur = hist[:i], hist[i]
        n_eval += 1
        for m, fn in methods.items():
            pred = fn(prev)
            if pred is None:
                continue
            hit[m][0] += 1
            hit[m][1] += pred == cur["脚質"]
            conf[m][(pred, cur["脚質"])] += 1

base = collections.Counter(r["脚質"] for r in rows if r.get("脚質") in STYLES)
tot = sum(base.values())
print(f"■ 評価対象 {n_eval:,}頭・走（過去走が1回以上ある出走）／ 実際の脚質分布: "
      + " ".join(f"{s}{base[s]/tot*100:.0f}%" for s in STYLES))
print(f"   基準線: 常に最多クラス（{base.most_common(1)[0][0]}）と答える = {base.most_common(1)[0][1]/tot*100:.1f}%\n")
print(f"{'方式':<20}{'n':>8}{'一致率':>9}   隣接1段階以内")
for m in methods:
    n, ok = hit[m]
    if not n:
        continue
    adj = sum(v for (p, a), v in conf[m].items() if abs(STYLES.index(p) - STYLES.index(a)) <= 1)
    print(f"{m:<20}{n:>8}{ok/n*100:>8.1f}%   {adj/n*100:5.1f}%")

# 逃げ馬の予測だけ切り出す（sc[8]・ペース想定で最も効く）
print("\n■ 『逃げ』と予測した馬が実際に逃げた割合（方式別）")
for m in methods:
    c = conf[m]
    pred_nige = sum(v for (p, a), v in c.items() if p == "逃げ")
    ok = c[("逃げ", "逃げ")]
    front = sum(v for (p, a), v in c.items() if p == "逃げ" and a in ("逃げ", "先行"))
    if pred_nige:
        print(f"  {m:<20} 逃げ予測{pred_nige:>6}頭 → 実際に逃げ {ok/pred_nige*100:5.1f}% ／ 逃げor先行 {front/pred_nige*100:5.1f}%")

print("\n■ recordsの想定脚質（context_auditで27.6%）と比べ、どの方式が上か。上回る方式があれば collect_weekend_bigdata の脚質をそれに置き換える")
