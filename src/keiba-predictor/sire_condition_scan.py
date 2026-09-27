# -*- coding: utf-8 -*-
"""
sire_condition_scan.py — 種牡馬 × 条件（芝ダ・距離・馬場）を両関門で検定する（2026-09-27）
==============================================================================================
2026-09-27に血統のカバー率が **100%（33,849頭）** になったので、初めてまともに検定できる。
pdca_rounds.py では種牡馬「単体」を20頭テストして**両関門通過ゼロ**だった。
メモリ [[keiba_bloodline_analysis]] の主張は「血統は買う理由でなく、条件別の不適検出に使う」。
それが完全データでも成立するかを確かめる。

両関門（factor_audit_v2 / pdca_rounds と同じ）:
  ① 全体で、同じ人気帯の平均より3着内率が有意に離れている（|z| >= 2）
  ② 前半／後半に割っても同じ向きで、後半の |z| >= 1.5
  ＝ 片方だけ良いものは偶然として捨てる

使い方: python sire_condition_scan.py [--min-n 120]
"""
from __future__ import annotations
import argparse, collections, json, math, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
rows = json.loads((DB / "race_results.json").read_text(encoding="utf-8"))

ap = argparse.ArgumentParser()
ap.add_argument("--min-n", type=int, default=120)
a = ap.parse_args()


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "")
    return int(s) if s.isdigit() else None


def pop(r):
    try:
        return int(float(r.get("人気")))
    except (TypeError, ValueError):
        return None


use = [r for r in rows if r.get("父") and fin(r) and pop(r) and r.get("date")]
use.sort(key=lambda r: r["date"])
half = use[len(use) // 2]["date"]
print(f"■ 対象 {len(use):,}頭（父100%）／前半・後半の境 {half}")

# 人気帯ごとの基準3着内率（「強い馬は人気」の再発見を避けるため必ず人気で条件付ける）
base = collections.defaultdict(lambda: [0, 0])
for r in use:
    e = base[min(pop(r), 18)]
    e[0] += 1
    e[1] += 1 if fin(r) <= 3 else 0
BASE = {k: v[1] / v[0] for k, v in base.items()}


def cond_surface(r):
    d = str(r.get("距離") or "")
    return "芝" if d.startswith("芝") else ("ダート" if d.startswith("ダ") else None)


def cond_dist(r):
    d = str(r.get("距離") or "")
    n = "".join(c for c in d if c.isdigit())
    if not n:
        return None
    m = int(n)
    return "短(〜1400)" if m <= 1400 else ("マ(1500-1800)" if m <= 1800 else "長(1900-)")


def cond_baba(r):
    s = str(r.get("馬場状態") or "")
    return "良" if s.startswith("良") else ("道悪" if s[:1] in ("稍", "重", "不") else None)


AXES = (("芝ダ", cond_surface), ("距離帯", cond_dist), ("馬場", cond_baba))

sire_n = collections.Counter(r["父"] for r in use)
targets = [s for s, n in sire_n.items() if n >= 300]
print(f"   出走300頭以上の種牡馬 {len(targets)}頭 × 条件 → 検定\n")


def zscore(sub):
    """同じ人気帯の期待値と比べたz値"""
    if not sub:
        return None
    exp = sum(BASE[min(pop(r), 18)] for r in sub)
    var = sum(BASE[min(pop(r), 18)] * (1 - BASE[min(pop(r), 18)]) for r in sub)
    obs = sum(1 for r in sub if fin(r) <= 3)
    if var <= 0:
        return None
    return (obs - exp) / math.sqrt(var), (obs - exp) / len(sub) * 100, len(sub)


res = []
for sire in targets:
    mine = [r for r in use if r["父"] == sire]
    for axis, fn in AXES:
        for val in sorted({fn(r) for r in mine} - {None}):
            sub = [r for r in mine if fn(r) == val]
            if len(sub) < a.min_n:
                continue
            allz = zscore(sub)
            h1 = zscore([r for r in sub if r["date"] < half])
            h2 = zscore([r for r in sub if r["date"] >= half])
            if not (allz and h1 and h2):
                continue
            gate1 = abs(allz[0]) >= 2.0
            gate2 = (allz[0] * h2[0] > 0) and abs(h2[0]) >= 1.5 and (h1[0] * h2[0] > 0)
            res.append((abs(allz[0]), sire, axis, val, allz, h1, h2, gate1 and gate2))

res.sort(reverse=True)
print(f"{'種牡馬':<16}{'条件':<14}{'n':>6}{'超過pt':>9}{'z':>7}{'前半z':>8}{'後半z':>8}  判定")
print("-" * 82)
pass_n = 0
for _, sire, axis, val, allz, h1, h2, ok in res[:25]:
    mark = "★両関門通過" if ok else ("（全体のみ）" if abs(allz[0]) >= 2 else "")
    pass_n += 1 if ok else 0
    print(f"{sire:<16}{val:<14}{allz[2]:>6}{allz[1]:>+8.1f}pt{allz[0]:>+7.2f}"
          f"{h1[0]:>+8.2f}{h2[0]:>+8.2f}  {mark}")

total_pass = sum(1 for r in res if r[7])
print(f"\n■ 検定した組み合わせ {len(res)}件 ／ 全体でp<0.05は {sum(1 for r in res if abs(r[4][0])>=2)}件"
      f"（偶然でも約{len(res)*0.05:.0f}件）／ **両関門を通ったのは {total_pass}件**")
if total_pass:
    print("\n  通過した組み合わせ:")
    for _, sire, axis, val, allz, h1, h2, ok in res:
        if ok:
            d = "高い" if allz[0] > 0 else "低い"
            print(f"   ★ {sire} × {val}：同じ人気帯より3着内率が{d}"
                  f"（{allz[1]:+.1f}pt・n={allz[2]}・後半z={h2[0]:+.2f}）")

    # 在サンプルの発見なので、そのまま使わず前向き台帳に事前登録する。
    # （300帯スキャンがhold-outで全滅した教訓＝[[keiba_band_scan_v73]]）
    import datetime
    led = DB / "sire_candidates.json"
    old = json.loads(led.read_text(encoding="utf-8")) if led.exists() else []
    known = {(c["sire"], c["cond"]) for c in old}
    today = datetime.date.today().strftime("%Y%m%d")
    add = 0
    for _, sire, axis, val, allz, h1, h2, ok in res:
        if ok and (sire, val) not in known:
            old.append({"sire": sire, "axis": axis, "cond": val,
                        "registered": today, "eval_from": today,
                        "in_sample": {"n": allz[2], "excess_pt": round(allz[1], 1),
                                      "z": round(allz[0], 2), "z_h1": round(h1[0], 2),
                                      "z_h2": round(h2[0], 2)},
                        "direction": "up" if allz[0] > 0 else "down",
                        "note": "在サンプルの発見。eval_from 以降のレースだけで前向き判定する"})
            add += 1
    led.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  前向き台帳に登録: 新規{add}件 / 累計{len(old)}件 → {led.name}")
    print("  ⚠ ここで残ったものは候補。eval_from 以降のレースだけで再評価するまで買う根拠にしない")
