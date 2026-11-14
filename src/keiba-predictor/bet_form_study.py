# -*- coding: utf-8 -*-
"""bet_form_study.py — 買い方の型（軸1頭流し・軸2頭流し・BOX・フォーメーション・マルチ）を、券種ごとに実際の払戻で比べる（2026-11-14 新設）

きっかけ（2026-11-14 ユーザー指示）: 「3連複は安くても30倍、高いと50〜100倍つく。1点に300円・800円かける必要は薄い。もっと広げていい。
 3連複のフォーメーション・軸1頭流し・軸2頭流し、馬連の軸流し・BOX、ワイドの軸流し・BOX・フォーメーション、3連単のマルチなどを研究して」。
印: web_picks.marks_of と同じ ◎○▲△ ＋ 穴（6番人気以下・2%以上・印なしで最も割安）。ヒモ＝印の無い馬のうち勝つ確率の高い順（最大3頭）。
相手の並び: 印全部＝[○,▲,△…,穴]。前向き予測（2019〜）・確定払戻・**1点100円の均等買い**。
出すもの: 型ごとの 平均点数・何か当たる率・回収率（全／前半／後半）・当たったときの払戻の中央値（倍率＝払戻÷その型の購入額）・
          当たっても購入額を下回る（ガミ）割合・1レースのばらつきと±10ポイントまでのレース数。頭数別（〜11／12〜15／16〜）も出す。
  python bet_form_study.py
"""
import collections, itertools, json, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import bet_portfolio_study as BP


def himo(pr, used, k=3):
    p = np.asarray(pr["p"], float); uma = list(pr["uma"])
    return [int(uma[i]) for i in np.argsort(-p) if uma[i] not in used][:k]


def forms(H, o, t, D, a, hm):
    aite = [x for x in [o, t] + D + [a] if x is not None]            # 印全部（◎以外）
    core = [x for x in (o, t) if x is not None]                      # ○▲
    wide = aite + hm[:2]                                             # 印＋ヒモ2頭
    F = {}
    def add(k, typ, combs):
        cs = []
        for c in combs:
            if len(set(c)) != len(c):
                continue
            cs.append(c if typ in ("馬単", "3連単") else tuple(sorted(c)))
        cs = list(dict.fromkeys(cs))
        if cs:
            F[k] = [(typ, c) for c in cs]
    # ── 3連複 ──
    if len(core) == 2:
        add("3連複 ◎-○-▲の1点", "3連複", [(H, o, t)])
        add("3連複 BOX ◎○▲＋印1頭（4頭4点）", "3連複", itertools.combinations([H] + aite[:3], 3))
        add("3連複 BOX 印5頭（10点）", "3連複", itertools.combinations([H] + aite[:4], 3))
        add("3連複 ◎○2頭軸流し→印", "3連複", [(H, o, x) for x in aite if x != o])
        add("3連複 ◎○2頭軸流し→印＋ヒモ2", "3連複", [(H, o, x) for x in wide if x != o])
        add("3連複 フォーメーション ◎-○▲-印", "3連複", [(H, x, y) for x in core for y in aite if y != x])
        add("3連複 フォーメーション ◎-○▲-印＋ヒモ2", "3連複", [(H, x, y) for x in core for y in wide if y != x])
        add("3連複 フォーメーション ◎-○▲-印＋ヒモ3", "3連複", [(H, x, y) for x in core for y in aite + hm[:3] if y != x])
    add("3連複 ◎1頭軸流し→印", "3連複", [(H, x, y) for x, y in itertools.combinations(aite, 2)])
    add("3連複 ◎1頭軸流し→印＋ヒモ2", "3連複", [(H, x, y) for x, y in itertools.combinations(wide, 2)])
    # ── 馬連 ──
    add("馬連 ◎-○の1点", "馬連", [(H, o)] if o else [])
    add("馬連 ◎-○・◎-▲", "馬連", [(H, x) for x in core])
    add("馬連 ◎軸流し→印", "馬連", [(H, x) for x in aite])
    add("馬連 ◎軸流し→印＋ヒモ2", "馬連", [(H, x) for x in wide])
    add("馬連 BOX ◎○▲（3点）", "馬連", itertools.combinations([H] + core, 2))
    add("馬連 BOX 印4頭（6点）", "馬連", itertools.combinations([H] + aite[:3], 2))
    add("馬連 フォーメーション ◎○-印", "馬連", [(x, y) for x in [H] + core[:1] for y in [H] + aite if x != y])
    # ── ワイド ──
    add("ワイド ◎-○・◎-▲", "ワイド", [(H, x) for x in core])
    add("ワイド ◎軸流し→印", "ワイド", [(H, x) for x in aite])
    add("ワイド BOX ◎○▲（3点）", "ワイド", itertools.combinations([H] + core, 2))
    add("ワイド BOX 印4頭（6点）", "ワイド", itertools.combinations([H] + aite[:3], 2))
    add("ワイド フォーメーション ◎○-印", "ワイド", [(x, y) for x in [H] + core[:1] for y in [H] + aite if x != y])
    add("ワイド ◎-穴・◎-ヒモ2（人気薄だけ）", "ワイド", [(H, x) for x in ([a] if a else []) + hm[:2]])
    # ── 馬単 ──
    add("馬単 ◎1着流し→○▲", "馬単", [(H, x) for x in core])
    add("馬単 ◎1着流し→印", "馬単", [(H, x) for x in aite])
    add("馬単 ◎マルチ（表裏）→○▲", "馬単", [c for x in core for c in ((H, x), (x, H))])
    # ── 3連単 ──
    if len(core) == 2:
        add("3連単 ◎1着固定→○▲→印", "3連単", [(H, x, y) for x in core for y in aite if y != x])
        add("3連単 ◎1着固定→印→印", "3連単", [(H, x, y) for x in aite for y in aite if y != x])
        add("3連単 ◎1頭軸マルチ→○▲（6点）", "3連単", [p_ for p_ in itertools.permutations([H] + core, 3)])
        add("3連単 ◎○2頭軸マルチ→印", "3連単", [p_ for x in aite if x != o for p_ in itertools.permutations([H, o, x], 3)])
        add("3連単 フォーメーション ◎○→◎○▲→印", "3連単", [(x, y, z) for x in (H, o) for y in (H, o, t) for z in [H] + aite if len({x, y, z}) == 3])
    # ── 単複 ──
    add("単勝 ◎", "単勝", [(H,)]); add("複勝 ◎", "複勝", [(H,)])
    return F


def main():
    preds, pay = C.predictions(), C.load_pay()
    R = collections.defaultdict(list)                       # (型, 区分) → [(点, 払戻, 期)]
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("3連複") or not pp.get("3連単"):
            continue
        H, o, t, D, a, hp = BP.marks(pr)
        used = {x for x in [H, o, t, a] + D if x is not None}
        hm = himo(pr, used)
        n = len(pr["uma"]); half = "前" if pr["key"][0] < "20230101" else "後"
        seg = "〜11頭" if n <= 11 else "12〜15頭" if n <= 15 else "16頭〜"
        for nm, pts in forms(H, o, t, D, a, hm).items():
            rt = sum(BP.payout(pp, tt, c) for tt, c in pts)
            for s in ("全", seg):
                R[(nm, s)].append((len(pts), rt, half))
    out = {}

    def line(nm, s):
        x = R.get((nm, s))
        if not x:
            return None
        k = np.array([a_[0] for a_ in x], float); r = np.array([a_[1] for a_ in x], float); h = np.array([a_[2] for a_ in x])
        st = k * 100
        roi = r.sum() / st.sum() * 100
        rf = r[h == "前"].sum() / st[h == "前"].sum() * 100; rb = r[h == "後"].sum() / st[h == "後"].sum() * 100
        hit = (r > 0).mean() * 100; gami = ((r > 0) & (r < st)).sum() / max((r > 0).sum(), 1) * 100
        mult = np.median((r / st)[r > 0]) if (r > 0).any() else 0
        sd = (r / st).std(); need = (1.96 * sd / 0.10) ** 2
        return dict(n=len(x), pts=k.mean(), hit=hit, roi=roi, rf=rf, rb=rb, gami=gami, mult=float(mult), need=int(need))

    names = []
    for k in R:
        if k[0] not in names:
            names.append(k[0])
    print("## 全レース（1点100円の均等買い）")
    print("   型 ｜ 平均点数 ｜ 何か当たる ｜ 回収率（前半／後半）｜ 当たったときの戻り（中央値・購入額の何倍）｜ 当たっても損の割合 ｜ ±10ptまでのレース数")
    for typ in ("単勝", "複勝", "馬連", "ワイド", "馬単", "3連複", "3連単"):
        rows = [(nm, line(nm, "全")) for nm in names if nm.startswith(typ)]
        for nm, v in sorted(rows, key=lambda z: -z[1]["roi"]):
            star = "★" if v["rf"] >= 90 and v["rb"] >= 90 else "  "
            print(f" {star}{nm:30} {v['pts']:5.1f}点  当{v['hit']:5.1f}%  回収{v['roi']:6.1f}%（{v['rf']:6.1f}／{v['rb']:6.1f}）  戻り{v['mult']:5.1f}倍  損{v['gami']:5.1f}%  {v['need']:>7,}R")
            out[nm] = {k_: round(float(x_), 2) for k_, x_ in v.items()}
        print()
    print("## 頭数別の回収率（〜11頭／12〜15頭／16頭〜）と何か当たる率")
    for nm in names:
        v = [line(nm, s) for s in ("〜11頭", "12〜15頭", "16頭〜")]
        if all(v):
            print(f"  {nm:30} " + " ｜ ".join(f"{x['roi']:6.1f}%（当{x['hit']:4.1f}%・{x['pts']:4.1f}点）" for x in v))
            out[nm + "|頭数別"] = [[round(x["roi"], 1), round(x["hit"], 1), round(x["pts"], 1)] for x in v]
    (E.DB / "bet_form_results.json").write_text(json.dumps(dict(made="20261114", results=out), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
