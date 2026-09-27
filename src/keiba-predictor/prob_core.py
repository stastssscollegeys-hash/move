# -*- coding: utf-8 -*-
"""
prob_core.py — 確率の土台を1本にする（2026-09-27・システム再検証を受けて新設）
================================================================================
再検証（index_audit_leakfree.py・レース前records 523R）で分かったこと:
  ・総合指数1位の単勝回収 68.8%［53〜86%］ ＜ 市場1番人気 86.1%
  ・同じ人気帯の中で「指数1位」は他馬と差がない（±4pt）＝指数は市場に無い情報を持たない
  ・確率を順位テーブル／人気帯から作っていたので、期待値は控除率（≒80%）に固定されていた

この module は **市場オッズを確率の唯一の源** にし、そこに
**両関門（全体＋後半期間で有意）を通った要素だけ** を掛ける。
現時点で通っているのは2つ、どちらも「消し」方向（pdca_rounds.py・2026-09-25 と 09-27 の2回で再現）:
  ・斤量有利70以上（F10_斤量 >= 70）      … 同人気帯より3着内率 -1.15pt（obs/exp = 582/616.9 = 0.94・n=3,031）
  ・馬体重 -10kg以下                      … 同人気帯より3着内率 -1.48pt（obs/exp = 315/343.8 = 0.92・n=1,953）
加点候補（種牡馬×条件・指数差6以上）は在サンプルなので **前向き判定が終わるまで入れない**。

使い方（他モジュールから）:
    from prob_core import market_probs, adjust, top3_scenarios, ticket_probs, marks
    q  = market_probs({1: 3.5, 2: 8.2, ...})           # 単勝オッズ → 勝率
    p  = adjust(q, {1: {"kin70": True}, 5: {"wt_m10": True}})
    sc = top3_scenarios(p)                              # (1着,2着,3着) → 確率（λ-Harville）
    tp = ticket_probs(sc, p)                            # 単勝/複勝/馬連/ワイド/馬単/3連複 → 確率
    mk = marks(p, q)                                    # ◎○▲△△🔥

検証（このファイル単体）: python prob_core.py   → 市場のみ vs 消し補正後 を leak-free 523R で比較
"""
from __future__ import annotations
import collections, itertools, json, sys
from pathlib import Path

LAMBDA = (1.00, 0.80, 0.70)      # kaime_design_v7 と同じ（自前1,111Rで推定）
TOPN = 8                          # 3着内シナリオを列挙する上位頭数（それ以下は「候補外」として確率を残す）
COVERED = 0.80                    # 上位8頭で決まる決着の割合（残り20%は候補外）

# 両関門を通った要素だけ。値は「同じ人気帯の期待3着内数に対する実測の比」。
KESHI = {
    "kin70":  0.94,   # 斤量有利70以上   pdca_rounds #77
    "wt_m10": 0.92,   # 馬体重-10kg以下  pdca_rounds #49
}


def market_probs(tan: dict[int, float]) -> dict[int, float]:
    """単勝オッズ → 正規化した勝率。0.8/odds の 0.8 は正規化で消えるので 1/odds でよい"""
    inv = {u: 1.0 / o for u, o in tan.items() if o and o > 0}
    s = sum(inv.values()) or 1.0
    return {u: v / s for u, v in inv.items()}


def adjust(q: dict[int, float], flags: dict[int, dict] | None) -> dict[int, float]:
    """消し要素を掛けて再正規化。flags[馬番] = {"kin70": bool, "wt_m10": bool}"""
    if not flags:
        return dict(q)
    p = {}
    for u, v in q.items():
        f = flags.get(u) or {}
        for k, mult in KESHI.items():
            if f.get(k):
                v *= mult
        p[u] = v
    s = sum(p.values()) or 1.0
    return {u: v / s for u, v in p.items()}


def top3_scenarios(p: dict[int, float]) -> dict[tuple, float]:
    """λ-Harville で (1着,2着,3着) の確率。上位TOPN頭だけ列挙し、合計をCOVEREDに揃える"""
    pool = sorted(p, key=lambda u: -p[u])[:TOPN]
    out = {}
    for perm in itertools.permutations(pool, 3):
        rest = {u: max(p[u], 1e-4) for u in pool}
        pr = 1.0
        for i, u in enumerate(perm):
            w = {k: v ** LAMBDA[i] for k, v in rest.items()}
            tot = sum(w.values())
            pr *= w[u] / tot
            del rest[u]
        out[perm] = pr
    tot = sum(out.values()) or 1.0
    return {k: v / tot * COVERED for k, v in out.items()}


def ticket_probs(sc: dict[tuple, float], p: dict[int, float]) -> dict[str, dict[tuple, float]]:
    """券種ごとの組み合わせ確率。単勝は p そのまま、その他はシナリオを畳む"""
    t = {"単勝": {(u,): v for u, v in p.items()},
         "複勝": collections.defaultdict(float), "馬連": collections.defaultdict(float),
         "ワイド": collections.defaultdict(float), "馬単": collections.defaultdict(float),
         "3連複": collections.defaultdict(float)}
    for (a, b, c), pr in sc.items():
        for u in (a, b, c):
            t["複勝"][(u,)] += pr
        t["馬連"][tuple(sorted((a, b)))] += pr
        t["馬単"][(a, b)] += pr
        for x, y in ((a, b), (a, c), (b, c)):
            t["ワイド"][tuple(sorted((x, y)))] += pr
        t["3連複"][tuple(sorted((a, b, c)))] += pr
    return {k: dict(v) for k, v in t.items()}


def marks(p: dict[int, float], q: dict[int, float] | None = None) -> dict:
    """印は補正後確率の順。🔥は市場より上がった馬（消しの反射で上がる）のうち最も比が大きい8番人気以下"""
    order = sorted(p, key=lambda u: -p[u])
    mk = {"◎": order[0], "○": order[1] if len(order) > 1 else None,
          "▲": order[2] if len(order) > 2 else None, "△": order[3:5]}
    if q:
        pop = {u: i + 1 for i, u in enumerate(sorted(q, key=lambda u: -q[u]))}
        cands = [u for u in p if pop[u] >= 8 and u not in order[:5]]
        mk["🔥"] = max(cands, key=lambda u: p[u] / max(q[u], 1e-9)) if cands else None
    return mk


# ────────────────────────────────────────────────────────────────────────
# 検証: 市場のみ vs 消し補正後（leak-free records）
# ────────────────────────────────────────────────────────────────────────
def _weight_diff(s):
    """'480(-14)' → -14"""
    import re
    m = re.search(r"\(([+-]?\d+)\)", str(s or ""))
    return int(m.group(1)) if m else None


def _eval():
    import datetime
    sys.stdout.reconfigure(encoding="utf-8")
    BASE = Path.home() / "Desktop" / "競馬予想レポート"
    DB = BASE / "daily_pdca" / "db"
    pre = {}
    for f in sorted(BASE.glob("**/週末ビッグデータ_*_records.json")):
        try:
            rs = json.load(open(f, encoding="utf-8")).get("records", [])
        except Exception:
            continue
        if not rs:
            continue
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).date()
        last = max(r["date"] for r in rs)
        if mtime > datetime.date(int(last[:4]), int(last[4:6]), int(last[6:8])):
            continue
        for r in rs:
            pre.setdefault((r["date"], r["競馬場"], int(r["R"])), {})[int(float(r["馬番"]))] = r
    res = collections.defaultdict(dict)
    for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8")):
        try:
            res[(r["date"], r["競馬場"], int(r["R"]))][int(float(r["馬番"]))] = r
        except (TypeError, ValueError):
            pass

    def fin(r):
        v = r.get("着順int")
        if v:
            return int(v)
        s = str(r.get("着順") or "")
        return int(s) if s.isdigit() else None

    stats = {"市場のみ◎": [], "消し補正後◎": []}
    changed = 0
    for k, horses in pre.items():
        rows = res.get(k)
        if not rows:
            continue
        tan, flags, out = {}, {}, {}
        for u, rec in horses.items():
            q = rows.get(u)
            if not q or not fin(q):
                continue
            try:
                tan[u] = float(q["単勝オッズ"])
            except (TypeError, ValueError):
                continue
            wd = _weight_diff(q.get("馬体重"))
            flags[u] = {"kin70": float(rec.get("F10_斤量") or 0) >= 70,
                        "wt_m10": wd is not None and wd <= -10}
            out[u] = (fin(q), tan[u])
        if len(tan) < 8:
            continue
        q = market_probs(tan)
        p = adjust(q, flags)
        a, b = max(q, key=q.get), max(p, key=p.get)
        changed += a != b
        stats["市場のみ◎"].append(out[a])
        stats["消し補正後◎"].append(out[b])
    print(f"■ leak-free {len(stats['市場のみ◎'])}レース ／ 消しで◎が変わったレース {changed}")
    print(f"{'◎の決め方':<10}{'1着率':>8}{'3着内':>8}{'単勝回収':>9}")
    for lab, xs in stats.items():
        n = len(xs)
        w = sum(1 for f, o in xs if f == 1) / n * 100
        p3 = sum(1 for f, o in xs if f <= 3) / n * 100
        roi = sum(o * 100 for f, o in xs if f == 1) / (n * 100) * 100
        print(f"{lab:<10}{w:>7.1f}%{p3:>7.1f}%{roi:>8.1f}%")
    print("\n  消しが◎を動かしたレースだけ:")
    sub = [(x, y) for x, y in zip(stats["市場のみ◎"], stats["消し補正後◎"]) if x != y]
    if sub:
        for lab, idx in (("市場のみ◎", 0), ("消し補正後◎", 1)):
            xs = [t[idx] for t in sub]
            n = len(xs)
            print(f"  {lab:<10} n={n:>3} 1着{sum(1 for f,o in xs if f==1)/n*100:5.1f}% "
                  f"3着内{sum(1 for f,o in xs if f<=3)/n*100:5.1f}% 単勝回収{sum(o*100 for f,o in xs if f==1)/(n*100)*100:6.1f}%")


if __name__ == "__main__":
    _eval()
