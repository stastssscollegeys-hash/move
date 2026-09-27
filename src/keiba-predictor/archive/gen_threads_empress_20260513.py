# -*- coding: utf-8 -*-
"""エンプレス杯 Threads投稿案 Word出力"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

OUTPUT_PATH = r"C:\Users\User\Desktop\競馬予想レポート\20260513\Threads投稿案_エンプレス杯_20260513.docx"

def add_heading(doc, text, level=1, color=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.bold = True
    if level == 1:
        run.font.size = Pt(16)
    elif level == 2:
        run.font.size = Pt(13)
    else:
        run.font.size = Pt(11)
    if color:
        run.font.color.rgb = RGBColor(*color)
    return p

def add_body(doc, text, bold=False, size=10.5):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    return p

def add_separator(doc):
    p = doc.add_paragraph("─" * 40)
    p.runs[0].font.size = Pt(9)
    p.runs[0].font.color.rgb = RGBColor(180, 180, 180)

def main():
    doc = Document()

    # ページ余白
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # タイトル
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Threads投稿案｜エンプレス杯キヨフジ記念 2026")
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub.add_run("2026年5月13日（火）川崎競馬 11R 20:10発走　JpnII ダート2100m")
    sr.font.size = Pt(10)
    sr.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()

    # ===== 投稿① =====
    add_separator(doc)
    add_heading(doc, "【投稿①】フック・レース紹介", level=2, color=(0x1E, 0x3A, 0x8A))
    add_separator(doc)
    doc.add_paragraph()

    post1 = doc.add_paragraph()
    post1.add_run(
        "🏇 本日20:10発走【エンプレス杯キヨフジ記念】JpnII\n\n"
        "川崎ダート2100m 牝馬頂上決戦🔥\n\n"
        "去年の女王・テンカジョウが\n"
        "2連覇に挑む一戦👑\n\n"
        "ルメール×メモリアカフェ\n"
        "武豊×プロミストジーン\n\n"
        "豪華メンバーが集結した\n"
        "今年最初の牝馬ダートG2！\n\n"
        "予想と買い目、スクロールで公開👇\n\n"
        "#エンプレス杯 #川崎競馬 #地方競馬"
    ).font.size = Pt(11)

    note1 = doc.add_paragraph()
    nr1 = note1.add_run("📌 目安文字数：約180字　目的：興味を引く・レース情報提示")
    nr1.font.size = Pt(9)
    nr1.font.color.rgb = RGBColor(130, 130, 130)
    nr1.italic = True

    doc.add_paragraph()

    # ===== 投稿② =====
    add_separator(doc)
    add_heading(doc, "【投稿②】全頭診断・予想印", level=2, color=(0x1E, 0x3A, 0x8A))
    add_separator(doc)
    doc.add_paragraph()

    post2 = doc.add_paragraph()
    post2.add_run(
        "📊 アスメシ式 全頭診断\n\n"
        "◎ ⑥テンカジョウ（松山弘平）\n"
        "→ 昨年優勝馬。川崎2100mを\n"
        "　 2周目向正面から早め先頭\n"
        "　 牝馬限定戦では崩れ知らず\n"
        "　 雨馬場もプラス材料💪\n\n"
        "○ ①メモリアカフェ（C.ルメール）\n"
        "→ 関東オークス5馬身差圧勝\n"
        "　 調教でB評価の好タイム\n"
        "　 ルメール継続でコース熟知✨\n\n"
        "▲ ④アピーリングルック（戸崎圭太）\n"
        "→ ブラジルC（川崎2100m）勝利\n"
        "　 4枠は過去10年複勝率50%👀\n"
        "　 戸崎への手替わりが強化要素\n\n"
        "△ ②プロミストジーン（武豊）\n"
        "→ 先行力で展開を作れる\n"
        "　 「距離はもっと長くていい」\n"
        "　 武豊コメントで適性◎\n\n"
        "#エンプレス杯予想 #アスメシ式"
    ).font.size = Pt(11)

    note2 = doc.add_paragraph()
    nr2 = note2.add_run("📌 目安文字数：約220字　目的：専門性・信頼感の演出")
    nr2.font.size = Pt(9)
    nr2.font.color.rgb = RGBColor(130, 130, 130)
    nr2.italic = True

    doc.add_paragraph()

    # ===== 投稿③ =====
    add_separator(doc)
    add_heading(doc, "【投稿③】買い目公開", level=2, color=(0x1E, 0x3A, 0x8A))
    add_separator(doc)
    doc.add_paragraph()

    post3 = doc.add_paragraph()
    post3.add_run(
        "💰 本日の買い目（予算2,000円）\n\n"
        "【3連単フォーメーション】\n\n"
        "▶本線（200円×4通り）\n"
        "　⑥→①→④\n"
        "　⑥→①→②\n"
        "　⑥→④→①\n"
        "　⑥→④→②\n\n"
        "▶穴流し（100円×6通り）\n"
        "　⑥→①→⑤　⑥→①→⑧\n"
        "　⑥→④→⑤　⑥→④→⑧\n"
        "　⑥→②→①　⑥→②→④\n\n"
        "▶逆転カバー（600円）\n"
        "　①→⑥→④（200円）\n"
        "　①→④→⑥ / ①→⑥→②（各100円）\n"
        "　④→⑥→① / ④→①→⑥（各100円）\n\n"
        "🎯 本命決着で回収率350%\n"
        "💥 プロミストジーン絡みで500%超\n"
        "🔥 穴馬絡みで1,000%超も視野！\n\n"
        "合計：2,000円\n\n"
        "#馬券 #競馬予想 #エンプレス杯"
    ).font.size = Pt(11)

    note3 = doc.add_paragraph()
    nr3 = note3.add_run("📌 目安文字数：約250字　目的：具体的行動の喚起")
    nr3.font.size = Pt(9)
    nr3.font.color.rgb = RGBColor(130, 130, 130)
    nr3.italic = True

    doc.add_paragraph()

    # ===== 投稿④ =====
    add_separator(doc)
    add_heading(doc, "【投稿④】レース直前・馬場情報", level=2, color=(0x1E, 0x3A, 0x8A))
    add_separator(doc)
    doc.add_paragraph()

    post4 = doc.add_paragraph()
    post4.add_run(
        "⚠️ 馬場注意情報\n\n"
        "川崎競馬場、夕方から雨の予報☔\n\n"
        "20:10発走のメインまでに\n"
        "【重〜不良】になる可能性あり\n\n"
        "→ テンカジョウは重馬場OK✅\n"
        "→ メモリアカフェは道悪が課題⚡\n\n"
        "不良馬場確定なら\n"
        "プロミストジーン(武豊)の\n"
        "先行粘り込みに注目👀\n\n"
        "最終オッズ確認してから判断を！\n\n"
        "20時10分、川崎に注目🏇✨\n\n"
        "#川崎競馬 #エンプレス杯2026\n"
        "#地方競馬 #競馬好きと繋がりたい"
    ).font.size = Pt(11)

    note4 = doc.add_paragraph()
    nr4 = note4.add_run("📌 目安文字数：約180字　目的：リアルタイム感・再拡散狙い")
    nr4.font.size = Pt(9)
    nr4.font.color.rgb = RGBColor(130, 130, 130)
    nr4.italic = True

    doc.add_paragraph()

    # ===== 出走馬参考表 =====
    add_separator(doc)
    add_heading(doc, "【参考】出走馬一覧", level=2, color=(0x4B, 0x5E, 0x6F))
    add_separator(doc)
    doc.add_paragraph()

    table = doc.add_table(rows=9, cols=5)
    table.style = "Table Grid"

    headers = ["馬番", "馬名", "騎手", "オッズ", "予想印"]
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(9)

    horses = [
        ("①", "メモリアカフェ", "C.ルメール", "3.8倍", "○"),
        ("②", "プロミストジーン", "武豊", "7.7倍", "△"),
        ("③", "マテリアルガール", "矢野貴之", "108.4倍", "×"),
        ("④", "アピーリングルック", "戸崎圭太", "3.0倍", "▲"),
        ("⑤", "マーブルマウンテン", "吉原寛人", "31.2倍", "紐"),
        ("⑥", "テンカジョウ", "松山弘平", "2.2倍", "◎"),
        ("⑦", "レクランスリール", "丸山真一", "285.8倍", "×"),
        ("⑧", "レイナデアルシーラ", "田口貫太", "18.9倍", "紐"),
    ]

    for row_idx, horse in enumerate(horses, start=1):
        for col_idx, val in enumerate(horse):
            cell = table.rows[row_idx].cells[col_idx]
            cell.text = val
            run = cell.paragraphs[0].runs[0]
            run.font.size = Pt(9)
            if col_idx == 4 and val == "◎":
                run.bold = True
                run.font.color.rgb = RGBColor(0xE7, 0x4C, 0x3C)

    doc.add_paragraph()

    # フッター
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("アスメシ式 競馬予想　2026年5月13日　川崎競馬 エンプレス杯キヨフジ記念")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(150, 150, 150)

    doc.save(OUTPUT_PATH)
    print(f"OK: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
