# -*- coding: utf-8 -*-
"""
daybias_test.py — 前日のトラックバイアスは翌日（同じ開催の連続開催日）に続くか（2026-10-13新規・10年・リークなし）
===================================================================================================================
week_bias_test.py（週→週）の「日→日」版。測り方は同じ:
  ・競馬場 × 芝ダ × 日 ごとに「内枠（1〜3枠）」「前で運んだ馬（逃げ・先行）」の 3着内 − 人気からの期待（1頭あたり）を出す
  ・翌日（同じ開催・芝は同じ柵）の、レース前に分かる「内枠の馬」「前で運ぶ型の馬」の 3着内 − 期待 を、前日の偏りの向きで比べる
  ・前半(2016-2021)／後半(2022-2026)に分けて、同じ向きかを確認
結果（2026-10-13・docs/keiba_weekend_review_20261010-12.md）:
  内枠の馬は前日の内外の有利不利を翌日に引きずる（芝: 前日内有利→1.04〜1.07倍／前日内不利→0.95〜1.00倍、差 +7〜9pt・前半後半とも同じ向き）。
  前で運ぶ型は芝で向きが安定しない（前半+4.7pt／後半-5.2pt）＝使わない。
使い方: python daybias_test.py     # 約3分・メモリ約2〜3GB（他のPython処理と同時に回さない）
"""
from __future__ import annotations
import collections, datetime, glob, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import predict_day as P
import target_import as T

E.SOURCE = P.HIST


def meta():
    """(日付, 場, R) → (回, 日目, 柵)  week_bias_test.meta と同じ"""
    out = {}
    for y in range(2016, 2027):
        for f in glob.glob(f"C:/TFJV/SE_DATA/{y}/SR*.DAT"):
            for r in T.records(Path(f), 1272):
                x = T.parse_ra(r)
                if x and x["R"]:
                    out[(x["date"], x["venue"], x["R"])] = (T.seg(r, 22, 2), T.seg(r, 24, 2), r[709:710].decode("ascii", "ignore").strip())
    return out


def ratio(sub):
    ex = sum(o["e"] for o in sub); rs = sum(o["res"] for o in sub); var = sum(o["e"] * (1 - o["e"]) for o in sub)
    return (ex + rs) / ex, rs / math.sqrt(var), len(sub)


def main():
    M = meta()
    rows = [r for r in E.load_rows() if r.get("着順int") and r.get("人気")]
    pr = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        p = min(int(r["人気"]), 14); pr[p][0] += 1; pr[p][1] += r["着順int"] <= 3
    EXP = {p: v[1] / v[0] for p, v in pr.items()}
    by_h = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: (r["date"], r["R"])):
        by_h[r.get("horse_id") or r["馬名"]].append(r)
    pre = {}
    for rs in by_h.values():
        for i, r in enumerate(rs):
            past = [x for x in rs[max(0, i - 5):i] if x.get("脚質")]
            if len(past) >= 2:
                sh = sum(x["脚質"] in ("逃げ", "先行") for x in past) / len(past)
                pre[id(r)] = "前" if sh >= 0.6 else "後" if sh <= 0.2 else "中"
    day = collections.defaultdict(list)
    for r in rows:
        day[(r["競馬場"], r["距離"][:1], r["date"])].append(r)
    stat = {}
    for k, rs in day.items():
        inn = [r for r in rs if r.get("枠") and r["枠"] <= 3]
        fr = [r for r in rs if r.get("脚質") in ("逃げ", "先行")]
        if len(inn) < 12 or len(fr) < 12:
            continue
        m = [x for x in (M.get((r["date"], r["競馬場"], r["R"])) for r in rs) if x]
        stat[k] = dict(W=sum((r["着順int"] <= 3) - EXP[min(int(r["人気"]), 14)] for r in inn) / len(inn),
                       B=sum((r["着順int"] <= 3) - EXP[min(int(r["人気"]), 14)] for r in fr) / len(fr),
                       kai=collections.Counter(x[0] for x in m).most_common(1)[0][0] if m else "",
                       rail=collections.Counter(x[2] for x in m).most_common(1)[0][0] if m else "")
    obs = []
    for (v, sf, d), cur in stat.items():
        nxt = (datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])) + datetime.timedelta(days=1)).strftime("%Y%m%d")
        nx = stat.get((v, sf, nxt))
        if not nx or not cur["kai"] or cur["kai"] != nx["kai"]:
            continue
        same = (sf != "芝") or (cur["rail"] == nx["rail"])
        for r in day[(v, sf, nxt)]:
            e = EXP[min(int(r["人気"]), 14)]
            obs.append(dict(sf=sf, same=same, Wp=cur["W"], Bp=cur["B"], inner=bool(r.get("枠") and r["枠"] <= 3),
                            style=pre.get(id(r)), res=(r["着順int"] <= 3) - e, e=e, year=r["date"][:4]))
    print(f"■ 前日→翌日（同じ開催・連続日）判定頭数 {len(obs):,}")
    halves = (("全期間", [str(y) for y in range(2016, 2027)]), ("前半", [str(y) for y in range(2016, 2022)]), ("後半", [str(y) for y in range(2022, 2027)]))
    for sf in ("芝", "ダ"):
        print(f"\n■ {sf}（同じ柵）")
        for lab, yrs in halves:
            def sel(f, key, hi=True):
                return [o for o in obs if o["sf"] == sf and o["same"] and f(o) and o["year"] in yrs and ((o[key] >= 0.06) if hi else (o[key] <= -0.06))]
            hi, lo = sel(lambda o: o["inner"], "Wp", True), sel(lambda o: o["inner"], "Wp", False)
            if len(hi) >= 300 and len(lo) >= 300:
                a, b = ratio(hi), ratio(lo)
                print(f"  内枠の馬 {lab}: 前日内有利→{a[0]:.3f}(n={a[2]:,},z={a[1]:+.2f}) ／ 前日内不利→{b[0]:.3f}(n={b[2]:,},z={b[1]:+.2f}) ／ 差 {(a[0] - b[0]) * 100:+.1f}pt")
            hi, lo = sel(lambda o: o["style"] == "前", "Bp", True), sel(lambda o: o["style"] == "前", "Bp", False)
            if len(hi) >= 300 and len(lo) >= 300:
                a, b = ratio(hi), ratio(lo)
                print(f"  前で運ぶ型 {lab}: 前日前残り→{a[0]:.3f}(n={a[2]:,}) ／ 前日前が止まる→{b[0]:.3f}(n={b[2]:,}) ／ 差 {(a[0] - b[0]) * 100:+.1f}pt")


if __name__ == "__main__":
    main()
