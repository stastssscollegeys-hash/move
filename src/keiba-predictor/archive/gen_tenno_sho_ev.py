"""
天皇賞・春 2026 独自指数（純粋能力評価）＋EV参考予想
X / Threads / note の3形式をWordで出力

方針:
  - 独自スコアは純粋な能力・適性評価（人気・オッズは一切加味しない）
  - EV（期待値）は「買い目の上乗せ判断」として別途参照
  - 硬い部分は硬く、穴はEV根拠で加える
"""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260503")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "20260503_天皇賞春_独自指数EV予想SNS.docx"


# ════════════════════════════════════════════════════
# 独自スコアリング（7項目・純粋能力評価）
# ════════════════════════════════════════════════════
# [1] 能力・実績  30点  G1/G2実績・タイム・近走内容
# [2] 距離適性   20点  3000m以上での実績（必須項目）
# [3] 京都適性   10点  京都コースでの成績
# [4] 枠順      10点  今回の枠の有利不利
# [5] 調教評価   15点  最終追い切り評価
# [6] 騎手      10点  騎手の技術・コース相性
# [7] 展開       5点  脚質×予想ペース（スロー想定）
#
# ペース想定: スティンガーグラス回避→逃げ馬減→スロー〜平均
#            先行有利。差しは末脚の質次第。

HORSES = [
    # (馬番, 馬名, 騎手, 性齢, 斤量, オッズ, [能力,距離,京都,枠,調教,騎手,展開], 脚質, メモ)
    ( 1, "ヴェルミセル",       "鮫島克駿", "牝6", 56.0, 110.0,
      [ 5,  4,  4,  8, 10,  5,  2], "先行〜差し", "前走海外11着"),
    ( 2, "サンライズソレイユ",  "池添謙一", "牡5", 58.0, 100.0,
      [ 5,  5,  4,  8,  9,  7,  2], "不明",       "近走低迷"),
    ( 3, "アドマイヤテラ",     "武豊",     "牡5", 58.0,   3.6,
      [22, 17,  7,  9, 12, 10,  5], "先行",       "阪神大賞典3000mレコード・菊花賞3着"),
    ( 4, "アクアヴァーナル",   "松山弘平", "牝5", 56.0,  12.3,
      [16, 14,  5,  8, 10,  7,  4], "先行",       "阪神大賞典2着・牝馬2kg有利・内枠"),
    ( 5, "ケイアイサンデラ",   "藤懸貴志", "セ6", 58.0, 230.0,
      [ 1,  3,  3,  7,  9,  4,  1], "不明",       "前走障害11着"),
    ( 6, "エヒト",            "川田将雅", "牡9", 58.0,  47.9,
      [12,  7,  4,  6, 10, 10,  2], "差し",       "AJCC1着(9歳)・3000m超初・川田"),
    ( 7, "クロワデュノール",   "北村友一", "牡4", 58.0,   2.3,
      [29,  8,  4,  7, 15,  6,  4], "中団差し",   "ダービー×大阪杯G1・調教S評価・3200m初"),
    ( 8, "シンエンペラー",     "岩田望来", "牡5", 58.0,  22.6,
      [20, 11,  5,  6, 10,  6,  3], "先行",       "JC2着同着・凱旋門賞経験・3200m初"),
    ( 9, "プレシャスデイ",     "吉村誠之助","牡4",58.0, 200.0,
      [ 3,  3,  3,  5,  9,  4,  1], "不明",       "格下・重賞実績なし"),
    (10, "マイネルカンパーナ", "津村明秀", "牡6", 58.0,  78.3,
      [ 8, 13,  4,  6, 12,  4,  3], "逃げ",       "ダイヤモンドS(3400m)経験・調教A"),
    (11, "タガノデュード",     "古川吉洋", "牡5", 58.0,  26.6,
      [14,  5,  4,  6,  9,  4,  3], "差し",       "大阪杯4着・3000m超初"),
    (12, "ヘデントール",       "C.ルメール","牡5",58.0,   5.2,
      [24, 20, 10,  5,  5,  9,  3], "先行〜差し", "昨年覇者・骨折明け・調教C"),
    (13, "ミステリーウェイ",   "松本大輝", "牡8", 58.0, 140.0,
      [ 9, 11,  4,  4,  9,  4,  3], "逃げ",       "長距離OP勝ち・8歳高齢"),
    (14, "ホーエリート",       "戸崎圭太", "牝5", 56.0,  32.8,
      [17, 18,  3,  4, 10,  8,  4], "先行",       "ステイヤーズS3600m優勝・牝馬2kg有利"),
    (15, "ヴェルテンベルク",   "松若風馬", "牡6", 58.0, 130.0,
      [ 8, 12,  4,  3,  9,  5,  2], "不明",       "ダイヤモンドS4着・ステイヤーズS6着"),
]

# 独自勝率（%）: スコアをベースに距離・展開の不確実性を加味して手動調整
# ※オッズは一切参照しない
MY_WIN_PROB = {
    3:  30.0,   # アドマイヤテラ：指数1位・全条件揃う
    12: 18.0,   # ヘデントール：指数2位・状態懸念でやや割引
    7:  20.0,   # クロワデュノール：能力最上位・3200m初で不確実性割引
    14:  8.0,   # ホーエリート：距離適性高・能力差で割引
    4:   6.0,   # アクアヴァーナル：内枠×牝馬有利
    8:   6.0,   # シンエンペラー：高能力・距離未知数
    6:   3.5,   # エヒト：川田×調教好調
    10:  2.5,   # マイネルカンパーナ：調教A・展開次第
    11:  2.0,   # タガノデュード：3000m超初
    13:  1.0,   # ミステリーウェイ：8歳高齢
    15:  1.0,   # ヴェルテンベルク：大外・実績差
    1:   0.5,   # ヴェルミセル
    2:   0.5,   # サンライズソレイユ
    5:   0.5,   # ケイアイサンデラ
    9:   0.5,   # プレシャスデイ
}


def calc_ev(horse_no, odds):
    p = MY_WIN_PROB.get(horse_no, 0.5) / 100
    return (p * odds - 1) * 100


def ev_tag(ev):
    if ev >= 100: return "★★★ EV+++"
    if ev >= 30:  return "★★  EV++"
    if ev >= 0:   return "★   EV+"
    if ev >= -30: return "    EV-"
    return               "✗   EV--"


# ════════════════════════════════════════════════════
# Word ユーティリティ
# ════════════════════════════════════════════════════

def set_font(run, size_pt=10.5, bold=False, color=None, font_name="游ゴシック"):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:hint'), 'eastAsia')
    rFonts.set(qn('w:eastAsia'), font_name)
    rpr.insert(0, rFonts)

def set_mincho(run, size_pt=11, bold=False, color=None):
    set_font(run, size_pt=size_pt, bold=bold, color=color, font_name="游明朝")

def add_section_bar(doc, text, color=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_font(run, size_pt=13, bold=True, color=color or RGBColor(0x0F, 0x47, 0x61))

def add_label(doc, text, color):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_font(run, size_pt=10, bold=True, color=color)

def add_box(doc, content, bg_color="F5F5F5", note=None):
    if note:
        pn = doc.add_paragraph()
        run = pn.add_run(f"  ※{note}")
        set_font(run, size_pt=8.5, color=RGBColor(0x88, 0x88, 0x88))
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = 'Table Grid'
    cell = tbl.rows[0].cells[0]
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), bg_color)
    tcPr.append(shd)
    for line in content.strip().split('\n'):
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10)
    doc.add_paragraph()

def add_heading(doc, text, level=2):
    p = doc.add_paragraph()
    if level == 2:
        run = p.add_run(f"▍ {text}")
        set_font(run, size_pt=13, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    elif level == 3:
        run = p.add_run(f"◆ {text}")
        set_font(run, size_pt=11, bold=True, color=RGBColor(0x33, 0x66, 0x99))

def add_body(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_mincho(run, size_pt=11)


# ════════════════════════════════════════════════════
# SNS投稿テキスト
# ════════════════════════════════════════════════════

X_POST1 = """\
🏇【天皇賞・春2026 独自指数予想】
7項目スコアリング×EV分析で導いた結論

独自指数ランキング（純粋能力評価）
1位 アドマイヤテラ  82点
2位 ヘデントール    76点
3位 クロワデュノール 73点
4位 ホーエリート   64点

能力指数では◎アドマイヤテラが断然
EV計算で穴はホーエリート（+162%）を加える

詳細は次ツイートで👇
#天皇賞春 #競馬 #アスメシ競馬"""

X_POST2 = """\
🏇【天皇賞・春2026 独自指数予想】本命発表

◎ 3番 アドマイヤテラ（武豊）3.6倍
指数1位82点 EV+8%
阪神大賞典3000mレコード×菊花賞3着
武豊×京都×内枠が全部揃った

○ 12番 ヘデントール（ルメール）5.2倍
指数2位76点 ※状態懸念
昨年京都3200m覇者・距離適性は最高
ただし骨折明け・調教C→信頼度割引

▲ 7番 クロワデュノール（北村）2.3倍
指数3位73点 ※3200m初距離が唯一の壁
能力は全馬最上位・調教S評価
初距離さえ克服すれば差し込んでくる

★穴 14番 ホーエリート（戸崎）32.8倍
指数4位64点 EV+162%
唯一の3600mG2制覇馬×牝馬2kg有利
能力差があっても距離と斤量で捲る可能性

#天皇賞春 #競馬予想 #アスメシ競馬"""

X_POST3 = """\
🏇【天皇賞・春2026 買い目】

【固い本線】
単勝   ③アドマイヤテラ
馬連   ③-⑫（◎×昨年覇者）
馬連   ③-⑦（◎×能力最上位）

【穴上乗せ（EV+162%）】
ワイド  ③-⑭（◎×ステイヤー）
ワイド  ⑦-⑭（能力×ステイヤー）

【穴狙い派向け】
3連複  ③-⑦-⑭

【消し】
✗ ケイアイサンデラ（前走障害11着）
✗ プレシャスデイ（格下）
✗ ミステリーウェイ（8歳・前走大敗）

#天皇賞春 #馬券 #アスメシ競馬"""

THREADS_POST = """\
🏇【天皇賞・春2026 独自指数×EV分析予想】
2026年5月3日（日）京都芝3200m G1

━━━━━━━━━━━━━━━━
📊 独自7項目スコア（純粋能力評価）
━━━━━━━━━━━━━━━━
能力・実績30 + 距離適性20 + 京都適性10
+ 枠順10 + 調教15 + 騎手10 + 展開5 = 100点満点

人気・オッズは一切考慮しない純粋評価

━━━━━━━━━━━━━━━━
🏆 独自指数ランキング
━━━━━━━━━━━━━━━━
1位 アドマイヤテラ  82点  EV +8%   ◎
2位 ヘデントール    76点  EV −22%  ○（状態懸念）
3位 クロワデュノール 73点  EV −43%  ▲（3200m初）
4位 ホーエリート   64点  EV+162%  ★穴（距離実績最高）
4位 アクアヴァーナル 64点  EV −38%  △（内枠×牝馬）
6位 シンエンペラー  61点  EV +13%  △

━━━━━━━━━━━━━━━━
◎ アドマイヤテラ（武豊）3.6倍
━━━━━━━━━━━━━━━━
阪神大賞典(3000m)コースレコード勝ち＋菊花賞3着という
長距離での実績が武豊×内枠（2枠3番）と組み合わさった。
調教A評価で状態面も万全。7項目中6項目でメンバー上位を記録。
EV+8%と小さいが「最も死角が少い信頼できる軸馬」。

━━━━━━━━━━━━━━━━
○ ヘデントール（ルメール）5.2倍
━━━━━━━━━━━━━━━━
昨年の天皇賞・春覇者。京都3200mの経験値はこの馬だけが持つ唯一の武器。
ただし骨折明け初戦の京都記念8着からの2戦目、最終追い切りで
併せ馬に遅れた「調教C評価」はどうしても引っかかる。
能力と実績から○は動かないが、EV的には割高（-22%）。
当日のパドックで状態を必ず確認したい。

━━━━━━━━━━━━━━━━
▲ クロワデュノール（北村友一）2.3倍
━━━━━━━━━━━━━━━━
ダービー×大阪杯G1制覇、調教S評価、レーティング122。
能力は全馬で最上位であることは疑いようがない。
唯一の課題は「3200mを走ったことがない」という一点。
最長距離は有馬記念(2500m)。父キタサンブラックの血統背景は
距離延長に好材料だが、調教師も「力む面が不安」とコメント。
能力で乗り越える可能性は十分ある▲評価。買い目に含める。

━━━━━━━━━━━━━━━━
★穴 ホーエリート（戸崎圭太）32.8倍
━━━━━━━━━━━━━━━━
指数4位ながらEV+162%という最大の期待値馬。
ステイヤーズS(G2・3600m)優勝という「出走馬唯一の3600m実績」保持者。
牝馬56kgで雄馬比2kg軽い斤量は長距離消耗戦で直結する。
32.8倍という評価は明らかに距離実績が無視されている。
戸崎騎手との鉄板コンビで、折り合いと位置取りは安心。
京都初挑戦と輸送がリスクだが、EV的に買わない理由がない穴馬。

━━━━━━━━━━━━━━━━
💰 買い目
━━━━━━━━━━━━━━━━
【固い本線】
単勝    ③アドマイヤテラ
馬連    ③-⑫（◎×昨年覇者）
馬連    ③-⑦（◎×能力最上位）

【EV穴追加】
ワイド   ③-⑭（◎×ステイヤー EV+162%）
ワイド   ⑦-⑭（能力×ステイヤー）

【穴狙い派向け】
3連複   ③-⑦-⑭

#天皇賞春 #競馬予想 #AI競馬予想 #アスメシ競馬"""


# ════════════════════════════════════════════════════
# メイン
# ════════════════════════════════════════════════════

def main():
    doc = Document()

    # ── 表紙 ──
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("天皇賞・春 2026 独自指数×EV分析予想 SNS投稿案")
    set_font(run, size_pt=15, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026年5月3日（日）京都競馬場 芝3200m G1 ／ 全15頭（スティンガーグラス回避）")
    set_font(run, size_pt=9, color=RGBColor(0x88, 0x88, 0x88))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "◎アドマイヤテラ（指数1位82点）  ○ヘデントール  ▲クロワデュノール  ★穴ホーエリート（EV+162%）"
    )
    set_font(run, size_pt=10, bold=True, color=RGBColor(0xB7, 0x1C, 0x1C))

    doc.add_paragraph()

    # ── 独自スコア表（純粋能力評価） ──
    add_section_bar(doc, "━━━ 独自7項目スコア（純粋能力評価・オッズ無関係） ━━━",
                    RGBColor(0x1B, 0x5E, 0x20))
    doc.add_paragraph()

    pn = doc.add_paragraph()
    run = pn.add_run(
        "  ※能力30＋距離20＋京都10＋枠10＋調教15＋騎手10＋展開5 ＝ 100点満点　"
        "｜ EV = 独自勝率 × オッズ − 1（参考）"
    )
    set_font(run, size_pt=8.5, color=RGBColor(0x55, 0x55, 0x55))

    # テーブル
    COL_HEADERS = ["順位", "馬番", "馬名", "オッズ", "能力", "距離", "京都",
                   "枠", "調教", "騎手", "展開", "合計", "独自勝率", "EV%", "EV評価"]
    tbl = doc.add_table(rows=1, cols=len(COL_HEADERS))
    tbl.style = 'Table Grid'
    hdr_row = tbl.rows[0]
    for i, h in enumerate(COL_HEADERS):
        cell = hdr_row.cells[i]
        p = cell.paragraphs[0]
        run = p.add_run(h)
        set_font(run, size_pt=8, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), "0F4761")
        tcPr.append(shd)

    sorted_horses = sorted(HORSES, key=lambda h: sum(h[6]), reverse=True)
    for rank, h in enumerate(sorted_horses, 1):
        no, name, jockey, age, kg, odds, scores, style, memo = h
        total = sum(scores)
        my_prob = MY_WIN_PROB.get(no, 0.5)
        ev = calc_ev(no, odds)
        ev_str = f"{ev:+.1f}%"
        ev_jdg = ev_tag(ev)

        row = tbl.add_row()
        vals = [
            str(rank), str(no), name, f"{odds}倍",
            str(scores[0]), str(scores[1]), str(scores[2]),
            str(scores[3]), str(scores[4]), str(scores[5]), str(scores[6]),
            str(total), f"{my_prob:.1f}%", ev_str, ev_jdg
        ]
        for i, val in enumerate(vals):
            cell = row.cells[i]
            p = cell.paragraphs[0]
            run = p.add_run(val)
            set_font(run, size_pt=8)
            # 色分け：EV+++は緑、EV--は赤
            if ev >= 100:   bg = "E8F5E9"
            elif ev >= 0:   bg = "F1F8E9"
            elif ev < -30:  bg = "FFF5F5"
            else:           bg = "FFFFFF"
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), bg)
            tcPr.append(shd)

    doc.add_paragraph()

    # ── 予想サマリー ──
    add_section_bar(doc, "━━━ 予想サマリー ━━━", RGBColor(0x1A, 0x23, 0x7E))
    doc.add_paragraph()

    add_box(doc, """\
【指数×EV 総合予想】

◎ 3番  アドマイヤテラ   3.6倍  指数1位(82点) EV +8%
   → 指数・実績・枠・騎手・状態、全ての観点で最も信頼できる軸馬

○ 12番 ヘデントール     5.2倍  指数2位(76点) EV −22%
   → 昨年覇者・コース経験値最高。ただし調教C・骨折明けで割引

▲ 7番  クロワデュノール  2.3倍  指数3位(73点) EV −43%
   → 能力・調教は全馬最上位。3200m初距離の不確実性だけが懸念

★穴 14番 ホーエリート   32.8倍 指数4位(64点) EV +162%
   → 唯一の3600mG2覇者＋牝馬2kg有利。市場が長距離実績を無視

△ 4番  アクアヴァーナル 12.3倍  指数4位(64点)
   → 内枠×牝馬2kg×阪神大賞典2着。アドマイヤテラとのワイド推奨

【消し馬】
✗  5番 ケイアイサンデラ（前走障害11着・指数最下位）
✗  9番 プレシャスデイ  （格下・重賞実績なし）
✗ 13番 ミステリーウェイ（8歳・直近大敗）
✗  1番 ヴェルミセル   （前走海外11着）""",
        bg_color="E3F2FD")

    doc.add_page_break()

    # ── X投稿 ──
    add_section_bar(doc, "━━━ X（Twitter）投稿 ━━━", RGBColor(0x1D, 0xA1, 0xF2))
    doc.add_paragraph()

    add_label(doc, "【投稿①】指数ランキング公開（最初）", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_POST1, "EBF5FB", note="枠順確定日〜前日に投稿。指数結果で注目を集める")

    add_label(doc, "【投稿②】本命発表", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_POST2, "EBF5FB", note="投稿①の数時間後〜前日夜")

    add_label(doc, "【投稿③】買い目公開", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_POST3, "EBF5FB", note="当日朝（5/3）に投稿")

    doc.add_page_break()

    # ── Threads ──
    add_section_bar(doc, "━━━ Threads投稿（全情報まとめ版） ━━━", RGBColor(0x00, 0x00, 0x00))
    doc.add_paragraph()
    add_label(doc, "【Threads】独自指数×EV分析まとめ（1投稿）", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, THREADS_POST, "F5F5F5", note="前日夜〜当日朝に投稿")

    doc.add_page_break()

    # ── note記事 ──
    add_section_bar(doc, "━━━ note記事（独自指数×EV分析版） ━━━", RGBColor(0xC2, 0x18, 0x5B))
    doc.add_paragraph()

    p = doc.add_paragraph()
    run = p.add_run(
        "【天皇賞・春2026】独自7項目指数1位◎アドマイヤテラが軸、"
        "EV+162%のホーエリートを穴で加える理由"
    )
    set_font(run, size_pt=14, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    run = p.add_run("2026年5月3日（日）京都競馬場 芝3200m G1　アスメシ競馬予想")
    set_font(run, size_pt=9, color=RGBColor(0x99, 0x99, 0x99))

    doc.add_paragraph()

    add_body(doc,
        "　今回は「7項目独自スコアリング（純粋能力評価）」と「期待値（EV）分析」を組み合わせた予想をお届けします。"
        "能力で固い部分は固く、EV的に過小評価されている穴馬を買い目に加えるという方針です。"
    )
    doc.add_paragraph()

    # スコアリング説明
    add_heading(doc, "独自スコアリングの7項目と考え方", level=2)
    doc.add_paragraph()
    add_box(doc, """\
① 能力・実績   30点  G1/G2の勝ち鞍・レーティング・近走タイム
② 距離適性    20点  3000m以上での出走実績と着順（最重要項目）
③ 京都適性    10点  京都コースでの勝利・馬券実績
④ 枠順       10点  今回の枠番の物理的有利不利
⑤ 調教評価    15点  最終追い切り・1週前のタイム・評価
⑥ 騎手       10点  騎手の技術・当該コース相性・馬との信頼関係
⑦ 展開        5点  脚質×ペース予想（スロー）との整合性

【重要】このスコアはオッズ・人気を一切参照していない純粋評価。
高いスコアでも人気が高いとは限らず、低いスコアでも穴になれる。
EV分析は「スコアに対してオッズが妥当かどうか」を示す別の指標。""",
        bg_color="E3F2FD")

    doc.add_paragraph()

    # 各馬評価
    add_heading(doc, "◎ 本命：3番 アドマイヤテラ（武豊）3.6倍 ― 指数1位82点", level=2)
    doc.add_paragraph()
    add_box(doc, """\
能力 22/30：阪神大賞典3000mコースレコード制覇。G2レベルでは格上の存在。
距離 17/20：菊花賞3着(3000m)＋阪神大賞典1着(3000m)。3000mでの経験値◎
京都  7/10：菊花賞3着の京都コース経験あり
枠    9/10：2枠3番は今回最高水準の内枠。ロスを最小化できる
調教 12/15：A評価。最終追い切りで「仕上がり完了」
騎手 10/10：武豊×京都×先行という黄金の組み合わせ
展開  5/ 5：スロー予想×先行脚質で最高の恩恵

EV +8%：3.6倍でも独自勝率30%から見ると小幅に割安""",
        bg_color="E8F5E9")

    doc.add_paragraph()

    add_heading(doc, "○ 対抗：12番 ヘデントール（C.ルメール）5.2倍 ― 指数2位76点", level=2)
    doc.add_paragraph()
    add_box(doc, """\
能力 24/30：天皇賞・春2025覇者。ダイヤモンドS(3400m)も制覇。
距離 20/20：3200mでの勝利実績は出走馬で唯一。満点評価。
京都 10/10：昨年の天皇賞・春を制した京都3200m。コース適性は最高。
枠    5/10：7枠12番の外枠はやや不利。道中のロスを嫌う。
調教  5/15：C評価（全15頭最低）。骨折明け2戦目・最終追い切りで併せ遅れ。
騎手  9/10：ルメール騎手の技術は最高水準。
展開  3/ 5：先行〜差しだが外枠でのスムーズさが課題。

EV −22%：能力と実績は◎レベルだが調教C評価が大きなリスク。
当日パドックで状態を必ず確認してから最終判断を。""",
        bg_color="FFF9C4")

    doc.add_paragraph()

    add_heading(doc, "▲ 3番手：7番 クロワデュノール（北村友一）2.3倍 ― 指数3位73点", level=2)
    doc.add_paragraph()
    add_box(doc, """\
能力 29/30：ダービー×大阪杯G1制覇。レーティング122は全馬最高。
距離  8/20：最長経験は有馬記念2500m。3200mは今回が初。← 最大のリスク
京都  4/10：重賞での京都実績なし。
枠    7/10：4枠7番の中枠。折り合いに集中できる標準的な枠。
調教 15/15：S評価（全馬最高）。「先週より格段に良くなっている」
騎手  6/10：北村友一騎手。能力を引き出せるか。
展開  4/ 5：中団差し。スローなら直線の切れ味を使える。

EV −43%：2.3倍という低オッズに対して3200m初という不確実性が大きい。
「能力で押し切れるか、距離の壁に屈するか」の二択。▲で買い目に含める。""",
        bg_color="FFF5F5")

    doc.add_paragraph()

    add_heading(doc, "★穴 14番 ホーエリート（戸崎圭太）32.8倍 ― 指数4位64点 EV+162%", level=2)
    doc.add_paragraph()
    add_box(doc, """\
能力 17/30：ステイヤーズS(G2)1着・目黒記念2着。G1実績はないが長距離の確かな地力。
距離 18/20：ステイヤーズS(3600m)優勝。3200mは「距離短縮」で来れる唯一の馬。
京都  3/10：関東馬・京都実績なし。← リスク要因
枠    4/10：8枠14番の外枠。スタートから距離ロス有。
調教 10/15：B評価。最終週で「馬体引き締まり、勝負所での反応に大きな変化」
騎手  8/10：戸崎圭太×ステイヤーズS・目黒記念の実績コンビ。
展開  4/ 5：先行脚質×スロー予想で有利。

EV計算：独自勝率8% × 32.8倍 = +162%
指数4位の馬が32.8倍というオッズは「長距離実績を市場が無視している」証拠。
固い軸（アドマイヤテラ）に上乗せするEV穴として必ず買い目に加える。""",
        bg_color="E8F5E9")

    doc.add_paragraph()

    # 買い目
    add_heading(doc, "買い目（案）", level=2)
    doc.add_paragraph()
    add_box(doc, """\
【固い本線】
単勝    ③ アドマイヤテラ        → 軸として最も信頼
馬連    ③-⑫                 → ◎×昨年覇者（実績ライン）
馬連    ③-⑦                 → ◎×能力最上位（能力ライン）

【EV穴 上乗せ（推奨）】
ワイド   ③-⑭                → ◎×EV+162%穴馬
ワイド   ⑦-⑭                → 能力馬×ステイヤー（大穴）

【穴狙い派向け】
3連複   ③-⑦-⑭

【参考：EV+馬同士の組み合わせ】
ワイド   ③-⑧（アドマイヤテラ×シンエンペラー EV+13%）""",
        bg_color="FFF9C4")

    doc.add_paragraph()

    # まとめ
    add_heading(doc, "まとめ", level=2)
    doc.add_paragraph()
    add_body(doc,
        "　独自指数では◎アドマイヤテラが82点で断然トップ。武豊×京都×内枠×距離実績という"
        "最高の条件が揃っており、最も安心して軸に据えられる馬です。"
    )
    doc.add_paragraph()
    add_body(doc,
        "　ヘデントールは実績・距離適性・コース適性で指数2位ですが、骨折明け×調教C評価が"
        "懸念材料。対抗に置きながらも、当日の状態確認を強く推奨します。"
    )
    doc.add_paragraph()
    add_body(doc,
        "　クロワデュノールの能力は本物ですが、3200m初という最大の未知数を2.3倍では"
        "買いにくい。▲として買い目には含めつつ、軸にはしません。"
    )
    doc.add_paragraph()
    add_body(doc,
        "　ホーエリートはEV+162%という独自分析で最も過小評価されている馬。"
        "指数4位の実力でも、唯一の3600mG2実績＋牝馬2kg有利という武器は32.8倍では割安です。"
        "固い本線に上乗せする形で、必ずワイドで押さえます。"
    )
    doc.add_paragraph()

    add_heading(doc, "推奨ハッシュタグ", level=2)
    doc.add_paragraph()
    add_box(doc, """\
#天皇賞春 #天皇賞 #競馬予想 #AI競馬予想 #重賞予想
#G1 #京都競馬場 #アドマイヤテラ #ヘデントール
#ホーエリート #武豊 #競馬収支 #アスメシ競馬 #馬券""",
        bg_color="F3E5F5",
        note="レース当日は #天皇賞春2026 を追加推奨")

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
