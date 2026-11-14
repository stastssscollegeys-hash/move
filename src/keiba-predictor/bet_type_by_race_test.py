# -*- coding: utf-8 -*-
"""bet_type_by_race_test.py — 印は同じまま、レースの型ごとに「どの券種・どの形が一番良いか」を実際の払戻で比べる（2026-11-14 新設）

きっかけ（2026-11-14 ユーザー指示）: 「全部ワイドで買う感じだけど本当に合っているのか。券種はレースによって変えるのがベスト。買い方は印と同等以上に大事」。
Web版の採用ルール（web_picks: 的中35%以上で期待値最大）は、的中率の下限のせいでほぼワイドしか通らない＝券種を選んでいなかった。
印は web_picks.marks_of と同じ（mark_rule_test の A）。年ごとの前向き予測（2019〜）・確定払戻・1点100円の均等買い。
券種と形: 単勝◎／複勝◎／馬連◎-○／馬連◎流し／馬連◎○▲BOX／ワイド◎-○／ワイド◎流し／ワイド◎流し＋○-▲／馬単◎→○▲／馬単◎⇔○（表裏）／
          3連複◎-○-▲（1点）／3連複◎軸流し（相手全部）／3連複◎○2頭軸流し／3連単◎→○▲→印（◎1着固定）
レースの型（発走前にわかるものだけ）: ◎の人気（1番人気／2〜3番人気／4番人気以下）× ◎の勝つ確率（20%以上／未満）× 頭数（11頭以下／12頭以上）、
          混戦度（1番人気の市場確率 30%以上＝一強／20〜30%／20%未満＝混戦）。
見るもの: 型ごとの各形の 何か当たる率・回収率（前半2019〜22／後半2023〜）。型ごとに「前半で一番良かった形」が後半でも上位かどうか。
  python bet_type_by_race_test.py
"""
import collections, itertools, json, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as MR


def forms(m):
    U = {a: [u for b, u, _ in m if b == a] for a in "◎○▲△"}
    H = U["◎"][0]; o = U["○"][0] if U["○"] else None; t = U["▲"][0] if U["▲"] else None
    al = [u for _, u, _ in m][1:]
    ot = [x for x in (o, t) if x]
    F = {"単勝◎": [("単勝", (H,))], "複勝◎": [("複勝", (H,))], "ワイド◎流し": [("ワイド", (H, x)) for x in al],
         "馬連◎流し": [("馬連", (H, x)) for x in al]}
    if o:
        F["馬連◎-○"] = [("馬連", (H, o))]; F["ワイド◎-○"] = [("ワイド", (H, o))]
        F["馬単◎⇔○"] = [("馬単", (H, o)), ("馬単", (o, H))]
    if len(ot) == 2:
        F["馬連◎○▲BOX"] = [("馬連", c) for c in itertools.combinations([H] + ot, 2)]
        F["ワイド◎流し＋○-▲"] = F["ワイド◎流し"] + [("ワイド", (o, t))]
        F["馬単◎→○▲"] = [("馬単", (H, x)) for x in ot]
        F["3連複◎-○-▲"] = [("3連複", (H, o, t))]
        F["3連単◎→○▲→印"] = [("3連単", (H, a, b)) for a in ot for b in al if b != a]
    if len(al) >= 2:
        F["3連複◎軸流し"] = [("3連複", (H,) + c) for c in itertools.combinations(al, 2)]
    if o and len(al) >= 2:
        F["3連複◎○2頭軸"] = [("3連複", (H, o, x)) for x in al if x != o]
    return F


def payout(pp, t, c):
    tb = pp.get(t, {})
    if t in ("単勝", "複勝"):
        return tb.get(str(c[0]), 0)
    if t in ("馬単", "3連単"):
        return tb.get("-".join(map(str, c)), 0)
    return tb.get("-".join(map(str, sorted(c))), 0)


def main():
    preds, pay = C.predictions(), C.load_pay()
    R = collections.defaultdict(list)                     # (型, 形, 期) → [(賭け, 払戻)]
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("3連複"):
            continue
        p, q = np.asarray(pr["p"], float), np.asarray(pr["q"], float); p, q = p / p.sum(), q / q.sum()
        m = MR.mark(pr, {}, "A")
        hi = list(pr["uma"]).index(m[0][1]); hp = m[0][2]; n = len(q); q1 = float(q.max())
        half = "前" if pr["key"][0] < "20230101" else "後"
        types = ["全レース",
                 "◎" + ("1番人気" if hp == 1 else "2〜3番人気" if hp <= 3 else "4番人気以下"),
                 "◎の勝つ確率" + ("20%以上" if p[hi] >= .20 else "12〜20%" if p[hi] >= .12 else "12%未満"),
                 "頭数" + ("11頭以下" if n <= 11 else "12〜15頭" if n <= 15 else "16頭以上"),
                 "1番人気が" + ("一強(30%以上)" if q1 >= .30 else "普通(20〜30%)" if q1 >= .20 else "混戦(20%未満)"),
                 ("混戦" if q1 < .20 else "非混戦") + "×◎" + ("人気(1〜3)" if hp <= 3 else "中穴(4〜)")]
        for nm, pts in forms(m).items():
            st = 100 * len(pts); rt = sum(payout(pp, t, c) for t, c in pts)
            for ty in types:
                for h in (half, "全"):
                    R[(ty, nm, h)].append((st, rt))
    out = {}
    tys = []
    for k in R:
        if k[0] not in tys:
            tys.append(k[0])
    names = ["単勝◎", "複勝◎", "ワイド◎-○", "ワイド◎流し", "ワイド◎流し＋○-▲", "馬連◎-○", "馬連◎流し", "馬連◎○▲BOX", "馬単◎⇔○", "馬単◎→○▲",
             "3連複◎-○-▲", "3連複◎○2頭軸", "3連複◎軸流し", "3連単◎→○▲→印"]
    for ty in sorted(tys):
        nR = len(R[(ty, "単勝◎", "全")])
        print(f"\n■ {ty}（{nR:,}レース）   形: 何か当たる／回収 全｜前半｜後半")
        rows = []
        for nm in names:
            v = {}
            for h in ("全", "前", "後"):
                x = R.get((ty, nm, h), [])
                if not x:
                    v[h] = (0, 0, 0); continue
                st = sum(a for a, _ in x); rt = sum(b for _, b in x)
                v[h] = (len(x), sum(b > 0 for _, b in x) / len(x) * 100, rt / st * 100)
            rows.append((nm, v)); out[f"{ty}|{nm}"] = {h: [round(z, 1) for z in v[h]] for h in v}
        rk_f = {nm: i for i, (nm, _) in enumerate(sorted(rows, key=lambda r: -r[1]["前"][2]))}
        for nm, v in sorted(rows, key=lambda r: -r[1]["全"][2]):
            star = "★" if v["前"][2] >= 90 and v["後"][2] >= 90 else "  "
            print(f"  {star}{nm:16} 当{v['全'][1]:5.1f}%  回収{v['全'][2]:6.1f}% ｜ {v['前'][2]:6.1f}% ｜ {v['後'][2]:6.1f}%   （前半の順位 {rk_f[nm] + 1}）")
    (E.DB / "bet_type_by_race_results.json").write_text(json.dumps(dict(made="20261114", results=out), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
