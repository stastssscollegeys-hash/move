# -*- coding: utf-8 -*-
"""エンプレス杯 Threads振り返り投稿案 Word出力"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUTPUT_PATH = r"C:\Users\User\Desktop\競馬予想レポート\20260513\Threads振り返り投稿案_エンプレス杯_20260513.docx"

C_TITLE  = RGBColor(0x1A, 0x1A, 0x2E)
C_HEAD   = RGBColor(0x1E, 0x3A, 0x8A)
C_RED    = RGBColor(0xE7, 0x4C, 0x3C)
C_GREEN  = RGBColor(0x27, 0xAE, 0x60)
C_GRAY   = RGBColor(0x95, 0x96, 0x97)
C_ORANGE = RGBColor(0xE6, 0x7E, 0x22)
C_GOLD   = RGBColor(0xF3, 0x9C, 0x12)


def add_sep(doc):
    p = doc.add_paragraph("━" * 38)
    r = p.runs[0]
    r.font.size = Pt(8)
    r.font.color.rgb = C_GRAY


def h(doc, text, size=13, color=C_HEAD, bold=True):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return p


def note(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(f"📌 {text}")
    r.font.size = Pt(8.5)
    r.font.color.rgb = C_GRAY
    r.italic = True


def shade_row(row, hex_color="E8F4FD"):
    for cell in row.cells:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)


def main():
    doc = Document()
    for sec in doc.sections:
        sec.top_margin    = Cm(2)
        sec.bottom_margin = Cm(2)
        sec.left_margin   = Cm(2.5)
        sec.right_margin  = Cm(2.5)

    # タイトル
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Threads振り返り投稿案｜エンプレス杯キヨフジ記念 2026")
    r.bold = True; r.font.size = Pt(18); r.font.color.rgb = C_TITLE

    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = s.add_run("2026年5月13日（火）川崎競馬 11R　JpnII ダート2100m 良馬場　タイム 2:16.1")
    sr.font.size = Pt(9); sr.font.color.rgb = C_GRAY
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿① レース結果速報
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿①】レース結果速報", color=C_RED)
    add_sep(doc)
    doc.add_paragraph()

    p1 = doc.add_paragraph()
    r1 = p1.add_run(
        "🏁 エンプレス杯 結果速報！\n\n"
        "川崎ダート2100m 良馬場\n"
        "タイム 2:16.1\n\n"
        "🥇 1着 ①メモリアカフェ\n"
        "　　C.ルメール騎手\n"
        "　　後方から鮮やかな差し切り!\n\n"
        "🥈 2着 ⑥テンカジョウ\n"
        "　　松山弘平騎手（1馬身差）\n"
        "　　直線先頭から惜しくも捕まる\n\n"
        "🥉 3着 ⑧レイナデアルシーラ\n"
        "　　田口貫太騎手\n"
        "　　18.9倍の穴馬が3着激走！\n\n"
        "4着 ②プロミストジーン（武豊）\n"
        "5着 ④アピーリングルック（戸崎圭太）\n\n"
        "#エンプレス杯 #川崎競馬 #競馬結果"
    )
    r1.font.size = Pt(11)

    note(doc, "目安：約200字　目的：速報フォーマットで拡散狙い")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿② 予想振り返り
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿②】予想の振り返り", color=C_HEAD)
    add_sep(doc)
    doc.add_paragraph()

    p2 = doc.add_paragraph()
    r2 = p2.add_run(
        "📊 アスメシ式 予想振り返り\n\n"
        "◎⑥テンカジョウ → 2着\n"
        "　直線で先頭に立つも\n"
        "　外からメモリアカフェに差し切られた\n"
        "　本命は2着と健闘🙏\n\n"
        "○①メモリアカフェ → 1着🎯\n"
        "　馬体重+4kgを「やや太め」と見たが\n"
        "　ルメールが後方から完璧な差し切り\n"
        "　予想3番手が結果1番手に!\n\n"
        "▲④アピーリングルック → 5着✗\n"
        "　-5kgで仕上がり良好とみたが撃沈\n"
        "　道中のポジションが取れなかった\n\n"
        "△⑧レイナデアルシーラ → 3着🎯\n"
        "　18.9倍の穴馬が3連複を演出\n"
        "　押さえて正解だった!\n\n"
        "△②プロミストジーン → 4着\n"
        "　良馬場で先行力が活かしきれず\n\n"
        "#予想振り返り #エンプレス杯2026"
    )
    r2.font.size = Pt(11)

    note(doc, "目安：約260字　目的：予想の正直な自己分析・信頼感の構築")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿③ 馬券結果・収支報告
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿③】馬券結果・収支報告", color=C_GREEN)
    add_sep(doc)
    doc.add_paragraph()

    p3 = doc.add_paragraph()
    r3 = p3.add_run(
        "💰 馬券結果 収支報告\n\n"
        "┌─────────────────────┐\n"
        "│  投資 5,000円 → 回収 5,910円   │\n"
        "│       回収率 118%               │\n"
        "└─────────────────────┘\n\n"
        "━━━━ ✅ 的中3通り ━━━━\n\n"
        "【ワイド ①-⑥】\n"
        "　投資 400円 → 払戻 520円\n"
        "　（130円 × 4口）\n\n"
        "【馬連 ①-⑥】\n"
        "　投資 500円 → 払戻 1,250円\n"
        "　（250円 × 5口）\n\n"
        "【3連複 ①-⑥-⑧】\n"
        "　投資 300円 → 払戻 4,140円\n"
        "　（1,380円 × 3口）\n"
        "　穴馬⑧レイナデアルシーラが3着!\n\n"
        "━━━━ ❌ 外れ ━━━━\n"
        "単勝⑥② / 馬連②⑥・④⑥\n"
        "3連複①④⑥ など計11通り\n"
        "→ ④アピーリングルック5着で芋づる外れ\n\n"
        "💡 3連単①-⑥-⑧は5,190円の高配当\n"
        "　 次回は3連単も視野に入れる!\n\n"
        "#馬券結果 #エンプレス杯 #競馬収支"
    )
    r3.font.size = Pt(11)

    note(doc, "目安：約270字　目的：正確な収支開示・次回への教訓")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿④ 今後への学び・総括
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿④】総括・今後への学び", color=C_GOLD)
    add_sep(doc)
    doc.add_paragraph()

    p4 = doc.add_paragraph()
    r4 = p4.add_run(
        "📝 エンプレス杯 総括\n\n"
        "✅ 良かった点\n"
        "・⑧レイナデアルシーラ（18.9倍）を\n"
        "　 △で押さえていた\n"
        "　 →3連複①-⑥-⑧が的中！\n"
        "・馬連・ワイドの軸①-⑥を\n"
        "　 きちんと買えていた\n"
        "・3連複フォーメーションで\n"
        "　 穴の組み合わせをカバーできた\n\n"
        "❌ 反省点\n"
        "・◎テンカジョウが1着と判断したが\n"
        "　 メモリアカフェに差し切られた\n"
        "　 →「良馬場なら軸候補」の評価を\n"
        "　 　印に正直に反映すべきだった\n"
        "・馬体重+4kgを「太め」と減点したが\n"
        "　 ルメールが完璧に乗りこなした\n"
        "　 →体重増加の判断は慎重に\n"
        "・▲アピーリングルックへの資金が\n"
        "　 多すぎた（-5kg過信）\n\n"
        "次走はヴィクトリアマイルへ→続報待て！\n\n"
        "#競馬 #反省 #エンプレス杯2026"
    )
    r4.font.size = Pt(11)

    note(doc, "目安：約280字　目的：学びの共有・次走へのつなぎ")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 着順結果テーブル
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【参考】最終着順・予想印との照合", size=12, color=C_TITLE)
    add_sep(doc)
    doc.add_paragraph()

    rtbl = doc.add_table(rows=9, cols=6)
    rtbl.style = "Table Grid"
    rheaders = ["着順", "馬番", "馬名", "騎手", "予想印", "結果"]
    for i, hh in enumerate(rheaders):
        c = rtbl.rows[0].cells[i]
        c.text = hh
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
    shade_row(rtbl.rows[0], "1E3A8A")
    for cell in rtbl.rows[0].cells:
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    results = [
        ("1着", "①", "メモリアカフェ",    "C.ルメール", "○", "🎯 1着"),
        ("2着", "⑥", "テンカジョウ",      "松山弘平",   "◎", "惜2着"),
        ("3着", "⑧", "レイナデアルシーラ","田口貫太",   "△", "🎯 穴3着"),
        ("4着", "②", "プロミストジーン",  "武豊",       "△", "4着"),
        ("5着", "④", "アピーリングルック","戸崎圭太",   "▲", "✗ 5着"),
        ("6着", "③", "マテリアルガール",  "矢野貴之",   "×", "6着"),
        ("7着", "⑤", "マーブルマウンテン","吉原寛人",   "紐", "7着"),
        ("8着", "⑦", "レクランスリール",  "丸山真一",   "×", "8着"),
    ]

    hit_color = RGBColor(0x27, 0xAE, 0x60)
    miss_color = RGBColor(0xE7, 0x4C, 0x3C)
    mark_colors = {"◎": C_RED, "○": C_HEAD, "▲": C_ORANGE, "△": C_GREEN}

    for ri, row_data in enumerate(results, start=1):
        row = rtbl.rows[ri]
        for ci, val in enumerate(row_data):
            cell = row.cells[ci]
            cell.text = val
            run = cell.paragraphs[0].runs[0]
            run.font.size = Pt(9)
            if ci == 4 and val in mark_colors:
                run.bold = True
                run.font.color.rgb = mark_colors[val]
            if ci == 5:
                if "🎯" in val:
                    run.bold = True
                    run.font.color.rgb = hit_color
                elif "✗" in val:
                    run.font.color.rgb = miss_color
        if ri in [1, 2, 3]:  # 1〜3着行を強調
            shade_row(row, "F0FFF4")
        elif ri % 2 == 0:
            shade_row(row, "FFF8F0")

    doc.add_paragraph()

    # 馬券的中まとめ
    add_sep(doc)
    h(doc, "【参考】馬券的中まとめ", size=12, color=C_TITLE)
    add_sep(doc)
    doc.add_paragraph()

    btbl = doc.add_table(rows=9, cols=5)
    btbl.style = "Table Grid"
    bheaders = ["馬券種", "組み合わせ", "投資額", "結果", "払戻 / 差引"]
    for i, hh in enumerate(bheaders):
        c = btbl.rows[0].cells[i]
        c.text = hh
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
    shade_row(btbl.rows[0], "1E3A8A")
    for cell in btbl.rows[0].cells:
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    bets = [
        ("単勝",   "⑥テンカジョウ",   "300円", "✗ 外れ",  "2着 / -300円"),
        ("単勝",   "②プロミストジーン","300円", "✗ 外れ",  "4着 / -300円"),
        ("ワイド", "①-⑥",            "400円", "✅ 的中",  "→ 520円 (+120円)"),
        ("ワイド", "②-⑥",            "400円", "✗ 外れ",  "②4着 / -400円"),
        ("馬連",   "①-⑥",            "500円", "✅ 的中",  "→ 1,250円 (+750円)"),
        ("馬連",   "②-⑥",            "500円", "✗ 外れ",  "②4着 / -500円"),
        ("3連複",  "①-⑥-⑧",         "300円", "✅ 的中",  "→ 4,140円 (+3,840円)"),
    ]

    for ri, bet in enumerate(bets, start=1):
        row = btbl.rows[ri]
        for ci, val in enumerate(bet):
            cell = row.cells[ci]
            cell.text = val
            run = cell.paragraphs[0].runs[0]
            run.font.size = Pt(9)
            if ci == 3:
                if "✅" in val:
                    run.bold = True
                    run.font.color.rgb = hit_color
                elif "✗" in val:
                    run.font.color.rgb = miss_color
            if ci == 4 and "✅" in bet[3]:
                run.bold = True
                run.font.color.rgb = hit_color
        if "✅" in bet[3]:
            shade_row(row, "F0FFF4")

    # 合計行
    total_row = btbl.rows[8]
    total_data = ["合計", "14通り", "5,000円", "的中3通り", "回収 5,910円（118%）"]
    for ci, val in enumerate(total_data):
        cell = total_row.cells[ci]
        cell.text = val
        run = cell.paragraphs[0].runs[0]
        run.font.size = Pt(9)
        run.bold = True
        if ci == 4:
            run.font.color.rgb = hit_color
    shade_row(total_row, "E8F8E8")

    doc.add_paragraph()

    # フッター
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = foot.add_run(
        "アスメシ式 競馬予想　2026年5月13日　川崎競馬 エンプレス杯キヨフジ記念　振り返りレポート\n"
        "※払戻金は確認中。最終値は公式サイトをご確認ください。"
    )
    fr.font.size = Pt(8)
    fr.font.color.rgb = C_GRAY

    doc.save(OUTPUT_PATH)
    print(f"OK: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
