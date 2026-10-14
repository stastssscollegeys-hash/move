# -*- coding: utf-8 -*-
"""
strategy_tournament.py — 買い方（戦略）を同じ物差しで一斉に比べる「戦略トーナメント」（2026-10-14）
=====================================================================================================
狙い: 「どの買い方・どの条件が長い目で回収率100%を超えるか」を、後付けの当たり探しにならない形で決める。
  1) 年ごとの前向き検証（その年より前だけで学習 → その年を予測）のモデル確率を一度だけ作って保存（--build）
  2) 戦略（券種×選び方×条件）を全部、同じレース・同じ実際の払戻で採点
  3) 発見期間（2019〜2023）で候補を選ぶ → 確認期間（2024〜）で同じ条件のまま通用するかを見る
     ・発見期間の選抜は「多く試すほど偶然の当たりが混ざる」ので Benjamini-Hochberg（q=0.10）で絞る
     ・確認期間で 回収率>100% かつ 95%区間の下限も見る。採用基準（300R・下限>100%）は変えない
注意: オッズは確定オッズ（締切直前に近い）。実際に買う時刻のオッズとはずれる → 採用前に前向き台帳で確かめる
使い方:
  python strategy_tournament.py --build        # 年ごとの学習→確率を _cache/walk_probs.pkl へ（約5〜10分・メモリ3GB前後）
  python strategy_tournament.py                # 採点して docs/ に報告（数十秒）
"""
from __future__ import annotations
import argparse, collections, itertools, json, math, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
CACHE = HERE / "_cache" / "walk_probs.pkl"
REGISTRY = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "strategy_registry.json"   # 事前登録（条件を固定し、登録日より後のレースだけで判定）
DISCOVER = ("2019", "2023")
CONFIRM_FROM = "2024"


# ── 1) 年ごとの前向き確率を作る ───────────────────────────────────
def build_cache(first=2019, l2=0.01):
    import ev_engine as E
    import predict_day as P
    E.SOURCE = P.HIST
    races, _ = E.build()
    years = sorted({r["key"][0][:4] for r in races})
    out = []
    for y in years:
        if int(y) < first:
            continue
        tr = [r for r in races if r["key"][0][:4] < y]
        te = [r for r in races if r["key"][0][:4] == y]
        if len(tr) < 5000 or not te:
            continue
        beta, w = E.fit(E.pack(tr), l2)
        for r in te:
            out.append(dict(key=r["key"], uma=list(r["uma"]), odds=r["odds"].astype(float), q=np.asarray(r["q"], float),
                            p=E.probs(r, beta, w), fins=list(r["fins"])))
        print(f"  {y}: {len(te):,}レース（学習 {len(tr):,}）", flush=True)
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_bytes(pickle.dumps(out))
    print(f"保存: {CACHE}（{len(out):,}レース）")


# ── 2) レースの条件と払戻 ─────────────────────────────────────────
def load_meta():
    import predict_day as P
    meta, pay = {}, {}
    for f in sorted(Path(P.HIST).glob("results_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            k = (r["date"], r["競馬場"], int(float(r["R"])))
            if k in meta:
                continue
            d = str(r.get("距離") or "")
            c = str(r.get("条件") or "")
            cls = ("新馬" if "新馬" in c else "未勝利" if "未勝利" in c else "1勝" if "1勝" in c else "2勝" if "2勝" in c
                   else "3勝" if "3勝" in c else "重賞" if c[:2] in ("G1", "G2", "G3") else "OP")
            try:
                m = int("".join(ch for ch in d if ch.isdigit()))
            except ValueError:
                m = 0
            meta[k] = dict(surf="芝" if d.startswith("芝") else "ダ", m=m, cls=cls, baba=r.get("馬場状態") or "",
                           venue=r["競馬場"])
    for f in sorted(Path(P.HIST).glob("payouts_*.json")):
        for k, v in json.loads(f.read_text(encoding="utf-8")).items():
            d, vn, R = k.split("|")
            pay[(d, vn, int(R))] = v
    return meta, pay


# ── 確率の道具（Harville） ──────────────────────────────────────────
def harv_pair(p, i, j):                  # i,j が1-2着（順不同）
    return p[i] * p[j] / (1 - p[i]) + p[j] * p[i] / (1 - p[j])


def harv_exacta(p, i, j):
    return p[i] * p[j] / (1 - p[i])


def harv_tri(p, i, j, k):                # i→j→k
    return p[i] * p[j] / (1 - p[i]) * p[k] / (1 - p[i] - p[j])


def harv_place(p, i):                    # 3着内（Harville・全頭）
    n = len(p)
    s = p[i]
    for j in range(n):
        if j == i:
            continue
        s += harv_exacta(p, j, i)
        for k in range(n):
            if k in (i, j):
                continue
            s += harv_tri(p, j, k, i)
    return s


def harv_wide(p, i, j):                  # i,j がともに3着内
    n = len(p)
    s = 0.0
    for a, b in ((i, j), (j, i)):
        s += harv_exacta(p, a, b)
        for k in range(n):
            if k in (i, j):
                continue
            s += harv_tri(p, a, k, b) + harv_tri(p, k, a, b)
    return s


def key2(a, b):
    return "-".join(str(x) for x in sorted((a, b)))


def key3(a, b, c):
    return "-".join(str(x) for x in sorted((a, b, c)))


# ── 3) 戦略 ─────────────────────────────────────────────────────────
# 各戦略は race → [(券種, 組番の文字列, 賭け金)] を返す。100円単位。
def S(r):
    """よく使う並びを1回だけ計算"""
    if "_rank" not in r:
        r["_rank"] = list(np.argsort(-r["p"]))
        r["_qrank"] = list(np.argsort(-r["q"]))
        r["_ratio"] = r["p"] / r["q"]
    return r


def u(r, i):
    return r["uma"][i]


def st_win_fav(r):
    i = S(r)["_qrank"][0]
    return [("単勝", str(u(r, i)), 100)]


def st_win_top(r):
    i = S(r)["_rank"][0]
    return [("単勝", str(u(r, i)), 100)]


def mk_win_ev(t, lo=1.0, hi=1e9):
    def f(r):
        ev = r["p"] * r["odds"]
        return [("単勝", str(u(r, i)), 100) for i in range(len(ev)) if ev[i] >= t and lo <= r["odds"][i] < hi]
    return f


def mk_win_ratio(t, hi=20.0):
    def f(r):
        ra = S(r)["_ratio"]
        return [("単勝", str(u(r, i)), 100) for i in range(len(ra)) if ra[i] >= t and r["odds"][i] < hi]
    return f


def st_win_kelly(r):
    """ケリーの1/4で賭け金を変える（1R上限1,000円）。期待値が高いほど厚く"""
    out = []
    for i in range(len(r["p"])):
        o, p = r["odds"][i], r["p"][i]
        if p * o <= 1.0 or o >= 20:
            continue
        k = (p * o - 1) / (o - 1) / 4
        units = int(min(10, max(0, round(k * 100))))      # 資金1万円の想定で 100円単位
        if units:
            out.append(("単勝", str(u(r, i)), 100 * units))
    return out


def mk_place_ratio(t, top_only=True):
    def f(r):
        S(r)
        cands = r["_rank"][:3]
        out = []
        for i in cands:
            if harv_place(r["p"], i) / harv_place(r["q"], i) >= t:
                out.append(("複勝", str(u(r, i)), 100))
                if top_only:
                    break
        return out
    return f


def st_place_top(r):
    i = S(r)["_rank"][0]
    return [("複勝", str(u(r, i)), 100)]


def st_q_top2(r):
    a, b = S(r)["_rank"][:2]
    return [("馬連", key2(u(r, a), u(r, b)), 100)]


def mk_q_ratio(t, pool=4):
    """上位pool頭の組で、モデルの馬連確率/市場の馬連確率 ≥ t の組を全部"""
    def f(r):
        S(r)
        out = []
        for a, b in itertools.combinations(r["_rank"][:pool], 2):
            if harv_pair(r["p"], a, b) / harv_pair(r["q"], a, b) >= t:
                out.append(("馬連", key2(u(r, a), u(r, b)), 100))
        return out
    return f


def st_q_box3(r):
    t = S(r)["_rank"][:3]
    return [("馬連", key2(u(r, a), u(r, b)), 100) for a, b in itertools.combinations(t, 2)]


def st_wide_top2(r):
    a, b = S(r)["_rank"][:2]
    return [("ワイド", key2(u(r, a), u(r, b)), 100)]


def st_wide_nagashi(r):
    t = S(r)["_rank"]
    return [("ワイド", key2(u(r, t[0]), u(r, x)), 100) for x in t[1:4]]


def mk_wide_ratio(t, pool=5):
    def f(r):
        S(r)
        out = []
        for a, b in itertools.combinations(r["_rank"][:pool], 2):
            if harv_wide(r["p"], a, b) / harv_wide(r["q"], a, b) >= t:
                out.append(("ワイド", key2(u(r, a), u(r, b)), 100))
        return out
    return f


def st_exacta_12(r):
    a, b = S(r)["_rank"][:2]
    return [("馬単", f"{u(r, a)}-{u(r, b)}", 100)]


def mk_exacta_ratio(t, pool=4):
    def f(r):
        S(r)
        out = []
        for a, b in itertools.permutations(r["_rank"][:pool], 2):
            if harv_exacta(r["p"], a, b) / harv_exacta(r["q"], a, b) >= t:
                out.append(("馬単", f"{u(r, a)}-{u(r, b)}", 100))
        return out
    return f


def st_trio_box4(r):
    t = S(r)["_rank"][:4]
    return [("3連複", key3(*(u(r, x) for x in c)), 100) for c in itertools.combinations(t, 3)]


def st_trio_axis(r):
    t = S(r)["_rank"]
    return [("3連複", key3(u(r, t[0]), u(r, a), u(r, b)), 100) for a, b in itertools.combinations(t[1:5], 2)]


def mk_trio_ratio(t, pool=6):
    def f(r):
        S(r)
        out = []
        for c in itertools.combinations(r["_rank"][:pool], 3):
            pm = sum(harv_tri(r["p"], *pp) for pp in itertools.permutations(c))
            pq = sum(harv_tri(r["q"], *pp) for pp in itertools.permutations(c))
            if pm / pq >= t:
                out.append(("3連複", key3(*(u(r, x) for x in c)), 100))
        return out
    return f


def st_tri_form(r):
    t = S(r)["_rank"]
    return [("3連単", f"{u(r, t[0])}-{u(r, b)}-{u(r, c)}", 100) for b in t[1:3] for c in t[1:4] if b != c]


def mk_tri_ratio(t, pool=5):
    def f(r):
        S(r)
        out = []
        for c in itertools.permutations(r["_rank"][:pool], 3):
            if harv_tri(r["p"], *c) / harv_tri(r["q"], *c) >= t:
                out.append(("3連単", "-".join(str(u(r, x)) for x in c), 100))
        return out
    return f


BASE = {
    # 単勝
    "単勝・1番人気（比較用）": st_win_fav,
    "単勝・モデル1位": st_win_top,
    "単勝・EV≧1.0": mk_win_ev(1.0),
    "単勝・EV≧1.1": mk_win_ev(1.1),
    "単勝・EV≧1.2": mk_win_ev(1.2),
    "単勝・EV≧1.3": mk_win_ev(1.3),
    "単勝・EV≧1.0・10倍以下": mk_win_ev(1.0, hi=10),
    "単勝・EV≧1.0・3〜6倍（T1）": mk_win_ev(1.0, 3, 6),
    "単勝・EV≧1.1・20倍以下": mk_win_ev(1.1, hi=20),
    "単勝・比≧1.2・20倍以下": mk_win_ratio(1.2),
    "単勝・比≧1.3・20倍以下": mk_win_ratio(1.3),
    "単勝・比≧1.5・20倍以下": mk_win_ratio(1.5),
    "単勝・ケリー1/4": st_win_kelly,
    # 複勝
    "複勝・モデル1位": st_place_top,
    "複勝・上位3頭で比≧1.1の最上位": mk_place_ratio(1.1),
    "複勝・上位3頭で比≧1.2の最上位": mk_place_ratio(1.2),
    # 馬連
    "馬連・モデル1-2位": st_q_top2,
    "馬連・上位3頭ボックス": st_q_box3,
    "馬連・上位4頭で比≧1.3": mk_q_ratio(1.3),
    "馬連・上位4頭で比≧1.5": mk_q_ratio(1.5),
    # ワイド
    "ワイド・モデル1-2位": st_wide_top2,
    "ワイド・1位から2〜4位へ流し": st_wide_nagashi,
    "ワイド・上位5頭で比≧1.3": mk_wide_ratio(1.3),
    "ワイド・上位5頭で比≧1.5": mk_wide_ratio(1.5),
    # 馬単
    "馬単・モデル1→2位": st_exacta_12,
    "馬単・上位4頭で比≧1.5": mk_exacta_ratio(1.5),
    # 3連複
    "3連複・上位4頭ボックス": st_trio_box4,
    "3連複・1位軸で2〜5位へ流し": st_trio_axis,
    "3連複・上位6頭で比≧1.5": mk_trio_ratio(1.5),
    "3連複・上位6頭で比≧2.0": mk_trio_ratio(2.0),
    # 3連単
    "3連単・1位→2,3位→2〜4位": st_tri_form,
    "3連単・上位5頭で比≧2.0": mk_tri_ratio(2.0),
    "3連単・上位5頭で比≧3.0": mk_tri_ratio(3.0),
}

SEGMENTS = {
    "全レース": lambda m: True,
    "芝": lambda m: m["surf"] == "芝",
    "ダート": lambda m: m["surf"] == "ダ",
    "1400m以下": lambda m: 0 < m["m"] <= 1400,
    "1500〜1800m": lambda m: 1500 <= m["m"] <= 1800,
    "1900m以上": lambda m: m["m"] >= 1900,
    "新馬": lambda m: m["cls"] == "新馬",
    "未勝利": lambda m: m["cls"] == "未勝利",
    "1勝クラス": lambda m: m["cls"] == "1勝",
    "2勝・3勝": lambda m: m["cls"] in ("2勝", "3勝"),
    "OP・重賞": lambda m: m["cls"] in ("OP", "重賞"),
    "良馬場": lambda m: m["baba"] == "良",
    "道悪（稍重〜不良）": lambda m: m["baba"] in ("稍重", "重", "不良"),
    "10頭以下": lambda m: m["n"] <= 10,
    "11〜14頭": lambda m: 11 <= m["n"] <= 14,
    "15頭以上": lambda m: m["n"] >= 15,
}
# 条件で分けるのは 期待値型の買い方だけ（全部掛け合わせると試行が多すぎて偶然が混ざる）
SEG_STRATS = ["単勝・EV≧1.0", "単勝・EV≧1.0・10倍以下", "単勝・比≧1.3・20倍以下", "複勝・上位3頭で比≧1.1の最上位",
              "馬連・上位4頭で比≧1.3", "ワイド・上位5頭で比≧1.3", "3連複・上位6頭で比≧1.5", "3連単・上位5頭で比≧2.0"]


# ── 4) 採点 ─────────────────────────────────────────────────────────
def settle(bets, pay):
    ret = 0
    for kind, combo, stake in bets:
        v = (pay.get(kind) or {}).get(combo)
        if v:
            ret += v * stake // 100
    return ret


def boot(st, rt, n=2000, seed=7):
    """レース単位ブートストラップ: 回収率の95%区間と「回収率≦100%」の片側p値"""
    if st.sum() == 0:
        return None, None, None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(st), size=(n, len(st)))
    s, r = st[idx].sum(axis=1), rt[idx].sum(axis=1)
    x = r[s > 0] / s[s > 0]
    return rt.sum() / st.sum(), float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975)), float((x <= 1.0).mean())


def bh(pvals, q=0.10):
    """Benjamini-Hochberg: 通過したインデックスの集合"""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, k = len(pvals), 0
    for rank, i in enumerate(order, 1):
        if pvals[i] <= q * rank / m:
            k = rank
    return set(order[:k])


def run(report_path=None):
    races = pickle.loads(CACHE.read_bytes())
    meta, pay = load_meta()
    rows = []
    for r in races:
        k = r["key"]
        if k not in meta or k not in pay:
            continue
        m = dict(meta[k], n=len(r["uma"]))
        rows.append((r, m, pay[k]))
    print(f"■ 採点対象 {len(rows):,}レース（{rows[0][0]['key'][0]}〜{rows[-1][0]['key'][0]}）")

    # 戦略×条件ごとに レース単位の (賭け金, 戻り, 年) を溜める
    combos = [(s, "全レース") for s in BASE] + [(s, g) for s in SEG_STRATS for g in SEGMENTS if g != "全レース"]
    acc = {c: ([], [], [], []) for c in combos}            # stake, ret, year, hit
    for r, m, pv in rows:
        y = r["key"][0][:4]
        segs = [g for g, f in SEGMENTS.items() if f(m)]
        cache = {}
        for s, g in combos:
            if g not in segs:
                continue
            if s not in cache:
                b = BASE[s](r)
                cache[s] = (sum(x[2] for x in b), settle(b, pv)) if b else (0, 0)
            st, rt = cache[s]
            if st == 0:
                continue
            a = acc[(s, g)]
            a[0].append(st); a[1].append(rt); a[2].append(y); a[3].append(rt > 0)

    def stats(c, lo_y, hi_y):
        st, rt, ys, hit = (np.array(v) for v in acc[c])
        if len(st) == 0:
            return None
        sel = (ys >= lo_y) & (ys <= hi_y)
        if sel.sum() == 0:
            return None
        s, r_, h = st[sel], rt[sel], hit[sel]
        roi, lo, hi, pv = boot(s.astype(float), r_.astype(float))
        yrs = sorted(set(ys[sel]))
        per = {yy: r_[ys[sel] == yy].sum() / s[ys[sel] == yy].sum() for yy in yrs}
        return dict(n=int(sel.sum()), bets=int(s.sum() // 100), roi=roi, lo=lo, hi=hi, p=pv, hit=float(h.mean()),
                    pos=sum(1 for v in per.values() if v > 1), years=len(yrs), per=per, profit=int(r_.sum() - s.sum()))

    disc = {c: stats(c, *DISCOVER) for c in combos}
    conf = {c: stats(c, CONFIRM_FROM, "9999") for c in combos}
    full = {c: stats(c, "0000", "9999") for c in combos}
    valid = [c for c in combos if disc[c] and disc[c]["n"] >= 300]
    passed = bh([disc[c]["p"] for c in valid], q=0.10)
    sel = [valid[i] for i in passed]

    L = []
    pr = L.append
    pr(f"# 戦略トーナメント（{rows[0][0]['key'][0]}〜{rows[-1][0]['key'][0]}・{len(rows):,}レース）\n")
    pr("年ごとの前向き検証（その年より前だけで学習）の確率で、各戦略を確定オッズ・実際の払戻で採点。"
       f"発見期間 {DISCOVER[0]}〜{DISCOVER[1]}、確認期間 {CONFIRM_FROM}〜。試した組み合わせ {len(combos)} 通り"
       f"（うち発見期間300R以上 {len(valid)}）。\n")
    pr("## 1. 買い方ごと（全レース・全期間）\n")
    pr("| 戦略 | レース | 点数 | 的中率(R) | 回収率 | 95%区間 | プラスの年 | 収支(円) | 年別 |")
    pr("|---|---:|---:|---:|---:|---|---:|---:|---|")
    for s in BASE:
        f = full[(s, "全レース")]
        if not f:
            continue
        per = " ".join(f"{v * 100:.0f}" for v in f["per"].values())
        pr(f"| {s} | {f['n']:,} | {f['bets']:,} | {f['hit'] * 100:.1f}% | **{f['roi'] * 100:.1f}%** | "
           f"{f['lo'] * 100:.1f}〜{f['hi'] * 100:.1f}% | {f['pos']}/{f['years']} | {f['profit']:+,} | {per} |")
    pr("\n## 2. 発見期間で偶然を補正しても残った候補 → 確認期間での成績\n")
    pr("発見期間の片側p値に Benjamini-Hochberg（q=0.10）。残った候補だけを確認期間で見る（確認期間の数字で選び直さない）。\n")
    if not sel:
        pr("**発見期間で補正後に残った戦略はなし。**（下の表は補正前の上位。参考扱い）\n")
    pr("| 戦略 | 条件 | 発見: R | 発見: 回収率［95%］ | p値 | 確認: R | 確認: 回収率［95%］ | 確認: 的中率 | 判定 |")
    pr("|---|---|---:|---|---:|---:|---|---:|---|")
    show = sel if sel else sorted(valid, key=lambda c: disc[c]["p"])[:15]
    for c in sorted(show, key=lambda c: disc[c]["p"]):
        d, k = disc[c], conf[c]
        if k:
            ok = ("◎ 確認でも下限>100%" if k["lo"] > 1 and k["n"] >= 300 else "○ 確認でも100%超" if k["roi"] > 1 else "× 確認で100%割れ")
            kc = f"{k['n']:,} | {k['roi'] * 100:.1f}%［{k['lo'] * 100:.0f}〜{k['hi'] * 100:.0f}］ | {k['hit'] * 100:.1f}%"
        else:
            ok, kc = "－", "－ | － | －"
        pr(f"| {c[0]} | {c[1]} | {d['n']:,} | {d['roi'] * 100:.1f}%［{d['lo'] * 100:.0f}〜{d['hi'] * 100:.0f}］ | {d['p']:.3f} | {kc} | {ok} |")
    pr("\n## 3. 条件別（期待値型の買い方 × 条件・全期間）\n")
    for s in SEG_STRATS:
        pr(f"\n### {s}\n")
        pr("| 条件 | レース | 的中率 | 回収率 | 95%区間 | プラスの年 | 発見→確認 |")
        pr("|---|---:|---:|---:|---|---:|---|")
        for g in SEGMENTS:
            f = full.get((s, g))
            if not f:
                continue
            d, k = disc.get((s, g)), conf.get((s, g))
            dk = f"{d['roi'] * 100:.0f}%→{k['roi'] * 100:.0f}%" if d and k else "－"
            pr(f"| {g} | {f['n']:,} | {f['hit'] * 100:.1f}% | {f['roi'] * 100:.1f}% | {f['lo'] * 100:.0f}〜{f['hi'] * 100:.0f}% | {f['pos']}/{f['years']} | {dk} |")
    if REGISTRY.exists():
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        pr("\n## 4. 事前登録した候補の登録後の成績（ここだけが本当の答え合わせ）\n")
        pr("| ID | 戦略 | 条件 | 登録日 | 登録後: R | 的中率 | 回収率［95%］ | 収支(円) |")
        pr("|---|---|---|---|---:|---:|---|---:|")
        for c in reg["candidates"]:
            st, rt, hit = [], [], []
            for r, m, pv in rows:
                if r["key"][0] < c["eval_from"] or not SEGMENTS[c["segment"]](m):
                    continue
                b = BASE[c["strategy"]](r)
                if b:
                    s_, r_ = sum(x[2] for x in b), settle(b, pv)
                    st.append(s_); rt.append(r_); hit.append(r_ > 0)
            if st:
                roi, lo, hi, _ = boot(np.array(st, float), np.array(rt, float))
                pr(f"| {c['id']} | {c['strategy']} | {c['segment']} | {c['eval_from']} | {len(st):,} | {np.mean(hit) * 100:.1f}% | "
                   f"{roi * 100:.1f}%［{lo * 100:.0f}〜{hi * 100:.0f}］ | {int(sum(rt) - sum(st)):+,} |")
            else:
                pr(f"| {c['id']} | {c['strategy']} | {c['segment']} | {c['eval_from']} | 0 | － | － | － |")
    text = "\n".join(L)
    out = Path(report_path) if report_path else HERE.parents[1] / "docs" / "keiba_strategy_tournament.md"
    out.write_text(text, encoding="utf-8")
    json_out = HERE / "_cache" / "strategy_tournament.json"
    json_out.write_text(json.dumps({f"{c[0]}|{c[1]}": dict(full=full[c], disc=disc[c], conf=conf[c]) for c in combos if full[c]},
                                   ensure_ascii=False, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else str(o), indent=1), encoding="utf-8")
    print(text)
    print(f"\n保存: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--first", type=int, default=2019)
    ap.add_argument("--report")
    a = ap.parse_args()
    if a.build:
        build_cache(a.first)
    else:
        run(a.report)
