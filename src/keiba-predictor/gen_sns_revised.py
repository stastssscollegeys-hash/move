"""
2026/04/26 フローラS・マイラーズC 改訂版SNS投稿案生成
AIモデル再予測 + 全頭データ分析に基づく修正版
"""
import sys, os
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260426")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "20260426_SNS投稿案_revised.docx"

# ────────────────────────────────────────────────────────
# AI再予測結果（analyze_races.py の出力に基づく）
# ────────────────────────────────────────────────────────

# フローラS（東京 11R 芝2000m 13頭）
# 能力スコア順: ラフターラインズ15.3% > ペンダント11.6% > エンネ10.5% > ファムクラジューズ9.4% > サムシングスイート9.1% > ラベルセーヌ8.0%
# EV注目: ペンダント9.75x（CL評価A） / エンネ4.50x / ファムクラジューズ2.88x
FLORA_HORSES = {
    "hon":  {"no": 5,  "name": "ラフターラインズ",   "ability": 15.3, "ninki": 1,  "odds": 2.9,
              "reason": ["上がり3F 32.5s（メンバー最速）", "きさらぎ賞 上がり1位の末脚", "東京2000m直線向き"]},
    "tai":  {"no": 13, "name": "エンネ",             "ability": 10.5, "ninki": 3,  "odds": 6.8,
              "reason": ["前走1着・上がり最速", "EV4.50x 市場66%が認める素質", "外国人騎手D.レーン起用"]},
    "san":  {"no": 11, "name": "ファムクラジューズ",  "ability":  9.4, "ninki": 4,  "odds": 7.1,
              "reason": ["テンポ最速(#1)", "フリージア賞1着の実績", "横山武史騎手×勢い"]},
    "ana1": {"no": 6,  "name": "ペンダント",          "ability": 11.6, "ninki": 9,  "odds": 25.2,
              "reason": ["CL評価A（最高格付け）", "EV9.75x 超穴候補", "前走8人気1着の逆転実績"]},
    "ana2": {"no": 2,  "name": "ラベルセーヌ",        "ability":  8.0, "ninki": 2,  "odds": 4.4,
              "reason": ["2人気の支持", "前走1着・上がり1位", "荻野極騎手"]},
    "kesi": {"name": "ゴバド", "reason": "前走クイーンC13着大敗"},
}
FLORA_KAIMOKU = {
    "tansho": 5,
    "wide": [(5, 13), (5, 6)],
    "baren": [(5, 13), (5, 6)],
    "san_fuku": [(5, 13, 11)],
}

# マイラーズC（京都 11R 芝1600m 18頭）
# 能力スコア順: アドマイヤズーム12.4% > ファーヴェント12.0% > ベラジオボンド9.9% > シックスペンス7.7% > オフトレイル7.3% > ウォーターリヒト6.7%
# EV注目: ファーヴェント7.11x（CL評価A） / ベラジオボンド3.64x / ウォーターリヒト1.01x
MILERS_HORSES = {
    "hon":  {"no": 9,  "name": "アドマイヤズーム",   "ability": 12.4, "ninki": 1,  "odds": 3.6,
              "reason": ["テン337秒（18頭中最速）", "武豊騎手×京都内回り", "同コース1走1勝の適性"]},
    "tai":  {"no": 12, "name": "ファーヴェント",      "ability": 12.0, "ninki": 8,  "odds": 17.2,
              "reason": ["CL評価A（最高格付け）", "EV7.11x 大穴フラグ", "ダービーCT1人気3着の実力"]},
    "san":  {"no": 7,  "name": "ベラジオボンド",      "ability":  9.9, "ninki": 6,  "odds": 11.2,
              "reason": ["六甲S1着→新春S1着の連勝", "EV3.64x 妙味あり", "北村友一騎手起用"]},
    "ana1": {"no": 10, "name": "ウォーターリヒト",    "ability":  6.7, "ninki": 3,  "odds": 5.4,
              "reason": ["京都芝1600m 2走2勝（適性A）", "前走東京新聞杯3着", "高杉吏麒騎手"]},
    "ana2": {"no": 2,  "name": "オフトレイル",        "ability":  7.3, "ninki": 2,  "odds": 4.7,
              "reason": ["上がり328秒（メンバー最速）", "2人気の市場評価", "岩田望来騎手"]},
    "kesi": {"name": "シックスペンス", "reason": "前走ダート（フェブラリーS）大敗・同コース0走"},
}
MILERS_KAIMOKU = {
    "tansho": 9,
    "wide": [(9, 12), (9, 7)],
    "baren": [(9, 12), (9, 7)],
    "san_fuku": [(9, 12, 7)],
}


# ────────────────────────────────────────────────────────
# Word生成ユーティリティ
# ────────────────────────────────────────────────────────

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


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    if level == 1:
        set_font(run, size_pt=16, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    else:
        set_font(run, size_pt=13, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    return p


def add_section_title(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_font(run, size_pt=11, bold=True, color=RGBColor(0xFF, 0x88, 0x00))
    return p


def add_box(doc, title, lines, title_color=None, bg_color="E8F4FD"):
    """背景色付きボックスを追加"""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = 'Table Grid'
    cell = tbl.rows[0].cells[0]

    # 背景色設定
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), bg_color)
    tcPr.append(shd)

    if title:
        p = cell.add_paragraph()
        run = p.add_run(title)
        set_font(run, size_pt=10.5, bold=True, color=title_color or RGBColor(0x0F, 0x47, 0x61))

    for line in lines:
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10.5)

    doc.add_paragraph()


def add_x_post_box(doc, label, content, bg="EBF5FB"):
    """X投稿ボックス"""
    p = doc.add_paragraph()
    run = p.add_run(f"【{label}】")
    set_font(run, size_pt=10, bold=True, color=RGBColor(0x1D, 0xA1, 0xF2))

    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = 'Table Grid'
    cell = tbl.rows[0].cells[0]
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), bg)
    tcPr.append(shd)

    for line in content.strip().split('\n'):
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10.5)

    doc.add_paragraph()


def circle_num(n):
    """丸数字→番号テキスト変換"""
    return f"{n}番"


def fmt_wide(pairs):
    return " / ".join(f"{circle_num(a)}-{circle_num(b)}" for a, b in pairs)


def fmt_san_fuku(triples):
    return " / ".join(f"{circle_num(a)}-{circle_num(b)}-{circle_num(c)}" for a, b, c in triples)


# ────────────────────────────────────────────────────────
# メイン生成処理
# ────────────────────────────────────────────────────────

def build_race_section(doc, race_title, race_sub, horses, kaimoku, threads_text, note_text):
    """1レース分のセクション生成"""
    add_heading(doc, race_title, level=1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(race_sub)
    set_font(run, size_pt=10.5)
    doc.add_paragraph()

    # ──────────── X投稿① 予想発表 ────────────
    hon = horses["hon"]
    tai = horses["tai"]
    san = horses["san"]
    ana1 = horses["ana1"]
    ana2 = horses["ana2"]
    kesi = horses["kesi"]

    x1 = f"""🍱{race_title.split('（')[0]}

◎{circle_num(hon['no'])}{hon['name']}
○{circle_num(tai['no'])}{tai['name']}
▲{circle_num(san['no'])}{san['name']}
△{circle_num(ana1['no'])}{ana1['name']}
△{circle_num(ana2['no'])}{ana2['name']}

✕消し　{kesi['name']}（{kesi['reason']}）

AIが全頭スキャン！本命は{hon['name']}🔥

{get_hashtags(race_title)}"""
    add_x_post_box(doc, "X投稿① 予想発表", x1)

    # ──────────── X投稿② 本命の根拠 ────────────
    x2 = f"""📊 本命{circle_num(hon['no'])}{hon['name']}の推しポイント

① {hon['reason'][0]}
② {hon['reason'][1]}
③ {hon['reason'][2]}

✕{kesi['name']}　{kesi['reason']}笑

{get_hashtags(race_title)}"""
    add_x_post_box(doc, "X投稿② 本命の根拠", x2)

    # ──────────── X投稿③ 買い目 ────────────
    wide_str = fmt_wide(kaimoku["wide"])
    baren_str = fmt_wide(kaimoku["baren"])
    san_fuku_str = fmt_san_fuku(kaimoku["san_fuku"])

    x3 = f"""🎯{race_title.split('（')[0]} 買い目　予算1万円

💴 単勝　{circle_num(kaimoku['tansho'])}番：3,000円
🎫 ワイド　{wide_str}：各2,000円
🎰 馬連　{baren_str}：各1,000円
🎲 3連複　{san_fuku_str}：1,000円

◎{hon['name']}軸に妙味ある相手を狙います🎯

{get_hashtags(race_title)}"""
    add_x_post_box(doc, "X投稿③ 買い目", x3)

    # ──────────── Threads ────────────
    p = doc.add_paragraph()
    run = p.add_run("【Threads投稿（500字以内・1投稿）】")
    set_font(run, size_pt=10, bold=True, color=RGBColor(0x00, 0x00, 0x00))
    add_box(doc, None, threads_text.strip().split('\n'), bg_color="F0F0F0")

    # ──────────── Note記事 ────────────
    p = doc.add_paragraph()
    run = p.add_run("【Note記事（冒頭）】")
    set_font(run, size_pt=10, bold=True, color=RGBColor(0x00, 0x00, 0x00))
    add_box(doc, None, note_text.strip().split('\n'), bg_color="FAFAFA")

    doc.add_page_break()


def get_hashtags(race_title):
    if "マイラーズ" in race_title:
        return "#マイラーズカップ #競馬予想 #アスメシ競馬"
    elif "フローラ" in race_title:
        return "#フローラステークス #競馬予想 #アスメシ競馬"
    return "#競馬予想 #アスメシ競馬"


def build_threads_flora():
    return """🍱【フローラS G2】東京芝2000m 本日11R

◎5番 ラフターラインズ（1人気2.9倍）
○13番 エンネ（3人気6.8倍）
▲11番 ファムクラジューズ（4人気7.1倍）
△6番 ペンダント（9人気25.2倍）
△2番 ラベルセーヌ（2人気4.4倍）

AI全頭スキャン✅ 本命は上がり最速ラフターラインズ🔥
①上がり32.5秒メンバー最速②きさらぎ賞で上がり1位③東京2000mの末脚勝負で最適

⚠穴はペンダント（CL評価A・EV9.75倍）

💰単勝5番 ワイド5-13/5-6 馬連5-13/5-6

#フローラステークス #競馬予想 #アスメシ競馬"""


def build_threads_milers():
    return """🍱【マイラーズC G2】京都芝1600m 本日11R

◎9番 アドマイヤズーム（1人気3.6倍）
○12番 ファーヴェント（8人気17.2倍）
▲7番 ベラジオボンド（6人気11.2倍）
△10番 ウォーターリヒト（3人気5.4倍）
△2番 オフトレイル（2人気4.7倍）

AI全頭スキャン✅ 本命は武豊×テン最速アドマイヤズーム🔥
①テン337秒18頭中最速②武豊騎手×京都内回り③同コース1走1勝の適性

⚠対抗に超穴ファーヴェント（CL評価A・EV7.11倍）を抜擢！

💰単勝9番 ワイド9-12/9-7 馬連9-12/9-7

#マイラーズカップ #競馬予想 #アスメシ競馬"""


def build_note_flora():
    return """# フローラステークス2026【AI全頭予想】本命はラフターラインズ🌸

こんにちは！アスメシ競馬予想です😊
今日は東京競馬場「サンケイスポーツ賞フローラステークス（G2）」芝2000m のAI予想です！

---

## 予想印（AI能力スコア順）

| 印 | 馬番 | 馬名 | 能力スコア | 人気 |
|----|------|------|-----------|------|
| ◎ | 5番 | ラフターラインズ | 15.3% | 1人気 |
| ○ | 13番 | エンネ | 10.5% | 3人気 |
| ▲ | 11番 | ファムクラジューズ | 9.4% | 4人気 |
| △ | 6番 | ペンダント | 11.6% | 9人気 |
| △ | 2番 | ラベルセーヌ | 8.0% | 2人気 |

---

## ◎本命：5番 ラフターラインズ（1人気 2.9倍）

AIの能力スコアで堂々の1位（15.3%）。

前走きさらぎ賞では3着ながら上がり3F最速（32.8秒）を記録。
東京2000mは長い直線で末脚が活きるコース。
このメンバーで上がり最速の脚を持つ馬が勝つ展開になれば◎。
レーン騎手×小笠倫弘厩舎という最強タッグで戴冠を狙います！

---

## ○対抗：13番 エンネ（3人気 6.8倍）

前走1着・上がり最速1位の素質馬。
AIの市場確率66.1%はメンバー最高水準。
キャリアは浅いが外国人騎手ディー騎乗で大きな期待。
EV4.50倍という効率の良さも魅力。

---

## ▲三番手：11番 ファムクラジューズ（4人気 7.1倍）

テンポ349秒（メンバー最速#1）で先手を取れる逃げ馬。
フリージア賞1着からの参戦で勢いも十分。
横山武史騎手が積極的な騎乗を見せれば。

---

## △穴候補：6番 ペンダント（9人気 25.2倍）

CL評価A（最高格付け）、CR値13という高スペック。
前走8人気1着という実力上位の穴馬。
AIのEV値9.75倍はメンバー最高水準。3連複に絡む可能性大！

---

## 全頭診断

━━━━━━━━━━━━━━━━━
◎ 5番 ラフターラインズ
→ 能力1位・上がり最速の本命
━━━━━━━━━━━━━━━━━
○ 13番 エンネ
→ 市場確率最高・素質開花の対抗
━━━━━━━━━━━━━━━━━
▲ 11番 ファムクラジューズ
→ テン最速・連勝の勢いで押し切る
━━━━━━━━━━━━━━━━━
△ 6番 ペンダント（穴）
→ CL評価A・EV9.75倍の大穴候補
━━━━━━━━━━━━━━━━━
△ 2番 ラベルセーヌ
→ 2人気の支持・前走1着好内容
━━━━━━━━━━━━━━━━━
▼ 7番 リアライズルミナス
→ 前走1着だが能力6.5%は平凡
━━━━━━━━━━━━━━━━━
▼ 1番 リスレジャンデール
→ 能力7.6%も7人気は買いにくい
━━━━━━━━━━━━━━━━━
▼ 3番 サムシングスイート
→ 能力9.1%も前走上がり2位と堅実
━━━━━━━━━━━━━━━━━
消 8番 ゴバド
→ 前走クイーンC13着・大敗
━━━━━━━━━━━━━━━━━
消 12番 スタニングレディ
→ 阪神JF11着の経験だけでは不足
━━━━━━━━━━━━━━━━━

---

## 買い目（予算1万円）

- **単勝**：5番 3,000円
- **ワイド**：5-13 2,000円 / 5-6 2,000円
- **馬連**：5-13 1,000円 / 5-6 1,000円
- **3連複**：5-13-11 1,000円

オークストライアル、夢馬券を狙います🌸
今日もアスメシ競馬の予想を応援よろしくお願いします🙏"""


def build_note_milers():
    return """# 読売マイラーズカップ2026【AI全頭予想】本命は武豊アドマイヤズーム🏇

こんにちは！アスメシ競馬予想です😊
今日は京都競馬場「読売マイラーズカップ（G2）」芝1600m のAI予想です！

---

## 予想印（AI能力スコア順）

| 印 | 馬番 | 馬名 | 能力スコア | 人気 |
|----|------|------|-----------|------|
| ◎ | 9番 | アドマイヤズーム | 12.4% | 1人気 |
| ○ | 12番 | ファーヴェント | 12.0% | 8人気 |
| ▲ | 7番 | ベラジオボンド | 9.9% | 6人気 |
| △ | 10番 | ウォーターリヒト | 6.7% | 3人気 |
| △ | 2番 | オフトレイル | 7.3% | 2人気 |

---

## ◎本命：9番 アドマイヤズーム（1人気 3.6倍）

AIの能力スコアで1位（12.4%）。

テン337秒は18頭中断然最速。逃げ・先行脚質で京都内回りは絶好の舞台。
武豊騎手との初コンビで、同コース1走1勝の適性も示済み。
前走スワンSは6着と案外だったが、今日の京都内回りは条件が好転。
有力馬を引き離してそのまま押し切る展開を期待！

---

## ○対抗：12番 ファーヴェント（8人気 17.2倍）

本命との能力差わずか0.4%（12.0% vs 12.4%）の実力馬。
CL評価A（最高格付け）、EV7.11倍という超穴フラグが立っています。
前走ダービーCTで1人気3着という実力は本物。
同コース1走1勝の経験もプラス。8人気は明らかに過小評価！

---

## ▲三番手：7番 ベラジオボンド（6人気 11.2倍）

六甲S1着→新春S1着という2連勝の勢いが本物。
EV3.64倍という妙味も十分。
前走の1人気1着は圧巻のパフォーマンス。北村友一騎手の手綱さばきに注目。

---

## △注目馬①：10番 ウォーターリヒト（3人気 5.4倍）

京都芝1600m 2走2勝という完璧な適性データ。
このコースだけ別馬になると言っても過言ではない。
前走東京新聞杯3着の安定感も評価できる。

---

## △注目馬②：2番 オフトレイル（2人気 4.7倍）

上がり328秒はメンバー最速。前走は10着と大敗したが、
東京→京都の条件変わりで反撃の可能性。

---

## 全頭診断

━━━━━━━━━━━━━━━━━
◎ 9番 アドマイヤズーム
→ テン最速・武豊・能力1位の本命
━━━━━━━━━━━━━━━━━
○ 12番 ファーヴェント
→ CL評価A・EV7.11倍の超穴対抗
━━━━━━━━━━━━━━━━━
▲ 7番 ベラジオボンド
→ 2連勝の勢いと妙味で三番手
━━━━━━━━━━━━━━━━━
△ 10番 ウォーターリヒト
→ 同コース2走2勝の最強適性
━━━━━━━━━━━━━━━━━
△ 2番 オフトレイル
→ 上がり最速・2人気の意地
━━━━━━━━━━━━━━━━━
▼ 18番 ランスオブカオス
→ 能力5.0%・前走上がり14位
━━━━━━━━━━━━━━━━━
▼ 1番 ドラゴンブースト
→ 前走大阪城S1着も京都G2では格不足
━━━━━━━━━━━━━━━━━
消 16番 シックスペンス
→ 前走ダート（フェブラリーS）大敗・同コース0走
━━━━━━━━━━━━━━━━━
消 17番 エルトンバローズ
→ 前走東京新聞杯1人気13着の大惨敗
━━━━━━━━━━━━━━━━━
消 15番 マテンロウスカイ
→ 前走マーチS12着・ダート馬
━━━━━━━━━━━━━━━━━

---

## 買い目（予算1万円）

- **単勝**：9番 3,000円
- **ワイド**：9-12 2,000円 / 9-7 2,000円
- **馬連**：9-12 1,000円 / 9-7 1,000円
- **3連複**：9-12-7 1,000円

AIが強く推す穴対抗ファーヴェントとの組み合わせで
高配当を狙いにいきます🏇
今日もアスメシ競馬の予想を応援よろしくお願いします🙏"""


def main():
    doc = Document()

    # ── 表紙 ──
    doc.add_paragraph()
    add_heading(doc, "SNS投稿案【改訂版】2026/04/26（日）", level=1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("マイラーズカップ G2 ＆ フローラステークス G2")
    set_font(run, size_pt=12)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("AIモデル再予測 + 全頭データ詳細分析（当日最終版）")
    set_font(run, size_pt=10, color=RGBColor(0x88, 0x88, 0x88))
    doc.add_page_break()

    # ── マイラーズC ──
    add_heading(doc, "🏇 読売マイラーズカップ（G2）京都11R 芝1600m", level=2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("【主な変更点】▲をウォーターリヒト→消し、シックスペンスを消し追加（ダート帰り）、ファーヴェントを○に格上げ")
    set_font(run, size_pt=9, color=RGBColor(0xCC, 0x33, 0x33))
    doc.add_paragraph()

    build_race_section(
        doc,
        "読売マイラーズカップ（G2）",
        "京都競馬場 芝1600m 2026年4月26日（日）",
        MILERS_HORSES,
        MILERS_KAIMOKU,
        build_threads_milers(),
        build_note_milers(),
    )

    # ── フローラS ──
    add_heading(doc, "🌸 フローラステークス（G2）東京11R 芝2000m", level=2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("【主な変更点】▲をラベルセーヌ→ファムクラジューズに変更、ペンダントを△追加（CL評価A・EV9.75倍）")
    set_font(run, size_pt=9, color=RGBColor(0xCC, 0x33, 0x33))
    doc.add_paragraph()

    build_race_section(
        doc,
        "フローラステークス（G2）",
        "東京競馬場 芝2000m 2026年4月26日（日）",
        FLORA_HORSES,
        FLORA_KAIMOKU,
        build_threads_flora(),
        build_note_flora(),
    )

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
