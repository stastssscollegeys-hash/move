# -*- coding: utf-8 -*-
"""
kaime_select_live.py — 実オッズで買い方を選ぶ（2026-09-27新規）
=================================================================
kaime_select.py は payout_estimator で配当を推定していたが、極端な人気薄の組で
外挿になり、推定1,000倍・期待値1,112%のような信用できない数字が出た。

当日は **組み合わせ券種の実オッズが発売済み** なので、推定をやめて実オッズを使う。
的中率は band_hitrate.json（確定払戻1,536レース）の人気帯別実測を使う。
  → 期待値 ＝ 実測的中率 × 実オッズ。推定が一切入らない。

ガード: Σ(1/配当)≦1.0 ／ 本線は4.0倍以上 ／ 100円単位 ／ 3連単は使わない
使い方: build_live(snapshot_json, score) → 候補リスト
"""
from __future__ import annotations
import itertools, json
from pathlib import Path

_BH = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "band_hitrate.json"
BAND = json.loads(_BH.read_text(encoding="utf-8")) if _BH.exists() else {}
MIN_N = 300
MIN_HONSEN = 4.0
MIN_HIT = 0.10
# 券種別の「狙うべき期待値」の下限（dulbea方式・2026-09-27採用）。
# 期待値が最大の型を機械的に取るのではなく、まずこのしきい値を満たすかで足切りする。
EV_MIN = {"複勝": 1.1, "ワイド": 1.1, "単勝": 1.2, "馬連": 1.4, "馬単": 1.6,
          "3連複": 2.0, "3連単": 2.0}        # 1点以上当たる確率がこれ未満の型は選ばない。
#   人気薄どうしの帯は実測ROIが100%を超えることがあるが、的中率が数%しかなく
#   分散が大きい。帯スキャンでこの種の候補はhold-outで全滅している（2026-09-09）。


def _rate(t, pops):
    key = ">".join(str(x) for x in pops) if t == "馬単" else "-".join(str(x) for x in sorted(pops))
    d = BAND.get(t, {}).get(key)
    return d["rate"] if d and d["n"] >= MIN_N else None


def load_live(snap_path):
    """スナップショットから 単勝オッズ と 組み合わせ実オッズ を取り出す"""
    d = json.loads(Path(snap_path).read_text(encoding="utf-8"))
    tan = {int(k): float(v[0]) for k, v in d["odds"]["単勝"].items()}
    live = {}
    for t in ("複勝", "馬連", "ワイド", "馬単", "3連複"):
        o = d["odds"].get(t) or {}
        tbl = {}
        for k, v in o.items():
            nums = tuple(int(k[i:i + 2]) for i in range(0, len(k), 2))
            key = nums if t == "馬単" else tuple(sorted(nums))
            try:
                tbl[key] = float(v[0])
            except (TypeError, ValueError):
                continue
        live[t] = tbl
    live["単勝"] = {(u,): o for u, o in tan.items()}
    return tan, live, d


def build_live(tan, live, score, name):
    """実オッズだけで候補を作る"""
    pop = sorted(tan, key=lambda u: tan[u])
    pop_of = {u: i + 1 for i, u in enumerate(pop)}
    rank = sorted(tan, key=lambda u: -score.get(u, 0))
    hon = rank[0]
    aite = rank[1:5]
    pop4 = [u for u in pop[:5] if u != hon][:4]
    marked = set([hon] + aite)
    ana = next((u for u in rank if u not in marked and pop_of[u] >= 8), None)

    def P(t, combo):
        key = tuple(combo) if t == "馬単" else tuple(sorted(combo))
        o = live.get(t, {}).get(key)
        if not o:
            return None
        r = _rate(t, [pop_of[x] for x in combo])
        if r is None:
            return None
        return {"t": t, "combo": list(combo), "est": o, "p": r, "p_src": "実測"}

    def C(nm, kind, pts, note=""):
        pts = [p for p in pts if p]
        return dict(name=nm, kind=kind, points=pts, note=note) if pts else None

    out = [
        C("単勝集中", "堅い＝人気どおりに決まる", [P("単勝", [hon])]),
        C("馬単◎1着流し", "堅い＝本命が勝ち2着が割れる", [P("馬単", [hon, u]) for u in pop4]),
        C("3連複◎軸流し", "本命は勝つが2-3着が荒れる",
          [P("3連複", (hon, x, y)) for x, y in itertools.combinations(pop4, 2)]),
        C("ワイド◎流し", "本命は3着内。相手は広く", [P("ワイド", (hon, u)) for u in pop4]),
        C("馬連◎流し", "本命が1-2着に入る", [P("馬連", (hon, u)) for u in pop4]),
        C("馬連BOX3", "上位3頭が拮抗", [P("馬連", c) for c in itertools.combinations([hon] + aite[:2], 2)]),
        C("ワイドBOX3", "上位3頭が拮抗", [P("ワイド", c) for c in itertools.combinations([hon] + aite[:2], 2)]),
    ]
    if ana:
        others = [u for u in pop[:7] if u != ana][:5]
        out += [
            C("ワイド穴軸流し", f"穴（{name.get(ana, ana)}）が勝ち負けできる",
              [P("ワイド", (ana, u)) for u in others]),
            C("馬連穴軸流し", f"穴（{name.get(ana, ana)}）が勝ち負けできる",
              [P("馬連", (ana, u)) for u in others[:4]]),
            C("3連複2列目", f"穴（{name.get(ana, ana)}）を2列目に入れる",
              [P("3連複", (hon, ana, u)) for u in others[:5] if u not in (hon, ana)]),
        ]
    return [c for c in out if c], hon, ana, pop_of


def p_t_label(pts):
    ts = sorted({p["t"] for p in pts})
    return "・".join(ts)


def evaluate(c, budget):
    pts = sorted(c["points"], key=lambda p: -p["p"])[:10]
    w = [1 / p["est"] for p in pts]
    tot = sum(w)
    amts = [max(100, int(round(budget * x / tot / 100)) * 100) for x in w]
    amts[amts.index(max(amts))] += budget - sum(amts)
    for p, m in zip(pts, amts):
        p["amt"] = m
    ev = sum(p["p"] * p["amt"] * p["est"] for p in pts) / budget
    hit = min(0.99, sum(p["p"] for p in pts))
    over = sum(1 / p["est"] for p in pts)
    honsen = max(pts, key=lambda p: p["amt"])
    ng = []
    if over > 1.0:
        ng.append("Σ>1.0")
    if honsen["est"] < MIN_HONSEN:
        ng.append("本線が安い")
    if hit < MIN_HIT:
        ng.append(f"的中率{hit*100:.1f}%＝薄すぎ")
    need = max(EV_MIN.get(p["t"], 1.0) for p in pts)
    if ev < need:
        ng.append(f"期待値{ev:.2f}＜{p_t_label(pts)}の基準{need:.1f}")
    return dict(cand=c, points=pts, ev=ev, hit=hit, over=over, honsen=honsen,
                ok=not ng, ng="・".join(ng))
