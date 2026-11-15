"""web_frontier.py — 1レースについて「的中率と期待値のバランスが良い買い方」を、実オッズで比べる（2026-11-06 新設）

web_live.py が出したモデル確率（{日付}_web_probs.json）と、Yahoo!の馬連・ワイド・3連複の中間オッズを使う。
人気馬も3着内に絡める形（BOX・流し）を含めて、候補の買い方ごとに 的中率・期待回収率（モデル確率／市場確率の2通り）・最小戻りを計算する。
  python web_frontier.py --date 20261107 --race 福島12 [--budget 10000]
採用の目安（2026-11-06 ユーザー指示「的中率と回収率のいい塩梅」）: 的中率35%以上の中で期待回収率（モデル）が最大。無ければ的中率の下限を下げる。
注意: 前売りは投票が少なく、組合せオッズが歪む（高配当側に偏る）。期待値が1を大きく超える組は疑う。
"""
import argparse
import itertools
import json
import re
import sys

import numpy as np
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
import bet_engine as B
import web_live as WL


def _main(url):
    r = requests.get(url, headers=WL.UA, timeout=30)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")
    return s.find("main") or s


def pair_odds(rid):
    """{'馬連': {(a,b): odds}, 'ワイド': {(a,b): 下限}}"""
    out = {"馬連": {}, "ワイド": {}}
    for key, path in (("馬連", "ur"), ("ワイド", "wide")):
        for tb in _main(f"{WL.BASE}odds/{path}/{rid}").select("table"):
            tx = re.sub(r"\s+", " ", tb.get_text(" ", strip=True))
            m = re.match(r"^(\d+) (.*)$", tx)
            if not m:
                continue
            a = int(m.group(1))
            if key == "馬連":
                for b, o in re.findall(r"(\d+) ([\d,]+\.\d)", m.group(2)):
                    out[key][tuple(sorted((a, int(b))))] = float(o.replace(",", ""))
            else:
                for b, lo, hi in re.findall(r"(\d+) ([\d,]+\.\d) ?[-~] ?([\d,]+\.\d)", m.group(2)):
                    out[key][tuple(sorted((a, int(b))))] = float(lo.replace(",", ""))
    return out


def trio_odds(rid):
    out = {}
    for tb in _main(f"{WL.BASE}odds/sf/{rid}").select("table"):
        tx = re.sub(r"\s+", " ", tb.get_text(" ", strip=True))
        m = re.match(r"^(\d+)[－\-](\d+) (.*)$", tx)
        if not m:
            continue
        for c, o in re.findall(r"(\d+) ([\d,]+\.\d)", m.group(3)):
            out[tuple(sorted((int(m.group(1)), int(m.group(2)), int(c))))] = float(o.replace(",", ""))
    return out


def run(race, budget=10000, min_hit=0.35, verbose=True, extra=None):
    """extra: {名前: [(券種, 馬番のタプル), ...]} … 自動の候補に加えて比べたい任意の買い方（例: 近走の根拠が弱い人気馬を外した形）"""
    uma = [h["uma"] for h in race["horses"]]
    p = np.array([h["p_model"] for h in race["horses"]]); p = p / p.sum()
    win = {h["uma"]: h["odds"] for h in race["horses"]}
    q = np.array([1 / win[u] for u in uma]); q = q / q.sum()
    names = {h["uma"]: h["name"] for h in race["horses"]}
    idx = {u: i for i, u in enumerate(uma)}
    po, to = pair_odds(race["rid"]), trio_odds(race["rid"])
    Tp, Tq = B.tensor(p), B.tensor(q)
    t3 = Tp.sum(axis=(1, 2)) + Tp.sum(axis=(0, 2)) + Tp.sum(axis=(0, 1))
    order = [uma[i] for i in np.argsort(-t3)]                      # 3着内に来る見込みの高い順

    def od(t, c):
        c = tuple(sorted(c))
        if t == "単勝":
            return win.get(c[0])
        if t == "3連複":
            return to.get(c)
        return po[t].get(c)

    def evaluate(pts, T):
        tot = sum(s for _, _, s in pts)
        hit = ret = 0.0
        n = len(uma)
        for a in range(n):
            for b in range(n):
                if a == b:
                    continue
                for c in range(n):
                    if c == a or c == b or T[a, b, c] <= 0:
                        continue
                    ua, ub, uc = uma[a], uma[b], uma[c]
                    pay = 0.0
                    for t, cb, s in pts:
                        sc = set(cb)
                        if (t == "馬連" and {ua, ub} == sc) or (t == "ワイド" and sc <= {ua, ub, uc}) or (t == "3連複" and {ua, ub, uc} == sc) or (t == "単勝" and cb[0] == ua):
                            pay += s * od(t, cb)
                    if pay > 0:
                        hit += T[a, b, c]
                        ret += T[a, b, c] * pay
        return hit, ret / tot

    def alloc(points):
        inv = [1 / od(t, c) for t, c in points]
        s = sum(inv)
        return [(t, c, max(100, int(round(budget * w / s / 100)) * 100)) for (t, c), w in zip(points, inv)]

    top = order[:6]
    cands = {}
    for k in (3, 4, 5):                                                 # 3着内の見込み上位k頭のワイドBOX
        cands[f"ワイドBOX 上位{k}頭"] = [("ワイド", c) for c in itertools.combinations(top[:k], 2)]
    axis = max(uma, key=lambda u: p[idx[u]])                            # 勝つ確率が最も高い馬を軸に
    for k in (3, 4, 5):
        rest = [u for u in order if u != axis][:k]
        cands[f"ワイド 軸{axis}→上位{k}頭"] = [("ワイド", (axis, x)) for x in rest]
        cands[f"馬連 軸{axis}→上位{k}頭"] = [("馬連", (axis, x)) for x in rest]
    for k in (4, 5, 6):
        cands[f"3連複BOX 上位{k}頭"] = [("3連複", c) for c in itertools.combinations(top[:k], 3)]
    rest5 = [u for u in order if u != axis][:5]
    cands[f"3連複 軸{axis}→上位5頭(10点)"] = [("3連複", (axis,) + pr) for pr in itertools.combinations(rest5, 2)]
    cands.update(extra or {})
    rows = []
    for name, pl in cands.items():
        pl = [(t, tuple(sorted(c))) for t, c in pl if od(t, c)]
        if len(pl) < 2:
            continue
        pts = alloc(pl)
        tot = sum(s for _, _, s in pts)
        hp, ep = evaluate(pts, Tp)
        hq, eq = evaluate(pts, Tq)
        rows.append(dict(name=name, pts=pts, tot=tot, hit=hp, evp=ep, evq=eq, minret=min(s * od(t, c) for t, c, s in pts) / tot))
    rows.sort(key=lambda r: -r["evp"])
    good = [r for r in rows if r["hit"] >= min_hit]
    best = good[0] if good else max(rows, key=lambda r: r["hit"] * r["evp"])
    if verbose:
        print("■", race.get("title"), race["venue"], f"{race['R']}R", race["start"], f"{race['n']}頭", race["dist"], race["baba"])
        print("  3着内の見込み上位:", " ".join(f"{u}{names[u]}({t3[idx[u]]*100:.0f}%)" for u in top))
        for r in rows[:8]:
            print("  %-30s %2d点 %6d円 的中%5.1f%% EV(モデル)%.2f EV(市場)%.2f 最小戻り%.2f" % (r["name"], len(r["pts"]), r["tot"], r["hit"] * 100, r["evp"], r["evq"], r["minret"]))
        print("  → 採用:", best["name"], " / ".join(f"{t}{'-'.join(map(str, c))} {s}円" for t, c, s in best["pts"]))
    return best, rows, t3, order


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--race", nargs="+", required=True, help="例: 福島12 京都11")
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--min-hit", type=float, default=0.35)
    a = ap.parse_args()
    d = json.load(open(WL.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"]
    for k in a.race:
        run(d[k], a.budget, a.min_hit)
        print()
