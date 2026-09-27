# -*- coding: utf-8 -*-
"""
2026-08-30 重賞2本 手動レイヤー期待値評価（v2: 全券種ファミリー横断）
=====================================================================
v1の反省: 3連複とワイドに偏った12パターンしか評価せず、2レースとも同じ
「3連複＋ワイド2点」の型になった。SKILL.mdの核心は「46〜53パターンを
全券種ファミリー横断で機械評価し、レースに合った構成を選ぶ」こと。

v2では単勝・馬連・馬単・ワイド・3連複・3連単・ハイブリッドの
全ファミリー約60パターンを評価する。

評価指標（v5と同一定義）:
  E[回収率] / P(300%+) / P(1000%+) / 的中率 / ガミ率
採用基準: E[回収率]115%以上 × ガミ率35%以下

ガード（SKILL.md v5.2〜v5.8）:
  - 単勝系T1〜T3は◎の実オッズ3.0〜10.0倍のみ許可
  - 単勝・3連単の「◎単独軸」は○▲の複勝ヘッジ併設が必須
  - 人気2頭軸（◎=1人気×○=2人気）の構成は禁止
  - ○を含む点が7割超の構成は禁止（v5.8）
  - △は全頭を3連複の相手に最低1回入れる（v5.8）
"""
from __future__ import annotations
import itertools
from collections import defaultdict

TRIO_TAKE = 0.75; WIDE_TAKE = 0.775; QN_TAKE = 0.775
EX_TAKE = 0.75;   T1_TAKE = 0.80;    TR_TAKE = 0.725

MARU = "⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"
def m(n): return MARU[n]

# ══════════════════════════════════════════════════════════
RACES = {}

RACES["新潟記念"] = dict(
    label="新潟記念(G3) 新潟芝2000m外 11頭 15:45 / ハンデ戦",
    # 当日8:57の実オッズ／馬場は前日想定の道悪ではなく「良」に回復したため評価を組み替え
    horses={
        8:  ("ダノンシーマ",      3.6, 20.0),  # 1番人気に浮上/エンジン総合1位/川田/調教「中心はこの馬でいい」 ▲父の新潟外回り0-0-0-8
        5:  ("ゾロアストロ",      3.8, 20.0),  # 調教A判定で全馬首位・同厩ステレンボッシュに半馬身先着/55kg最軽量/道悪未経験リスクは良馬場で消滅
        3:  ("ロデオドライブ",    4.2, 18.0),  # ML最高43.2%/4戦全連対/良馬場の上がり勝負は歓迎
        4:  ("ドゥレッツァ",      7.9, 13.0),  # 追い切り唯一のS/前日9.6→7.9と最も売れた ▲59kg・11ヶ月ぶり
        11: ("ステレンボッシュ", 11.8,  8.0),  # 道悪減点が消えて評価を戻す ▲安田記念で上がり13位＝決め手不足
        6:  ("チェルヴィニア",   12.7,  7.0),  # G1・2勝 ▲追い切りC
        9:  ("アーバンシック",   13.7,  7.0),  # 菊花賞馬 ▲59kg最重量タイ
        10: ("バレエマスター",   27.7,  5.0),  # 穴の根拠を道悪実績→「同コース新潟大賞典2着・上がり最速33.4」に差し替え（良馬場でも買える）
        2:  ("サヴォーナ",       28.7,  3.0),  # 2枠は過去10年0-0-0-16（良馬場でも変わらない）
        7:  ("ジュンブロッサム", 39.1,  2.0),  # 道悪0-0-0-4の減点が良馬場で消滅。新潟芝1800mで上がり32.0の実績
        1:  ("ボーンディスウェイ",56.5,  2.0),
    },
    # 手組みの印（モデルpの並びではなく、印そのもの）
    roles={'H': 5, 'O': 3, 'S': 8, 'D1': 4, 'D2': 11, 'D3': 6, 'D4': 9, 'A': 10},
    budget=4900,   # 前日確定の配分を維持（期待値ベース按分の結果）
    pick="★最終A 穴⑩軸に集中 8点",
    arch="C 波乱狙い型",
    target="800〜1500%",
    # 採用可の3つはすべて穴⑩絡み。人気サイド構成は全てEV不足のため穴に集中する
    final={
        "★最終A 穴⑩軸に集中 8点": [("F8 3連複 穴A軸-相手4頭", 1.0), ("W5 ワイド穴A絡み2点", 0.9)],
        "★最終B 穴⑩軸+馬連 10点": [("F8 3連複 穴A軸-相手4頭", 1.0), ("W5 ワイド穴A絡み2点", 0.8),
                                  ("U6 馬連 穴A絡み2点", 0.6)],
    },
)

RACES["中京2歳S"] = dict(
    label="中京2歳ステークス(G3) 中京芝1400m 9頭 15:35 / 2歳重賞",
    # 当日8:56の実オッズ／馬場は良・Bコース2週目・土曜は基準比−3.2秒の高速
    horses={
        9: ("ジーティーマイカ",   2.0, 28.0),  # 2.4→2.0とさらに売れ断然人気/新馬7馬身差圧勝/追い切りラスト11.4で3頭併せ最先着 ▲左回り初
        4: ("シスキンブルーム",  10.3, 20.0),  # 9.0→10.3と緩み妙味拡大/AI指数トップ86.7/4枠は2歳戦31.8%で最良
        7: ("ビスケットサンド",   4.1, 18.0),  # エンジン3位/阪神1400m新馬を上がり最速で差し切り ▲7枠は2歳戦13.8%で最不振
        3: ("サンタンジェロ",     5.5, 15.0),  # 4.6→5.5と緩む/唯一の中京1400m勝ち馬/馬具工夫で右→左の走りが改善
        5: ("マルモリムソウ",     9.7,  9.0),  # 11.5→9.7と売れて4番人気に浮上/小倉1200m逃げ切り
        2: ("バクソウシャチョウ",14.7,  7.0),  # 中京芝1200mで上がり33.2の2着/坂路この日の一番時計
        6: ("ジャスパートレノ",  21.4,  2.0),  # 15.6→21.4と大きく緩む・芝は初
        8: ("ピコジャック",      53.5,  1.0),
        1: ("ピコキング",        80.0,  1.0),
    },
    roles={'H': 9, 'O': 4, 'S': 7, 'D1': 3, 'D2': 5, 'A': 2},
    budget=15800,  # 前日確定の配分を維持（この日の最大配分）
    pick="★最終B ○④軸+馬連厚め 9点",
    arch="B 標準中穴型",
    target="300〜500%",
    # 選択肢が豊富。○④(9.0倍・p/q2.28)を軸に、的中率と高配当を両取りする
    final={
        "★最終A ○④軸コア+ヘッジ 10点": [("F7 3連複○軸-相手4頭(◎飛び)", 1.0), ("W1 ワイド◎-○ 1点厚張り", 1.1),
                                       ("U1 馬連◎-○ 1点厚張り", 0.9), ("W5 ワイド穴A絡み2点", 0.7)],
        "★最終B ○④軸+馬連厚め 9点": [("F7 3連複○軸-相手4頭(◎飛び)", 1.0), ("U1 馬連◎-○ 1点厚張り", 1.3),
                                    ("U6 馬連 穴A絡み2点", 0.6)],
        "★最終C 的中率寄せ 12点": [("F7 3連複○軸-相手4頭(◎飛び)", 1.0), ("F2 3連複◎○軸-相手3頭", 0.8),
                                 ("W1 ワイド◎-○ 1点厚張り", 1.2), ("W5 ワイド穴A絡み2点", 0.6)],
    },
)


# ══════════════════════════════════════════════════════════
# ── 市場寄り補正（2026-08-30・ユーザー承認）────────────────────────
# 実オッズを入れた途端、平場でE627%・E495%が出た。中身はモデルが1番人気を5%・
# 8番人気を18.5%と評価しており、その乖離を「妙味」と解釈して期待値が発散していた。
# 実測は8/29が回収率8.2%、ROI台帳の通期が46.3%で、モデルの期待値は実測の3〜5倍過大。
# 期待値の計算には p ではなく p_eff = 0.3×p + 0.7×q（市場寄り）を使う。
P_BLEND = 0.5   # 2026-08-30: 前日と同じ評価軸に戻す（0.3の市場寄りは今朝の暫定変更）


def build(race):
    hs = race["horses"]; nums = list(hs.keys())
    tq = sum(0.8 / hs[n][1] for n in nums)
    q = {n: (0.8 / hs[n][1]) / tq for n in nums}
    tp = sum(hs[n][2] for n in nums)
    p_raw = {n: hs[n][2] / tp for n in nums}
    pe = {n: P_BLEND * p_raw[n] + (1 - P_BLEND) * q[n] for n in nums}
    s = sum(pe.values()) or 1
    p = {n: pe[n] / s for n in nums}
    return nums, p, q, p_raw


def order_probs(nums, prob):
    out = {}
    for a, b, c in itertools.permutations(nums, 3):
        pa = prob[a]; rb = 1 - pa
        if rb <= 1e-12: continue
        pb = prob[b] / rb; rc = 1 - pa - prob[b]
        if rc <= 1e-12: continue
        out[(a, b, c)] = pa * (pb) * (prob[c] / rc)
    return out


def payouts(nums, q):
    qo = order_probs(nums, q)
    trio = defaultdict(float); wide = defaultdict(float)
    qn = defaultdict(float);   exa = defaultdict(float); tri = {}
    for (a, b, c), pr in qo.items():
        trio[frozenset((a, b, c))] += pr
        qn[frozenset((a, b))] += pr
        exa[(a, b)] += pr
        tri[(a, b, c)] = pr
        for x, y in itertools.combinations((a, b, c), 2):
            wide[frozenset((x, y))] += pr
    P = {}
    P["trio"] = {k: TRIO_TAKE / v * 100 for k, v in trio.items() if v > 1e-12}
    P["wide"] = {k: WIDE_TAKE / v * 100 for k, v in wide.items() if v > 1e-12}
    P["qn"]   = {k: QN_TAKE / v * 100 for k, v in qn.items() if v > 1e-12}
    P["exa"]  = {k: EX_TAKE / v * 100 for k, v in exa.items() if v > 1e-12}
    P["tri"]  = {k: TR_TAKE / v * 100 for k, v in tri.items() if v > 1e-12}
    P["win"]  = {n: T1_TAKE / q[n] * 100 for n in nums}
    return P


def evaluate(bets, nums, p, P, budget):
    merged = {}
    for kind, key, w in bets:
        merged[(kind, key)] = merged.get((kind, key), 0) + w
    bl = [(k[0], k[1], w) for k, w in merged.items()]
    tw = sum(b[2] for b in bl) or 1
    stakes = []
    for kind, key, w in bl:
        amt = max(100, round(budget * w / tw / 100) * 100)
        stakes.append((kind, key, amt))
    invest = sum(s[2] for s in stakes)

    ev = hit = gami = p300 = p1000 = 0.0
    for (a, b, c), pr in order_probs(nums, p).items():
        ret = 0.0
        for kind, key, amt in stakes:
            if kind == "trio" and key == frozenset((a, b, c)):
                ret += amt * P["trio"].get(key, 0) / 100
            elif kind == "wide" and len(key & {a, b, c}) == 2:
                ret += amt * P["wide"].get(key, 0) / 100
            elif kind == "qn" and key == frozenset((a, b)):
                ret += amt * P["qn"].get(key, 0) / 100
            elif kind == "exa" and key == (a, b):
                ret += amt * P["exa"].get(key, 0) / 100
            elif kind == "tri" and key == (a, b, c):
                ret += amt * P["tri"].get(key, 0) / 100
            elif kind == "win" and key == a:
                ret += amt * P["win"].get(key, 0) / 100
        ev += pr * ret
        if ret > 0:
            hit += pr
            if ret < invest: gami += pr
            if ret >= invest * 3:  p300 += pr
            if ret >= invest * 10: p1000 += pr
    return dict(ev=100 * ev / invest, hit=100 * hit, p300=100 * p300, p1000=100 * p1000,
                gami=100 * gami / hit if hit > 1e-12 else 0.0,
                points=len(stakes), invest=invest, stakes=stakes)


# ══════════════════════════════════════════════════════════
# 全券種ファミリー パターンライブラリ
# ══════════════════════════════════════════════════════════
def build_patterns(R, hs, p, q, nums):
    """R=ロール辞書。戻り: {名前: [(券種,キー,配分比)...]}"""
    H, O, S = R['H'], R['O'], R['S']
    Ds = [R[k] for k in ('D1', 'D2', 'D3', 'D4') if k in R]
    A = R.get('A')
    # 妙味馬V = モデル上位6頭のうちp/q乖離最大
    top6 = sorted(nums, key=lambda n: -p[n])[:6]
    V = max(top6, key=lambda n: p[n] / q[n])
    rel = [O, S] + Ds                      # ◎以外の印
    C = {}

    def T(*a): return ("trio", frozenset(a))
    def W(*a): return ("wide", frozenset(a))
    def Q(*a): return ("qn", frozenset(a))
    def E(a, b): return ("exa", (a, b))
    def R3(a, b, c): return ("tri", (a, b, c))
    def N(n): return ("win", n)

    h_odds = hs[H][1]
    t_gate = 3.0 <= h_odds <= 10.0        # 単勝系ゲート（v5.3）

    # ── 単勝系 ─────────────────────────────
    if t_gate:
        C["T1 単勝◎1点"] = [(*N(H), 1.0)]
        C["T2 単勝◎○2点"] = [(*N(H), 0.6), (*N(O), 0.4)]
        C["T3 単勝◎+ワイド◎-○(ヘッジ)"] = [(*N(H), 0.5), (*W(H, O), 0.5)]
    C["T4 単勝V(妙味馬)1点"] = [(*N(V), 1.0)]
    if A: C["T5 単勝◎+穴A 2点"] = [(*N(H), 0.55), (*N(A), 0.45)]

    # ── 馬連系 ─────────────────────────────
    C["U1 馬連◎-○ 1点厚張り"] = [(*Q(H, O), 1.0)]
    C["U2 馬連◎軸-相手3頭"] = [(*Q(H, x), w) for x, w in zip(rel[:3], (1.2, 1.0, 0.8))]
    C["U3 馬連◎軸-相手4頭"] = [(*Q(H, x), w) for x, w in zip(rel[:4], (1.2, 1.0, 0.9, 0.8))]
    C["U4 馬連上位3頭BOX 3点"] = [(*Q(a, b), 1.0) for a, b in itertools.combinations((H, O, S), 2)]
    C["U5 馬連○軸-相手3頭(◎飛び)"] = [(*Q(O, x), 1.0) for x in [H, S] + Ds[:1]]
    if A:
        C["U6 馬連 穴A絡み2点"] = [(*Q(A, H), 0.55), (*Q(A, O), 0.45)]
        C["U7 馬連◎-○本線+穴A保険"] = [(*Q(H, O), 1.4), (*Q(A, H), 0.8), (*Q(A, O), 0.6)]

    # ── 馬単系 ─────────────────────────────
    C["E1 馬単◎→○ 1点"] = [(*E(H, O), 1.0)]
    C["E2 馬単◎→相手3頭"] = [(*E(H, x), w) for x, w in zip(rel[:3], (1.2, 1.0, 0.8))]
    C["E3 馬単◎⇔○ マルチ2点"] = [(*E(H, O), 0.6), (*E(O, H), 0.4)]
    C["E4 馬単◎→相手4頭+○→◎保険"] = [(*E(H, x), w) for x, w in zip(rel[:4], (1.1, 0.9, 0.8, 0.7))] + [(*E(O, H), 0.7)]
    C["E5 馬単 2着固定(相手→◎)"] = [(*E(x, H), 1.0) for x in rel[:3]]
    if A: C["E6 馬単◎→穴A / ○→穴A"] = [(*E(H, A), 0.55), (*E(O, A), 0.45)]

    # ── ワイド系 ───────────────────────────
    C["W1 ワイド◎-○ 1点厚張り"] = [(*W(H, O), 1.0)]
    C["W2 ワイド◎軸-相手2頭"] = [(*W(H, O), 0.55), (*W(H, S), 0.45)]
    C["W3 ワイド◎軸-相手3頭"] = [(*W(H, x), w) for x, w in zip(rel[:3], (1.2, 1.0, 0.8))]
    C["W4 ワイド上位3頭BOX 3点"] = [(*W(a, b), 1.0) for a, b in itertools.combinations((H, O, S), 2)]
    if A: C["W5 ワイド穴A絡み2点"] = [(*W(A, H), 0.55), (*W(A, O), 0.45)]
    C["W6 ワイドV絡み2点"] = [(*W(V, H), 0.55), (*W(V, O), 0.45)]

    # ── 3連複系 ───────────────────────────
    C["F1 3連複 上位3頭1点"] = [(*T(H, O, S), 1.0)]
    C["F2 3連複◎○軸-相手3頭"] = [(*T(H, O, x), 1.0) for x in [S] + Ds[:2]]
    C["F3 3連複◎軸-相手4頭 6点"] = [(*T(H, a, b), 1.0) for a, b in itertools.combinations(rel[:4], 2)]
    C["F4 3連複◎軸-相手5頭 10点"] = [(*T(H, a, b), 1.0) for a, b in itertools.combinations(rel[:5], 2)] if len(rel) >= 5 else None
    C["F5 3連複 上位4頭BOX 4点"] = [(*T(*c), 1.0) for c in itertools.combinations((H, O, S, Ds[0]), 3)]
    C["F6 3連複 上位5頭BOX 10点"] = [(*T(*c), 1.0) for c in itertools.combinations((H, O, S) + tuple(Ds[:2]), 3)] if len(Ds) >= 2 else None
    C["F7 3連複○軸-相手4頭(◎飛び)"] = [(*T(O, a, b), 1.0) for a, b in itertools.combinations([H, S] + Ds[:2], 2)]
    if A:
        C["F8 3連複 穴A軸-相手4頭"] = [(*T(A, a, b), 1.0) for a, b in itertools.combinations([H, O, S] + Ds[:1], 2)]
        C["F9 3連複◎○軸+穴A 1点"] = [(*T(H, O, A), 1.0)]

    # ── 3連単系 ───────────────────────────
    C["S1 3連単◎1着固定-相手3頭 6点"] = [(*R3(H, a, b), 1.0) for a, b in itertools.permutations(rel[:3], 2)]
    C["S2 3連単◎○1-2着マルチ-3着3頭"] = [(*R3(a, b, c), 1.0)
                                        for a, b in ((H, O), (O, H))
                                        for c in [S] + Ds[:2]]
    C["S3 3連単 上位3頭BOX 6点"] = [(*R3(*pm), 1.0) for pm in itertools.permutations((H, O, S))]
    C["S4 3連単F 1着◎○/2着◎○▲/3着広め"] = [
        (*R3(a, b, c), 1.0)
        for a in (H, O) for b in (H, O, S) for c in [S] + Ds[:3]
        if len({a, b, c}) == 3]
    if A:
        C["S5 3連単F 3着に穴A固定"] = [(*R3(a, b, A), 1.0)
                                     for a, b in itertools.permutations([H, O, S], 2)]
        C["S6 3連単F 1着◎/2-3着に穴A絡め"] = [(*R3(H, b, c), 1.0)
                                            for b, c in itertools.permutations([O, S, A], 2)
                                            if A in (b, c)]

    # ── 人気絡め・妙味馬系 ─────────────────
    C["V1 3連複V軸-相手4頭"] = [(*T(V, a, b), 1.0)
                              for a, b in itertools.combinations([x for x in [H, O, S] + Ds[:2] if x != V], 2)]
    C["V2 ワイドV 2点+3連複V軸4点"] = [(*W(V, H), 1.3), (*W(V, O), 1.1)] + \
                                     [(*T(V, a, b), 0.8) for a, b in itertools.combinations([x for x in [H, O, S] if x != V], 2)]

    # ── ハイブリッド系（券種ミックス）───────
    C["X1 馬連◎-○厚+3連複◎軸4点"] = [(*Q(H, O), 2.0)] + \
        [(*T(H, a, b), 0.7) for a, b in itertools.combinations(rel[:3], 2)]
    C["X2 ワイド2点+馬連1点+3連複4点"] = [(*W(H, O), 1.5), (*W(H, S), 1.1), (*Q(H, O), 1.2)] + \
        [(*T(H, O, x), 0.8) for x in [S] + Ds[:2]] + [(*T(H, S, Ds[0]), 0.7)]
    C["X3 馬単◎→3頭+ワイド保険2点"] = [(*E(H, x), w) for x, w in zip(rel[:3], (1.2, 1.0, 0.8))] + \
        [(*W(H, O), 1.0), (*W(H, S), 0.8)]
    if A:
        C["X4 3連単F少点+3連複本線+穴ワイド"] = \
            [(*R3(a, b, c), 0.5) for a, b in ((H, O), (O, H)) for c in [S, Ds[0]]] + \
            [(*T(H, O, S), 1.3), (*T(H, O, Ds[0]), 1.0), (*T(H, S, Ds[0]), 0.9)] + \
            [(*W(A, H), 1.0), (*W(A, O), 0.8)]
        C["X5 単勝/馬連/3連複/穴の4層"] = \
            ([(*N(H), 1.2)] if t_gate else []) + \
            [(*Q(H, O), 1.3), (*Q(H, S), 0.9)] + \
            [(*T(H, O, S), 1.2), (*T(H, O, Ds[0]), 0.9), (*T(H, S, Ds[0]), 0.8)] + \
            [(*W(A, H), 0.9), (*T(H, O, A), 0.8)]
        C["X6 3連複広め+穴3連単でレバレッジ"] = \
            [(*T(H, a, b), 0.9) for a, b in itertools.combinations(rel[:4], 2)] + \
            [(*T(A, H, O), 1.0), (*T(A, H, S), 0.9)] + \
            [(*R3(H, O, A), 0.7), (*R3(O, H, A), 0.6)]

    return {k: v for k, v in C.items() if v}, V


# ══════════════════════════════════════════════════════════
def guard_ok(name, bets, R, hs, p, q, nums):
    """SKILL.md v5.2〜v5.8 のガードを機械適用。戻り: (可否, 理由)

    v1の反省: 「○を含む点が7割超」で弾くと上位4頭BOX（構造上3/4が○絡み）まで
    誤って除外してしまった。BOXは○が飛んでも他の3頭で当たるので○依存ではない。
    正しくは「○を含まない点が1つも無い＝○が飛ぶと全滅」で判定する。
    同様に「3連単のみの構成」を一律禁止すると3連単BOX・マルチまで消えるため、
    禁止対象は本来の「◎の1着固定のみ」に限定する。
    """
    H, O = R['H'], R['O']
    rank = {n: i + 1 for i, n in enumerate(sorted(nums, key=lambda x: hs[x][1]))}
    kinds = {kd for kd, _, _ in bets}
    keys = [(kd, k) for kd, k, _ in bets]

    def has(k, n):
        if isinstance(k, frozenset): return n in k
        if isinstance(k, tuple): return n in k
        return k == n

    # (1) 人気1-2位の2頭軸に偏る構成は禁止（v5.7）
    if rank[H] == 1 and rank[O] == 2:
        two = sum(1 for _, k in keys if isinstance(k, frozenset) and {H, O} <= set(k))
        if two >= max(1, len(keys) * 0.5):
            return False, "人気1-2位の2頭軸に偏る（v5.7）"

    # (2) ○が飛ぶと全滅する構成は、○に明確な妙味がある場合のみ許可（v5.8）
    if all(has(k, O) for _, k in keys) and p[O] / q[O] < 1.4:
        return False, "全点が○絡み＝○が飛ぶと全滅／かつ○に妙味なし（v5.8）"

    # (3) ◎単独軸でヘッジのない単勝・3連単は禁止（v5.7）
    if kinds == {"win"} and len(bets) == 1:
        return False, "単勝1点のみでヘッジなし（v5.7）"
    if kinds == {"tri"} and all(k[0] == H for kd, k in keys if kd == "tri"):
        return False, "3連単の◎1着固定のみでヘッジなし（v5.7）"

    return True, ""


def main():
    for rname, race in RACES.items():
        nums, p, q, p_raw = build(race)
        P = payouts(nums, q); hs = race["horses"]; R = race["roles"]
        budget = race["budget"]
        cands, V = build_patterns(R, hs, p, q, nums)
        R['V'] = V
        # 採用可パターンを合成した「最終構成」を候補に加える
        for mn, mk in race.get("final", {}).items():
            merged = []
            for key, wt in mk:
                merged += [(kd, k, w * wt) for kd, k, w in cands[key]]
            cands[mn] = merged

        print("\n" + "=" * 108)
        print("■ %s" % race["label"])
        print("   類型: %s ／ 目標回収率: %s ／ 予算: %s円" % (race["arch"], race["target"], f"{budget:,}"))
        print("=" * 108)
        lab = {R['H']: '◎', R['O']: '○', R['S']: '▲', R.get('A'): '🔥穴'}
        for k in ('D1', 'D2', 'D3', 'D4'):
            if k in R: lab.setdefault(R[k], '△')
        print("%-4s %-18s %8s %7s %7s %7s %7s  %s" % ("馬番", "馬名", "実オッズ", "生p", "補正p", "大衆q", "p/q", "印"))
        for n in sorted(nums, key=lambda x: -p[x]):
            print("%-4d %-18s %7.1f倍 %6.1f%% %6.1f%% %6.1f%% %6.2f  %s%s" % (
                n, hs[n][0], hs[n][1], 100 * p_raw[n], 100 * p[n], 100 * q[n], p[n] / q[n],
                lab.get(n, ""), "  ★V(妙味最大)" if n == V else ""))

        rows = []
        for name, bets in cands.items():
            ok_g, why_g = guard_ok(name, bets, R, hs, p, q, nums)
            r = evaluate(bets, nums, p, P, budget)
            r['guard'] = ok_g; r['guard_why'] = why_g
            rows.append((name, r))

        print("\n  %-34s %5s %9s %8s %8s %9s %7s  %s" %
              ("パターン", "点数", "E[回収率]", "的中率", "P(300%+)", "P(1000%+)", "ガミ率", "判定"))
        adopt = []
        for name, r in sorted(rows, key=lambda x: -x[1]["ev"]):
            if not r['guard']:
                v = "✕ガード"
            elif r["ev"] >= 115 and r["gami"] <= 35:
                v = "◎採用可"; adopt.append((name, r))
            elif r["ev"] < 115:
                v = "△EV不足"
            else:
                v = "×ガミ過多"
            print("  %-34s %4d点 %8.0f%% %7.1f%% %7.1f%% %8.1f%% %6.1f%%  %s" % (
                name, r["points"], r["ev"], r["hit"], r["p300"], r["p1000"], r["gami"], v))

        print("\n  ── 採用候補（基準クリア）を目的別に整理 ─────────────────────────")
        if not adopt:
            print("   なし = 見送り候補")
        else:
            best_ev = max(adopt, key=lambda x: x[1]["ev"])
            best_hit = max(adopt, key=lambda x: x[1]["hit"])
            best_p300 = max(adopt, key=lambda x: x[1]["p300"])
            best_p1000 = max(adopt, key=lambda x: x[1]["p1000"])
            for lbl, (nm, r) in (("期待値が最大", best_ev), ("的中率が最大", best_hit),
                                 ("300%超の確率が最大", best_p300), ("1000%超の確率が最大", best_p1000)):
                print("   %-20s %-34s E%3.0f%% 的中%4.1f%% P300 %4.1f%% P1000 %4.1f%% ガミ%4.1f%%" % (
                    lbl, nm, r["ev"], r["hit"], r["p300"], r["p1000"], r["gami"]))

        # ── 採用構成の買い目明細＋配当シミュレーション ──────────
        pick = race.get("pick")
        rd = dict(rows)
        if not pick or pick not in rd:
            continue
        r = rd[pick]
        print("\n" + "-" * 108)
        print("  【採用】%s  合計%d点・%s円  E%.0f%% / 的中%.1f%% / P300 %.1f%% / P1000 %.1f%% / ガミ%.1f%%" % (
            pick, r["points"], f"{r['invest']:,}", r["ev"], r["hit"], r["p300"], r["p1000"], r["gami"]))
        print("-" * 108)
        KN = {"trio": "3連複", "wide": "ワイド", "qn": "馬連", "exa": "馬単", "tri": "3連単", "win": "単勝"}
        SEP = {"trio": "-", "wide": "-", "qn": "-", "exa": "→", "tri": "→"}
        by = defaultdict(list)
        for kind, key, amt in r["stakes"]:
            by[kind].append((key, amt))
        for kind in ("win", "qn", "exa", "wide", "trio", "tri"):
            if kind not in by: continue
            lst = sorted(by[kind], key=lambda x: -x[1])
            print("  【%s】（%d点 %s円）" % (KN[kind], len(lst), f"{sum(a for _, a in lst):,}"))
            for key, amt in lst:
                if kind == "win":
                    disp = m(key)
                elif isinstance(key, frozenset):
                    disp = SEP[kind].join(m(x) for x in sorted(key))
                else:
                    disp = SEP[kind].join(m(x) for x in key)
                print("　　%s %s円" % (disp, f"{amt:,}"))
        print("\n  📌 配当シミュレーション（前日実オッズからの推定）")
        shown, seen = 0, set()
        for (a, b, c), pr in sorted(order_probs(nums, p).items(), key=lambda x: -x[1]):
            k3 = frozenset((a, b, c))
            if k3 in seen: continue
            seen.add(k3)
            ret = 0.0
            for kind, key, amt in r["stakes"]:
                if kind == "trio" and key == k3: ret += amt * P["trio"].get(key, 0) / 100
                elif kind == "wide" and len(key & {a, b, c}) == 2: ret += amt * P["wide"].get(key, 0) / 100
                elif kind == "qn" and key == frozenset((a, b)): ret += amt * P["qn"].get(key, 0) / 100
                elif kind == "exa" and key == (a, b): ret += amt * P["exa"].get(key, 0) / 100
                elif kind == "tri" and key == (a, b, c): ret += amt * P["tri"].get(key, 0) / 100
                elif kind == "win" and key == a: ret += amt * P["win"].get(key, 0) / 100
            if ret <= 0: continue
            print("　　%s-%s-%s（%s/%s/%s）→ 約%s円（%.0f%%）" % (
                m(a), m(b), m(c), hs[a][0][:7], hs[b][0][:7], hs[c][0][:7],
                f"{int(ret):,}", 100 * ret / r["invest"]))
            shown += 1
            if shown >= 7: break


if __name__ == "__main__":
    main()
