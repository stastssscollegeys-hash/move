# -*- coding: utf-8 -*-
"""
kaime_design_v7.py — 買い目設計 v7（シナリオベース・パターン固定をやめた版）
==============================================================================
なぜ作り直したか
----------------
v5〜v6は「53種のパターンライブラリから最良を選ぶ」設計だった。
その結果、予想（印）が当たっているのに買い目が固定的で、
**当たってもガミる**（的中したのに投資額を下回る）ことが繰り返された。

2026/9/6 の実績: 7レース中6レース的中（85.7%）なのに回収率66%。
的中6レースのうち5レースは「当たっても100%に届かない点」で当たっていた。

新しい考え方
------------
パターンを選ぶのをやめ、**その馬券が当たったときいくら返るか**を起点に組む。

    その点の的中時回収率 ＝ 配分比率 × 配当倍率

これが 1.0 未満の点は「当たっても損する点」＝**ガミ点**。原則として買わない。

さらに、レースは1点だけ当たるとは限らないので、
**決着シナリオを列挙 → シナリオごとの合計回収率を評価 → 配分を最適化**する。

実測の土台（確定払戻1,044レース）
---------------------------------
◆ 3着以内の人気構成
    上位3人気だけで決まる      8.4%   ← 本命サイド一点張りは分が悪い
    8番人気以下が1頭でも絡む  37.2%   ← 穴を1頭は入れる根拠
    最頻は「1-3人気2頭＋4-7人気1頭」34.7%

◆ ワイドの配当中央値（人気の組み合わせ別）
    1-2人気 2.2倍 / 1-3人気 3.2倍 / 1-4人気 3.8倍 / 1-5人気 4.9倍
    1-6人気 7.1倍 / 1-8人気 11.2倍 / 2-8人気 15.4倍
    → **◎1番人気×○2番人気のワイドは2.2倍。5点均等ならガミ確定**

◆ 3連複の配当中央値
    1-2-3人気 8.0倍 / 1-2-5人気 13.9倍 / 1-3-5人気 19.6倍 / 1-3-8人気 51.4倍

◆ ガミにならない最低配当（均等配分の場合）
    5点なら500円以上 / 4点なら400円以上 / 3点なら300円以上

使い方
------
    from kaime_design_v7 import design
    res = design(budget=10000, marks={...}, odds={...}, probs={...})
"""
from __future__ import annotations
import sys, io, json
from pathlib import Path
from itertools import combinations, permutations

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from payout_estimator import estimate
from ev_reference import BASELINE, LONGSHOT_CUT, BAD_POP, GOOD_POP, flb_roi
import ev_reference as ev_ref

# ── 実測テーブル（1,044レース）──────────────────────────
# 3着以内の人気構成の出現率。シナリオ確率の事前分布に使う。
TOP3_BAND = {
    (2, 1, 0): 0.347,   # 1-3人気2頭 + 4-7人気1頭  ← 最頻
    (1, 2, 0): 0.177,
    (1, 1, 1): 0.171,
    (2, 0, 1): 0.122,
    (3, 0, 0): 0.084,   # 上位3人気で決着 ← 意外に少ない
    (1, 0, 2): 0.028,
    (0, 2, 1): 0.025,
    (0, 1, 2): 0.024,
    (0, 3, 0): 0.020,
}
P_ANY_LONGSHOT = 0.372   # 8番人気以下が1頭でも3着以内に入る確率

# ── 券種別の期待値しきい値（dulbea期待値論 × 自前実測14,982頭で確認）──
# 期待値 = オッズ × 的中率。券種ごとに的中率が違うので物差しも違う。
# 3連複が2.0〜3.0を要求されるのは的中率1〜10%だから。ワイドは30〜70%当たるので1.1〜1.5でよい。
EV_MIN = {"単勝": 1.20, "複勝": 1.10, "ワイド": 1.10, "馬連": 1.40,
          "馬単": 1.60, "3連複": 2.00, "3連単": 2.00}

# ── 人気帯別の実測期待値（14,982頭）──────────────────────
# 1番人気0.88が最良クラス／7番人気0.68が最悪（過剰人気の罠）／4番人気0.85は良い帯
POP_EV = {1: 0.88, 2: 0.80, 3: 0.80, 4: 0.85, 5: 0.76, 6: 0.77, 7: 0.68, 8: 0.85}
POP_EV_LONG = 1.10          # 9番人気以下（的中率1.1%なので3連複の3頭目向き）

GAMI = 1.0        # 的中時回収率がこれ未満なら「ガミ点」
MIN_UNIT = 100    # 100円単位


# ══════════════════════════════════════════════════════
# 1. 勝率の推定（多ソースのブレンド）
# ══════════════════════════════════════════════════════
def blend_prob(num: int, odds: float | None, model_rank: int | None,
               n_field: int, signals: dict | None = None) -> float:
    """
    1頭の「3着以内に入る力」の相対値を返す（正規化前）。

    実測で分かっていること:
      ・市場（オッズ）のほうがモデルより精度が高い（単勝回収 市場84% vs モデル優位48〜62%）
      ・よって市場を主、モデルを従とし、外部シグナルで微調整する
    signals: {"influencer": 補正点, "bias_ok": True/False, "oikiri": "S"/"A"/..., "weight_ng": True}
    """
    if not odds or odds <= 0:
        return 0.0
    p_market = 0.8 / odds                     # 控除率20%を戻した市場推定勝率
    p = p_market
    # モデル順位による微調整（±15%まで。市場を覆さない）
    if model_rank:
        adj = 1.0 + max(-0.15, min(0.15, (n_field / 2 - model_rank) * 0.02))
        p *= adj
    s = signals or {}
    if s.get("influencer"):
        p *= 1.0 + max(-0.10, min(0.10, s["influencer"] * 0.02))
    if s.get("bias_ok") is True:
        p *= 1.08                              # 当日バイアスに順行
    elif s.get("bias_ok") is False:
        p *= 0.92
    if s.get("oikiri") in ("S", "A"):
        p *= 1.05
    if s.get("weight_ng"):
        p *= 0.85                              # 馬体重±15kg以上
    # 実測の人気帯バイアス（14,982頭）: 7番人気帯は単勝EV0.68で最悪、1/4/8は0.85以上
    pop = s.get("pop")
    if pop in BAD_POP:
        p *= 0.90
    elif pop in GOOD_POP:
        p *= 1.05
    # 単勝100倍以上は実測回収29.2%。確率をほぼゼロに落とす
    if odds >= LONGSHOT_CUT:
        p *= 0.30
    return p


def top3_probs(cands: list[dict], n_field: int) -> dict[int, float]:
    """各馬の3着内確率（合計が3になるよう正規化）"""
    raw = {c["num"]: blend_prob(c["num"], c.get("odds"), c.get("rank"), n_field, c.get("signals"))
           for c in cands}
    s = sum(raw.values())
    if s <= 0:
        return {}
    # 単勝相当を3着内に引き伸ばす（経験的に単勝確率の約2.6倍が複勝圏）
    return {k: min(0.95, v / s * 3.0) for k, v in raw.items()}


# ══════════════════════════════════════════════════════
# 2. 決着シナリオの列挙
# ══════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════
# Harville式の λ 補正（2026-09-06・自前1,111レースで推定）
# ══════════════════════════════════════════════════════
# 素朴なHarvilleは「1着確率をそのまま2着・3着に使い回す」ため、
# 上位人気馬の連対率・複勝率を系統的に過大評価する。
#   例) 1番人気の3着率  素朴H 16.7% → 実測 12.8%
#       8番人気の3着率  素朴H  4.2% → 実測  7.4%
#
# λを掃引して実測に最も合う値を選んだ結果（加重平均絶対誤差）:
#       2着  素朴H 1.478pt → λ=0.80 で 0.782pt（-47%）
#       3着  素朴H 1.651pt → λ=0.70 で 0.662pt（-60%）
# 伊藤(2010)のJRA推定値 (0.76, 0.62) より僅かに1.0寄りだが、
# 文献値でも 0.788 / 0.766pt と十分良く、方向は完全に一致している。
#
#   → ◎からの3連単流しで単勝支持率をそのまま掛け算するのは禁止。
LAMBDA = (1.00, 0.80, 0.70)   # (1着, 2着, 3着)


def scenarios(cands: list[dict], p3: dict[int, float], topn: int = 8) -> list[tuple[tuple, float]]:
    """
    起こりうる決着を **着順つき** で列挙する (1着, 2着, 3着)。
    馬連・馬単・3連単は着順が要るので、順不同の集合では評価できない。
    候補を絞りすぎると穴を取りこぼすので市場上位8頭まで見る。
    """
    pool = sorted(cands, key=lambda c: c.get("odds") or 999)[:topn]
    nums = [x["num"] for x in pool]
    out = []
    for perm in permutations(nums, 3):
        # 1着→2着→3着 と順に引く（Harville型の逐次抽出＋λ補正）
        rest = {n: max(p3.get(n, 0.01), 1e-4) for n in nums}
        pr = 1.0
        for i, n in enumerate(perm):
            lam = LAMBDA[i]
            w = {k: v ** lam for k, v in rest.items()}   # 着順が下がるほど差を縮める
            tot = sum(w.values())
            if tot <= 0:
                pr = 0.0
                break
            pr *= w[n] / tot
            del rest[n]
        out.append((perm, pr))
    tot = sum(p for _, p in out) or 1.0
    covered = 0.80   # 候補外での決着ぶんは確率として残す
    return [(c, p / tot * covered) for c, p in out]


# ══════════════════════════════════════════════════════
# 3. 買い目候補の生成と評価
# ══════════════════════════════════════════════════════
def _tag_band(bet: dict, ticket: str, pops: list) -> None:
    """
    その買い目の人気の組み合わせに、実測の帯データを貼る。

    2026-09-08に自前1,086レースで全300帯を測った結果、**同じ券種でも人気の
    組み合わせだけで回収率が桁違いに違う**ことが分かった。
        馬連 4-6人気 120%（除外後111%） ↔ 馬連1-2人気 78%
        ワイドは45帯すべてで100%未満＝**構造的に届かない**
    推定配当も的中確率も市場オッズ由来なので、両者から作った期待値には
    この差が入らない。だから外から係数を掛ける。
    """
    if not all(pops):
        return
    b = ev_ref.ticket_band(ticket, pops)
    bet["band"] = b
    bet["quality"] = ev_ref.band_quality(ticket, pops)
    if b and b.get("roi_ex_top", 0) < 0.80:
        bet["weak_band"] = True          # 本線に置かない
    key = (ticket, tuple(pops) if ticket == "馬単" else tuple(sorted(pops)))
    if key in ev_ref.ROBUST_BANDS:
        # 3関門（的中15件以上・最高配当除外・期間3分割）を通った帯。
        # ただし300帯を検定して2帯なので確定エッジではない（band_trackerで追跡中）
        bet["robust_band"] = True


def candidate_bets(marks: dict, odds: dict) -> list[dict]:
    """印から買い目候補を作り、推定配当を付ける。券種は絞らない。"""
    hon, tai, tan = marks.get("◎"), marks.get("○"), marks.get("▲")
    ds = list(marks.get("△") or [])
    ana = marks.get("🔥")
    named = [x for x in [hon, tai, tan, *ds, ana] if x]
    # 人気順位（実測テーブルを引くのに使う）
    rank = {n: i + 1 for i, n in enumerate(
        sorted([n for n in odds if odds.get(n)], key=lambda n: odds[n]))}

    out = []
    for a, b in combinations(named, 2):
        for t in ("ワイド", "馬連"):
            e = estimate(t, [odds.get(a), odds.get(b)])
            if not e:
                continue
            bet = {"t": t, "combo": sorted([a, b]), "est": e}
            _tag_band(bet, t, [rank.get(a), rank.get(b)])
            out.append(bet)
    for c in combinations(named, 3):
        e = estimate("3連複", [odds.get(x) for x in c])
        if e:
            bet = {"t": "3連複", "combo": sorted(c), "est": e}
            _tag_band(bet, "3連複", [rank.get(x) for x in c])
            out.append(bet)
    if hon and tai:
        e = estimate("馬単", [odds.get(hon), odds.get(tai)])
        if e:
            bet = {"t": "馬単", "combo": [hon, tai], "est": e, "ordered": True}
            _tag_band(bet, "馬単", [rank.get(hon), rank.get(tai)])
            out.append(bet)
    return out


def hits(bet: dict, sc: tuple) -> bool:
    """着順つきシナリオ sc=(1着,2着,3着) でこの点が当たるか"""
    c = bet["combo"]
    t = bet["t"]
    if t == "ワイド":
        return set(c) <= set(sc)                       # 3着以内に2頭
    if t == "馬連":
        return set(c) == set(sc[:2])                   # 1-2着（順不同）
    if t == "馬単":
        return tuple(c) == tuple(sc[:2])               # 1-2着（着順どおり）
    if t == "3連複":
        return set(c) == set(sc)                       # 1-3着（順不同）
    if t == "3連単":
        return tuple(c) == tuple(sc)
    return False


def evaluate(bets: list[dict], budget: int, scen: list[tuple[frozenset, float]]) -> dict:
    """シナリオ全列挙で E[回収率]・ガミ率・的中率・全外し率を出す"""
    e_ret = hit_p = gami_p = 0.0
    for sc, p in scen:
        ret = sum(b["amt"] * b["est"] for b in bets if hits(b, sc))
        if ret > 0:
            hit_p += p
            if ret < budget:
                gami_p += p
        e_ret += p * ret
    return {"E": e_ret / budget, "hit": hit_p, "gami": gami_p,
            "gami_ratio": gami_p / hit_p if hit_p else 0.0}


def design(budget: int, marks: dict, odds: dict, n_field: int,
           cands: list[dict] | None = None, min_points: int = 4,
           max_points: int = 10, cap: float = 0.35) -> dict:
    """
    買い目を設計する。パターンから選ばず、次の順で組み立てる。

      1) 候補点をすべて作り、推定配当を付ける
      2) **ガミ点を除外する**（配分比率 × 配当 < 1.0 になる点）
      3) シナリオ確率で期待値の高い順に採用
      4) 制約（100円単位・合計=予算・◎抜き1点・△全部を組込み・1点上限）を満たすよう配分
    """
    if cands is None:
        cands = [{"num": n, "odds": o, "rank": None} for n, o in odds.items()]
    p3 = top3_probs(cands, n_field)
    scen = scenarios(cands, p3, topn=min(8, len(cands)))
    pool = candidate_bets(marks, odds)
    if not pool:
        return {"bets": [], "total": 0, "note": "候補なし"}

    # 各点の「期待配当 × 的中確率」でスコア ＝ 期待値そのもの
    for b in pool:
        b["p"] = sum(p for sc, p in scen if hits(b, sc))
        b["ev"] = b["p"] * b["est"]          # = 的中率 × オッズ = 期待値
        # 全券種に実測の人気帯係数を掛ける（2026-09-08に馬連・3連複・馬単へ拡張）。
        # 推定配当と的中確率はどちらも市場オッズ由来なので、両者から作った期待値には
        # 「同じ配当でも人気の組み合わせによって実収支が違う」という情報が入らない。
        # 1,086レースの実測ではこの差が桁で効く（馬連4-6人気111% ↔ 1-2人気78%）。
        # 補正しないと、◎○が上位人気のとき自動的に不利な帯へ寄る。
        if "quality" in b:
            b["ev"] *= b["quality"]

    # ── 軸1: 期待値による選別 ────────────────────────
    # ⚠重要な限界: 的中率を市場オッズから作ると、控除率20%のぶん
    #   期待値は定義上どの点も0.8前後になる。**絶対しきい値（3連複2.0等）で
    #   絞ると全滅する。** dulbeaのしきい値は「市場と違う自前の的中率推定」が
    #   ある前提の数字であり、当方にはまだそのエッジが実証できていない
    #   （実測: エンジン69.4% vs 市場80%）。
    # したがって絶対値ではなく **レース内の相対順位** で使い、
    #   絶対期待値は「参考値」として必ず表示する（自己欺瞞を防ぐため）。
    base = sum(b["ev"] for b in pool) / len(pool) if pool else 0
    for b in pool:
        b["ev_rel"] = b["ev"] / base if base > 0 else 0        # レース内相対
        b["ev_gate"] = EV_MIN.get(b["t"], 1.0)                  # 参考: 記事のしきい値
        b["ev_ok"] = b["ev"] >= b["ev_gate"]
    ev_cut = sum(1 for b in pool if not b["ev_ok"])
    # 相対で下位30%は落とす（同一券種内で比較。券種をまたぐと物差しが違うため）
    keep_rel = []
    by_t = {}
    for b in pool:
        by_t.setdefault(b["t"], []).append(b)
    for t, lst in by_t.items():
        lst.sort(key=lambda x: -x["ev"])
        keep_rel += lst[:max(2, int(len(lst) * 0.7))]
    pool = keep_rel

    # ── ガミ点の除外 ────────────────────────────
    # 実測: 5点均等なら配当5倍、4点なら4倍、3点なら3倍が最低ライン。
    # 「その点に上限いっぱい張っても100%に届かない」点は最初から候補から外す。
    floor_odds = 1.0 / cap                        # cap=0.35 なら 2.9倍
    keep = [b for b in pool if b["est"] >= floor_odds]
    if len(keep) < min_points:
        keep = sorted(pool, key=lambda b: -b["est"])[:min_points]

    # 券種の偏りを防ぐ: 同一券種は最大で全体の6割まで
    keep.sort(key=lambda b: -b["ev"])
    chosen, per_t = [], {}
    lim = max(2, int(max_points * 0.6))
    for b in keep:
        if len(chosen) >= max_points:
            break
        if per_t.get(b["t"], 0) >= lim:
            continue
        chosen.append(b)
        per_t[b["t"]] = per_t.get(b["t"], 0) + 1

    # ── 制約の充足 ──────────────────────────────
    hon = marks.get("◎")
    if hon and all(hon in b["combo"] for b in chosen):
        alt = next((b for b in keep if hon not in b["combo"]), None)
        if alt:
            chosen[-1] = alt
    for d in (marks.get("△") or []):
        if not any(d in b["combo"] for b in chosen):
            alt = next((b for b in keep if d in b["combo"] and b not in chosen), None)
            if alt:
                chosen[-1] = alt

    # ── 配分の原理（v7の中核）────────────────────────
    # ある点がガミにならない最低額は  budget / 推定配当 。
    # 買う点すべてでこれを満たすには
    #       Σ ( 1 / 推定配当 ) ≦ 1.0
    # が必要。これはブックメーカーで言う「オーバーラウンドが100%以下」と同じ条件で、
    # **満たせない点数を買った時点で、どう配分してもどこかがガミになる**。
    # したがって、この不等式が成立するところまで期待値の低い点から落とす。
    chosen.sort(key=lambda b: -b["ev"])
    while len(chosen) > min_points and sum(1.0 / b["est"] for b in chosen) > 1.0:
        chosen.pop()          # 期待値が最も低い点を落とす

    overround = sum(1.0 / b["est"] for b in chosen)
    cap_amt = int(budget * cap / MIN_UNIT) * MIN_UNIT

    if overround <= 1.0:
        # 全点をガミ回避できる。まず最低額を確保し、余りを期待値比で上乗せする
        for b in chosen:
            b["amt"] = int((budget / b["est"]) / MIN_UNIT + 0.999) * MIN_UNIT
        rest = budget - sum(b["amt"] for b in chosen)
        if rest > 0:
            tot_ev = sum(b["ev"] for b in chosen) or 1.0
            for b in chosen:
                b["amt"] = min(cap_amt, b["amt"] + int(rest * b["ev"] / tot_ev / MIN_UNIT) * MIN_UNIT)
    else:
        # 落としきれない場合（点数下限に達した）は期待値比で配る
        tot_ev = sum(b["ev"] for b in chosen) or 1.0
        for b in chosen:
            b["amt"] = min(cap_amt, max(MIN_UNIT,
                          int(budget * b["ev"] / tot_ev / MIN_UNIT) * MIN_UNIT))

    # 合計を予算にぴったり合わせる（ガミを増やさない向きに調整）
    guard = 0
    while sum(b["amt"] for b in chosen) != budget and guard < 800:
        guard += 1
        s_now = sum(b["amt"] for b in chosen)
        if s_now < budget:
            r = [b for b in chosen if b["amt"] + MIN_UNIT <= cap_amt]
            if not r: break
            # ガミの点を優先的に底上げし、無ければ期待値最良に足す
            g = [b for b in r if b["amt"] * b["est"] < budget]
            (max(g, key=lambda b: b["ev"]) if g else max(r, key=lambda b: b["ev"]))["amt"] += MIN_UNIT
        else:
            r = [b for b in chosen if b["amt"] - MIN_UNIT >= MIN_UNIT]
            if not r: break
            # 削ってもガミにならない点から削る
            ok = [b for b in r if (b["amt"] - MIN_UNIT) * b["est"] >= budget]
            (min(ok, key=lambda b: b["ev"]) if ok else min(r, key=lambda b: b["ev"]))["amt"] -= MIN_UNIT

    ev = evaluate(chosen, budget, scen)
    for b in chosen:
        b["ret_if_hit"] = b["amt"] * b["est"] / budget      # この点が当たった時の回収率
        b["gami"] = b["ret_if_hit"] < GAMI
    return {"bets": sorted(chosen, key=lambda b: -b["amt"]),
            "total": sum(b["amt"] for b in chosen),
            "overround": sum(1.0 / b["est"] for b in chosen),
            "ev_cut": ev_cut, **ev}


def render(res: dict, budget: int) -> str:
    ng = sum(1 for b in res["bets"] if b["gami"])
    L = [f"💰 買い目 合計{len(res['bets'])}点・{res['total']:,}円",
         f"　E[回収率] {res['E']*100:.0f}% ／ 的中率 {res['hit']*100:.0f}% ／ "
         f"ガミ率 {res['gami_ratio']*100:.0f}%（的中したのに損する確率）",
         f"　Σ(1/配当) = {res.get('overround',0):.2f}"
         f"{'（1.00以下＝全点ガミなしで組める）' if res.get('overround',9)<=1 else '（1.00超＝どう配分してもガミが出る）'}"
         f" ／ ガミ点 {ng}点", ""]
    ok = sum(1 for b in res["bets"] if b.get("ev_ok"))
    L.append(f"　期待値: 記事のしきい値を満たす点 {ok}/{len(res['bets'])}"
             f"（満たさなくても相対順位で採用している。控除率20%のぶん市場確率ベースでは"
             f"どの点も0.8前後になるため）")
    L.append("")
    # 券種別の基準線と比べてどうか（選ぶ力があるかの目安）
    bl = {}
    for b in res["bets"]:
        bl.setdefault(b["t"], []).append(b)
    L.append("　基準線比較（フラット買いの実測回収率）:")
    for t, lst in bl.items():
        base = BASELINE.get(t)
        if base:
            L.append(f"　　{t}: 基準線{base*100:.1f}% ／ この構成のE[回収率]が"
                     f"これを超えていなければ選ぶ意味がない")
    L.append("")
    by = {}
    for b in res["bets"]:
        by.setdefault(b["t"], []).append(b)
    for t, lst in by.items():
        L.append(f"【{t}】{len(lst)}点 {sum(x['amt'] for x in lst):,}円")
        for b in lst:
            flag = "  ⚠ガミ点" if b["gami"] else ""
            L.append(f"　{'-'.join(map(str,b['combo']))} {b['amt']:,}円"
                     f"（推定{b['est']:.1f}倍・期待値{b['ev']:.2f} → 当たれば{b['ret_if_hit']*100:.0f}%）{flag}")
    return "\n".join(L)


if __name__ == "__main__":
    # デモ: 9/6 セントウルS（実際は 1着◎3 - 2着○9 - 3着△1 / 3連複15.6倍）
    marks = {"◎": 3, "○": 9, "▲": 5, "△": [8, 11, 1]}
    odds = {3: 3.2, 9: 5.1, 5: 6.9, 8: 4.2, 11: 18.9, 1: 9.9}
    cands = [{"num": n, "odds": o, "rank": i + 1} for i, (n, o) in
             enumerate(sorted(odds.items(), key=lambda x: x[1]))]
    res = design(5000, marks, odds, n_field=16, cands=cands)
    print("═══ v7 デモ: 2026/9/6 セントウルS（予算5,000円）═══\n")
    print(render(res, 5000))
    got = sum(b["amt"] * 15.60 for b in res["bets"]
              if b["t"] == "3連複" and sorted(b["combo"]) == [1, 3, 9])
    got += sum(b["amt"] * 3.30 for b in res["bets"]
               if b["t"] == "ワイド" and sorted(b["combo"]) == [3, 9])
    got += sum(b["amt"] * 4.30 for b in res["bets"]
               if b["t"] == "ワイド" and sorted(b["combo"]) == [1, 3])
    got += sum(b["amt"] * 6.90 for b in res["bets"]
               if b["t"] == "ワイド" and sorted(b["combo"]) == [1, 9])
    got += sum(b["amt"] * 6.40 for b in res["bets"]
               if b["t"] == "馬連" and sorted(b["combo"]) == [3, 9])
    print(f"\n実際の決着 1着③-2着⑨-3着① → 払戻 {int(got):,}円（回収率 {got/5000*100:.0f}%）")
