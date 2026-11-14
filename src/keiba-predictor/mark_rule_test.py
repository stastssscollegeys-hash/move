# -*- coding: utf-8 -*-
"""mark_rule_test.py — 印の付け方を変えたら成績はどうなるかを、年ごとの前向き予測（2019〜・約2.5万レース）と実際の払戻で比べる（2026-11-14 新設）

きっかけ（2026-11-14 ユーザー指示）: 「印の付け方を全部見直して」。11/14 は ◎（割安さ最上位）の休み明けが大敗、▲が3日で勝率6%。
比べるのは Web版の印（web_picks.marks_of）＝ ◎: 勝つ確率8%以上で最も割安／○▲: 5%以上で割安な順／△: 1〜3番人気で印の無い馬。
  A 現行 ／ B ◎から150日以上の休み明けを外す ／ C・D ◎の下限を10%・12% ／ E ○▲を勝つ確率の高い順 ／ F ○▲の下限を8%
  G ◎をモデル確率1位（割安さを見ない）／ H ◎は「3着内の見込み」が高い割安馬（確率×比 最大）／ I B＋E ／ J B＋H＋E
見るもの: 印ごとの勝率・3着内率・単勝回収、ワイド（◎流し／印BOX・1点100円）の何か当たる率と回収率、前半（2019〜22）と後半（2023〜）。
注意: オッズは確定オッズ（朝のオッズより有利）。同じ期間を見て選ぶので、良く見えた形は「候補」。採用は前半・後半とも同じ向きのものだけ。
  python mark_rule_test.py
"""
import collections, itertools, json, sys
from datetime import date
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E

OUT = E.DB / "mark_rule_results.json"


def gaps():
    """(date, 場, R, 馬番) → 前走からの日数（DBに前走が無ければ None）"""
    last, g = {}, {}
    for f in sorted(Path(E.SOURCE).glob("results_*.json")):
        rows = [(r.get("date"), r.get("競馬場"), r.get("R"), r.get("馬番"), r.get("horse_id")) for r in json.loads(f.read_text(encoding="utf-8"))]
        rows.sort(key=lambda x: str(x[0]))
        for d, v, R, u, h in rows:
            if not h or not d:
                continue
            d = str(d)
            try:
                dd = date(int(d[:4]), int(d[4:6]), int(d[6:8])); k = (d, v, int(R), int(u))
            except (TypeError, ValueError):
                continue
            if h in last and last[h] < dd:
                g[k] = (dd - last[h]).days
            last[h] = dd
    return g


def mark(pr, G, v):
    p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), list(pr["uma"])
    p, q = p / p.sum(), q / q.sum()
    n = len(uma)
    pop = np.empty(n, int); pop[np.argsort(-q)] = np.arange(1, n + 1)
    ratio = p / q
    k0 = pr["key"]
    long_ = [(G.get((k0[0], k0[1], int(k0[2]), int(u))) or 0) >= 150 for u in uma]
    lo = {"C": .10, "D": .12}.get(v, .08)
    c = [i for i in range(n) if p[i] >= lo]
    if v in ("B", "I", "J"):
        c2 = [i for i in c if not long_[i]]
        c = c2 or c
    if not c:
        c = [int(np.argmax(p))]
    if v == "G":
        hon = int(np.argmax(p))
    elif v in ("H", "J"):
        hon = max(c, key=lambda i: p[i] * ratio[i])
    else:
        hon = max(c, key=lambda i: ratio[i])
    lo2 = .08 if v == "F" else .05
    rest = [i for i in range(n) if i != hon and p[i] >= lo2]
    rest.sort(key=(lambda i: -p[i]) if v in ("E", "I", "J") else (lambda i: -ratio[i]))
    m = [("◎", hon)] + list(zip(("○", "▲"), rest[:2]))
    used = {i for _, i in m}
    for i in np.argsort(-q)[:3]:
        if int(i) not in used:
            m.append(("△", int(i))); used.add(int(i))
    return [(a, int(uma[i]), int(pop[i])) for a, i in m]


def main():
    preds, pay, G = C.predictions(), C.load_pay(), gaps()
    print(f"前向き予測 {len(preds):,}レース ／ 前走間隔 {len(G):,}頭ぶん")
    V = "ABCDEFGHIJ"
    names = dict(A="現行", B="◎から休み明け150日以上を外す", C="◎の下限10%", D="◎の下限12%", E="○▲を勝つ確率の高い順", F="○▲の下限8%",
                 G="◎＝モデル確率1位", H="◎＝確率×割安さが最大", I="B＋E", J="B＋H＋E")
    S = {v: collections.defaultdict(lambda: [0, 0, 0, 0]) for v in V}      # (印,期) → [頭, 勝, 3着内, 単勝払戻]
    W = {v: collections.defaultdict(list) for v in V}                       # (形,期) → [(点, 払戻)]
    PP = {v: collections.Counter() for v in V}
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("単勝"):
            continue
        win = {int(k): y for k, y in pp["単勝"].items()}
        wide = {tuple(sorted(map(int, k.split("-")))): y for k, y in pp["ワイド"].items()}
        top3 = {u for c in wide for u in c}
        half = "前" if pr["key"][0] < "20230101" else "後"
        for v in V:
            m = mark(pr, G, v)
            for a, u, po in m:
                for h in (half, "全"):
                    e = S[v][(a, h)]; e[0] += 1; e[1] += u in win; e[2] += u in top3; e[3] += win.get(u, 0)
                if a == "◎":
                    PP[v][min(po, 6)] += 1
            M = [u for _, u, _ in m]
            for nm, pts in (("◎流し", [(M[0], x) for x in M[1:]]), ("印BOX", list(itertools.combinations(M, 2)))):
                r = sum(wide.get(tuple(sorted(c)), 0) for c in pts)
                for h in (half, "全"):
                    W[v][(nm, h)].append((len(pts) * 100, r))
    out = {}
    for v in V:
        print(f"\n■ {v} {names[v]}   ◎の人気: " + " ".join(f"{k}{'番人気' if k < 6 else '番人気以下'}{c/sum(PP[v].values())*100:.0f}%" for k, c in sorted(PP[v].items())))
        o = out[v] = dict(name=names[v])
        for a in "◎○▲△":
            x = []
            for h in ("全", "前", "後"):
                n, w, t, y = S[v][(a, h)]
                x.append(f"{h} {n:6,}頭 勝{w/n*100:4.1f}% 3着内{t/n*100:4.1f}% 単回{y/n:5.1f}%")
                o[f"{a}|{h}"] = [n, w, t, y]
            print(f"  {a} " + " ｜ ".join(x))
        for nm in ("◎流し", "印BOX"):
            x = []
            for h in ("全", "前", "後"):
                st = [a for a, _ in W[v][(nm, h)]]; rt = [b for _, b in W[v][(nm, h)]]
                s = f"{h} 当{sum(b > 0 for b in rt)/len(rt)*100:4.1f}% 回収{sum(rt)/sum(st)*100:5.1f}%"
                if h == "全":
                    lo, hi = C.ci(st, rt, n=1000); s += f"［{lo*100:.1f}〜{hi*100:.1f}］"
                x.append(s); o[f"{nm}|{h}"] = [len(rt), sum(st), sum(rt)]
            print(f"  ワイド{nm} " + " ｜ ".join(x))
    OUT.write_text(json.dumps(dict(made="20261114", n=len(preds), results=out), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n保存:", OUT)


if __name__ == "__main__":
    main()
