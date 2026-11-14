# -*- coding: utf-8 -*-
"""mark_pair_test.py — 現行の印（web_picks.marks_of と同じ）で、ワイドの「組の種類」ごとの的中率と回収率を測る（2026-11-14 新設）

mark_rule_test.py の続き。◎流し 88.7% ＞ 印BOX 83.9% だったので、どの組が足を引っぱるかを見る。
組の種類: ◎-○／◎-▲／◎-△／○-▲／○-△／▲-△／△-△。さらに ◎の人気（1〜3番人気／4番人気以下）と相手の人気で分ける。
形の比較: ◎流し／◎流し＋○-▲／◎○▲のBOX（△なし）／◎→○▲だけ／印BOX。前半（2019〜22）・後半（2023〜）。確定オッズ・1点100円。
  python mark_pair_test.py
"""
import collections, itertools, json, sys

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E
import mark_rule_test as MR


def main():
    preds, pay = C.predictions(), C.load_pay()
    T = collections.defaultdict(lambda: [0, 0, 0])          # (区分, 期) → [点, 的中, 払戻]
    F = collections.defaultdict(list)
    for pr in preds:
        pp = pay.get(f"{pr['key'][0]}|{pr['key'][1]}|{pr['key'][2]}")
        if not pp or not pp.get("ワイド"):
            continue
        wide = {tuple(sorted(map(int, k.split("-")))): y for k, y in pp["ワイド"].items()}
        half = "前" if pr["key"][0] < "20230101" else "後"
        m = MR.mark(pr, {}, "A")
        hp = m[0][2]
        for (a1, u1, p1), (a2, u2, p2) in itertools.combinations(m, 2):
            y = wide.get(tuple(sorted((u1, u2))), 0)
            ks = [f"{a1}-{a2}", f"{a1}-{a2}｜◎{'1〜3番人気' if hp <= 3 else '4番人気以下'}"]
            if a1 == "◎":
                ks.append(f"◎({'人気' if hp <= 3 else '中穴'})-相手{'1〜3番人気' if p2 <= 3 else '4〜6番人気' if p2 <= 6 else '7番人気以下'}")
            for k in ks:
                for h in (half, "全"):
                    e = T[(k, h)]; e[0] += 1; e[1] += y > 0; e[2] += y
        U = {a: [u for b, u, _ in m if b == a] for a in "◎○▲△"}
        H = U["◎"][0]; ot = U["○"] + U["▲"]; al = [u for _, u, _ in m]
        forms = {"◎流し（全印へ）": [(H, x) for x in al[1:]],
                 "◎→○▲だけ": [(H, x) for x in ot],
                 "◎流し＋○-▲": [(H, x) for x in al[1:]] + ([tuple(ot)] if len(ot) == 2 else []),
                 "◎○▲のBOX": list(itertools.combinations([H] + ot, 2)),
                 "印BOX": list(itertools.combinations(al, 2))}
        for n, pts in forms.items():
            if pts:
                r = sum(wide.get(tuple(sorted(c)), 0) for c in pts)
                for h in (half, "全"):
                    F[(n, h)].append((len(pts) * 100, r))
    out = {}
    print("## 組の種類ごと（点数・的中率・回収率 全｜前半｜後半）")
    for k in sorted({k for k, _ in T}):
        x = []
        for h in ("全", "前", "後"):
            n, w, y = T[(k, h)]
            x.append(f"{h} {n:6,}点 当{w/max(n,1)*100:4.1f}% 回収{y/max(n,1):5.1f}%")
        out[k] = T[(k, "全")]
        print(f"  {k:24} " + " ｜ ".join(x))
    print("\n## 形ごと（何か当たる・回収率）")
    for n in ("◎流し（全印へ）", "◎→○▲だけ", "◎流し＋○-▲", "◎○▲のBOX", "印BOX"):
        x = []
        for h in ("全", "前", "後"):
            st = [a for a, _ in F[(n, h)]]; rt = [b for _, b in F[(n, h)]]
            s = f"{h} 当{sum(b > 0 for b in rt)/len(rt)*100:4.1f}% 回収{sum(rt)/sum(st)*100:5.1f}%"
            if h == "全":
                lo, hi = C.ci(st, rt, n=1000); s += f"［{lo*100:.1f}〜{hi*100:.1f}］"
            x.append(s)
        out["形|" + n] = [len(F[(n, "全")]), sum(a for a, _ in F[(n, "全")]), sum(b for _, b in F[(n, "全")])]
        print(f"  {n:12} " + " ｜ ".join(x))
    (E.DB / "mark_pair_results.json").write_text(json.dumps(dict(made="20261114", results=out), ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
