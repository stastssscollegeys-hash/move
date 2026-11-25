# -*- coding: utf-8 -*-
"""race_select_test.py — 「買うレースを絞る」を細かく測る（2026-11-26 新設）

きっかけ: 2026-11-26 ユーザー指示「ネット上で回収率・的中率を上げる方法やコツを探して取り入れる」。ネットで繰り返し出てくるコツは
  ①買うレースを絞る ②点数を増やさない ③人気薄を買いすぎない（人気薄ほど回収率が低い＝favorite-longshot bias）。
①は §3k の S1・S2（◎の割安さで強さを変える）で取り入れ済み。ここでは、同じ◎（割安さ1位・確率8%以上）を
  「割安さの帯 × ◎の人気 × 頭数」で分けて、単勝・複勝相当（3着内）・ワイド◎-○ の成績を、前半（2019〜22）と後半（2023〜）で見る。
データ: 年ごとの前向き予測（combo_backtest.predictions・約2.5万レース）と実際の払戻。オッズは確定オッズ。1点100円。
注意: 区分を細かくすると偶然の100%超が混ざる。前半・後半とも100%超で、各300レース以上の区分だけを「候補」と呼ぶ。採用は前向き台帳で確かめてから。
  python race_select_test.py
"""
import collections, json, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E

OUT = E.DB / "race_select_results.json"


def main():
    preds, pay = C.predictions(), C.load_pay()
    S = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])      # (区分, 期) → [R, 単勝的中, 単勝払戻, 3着内, ワイド◎-○的中, ワイド払戻]
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド") or not pp.get("単勝"):
            continue
        p, q, uma = np.asarray(pr["p"], float), np.asarray(pr["q"], float), list(pr["uma"])
        p, q = p / p.sum(), q / q.sum(); n = len(uma)
        pop = np.empty(n, int); pop[np.argsort(-q)] = np.arange(1, n + 1)
        ratio = p / q
        c = [i for i in range(n) if p[i] >= .08] or [int(np.argmax(p))]
        hon = max(c, key=lambda i: ratio[i])
        rest = sorted([i for i in range(n) if i != hon and p[i] >= .05], key=lambda i: -ratio[i])
        win = {int(k): y for k, y in pp["単勝"].items()}
        wide = {tuple(sorted(map(int, k.split("-")))): y for k, y in pp["ワイド"].items()}
        top3 = {u for cc in wide for u in cc}
        u = int(uma[hon]); r = ratio[hon]; po = int(pop[hon]); odds = 0.8 / q[hon]
        rb = "割安さ1.30以上" if r >= 1.30 else "割安さ1.15〜1.30" if r >= 1.15 else "割安さ1.15未満"
        pb = "◎1番人気" if po == 1 else "◎2〜3番人気" if po <= 3 else "◎4〜5番人気" if po <= 5 else "◎6番人気以下"
        nb = "〜11頭" if n <= 11 else "12〜15頭" if n <= 15 else "16頭〜"
        ob = "◎の単勝 5倍未満" if odds < 5 else "◎の単勝 5〜10倍" if odds < 10 else "◎の単勝 10〜20倍" if odds < 20 else "◎の単勝 20倍以上"
        P = int(np.argmax(p)); sb = "◎＝P（確率1位）" if hon == P else "◎がPの7割以上" if p[hon] >= .7 * p[P] else "◎がPの7割未満"
        wk = tuple(sorted((u, int(uma[rest[0]])))) if rest else None
        half = "前" if pr["key"][0] < "20230101" else "後"
        keys = ["全体", rb, pb, nb, ob, sb, f"{rb}×{pb}", f"{rb}×{nb}", f"{rb}×{sb}", f"{pb}×{nb}"]
        for k in keys:
            for h in (half, "全"):
                e = S[(k, h)]; e[0] += 1; e[1] += u in win; e[2] += win.get(u, 0); e[3] += u in top3
                if wk:
                    e[4] += wk in wide; e[5] += wide.get(wk, 0)
    names = sorted({k for k, _ in S}, key=lambda x: (x.count("×"), x))
    print(f"{'区分':30} {'R':>6} 勝率  3着内 ｜ 単勝回収 全／前／後 ｜ ワイド◎-○回収 全／前／後")
    out = {}; cand = []
    for k in names:
        a, f, b = S[(k, "全")], S[(k, "前")], S[(k, "後")]
        if a[0] < 200:
            continue
        g = lambda e, i: (e[i] / e[0]) if e[0] else 0
        print(f"{k:30} {a[0]:6,} {g(a,1)*100:4.1f}% {g(a,3)*100:4.1f}% ｜ {g(a,2):5.1f}／{g(f,2):5.1f}／{g(b,2):5.1f} ｜ {g(a,5):5.1f}／{g(f,5):5.1f}／{g(b,5):5.1f}")
        out[k] = dict(n=a[0], win=g(a, 1), top3=g(a, 3), tan=[g(a, 2), g(f, 2), g(b, 2)], wide=[g(a, 5), g(f, 5), g(b, 5)], n_half=[f[0], b[0]])
        if min(f[0], b[0]) >= 300 and g(f, 2) > 100 and g(b, 2) > 100:
            cand.append(("単勝", k, a[0], g(a, 2), g(f, 2), g(b, 2)))
        if min(f[0], b[0]) >= 300 and g(f, 5) > 100 and g(b, 5) > 100:
            cand.append(("ワイド◎-○", k, a[0], g(a, 5), g(f, 5), g(b, 5)))
    print("\n■ 前半・後半とも100%超（各300レース以上）の区分＝候補")
    for t, k, n, a, f, b in cand:
        print(f"  {t} ｜ {k} ｜ {n:,}R ｜ 全{a:.1f}%・前{f:.1f}%・後{b:.1f}%")
    if not cand:
        print("  なし")
    OUT.write_text(json.dumps(dict(made="20261126", results=out, candidates=cand), ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n保存:", OUT)


if __name__ == "__main__":
    main()
