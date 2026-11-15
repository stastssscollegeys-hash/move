# -*- coding: utf-8 -*-
"""axis_structure_test.py — 「軸を誰にするか」で当たる頻度と回収率がどう変わるかを、年ごとの前向き予測（2019〜・約2.5万レース）と実際の払戻で比べる（2026-11-16 新設）

きっかけ（2026-11-16 ユーザー指示）: 「的中率を上げる方法を分析して。馬券の買い目・印の付け方も含めて」。
11/15 の直前予想19レースは、軸（割安さ最上位の◎）が3着内10・圏外9。軸が圏外の9レースは払戻0円（保険が効かなかった）。
mark_rule_test.py（11/14）で分かっていること: ◎をモデル確率1位にすると 3着内 51%→65% に上がるが、単勝回収は 91%→82% に下がる。
ここで比べるのは「印（割安さ順）はそのままにして、買い目の軸だけを変える」形:
  P＝モデル確率1位（一番来そうな馬）／◎○▲＝現行の印（割安さ順）／△＝1〜3番人気で印の無い馬
  ワイド: W1 ◎流し（現行）／W2 P流し（相手＝◎○▲。Pが◎なら○▲△）／W3 P-◎の1点（Pと◎が別の馬のレースだけ）／W4 二軸（◎流し＋P流し・重複は1点）
  馬連:   U1 ◎流し／U2 P流し／U3 P-◎の1点
  3連複:  T1 ◎1頭軸流し（相手＝印の残り）／T2 P・◎の2頭軸流し（相手＝印の残り。Pと◎が別のレースだけ）／T3 P1頭軸流し
見るもの: 買ったレース数・1レースの点数・何か当たる率・回収率（全体／前半2019〜22／後半2023〜）。1点100円の均等買い・確定払戻。
注意: 同じ期間を見て選ぶので、良く見えた形は「候補」。採用は前半・後半とも同じ向きのものだけ。
  python axis_structure_test.py
"""
import collections, itertools, json, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as M

OUT = E.DB / "axis_structure_results.json"


def key2(k): return tuple(sorted(map(int, str(k).split("-"))))


def main():
    preds, pay = C.predictions(), C.load_pay()
    R = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))   # 形 → 期 → [レース, 点, 的中レース, 払戻]
    same = tot = 0; ptop = [0, 0, 0]
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("馬連") or not pp.get("3連複"):
            continue
        wide = {key2(k): y for k, y in pp["ワイド"].items()}; uren = {key2(k): y for k, y in pp["馬連"].items()}; trio = {key2(k): y for k, y in pp["3連複"].items()}
        m = M.mark(pr, {}, "A"); marks = [u for _, u, _ in m]; hon = marks[0]
        p = np.asarray(pr["p"], float); P = int(list(pr["uma"])[int(np.argmax(p))])
        top3 = {u for c in wide for u in c}
        tot += 1; same += P == hon; ptop[0] += P in top3; ptop[1] += hon in top3; ptop[2] += (P in top3) or (hon in top3)
        rest_h = [u for u in marks if u != hon]; rest_p = [u for u in marks if u != P]
        both = [u for u in marks if u not in (P, hon)]
        S = {
            "W1 ワイド◎流し": ("w", [(hon, x) for x in rest_h]),
            "W2 ワイドP流し": ("w", [(P, x) for x in rest_p]),
            "W3 ワイドP-◎の1点": ("w", [(P, hon)] if P != hon else []),
            "W4 ワイド二軸（◎流し＋P流し）": ("w", list({key2(f"{a}-{b}") for a, b in [(hon, x) for x in rest_h] + [(P, x) for x in rest_p]})),
            "U1 馬連◎流し": ("u", [(hon, x) for x in rest_h]),
            "U2 馬連P流し": ("u", [(P, x) for x in rest_p]),
            "U3 馬連P-◎の1点": ("u", [(P, hon)] if P != hon else []),
            "T1 3連複◎1頭軸流し": ("t", [(hon, a, b) for a, b in itertools.combinations(rest_h, 2)]),
            "T2 3連複P・◎2頭軸流し": ("t", [(P, hon, x) for x in both] if P != hon else []),
            "T3 3連複P1頭軸流し": ("t", [(P, a, b) for a, b in itertools.combinations(rest_p, 2)]),
        }
        half = "前" if pr["key"][0] < "20230101" else "後"
        for nm, (kind, pts) in S.items():
            if not pts:
                continue
            tb = dict(w=wide, u=uren, t=trio)[kind]
            r = sum(tb.get(tuple(sorted(c)), 0) for c in pts)
            for h in (half, "全"):
                e = R[nm][h]; e[0] += 1; e[1] += len(pts); e[2] += r > 0; e[3] += r
    print(f"対象 {tot:,}レース ／ Pと◎が同じ馬 {same/tot*100:.1f}% ／ 3着内: P {ptop[0]/tot*100:.1f}%・◎ {ptop[1]/tot*100:.1f}%・どちらか {ptop[2]/tot*100:.1f}%")
    out = dict(n=tot, same=same, p_top3=ptop[0], hon_top3=ptop[1], either=ptop[2], results={})
    print(f"\n{'形':28s} {'レース':>7s} {'点/R':>5s} {'当たる':>6s} {'回収':>7s} {'前半':>6s} {'後半':>6s}")
    for nm, d in R.items():
        a = d["全"]; f = d["前"]; b = d["後"]
        print(f"{nm:28s} {a[0]:7,d} {a[1]/a[0]:5.1f} {a[2]/a[0]*100:5.1f}% {a[3]/a[1]:6.1f}% {f[3]/f[1]:5.1f}% {b[3]/b[1]:5.1f}%")
        out["results"][nm] = dict(races=a[0], pts=a[1], hit=a[2], ret=a[3], front=[f[1], f[3]], back=[b[1], b[3]])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n保存", OUT)


if __name__ == "__main__":
    main()
