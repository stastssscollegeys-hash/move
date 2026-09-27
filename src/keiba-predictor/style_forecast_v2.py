# -*- coding: utf-8 -*-
"""
style_forecast_v2.py — 想定脚質の精度を上げる（2026-09-27）
==============================================================
style_forecast_audit.py の結果: 直近5走多数決 41.9%／「常に追込」38.7%／recordsの脚質 27.6%。
脚質を使う層（sc[8]・文脈層）の効きはこの予測精度が上限になるので、ここを上げる。

試す方式（すべて「その馬のそれより前の出走」だけを使う＝リークなし）
  M0 直近5走多数決（現行・基準）
  M1 直近5走の 1角位置/頭数 の加重平均（直近ほど重い）→ 4分位
  M2 M1 ＋ 最終コーナー位置も混ぜる（前半と後半の位置の平均）
  M3 M1 の連続値を、今回の 頭数・距離変化 で補正
       ・頭数が多いほど同じ「位置比」でも後ろになる → 比率で吸収済み
       ・距離短縮（-200m以上）は前に行きにくい、延長は前に行きやすい → ±0.05
  M4 M3 の分類しきい値を、実際の脚質分布（逃15/先17/差29/追39%）に合わせて最適化
  M5 「前（逃げ+先行）／後（差し+追込）」の2分類（層に使うなら実はこれで足りる）

評価: 4分類一致率／隣接1段階以内／前後2分類一致率／「逃げ」予測の精度。
使い方: python style_forecast_v2.py
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
STYLES = ("逃げ", "先行", "差し", "追込")
FRONT = {"逃げ", "先行"}


def meters(r):
    s = str(r.get("距離") or "")
    n = "".join(c for c in s if c.isdigit())
    return int(n) if n else None


field = collections.Counter((r["date"], r["競馬場"], int(float(r["R"]))) for r in rows)
for r in rows:
    r["_n"] = field[(r["date"], r["競馬場"], int(float(r["R"])))]


def pos_ratio(r, which="first"):
    parts = [p for p in str(r.get("コーナー通過") or "").split("-") if p.isdigit()]
    n = r["_n"]
    if not parts or n < 2:
        return None
    p = int(parts[0]) if which == "first" else int(parts[-1])
    return (p - 1) / (n - 1)


by_horse = collections.defaultdict(list)
for r in rows:
    if r.get("脚質") in STYLES and r.get("馬名") and r.get("date"):
        by_horse[r["馬名"]].append(r)
for v in by_horse.values():
    v.sort(key=lambda r: (r["date"], r["競馬場"], int(float(r["R"]))))

W = [0.15, 0.2, 0.25, 0.4, 0.5][::-1]      # 直近ほど重い（末尾が直近になるよう後で反転）


def wavg(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    ws = [0.5, 0.4, 0.25, 0.2, 0.15][:len(vals)][::-1]   # vals は古→新
    return sum(v * w for v, w in zip(vals, ws)) / sum(ws)


def majority(hist):
    c = collections.Counter(h["脚質"] for h in hist)
    top = max(c.values())
    cands = {s for s, n in c.items() if n == top}
    for h in reversed(hist):
        if h["脚質"] in cands:
            return h["脚質"]


def classify(x, th=(0.12, 0.40, 0.72)):
    return "逃げ" if x < th[0] else "先行" if x < th[1] else "差し" if x < th[2] else "追込"


def m1(prev, cur):
    return wavg([pos_ratio(h) for h in prev[-5:]])


def m2(prev, cur):
    a = wavg([pos_ratio(h) for h in prev[-5:]])
    b = wavg([pos_ratio(h, "last") for h in prev[-5:]])
    if a is None:
        return None
    return a if b is None else (a * 0.6 + b * 0.4)


def m3(prev, cur):
    x = m1(prev, cur)
    if x is None:
        return None
    dm, pm = meters(cur), meters(prev[-1])
    if dm and pm:
        if dm - pm <= -200:
            x += 0.05           # 短縮: 前に行きにくい
        elif dm - pm >= 200:
            x -= 0.05           # 延長: 前に行きやすい
    return min(1.0, max(0.0, x))


# 評価データ（過去走あり）
samples = []
for name, hist in by_horse.items():
    for i in range(1, len(hist)):
        samples.append((hist[:i], hist[i]))
print(f"■ 評価 {len(samples):,}頭・走（実際の脚質分布: "
      + " ".join(f"{s}{sum(1 for _,c in samples if c['脚質']==s)/len(samples)*100:.0f}%" for s in STYLES) + "）")

# M4: しきい値を分布に合わせる（連続値の分位点＝実際の脚質割合）
xs = sorted(x for x in (m3(p, c) for p, c in samples) if x is not None)
dist = collections.Counter(c["脚質"] for _, c in samples)
tot = sum(dist.values())
q1 = xs[int(len(xs) * dist["逃げ"] / tot)]
q2 = xs[int(len(xs) * (dist["逃げ"] + dist["先行"]) / tot)]
q3 = xs[int(len(xs) * (dist["逃げ"] + dist["先行"] + dist["差し"]) / tot)]
TH4 = (q1, q2, q3)
print(f"   M4 の分布合わせしきい値: 逃げ<{q1:.3f} 先行<{q2:.3f} 差し<{q3:.3f}\n")

methods = {
    "M0 直近5走多数決（現行）": lambda p, c: majority(p[-5:]),
    "M1 1角位置の加重平均": lambda p, c: (lambda x: classify(x) if x is not None else None)(m1(p, c)),
    "M2 1角+最終角の混合": lambda p, c: (lambda x: classify(x) if x is not None else None)(m2(p, c)),
    "M3 M1+距離変化補正": lambda p, c: (lambda x: classify(x) if x is not None else None)(m3(p, c)),
    "M4 M3+分布合わせ閾値": lambda p, c: (lambda x: classify(x, TH4) if x is not None else None)(m3(p, c)),
}
print(f"{'方式':<24}{'n':>7}{'4分類一致':>9}{'隣接以内':>9}{'前後2分類':>9}   逃げ予測→実際に逃げ／前")
for lab, fn in methods.items():
    n = ok = adj = fb = 0
    pn = pok = pfront = 0
    for prev, cur in samples:
        pred = fn(prev, cur)
        if pred is None:
            continue
        act = cur["脚質"]
        n += 1
        ok += pred == act
        adj += abs(STYLES.index(pred) - STYLES.index(act)) <= 1
        fb += (pred in FRONT) == (act in FRONT)
        if pred == "逃げ":
            pn += 1
            pok += act == "逃げ"
            pfront += act in FRONT
    print(f"{lab:<24}{n:>7}{ok/n*100:>8.1f}%{adj/n*100:>8.1f}%{fb/n*100:>8.1f}%   "
          f"{pn:>5}頭 → {pok/max(pn,1)*100:5.1f}%／{pfront/max(pn,1)*100:5.1f}%")

print("\n   基準線: 常に『追込』= 4分類38.7%／常に『後』= 前後2分類 68%前後")
print("   → 前後2分類で市場を超える情報になるかは context_audit.py（--style db）で再検定する")
