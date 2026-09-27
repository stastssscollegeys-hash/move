"""
2026/04/26 フローラS・マイラーズC
X投稿 + Threads のみ生成（改訂最終版）
"""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260426")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "20260426_X_Threads.docx"


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


def add_label(doc, text, color):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_font(run, size_pt=10, bold=True, color=color)


def add_box(doc, lines, bg_color):
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
    for line in lines:
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10.5)
    doc.add_paragraph()


def add_section_bar(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_font(run, size_pt=13, bold=True, color=RGBColor(0x0F, 0x47, 0x61))


# ────────────────────────────────────────────
# マイラーズC 投稿文
# ────────────────────────────────────────────

MILERS_X1 = """🍱【読売マイラーズC G2】京都芝1600m

◎9番 アドマイヤズーム
○12番 ファーヴェント
▲7番 ベラジオボンド
△10番 ウォーターリヒト
△2番 オフトレイル

✕消し シックスペンス（前走ダート大敗・同コース0走）
✕消し エルトンバローズ（前走1人気13着惨敗）

武豊×テン最速でそのまま押し切り！🔥

#マイラーズカップ #競馬予想 #アスメシ競馬"""

MILERS_X2 = """📊 本命⑨アドマイヤズームの推しポイント

① テン337秒（18頭中断然最速）
② 武豊騎手×京都内回りの黄金コンビ
③ 同コース1走1勝の適性証明済み

⚠超注目：対抗⑫ファーヴェント（8人気17.2倍）
→ CL評価A・AI市場確率41%・EV7.1倍
→ 能力差わずか0.4%の実力は本命並み！

✕シックスペンス 前走フェブラリーS（ダート）帰り笑

#マイラーズカップ #競馬予想"""

MILERS_X3 = """🎯 マイラーズC 買い目　予算1万円

💴 単勝　9番：3,000円
🎫 ワイド　9-12 / 9-7：各2,000円
🎰 馬連　9-12 / 9-7：各1,000円
🎲 3連複　9-12-7：1,000円

◎武豊×本命軸に
○穴ファーヴェント（8人気）を狙って
高配当を取りにいきます🏇

#マイラーズカップ #競馬 #アスメシ競馬"""

MILERS_THREADS = """🍱【マイラーズC G2】京都芝1600m 本日11R

◎9番 アドマイヤズーム（1人気3.6倍）
○12番 ファーヴェント（8人気17.2倍）
▲7番 ベラジオボンド（6人気11.2倍）
△10番 ウォーターリヒト（3人気5.4倍）
△2番 オフトレイル（2人気4.7倍）

AI全頭スキャン✅ 本命は武豊×テン最速アドマイヤズーム🔥
①テン337秒18頭中最速 ②武豊×京都内回り ③同コース1走1勝

⚠対抗は8人気ファーヴェント！CL評価A・EV7.1倍の超穴🔥

✕シックスペンス（ダート帰り）✕エルトンバローズ（前走大惨敗）

💰単勝9番 ワイド9-12/9-7 馬連9-12/9-7

#マイラーズカップ #競馬予想 #アスメシ競馬"""

# ────────────────────────────────────────────
# フローラS 投稿文
# ────────────────────────────────────────────

FLORA_X1 = """🌸【フローラS G2】東京芝2000m

◎5番 ラフターラインズ
○13番 エンネ
▲11番 ファムクラジューズ
△6番 ペンダント
△2番 ラベルセーヌ

✕消し ゴバド（前走クイーンC13着大敗）

末脚最速ラフターラインズで東京直線を差し切る！✨

#フローラステークス #競馬予想 #アスメシ競馬"""

FLORA_X2 = """📊 本命⑤ラフターラインズの推しポイント

① 上がり3F 32.5秒（メンバー最速）
② きさらぎ賞でも上がり1位の末脚
③ 東京2000mの長い直線が最適舞台

⚠超注目：△⑥ペンダント（9人気25.2倍）
→ CL評価A・EV9.75倍の大穴フラグ！
→ 前走8人気1着の逆転実績あり

▲⑪ファムクラジューズもテン最速で面白い

✕ゴバド 前走クイーンC13着笑

#フローラステークス #競馬予想"""

FLORA_X3 = """🎯 フローラS 買い目　予算1万円

💴 単勝　5番：3,000円
🎫 ワイド　5-13 / 5-6：各2,000円
🎰 馬連　5-13 / 5-6：各1,000円
🎲 3連複　5-13-11：1,000円

◎ラフターラインズ軸に
○エンネ・△穴ペンダントで
オークストライアルの夢馬券を🌸

#フローラステークス #競馬 #アスメシ競馬"""

FLORA_THREADS = """🍱【フローラS G2】東京芝2000m 本日11R

◎5番 ラフターラインズ（1人気2.9倍）
○13番 エンネ（3人気6.8倍）
▲11番 ファムクラジューズ（4人気7.1倍）
△6番 ペンダント（9人気25.2倍）
△2番 ラベルセーヌ（2人気4.4倍）

AI全頭スキャン✅ 本命は上がり最速ラフターラインズ🔥
①上がり32.5秒メンバー最速 ②きさらぎ賞上がり1位 ③東京直線向きの末脚

⚠穴はペンダント（9人気）！CL評価A・EV9.75倍🔥
前走8人気1着の逆転実績あり

✕ゴバド（前走クイーンC13着大敗）

💰単勝5番 ワイド5-13/5-6 馬連5-13/5-6

#フローラステークス #競馬予想 #アスメシ競馬"""


# ────────────────────────────────────────────
# 生成
# ────────────────────────────────────────────

def main():
    doc = Document()

    # 表紙見出し
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("SNS投稿案（X・Threads）2026/04/26")
    set_font(run, size_pt=15, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("マイラーズカップ G2 ／ フローラステークス G2　AI改訂最終版")
    set_font(run, size_pt=10, color=RGBColor(0x88, 0x88, 0x88))

    doc.add_paragraph()

    # ════════════ マイラーズC ════════════
    add_section_bar(doc, "━━━━━ 🏇 読売マイラーズカップ（G2）京都11R 芝1600m ━━━━━")
    doc.add_paragraph()

    add_label(doc, "【X投稿① 予想発表】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, MILERS_X1.split('\n'), "EBF5FB")

    add_label(doc, "【X投稿② 本命の根拠】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, MILERS_X2.split('\n'), "EBF5FB")

    add_label(doc, "【X投稿③ 買い目】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, MILERS_X3.split('\n'), "EBF5FB")

    add_label(doc, "【Threads（500字以内・1投稿）】", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, MILERS_THREADS.split('\n'), "F0F0F0")

    doc.add_page_break()

    # ════════════ フローラS ════════════
    add_section_bar(doc, "━━━━━ 🌸 フローラステークス（G2）東京11R 芝2000m ━━━━━")
    doc.add_paragraph()

    add_label(doc, "【X投稿① 予想発表】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, FLORA_X1.split('\n'), "EBF5FB")

    add_label(doc, "【X投稿② 本命の根拠】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, FLORA_X2.split('\n'), "EBF5FB")

    add_label(doc, "【X投稿③ 買い目】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, FLORA_X3.split('\n'), "EBF5FB")

    add_label(doc, "【Threads（500字以内・1投稿）】", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, FLORA_THREADS.split('\n'), "F0F0F0")

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
