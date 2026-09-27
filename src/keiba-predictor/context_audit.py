# -*- coding: utf-8 -*-
"""
context_audit.py — 文脈層（L1〜L4）は市場に無い情報か（2026-09-27）
====================================================================
context_layer の各層について、**同じ人気帯の中で** 層が「有利」とした馬が他より走るかを測る。
層は「そのレースより前の情報」だけで作るので、蓄積DB全件（結果リークなし）で検定できる。
指数を使わないので、レース前records（523R）より桁違いに多い ~2,800レース で判定できる。

判定（factor_audit_v2 / pdca_rounds と同じ両関門）
  ① 全体で、同じ人気帯の期待3着内数に対する実測が |z| >= 2
  ② 前半／後半に割っても同じ向きで、後半の |z| >= 1.5
使い方: python context_audit.py [--thr 1.10]
"""
from __future__ import annotations
import argparse, collections, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from context_layer import ContextDB, multipliers, _fin

ap = argparse.ArgumentParser()
ap.add_argument("--thr", type=float, default=1.10, help="この倍率以上を『有利』、1/thr以下を『不利』とみなす")
ap.add_argument("--actual-style", action="store_true",
                help="🚫比較用: 蓄積DBの脚質（＝そのレースで実際に取った位置＝結果）を使う。リークするので判定には使わない")
ap.add_argument("--style", choices=("db", "records"), default="db",
                help="馬の想定脚質の出し方。db=蓄積DBの直近5走多数決（一致率41.9%・全件で検定可）／records=レース前recordsの脚質（27.6%・523Rのみ）")
a = ap.parse_args()

cdb = ContextDB()

# ── 馬の脚質は「レース前の想定」を使う（結果リーク防止）────────────────────────────
# 蓄積DBの『脚質』はコーナー通過から事後に付けた実際の位置取り。これで「短距離の逃げは走る」を測ると
# 「逃げられた馬が走った」という結果の再確認になる（実測: z=+15.8 が出た）。
# レース前records（週末ビッグデータ_*_records.json・素性チェック済み）の『脚質』は過去走からの想定なので使える。
import datetime, glob, os
BASE_DIR = Path.home() / "Desktop" / "競馬予想レポート"
pre_style = {}
for f in sorted(BASE_DIR.glob("**/週末ビッグデータ_*_records.json")):
    try:
        import json as _j
        rs = _j.load(open(f, encoding="utf-8")).get("records", [])
    except Exception:
        continue
    if not rs:
        continue
    mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).date()
    last = max(r["date"] for r in rs)
    if mtime > datetime.date(int(last[:4]), int(last[4:6]), int(last[6:8])):
        continue                                    # レース後に作られた records は除外
    for r in rs:
        try:
            pre_style[(r["date"], r["競馬場"], int(float(r["R"])), int(float(r["馬番"])))] = r.get("脚質")
        except (TypeError, ValueError, KeyError):
            pass

rows = []
agree = tot = 0
for r in cdb.rows:
    if not (_fin(r) and r.get("脚質") and r.get("date")):
        continue
    if a.actual_style:
        rows.append(r)
        continue
    if a.style == "db":
        ps = cdb.style_forecast(r.get("馬名"), r["date"])      # 自分より前の出走だけ＝リークなし
    else:
        try:
            k = (r["date"], r["競馬場"], int(float(r["R"])), int(float(r["馬番"])))
        except (TypeError, ValueError):
            continue
        ps = pre_style.get(k)
    if ps not in ("逃げ", "先行", "差し", "追込"):
        continue
    tot += 1
    agree += ps == r["脚質"]
    r = dict(r)
    r["脚質_実際"] = r["脚質"]
    r["脚質"] = ps                                  # 以降の判定はレース前の想定脚質で行う
    rows.append(r)
if not a.actual_style:
    src = "蓄積DBの直近5走多数決" if a.style == "db" else "レース前records"
    print(f"■ 馬の脚質＝レース前の想定（{src}）を使用。想定と実際の一致率 {agree/max(tot,1)*100:.1f}%（{tot:,}頭）")
else:
    print("■ 🚫 比較用: 蓄積DBの実際の脚質を使用（結果リークあり・判定には使わない）")
rows.sort(key=lambda r: (r["date"], r["競馬場"], int(float(r["R"]))))
half = rows[len(rows) // 2]["date"]


def pop(r):
    try:
        return min(int(float(r.get("人気"))), 18)
    except (TypeError, ValueError):
        return None


base = collections.defaultdict(lambda: [0, 0])
for r in rows:
    p = pop(r)
    if p:
        base[p][0] += 1
        base[p][1] += 1 if _fin(r) <= 3 else 0
BASE = {k: v[1] / v[0] for k, v in base.items()}

# レースごとに文脈を1回計算して、各馬の層別倍率を付ける
races = collections.defaultdict(list)
for r in rows:
    races[(r["date"], r["競馬場"], int(float(r["R"])))].append(r)
print(f"■ 対象 {len(races):,}レース / {len(rows):,}頭（前半・後半の境 {half}）")

tagged = []          # (r, {L1: m, L2: m, L3: m, ALL: m})
for (d, v, R), rs in races.items():
    d0 = rs[0].get("距離") or ""
    surf = "芝" if d0.startswith("芝") else ("ダ" if d0.startswith("ダ") else None)
    num = "".join(c for c in d0 if c.isdigit())
    ctx = cdb.context(d, v, R, surface=surf, meters=int(num) if num else None, baba=rs[0].get("馬場状態"))
    for r in rs:
        if not pop(r):
            continue
        ms = {}
        for L in ("L1", "L2", "L3"):
            ms[L] = multipliers(ctx, r.get("脚質"), r.get("枠"), layers=(L,))["total"]
        ms["L2+L3"] = ms["L2"] * ms["L3"]
        ms["ALL"] = ms["L1"] * ms["L2"] * ms["L3"]
        ms["_n_done"] = ctx["n_done"]
        tagged.append((r, ms))


def test(sel, label):
    """sel: 馬のリスト。同じ人気帯の期待値と比べる"""
    def z_of(sub):
        if not sub:
            return None
        exp = sum(BASE[pop(r)] for r in sub)
        var = sum(BASE[pop(r)] * (1 - BASE[pop(r)]) for r in sub)
        obs = sum(1 for r in sub if _fin(r) <= 3)
        return ((obs - exp) / math.sqrt(var) if var > 0 else 0, (obs - exp) / len(sub) * 100, len(sub), obs / len(sub) * 100)
    allz = z_of(sel)
    h1 = z_of([r for r in sel if r["date"] < half])
    h2 = z_of([r for r in sel if r["date"] >= half])
    if not (allz and h1 and h2) or allz[2] < 200:
        print(f"  {label:<28} n={allz[2] if allz else 0:>6}  （少なすぎ）")
        return False
    ok = abs(allz[0]) >= 2 and (allz[0] * h2[0] > 0) and abs(h2[0]) >= 1.5 and (h1[0] * h2[0] > 0)
    mark = "★両関門通過" if ok else ("（全体のみ）" if abs(allz[0]) >= 2 else "")
    print(f"  {label:<28} n={allz[2]:>6} 3着内{allz[3]:5.1f}% 超過{allz[1]:+5.2f}pt z={allz[0]:+5.2f} ｜前半z{h1[0]:+5.2f} 後半z{h2[0]:+5.2f}  {mark}")
    return ok


thr = a.thr
passed = []
for L in ("L1", "L2", "L3", "L2+L3", "ALL"):
    print(f"\n■ {L}  （倍率 ≥{thr} を有利、≤{1/thr:.3f} を不利。人気で条件付け）")
    fav = [r for r, m in tagged if m[L] >= thr]
    dis = [r for r, m in tagged if m[L] <= 1 / thr]
    if test(fav, f"{L} 有利とした馬"):
        passed.append((L, "up"))
    if test(dis, f"{L} 不利とした馬"):
        passed.append((L, "down"))
    if L == "L2":
        # 当日層は「何レース終わってから」で情報量が違う
        for lo, hi, lab in ((1, 3, "1〜3R終了後"), (4, 7, "4〜7R終了後"), (8, 11, "8R以降")):
            f2 = [r for r, m in tagged if m[L] >= thr and lo <= m["_n_done"] <= hi]
            test(f2, f"  L2有利・{lab}")

# 倍率の分布（どれくらい動くのか）
import statistics as st
for L in ("L1", "L2", "L3"):
    xs = sorted(m[L] for _, m in tagged)
    print(f"\n{L} 倍率分布: 5%点{xs[int(len(xs)*.05)]:.3f} 中央{st.median(xs):.3f} 95%点{xs[int(len(xs)*.95)]:.3f}"
          f"  ／ ≥{thr}: {sum(1 for x in xs if x>=thr)/len(xs)*100:.1f}%  ≤{1/thr:.3f}: {sum(1 for x in xs if x<=1/thr)/len(xs)*100:.1f}%")

# 監査結果を台帳に追記（データが増えるごとに再実行し、通った層だけ db/context_layers.json で有効化する）
import datetime as _dt, json as _json
led = DB / "context_audit.json"
hist = _json.loads(led.read_text(encoding="utf-8")) if led.exists() else []
hist.append({"run": _dt.datetime.now().isoformat(timespec="minutes"), "style_source": ("actual" if a.actual_style else a.style),
             "races": len(races), "horses": len(tagged), "thr": thr, "passed": [f"{L}:{d}" for L, d in passed]})
led.write_text(_json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n台帳に追記 → {led.name}（{len(hist)}回目）")

print("\n■ 結論")
if passed:
    for L, dr in passed:
        print(f"  ★ {L} の『{'有利' if dr=='up' else '不利'}』側は市場に無い情報を持つ → prob_core に層として接続してよい（前向き台帳で追跡）")
else:
    print("  両関門を通った層なし。文脈は SNS の説明材料としては使えるが、確率には掛けない")
