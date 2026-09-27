# -*- coding: utf-8 -*-
"""
gen_kaime_v5.py — v5 EVアダプティブ買い目構築（パターンライブラリ選択方式）

53種の買い目パターンをライブラリ化し、レースごとに全パターンを機械評価して
「期待回収率」と「回収率300%以上の達成確率」が最大のパターンを自動選択する。
（v5.6/2026-08-19: 穴印A系4種・広め流しF8/F9・○軸O1を追加、非◎軸の保守並行評価を導入）

確率モデル:
  p (モデル勝率)   = ML能力%をレース内正規化
  q (大衆勝率推定) = 近走着順・ML・騎手勝率から大衆の賭け行動を推定しsoftmax
  想定オッズ       = 払戻率 / q系確率（Harville式で連系に展開）
  各パターンの評価 = 上位馬の着順シナリオを全列挙し、E[回収率]とP(回収率>=300%)を計算

選択基準:
  E[回収率] >= 115% のパターンの中から P(回収率>=300%) 最大を選択。
  1つも基準を満たさなければ「見送り」。

予算: 自信度連動（10=15,000 / 9=12,000 / 8=8,000 / 7=5,000）

使い方:
  python gen_kaime_v5.py --json <records.json> [--conf-min 7] [--odds-file odds.json]
  odds.json: {"YYYYMMDD_会場_R": {"馬番": 単勝オッズ, ...}} 形式で実オッズ上書き可
"""
from __future__ import annotations
import sys, json, math, argparse, itertools
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_weekend_confidence_report import calc_confidence
import payout_correction   # 想定オッズの実配当補正（v6.1・切り戻しは ENABLED=False）

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

FONT = '游ゴシック'
BUDGET_BY_CONF = {10: 15000, 9: 12000, 8: 8000, 7: 5000}
TAKEOUT = {'単勝': 0.80, '複勝': 0.80, '馬連': 0.775, 'ワイド': 0.775,
           '馬単': 0.75, '3連複': 0.75, '3連単': 0.725}
EV_MIN   = 1.15   # E[回収率]の下限
TARGET   = 3.0    # 目標回収率300%
ENUM_TOP = 10     # 着順シナリオ列挙対象の上位頭数


# ============================================================
# 確率モデル（累積DB9,259戦の実測テーブルで較正）
#
# 設計思想: モデルpと大衆qは同じ「順位→勝率」形状を使い、
# 「並び順のズレ」（モデルが上位評価×大衆が人気薄）からEVを取る。
# 人気順位別の実測勝率(1人気34.9%/2人気18.2%/...)は市場の実勢と一致
# しており、これを両者の較正テーブルに使う。
# ============================================================
RANK_WIN_TABLE = [0.349, 0.182, 0.128, 0.112, 0.075, 0.053,
                  0.033, 0.033, 0.016, 0.017, 0.012, 0.010,
                  0.008, 0.007, 0.006, 0.005, 0.004, 0.004]


def zscores(vals):
    n = len(vals)
    mu = sum(vals) / n
    sd = (sum((v-mu)**2 for v in vals) / n) ** 0.5 or 1.0
    return [(v-mu)/sd for v in vals]


def _rank_table_probs(order, n, strength=None, adj=0.25):
    """順位リスト(order[i]=そのインデックスの順位0起点)に実測テーブルを割当て正規化。
    strength(0-1正規化済み)があれば±adjの範囲で微調整。"""
    probs = [0.0]*n
    for i in range(n):
        base = RANK_WIN_TABLE[order[i]] if order[i] < len(RANK_WIN_TABLE) else 0.003
        if strength is not None:
            base *= (1.0 - adj) + 2*adj*strength[i]
        probs[i] = base
    s = sum(probs)
    return [x/s for x in probs]


def model_probs(recs):
    """p: モデル勝率。総合指数の並び順に実測テーブルを割当、ML強度で微調整。"""
    n = len(recs)
    idx_sorted = sorted(range(n), key=lambda i: -recs[i]['総合指数'])
    order = [0]*n
    for rank, i in enumerate(idx_sorted):
        order[i] = rank
    mls = [r['ML能力%'] for r in recs]
    mn, mx = min(mls), max(mls)
    strength = [(v-mn)/(mx-mn) if mx > mn else 0.5 for v in mls]
    return _rank_table_probs(order, n, strength)


def public_probs(recs, odds_override=None):
    """q: 大衆勝率。実オッズがあれば0.8/oddsを正規化（最優先）。
    なければ大衆スコア（近走着順・ML・騎手）の並び順に実測人気テーブルを割当。"""
    n = len(recs)
    if odds_override:
        qs = []
        for r in recs:
            od = odds_override.get(str(r['馬番']))
            qs.append(0.8/float(od) if od else None)
        known = [x for x in qs if x is not None]
        if known:
            rest = max(0.05, 1.0 - sum(known))
            n_unk = sum(1 for x in qs if x is None)
            qs = [x if x is not None else rest/max(n_unk,1) for x in qs]
            s = sum(qs)
            return [x/s for x in qs]
    fins = [r.get('近5走平均着', 0) or 0 for r in recs]
    valid = sorted([f for f in fins if f > 0])
    med = valid[len(valid)//2] if valid else 5.0
    fin_score = [-(f if f > 0 else med) for f in fins]
    ml_score  = [r['ML能力%'] for r in recs]
    jk_score  = [r.get('騎手勝率%', 0) for r in recs]
    crowd = [0.40*a + 0.40*b + 0.20*c
             for a, b, c in zip(zscores(ml_score), zscores(fin_score), zscores(jk_score))]
    idx_sorted = sorted(range(n), key=lambda i: -crowd[i])
    order = [0]*n
    for rank, i in enumerate(idx_sorted):
        order[i] = rank
    return _rank_table_probs(order, n)


def harville_exacta(p, i, j):
    return p[i] * p[j] / max(1e-9, 1 - p[i])

def harville_trifecta(p, i, j, k):
    return p[i] * p[j] / max(1e-9, 1-p[i]) * p[k] / max(1e-9, 1-p[i]-p[j])


def bet_prob(p, btype, horses):
    """モデル確率pでの各券種的中確率（horses=index tuple）"""
    n = len(p)
    if btype == '単勝':
        return p[horses[0]]
    if btype == '馬単':
        return harville_exacta(p, horses[0], horses[1])
    if btype == '馬連':
        i, j = horses
        return harville_exacta(p, i, j) + harville_exacta(p, j, i)
    if btype == '3連単':
        return harville_trifecta(p, *horses)
    if btype == '3連複':
        return sum(harville_trifecta(p, a, b, c)
                   for a, b, c in itertools.permutations(horses))
    if btype == 'ワイド':
        i, j = horses
        tot = 0.0
        for a, b, c in itertools.permutations(range(n), 3):
            if {i, j} <= {a, b, c}:
                tot += harville_trifecta(p, a, b, c)
        return tot
    return 0.0


def est_odds(q, btype, horses):
    """大衆確率qからの想定オッズ = 払戻率/q_bet

    Harville式は高配当を過大評価する（確定払戻1,044レースで実測）。
    そのままだと200倍超の3連複を実際の1.85倍に見積もり、期待値を過信する。
    payout_correction で実配当水準に引き戻す。
    """
    qb = bet_prob(q, btype, horses)
    raw = max(1.1, TAKEOUT[btype] / max(qb, 1e-6))
    return payout_correction.apply(btype, raw)


# ============================================================
# パターンライブラリ v5.6（53種）
# 各パターン: (name, 説明, legs) legs=[(券種, 馬キー tuple, 配分比率)]
# 馬キー: 'H'=◎ 'O'=○ 'S'=▲ 'D1'〜'D5'=△(頭数可変) / 'A'=🔥穴印
#         'P1' 'P2'=想定人気上位(◎以外) / 'V'=妙味馬(p/q乖離最大・◎以外)
# ============================================================
def build_pattern_library():
    P = []

    # ── 単勝系（4）────────────────────────────────────
    P.append(("T1 単勝一点",       "◎単勝に全額。人気薄◎の最効率形",
              [('単勝', ('H',), 1.00)]))
    P.append(("T2 単勝+馬連",      "単勝主軸+◎-○馬連",
              [('単勝', ('H',), 0.70), ('馬連', ('H','O'), 0.30)]))
    P.append(("T3 単勝+ワイド",    "単勝主軸+ワイド保険",
              [('単勝', ('H',), 0.60), ('ワイド', ('H','O'), 0.40)]))
    P.append(("T4 二頭単勝",       "◎○両方の単勝。2強で どちらが勝っても",
              [('単勝', ('H',), 0.65), ('単勝', ('O',), 0.35)]))

    # ── 馬連系（6）────────────────────────────────────
    P.append(("U1 馬連1点厚張り",  "◎-○集中",
              [('馬連', ('H','O'), 1.00)]))
    P.append(("U2 馬連2点",        "◎-○/◎-▲",
              [('馬連', ('H','O'), 0.60), ('馬連', ('H','S'), 0.40)]))
    P.append(("U3 馬連流し3頭",    "◎から傾斜配分",
              [('馬連', ('H','O'), 0.45), ('馬連', ('H','S'), 0.30), ('馬連', ('H','D1'), 0.25)]))
    P.append(("U4 馬連流し4頭",    "◎から広めに傾斜",
              [('馬連', ('H','O'), 0.35), ('馬連', ('H','S'), 0.28), ('馬連', ('H','D1'), 0.22), ('馬連', ('H','D2'), 0.15)]))
    P.append(("U5 馬連BOX3頭",     "上位3頭ボックス",
              [('馬連', ('H','O'), 0.40), ('馬連', ('H','S'), 0.32), ('馬連', ('O','S'), 0.28)]))
    P.append(("U6 対抗軸馬連",     "○軸流し。◎過剰人気時の本命外し",
              [('馬連', ('O','H'), 0.40), ('馬連', ('O','S'), 0.32), ('馬連', ('O','D1'), 0.28)]))

    # ── 馬単系（6）────────────────────────────────────
    P.append(("E1 馬単1点",        "◎→○の1着固定1点",
              [('馬単', ('H','O'), 1.00)]))
    P.append(("E2 馬単裏表",       "◎⇔○",
              [('馬単', ('H','O'), 0.60), ('馬単', ('O','H'), 0.40)]))
    P.append(("E3 馬単流し3頭",    "◎1着固定→3頭",
              [('馬単', ('H','O'), 0.40), ('馬単', ('H','S'), 0.32), ('馬単', ('H','D1'), 0.28)]))
    P.append(("E4 馬単流し4頭",    "◎1着固定→4頭",
              [('馬単', ('H','O'), 0.35), ('馬単', ('H','S'), 0.28), ('馬単', ('H','D1'), 0.20), ('馬単', ('H','D2'), 0.17)]))
    P.append(("E5 馬単2着固定",    "◎2着付け。人気馬勝ち×穴◎2着の構図",
              [('馬単', ('O','H'), 0.40), ('馬単', ('S','H'), 0.32), ('馬単', ('D1','H'), 0.28)]))
    P.append(("E6 馬単+単勝複合",  "1着固定+単勝で絞り切る",
              [('単勝', ('H',), 0.30), ('馬単', ('H','O'), 0.28), ('馬単', ('H','S'), 0.22), ('馬単', ('H','D1'), 0.20)]))

    # ── ワイド系（5）──────────────────────────────────
    P.append(("W1 ワイド1点厚張り", "◎-○集中。複勝圏×2の堅実最大化",
              [('ワイド', ('H','O'), 1.00)]))
    P.append(("W2 ワイド2点",       "◎-○/◎-▲",
              [('ワイド', ('H','O'), 0.55), ('ワイド', ('H','S'), 0.45)]))
    P.append(("W3 ワイド流し3頭",   "◎軸で広く",
              [('ワイド', ('H','O'), 0.40), ('ワイド', ('H','S'), 0.32), ('ワイド', ('H','D1'), 0.28)]))
    P.append(("W4 ワイドBOX3頭",    "上位3頭の2頭で的中",
              [('ワイド', ('H','O'), 0.36), ('ワイド', ('H','S'), 0.34), ('ワイド', ('O','S'), 0.30)]))
    P.append(("W5 穴ワイド2点",     "△の穴を軸に◎○へ",
              [('ワイド', ('D1','H'), 0.55), ('ワイド', ('D1','O'), 0.45)]))

    # ── 3連複系（7）──────────────────────────────────
    P.append(("F1 3連複軸2頭3点",  "◎○固定×3頭目流し",
              [('3連複', ('H','O','S'), 0.40), ('3連複', ('H','O','D1'), 0.33), ('3連複', ('H','O','D2'), 0.27)]))
    P.append(("F2 3連複1点厚張り", "◎○▲で決まる読み",
              [('3連複', ('H','O','S'), 1.00)]))
    P.append(("F3 3連複軸1頭3点",  "◎軸×相手3頭",
              [('3連複', ('H','O','S'), 0.40), ('3連複', ('H','O','D1'), 0.32), ('3連複', ('H','S','D1'), 0.28)]))
    P.append(("F4 3連複軸1頭6点",  "◎軸×相手4頭全組合せ",
              [('3連複', ('H','O','S'), 0.24), ('3連複', ('H','O','D1'), 0.19), ('3連複', ('H','O','D2'), 0.15),
               ('3連複', ('H','S','D1'), 0.16), ('3連複', ('H','S','D2'), 0.14), ('3連複', ('H','D1','D2'), 0.12)]))
    P.append(("F5 3連複BOX4頭",    "上位4頭ボックス",
              [('3連複', ('H','O','S'), 0.30), ('3連複', ('H','O','D1'), 0.26),
               ('3連複', ('H','S','D1'), 0.24), ('3連複', ('O','S','D1'), 0.20)]))
    P.append(("F6 3連複▲2頭軸",   "◎▲軸。○が過剰人気の時",
              [('3連複', ('H','S','O'), 0.40), ('3連複', ('H','S','D1'), 0.33), ('3連複', ('H','S','D2'), 0.27)]))
    P.append(("F7 3連複本命外し",  "○▲△軸。◎が過剰人気で飛ぶ読み",
              [('3連複', ('O','S','D1'), 0.40), ('3連複', ('O','S','D2'), 0.32), ('3連複', ('O','D1','D2'), 0.28)]))

    # ── 3連単系（6）──────────────────────────────────
    P.append(("S1 3連単1点",       "◎→○→▲の完全決め打ち",
              [('3連単', ('H','O','S'), 1.00)]))
    P.append(("S2 3連単2点",       "◎→(○▲)→(▲○)",
              [('3連単', ('H','O','S'), 0.55), ('3連単', ('H','S','O'), 0.45)]))
    P.append(("S3 3連単1着固定4点", "◎→(○▲)→(○▲△)",
              [('3連単', ('H','O','S'), 0.30), ('3連単', ('H','O','D1'), 0.22),
               ('3連単', ('H','S','O'), 0.27), ('3連単', ('H','S','D1'), 0.21)]))
    P.append(("S4 3連単1着固定6点", "◎→(○▲)→(○▲△△)",
              [('3連単', ('H','O','S'), 0.22), ('3連単', ('H','O','D1'), 0.17), ('3連単', ('H','O','D2'), 0.13),
               ('3連単', ('H','S','O'), 0.20), ('3連単', ('H','S','D1'), 0.15), ('3連単', ('H','S','D2'), 0.13)]))
    P.append(("S5 3連単1-2着固定", "(◎○)⇔(○◎)×3着流し3頭",
              [('3連単', ('H','O','S'), 0.20), ('3連単', ('H','O','D1'), 0.17), ('3連単', ('H','O','D2'), 0.14),
               ('3連単', ('O','H','S'), 0.19), ('3連単', ('O','H','D1'), 0.16), ('3連単', ('O','H','D2'), 0.14)]))
    P.append(("S6 3連単BOX3頭",    "◎○▲の全順列6点",
              [('3連単', ('H','O','S'), 0.18), ('3連単', ('H','S','O'), 0.17), ('3連単', ('O','H','S'), 0.17),
               ('3連単', ('O','S','H'), 0.16), ('3連単', ('S','H','O'), 0.16), ('3連単', ('S','O','H'), 0.16)]))

    # ── 人気上位絡め系（3）────────────────────────────
    P.append(("N1 単勝+人気馬連",  "◎単勝+人気上位2頭への馬連カバー",
              [('単勝', ('H',), 0.45), ('馬連', ('H','P1'), 0.20), ('馬連', ('H','P2'), 0.15), ('馬連', ('H','O'), 0.20)]))
    P.append(("N2 人気軸3連複",    "人気P1を3頭目に固定して点数圧縮",
              [('3連複', ('H','O','P1'), 0.55), ('3連複', ('H','S','P1'), 0.45)]))
    P.append(("N3 人気馬単絡み",   "P1→◎の2着付け+◎→P1",
              [('馬単', ('P1','H'), 0.55), ('馬単', ('H','P1'), 0.45)]))

    # ── 妙味馬(V)アンカー系（4）──────────────────────
    P.append(("V1 妙味単勝ドカン", "p/q乖離最大馬の単勝集中",
              [('単勝', ('V',), 0.70), ('ワイド', ('V','H'), 0.30)]))
    P.append(("V2 妙味ワイド",     "V軸ワイドで乖離を安全に回収",
              [('ワイド', ('V','H'), 0.55), ('ワイド', ('V','O'), 0.45)]))
    P.append(("V3 妙味3連複",      "◎○にVを絡めて配当ジャンプ",
              [('3連複', ('H','O','V'), 0.60), ('3連複', ('H','S','V'), 0.40)]))
    P.append(("V4 妙味馬単",       "V→◎/V→○の1着固定",
              [('馬単', ('V','H'), 0.55), ('馬単', ('V','O'), 0.45)]))

    # ── v5.6 拡張（2026-08-19ユーザー承認・穴印/広め流し/○軸）──
    # 'A'=🔥穴印の馬（合算v2の穴シグナル該当）。役割が無いレースでは自動スキップ
    P.append(("A1 穴ワイド2点",    "🔥穴軸を◎○へ。穴シグナル該当時の標準捕捉",
              [('ワイド', ('A','H'), 0.55), ('ワイド', ('A','O'), 0.45)]))
    P.append(("A2 穴3連複添え",    "本線◎○/◎▲に穴を1頭添える（レディネス型）",
              [('3連複', ('H','O','A'), 0.60), ('3連複', ('H','S','A'), 0.40)]))
    P.append(("A3 穴軸3連複",      "穴軸-上位3頭。波乱本線の獲り切り",
              [('3連複', ('A','H','O'), 0.45), ('3連複', ('A','H','S'), 0.30), ('3連複', ('A','O','S'), 0.25)]))
    P.append(("A4 穴2着馬単",      "人気サイド勝ち×穴2着の構図",
              [('馬単', ('H','A'), 0.55), ('馬単', ('O','A'), 0.45)]))
    P.append(("F8 3連複軸1頭広め", "◎軸-相手5頭全組合せ10点（△3頭以上で発動・波乱捕捉）",
              [('3連複', ('H','O','S'), 0.16), ('3連複', ('H','O','D1'), 0.12), ('3連複', ('H','O','D2'), 0.10),
               ('3連複', ('H','O','D3'), 0.08), ('3連複', ('H','S','D1'), 0.11), ('3連複', ('H','S','D2'), 0.09),
               ('3連複', ('H','S','D3'), 0.08), ('3連複', ('H','D1','D2'), 0.10), ('3連複', ('H','D1','D3'), 0.08),
               ('3連複', ('H','D2','D3'), 0.08)]))
    P.append(("F9 3連複軸2頭広め", "◎○軸-相手5頭（実証勝ち筋の広め版・△3頭+穴印で発動）",
              [('3連複', ('H','O','S'), 0.28), ('3連複', ('H','O','D1'), 0.22), ('3連複', ('H','O','D2'), 0.18),
               ('3連複', ('H','O','D3'), 0.17), ('3連複', ('H','O','A'), 0.15)]))
    P.append(("O1 対抗軸3連複6点", "○軸-相手4頭全組合せ（◎飛びクラスタ対策・F4の○軸版）",
              [('3連複', ('O','H','S'), 0.24), ('3連複', ('O','H','D1'), 0.19), ('3連複', ('O','H','D2'), 0.15),
               ('3連複', ('O','S','D1'), 0.16), ('3連複', ('O','S','D2'), 0.14), ('3連複', ('O','D1','D2'), 0.12)]))

    # ── ハイブリッド系（5）────────────────────────────
    P.append(("X1 単勝+3連複",     "単勝ドカン+3連複ボーナス二段構え",
              [('単勝', ('H',), 0.45), ('3連複', ('H','O','S'), 0.22), ('3連複', ('H','O','D1'), 0.18), ('3連複', ('H','S','D1'), 0.15)]))
    P.append(("X2 馬単+ワイド保険", "1着固定レバレッジ+ワイドでガミ回避",
              [('馬単', ('H','O'), 0.35), ('馬単', ('H','S'), 0.25), ('ワイド', ('H','O'), 0.40)]))
    P.append(("X3 馬連+3連単",     "馬連本線+3連単1点夢",
              [('馬連', ('H','O'), 0.60), ('馬連', ('H','S'), 0.25), ('3連単', ('H','O','S'), 0.15)]))
    P.append(("X4 ワイド+3連複BOX", "複勝圏能力の二重取り",
              [('ワイド', ('H','O'), 0.40), ('3連複', ('H','O','S'), 0.25), ('3連複', ('H','O','D1'), 0.20), ('3連複', ('H','S','D1'), 0.15)]))
    P.append(("X5 v4型3ブロック",  "旧v4構造（比較用ベースライン）",
              [('馬連', ('H','O'), 0.40), ('馬連', ('H','S'), 0.20), ('ワイド', ('H','O'), 0.25), ('馬連', ('O','S'), 0.15)]))

    return P


PATTERNS = build_pattern_library()


# ============================================================
# パターン評価
# ============================================================
def resolve_key(key, roles):
    return roles.get(key)


def evaluate_pattern(legs, roles, p, q, budget):
    """
    Returns dict(E_return_rate, P_target, P_hit, bets) or None（馬役割欠落時）
    bets = [(券種, 馬番表記, 金額, 想定オッズ, モデル的中率%)]
    """
    n = len(p)
    resolved = []
    for btype, keys, frac in legs:
        idxs = tuple(resolve_key(k, roles) for k in keys)
        if any(i is None for i in idxs):
            return None
        if len(set(idxs)) != len(idxs):
            return None
        amount = max(100, int(round(budget * frac / 100.0)) * 100)
        odds = est_odds(q, btype, idxs)
        resolved.append((btype, idxs, amount, odds))

    total_amt = sum(a for _, _, a, _ in resolved)

    # 着順シナリオ列挙（モデルp上位ENUM_TOP頭の順序3つ組）
    top_idx = sorted(range(n), key=lambda i: -p[i])[:min(n, ENUM_TOP)]
    E_ret = 0.0
    P_target = 0.0
    P_hit = 0.0
    P_gami = 0.0    # 的中したのに投資額を下回る「ガミ」確率
    for a, b, c in itertools.permutations(top_idx, 3):
        pr = harville_trifecta(p, a, b, c)
        ret = 0.0
        for btype, idxs, amount, odds in resolved:
            hit = False
            if btype == '単勝':
                hit = (a == idxs[0])
            elif btype == '馬単':
                hit = ((a, b) == idxs)
            elif btype == '馬連':
                hit = ({a, b} == set(idxs))
            elif btype == 'ワイド':
                hit = set(idxs) <= {a, b, c}
            elif btype == '3連複':
                hit = ({a, b, c} == set(idxs))
            elif btype == '3連単':
                hit = ((a, b, c) == idxs)
            if hit:
                ret += amount * odds
        if ret > 0:
            P_hit += pr
            E_ret += pr * ret
            if ret >= TARGET * total_amt:
                P_target += pr
            if ret < total_amt:
                P_gami += pr
    # 残余確率（上位外が絡む）は回収0と保守評価
    gami_ratio = P_gami / P_hit if P_hit > 0 else 1.0
    return {
        'E_rate': E_ret / total_amt,
        'P_target': P_target,
        'P_hit': P_hit,
        'P_gami': P_gami,
        'gami_ratio': gami_ratio,
        'bets': resolved,
        'total': total_amt,
    }


# ── v5.2 PDCA改修（2026-08-01 土曜検証の教訓）────────────
# ① 若馬戦(新馬・未勝利)は◎の信頼度が過大になりやすく、実際に自信度10の
#    ◎が2頭とも大敗（8着・9着）。一方○▲は好走 → 1点集中型パターンを禁止し
#    予算も60%に圧縮する。
# ② V系(妙味馬)は推定オッズの誤差で「妙味の幻影」が発生（2戦0勝）
#    → 実オッズ(--odds-file)がある時のみ候補に入れる。
# ── v5.3 PDCA改修（2026-08-02 日曜検証の教訓）────────────
# ③ 若馬戦の禁止対象に馬単系流し(E3/E4)を追加。「◎1着前提」の券種は
#    若馬では全て危険（新潟1R E4馬単流し: ◎4着で全損）。
# ④ 単勝系(T1/T2/T3)は◎の実オッズが3.0〜10.0倍の時のみ許可。
#    PDCA100実測で1〜2.6倍帯はROI100%未満（中京6R: 1.4倍に単勝集中で140%止まり）。
CONCENTRATED_PATTERNS = {'T1', 'T2', 'T4', 'U1', 'W1', 'E1', 'S1', 'S2', 'E3', 'E4'}
V_PATTERNS = {'V1', 'V2', 'V3', 'V4'}
TANSHO_PATTERNS = {'T1', 'T2', 'T3'}
# v5.6: 非◎軸パターンは通常pに加え「◎のpを10%割り引いた保守p」でも並行評価し、
# 両者の平均メトリクスで順位付けする（選択器の◎バイアス中和・2026-08-19承認）
NON_HON_AXIS_PATTERNS = {'U6', 'E5', 'F7', 'W5', 'O1', 'A3'}
TANSHO_ODDS_MIN, TANSHO_ODDS_MAX = 3.0, 10.0
YOUNG_RACE_BUDGET_MULT = 0.6


def is_young_race(title):
    return ('新馬' in str(title)) or ('未勝利' in str(title))


def choose_pattern(recs, budget, odds_override=None):
    """全パターンを評価し最良を返す。(name, desc, result, ranking) or (None,...)=見送り"""
    title = recs[0].get('レース名', '') if recs else ''
    young = is_young_race(title)
    if young:
        budget = max(3000, int(round(budget * YOUNG_RACE_BUDGET_MULT / 1000)) * 1000)
    p = model_probs(recs)
    q = public_probs(recs, odds_override)
    idx_by_num = {r['馬番']: i for i, r in enumerate(recs)}
    marks = {r['AI印']: r for r in recs if r['AI印'] and r['AI印'] != '△'}
    deltas = [r for r in recs if r['AI印'] == '△']
    # 想定人気上位（◎以外）: q降順
    q_order = sorted(range(len(recs)), key=lambda i: -q[i])
    h_idx = idx_by_num.get(marks.get('◎', {}).get('馬番'))
    pops = [i for i in q_order if i != h_idx][:2]
    # V=妙味馬: モデル上位6頭のうちp/q乖離が最大の馬（◎以外）
    p_order = sorted(range(len(recs)), key=lambda i: -p[i])[:6]
    v_cands = [i for i in p_order if i != h_idx]
    v_idx = max(v_cands, key=lambda i: p[i]/max(q[i], 1e-6)) if v_cands else None
    roles = {
        'H': h_idx,
        'O': idx_by_num.get(marks.get('○', {}).get('馬番')),
        'S': idx_by_num.get(marks.get('▲', {}).get('馬番')),
        'D1': idx_by_num.get(deltas[0]['馬番']) if deltas else None,
        'D2': idx_by_num.get(deltas[1]['馬番']) if len(deltas) > 1 else None,
        'D3': idx_by_num.get(deltas[2]['馬番']) if len(deltas) > 2 else None,
        'D4': idx_by_num.get(deltas[3]['馬番']) if len(deltas) > 3 else None,
        'D5': idx_by_num.get(deltas[4]['馬番']) if len(deltas) > 4 else None,
        'P1': pops[0] if pops else None,
        'P2': pops[1] if len(pops) > 1 else None,
        'V': v_idx,
        # v5.6: 'A'=🔥穴印（△頭数可変ルール対応でD3-D5も追加・2026-08-19）
        'A': next((idx_by_num.get(r['馬番']) for r in recs
                   if str(r.get('AI印', '')) in ('穴', '🔥穴', '🔥')), None),
    }
    # ◎の実オッズ（単勝系ゲート用・v5.3）
    h_odds = None
    if odds_override and h_idx is not None:
        h_odds = odds_override.get(str(recs[h_idx]['馬番']))
        if h_odds is not None:
            h_odds = float(h_odds)

    ranking = []
    for name, desc, legs in PATTERNS:
        code = name.split(' ')[0]
        if young and code in CONCENTRATED_PATTERNS:
            continue   # 若馬戦は1点集中型・馬単流しを禁止（v5.2/v5.3）
        if code in V_PATTERNS and not odds_override:
            continue   # V系は実オッズがある時のみ（v5.2）
        if code in TANSHO_PATTERNS and h_odds is not None and \
           not (TANSHO_ODDS_MIN <= h_odds <= TANSHO_ODDS_MAX):
            continue   # 単勝系は◎実オッズ3〜10倍の妙味帯のみ（v5.3・PDCA100実測）
        res = evaluate_pattern(legs, roles, p, q, budget)
        if res and code in NON_HON_AXIS_PATTERNS and roles.get('H') is not None:
            # v5.6 ◎バイアス中和: ◎弱体化世界との平均で非◎軸パターンを公平に評価
            h_i = roles['H']
            p_cons = list(p)
            p_cons[h_i] *= 0.90
            s_cons = sum(p_cons)
            p_cons = [x / s_cons for x in p_cons]
            res2 = evaluate_pattern(legs, roles, p_cons, q, budget)
            if res2:
                for k in ('E_rate', 'P_target', 'P_hit', 'P_gami'):
                    res[k] = (res[k] + res2[k]) / 2
                res['gami_ratio'] = res['P_gami'] / res['P_hit'] if res['P_hit'] > 0 else 1.0
        if res:
            ranking.append((name, desc, res))
    # 選択基準:
    #   ① E[回収率]>=115% を満たすこと
    #   ② ガミ率（的中時に投資額を下回る割合）<=35% を優先
    #      →「当たったのに微プラス/マイナス」で収支が沈む構造を排除
    #   ③ その中でP(回収率300%+)最大 → E[回収率]最大
    ranking.sort(key=lambda x: (
        -(x[2]['E_rate'] >= EV_MIN),
        -(x[2]['gami_ratio'] <= 0.35),
        -x[2]['P_target'],
        -x[2]['E_rate'],
    ))
    if not ranking or ranking[0][2]['E_rate'] < EV_MIN:
        return None, None, None, ranking, p, q
    best = ranking[0]
    return best[0], best[1], best[2], ranking, p, q


# ============================================================
# 出力
# ============================================================
def set_font(run, size=10, bold=False, color=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--conf-min', type=int, default=7)
    ap.add_argument('--odds-file', help='実オッズJSONで大衆確率を上書き（当日再実行用）')
    ap.add_argument('--analyze', action='store_true',
                    help='ライブラリサイズ分析（パターン使用分布・限界効用カーブ）を出力')
    ap.add_argument('--dates', nargs='+', metavar='YYYYMMDD',
                    help='対象日を絞る（例: --dates 20260802）')
    args = ap.parse_args()

    with open(args.json, encoding='utf-8') as f:
        data = json.load(f)
    races = defaultdict(list)
    for r in data['records']:
        races[(r['date'], r['競馬場'], r['R'])].append(r)
    for k in races:
        races[k].sort(key=lambda x: x['AI予測順位'])

    real_odds = {}
    if args.odds_file:
        with open(args.odds_file, encoding='utf-8') as f:
            real_odds = json.load(f)

    conf_map = {k: calc_confidence(v) for k, v in races.items()}
    keys = sorted([k for k in races if conf_map[k][0] >= args.conf_min
                   and (not args.dates or k[0] in args.dates)],
                  key=lambda k: (k[0], -conf_map[k][0], k[1], k[2]))

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Cm(1.8); sec.bottom_margin = Cm(1.8)
        sec.left_margin = Cm(2.0); sec.right_margin = Cm(2.0)

    def h1(text, color=(15,71,97)):
        p_ = doc.add_heading(text, level=1)
        for r in p_.runs:
            set_font(r, 14); r.font.color.rgb = RGBColor(*color)

    def h2(text, color=(40,40,40)):
        p_ = doc.add_heading(text, level=2)
        for r in p_.runs:
            set_font(r, 11.5); r.font.color.rgb = RGBColor(*color)

    def box(lines, size=9.5):
        p_ = doc.add_paragraph()
        p_.paragraph_format.left_indent = Cm(0.5)
        p_.paragraph_format.space_before = Pt(4)
        p_.paragraph_format.space_after = Pt(8)
        r = p_.add_run("\n".join(lines))
        set_font(r, size)

    dates = sorted(set(k[0] for k in keys))
    t = doc.add_heading(f"週末買い目 v5 EVアダプティブ {dates[0][4:6]}/{dates[0][6:]}-{dates[-1][4:6]}/{dates[-1][6:]}", level=0)
    for r in t.runs: set_font(r, 15)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph("14パターンライブラリ×全レース機械評価 → E[回収率]115%以上の中からP(回収率300%+)最大を自動選択")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in sub.runs: set_font(r, 9.5)

    h1("■ v5の仕組み")
    box([
        "1. ML能力%からモデル勝率p、近走着順×騎手×MLから大衆勝率qを推定",
        "2. 想定オッズ = 払戻率/q（Harville式で馬連・馬単・ワイド・3連複・3連単に展開）",
        "3. 14種の買い目パターン全てについて、着順シナリオ全列挙で E[回収率]・P(回収率300%+)・的中率・ガミ率を計算",
        "4. E[回収率]115%以上×ガミ率35%以下のパターンからP(300%+)最大を選択。基準未満は見送り",
        "   ※ガミ率=「的中したのに投資額を下回る」確率の割合。当たって微プラス→トータルマイナスの構造を排除",
        "5. 予算は自信度連動: 10=15,000円 / 9=12,000円 / 8=8,000円 / 7=5,000円",
        "※前日時点はオッズ推定値。当日 --odds-file で実オッズを与えて再実行すると精密化",
    ])

    weekday = {'20260801': '土', '20260802': '日'}
    total_all = 0
    pat_count = defaultdict(int)
    summary_rows = []
    rankings_all = {}
    cur_date = None

    for k in keys:
        recs = races[k]
        top = recs[0]
        conf, _ = conf_map[k]
        budget = BUDGET_BY_CONF[conf]
        odds_key = f"{k[0]}_{k[1]}_{k[2]}"
        name, desc, res, ranking, p, q = choose_pattern(recs, budget, real_odds.get(odds_key))
        rankings_all[k] = ranking

        if k[0] != cur_date:
            cur_date = k[0]
            h1(f"■ {cur_date[:4]}/{cur_date[4:6]}/{cur_date[6:]}（{weekday.get(cur_date,'')}）", color=(150,30,30))

        grade = f"[{top['グレード']}]" if top['グレード'] else ""
        marks = [r for r in recs if r['AI印']]

        if name is None:
            pat_count['見送り'] += 1
            h2(f"{k[1]}{k[2]}R {top['レース名']}{grade} {top['距離']}　自信度{conf}/10　→ 見送り",
               color=(120,120,120))
            best_line = ""
            if ranking:
                b = ranking[0]
                best_line = f"最良パターン{b[0]}でもE[回収率]{b[2]['E_rate']*100:.0f}%（基準115%未満）"
            box(["印: " + "　".join(f"{r['AI印']}{r['馬番']}{r['馬名']}" for r in marks),
                 "", f"・◎の想定オッズが低く期待値が確保できないため投資0円。{best_line}",
                 "・当日オッズが想定より付くようなら再判定"])
            summary_rows.append((k, conf, '見送り', 0, 0, 0))
            continue

        pat_count[name.split(' ')[0]] += 1
        total_all += res['total']
        h2(f"{k[1]}{k[2]}R {top['レース名']}{grade} {top['距離']}　自信度{conf}/10　→ {name}",
           color=(180,80,0))

        h_rec = next(r for r in recs if r['AI印'] == '◎')
        hi = recs.index(h_rec)
        lines = [
            "印: " + "　".join(f"{r['AI印']}{r['馬番']}{r['馬名']}" for r in marks),
            "",
            f"◎{h_rec['馬名']}: モデル勝率{p[hi]*100:.0f}% / 大衆想定{q[hi]*100:.0f}%"
            f"（想定単勝{0.8/max(q[hi],1e-6):.1f}倍） → {'過小評価=妙味' if p[hi] > q[hi]*1.2 else '人気どおり' if p[hi] > q[hi]*0.8 else '過剰人気注意'}",
            f"選択理由: {desc}",
            f"評価: E[回収率]{res['E_rate']*100:.0f}% / P(300%達成){res['P_target']*100:.0f}% / 的中率{res['P_hit']*100:.0f}% / ガミ率{res['gami_ratio']*100:.0f}%",
            "",
            f"予算{budget:,}円（自信度{conf}連動） 実配分{res['total']:,}円",
        ]
        for btype, idxs, amount, odds in res['bets']:
            nums = "-".join(str(recs[i]['馬番']) for i in idxs) if btype not in ('馬単','3連単') \
                   else "→".join(str(recs[i]['馬番']) for i in idxs)
            names = "・".join(recs[i]['馬名'] for i in idxs)
            lines.append(f"　{btype}  {nums}（{names}）  {amount:,}円　想定{odds:.1f}倍")
        lines.append("")
        lines.append("次点パターン比較:")
        for nm, _, rr in ranking[1:4]:
            lines.append(f"　{nm}: E[回収率]{rr['E_rate']*100:.0f}% / P(300%){rr['P_target']*100:.0f}% / 的中率{rr['P_hit']*100:.0f}% / ガミ率{rr['gami_ratio']*100:.0f}%")
        box(lines)
        summary_rows.append((k, conf, name, res['total'], res['E_rate'], res['P_target']))

    # ── サマリー ──
    h1("■ 週末トータルサマリー")
    lines = [f"対象: 自信度{args.conf_min}以上 {len(keys)}レース / 総投資{total_all:,}円",
             f"パターン内訳: " + " / ".join(f"{k_}×{v}" for k_, v in sorted(pat_count.items())), "",
             "レース別:"]
    for k, conf, name, amt, er, pt in summary_rows:
        if amt:
            lines.append(f"　{k[0][4:6]}/{k[0][6:]} {k[1]}{k[2]:>2}R 自信度{conf} {name:<14} {amt:>7,}円 E{er*100:.0f}% P300={pt*100:.0f}%")
        else:
            lines.append(f"　{k[0][4:6]}/{k[0][6:]} {k[1]}{k[2]:>2}R 自信度{conf} 見送り")
    box(lines, 9)

    suffix = f"_{'_'.join(args.dates)}" if args.dates else ""
    out = Path(args.json).parent / f"週末買い目_v5EVアダプティブ{suffix}.docx"
    doc.save(str(out))

    print(f"\n{'='*90}")
    print(f"v5買い目構築完了: {len(keys)}レース / 総投資{total_all:,}円")
    for k, conf, name, amt, er, pt in summary_rows:
        top = races[k][0]
        label = name if amt else '見送り'
        extra = f" E{er*100:>4.0f}% P300={pt*100:>3.0f}%" if amt else ""
        print(f"  {k[0][4:6]}/{k[0][6:]} {k[1]}{k[2]:>2}R {top['レース名'][:14]:<14} 自信度{conf} {label:<16} {amt:>7,}円{extra}")
    print(f"\n[保存] {out}")

    # ── ライブラリサイズ分析 ──────────────────────────────
    if args.analyze:
        print(f"\n{'='*90}")
        print(f"パターンライブラリ分析（全{len(PATTERNS)}種）")
        print(f"{'='*90}")

        sel_count = defaultdict(int)
        top3_count = defaultdict(int)
        for k, ranking in rankings_all.items():
            if ranking and ranking[0][2]['E_rate'] >= EV_MIN:
                sel_count[ranking[0][0]] += 1
            for nm, _, rr in ranking[:3]:
                top3_count[nm] += 1

        print("\n[1] パターン別 採用回数 / TOP3入り回数（20レース中）:")
        for name, _, _ in PATTERNS:
            s, t3 = sel_count.get(name, 0), top3_count.get(name, 0)
            if s or t3:
                bar = '█'*s + '▒'*(t3-s)
                print(f"  {name:<18} 採用{s:>2} / TOP3 {t3:>2}  {bar}")
        unused = [name for name, _, _ in PATTERNS if top3_count.get(name, 0) == 0]
        print(f"\n  TOP3に一度も入らなかったパターン: {len(unused)}種")
        print(f"    {', '.join(n.split(' ')[0] for n in unused)}")

        # 限界効用カーブ: ライブラリ先頭N種だけ使えた場合の平均P(300%)
        print("\n[2] ライブラリサイズ別 限界効用（先頭N種のみ使用時）:")
        order = [name for name, _, _ in PATTERNS]
        print(f"  {'N':>4} {'平均P(300%)':>12} {'参加レース':>10} {'平均E[回収]':>12}")
        prev_p300 = None
        for n_lib in [6, 12, 18, 24, 30, 36, 42, len(PATTERNS)]:
            allowed = set(order[:n_lib])
            p300_sum, e_sum, joined = 0.0, 0.0, 0
            for k, ranking in rankings_all.items():
                subset = [x for x in ranking if x[0] in allowed]
                subset.sort(key=lambda x: (
                    -(x[2]['E_rate'] >= EV_MIN),
                    -(x[2]['gami_ratio'] <= 0.35),
                    -x[2]['P_target'],
                    -x[2]['E_rate'],
                ))
                if subset and subset[0][2]['E_rate'] >= EV_MIN:
                    p300_sum += subset[0][2]['P_target']
                    e_sum += subset[0][2]['E_rate']
                    joined += 1
            avg_p300 = p300_sum / len(rankings_all) * 100
            avg_e = (e_sum / joined * 100) if joined else 0
            delta = f" (+{avg_p300-prev_p300:.1f})" if prev_p300 is not None else ""
            print(f"  {n_lib:>4} {avg_p300:>11.1f}%{delta:<8} {joined:>8}R {avg_e:>11.0f}%")
            prev_p300 = avg_p300

        active = [n for n in order if top3_count.get(n, 0) > 0]
        print(f"\n[3] 推奨: アクティブセット{len(active)}種（TOP3入り実績あり）を主力に、")
        print(f"    残り{len(PATTERNS)-len(active)}種はレース構造が変わった時の予備として保持。")


if __name__ == '__main__':
    main()
