# -*- coding: utf-8 -*-
"""intraday_extreme_test.py — 2026-11-08 の振り返りで出た2つの仮説を、蓄積DB（2016〜）で確かめる（2026-11-08 新設）
  A 当日・同じ場×芝ダで、それまでのレースの外枠(7-8枠)の3着内率が極端に低い（20頭以上で5%以下／10%以下）とき、
    その後のレースの外枠の馬は、単勝オッズから見込む3着内率より走らないか（A/E）・単勝回収はどうか
    同じことを内枠(1-2枠)と「逃げ・先行が極端に有利（差し追込の3着内が5%以下）」でも見る
  B 休み明け（前走から150日以上）で5番人気以内の馬は、オッズから見込む3着内率どおり走るか
期待値（E）は「単勝オッズの帯×頭数の帯」ごとの全体の3着内率。A/E が 1 なら市場は織り込み済み。
  python intraday_extreme_test.py
"""
import collections, json, math, sys
from datetime import date
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E

KEEP = ("date", "競馬場", "R", "距離", "枠", "馬番", "単勝オッズ", "着順int", "頭数", "horse_id", "脚質", "コーナー通過", "人気")


def load():
    src = Path(E.SOURCE)
    rows = []
    for f in sorted(src.glob("results_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            d = str(r.get("距離") or "")
            if d.startswith("障") or not d:
                continue
            try:
                o = float(r["単勝オッズ"]); fi = int(r["着順int"]); u = int(r["枠"])
            except (TypeError, ValueError, KeyError):
                continue
            if o <= 0 or fi <= 0:
                continue
            rows.append({k: r.get(k) for k in KEEP} | {"_o": o, "_f": fi, "_w": u, "_s": d[0]})
    return rows


def obin(o):
    for b in (2, 3, 5, 8, 12, 20, 35, 60, 100):
        if o < b:
            return b
    return 999


def nbin(n):
    return 0 if n <= 10 else 1 if n <= 14 else 2


def front(r):
    """最初のコーナーで2番手以内か（course_profile.style_of と同じ定義の簡易版）。不明は None"""
    c = str(r.get("コーナー通過") or "").split("-")[0]
    try:
        return int(c) <= 2
    except ValueError:
        return None


def ci(a, e, n):
    """A/E と、二項近似の95%区間（実数の3着内 a、期待 e、頭数 n）"""
    if e <= 0:
        return (0, 0, 0)
    p = e / n
    sd = math.sqrt(n * p * (1 - p))
    return (a / e, (a - 1.96 * sd) / e, (a + 1.96 * sd) / e)


def main():
    rows = load()
    races = collections.defaultdict(list)
    for r in rows:
        races[(r["date"], r["競馬場"], r["_s"], int(float(r["R"])))].append(r)
    # 期待値の表（オッズ帯×頭数帯の3着内率）
    tab = collections.defaultdict(lambda: [0, 0])
    for hs in races.values():
        n = len(hs)
        for h in hs:
            t = tab[(obin(h["_o"]), nbin(n))]; t[0] += 1; t[1] += h["_f"] <= 3
    exp = {k: v[1] / v[0] for k, v in tab.items()}
    print(f"レース {len(races):,} ／ 出走 {len(rows):,}")

    # A: 当日の場×芝ダごとに、レース順に積み上げ
    day = collections.defaultdict(list)
    for (d, v, s, R), hs in races.items():
        day[(d, v, s)].append((R, hs))
    cond = {"外枠5%以下": [], "外枠10%以下": [], "内枠(1-2)5%以下": [], "差し追込5%以下(前有利)": [], "対照:外枠15〜30%": []}
    for key, lst in day.items():
        lst.sort()
        og = [0, 0]; ig = [0, 0]; back = [0, 0]
        for R, hs in lst:
            n = len(hs)
            outer = [h for h in hs if h["_w"] >= 7]; inner = [h for h in hs if h["_w"] <= 2]
            notf = [h for h in hs if front(h) is False]
            if og[0] >= 20:
                rt = og[1] / og[0]
                if rt <= 0.05: cond["外枠5%以下"] += [(h, n) for h in outer]
                if rt <= 0.10: cond["外枠10%以下"] += [(h, n) for h in outer]
                if 0.15 <= rt <= 0.30: cond["対照:外枠15〜30%"] += [(h, n) for h in outer]
            if ig[0] >= 20 and ig[1] / ig[0] <= 0.05:
                cond["内枠(1-2)5%以下"] += [(h, n) for h in inner]
            if back[0] >= 20 and back[1] / back[0] <= 0.05:
                cond["差し追込5%以下(前有利)"] += [(h, n) for h in hs if front(h) is False and h["_o"] < 999]
            for h in outer: og[0] += 1; og[1] += h["_f"] <= 3
            for h in inner: ig[0] += 1; ig[1] += h["_f"] <= 3
            for h in notf: back[0] += 1; back[1] += h["_f"] <= 3
    print("\n## A 当日の極端な偏りのあと、その後のレースの該当馬（3着内のA/E・単勝回収）")
    for name, lst in cond.items():
        n = len(lst)
        if not n:
            print(name, "該当なし"); continue
        a = sum(h["_f"] <= 3 for h, _ in lst); e = sum(exp[(obin(h["_o"]), nbin(m))] for h, m in lst)
        win = sum(h["_o"] * 100 for h, _ in lst if h["_f"] == 1) / (n * 100)
        r, lo, hi = ci(a, e, n)
        pop5 = [(h, m) for h, m in lst if (h.get("人気") or 99) <= 5]
        a5 = sum(h["_f"] <= 3 for h, _ in pop5); e5 = sum(exp[(obin(h["_o"]), nbin(m))] for h, m in pop5)
        print(f"{name}: {n}頭 3着内 {a}/{e:.1f} A/E {r:.2f}［{lo:.2f}〜{hi:.2f}］ 単勝回収 {win:.0%} ／ うち5番人気以内 {len(pop5)}頭 A/E {a5 / e5 if e5 else 0:.2f}")
        for lab, f in (("2016-20", lambda h: h["date"] < "2021"), ("2021-26", lambda h: h["date"] >= "2021"), ("芝", lambda h: h["_s"] == "芝"), ("ダ", lambda h: h["_s"] == "ダ")):
            sub = [(h, m) for h, m in lst if f(h)]
            if sub:
                a2 = sum(h["_f"] <= 3 for h, _ in sub); e2 = sum(exp[(obin(h["_o"]), nbin(m))] for h, m in sub)
                print(f"    {lab}: {len(sub)}頭 A/E {ci(a2, e2, len(sub))[0]:.2f}［{ci(a2, e2, len(sub))[1]:.2f}〜{ci(a2, e2, len(sub))[2]:.2f}］")

    # B: 休み明け
    byh = collections.defaultdict(list)
    for r in rows:
        if r.get("horse_id"):
            byh[r["horse_id"]].append(r)
    grp = collections.defaultdict(list)
    for hid, lst in byh.items():
        lst.sort(key=lambda x: x["date"])
        for p, c in zip(lst, lst[1:]):
            d0 = date(int(p["date"][:4]), int(p["date"][4:6]), int(p["date"][6:]))
            d1 = date(int(c["date"][:4]), int(c["date"][4:6]), int(c["date"][6:]))
            gap = (d1 - d0).days
            pop = c.get("人気") or 99
            g = "150日以上" if gap >= 150 else "90〜149日" if gap >= 90 else "89日以内"
            grp[(g, "5番人気以内" if pop <= 5 else "6番人気以下")].append(c)
    nmap = {k: len(v) for k, v in races.items()}
    print("\n## B 休み明け×人気（3着内のA/E・単勝回収）")
    for k in sorted(grp):
        lst = grp[k]; n = len(lst)
        a = sum(h["_f"] <= 3 for h in lst)
        e = sum(exp[(obin(h["_o"]), nbin(nmap.get((h["date"], h["競馬場"], h["_s"], int(float(h["R"]))), 12)))] for h in lst)
        win = sum(h["_o"] for h in lst if h["_f"] == 1) / n
        r, lo, hi = ci(a, e, n)
        print(f"{k[0]} {k[1]}: {n:,}頭 3着内率 {a / n:.1%} A/E {r:.3f}［{lo:.3f}〜{hi:.3f}］ 単勝回収 {win:.1%}")
        if k[0] == "150日以上":
            for lab, f in (("2016-20", lambda h: h["date"] < "2021"), ("2021-26", lambda h: h["date"] >= "2021")):
                sub = [h for h in lst if f(h)]
                a2 = sum(h["_f"] <= 3 for h in sub)
                e2 = sum(exp[(obin(h["_o"]), nbin(nmap.get((h["date"], h["競馬場"], h["_s"], int(float(h["R"]))), 12)))] for h in sub)
                print(f"    {lab}: {len(sub):,}頭 A/E {ci(a2, e2, len(sub))[0]:.3f}［{ci(a2, e2, len(sub))[1]:.3f}〜{ci(a2, e2, len(sub))[2]:.3f}］")


if __name__ == "__main__":
    main()
