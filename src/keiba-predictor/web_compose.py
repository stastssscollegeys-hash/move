# -*- coding: utf-8 -*-
"""web_compose.py — 1レースの買い目を「標準の構成」で組み、的中の見込み・場面ごとの受け皿・実オッズの期待値を計算して出す（2026-11-14 新設）

土台の検証（docs/keiba_weekend_review_20261114_sat.md §8〜10・SKILL §2）:
  bet_type_by_race_test.py（券種）／bet_portfolio_study.py（部品と場面）／bet_form_study.py（軸流し・BOX・フォーメーション・マルチ）
決め方（検証で残ったものだけ）:
  ・単勝◎ ＝ ◎1着の受け皿（払戻率80%・一番早く落ち着く）
  ・馬連 ◎-○・◎-▲（＋◎-穴）＝ ◎2着までの受け皿。総流し・BOX・ヒモ足しは回収率が下がるので広げない
  ・3連複 フォーメーション ◎-○▲-印全部 を 1点100円＝ ◎3着までを高配当で受ける（1点に厚くするのと回収率は同じで、当たる頻度が約3.6倍・落ち着くのが約4倍早い）。
     本線の ◎-○-▲ だけ上乗せ。1頭軸の総流し・BOX・ヒモ足し・3連単マルチは使わない
  ・ワイド ◎-○・◎-▲（＋◎-穴）＝ ◎3着のときの押さえ。△（割安でない人気馬）とのワイド・馬連は回収率が低いので買わない（△は3連複の3列目だけ）
  ・（2026-11-26 から）買い目は型 K1〜K6 から、レースの区分ごとに選ぶ。馬単・3連単・複勝も型の中で使う
  ・◎抜きの保険（馬連○-▲）は --hoken を付けたときだけ1点・予算の1割
印: web_picks.marks_of ＋ 穴（6番人気以下・勝つ確率2%以上・印なしで最も割安な1頭。--ana 馬番 で指定／--keep 馬番… で△として残す馬を足す）
  python web_compose.py --date 20261115 --race 京都11 [--budget 10000] [--keep 6] [--ana 10] [--hoken] [--no-odds]
強さ（2026-11-18〜）: ◎の割安さ 1.15未満＝見送り（予算の3割の少額で試算だけ）／1.15〜1.30＝通常／1.30以上＝単勝を本線（45%）。--no-tier で無効
出力: 買い目（100円単位）、◎が1着／2着／3着／着外のとき何%を拾えるか、どれかが当たる確率、券ごとの的中確率と（オッズが取れれば）期待値、当たっても損になる割合。
"""
import argparse
import itertools
import json
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import web_frontier as F
import web_live as WL
import web_picks as WP

SHARE = {"単勝◎": .25, "馬連◎-○": .20, "馬連◎-▲": .15, "馬連◎-穴": .05, "ワイド◎-○": .10, "ワイド◎-▲": .08, "ワイド◎-穴": .05, "3連複": .12}
# 2026-11-18 採用（ユーザー承認・docs/keiba_2026_summary_20261118.md §7）: ◎の割安さ（モデル÷市場）で買う強さを変える
#   S1 割安さ1.15未満 ＝ 見送り（公開しない。出すなら予算の3割の少額）… 10年25,440Rで、この帯は何を買っても回収率83〜90%
#   S2 割安さ1.30以上 ＝ 単勝を本線（予算の45%）… 単勝108%（前半111/後半104）。割安なレースはワイドより単勝
#   S5 △（人気で印なし）は押さえだけ ＝ もともと3連複の3列目だけ（単勝71%・◎とのワイド84.5%）
TIER_LO, TIER_HI, LOW_BUDGET = 1.15, 1.30, .30
# 2026-11-26: 割安さ1.30以上の帯は ワイド◎-○ も 112.3%（前半114.0／後半109.8・1,719R・race_select_test.py）→ ワイド◎-○ を 7%→17% に厚く（馬連◎-▲・ワイド◎-▲・3連複から移す）
#   同日: 全券種を帯ごとに測ると（bet_type_by_band_test.py）、1.30以上の帯は「◎と○の1点」がそろって100%超
#   （馬連◎-○ 123.2%〔前132.6／後110.1〕・ワイド◎-○ 112.4%・単勝 110.6%）。流し・3連複・BOXは100%未満 → ◎-○ に寄せる（3連複は100円ずつの最小限）
SHARE_TAN = {"単勝◎": .40, "馬連◎-○": .22, "馬連◎-▲": .05, "馬連◎-穴": .03, "ワイド◎-○": .17, "ワイド◎-▲": .03, "ワイド◎-穴": .02, "3連複": .08}
assert abs(sum(SHARE_TAN.values()) - 1) < 1e-9


# ── 2026-11-26 買い目の型（ユーザー指示「毎回同じ買い目・形にする必要はない。期待値・印・独自指数で、どの型かを判断して買う」）──
#   型＝券種ごとの配分。どの型にするかは、レースの条件14個（DIMS）で枝分かれさせた区分ごとに、10年の成績（web_pattern_test.py）で
#   「回収率と当たる頻度のつり合い」がいちばん良かった型を引く（db/web_pattern_table.json）。表が無いとき・--pattern で指定したときはその型。
#   3連複＝◎-○▲-印の全部に均等／3連単＝◎→○▲→印の全部に100円ずつ。馬単・3連単・複勝は 2026-11-26 から使えるようにした（それまでは単勝・馬連・ワイド・3連複だけ）
PATTERNS = {
    # ── ◎が主役 ──
    "K1": ("本線集中型（◎と○の1点に厚く）", {"単勝◎": .40, "馬連◎-○": .22, "馬連◎-▲": .05, "馬連◎-穴": .03, "ワイド◎-○": .17, "ワイド◎-▲": .03, "ワイド◎-穴": .02, "3連複": .08}),
    "K2": ("高配当型（◎の1着に寄せる）", {"単勝◎": .33, "馬単◎→○": .10, "馬連◎-○": .20, "馬連◎-▲": .05, "馬連◎-穴": .03, "ワイド◎-○": .15, "ワイド◎-穴": .02, "3連単": .07, "3連複": .05}),
    "K3": ("標準型（単勝・馬連・ワイド・3連複）", {"単勝◎": .25, "馬連◎-○": .20, "馬連◎-▲": .15, "馬連◎-穴": .05, "ワイド◎-○": .10, "ワイド◎-▲": .08, "ワイド◎-穴": .05, "3連複": .12}),
    "K4": ("的中重視型（複勝とワイド）", {"複勝◎": .25, "ワイド◎-○": .25, "ワイド◎-▲": .18, "馬連◎-○": .15, "馬連◎-▲": .07, "ワイド◎-穴": .04, "3連複": .06}),
    "K5": ("馬連・馬単型（◎と○▲の連対）", {"馬連◎-○": .35, "馬連◎-▲": .20, "馬単◎→○": .15, "単勝◎": .15, "ワイド◎-○": .10, "3連複": .05}),
    "K6": ("3連複型（◎から印へ広く）", {"3連複": .45, "ワイド◎-○": .20, "ワイド◎-▲": .15, "馬連◎-○": .20}),
    # ── ○（対抗）も主役 ──
    "K7": ("二頭軸型（◎と○の両方を頭に）", {"単勝◎": .22, "単勝○": .15, "馬連◎-○": .25, "ワイド◎-○": .18, "馬単◎→○": .05, "馬単○→◎": .05, "3連複2軸": .10}),
    "K8": ("対抗逆転型（○が勝つ場面も取る）", {"単勝○": .25, "単勝◎": .15, "馬連◎-○": .20, "馬単○→◎": .10, "ワイド◎-○": .12, "馬連○-▲": .08, "ワイド○-▲": .05, "3連複": .05}),
    "K9": ("複勝2頭型（◎と○の複勝＋ワイド）", {"複勝◎": .28, "複勝○": .22, "ワイド◎-○": .30, "馬連◎-○": .15, "3連複1点": .05}),
    # ── ▲（単穴）が主役 ──
    "K10": ("単穴一発型（▲の1着も取る）", {"単勝◎": .25, "単勝▲": .15, "馬連◎-▲": .18, "馬連◎-○": .15, "ワイド◎-▲": .12, "ワイド○-▲": .05, "馬単▲→◎": .05, "3連複": .05}),
    "K11": ("印3頭BOX型（◎○▲のどれが来ても）", {"馬連BOX": .40, "ワイドBOX": .40, "3連複1点": .10, "単勝◎": .10}),
    # ── △（紐）を使う ──
    "K12": ("紐流し型（◎から人気の△へも流す）", {"単勝◎": .20, "馬連◎-○": .18, "馬連◎-▲": .12, "馬連◎-△": .15, "ワイド◎-○": .10, "ワイド◎-△": .13, "3連複": .12}),
    "K13": ("◎抜き保険型（◎が飛んでも○▲で受ける）", {"単勝◎": .22, "馬連◎-○": .18, "馬連◎-▲": .12, "ワイド◎-○": .10, "ワイド◎-▲": .08, "馬連○-▲": .12, "ワイド○-▲": .12, "3連複": .06}),
    # ── 穴が主役 ──
    "K14": ("穴絡み型（穴の複勝と、◎○からのワイド）", {"複勝穴": .15, "単勝穴": .05, "ワイド◎-穴": .15, "ワイド○-穴": .08, "馬連◎-穴": .07, "単勝◎": .20, "馬連◎-○": .15, "ワイド◎-○": .10, "3連複穴": .05}),
    "K15": ("穴一発型（穴の単複を厚く）", {"単勝穴": .15, "複勝穴": .25, "ワイド◎-穴": .20, "ワイド○-穴": .10, "ワイド▲-穴": .05, "馬連◎-穴": .10, "馬連○-穴": .05, "3連複穴": .10}),
    "K16": ("本線＋穴の3連複型", {"単勝◎": .25, "馬連◎-○": .20, "ワイド◎-○": .15, "ワイド◎-穴": .10, "3連複穴": .20, "3連複": .10}),
    # ── 2026-11-26 夜に追加（ユーザー指示「もっと型を増やして」）。点数を絞る型・1つの券種に寄せる型・軸を替える型 ──
    "K17": ("単勝一点型（◎の単勝だけ）", {"単勝◎": 1.0}),
    "K18": ("単複型（◎の単勝と複勝）", {"単勝◎": .40, "複勝◎": .60}),
    "K19": ("複勝一点型（◎の複勝だけ）", {"複勝◎": 1.0}),
    "K20": ("馬連一点型（馬連◎-○とワイド◎-○）", {"馬連◎-○": .60, "ワイド◎-○": .40}),
    "K21": ("ワイド一点型（ワイド◎-○を厚く）", {"ワイド◎-○": .80, "単勝◎": .20}),
    "K22": ("単勝＋馬連2点型", {"単勝◎": .40, "馬連◎-○": .35, "馬連◎-▲": .25}),
    "K23": ("馬単表裏型（◎と○の順番も取る）", {"馬単◎→○": .35, "馬単○→◎": .25, "馬連◎-○": .25, "ワイド◎-○": .15}),
    "K24": ("3連単型（◎1着固定を厚く）", {"単勝◎": .30, "馬単◎→○": .15, "馬単◎→▲": .10, "3連単": .30, "馬連◎-○": .15}),
    "K25": ("2頭軸3連複型（◎と○から印へ）", {"3連複2軸": .50, "馬連◎-○": .25, "ワイド◎-○": .25}),
    "K26": ("対抗軸型（○から流す）", {"単勝○": .25, "馬連○-▲": .15, "馬連◎-○": .25, "ワイド○-▲": .12, "ワイド◎-○": .15, "ワイド○-穴": .08}),
    "K27": ("単穴軸型（▲から流す）", {"単勝▲": .25, "複勝▲": .15, "馬連◎-▲": .22, "馬連○-▲": .12, "ワイド◎-▲": .16, "ワイド○-▲": .10}),
    "K28": ("単勝3頭型（◎○▲の単勝）", {"単勝◎": .45, "単勝○": .30, "単勝▲": .25}),
    "K29": ("複勝3頭型（◎○▲の複勝）", {"複勝◎": .40, "複勝○": .32, "複勝▲": .28}),
    "K30": ("ワイド3点型（◎○▲のワイドBOX）", {"ワイドBOX": .85, "3連複1点": .15}),
    "K31": ("馬連3点型（◎○▲の馬連BOX）", {"馬連BOX": .85, "3連複1点": .15}),
    "K32": ("穴軸ワイド型（穴から印へワイド）", {"複勝穴": .25, "ワイド◎-穴": .30, "ワイド○-穴": .20, "ワイド▲-穴": .15, "単勝穴": .10}),
    "K33": ("本線＋紐の3連複型（△を3列目に厚く）", {"単勝◎": .25, "馬連◎-○": .20, "ワイド◎-○": .15, "ワイド◎-△": .10, "3連複": .30}),
    "K34": ("単勝＋ワイド2点型", {"単勝◎": .40, "ワイド◎-○": .35, "ワイド◎-▲": .25}),
}
TABLE = WL.L.DB / "web_pattern_table.json"
ROLE = {"単勝": "1着", "複勝": "3着まで", "馬連": "2着まで", "馬単": "1着・2着の順", "ワイド": "3着まで", "3連複": "3着まで（高配当）", "3連単": "◎1着（高配当）"}
O_VALUE, ANA_VALUE = 1.20, 1.30      # ○も割安＝○の割安さ1.20以上／割安な穴＝6番人気以下・勝つ確率2%以上・割安さ1.30以上（S3 と同じ線）


DIMS = ["帯", "○", "穴", "◎の人気", "◎の勝つ確率", "◎と○の差", "混戦度", "頭数", "▲", "△の数", "芝ダ", "距離", "クラス", "馬場",
        "◎の単勝オッズ", "○の人気", "▲の人気", "◎は確率1位か", "穴の候補", "競馬場", "上位3頭の確率", "◎の割安さの細かい帯"]
MAIN4 = ("東京", "中山", "京都", "阪神")


def feats(ratio, pop, n, o_ratio=0, ana_ratio=0, p_hon=0, p_o=0, fav_q=0, t_ratio=0, n_delta=0, dist="", cond="", baba="",
          odds_hon=0, pop_o=0, pop_t=0, hon_is_p=False, has_ana=False, venue="", top3_p=0):
    """レースの条件（発走前にわかるものだけ）→ {条件の名前: 区分}。型の表（木）はこの条件で枝分かれする。web_pattern_test.py と同じ関数を使う。
    2026-11-26 夜に 14個→22個（◎の単勝オッズ・○と▲の人気・◎は確率1位か・穴の候補がいるか・競馬場・上位3頭の確率の合計・割安さの細かい帯）"""
    import re
    m = re.search(r"(\d{3,4})", dist or ""); d = int(m.group(1)) if m else 0
    c = cond or ""
    return {
        "帯": "割安さ1.30以上" if ratio >= TIER_HI else "割安さ1.15〜1.30" if ratio >= TIER_LO else "割安さ1.15未満",
        "○": "○も割安" if (o_ratio or 0) >= O_VALUE else "○は割安でない",
        "穴": "割安な穴あり" if (ana_ratio or 0) >= ANA_VALUE else "割安な穴なし",
        "◎の人気": "◎1番人気" if pop == 1 else "◎2〜3番人気" if pop <= 3 else "◎4番人気以下",
        "◎の勝つ確率": "◎の確率25%以上" if p_hon >= .25 else "◎の確率15〜25%" if p_hon >= .15 else "◎の確率15%未満",
        "◎と○の差": "○が◎に接近（確率が8割以上）" if p_hon and p_o >= .8 * p_hon else "○は◎から離れている",
        "混戦度": "一強（1番人気が30%以上）" if fav_q >= .30 else "ふつう（1番人気が20〜30%）" if fav_q >= .20 else "混戦（1番人気が20%未満）",
        "頭数": "〜11頭" if n <= 11 else "12〜15頭" if n <= 15 else "16頭〜",
        "▲": "▲も割安" if (t_ratio or 0) >= 1.15 else "▲は割安でない",
        "△の数": "△なし" if n_delta == 0 else "△1頭" if n_delta == 1 else "△2頭以上",
        "芝ダ": "芝" if (dist or "").startswith("芝") else "ダート" if (dist or "").startswith("ダ") else "障害ほか",
        "距離": "〜1400m" if d and d <= 1400 else "1500〜1800m" if d and d <= 1800 else "1900m〜",
        "クラス": "新馬・未勝利" if ("新馬" in c or "未勝利" in c) else "1勝・2勝クラス" if ("1勝" in c or "2勝" in c) else "3勝・オープン・重賞",
        "馬場": "良" if (baba or "良") == "良" else "道悪",
        "◎の単勝オッズ": "◎の単勝3倍未満" if odds_hon and odds_hon < 3 else "◎の単勝3〜6倍" if odds_hon < 6 else "◎の単勝6〜10倍" if odds_hon < 10 else "◎の単勝10倍以上",
        "○の人気": "○1〜3番人気" if pop_o and pop_o <= 3 else "○4〜6番人気" if pop_o <= 6 else "○7番人気以下",
        "▲の人気": "▲1〜3番人気" if pop_t and pop_t <= 3 else "▲4〜6番人気" if pop_t <= 6 else "▲7番人気以下",
        "◎は確率1位か": "◎は確率1位" if hon_is_p else "◎は確率1位ではない",
        "穴の候補": "穴の候補あり" if has_ana else "穴の候補なし",
        "競馬場": "東京・中山・京都・阪神" if venue in MAIN4 else "ローカル",
        "上位3頭の確率": "上位3頭で60%以上（堅い）" if top3_p >= .60 else "上位3頭で45〜60%" if top3_p >= .45 else "上位3頭で45%未満（荒れ）",
        "◎の割安さの細かい帯": "1.50以上" if ratio >= 1.5 else "1.30〜1.50" if ratio >= 1.3 else "1.22〜1.30" if ratio >= 1.22 else "1.15〜1.22" if ratio >= 1.15 else "1.08〜1.15" if ratio >= 1.08 else "1.08未満",
    }


def pick_pattern(f):
    """条件 f（feats の結果）で、型の表（木）をたどる。→ (記号, 理由の文)。表が無ければ 帯で決める（1.30以上=K1・それ以外=K3）"""
    try:
        node = json.loads(TABLE.read_text(encoding="utf-8"))["tree"]
    except Exception:
        return ("K1" if f["帯"] == "割安さ1.30以上" else "K3"), "型の表が無いので、帯で決めた"
    path = []
    while node.get("dim") and f.get(node["dim"]) in node.get("children", {}):
        path.append(f[node["dim"]]); node = node["children"][f[node["dim"]]]
    e = node["leaf"]
    if e["pattern"] not in PATTERNS:
        return "K3", "表の型が見つからないので標準型"
    alt = "".join(f"／次点 {x['pattern']}（当たる{x['hit']:.0f}%・プラス{x['plus']:.0f}%・回収{x['roi']:.0f}%）" for x in e.get("next", [])[:2])
    return e["pattern"], f"{'・'.join(path) or '全レース'} の10年の成績（{e['n']:,}レース）: 当たる{e['hit']:.0f}%・プラス{e['plus']:.0f}%・回収{e['roi']:.0f}%（前半{e['front']:.0f}／後半{e['back']:.0f}）{alt}"


def tickets_for(SH, H, o, t, D, ana, budget):
    """型（配分）から買い目を並べる → [[券種, 組, 金額, 役割], …]。金額は100円単位。合計は budget に合わせる（余りは1つ目の点へ）
    配分のキー: 「単勝◎」「複勝穴」／「馬連◎-○」「ワイド○-穴」「馬連◎-△」（△は紐の全部へ均等）／「馬単○→◎」／
                「馬連BOX」「ワイドBOX」（◎○▲の3点へ均等）／「3連複」（◎-○▲-印の全部）「3連複2軸」（◎-○-印の全部）「3連複穴」（◎-穴-印の全部）「3連複1点」（◎-○-▲）／「3連単」（◎→○▲→印・100円ずつ）
    馬がいない印（穴がいない・▲がいない等）のキーは飛ばし、その分は1つ目の点に寄る"""
    core = [x for x in (o, t) if x is not None]; D = [d for d in D if d is not None]
    aite = [x for x in core + D + ([ana] if ana else []) if x is not None]
    who = {"◎": [H], "○": [o] if o else [], "▲": [t] if t else [], "穴": [ana] if ana else [], "△": D}
    T = []; seen = {}
    def put(typ, comb, yen, role=None):
        if yen < 100 or any(c is None for c in comb) or len(set(comb)) < len(comb):
            return
        cb = tuple(comb) if typ in ("単勝", "複勝", "馬単", "3連単") else tuple(sorted(comb))
        if (typ, cb) in seen:                                  # 同じ点が2つのキーから来たら足す
            seen[(typ, cb)][2] += r100(yen); return
        x = [typ, cb, r100(yen), role or ROLE[typ]]; T.append(x); seen[(typ, cb)] = x
    def spread(typ, combs, total, role=None):
        combs = list(dict.fromkeys(combs))
        if combs:
            each = max(100, int(total / len(combs) // 100) * 100)
            for c in combs:
                put(typ, c, each, role)
    for k, sh in SH.items():
        yen = budget * sh
        if k == "3連複":
            spread("3連複", [tuple(sorted((H, x, y))) for x in core for y in aite if y != x], yen)
        elif k == "3連複2軸":
            spread("3連複", [tuple(sorted((H, o, y))) for y in aite if o and y != o], yen)
        elif k == "3連複穴":
            spread("3連複", [tuple(sorted((H, ana, y))) for y in core + D if ana], yen, "穴が3着まで（高配当）")
        elif k == "3連複1点":
            if len(core) == 2:
                put("3連複", (H, o, t), yen)
        elif k == "3連単":
            for x in core:
                for y in aite:
                    if y != x:
                        put("3連単", (H, x, y), 100)
        elif k in ("馬連BOX", "ワイドBOX"):
            m3 = [H] + core
            spread(k[:-3], [tuple(sorted((x, y))) for i, x in enumerate(m3) for y in m3[i + 1:]], yen, "印の2頭が来れば")
        elif k[:2] in ("単勝", "複勝"):
            for u in who[k[2]]:
                put(k[:2], (u,), yen, f"{k[2]}が{ROLE[k[:2]]}")
        elif k.startswith("馬単"):
            x1, x2 = k[2], k[4]
            for u in who[x1]:
                for v in who[x2]:
                    put("馬単", (u, v), yen, f"{x1}1着・{x2}2着")
        else:
            typ = "馬連" if k.startswith("馬連") else "ワイド"; x1, x2 = k[len(typ)], k[len(typ) + 2]
            pairs = [(u, v) for u in who[x1] for v in who[x2]]
            role = ("穴の押さえ" if "穴" in k and "◎" in k else f"{x1}と{x2}が" + ("2着まで" if typ == "馬連" else "3着まで"))
            spread(typ, [tuple(sorted(c)) for c in pairs], yen, role)
    rest = budget - sum(x[2] for x in T)
    if T:
        T[0][2] = max(100, T[0][2] + rest)
    return T

def tier_of(ratio):
    return "見送り" if ratio < TIER_LO else "単勝本線" if ratio >= TIER_HI else "通常"


def r100(x):
    return int(round(x / 100.0)) * 100


def compose(race, budget=10000, keep=(), ana=None, hoken=False, use_odds=True, tier=True, pattern="auto"):
    hs, marks = WP.marks_of(race)
    by = {h["uma"]: h for h in hs}
    M = {m: [h["uma"] for mm, h in marks if mm == m] for m in "◎○▲△"}
    H = M["◎"][0]; o = (M["○"] or [None])[0]; t = (M["▲"] or [None])[0]
    D = M["△"] + [u for u in keep if u not in [H, o, t] + M["△"]]
    used = {H, o, t} | set(D)
    ratio = WP.value_ratio(race); tr = tier_of(ratio) if tier else "通常"   # 2026-11-26: 強さは「レースの割安さ」（割安さ1位の馬の比）で決める
    # 前向きに確かめる候補（まだ買い目には使わない）: S3 穴の基準（6番人気以下・割安さ1.3以上・確率2%以上）／S4 5頭目の印（印なしで割安さ1位・確率3%以上）
    rt = lambda h: h["p_model"] / h["p_market"]
    c3 = [h for h in hs if h["uma"] not in used and h["pop"] >= 6 and h["p_model"] >= .02 and rt(h) >= 1.3]
    s3 = max(c3, key=rt)["uma"] if c3 else None
    c4 = [h for h in hs if h["uma"] not in used and h["p_model"] >= .03]
    s4 = max(c4, key=rt)["uma"] if c4 else None
    if ana is None:
        c = [h for h in hs if h["uma"] not in used and h["pop"] >= 6 and h["p_model"] >= .02]
        ana = max(c, key=lambda h: h["p_model"] / h["p_market"])["uma"] if c else None
    o_ratio = rt(by[o]) if o else 0; ana_ratio = rt(by[ana]) if ana else 0
    if not tier:
        pat, why = "K3", "--no-tier（強さを変えない以前の組み方）"
    elif pattern and pattern != "auto":
        pat, why = pattern, "型を指定"
    else:
        ps = sum(h["p_model"] for h in race["horses"]) or 1; qs = sum(h["p_market"] for h in race["horses"]) or 1
        pm = sorted((h["p_model"] / ps for h in race["horses"]), reverse=True); Ph = max(race["horses"], key=lambda h: h["p_model"])["uma"]
        fx = feats(ratio, by[H]["pop"], len(race["horses"]), o_ratio, ana_ratio, by[H]["p_model"] / ps, (by[o]["p_model"] / ps if o else 0),
                   max(h["p_market"] for h in race["horses"]) / qs, (rt(by[t]) if t else 0), len(M["△"]), race.get("dist", ""), race.get("cond", "") + " " + race.get("title", ""), race.get("baba", ""),
                   odds_hon=by[H]["odds"], pop_o=(by[o]["pop"] if o else 0), pop_t=(by[t]["pop"] if t else 0), hon_is_p=(Ph == H), has_ana=bool(ana), venue=race.get("venue", ""), top3_p=sum(pm[:3]))
        pat, why = pick_pattern(fx)
    SH = PATTERNS[pat][1]
    if tr == "見送り":
        budget = max(r100(budget * LOW_BUDGET), 1000)
    core = [x for x in (o, t) if x is not None]
    T = tickets_for(SH, H, o, t, D, ana, budget)
    if hoken and len(core) == 2:
        T.append(["馬連", tuple(sorted((o, t))), r100(budget * .10), "◎抜きの保険"])
    # ── 確率（モデル・全頭 Harville）──
    uma = [h["uma"] for h in race["horses"]]; p = np.array([h["p_model"] for h in race["horses"]], float); p /= p.sum()
    q = np.array([h["p_market"] for h in race["horses"]], float); q /= q.sum()
    Tn = C.tensor(p); ix = {u: i for i, u in enumerate(uma)}; n = len(uma)
    hi = ix[H]
    tot = sum(x[2] for x in T)
    def hit(x, a, b, c):
        typ, cb = x[0], [ix[u] for u in x[1]]
        if typ == "単勝":
            return a == cb[0]
        if typ == "複勝":
            return cb[0] in (a, b, c)
        if typ == "馬単":
            return (a, b) == tuple(cb)
        if typ == "3連単":
            return (a, b, c) == tuple(cb)
        if typ == "馬連":
            return {a, b} == set(cb)
        if typ == "ワイド":
            return set(cb) <= {a, b, c}
        return set(cb) == {a, b, c}
    odds = {}
    if use_odds:
        try:
            po = F.pair_odds(race["rid"]); to = F.trio_odds(race["rid"])
            for x in T:
                if x[0] == "単勝":
                    odds[(x[0], x[1])] = by[x[1][0]]["odds"]
                elif x[0] in ("馬連", "ワイド"):
                    odds[(x[0], x[1])] = po[x[0]].get(x[1])
                elif x[0] == "3連複":
                    odds[(x[0], x[1])] = to.get(x[1])
                # 複勝・馬単・3連単のオッズはまだ取っていない（期待値は出さない。的中の確率だけ出す）
        except Exception as e:
            print("（組み合わせオッズは取れず:", str(e)[:60], "）")
    pos = np.zeros(4); cov = np.zeros(4); anyhit = 0.0; gami = 0.0; pt = np.zeros(len(T)); ev_ret = 0.0
    for a in range(n):
        for b in range(n):
            if b == a:
                continue
            for c in range(n):
                if c in (a, b):
                    continue
                pr = Tn[a, b, c]
                if pr <= 0:
                    continue
                k = 0 if a == hi else 1 if b == hi else 2 if c == hi else 3
                pos[k] += pr
                hs_ = [hit(x, a, b, c) for x in T]
                if any(hs_):
                    cov[k] += pr; anyhit += pr
                for j, h_ in enumerate(hs_):
                    if h_:
                        pt[j] += pr
                if odds:
                    ret = sum(x[2] * (odds.get((x[0], x[1])) or 0) for x, h_ in zip(T, hs_) if h_)
                    ev_ret += pr * ret
                    if any(hs_) and ret < tot:
                        gami += pr
    return dict(H=H, o=o, t=t, D=D, ana=ana, tickets=T, total=tot, pos=pos, cov=cov, anyhit=anyhit, pt=pt, odds=odds, ev=ev_ret / tot if odds else None,
                gami=gami / anyhit if odds and anyhit else None, by=by, ratio=ratio, tier=tr, s3=s3, s4=s4, pattern=pat, pattern_name=PATTERNS[pat][0], why=why, o_ratio=o_ratio, ana_ratio=ana_ratio)


CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"


def fmt_post(r):
    """買い目の表記（v3・2026-11-14。2026-11-26 に ◎以外が軸の点・複数の単勝/複勝・馬単・3連単・並びの違う3連複に対応）:
    合計を先に → 券種ごとのブロック → 流しは「軸 ― 相手」、フォーメーションは「1頭目／2頭目／3頭目」の3行 →
    同額は「各◯円」、金額が違う組は相手ごとに書く → 各ブロックの最後に役割を1行。全角スペースの桁揃えはしない（スマホで崩れる）。"""
    c = lambda u: CIRC[u - 1]
    T = r["tickets"]; H = r["H"]
    mk = {H: "◎"}
    for u, m in ((r["o"], "○"), (r["t"], "▲"), (r["ana"], "穴")):
        if u:
            mk.setdefault(u, m)
    for u in r["D"]:
        mk.setdefault(u, "△")
    cm = lambda u: (mk.get(u, "") if mk.get(u) in ("◎", "○", "▲", "穴") else "") + c(u)
    L = [f"💰 買い目 合計{len(T)}点・{r['total']:,}円", ""]
    for typ, tail in (("単勝", "が勝てば的中"), ("複勝", "が3着以内なら的中")):
        xs = [x for x in T if x[0] == typ]
        if len(xs) == 1:
            L += [f"【{typ}】{cm(xs[0][1][0])} {xs[0][2]:,}円", f"・{mk.get(xs[0][1][0], '')}{tail}", ""]
        elif xs:
            L += [f"【{typ}】" + "／".join(f"{cm(x[1][0])} {x[2]:,}円" for x in xs), f"・どちらか{tail}", ""]
    ut = [x for x in T if x[0] == "馬単"]
    if ut:
        L.append(f"【馬単】{len(ut)}点・{sum(x[2] for x in ut):,}円")
        L += [f"{cm(x[1][0])} → {cm(x[1][1])} {x[2]:,}円" for x in ut]
        L += ["・1着と2着の順番どおりなら的中", ""]
    for typ, role in (("馬連", "・◎が2着以内のときの本線"), ("ワイド", "・◎が3着以内のときの押さえ")):
        xs = [x for x in T if x[0] == typ and H in x[1]]
        if xs:
            aite = [(next(u for u in x[1] if u != H), x[2]) for x in xs]
            L.append(f"【{typ}】軸 ◎{c(H)} ― 相手 {''.join(c(u) for u, _ in aite)}（{len(aite)}点・{sum(y for _, y in aite):,}円）")
            if len({y for _, y in aite}) == 1:
                L.append(f"各{aite[0][1]:,}円")
            else:
                L.append("／".join(f"{c(u)} {y:,}円" for u, y in aite))
            L += [role, ""]
        ex = [x for x in T if x[0] == typ and H not in x[1]]
        if ex:
            L.append(f"【{typ}】" + "／".join(f"{'-'.join(cm(u) for u in x[1])} {x[2]:,}円" for x in ex))
            L += ["・◎が来ないときの受け", ""]
    tri = [x for x in T if x[0] == "3連複"]
    if tri:
        col2 = [u for u in (r["o"], r["t"]) if u]
        aite = [u for u in [r["o"], r["t"]] + r["D"] + [r["ana"]] if u]
        std = {tuple(sorted((H, x, y))) for x in col2 for y in aite if y != x}
        if {x[1] for x in tri} == std:
            col3 = [u for u in aite if any(u in x[1] for x in tri)]
            base = min(x[2] for x in tri); big = [x for x in tri if x[2] > base]
            L.append(f"【3連複フォーメーション】{len(tri)}点・{sum(x[2] for x in tri):,}円")
            L += [f"1頭目 ◎{c(H)}", f"2頭目 {''.join(c(u) for u in col2)}", f"3頭目 {''.join(c(u) for u in col3)}"]
            L.append(f"各{base:,}円" + ("".join(f"（{'-'.join(c(u) for u in x[1])}だけ{x[2]:,}円）" for x in big)))
        else:
            L.append(f"【3連複】{len(tri)}点・{sum(x[2] for x in tri):,}円")
            if len({x[2] for x in tri}) == 1:
                L += ["／".join("-".join(c(u) for u in x[1]) for x in tri), f"各{tri[0][2]:,}円"]
            else:
                L += [f"{'-'.join(c(u) for u in x[1])} {x[2]:,}円" for x in tri]
        L += ["・3頭とも3着以内なら高配当", ""]
    t3 = [x for x in T if x[0] == "3連単"]
    if t3:
        c2 = list(dict.fromkeys(x[1][1] for x in t3)); c3_ = list(dict.fromkeys(x[1][2] for x in t3))
        L.append(f"【3連単フォーメーション】{len(t3)}点・{sum(x[2] for x in t3):,}円")
        L += [f"1着 ◎{c(H)}", f"2着 {''.join(c(u) for u in c2)}", f"3着 {''.join(c(u) for u in c3_)}", f"各{t3[0][2]:,}円", "・◎が勝ったときに高配当を狙う", ""]
    pos, cov = r["pos"], r["cov"]
    L.append(f"どれかが当たる確率 約{r['anyhit']*100:.0f}%")
    L.append("◎が" + "・".join(f"{lab}なら{cov[i]/max(pos[i],1e-9)*100:.0f}%" for i, lab in enumerate(("1着", "2着", "3着"))) + "を拾える形"
             + (f"／◎が着外でも{cov[3]/max(pos[3],1e-9)*100:.0f}%を拾える" if cov[3] > 0 else ""))
    return chr(10).join(L)



def show(k, race, r):
    by = r["by"]; nm = lambda u: f"{u}{by[u]['name'][:8]}"
    print(f"■ {k} {race['title']} {race['dist']} {race['n']}頭")
    note = {"見送り": "＝見送り（公開しない。出すなら少額）", "単勝本線": "＝単勝を本線", "通常": "＝通常"}[r["tier"]]
    print(f"  型: {r['pattern']} {r['pattern_name']} ｜ {r['why']}")
    print(f"  判断の材料: ○の割安さ {r['o_ratio']:.2f}" + ("（○も割安）" if r["o_ratio"] >= O_VALUE else "") + f" ／ 穴の割安さ {r['ana_ratio']:.2f}" + ("（割安な穴）" if r["ana_ratio"] >= ANA_VALUE else ""))
    print(f"  ◎の割安さ {r['ratio']:.2f} {note}" + (f" ／ 候補S3の穴 {nm(r['s3'])}" if r["s3"] else "") + (f" ／ 候補S4の5頭目 {nm(r['s4'])}" if r["s4"] else ""))
    print("  印: ◎" + nm(r["H"]) + (" ○" + nm(r["o"]) if r["o"] else "") + (" ▲" + nm(r["t"]) if r["t"] else "") + "".join(" △" + nm(d) for d in r["D"]) + (" 穴" + nm(r["ana"]) if r["ana"] else ""))
    for (typ, cb, yen, role), p_ in zip(r["tickets"], r["pt"]):
        o_ = r["odds"].get((typ, cb)) if r["odds"] else None
        print(f"   {typ:4} {'-'.join(map(str, cb)):9} {yen:6,}円  当たる{p_*100:5.1f}%" + (f"  オッズ{o_:7.1f}  期待値{p_*o_:5.2f}" if o_ else "") + f"  〔{role}〕")
    pos, cov = r["pos"], r["cov"]
    print(f"  合計 {r['total']:,}円 ／ どれかが当たる {r['anyhit']*100:.1f}%" + (f" ／ 期待回収率 {r['ev']:.2f} ／ 当たっても損 {r['gami']*100:.0f}%" if r["ev"] else ""))
    print("  場面ごと: " + " ｜ ".join(f"◎{lab} {pos[i]*100:.1f}%→拾える{cov[i]/max(pos[i],1e-9)*100:.0f}%" for i, lab in enumerate(("1着", "2着", "3着", "着外"))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--race", nargs="+", required=True)
    ap.add_argument("--budget", type=int, default=10000); ap.add_argument("--keep", nargs="*", type=int, default=[])
    ap.add_argument("--ana", type=int); ap.add_argument("--hoken", action="store_true"); ap.add_argument("--no-odds", action="store_true")
    ap.add_argument("--post", action="store_true", help="投稿用の買い目の表記（v3）も出す")
    ap.add_argument("--no-tier", action="store_true", help="◎の割安さで強さを変えない（2026-11-18より前の組み方）")
    ap.add_argument("--pattern", default="auto", help="買い目の型。auto＝区分の表から引く（既定）／K1〜K34 で指定")
    a = ap.parse_args()
    d = json.load(open(WL.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))
    print("オッズ取得:", d.get("made_at"))
    out = {}
    for k in a.race:
        r = compose(d["races"][k], a.budget, a.keep, a.ana, a.hoken, not a.no_odds, not a.no_tier, a.pattern)
        show(k, d["races"][k], r)
        if a.post:
            print(chr(10) + fmt_post(r) + chr(10))
        out[k] = dict(tickets=[[t, list(c), y, ro] for t, c, y, ro in r["tickets"]], total=r["total"], anyhit=round(r["anyhit"], 4),
                      pos=[round(float(x), 4) for x in r["pos"]], cov=[round(float(x), 4) for x in r["cov"]], ev=r["ev"], ana=r["ana"], ratio=round(float(r["ratio"]), 3), tier=r["tier"], s3=r["s3"], s4=r["s4"], pattern=r["pattern"], pattern_name=r["pattern_name"])
    json.dump(out, open(WL.OUT / f"{a.date}_web_compose.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
