# -*- coding: utf-8 -*-
"""axis_stake_test.py — 「軸を誰にするか」に「金額の配り方」を足して、当たる頻度と回収率を測る（2026-11-18 新設）

きっかけ（2026-11-18 ユーザー指示）: 今年の総まとめ（docs/keiba_2026_summary_20261118.md）で、外れのいちばん多い型が「軸（◎）が来ない」。
◎は割安さ1位（平均2.8番人気・3着内55%）で、1番人気（74%）より来ない。axis_structure_test.py（11/16）は均等買いで
「軸をP（モデル確率1位）にすると当たる頻度は上がるが回収率は上がらない」。ここでは金額の配り方と券種の混ぜ方まで変えて比べる。

  軸 X: ◎（割安さ1位・現行）／P（モデルの勝つ確率1位）
  相手: 現行の印（◎○▲△）のうち X 以外
  配り方: 均等／来そうな組に厚く（モデルの組の確率に比例）／払戻をそろえる（市場の組の確率に比例＝どれが来ても同じくらい戻る）／割安な組に厚く（モデル÷市場に比例）
  券種: 単勝・複勝・ワイド流し・馬連流し、とその混ぜ方
  1レースの予算を 1 にそろえて比べる（点数が違っても同じ土俵）。確定払戻で精算。
見るもの: 何か当たる率／当たっても元が取れない率（トリガミ）／回収率（全体・前半2019〜22・後半2023〜）／いちばん大きい1%の的中を除いた回収率
注意: 同じ期間を見て選ぶので、良く見えた形は「候補」。前半・後半とも同じ向きのものだけ残す。
  python axis_stake_test.py
"""
import collections, json, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as M

OUT = E.DB / "axis_stake_results.json"


def pair_probs(p):
    """(複勝の確率ベクトル, ワイドの行列, 馬連の行列)"""
    T = C.tensor(p)
    first = T.sum(axis=2)                                   # [a,b] aが1着・bが2着
    ex = first + first.T                                    # 馬連
    a_c = T.sum(axis=1); b_c = T.sum(axis=0)                # [a,c] aが1着cが3着 / [b,c] bが2着cが3着
    wide = ex + a_c + a_c.T + b_c + b_c.T
    place = T.sum(axis=(1, 2)) + T.sum(axis=(0, 2)) + T.sum(axis=(0, 1))
    return place, wide, ex


def norm(w):
    w = np.asarray(w, float); s = w.sum()
    return w / s if s > 0 else np.full(len(w), 1 / len(w))


def main():
    preds, pay = C.predictions(), C.load_pay()
    R = collections.defaultdict(lambda: collections.defaultdict(list))        # 形 → 期 → [レースごとの戻り（予算1に対して）]
    info = collections.Counter()
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("馬連") or not pp.get("複勝") or not pp.get("単勝"):
            continue
        k2 = lambda k: tuple(sorted(map(int, str(k).split("-"))))
        wide = {k2(k): y / 100 for k, y in pp["ワイド"].items()}; uren = {k2(k): y / 100 for k, y in pp["馬連"].items()}
        fuku = {int(k): y / 100 for k, y in pp["複勝"].items()}; tan = {int(k): y / 100 for k, y in pp["単勝"].items()}
        uma = [int(u) for u in pr["uma"]]; ix = {u: i for i, u in enumerate(uma)}
        p = np.asarray(pr["p"], float); q = np.asarray(pr["q"], float); p, q = p / p.sum(), q / q.sum()
        m = M.mark(pr, {}, "A"); marks = [u for _, u, _ in m]; hon = marks[0]
        P = uma[int(np.argmax(p))]
        plm, wm, em = pair_probs(p); plq, wq, eq = pair_probs(q)
        half = "前" if pr["key"][0] < "20230101" else "後"
        info["n"] += 1; info["same"] += P == hon
        info["◎3着内"] += hon in fuku; info["P3着内"] += P in fuku; info["1人気3着内"] += uma[int(np.argmax(q))] in fuku
        S = {}
        for tag, X in (("◎", hon), ("P", P)):
            others = [u for u in marks if u != X]
            if not others:
                continue
            i = ix[X]; js = [ix[u] for u in others]
            wr = np.array([wide.get(tuple(sorted((X, u))), 0) for u in others])     # ワイドの払戻（倍）
            ur = np.array([uren.get(tuple(sorted((X, u))), 0) for u in others])
            pmw = np.array([wm[i, j] for j in js]); pqw = np.array([wq[i, j] for j in js])
            pme = np.array([em[i, j] for j in js]); pqe = np.array([eq[i, j] for j in js])
            W = {"均等": norm(np.ones(len(js))), "来そうな組に厚く": norm(pmw), "払戻をそろえる": norm(pqw), "割安な組に厚く": norm(pmw / np.maximum(pqw, 1e-9))}
            f = fuku.get(X, 0); t = tan.get(X, 0)
            S[f"{tag}軸 単勝1点"] = t
            S[f"{tag}軸 複勝1点"] = f
            for nm, w in W.items():
                S[f"{tag}軸 ワイド流し・{nm}"] = float((w * wr).sum())
            S[f"{tag}軸 馬連流し・均等"] = float((norm(np.ones(len(js))) * ur).sum())
            S[f"{tag}軸 馬連流し・払戻をそろえる"] = float((norm(pqe) * ur).sum())
            wz = float((W["払戻をそろえる"] * wr).sum()); uz = float((norm(pqe) * ur).sum())
            S[f"{tag}軸 複勝5割＋ワイド5割（そろえる）"] = 0.5 * f + 0.5 * wz
            S[f"{tag}軸 複勝3割＋ワイド4割＋馬連3割（そろえる）"] = 0.3 * f + 0.4 * wz + 0.3 * uz
            S[f"{tag}軸 単勝3割＋ワイド7割（そろえる）"] = 0.3 * t + 0.7 * wz
            # 割安な組だけ（モデル÷市場 ≧ 1.0）。該当が無いレースは見送り
            keep = pmw / np.maximum(pqw, 1e-9) >= 1.0
            if keep.any():
                S[f"{tag}軸 ワイド・割安な組だけ（そろえる）"] = float((norm(pqw * keep) * wr).sum())
        if P != hon:
            # 二軸: P流し と ◎流し を半分ずつ（払戻をそろえる）＋P-◎
            S["二軸 P流し5割＋◎流し5割（そろえる）"] = 0.5 * S["P軸 ワイド流し・払戻をそろえる"] + 0.5 * S["◎軸 ワイド流し・払戻をそろえる"]
            S["P-◎ ワイド1点"] = wide.get(tuple(sorted((P, hon))), 0)
            S["P複勝5割＋◎流し5割（そろえる）"] = 0.5 * fuku.get(P, 0) + 0.5 * S["◎軸 ワイド流し・払戻をそろえる"]
        for nm, r in S.items():
            R[nm][half].append(r); R[nm]["全"].append(r)
    n = info["n"]
    print(f"対象 {n:,}レース ／ Pと◎が同じ馬 {info['same']/n*100:.1f}% ／ 3着内: ◎ {info['◎3着内']/n*100:.1f}%・P {info['P3着内']/n*100:.1f}%・1番人気 {info['1人気3着内']/n*100:.1f}%")
    print(f"\n{'形':38s} {'レース':>7s} {'当たる':>6s} {'元割れ':>6s} {'回収':>7s} {'前半':>6s} {'後半':>6s} {'大当たり除く':>8s}")
    out = dict(info=dict(info), results={})
    for nm in sorted(R, key=lambda k: (k[0] != "◎", k[0] != "P", k)):
        a = np.array(R[nm]["全"]); f = np.array(R[nm]["前"]); b = np.array(R[nm]["後"])
        hit = (a > 0).mean(); gami = ((a > 0) & (a < 1)).mean()
        cut = np.sort(a)[: int(len(a) * 0.99)].mean()                      # 大きい1%を0扱いにせず外す＝残り99%の平均
        print(f"{nm:38s} {len(a):7,d} {hit*100:5.1f}% {gami*100:5.1f}% {a.mean()*100:6.1f}% {f.mean()*100:5.1f}% {b.mean()*100:5.1f}% {cut*100:7.1f}%")
        out["results"][nm] = dict(races=len(a), hit=float(hit), gami=float(gami), roi=float(a.mean()), front=float(f.mean()), back=float(b.mean()), roi_wo_top1pct=float(cut))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n保存", OUT)


if __name__ == "__main__":
    main()
