# -*- coding: utf-8 -*-
"""bet_portfolio_study.py — 馬券の構成（どの場面をどの券で受けるか）を、部品ごと・場面ごとに測る（2026-11-14 新設）

きっかけ（2026-11-14 ユーザー指示）: 「買い目の抜け漏れ。穴馬からのワイドの押さえ、対抗からの3連複・馬単・馬連など、ケアの仕方はいろいろある。馬券の構成をちゃんと学習して」。
やること:
 (1) 場面の頻度: ◎の着順（1着／2着／3着／着外）× ほかの印（○▲△・穴）が何頭3着内に来たか。どの場面で取りこぼしているかを見る
 (2) 部品（1種類の券の束）ごとの 点数・的中率・回収率（全体／前半2019〜22／後半2023〜）と、その部品が「どの場面で当たるか」
 (3) 構成（部品に金額を割り振ったもの）ごとの 何か当たる率・回収率・場面ごとの拾える割合・1レースあたりのばらつき・±10ポイントに収まるまでのレース数
 (4) 前半で回収率の良かった部品だけで組んだ構成が、後半でも良いか（選び直しの効き目の確認）
印: web_picks.marks_of と同じ（◎＝8%以上で最も割安／○▲＝5%以上で割安順／△＝1〜3番人気で印の無い馬）＋ 穴＝6番人気以下・勝つ確率2%以上・印なしの中で最も割安な1頭。
前向き予測（2019〜）・確定払戻・金額は構成に書いた比率。
  python bet_portfolio_study.py
"""
import collections, itertools, json, math, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as MR


def marks(pr):
    m = MR.mark(pr, {}, "A")
    p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), list(pr["uma"])
    p, q = p / p.sum(), q / q.sum()
    pop = np.empty(len(uma), int); pop[np.argsort(-q)] = np.arange(1, len(uma) + 1)
    used = {u for _, u, _ in m}
    c = [i for i in range(len(uma)) if uma[i] not in used and pop[i] >= 6 and p[i] >= .02]
    ana = int(uma[max(c, key=lambda i: p[i] / q[i])]) if c else None
    U = {a: [u for b, u, _ in m if b == a] for a in "◎○▲△"}
    return U["◎"][0], (U["○"] or [None])[0], (U["▲"] or [None])[0], U["△"], ana, m[0][2]


def comps(H, o, t, D, a):
    """部品 → [(券種, 組)]"""
    X = {}
    def add(k, v):
        v = [x for x in v if all(y is not None for y in x[1]) and len(set(x[1])) == len(x[1])]
        if v:
            X[k] = v
    add("単勝◎", [("単勝", (H,))]); add("複勝◎", [("複勝", (H,))]); add("単勝○", [("単勝", (o,))])
    for nm, t_ in (("馬連", "馬連"), ("ワイド", "ワイド")):
        add(f"{nm}◎-○", [(t_, (H, o))]); add(f"{nm}◎-▲", [(t_, (H, t))]); add(f"{nm}◎-△", [(t_, (H, d)) for d in D])
        add(f"{nm}◎-穴", [(t_, (H, a))]); add(f"{nm}○-▲", [(t_, (o, t))]); add(f"{nm}○-△", [(t_, (o, d)) for d in D])
    add("ワイド○-穴", [("ワイド", (o, a))]); add("ワイド▲-穴", [("ワイド", (t, a))]); add("ワイド△-穴", [("ワイド", (d, a)) for d in D])
    add("馬単◎→○", [("馬単", (H, o))]); add("馬単○→◎", [("馬単", (o, H))]); add("馬単◎→▲", [("馬単", (H, t))]); add("馬単▲→◎", [("馬単", (t, H))])
    add("馬単○→▲", [("馬単", (o, t))])
    add("3連複◎-○-▲", [("3連複", (H, o, t))]); add("3連複◎-○-△", [("3連複", (H, o, d)) for d in D]); add("3連複◎-▲-△", [("3連複", (H, t, d)) for d in D])
    add("3連複◎-○-穴", [("3連複", (H, o, a))]); add("3連複◎-▲-穴", [("3連複", (H, t, a))]); add("3連複◎-△-穴", [("3連複", (H, d, a)) for d in D])
    add("3連複○-▲-△（◎抜き）", [("3連複", (o, t, d)) for d in D]); add("3連複○-▲-穴（◎抜き）", [("3連複", (o, t, a))])
    add("3連単◎→○⇔▲", [("3連単", (H, o, t)), ("3連単", (H, t, o))]); add("3連単○▲→◎→○▲", [("3連単", (o, H, t)), ("3連単", (t, H, o))])
    return X


def payout(pp, t, c):
    tb = pp.get(t, {})
    if t in ("単勝", "複勝"):
        return tb.get(str(c[0]), 0)
    if t in ("馬単", "3連単"):
        return tb.get("-".join(map(str, c)), 0)
    return tb.get("-".join(map(str, sorted(c))), 0)


# 構成: 部品 → 金額（合計はおよそ1万円。部品が無いレースはその分を買わない）
PORT = {
 "A 旧: ワイド◎流し＋○-▲": {"ワイド◎-○": 3000, "ワイド◎-▲": 2500, "ワイド◎-△": 2500, "ワイド○-▲": 2000},
 "B 昨夜: 単勝＋馬単＋3連単＋ワイド": {"単勝◎": 2000, "馬単◎→○": 1500, "馬単◎→▲": 1500, "3連単◎→○⇔▲": 1800, "ワイド◎-○": 1600, "ワイド◎-▲": 1600},
 "C 単勝＋馬連＋3連複1点＋ワイド": {"単勝◎": 3000, "馬連◎-○": 2000, "馬連◎-▲": 2000, "3連複◎-○-▲": 1000, "ワイド◎-○": 1000, "ワイド◎-▲": 1000},
 "D C＋◎抜きの保険（馬連○-▲）": {"単勝◎": 2500, "馬連◎-○": 2000, "馬連◎-▲": 1500, "3連複◎-○-▲": 1000, "ワイド◎-○": 1000, "ワイド◎-▲": 1000, "馬連○-▲": 1000},
 "E C＋穴の押さえ（ワイド◎-穴・3連複◎-○-穴）": {"単勝◎": 2500, "馬連◎-○": 2000, "馬連◎-▲": 1500, "3連複◎-○-▲": 800, "ワイド◎-○": 1000, "ワイド◎-▲": 800, "ワイド◎-穴": 800, "3連複◎-○-穴": 600},
 "F 単勝＋馬連だけ": {"単勝◎": 4000, "馬連◎-○": 3000, "馬連◎-▲": 3000},
 "G 単勝＋馬連＋裏（馬単○→◎・▲→◎）": {"単勝◎": 3000, "馬連◎-○": 2500, "馬連◎-▲": 2000, "馬単○→◎": 1300, "馬単▲→◎": 1200},
 "H 単勝＋馬連＋3連複◎軸（○▲△穴）": {"単勝◎": 3000, "馬連◎-○": 2000, "馬連◎-▲": 1500, "3連複◎-○-▲": 1000, "3連複◎-○-△": 800, "3連複◎-▲-△": 700, "3連複◎-○-穴": 500, "3連複◎-▲-穴": 500},
 "I 単勝だけ": {"単勝◎": 10000},
 "J 馬連◎-○だけ": {"馬連◎-○": 10000},
}


def main():
    preds, pay = C.predictions(), C.load_pay()
    scen = collections.Counter(); scen_all = 0
    CR = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))     # 部品 → 期 → [点, 的中, 払戻]
    CS = collections.defaultdict(collections.Counter)                                   # 部品 → 場面 → 当たったレース数
    rows = []                                                                           # レースごと: (期, 場面, {部品: (点, 払戻)})
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("3連複") or not pp.get("馬単"):
            continue
        H, o, t, D, a, hp = marks(pr)
        ex = list(pp["馬単"].keys())[0].split("-"); w1, w2 = int(ex[0]), int(ex[1])
        top3 = {u for k in pp["ワイド"] for u in map(int, k.split("-"))}
        pos = 1 if H == w1 else 2 if H == w2 else 3 if H in top3 else 4
        others = [x for x in [o, t] + D + [a] if x is not None]
        k_in = sum(x in top3 for x in others)
        sc = f"◎{pos if pos < 4 else '着外'}{'着' if pos < 4 else ''}・他の印{min(k_in, 2)}{'頭以上' if k_in >= 2 else '頭'}"
        scen[sc] += 1; scen_all += 1
        half = "前" if pr["key"][0] < "20230101" else "後"
        rec = {}
        for nm, pts in comps(H, o, t, D, a).items():
            rt = sum(payout(pp, tt, c) for tt, c in pts)
            rec[nm] = (len(pts), rt)
            for h in (half, "全"):
                e = CR[nm][h]; e[0] += len(pts); e[1] += rt > 0; e[2] += rt
            if rt > 0:
                CS[nm][f"◎{pos if pos < 4 else '着外'}"] += 1
        rows.append((half, f"◎{pos if pos < 4 else '着外'}", rec))
    N = len(rows)
    out = {"n": N}
    print(f"対象 {N:,}レース\n\n## (1) 場面の頻度（◎の着順 × ほかの印〔○▲△穴〕が3着内に来た頭数）")
    for k in sorted(scen):
        print(f"  {k:16} {scen[k]/scen_all*100:5.1f}%")
    pos_n = collections.Counter(r[1] for r in rows)
    print("  ◎の着順: " + " ／ ".join(f"{k} {v/N*100:.1f}%" for k, v in sorted(pos_n.items())))
    out["scen"] = {k: round(v / scen_all * 100, 2) for k, v in scen.items()}
    print("\n## (2) 部品ごと（買えたレース数・的中率・回収率 全｜前半｜後半 ・当たったときの◎の着順の内訳）")
    comp_roi = {}
    for nm in sorted(CR, key=lambda k: -CR[k]["全"][2] / max(CR[k]["全"][0], 1)):
        v = CR[nm]; nr = sum(1 for r in rows if nm in r[2])
        roi = {h: v[h][2] / max(v[h][0], 1) for h in ("全", "前", "後")}
        comp_roi[nm] = roi
        hits = sum(CS[nm].values()) or 1
        mix = " ".join(f"{k}:{CS[nm][k]/hits*100:.0f}%" for k in ("◎1", "◎2", "◎3", "◎着外") if CS[nm][k])
        print(f"  {nm:18} {nr:6,}R 当{v['全'][1]/max(nr,1)*100:5.1f}%  回収{roi['全']:6.1f}% ｜ {roi['前']:6.1f}% ｜ {roi['後']:6.1f}%   [{mix}]")
        out["comp|" + nm] = [nr, round(v["全"][1] / max(nr, 1) * 100, 1), round(roi["全"], 1), round(roi["前"], 1), round(roi["後"], 1)]

    def run(name, W, sel=None):
        st = {h: [] for h in ("全", "前", "後")}
        cover = collections.Counter(); posn = collections.Counter()
        for half, pos, rec in rows:
            s = r = 0.0
            for nm, yen in W.items():
                if nm in rec:
                    k, rt = rec[nm]; s += yen; r += yen / (100.0 * k) * rt
            if s == 0:
                continue
            for h in (half, "全"):
                st[h].append((s, r))
            posn[pos] += 1; cover[pos] += r > 0
        res = {}
        for h in ("全", "前", "後"):
            S = np.array([x[0] for x in st[h]]); R = np.array([x[1] for x in st[h]])
            res[h] = (len(S), (R > 0).mean() * 100, R.sum() / S.sum() * 100)
        S = np.array([x[0] for x in st["全"]]); R = np.array([x[1] for x in st["全"]])
        ret = R / S; sd = ret.std(); need = (1.96 * sd / 0.10) ** 2
        # ガミ（当たったが投資額未満）の割合
        gami = ((R > 0) & (R < S)).mean() * 100
        cv = " ".join(f"{k}:{cover[k]/max(posn[k],1)*100:.0f}%" for k in ("◎1", "◎2", "◎3", "◎着外"))
        print(f"  {name}\n      何か当たる {res['全'][1]:5.1f}%（うち元返し未満 {gami:4.1f}%） 回収 {res['全'][2]:6.1f}% ｜ 前半 {res['前'][2]:6.1f}% ｜ 後半 {res['後'][2]:6.1f}%"
              f" ｜ 1レースのばらつき {sd:5.2f} → ±10ptまで約{need:,.0f}レース\n      場面ごとに拾える割合 [{cv}]")
        out["port|" + name] = dict(hit=round(res["全"][1], 1), gami=round(gami, 1), roi=round(res["全"][2], 1), roi_f=round(res["前"][2], 1), roi_b=round(res["後"][2], 1),
                                   sd=round(float(sd), 2), need=int(need), cover={k: round(cover[k] / max(posn[k], 1) * 100, 1) for k in posn})

    print("\n## (3) 構成ごと（金額の比率は表のとおり・部品が無いレースはその分を買わない）")
    for nm, W in PORT.items():
        run(nm, W)
    print("\n## (4) 前半の回収率が上位の部品だけで組むと後半はどうか（均等配分）")
    rank = sorted([k for k in comp_roi if CR[k]["前"][0] >= 3000], key=lambda k: -comp_roi[k]["前"])
    for k in (3, 5, 8):
        top = rank[:k]
        print("   上位%d: %s" % (k, "・".join(top)))
        run(f"前半上位{k}部品を均等に", {c: 1000 for c in top})
    (E.DB / "bet_portfolio_results.json").write_text(json.dumps(dict(made="20261114", results=out), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
