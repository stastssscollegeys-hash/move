"""
2026/04/26 フローラS・マイラーズC 結果報告 SNS投稿案（X・Threads）
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
OUTPUT_PATH = OUTPUT_DIR / "20260426_結果報告_X_Threads.docx"


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


def add_section_bar(doc, text, color=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_font(run, size_pt=13, bold=True,
             color=color or RGBColor(0x0F, 0x47, 0x61))


# ════════════════════════════════════════
# 投稿文テキスト
# ════════════════════════════════════════

# ── 両レース合同 速報1本目（最初に出す）──
BOTH_FIRST = """🍱【本日G2 2レース 予想結果報告】2026/04/26

🌸フローラS（東京芝2000m）
◎5番 ラフターラインズ → 🥇1着 本命的中✅
○13番 エンネ → 🥈2着 対抗的中✅
単勝・馬連・ワイド W的中🎯

🏇マイラーズC（京都芝1600m）
◎9番 アドマイヤズーム → 🥇1着 本命的中✅
▲7番 ベラジオボンド → 🥉3着 三番手的中✅
単勝・ワイド 的中🎯

2レース連続で本命が1着！
AIの力を見せつけました🔥

#アスメシ競馬 #競馬予想 #的中報告"""

# ── フローラS 結果詳細 ──
FLORA_RESULT_X1 = """🌸【フローラS G2 結果】東京芝2000m

🥇1着 ラフターラインズ（1人気）◎本命
🥈2着 エンネ（3人気）○対抗
🥉3着 リアライズルミナス（5人気）

◎○完璧W的中✅

本命ラフターラインズは直線で一気に突き抜け
対抗エンネも2着死守！
レーン騎手が魅せてくれました😊

#フローラステークス #競馬 #アスメシ競馬"""

FLORA_RESULT_X2 = """🎯【フローラS 買い目結果】

✅ 単勝 5番　的中！
✅ ワイド 5-13　的中！
✅ 馬連 5-13　的中！
❌ ワイド 5-6（ペンダント着外）
❌ 3連複 5-13-11（3着は7番）

本命◎対抗○の1.2フィニッシュで
単勝・ワイド・馬連すべて的中🎯

2人気ラベルセーヌは5着で消し大正解👊

#フローラステークス #アスメシ競馬 #的中"""

FLORA_THREADS = """🌸【フローラS G2 結果報告】2026/04/26

🥇1着 ◎ラフターラインズ（1人気2.9倍）本命的中✅
🥈2着 ○エンネ（3人気6.8倍）対抗的中✅
🥉3着 リアライズルミナス（5人気）

◎○のW的中！単勝・馬連・ワイドすべて的中🎯

AIが予想したとおりラフターラインズが東京の長い直線を豪快に差し切り重賞初制覇。対抗エンネも2着でしっかり来てくれました！

馬連5-13・ワイド5-13が的中。2人気ラベルセーヌは5着で消し判断も大正解でした👊

次はオークス！引き続き応援よろしくお願いします🌸

#フローラステークス #アスメシ競馬 #AI競馬予想 #的中"""

# ── マイラーズC 結果詳細 ──
MILERS_RESULT_X1 = """🏇【マイラーズC G2 結果】京都芝1600m

🥇1着 アドマイヤズーム（1人気）◎本命
🥈2着 ドラゴンブースト（9人気）
🥉3着 ベラジオボンド（6人気）▲三番手

◎1着 ▲3着的中✅

武豊騎手がテンから逃げて完璧なレース！
単勝410円・ワイド900円しっかり的中🎯

2着が9人気ドラゴンブーストは想定外でしたが
本命と三番手は完璧でした😊

#マイラーズカップ #競馬 #アスメシ競馬"""

MILERS_RESULT_X2 = """🎯【マイラーズC 買い目結果】

✅ 単勝 9番（410円）的中！
✅ ワイド 9-7（900円）的中！
❌ ワイド 9-12（ファーヴェント着外）
❌ 馬連 9-7（2着は1番ドラゴンブースト）
❌ 3連複 9-12-7（2着が9人気）

2着に9人気ドラゴンブーストが突っ込んで
馬連・3連複は惜しくも外れ…

でも単勝3000円→12,300円回収✅
ワイド2000円→18,000円回収✅
合計30,300円回収（投資10,000円）🔥

#マイラーズカップ #アスメシ競馬 #的中"""

MILERS_THREADS = """🏇【マイラーズC G2 結果報告】2026/04/26

🥇1着 ◎アドマイヤズーム（1人気3.6倍）本命的中✅
🥈2着 ドラゴンブースト（9人気24.2倍）
🥉3着 ▲ベラジオボンド（6人気11.2倍）三番手的中✅

◎▲的中！単勝410円・ワイド900円を回収🎯

武豊騎手がテン337秒最速で先手を奪いそのまま押し切り。完璧な逃げ切りでした！

2着にまさかの9人気ドラゴンブーストが突っ込み馬連は惜しくも外れましたが…
単勝3,000円→12,300円・ワイド2,000円→18,000円で合計30,300円の回収✅
投資1万円に対して3倍超えの回収です🔥

4人気シックスペンス・5人気エルトンバローズを消しにした判断も大正解でした👊

#マイラーズカップ #アスメシ競馬 #AI競馬予想 #的中"""

# ── 総合まとめ（最後に出す）──
SUMMARY_X = """📊【本日のAI予想まとめ】2026/04/26

【フローラS G2 東京11R】
◎ラフターラインズ → 🥇1着 ✅
○エンネ → 🥈2着 ✅
的中：単勝・馬連・ワイド

【マイラーズC G2 京都11R】
◎アドマイヤズーム → 🥇1着 ✅
▲ベラジオボンド → 🥉3着 ✅
的中：単勝（410円）・ワイド（900円）

2レースとも本命1着！
AIが2重賞を的中させました🔥

総回収 推定55,000円〜（投資20,000円）
回収率270%超え💰

いつも応援ありがとうございます🙏
また来週もよろしくお願いします！

#アスメシ競馬 #AI競馬予想 #的中 #重賞的中"""

SUMMARY_THREADS = """📊【本日G2 2レース完全結果報告】2026/04/26

━━━━━━━━━━━━━━━
🌸 フローラS（東京芝2000m）
━━━━━━━━━━━━━━━
◎5番 ラフターラインズ → 🥇1着 本命的中✅
○13番 エンネ → 🥈2着 対抗的中✅
3着 リアライズルミナス（△なし）
単勝・馬連・ワイド 的中🎯

━━━━━━━━━━━━━━━
🏇 マイラーズC（京都芝1600m）
━━━━━━━━━━━━━━━
◎9番 アドマイヤズーム → 🥇1着 本命的中✅
▲7番 ベラジオボンド → 🥉3着 三番手的中✅
2着 ドラゴンブースト（9人気・ノーマーク）
単勝410円・ワイド900円 的中🎯

━━━━━━━━━━━━━━━
G2 2レース連続本命1着！
推定回収率270%超🔥

消し判断：シックスペンス・エルトンバローズ（マイラーズC）、ゴバド・ラベルセーヌ（フローラS）も全部正解でした👊

今日もご覧いただきありがとうございます！
来週もAI予想でガチ勝負します💪

#アスメシ競馬 #AI競馬予想 #重賞的中 #フローラステークス #マイラーズカップ"""


# ════════════════════════════════════════
# Word生成
# ════════════════════════════════════════

def main():
    doc = Document()

    # 表紙
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("結果報告 SNS投稿案（X・Threads）")
    set_font(run, size_pt=15, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026/04/26（日）フローラS G2 ／ マイラーズC G2　両重賞本命的中記念")
    set_font(run, size_pt=10, color=RGBColor(0xCC, 0x44, 0x00))
    doc.add_paragraph()

    # ════ 速報（最初に投稿） ════
    add_section_bar(doc, "━━━ 🔔 速報（レース直後・最初に投稿） ━━━",
                    RGBColor(0xCC, 0x33, 0x33))
    doc.add_paragraph()
    add_label(doc, "【X投稿 / Threads共通 ── 速報1本目】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, BOTH_FIRST.split('\n'), "FFF3E0")

    doc.add_page_break()

    # ════ フローラS ════
    add_section_bar(doc, "━━━ 🌸 フローラステークス 結果詳細 ━━━")
    doc.add_paragraph()

    add_label(doc, "【X投稿① フローラS 結果】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, FLORA_RESULT_X1.split('\n'), "EBF5FB")

    add_label(doc, "【X投稿② フローラS 買い目結果】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, FLORA_RESULT_X2.split('\n'), "EBF5FB")

    add_label(doc, "【Threads フローラS 結果（500字以内）】", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, FLORA_THREADS.split('\n'), "F0F0F0")

    doc.add_page_break()

    # ════ マイラーズC ════
    add_section_bar(doc, "━━━ 🏇 マイラーズカップ 結果詳細 ━━━")
    doc.add_paragraph()

    add_label(doc, "【X投稿① マイラーズC 結果】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, MILERS_RESULT_X1.split('\n'), "EBF5FB")

    add_label(doc, "【X投稿② マイラーズC 買い目結果】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, MILERS_RESULT_X2.split('\n'), "EBF5FB")

    add_label(doc, "【Threads マイラーズC 結果（500字以内）】", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, MILERS_THREADS.split('\n'), "F0F0F0")

    doc.add_page_break()

    # ════ 総合まとめ（最後に投稿） ════
    add_section_bar(doc, "━━━ 📊 総合まとめ（最後に投稿） ━━━",
                    RGBColor(0x0F, 0x47, 0x61))
    doc.add_paragraph()

    add_label(doc, "【X投稿 総合まとめ】", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, SUMMARY_X.split('\n'), "EBF5FB")

    add_label(doc, "【Threads 総合まとめ（500字以内）】", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, SUMMARY_THREADS.split('\n'), "F0F0F0")

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
