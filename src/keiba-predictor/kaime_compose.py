# -*- coding: utf-8 -*-
"""
kaime_compose.py — 買い目の「パターン集」と「レースごとの当てはめ」（2026-10-30新規）
======================================================================================
ユーザー指示（2026-10-30）: 「買い目の構成は、本来は必要な数だけパターンを用意したい。最近は同じパターンしか
出てこないので、レースごとにそのパターンを当てはめて買い目を構成する仕組みにしてほしい」

なぜ作ったか
------------
・2026-10-10 から公開の買い目は V1.1（単勝◎＋馬連◎-○＋ワイド◎流し）の固定形で、全レース同じ形になっていた
・過去に「型を判定して買い方を選ぶ」仕組みは3回作られた（gen_kaime_v5 / kaime_patterns+kaime_select / race_type_v63）が、
  どれも毎日の予想（predict_day）の流れに入っておらず、固定形に戻っていた → 今回は predict_day.marks_and_bets の中に組み込む

何を変えるか／変えないか（正直に）
----------------------------------
・買い方を変えても回収率は変わらない（bet_structure_test.py: 24,927Rで V1〜V6 が 90〜93%）。
  変わるのは「何か当たる頻度」「当たったのにガミる割合」「外れ方」。パターン集の目的は、レースの型に合った形で、
  印が当たったときに馬券も当たりやすく、当たったら元が取れる形にすること。回収率を上げる仕組みではない
・回収率は印（確率の質）と「買う/買わない」の判断（B1ルール・台帳）で決まる。ここは別レーンのまま

予算と紐（2026-10-31追記・ユーザー指示）
--------------------------------------
・予算は基本1万円前後。旨味（買い目全体の期待回収率 e）が薄ければ点数を絞って少額、期待値が取れても上限15,000円（budget_for）
・紐（3着の相手）を足すかは、レースごとに足した点の期待値を計算して決める（compose の p_fn / extra / ev_odds_fn）。1点の金額は据え置いて点を足す
・p_fn を渡さない呼び出し（pattern_backtest.py など）は従来どおり固定予算。根拠は docs/keiba_himo_widening_20261031.md

使い方
------
  from kaime_compose import compose
  r = compose(M, ctx, odds_fn, day_counts)      # M = {"◎":馬番, "○":.., "▲":.., "△1":.., "△2":.., "🔥":..}
  r["plan"]    -> [(券種, [馬番...], 賭け金)]  100円単位・合計1万円以内
  r["pattern"] -> {"id","name","why"}
パターンを足すときは PATTERNS に dict を1つ足すだけ（applies と build）。足したら pattern_backtest.py で測る。
"""
from __future__ import annotations
import itertools
import math

BUDGET = 10000                  # 基本の予算（1万円前後）。旨味（期待回収率）で下の budget_for が増減する
BUDGET_MAX = 15000              # どんなに期待値が取れても上限（2026-10-31 ユーザー指示「1万円少し超えるぐらい・上限15,000円」）
WIDEN_MAX = 2                   # 紐（3着の相手）を足してよい最大頭数
WIDEN_MIN_EV = 0.50             # 足す紐の点の平均期待値（的中確率×オッズ）の下限
WIDEN_REL = 0.90                # かつ、既存の点の平均期待値の90%以上（期待値を薄めない）
PRUNE_EV = 0.50                 # 旨味が薄いとき、この期待値に満たない点は買わない
TAKE = {"単勝": 0.80, "複勝": 0.80, "馬連": 0.775, "ワイド": 0.775, "馬単": 0.75, "3連複": 0.75, "3連単": 0.725}


# ── レースの特徴（レース前に分かる情報だけ。結果リーク無し）──────────────────
def make_ctx(p, q, uma, M, pop):
    """p: モデル確率  q: 市場確率（どちらも合計1・uma と同じ並び）  M: 印→馬番  pop: 馬番→人気"""
    idx = {u: i for i, u in enumerate(uma)}

    def pm(m):
        return float(p[idx[M[m]]]) if m in M else 0.0

    q1 = float(max(q))
    kind = "堅い" if q1 >= 0.35 else "荒れ" if q1 < 0.20 else "普通"
    h, o, t = pm("◎"), pm("○"), pm("▲")
    top_unmarked = any(pop[u] <= 3 and u not in (M.get("◎"), M.get("○"), M.get("▲")) for u in pop)
    return dict(
        n=len(uma), q1=round(q1, 3), kind=kind,
        hon_pop=pop.get(M.get("◎"), 99), hon_p=h, p2=o, p3=t,
        gap=h - o,                                       # ◎が○をどれだけ引き離しているか（勝つ確率の差）
        tight=bool(t > 0 and h / t < 1.25),              # ◎○▲が拮抗しているか（◎の勝つ確率が▲の1.25倍未満）
        two=bool(h + o >= 0.45 and o >= 0.15 and h - o < 0.06),   # ◎○の2頭で勝つ確率の大半を占める
        ana=("🔥" in M), ana_pop=pop.get(M.get("🔥"), 0),
        top_unmarked=top_unmarked,
        # 印ごとの割安さ（モデル÷市場）と人気。K13（軸自由＋保険）が「穴の○▲を軸にするか」を決めるのに使う
        ratio={m: float(p[idx[M[m]]] / max(q[idx[M[m]]], 1e-9)) for m in M},
        mpop={m: pop.get(M[m], 99) for m in M},
    )


def seg_of(c):
    """検証・選択で使う区分名（堅い/普通/荒れ × ◎の人気）"""
    hp = "◎1人気" if c["hon_pop"] == 1 else "◎2〜3人気" if c["hon_pop"] <= 3 else "◎4人気以下"
    return c["kind"], hp


# ── パターン集 ──────────────────────────────────────────────────────────
# build(M, c) -> [(券種, [馬番...], 相対的な重み)]。賭け金は alloc で配分する
#   alloc_exp=1: どの組が当たっても戻りが揃う配分（ガミ対策）。0: 重みどおり
def _aite(M, keys=("○", "▲", "△1", "△2", "🔥", "紐1", "紐2")):      # 紐1・紐2 は印ではなく、compose が計算で足した3着候補
    return [M[k] for k in keys if k in M]


def _b_katagimi(M, c):          # 堅守: 単勝◎＋複勝◎＋ワイド◎-○・◎-▲＋馬連◎-○
    return [("単勝", [M["◎"]], 2), ("複勝", [M["◎"]], 3), ("ワイド", [M["◎"], M["○"]], 3), ("ワイド", [M["◎"], M["▲"]], 2), ("馬連", [M["◎"], M["○"]], 2)]


def _b_wide_nagashi(M, c):      # 標準（旧V1.1）: 単勝◎2＋馬連◎-○3＋ワイド◎-相手×1
    return [("単勝", [M["◎"]], 2), ("馬連", [M["◎"], M["○"]], 3)] + [("ワイド", [M["◎"], x], 1) for x in _aite(M)]


def _b_umaren_nagashi(M, c):    # 馬連◎流し: 単勝◎＋馬連◎-相手（頭が抜けていて相手が散るとき）
    return [("単勝", [M["◎"]], 2)] + [("馬連", [M["◎"], x], 1.5) for x in _aite(M)]


def _b_umatan(M, c):            # 馬単◎1着流し: ◎が勝ち切る型
    aite = _aite(M, ("○", "▲", "△1", "△2"))
    return [("単勝", [M["◎"]], 2)] + [("馬単", [M["◎"], x], 1.5) for x in aite] + [("ワイド", [M["◎"], M["○"]], 2)]


def _b_box3(M, c):              # ◎○▲が拮抗: ワイドBOX＋馬連◎-○
    a, b, d = M["◎"], M["○"], M["▲"]
    return [("ワイド", [a, b], 2), ("ワイド", [a, d], 2), ("ワイド", [b, d], 2), ("馬連", [a, b], 2), ("単勝", [a], 2)]


def _b_ana(M, c):               # 穴軸: 🔥を単勝・ワイド・馬連で厚めに、◎-○で押さえ
    f = M["🔥"]
    return [("単勝", [f], 1), ("ワイド", [f, M["◎"]], 2), ("ワイド", [f, M["○"]], 1.5), ("ワイド", [f, M["▲"]], 1.5),
            ("馬連", [f, M["◎"]], 1), ("馬連", [f, M["○"]], 1), ("ワイド", [M["◎"], M["○"]], 2)]


def _b_trio_nagashi(M, c):      # 3連複◎軸流し（相手5頭→10点）＋ワイド◎-○
    return [("ワイド", [M["◎"], M["○"]], 4), ("単勝", [M["◎"]], 2)] + [("3連複", [M["◎"], x, y], 0.8) for x, y in itertools.combinations(_aite(M), 2)]


def _b_ana_hon(M, c):           # ◎が人気薄: 単勝◎＋複勝◎＋ワイド◎流し（外れ方をやわらげる）
    return [("単勝", [M["◎"]], 2), ("複勝", [M["◎"]], 2)] + [("ワイド", [M["◎"], x], 1.2) for x in _aite(M)]


def _b_umatan_ura(M, c):        # ◎-○ 馬単の表裏＋ワイド＋単勝（◎○の2頭が抜けているとき）
    return [("馬単", [M["◎"], M["○"]], 3), ("馬単", [M["○"], M["◎"]], 1.5), ("ワイド", [M["◎"], M["○"]], 3),
            ("単勝", [M["◎"]], 2), ("ワイド", [M["◎"], M["▲"]], 1.5)]


def _b_formation(M, c):         # 3連複フォーメーション: ◎○▲ - ◎○▲ - 相手全員（点数を絞る）
    core = [M["◎"], M["○"], M["▲"]]
    rest = _aite(M, ("△1", "△2", "🔥"))
    pts = set()
    for a, b in itertools.combinations(core, 2):
        for x in rest:
            pts.add(tuple(sorted((a, b, x))))
    pts.add(tuple(sorted(core)))
    return [("ワイド", [M["◎"], M["○"]], 4), ("単勝", [M["◎"]], 2)] + [("3連複", list(k), 0.7) for k in sorted(pts)]


def _b_tan_fix(M, c):           # ◎1着固定: 3連単◎→(○▲△)→(○▲△△🔥)12点＋馬単◎→○▲△＋単勝◎＋ワイド◎○
    h = M["◎"]
    second = _aite(M, ("○", "▲", "△1"))
    third = _aite(M, ("○", "▲", "△1", "△2", "🔥", "紐1", "紐2"))
    pts = [("単勝", [h], 3), ("ワイド", [h, M["○"]], 3)] + [("馬単", [h, b], 2) for b in second]
    pts += [("3連単", [h, b, x], 1) for b in second for x in third if x != b]
    return pts


def _b_tan_multi(M, c):         # ◎○のマルチ: 3連単◎→○→相手・○→◎→相手（相手4頭×2＝8点）＋馬単の表裏＋ワイド◎○＋単勝◎
    a, b = M["◎"], M["○"]
    rest = _aite(M, ("▲", "△1", "△2", "🔥", "紐1", "紐2"))
    return [("単勝", [a], 1.5), ("ワイド", [a, b], 3), ("馬単", [a, b], 2), ("馬単", [b, a], 2)] +         [("3連単", [a, b, x], 1) for x in rest] + [("3連単", [b, a, x], 1) for x in rest]


def ana_axis_ctx(c):
    """上位印（○・▲）の中に「6番人気以下で割安（モデル÷市場≧1.15）」の馬がいれば、その印（割安さが最大）を返す。いなければ None"""
    best = None
    for m in ("○", "▲"):
        if c["mpop"].get(m, 0) >= 6 and c["ratio"].get(m, 0) >= 1.15:
            if best is None or c["ratio"][m] > c["ratio"][best]:
                best = m
    return best


def _b_axis_free(M, c):         # 軸自由＋保険（2026-11-01 ユーザー指示）: 軸は◎に限らない。穴の○▲が割安ならそこから◎へ流す。外れ用の保険も入れる
    h, o, t = M["◎"], M["○"], M["▲"]
    ax = ana_axis_ctx(c)
    ana = M.get("🔥") or M.get("△1")
    if ax:                                          # 穴軸: 穴の○▲を頭に、◎・もう一方へ流す
        a, other = M[ax], (t if ax == "○" else o)
        main = [("単勝", [a], 2), ("ワイド", [a, h], 3), ("馬連", [a, h], 2), ("ワイド", [a, other], 2)]
        ins = [("ワイド", [h, other], 2)]           # 保険: 穴軸が飛んでも◎と人気側の2頭で決まる形
    else:                                           # 通常: ◎軸
        main = [("単勝", [h], 2), ("ワイド", [h, o], 3), ("馬連", [h, o], 2), ("ワイド", [h, t], 2)]
        ins = [("ワイド", [o, t], 2)]               # 保険: ◎が飛んでも○▲で決まる形
    big = [("単勝", [ana], 1), ("ワイド", [ana, h], 1.5)] if ana and ana not in (h, o, t) else []     # 大穴の保険: 🔥の激走
    return main + ins + big


# prio が小さいほど先に当てはめる（より限定的な型を先に）。K2 は最後の受け皿
# live=False の型は試験中: 検証（axis_free_test.py）に通るまで本番の候補に入れない
PATTERNS = [
    dict(id="K13", prio=0.5, live=False, name="軸自由＋保険（穴の○▲を軸に・外れ用の保険つき）", alloc_exp=1.0, build=_b_axis_free,
         applies=lambda c: ana_axis_ctx(c) is not None,
         why="上位印に6番人気以下で割安な馬がいる。その馬から◎へ流し、◎・○▲の保険と🔥の保険も入れる"),
    dict(id="K4", prio=1, name="馬単◎1着流し（勝ち切る型）", alloc_exp=0.7, build=_b_umatan,
         applies=lambda c: c["hon_p"] >= 0.30 and c["hon_pop"] <= 2 and c["gap"] >= 0.12,
         why="◎の勝つ確率が3割を超え、○を大きく引き離している。頭で買う価値があるので馬単で配当を上乗せ"),
    dict(id="K12", prio=1.5, name="3連単マルチ（◎○の2頭が抜けた多頭数）", alloc_exp=0.0, build=_b_tan_multi,
         applies=lambda c: c["two"] and c["n"] >= 14 and c["kind"] != "堅い",
         why="多頭数で◎○の2頭に勝つ確率が集まる。◎○の1・2着を表裏で、3着に相手4頭を置く3連単で配当を上乗せ"),
    dict(id="K9", prio=2, name="馬単表裏（◎○の2頭が抜けた型）", alloc_exp=0.7, build=_b_umatan_ura,
         applies=lambda c: c["two"],
         why="◎○の2頭で勝つ確率の大半を占め、差も小さい。馬単の表裏とワイドで2頭の決着を厚く買う"),
    dict(id="K11", prio=2.5, name="3連単◎1着固定（勝ち切る型・幅広）", alloc_exp=0.0, build=_b_tan_fix,
         applies=lambda c: c["hon_p"] >= 0.22 and c["hon_pop"] <= 3 and c["gap"] >= 0.05 and c["kind"] != "荒れ" and c["n"] >= 10,
         why="◎が勝つ確率2割超で○との差もある。◎を1着に固定し、2着・3着を広く取る3連単（と馬単）で、◎が勝ったときの配当を厚くする"),
    dict(id="K1", prio=3, name="堅守型（単勝・複勝・ワイドで拾う）", alloc_exp=0.5, build=_b_katagimi,
         applies=lambda c: c["kind"] == "堅い" and c["hon_pop"] <= 2,
         why="堅いレースで◎が1〜2番人気。複勝とワイドを厚くして、印が当たったときに取りこぼさない"),
    dict(id="K3", prio=4, name="馬連◎流し（頭が抜けた型）", alloc_exp=1.0, build=_b_umaren_nagashi,
         applies=lambda c: c["gap"] >= 0.10 and c["hon_p"] >= 0.18,
         why="◎の勝つ確率が○を上回り軸が崩れにくい。馬連で相手を広く取り、当たったら配当を取る"),
    dict(id="K5", prio=5, name="ワイドBOX（◎○▲が拮抗）", alloc_exp=1.0, build=_b_box3,
         applies=lambda c: c["tight"] and c["kind"] != "荒れ",
         why="◎○▲の勝つ確率が近く、どの順でも決着しうる。3頭のワイド全組と馬連で取りこぼしを減らす"),
    dict(id="K10", prio=6, name="3連複フォーメーション（多頭数の荒れ）", alloc_exp=1.0, build=_b_formation,
         applies=lambda c: c["n"] >= 14 and c["kind"] == "荒れ",
         why="多頭数で人気が割れた荒れそうなレース。◎○▲を軸に相手を絞って、的中時の配当に厚みを持たせる"),
    dict(id="K6", prio=7, name="穴軸型（🔥から組む）", alloc_exp=0.8, build=_b_ana,
         applies=lambda c: c["ana"] and c["ana_pop"] >= 8 and c["kind"] != "堅い" and c["hon_p"] < 0.20,
         why="人気が割れ、8番人気以下に割安な馬（🔥）がいる。🔥を軸に単勝・ワイド・馬連を組む"),
    dict(id="K8", prio=8, name="人気薄◎（単勝・複勝・ワイド）", alloc_exp=1.0, build=_b_ana_hon,
         applies=lambda c: c["hon_pop"] >= 5,
         why="◎が5番人気以下。複勝を足して、当たる頻度と外れ方をやわらげる"),
    dict(id="K7", prio=9, name="3連複◎軸流し", alloc_exp=1.0, build=_b_trio_nagashi,
         applies=lambda c: c["n"] <= 14 and c["kind"] == "普通" and c["hon_pop"] <= 4,
         why="頭数が少なめで人気が割れる。◎を軸に相手5頭の3連複10点で、的中時の配当を上げる"),
    dict(id="K2", prio=99, name="ワイド◎流し（標準）", alloc_exp=1.0, build=_b_wide_nagashi,
         applies=lambda c: True,
         why="特徴の強く出ないレースの標準形。ワイドの相手を広く取って当たる頻度を上げる"),
]
BY_ID = {p["id"]: p for p in PATTERNS}


# ── 配分 ────────────────────────────────────────────────────────────────
def allocate(points, odds_fn, exp, budget=BUDGET):
    """points: [(券種, 馬番リスト, 重み)]。賭け金 ∝ 重み × (1/オッズ)^exp。100円単位・合計は budget 以内。
    exp=1 だと「どの組が当たっても戻りがほぼ揃う」配分（ガミ対策）。"""
    pts = []
    for t, combo, w in points:
        if None in combo:
            continue
        o = odds_fn(t, combo)
        if not o or o <= 1.0:
            continue
        pts.append((t, list(combo), w * (1.0 / o) ** exp, o))
    for _ in range(3):                                   # 100円に満たない点を落として配り直す
        if not pts:
            return []
        tot = sum(x[2] for x in pts)
        raw = [budget * x[2] / tot for x in pts]
        keep = [i for i, r in enumerate(raw) if r >= 100]
        if len(keep) == len(pts):
            break
        pts = [pts[i] for i in keep]
    tot = sum(x[2] for x in pts)
    raw = [budget * x[2] / tot for x in pts]
    st = [int(r // 100) * 100 for r in raw]
    left = budget - sum(st)
    for i in sorted(range(len(pts)), key=lambda i: -(raw[i] - st[i])):   # 端数は切り捨て分の大きい点から100円ずつ
        if left < 100:
            break
        st[i] += 100
        left -= 100
    return [(pts[i][0], pts[i][1], st[i]) for i in range(len(pts)) if st[i] >= 100]


def gami_stats(plan, odds_fn):
    """各点が単独で当たったときの戻り÷投資総額。1.0未満が『当たってもガミる点』"""
    tot = sum(s for _, _, s in plan)
    rets = [s * odds_fn(t, c) / tot for t, c, s in plan if odds_fn(t, c)]
    return dict(min_ret=round(min(rets), 2) if rets else 0.0, gami_pts=sum(1 for r in rets if r < 1.0), n=len(rets))


# ── 選び方 ──────────────────────────────────────────────────────────────
def candidates(c, seg_stats=None):
    """当てはまるパターンを優先順位（prio）で返す。データ（pattern_segment_results.json の select）があれば、
    その区分で標準形K2より回収率が5ポイント以上悪かった型（avoid）は外す。K2は必ず最後に残る"""
    ok = sorted((p for p in PATTERNS if p.get("live", True) and p["applies"](c)), key=lambda p: p["prio"])
    if seg_stats:
        st = seg_stats.get("|".join(seg_of(c)), {})
        ok = [p for p in ok if p["id"] == "K2" or not st.get(p["id"], {}).get("avoid")]
    return ok


def budget_for(e):
    """旨味（買い目全体の期待回収率 e＝Σ賭け金×的中確率×オッズ ÷ Σ賭け金）から、そのレースの予算の目安を返す。
    基本は1万円前後。旨味が薄ければ点数を絞って少額、期待値が取れていても上限は BUDGET_MAX（2026-10-31 ユーザー指示）
      e≧1.10 → 15,000円 ／ 1.00〜1.10 → 12,000円 ／ 0.70〜1.00 → 1万円前後（紐を足した分は少し超えてよい）
      0.55〜0.70 → 6,000円（期待値0.5未満の点は買わない） ／ 0.55未満 → 3,000円（期待値の高い数点だけ）"""
    if e >= 1.10:
        return 15000
    if e >= 1.00:
        return 12000
    if e >= 0.70:
        return None                      # None＝基本（紐を足した分を含めて 10,000〜 の範囲）
    return 6000 if e >= 0.55 else 3000


def _plan_ev(plan, odds_fn, p_fn):
    """買い目全体の期待回収率（的中確率×オッズを賭け金で重みづけ）。確率・オッズが無い点は除く"""
    s = ev = 0.0
    for t, cb, st in plan:
        o, p = odds_fn(t, cb), p_fn(t, cb)
        if o and p is not None:
            s += st
            ev += st * p * o
    return ev / s if s else 0.0


def _pt_ev(pt, odds_fn, p_fn):
    t, cb, _ = pt
    o, p = odds_fn(t, cb), p_fn(t, cb)
    return p * o if o and p is not None else None


def compose(M, c, odds_fn, day_counts=None, seg_stats=None, budget=BUDGET, force=None, p_fn=None, extra=None, ev_odds_fn=None):
    """レースの特徴 c に合うパターンを選び、買い目（plan）を返す。
    day_counts: {パターンID: 今日そのパターンを使った回数}。同じ日に同じ形が続くときは、次点の中で差が小さければそちらを使う
    p_fn(券種, 馬番リスト) -> モデルの的中確率、extra: 紐の追加候補の馬番（勝つ確率が高い順の印なし馬）。
    p_fn を渡したときだけ（2026-10-31〜）: ①紐を足すかをレースごとに計算で決める（足した点の平均期待値が下限以上かつ既存の90%以上）
    ②1点の金額は据え置いて点を足す＝予算は1万円前後から少し増える ③買い目全体の期待回収率で予算を増減する（budget_for・上限15,000円）。
    ev_odds_fn: 旨味（期待値）の判定に使うオッズ。実際に取れているオッズがあればそれを渡す（無ければ odds_fn の推定オッズ）
    p_fn が無ければ従来どおり budget 円で固定（pattern_backtest.py などの検証用）"""
    need = ("◎", "○", "▲")
    if not all(k in M for k in need):
        return dict(plan=[], pattern=dict(id="-", name="見送り（印が足りない）", why=""), gami={})
    cands = candidates(c, seg_stats)
    if force:
        cands = [BY_ID[force]] + [x for x in cands if x["id"] != force]
    pick = cands[0]
    if day_counts and not force and len(cands) > 1 and day_counts.get(pick["id"], 0) >= 3:
        alt = next((x for x in cands[1:] if day_counts.get(x["id"], 0) < day_counts.get(pick["id"], 0)), None)
        if alt:
            pick = alt
    pts = pick["build"](M, c)
    meta = {}
    oe = ev_odds_fn or odds_fn
    if p_fn is not None and pts:
        w_old = sum(w for _, _, w in pts)
        added = []
        for x in (extra or [])[:3]:
            if len(added) >= WIDEN_MAX or x in M.values():
                continue
            M2 = dict(M, **{"紐%d" % (len(added) + 1): x})
            pts2 = pick["build"](M2, c)
            new = [pt for pt in pts2 if pt not in pts]
            evn = [v for v in (_pt_ev(pt, oe, p_fn) for pt in new) if v is not None]
            evo = [v for v in (_pt_ev(pt, oe, p_fn) for pt in pts) if v is not None]
            if not evn or not evo:
                continue
            if sum(evn) / len(evn) >= max(WIDEN_MIN_EV, WIDEN_REL * sum(evo) / len(evo)):
                M, pts = M2, pts2
                added.append(x)
        w_new = sum(w for _, _, w in pts)
        b1 = int(min(BUDGET_MAX, budget * w_new / w_old) // 100 * 100)          # 1点の金額を据え置いて点を足した分の予算
        plan = allocate(pts, odds_fn, pick["alloc_exp"], b1)
        e = _plan_ev(plan, oe, p_fn)
        tier = budget_for(e)
        note = ""
        if tier is not None and tier < budget:                                   # 旨味が薄い: 期待値の高い点だけに絞って少額
            evs = [(_pt_ev(pt, oe, p_fn) or 0.0, pt) for pt in pts]
            keep = [pt for v, pt in sorted(evs, key=lambda z: -z[0]) if v >= PRUNE_EV]
            keep = keep if len(keep) >= 4 else [pt for _, pt in sorted(evs, key=lambda z: -z[0])[:4]]
            keep = keep[:4] if tier <= 3000 else keep
            for h in set(M.values()):          # 印の付いた馬（紐で足した馬も）は必ず1点以上の買い目に残す＝印と買い目を一致させる（2026-10-31 ユーザー指摘）
                if not any(h in cb for _, cb, _ in keep):
                    best = max((pt for pt in pts if h in pt[1]), key=lambda pt: _pt_ev(pt, oe, p_fn) or 0.0, default=None)
                    if best:
                        keep.append(best)
            plan = allocate(keep, odds_fn, pick["alloc_exp"], tier)
            note = "旨味が薄いため点数を絞って少額（期待回収率%.0f%%）" % (e * 100)
            e = _plan_ev(plan, oe, p_fn)
        elif tier is not None:                                                   # 期待値が取れている: 上限までは増やす
            plan = allocate(pts, odds_fn, pick["alloc_exp"], min(tier, BUDGET_MAX))
            note = "期待値が取れているため予算を増やす（期待回収率%.0f%%・上限%s円）" % (e * 100, f"{BUDGET_MAX:,}")
            e = _plan_ev(plan, oe, p_fn)
        meta = dict(e=round(e, 3), total=sum(s for _, _, s in plan), widened=added, note=note)
    else:
        plan = allocate(pts, odds_fn, pick["alloc_exp"], budget)
    if not plan:
        pick = BY_ID["K2"]
        plan = allocate(pick["build"](M, c), odds_fn, pick["alloc_exp"], budget)
    return dict(plan=plan, pattern=dict(id=pick["id"], name=pick["name"], why=pick["why"]),
                gami=gami_stats(plan, odds_fn), others=[x["id"] for x in cands if x["id"] != pick["id"]], meta=meta)
