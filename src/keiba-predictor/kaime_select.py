# -*- coding: utf-8 -*-
"""
kaime_select.py — 買い方（型）をレースごとに選ぶ（2026-09-26新規）
====================================================================
背景: kaime_mixed.py は買い目の出発点がワイド決め打ちで、馬連は救済でしか出ず、
単勝・複勝・馬単・3連複は候補にすら入っていなかった。結果として数週間ずっと
「ワイド流し＋穴の単勝」しか出ていなかった。実測（496R）では最も弱い型だった。

本モジュールは **単勝〜3連単の全ファミリーで候補を生成し、期待値で選ぶ**。

確率: 単勝オッズを正規化した市場確率と、指数から作ったモデル確率をブレンドし、
      Harville連鎖に実測補正（λ2=0.80 / λ3=0.70・2026-09-06）を掛けて着内確率にする。
配当: payout_estimator（確定払戻1,536Rで較正）。
事前: structure_backtest.py の実測ROI（496R・レース前の印のみ）を型ごとの係数にする。

ガード: Σ(1/配当)≦1.0 ／ 本線は推定4.0倍以上 ／ 100円単位 ／ 3連単は主軸にしない。
"""
from __future__ import annotations
import itertools
from dataclasses import dataclass, field

import json
from pathlib import Path as _P

from payout_estimator import estimate

L2, L3 = 0.80, 0.70
MIN_N = 300        # この件数以上の帯だけ実測を使う

_BH = _P.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "band_hitrate.json"
BAND = json.loads(_BH.read_text(encoding="utf-8")) if _BH.exists() else {}


def measured(t, pops):
    """人気帯の実測的中率。band_hitrate.py（確定払戻1,536R）から引く。無ければ None"""
    if t == "馬単":
        key = ">".join(str(x) for x in pops)
    else:
        key = "-".join(str(x) for x in sorted(pops))
    d = BAND.get(t, {}).get(key)
    return d["rate"] if d and d["n"] >= MIN_N else None
MIN_HONSEN_EST = 4.0

# structure_backtest.py（496R・レース前の印のみ・推定配当に反比例配分）の実測ROI。
# 期待値だけだと控除率で横並びになるので、型そのものの実測を事前分布として掛ける。
PRIOR = {
    "馬連◎流し": 1.32, "馬連BOX3": 1.07, "ワイド◎流し": 1.01, "3連複◎軸流し": 0.99,
    "馬単◎1着流し": 0.86, "ワイドBOX3": 0.80, "単勝◎": 0.82, "複勝◎": 0.84,
    "3連複BOX4": 0.77, "単勝集中": 0.82, "3連複2列目": 0.95, "ワイド穴軸流し": 0.90,
    "馬連穴軸流し": 0.95,
}


@dataclass
class Cand:
    name: str
    kind: str                     # レースの見立てラベル
    points: list = field(default_factory=list)   # [{t,combo,est,p}]
    note: str = ""


def market_p(odds: dict) -> dict:
    raw = {u: 1 / o for u, o in odds.items()}
    s = sum(raw.values())
    return {u: v / s for u, v in raw.items()}


def model_p(score: dict, odds: dict, temp: float = 6.0) -> dict:
    """指数を確率に直す（softmax）。指数差がそのまま勝率差になりすぎないよう温度で鈍らせる"""
    import math
    mx = max(score.values())
    e = {u: math.exp((score[u] - mx) / temp) for u in odds}
    s = sum(e.values())
    return {u: v / s for u, v in e.items()}


def blend(mp: dict, xp: dict, w_model: float = 0.35) -> dict:
    p = {u: (1 - w_model) * mp[u] + w_model * xp[u] for u in mp}
    s = sum(p.values())
    return {u: v / s for u, v in p.items()}


def top3_prob(p1: dict) -> dict:
    out = {}
    for u in p1:
        others = [x for x in p1 if x != u]
        p = p1[u]
        p2 = sum(p1[a] * p / max(1e-9, 1 - p1[a]) for a in others) * L2
        p3 = 0.0
        for a, b in itertools.permutations(others, 2):
            p3 += p1[a] * (p1[b] / max(1e-9, 1 - p1[a])) * (p / max(1e-9, 1 - p1[a] - p1[b]))
        out[u] = min(0.999, p + p2 + p3 * L3)
    return out


def p_pair_top3(a, b, t3):
    return t3[a] * t3[b] * 0.80


def p_quinella(a, b, p1):
    """馬連: a,bが1-2着（順不同）"""
    return (p1[a] * p1[b] / max(1e-9, 1 - p1[a]) + p1[b] * p1[a] / max(1e-9, 1 - p1[b]))


def p_exacta(a, b, p1):
    return p1[a] * p1[b] / max(1e-9, 1 - p1[a])


def p_trio(a, b, c, p1):
    s = 0.0
    for x, y, z in itertools.permutations((a, b, c)):
        s += p1[x] * (p1[y] / max(1e-9, 1 - p1[x])) * (p1[z] / max(1e-9, 1 - p1[x] - p1[y]))
    return s


def build_candidates(score, odds, name, ana=None):
    """レースの見立てごとに候補の型を作る"""
    p1 = blend(market_p(odds), model_p(score, odds))
    t3 = top3_prob(p1)
    rank = sorted(odds, key=lambda u: -score[u])          # 指数順
    pop = sorted(odds, key=lambda u: odds[u])              # 人気順
    hon = rank[0]
    aite = [u for u in rank[1:5]]
    pop4 = [u for u in pop[:5] if u != hon][:4]
    # 穴＝◎○▲△△に入っていない指数上位のうち、8番人気以下でいちばん指数が高い馬
    marked = set([hon] + aite)
    mid = [u for u in rank if u not in marked and pop.index(u) + 1 >= 8]
    ana = ana or (mid[0] if mid else None)
    C = []

    def P(t, combo, p):
        if t == "単勝":                      # 単勝は推定不要。オッズそのものが配当
            e = odds[combo[0]]
        elif t == "複勝":                    # 較正器に無い場合は単勝オッズから粗く見積もる
            e = estimate(t, [odds[x] for x in combo]) or max(1.1, odds[combo[0]] * 0.28)
        else:
            e = estimate(t, [odds[x] for x in combo])
            if e is None:                    # 較正外の券種は買わない
                return None
        pp = measured(t, [pop.index(x) + 1 for x in combo])
        return {"t": t, "combo": list(combo), "est": round(e, 1),
                "p": pp if pp is not None else p,
                "p_src": "実測" if pp is not None else "推定"}

    # ① 堅い（人気どおり）
    C.append(Cand("単勝集中", "堅い＝人気どおりに決まる", [P("単勝", [hon], p1[hon])],
                  "本命が勝つと踏むなら単勝に集中するのが最も素直"))
    C.append(Cand("馬単◎1着流し", "堅い＝本命が勝ち2着が割れる",
                  [P("馬単", [hon, u], p_exacta(hon, u, p1)) for u in pop4],
                  "1着を本命に固定して2着だけ流す"))
    # ② 人気馬が勝つが2-3着が荒れる
    C.append(Cand("3連複◎軸流し", "本命は勝つが2-3着が荒れる",
                  [P("3連複", sorted((hon, x, y)), p_trio(hon, x, y, p1))
                   for x, y in itertools.combinations(pop4, 2) if hon not in (x, y)],
                  "本命を軸に2-3着を人気上位で埋める"))
    C.append(Cand("ワイド◎流し", "本命は3着内。相手は広く",
                  [P("ワイド", sorted((hon, u)), p_pair_top3(hon, u, t3)) for u in pop4]))
    C.append(Cand("馬連◎流し", "本命が1-2着に入る",
                  [P("馬連", sorted((hon, u)), p_quinella(hon, u, p1)) for u in pop4]))
    # ③ 上位拮抗
    C.append(Cand("馬連BOX3", "上位3頭が拮抗",
                  [P("馬連", sorted(c), p_quinella(*c, p1)) for c in itertools.combinations([hon] + aite[:2], 2)]))
    C.append(Cand("ワイドBOX3", "上位3頭が拮抗（取りこぼしを減らす）",
                  [P("ワイド", sorted(c), p_pair_top3(*c, t3)) for c in itertools.combinations([hon] + aite[:2], 2)]))
    # ④ 穴・中穴が勝てる
    if ana:
        others = [u for u in pop[:7] if u != ana][:5]
        C.append(Cand("ワイド穴軸流し", f"穴（{name[ana]}）が勝ち負けできる",
                      [P("ワイド", sorted((ana, u)), p_pair_top3(ana, u, t3)) for u in others],
                      "指数が良いのに人気がない馬から広く流す"))
        C.append(Cand("馬連穴軸流し", f"穴（{name[ana]}）が勝ち負けできる",
                      [P("馬連", sorted((ana, u)), p_quinella(ana, u, p1)) for u in others[:4]]))
        C.append(Cand("3連複2列目", f"穴（{name[ana]}）を2列目に入れる",
                      [P("3連複", sorted((hon, ana, u)), p_trio(hon, ana, u, p1))
                       for u in others[:5] if u not in (hon, ana)],
                      "本命と穴の2頭軸で3列目を流す"))
    for c in C:
        c.points = [p for p in c.points if p]
    C = [c for c in C if c.points]
    return C, p1, t3, hon, ana


def allocate(points, budget):
    """推定配当に反比例（どれが当たっても戻りが揃う）・100円単位"""
    w = [1 / p["est"] for p in points]
    tot = sum(w)
    amts = [max(100, int(round(budget * x / tot / 100)) * 100) for x in w]
    amts[amts.index(max(amts))] += budget - sum(amts)
    for p, m in zip(points, amts):
        p["amt"] = m
    return points


def score_candidate(c: Cand, budget: int):
    pts = sorted(c.points, key=lambda p: -p["p"])[:10]
    allocate(pts, budget)
    ev = sum(p["p"] * p["amt"] * p["est"] for p in pts) / budget
    hit = min(0.99, sum(p["p"] for p in pts))
    over = sum(1 / p["est"] for p in pts)
    honsen = max(pts, key=lambda p: p["amt"])
    prior = PRIOR.get(c.name, 1.0)
    ok = over <= 1.0 and honsen["est"] >= MIN_HONSEN_EST
    return dict(cand=c, points=pts, ev=ev, hit=hit, over=over, prior=prior,
                adj=ev * prior, honsen=honsen, ok=ok,
                ng=("Σ>1.0" if over > 1.0 else "") + ("" if honsen["est"] >= MIN_HONSEN_EST else "本線が安い"))
