# -*- coding: utf-8 -*-
"""index_weight_test.py — 「アスメシ独自指数」（100点）の配点を、蓄積DB（2016〜）で確かめる（2026-11-14 新設）

きっかけ（2026-11-14 ユーザー指示）: 「独自指数の配点も見直して」。指数（score.py）は ①格と近走30 ②レースの型25 ③適性25 ④脚質10 ⑤状態10 を手で決めていて、前向き検証が無かった。
ここで測れるのは DB だけで機械的に作れる部分:
  近走（格×着順・直近3走 0.5/0.3/0.2）／同コース（同じ場・同じ距離の3着内率）／距離帯（近5走の同じ芝ダ±200mの3着内率）／上がり（直近3走の上がり順位）／
  脚質（近5走の多数決。逃げ先行＝高い）／間隔（33〜146日が高い）／人気より走った度合い（直近3走の 人気−着順）
測れないもの: ②のレースごとの「前走レース名」の型、⑤の追い切り評価（どちらも手入力）。
見るもの: (1) 部品ごと: その部品が1位の馬の勝率・3着内率・単勝回収  (2) 市場を入れない条件付きロジット＝データが決める配点
          (3) 市場（単勝オッズ）を土台に部品を足したとき、どれだけ良くなるか（前半2019〜22で係数→後半2023〜で採点）
          (4) 見立ての式 p = softmax(log 市場 + c×z(指数)) の c（今は0.4）をデータで決めると幾つか
  python index_weight_test.py [--graded]   # --graded は重賞・オープンだけ
"""
import argparse, collections, json, sys
from datetime import date
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E

CLS = (("G1", 1.0), ("G2", .85), ("G3", .75), ("(L", .6), ("オープン", .6), ("3勝", .5), ("2勝", .4), ("1勝", .35), ("新馬", .5), ("未勝利", .5))
NAMES = ["近走(格×着順)", "同コース3着内率", "距離帯3着内率", "上がり順位", "脚質(前に行く)", "間隔33〜146日", "人気より走った"]


def cls(c):
    return next((v for k, v in CLS if k in c), .5)


def finp(f):
    return 1.0 if f == 1 else .8 if f == 2 else .65 if f == 3 else .45 if f <= 5 else .2 if f <= 9 else 0


def load():
    races = collections.defaultdict(list)
    for f in sorted(Path(E.SOURCE).glob("results_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            d = str(r.get("距離") or "")
            try:
                o = float(r["単勝オッズ"]); fi = int(r["着順int"]); m = int(d[1:-1])
            except (TypeError, ValueError, KeyError):
                continue
            if d.startswith("障") or o <= 0 or fi <= 0 or not r.get("horse_id"):
                continue
            ds = str(r["date"])
            races[(ds, r["競馬場"], r["R"])].append((r["horse_id"], fi, o, int(r.get("人気") or 0), r.get("後3F順位"), r.get("脚質") or "", d[0], m, r.get("条件") or "", int(r["馬番"])))
    return races


def feats(hist, dd, venue, surf, m):
    """hist: その馬の過去走（古い順）[(date, venue, surf, m, fin, pop, f3rank, style, cond)]"""
    if not hist:
        return None
    r3 = hist[::-1][:3]; w = [.5, .3, .2][:len(r3)]
    f1 = sum(a * cls(r[8]) * finp(r[4]) for a, r in zip(w, r3)) / sum(w)
    sc = [r for r in hist if r[1] == venue and r[2] == surf and r[3] == m]
    f2 = sum(r[4] <= 3 for r in sc) / len(sc) if sc else .25
    l5 = hist[-5:]
    bd = [r for r in l5 if r[2] == surf and abs(r[3] - m) <= 200]
    f3 = sum(r[4] <= 3 for r in bd) / len(bd) if bd else .2
    up = [r[6] for r in r3 if r[6]]
    f4 = (lambda a: 1.0 if a <= 3 else .6 if a <= 5 else .2)(sum(up) / len(up)) if up else .4
    st = collections.Counter(r[7] for r in l5 if r[7]).most_common(1)
    f5 = {"逃げ": 1.0, "先行": 1.0, "差し": .7, "追込": .5}.get(st[0][0], .6) if st else .6
    g = (dd - hist[-1][0]).days
    f6 = 1.0 if 33 <= g <= 146 else .6 if g < 33 else .25
    pf = [max(-5, min(5, r[5] - r[4])) for r in r3 if r[5]]
    f7 = sum(pf) / len(pf) / 5 if pf else 0
    return [f1, f2, f3, f4, f5, f6, f7]


def build(graded):
    races = load()
    hist = collections.defaultdict(list)
    out = []
    for key in sorted(races):
        ds, venue, R = key
        rows = races[key]
        dd = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
        surf, m, cond = rows[0][6], rows[0][7], rows[0][8]
        use = ds >= "20190101" and len(rows) >= 8 and (not graded or "オープン" in cond)
        if use:
            F = [feats(hist[h[0]], dd, venue, surf, m) for h in rows]
            if all(x is not None for x in F) and sum(h[1] == 1 for h in rows) == 1:
                X = np.array(F, float)
                sd = X.std(0); sd[sd == 0] = 1
                Z = (X - X.mean(0)) / sd
                o = np.array([h[2] for h in rows]); q = (1 / o) / (1 / o).sum()
                fin = np.array([h[1] for h in rows])
                out.append(dict(ds=ds, X=X, Z=Z, q=q, o=o, fin=fin, w=int(np.argmin(fin))))
        for h in rows:
            hist[h[0]].append((dd, venue, surf, m, h[1], h[3], h[4], h[5], cond))
    return out


def nll(b, D, cols, use_q):
    s = 0.0
    for r in D:
        u = r["Z"][:, cols] @ b[:len(cols)] if cols else np.zeros(len(r["q"]))
        if use_q:
            u = u + b[-1] * np.log(r["q"])
        u = u - u.max(); p = np.exp(u); p /= p.sum()
        s -= np.log(p[r["w"]] + 1e-12)
    return s / len(D)


def fit(D, cols, use_q):
    x0 = np.zeros(len(cols) + (1 if use_q else 0))
    if use_q:
        x0[-1] = 1.0
    return minimize(nll, x0, args=(D, cols, use_q), method="L-BFGS-B").x


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--graded", action="store_true"); a = ap.parse_args()
    D = build(a.graded)
    tr = [r for r in D if r["ds"] < "20230101"]; te = [r for r in D if r["ds"] >= "20230101"]
    print(f"対象 {len(D):,}レース（{'重賞・オープン' if a.graded else '全レース'}・8頭以上・全頭に前走あり）前半{len(tr):,}／後半{len(te):,}")
    res = {}
    print("\n## (1) 部品が1位の馬（同点は人気順の上）: 勝率・3着内率・単勝回収 ｜ 参考: 1番人気")

    def top(sel):
        n = w = t = y = 0
        for r in D:
            i = sel(r); n += 1; w += r["fin"][i] == 1; t += r["fin"][i] <= 3; y += r["o"][i] * 100 * (r["fin"][i] == 1)
        return n, w / n * 100, t / n * 100, y / n

    for j, nm in enumerate(NAMES):
        n, w, t, y = top(lambda r: int(np.lexsort((r["o"], -r["X"][:, j]))[0]))
        print(f"  {nm:14} 勝{w:5.1f}% 3着内{t:5.1f}% 単回{y:5.1f}%"); res["top|" + nm] = [w, t, y]
    W0 = np.array([30, 10, 10, 5, 10, 8, 0], float)                # 今の配点に近い重み（型の前走レース名・状態は除く）
    comp = lambda r, W: (r["X"] * W).sum(1)
    n, w, t, y = top(lambda r: int(np.lexsort((r["o"], -comp(r, W0)))[0])); print(f"  {'今の配点の合計':14} 勝{w:5.1f}% 3着内{t:5.1f}% 単回{y:5.1f}%"); res["top|今の配点"] = [w, t, y]
    n, w, t, y = top(lambda r: int(np.argmin(r["o"]))); print(f"  {'1番人気':14} 勝{w:5.1f}% 3着内{t:5.1f}% 単回{y:5.1f}%"); res["top|1番人気"] = [w, t, y]

    cols = list(range(7))
    print("\n## (2) 市場を入れないとき、データが決める重み（前半で推定。レース内で標準化した値に掛ける係数）")
    b = fit(tr, cols, False)
    for nm, x in sorted(zip(NAMES, b), key=lambda z: -abs(z[1])):
        print(f"  {nm:14} {x:+.3f}")
    sh = np.clip(b, 0, None); sh = sh / sh.sum() * 100
    print("  → 正の係数を100点に割り振ると: " + " ／ ".join(f"{nm} {s:.0f}" for nm, s in zip(NAMES, sh)))
    base = float(np.mean([np.log(len(r["q"])) for r in te]))
    print(f"  後半の対数尤度（1レース平均・小さいほど良い）: 全馬同じ {base:.4f} ／ 部品だけ {nll(b, te, cols, False):.4f} ／ 市場だけ {nll(np.array([1.0]), te, [], True):.4f}")
    res["w_no_market"] = dict(zip(NAMES, map(float, b)))

    print("\n## (3) 市場を土台に部品を足す（前半で推定→後半で採点）")
    bq = fit(tr, [], True); l0 = nll(bq, te, [], True)
    ba = fit(tr, cols, True); la = nll(ba, te, cols, True)
    print(f"  市場だけ {l0:.4f} → 市場＋全部品 {la:.4f}（改善 {l0-la:+.4f}／レース）")
    for nm, x in sorted(zip(NAMES, ba[:-1]), key=lambda z: -abs(z[1])):
        print(f"    {nm:14} {x:+.3f}")
    for j, nm in enumerate(NAMES):
        b1 = fit(tr, [j], True); l1 = nll(b1, te, [j], True)
        print(f"  市場＋{nm:14} だけ: 後半 {l1:.4f}（{l0-l1:+.4f}） 係数 {b1[0]:+.3f}")
    res["w_with_market"] = dict(zip(NAMES, map(float, ba[:-1]))); res["gain_all"] = float(l0 - la)

    print("\n## (4) 見立ての式 p ∝ 市場 × exp(c×z(指数))。今は c=0.4")

    def zc(r, W):
        s = comp(r, W); sd = s.std() or 1
        return (s - s.mean()) / sd

    for lab, W in (("今の配点", W0), ("データの重み(2)", np.clip(b, 0, None))):
        def f(c, DD):
            s = 0
            for r in DD:
                u = np.log(r["q"]) + c * zc(r, W); u -= u.max(); p = np.exp(u); p /= p.sum(); s -= np.log(p[r["w"]] + 1e-12)
            return s / len(DD)
        best = min(np.arange(-0.2, 0.61, 0.02), key=lambda c: f(c, tr))
        print(f"  {lab}: 前半で最良の c={best:+.2f} ／ 後半の対数尤度 c=0: {f(0, te):.4f}  c={best:+.2f}: {f(best, te):.4f}  c=0.4: {f(0.4, te):.4f}")
        res["c|" + lab] = dict(best=float(best), ll0=float(f(0, te)), llbest=float(f(best, te)), ll04=float(f(0.4, te)))
    (E.DB / f"index_weight_results{'_graded' if a.graded else ''}.json").write_text(json.dumps(dict(made="20261114", n=len(D), results=res), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
