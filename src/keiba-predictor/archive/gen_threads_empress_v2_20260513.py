# -*- coding: utf-8 -*-
"""エンプレス杯 Threads投稿案 v2（データ分析・穴馬中心）Word出力"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUTPUT_PATH = r"C:\Users\User\Desktop\競馬予想レポート\20260513\Threads投稿案_エンプレス杯_v2_20260513.docx"

# ─── カラー定義 ───
C_TITLE   = RGBColor(0x1A, 0x1A, 0x2E)  # 紺
C_HEAD    = RGBColor(0x1E, 0x3A, 0x8A)  # 青
C_RED     = RGBColor(0xE7, 0x4C, 0x3C)  # 赤（本命）
C_GREEN   = RGBColor(0x27, 0xAE, 0x60)  # 緑（穴）
C_GRAY    = RGBColor(0x95, 0x96, 0x97)  # グレー（注釈）
C_ORANGE  = RGBColor(0xE6, 0x7E, 0x22)  # オレンジ（警告・注意）


def add_sep(doc, color=C_GRAY):
    p = doc.add_paragraph("━" * 38)
    r = p.runs[0]
    r.font.size = Pt(8)
    r.font.color.rgb = color


def h(doc, text, size=13, color=C_HEAD, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = doc.add_paragraph()
    p.alignment = align
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return p


def body(doc, text, size=10.5, bold=False, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    if color:
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

    # ══════════════════════════════════════
    # タイトル
    # ══════════════════════════════════════
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Threads投稿案｜エンプレス杯キヨフジ記念 2026")
    r.bold = True; r.font.size = Pt(18); r.font.color.rgb = C_TITLE

    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = s.add_run("2026年5月13日（火）川崎競馬 11R 20:10発走　JpnII ダート2100m　牝馬定量55kg　8頭立て")
    sr.font.size = Pt(9); sr.font.color.rgb = C_GRAY

    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿① レースの特徴・傾向データ
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿①】レースの特徴・傾向データ", size=13, color=C_HEAD)
    add_sep(doc)
    doc.add_paragraph()

    p1 = doc.add_paragraph()
    r1 = p1.add_run(
        "🏇 エンプレス杯【最終見解】\n\n"
        "⛅ 天気：晴れのち雨\n"
        "🟢 馬場：現在ダート【良】\n"
        "⚠️ 18〜24時 降水確率60%・雷注意報\n"
        "　 20:10発走時に稍重〜重の懸念あり\n\n"
        "📊 馬体重 注目ポイント\n"
        "◎⑥テンカジョウ 489kg【±0】\n"
        "　→ 体重維持は最高の状態証明🟢\n"
        "▲④アピーリングルック 489kg【-5】\n"
        "　→ 程よく絞れ・仕上がり良好🟢\n"
        "○①メモリアカフェ 489kg【+4】\n"
        "　→ やや太め感・道悪なら割引き⚠️\n"
        "△②プロミストジーン 468kg【+3】\n"
        "　→ 問題なし・雨なら先行力さらにUP⤴\n\n"
        "#エンプレス杯 #川崎競馬 #競馬データ"
    )
    r1.font.size = Pt(11)

    note(doc, "目安：約250字　目的：馬体重＋馬場情報の最終見解")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿② 上位人気馬 データ分析
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿②】上位人気馬のデータ分析", size=13, color=C_HEAD)
    add_sep(doc)
    doc.add_paragraph()

    p2 = doc.add_paragraph()
    r2 = p2.add_run(
        "🔍 ◎○▲の3頭をデータで斬る\n\n"
        "【◎⑥テンカジョウ 2.2倍 / 松山弘平】\n"
        "・昨年このレース優勝（2連覇挑戦）\n"
        "・牝馬限定戦は【7戦7連対】崩れなし\n"
        "・川崎2100mのコース経験は全頭中最多\n"
        "・重・不良馬場でも崩れない持続力型\n"
        "・馬体重 489kg（±0）→ 体重維持で状態万全🟢\n"
        "→ あらゆるデータで文句なしの本命\n\n"
        "【▲④アピーリングルック 3.0倍 / 戸崎圭太】\n"
        "・ブラジルC（川崎2100m）優勝の実績\n"
        "・4枠は過去10年複勝率【50%】でトップ\n"
        "・戸崎圭太への手替わりで強化\n"
        "・チークピーシズ装着でスタート改善\n"
        "・馬体重 489kg（-5kg）→ 程よく絞れて仕上がり良好🟢\n"
        "→ コース実績×有利枠×好馬体が重なる2番人気\n\n"
        "【○①メモリアカフェ 3.8倍 / C.ルメール】\n"
        "・関東オークス（川崎2100m）で5馬身差圧勝\n"
        "・追い切りB評価・65秒3-11秒3と好時計\n"
        "・ただし重馬場の実績は【1戦0勝】\n"
        "・馬体重 489kg（+4kg）→ やや増加、道悪ならさらに割り引き⚠️\n"
        "→ 良馬場なら軸候補、道悪は要注意\n\n"
        "#エンプレス杯予想 #データ競馬"
    )
    r2.font.size = Pt(11)

    note(doc, "目安：約280字　目的：各馬の強み弱みをデータで整理")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿③ 穴馬・期待値候補
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿③】穴馬・期待値の取れる馬", size=13, color=C_GREEN)
    add_sep(doc)
    doc.add_paragraph()

    p3 = doc.add_paragraph()
    r3 = p3.add_run(
        "💡 △△紐の3頭をピックアップ\n\n"
        "【△②プロミストジーン 7.7倍 / 武豊】\n"
        "・先行力で展開を支配できるタイプ\n"
        "・武豊コメント「距離は長い方がいい」\n"
        "　→ 2100m適性を騎手自ら太鼓判\n"
        "・前走・兵庫女王盃で2着\n"
        "　→ 相手強化でも崩れていない\n"
        "・馬体重 468kg（+3kg）→ 普通の増加、問題なし🟢\n"
        "・7.7倍は実力から見て過小評価\n"
        "→ 期待値ナンバーワンの穴本命\n\n"
        "【△⑧レイナデアルシーラ 18.9倍 / 田口貫太】\n"
        "・母がこのレース優勝の「母仔制覇」\n"
        "　歴史的ロマンがかかる一戦\n"
        "・近走は精彩を欠くが\n"
        "　舞台適性が噛み合えば一変の余地あり\n"
        "・馬体重 510kg（±0）→ 体重維持で安定🟢\n"
        "→ 3連複の3着候補として押さえ\n\n"
        "【紐⑤マーブルマウンテン 31.2倍 / 吉原寛人】\n"
        "・大井所属だが重賞クイーン賞で2着の実力\n"
        "・川崎コースの地の利あり\n"
        "・馬体重 492kg（+3kg）→ 普通の増加\n"
        "・100倍超の3連複配当を狙う大穴枠\n"
        "→ 少額で3連複に組み込む紐候補\n\n"
        "⚡ 雨・不良馬場なら\n"
        "　 先行できる②がさらに浮上👀\n\n"
        "#穴馬 #競馬予想 #期待値"
    )
    r3.font.size = Pt(11)

    note(doc, "目安：約260字　目的：穴馬の根拠を示して差別化")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # 投稿④ 予想印 + 買い目（5,000円）
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【投稿④】予想印 + 買い目（予算5,000円）", size=13, color=C_RED)
    add_sep(doc)
    doc.add_paragraph()

    p4 = doc.add_paragraph()
    r4 = p4.add_run(
        "🏇 アスメシ式 最終予想\n\n"
        "◎ ⑥ テンカジョウ（松山弘平）\n"
        "▲ ④ アピーリングルック（戸崎圭太）\n"
        "○ ① メモリアカフェ（C.ルメール）\n"
        "△ ② プロミストジーン（武豊）\n"
        "△ ⑧ レイナデアルシーラ（田口貫太）\n"
        "紐 ⑤ マーブルマウンテン（吉原寛人）\n"
        "× ③⑦ 消し\n\n"
        "⛅ 馬場別シナリオ\n"
        "【良馬場】◎⑥vs○①の一騎打ち本線\n"
        "【重〜不良】②先行力が浮上👀単勝②価値UP\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 予算5,000円 買い目（全14通り）\n\n"
        "【単勝】1着を当てる　計600円\n"
        "⑥　300円　②　300円\n\n"
        "【ワイド】指定2頭が3着以内に来ればOK\n"
        "＜⑥軸→①②流し＞　計800円\n"
        "⑥-① 400円　⑥-② 400円\n\n"
        "【馬連】指定2頭が1・2着（順不同）\n"
        "＜⑥軸→①②④流し＞　計1,200円\n"
        "⑥-① 500円　⑥-② 500円　⑥-④ 200円\n\n"
        "【3連複】指定3頭が1〜3着（順不同）\n"
        "＜⑥1頭軸フォーメーション＞ 7通り 計2,400円\n"
        "※⑥テンカジョウを全通りに固定\n"
        "─────────────────\n"
        "軸  相手A 相手B  金額  区分\n"
        "⑥ ＋ ① ＋ ④  500円 【本線】\n"
        "⑥ ＋ ① ＋ ②  500円 【本線】\n"
        "⑥ ＋ ② ＋ ④  500円 【展開】\n"
        "⑥ ＋ ① ＋ ⑧  300円 【穴　】\n"
        "⑥ ＋ ① ＋ ⑤  200円 【大穴】\n"
        "⑥ ＋ ② ＋ ⑤  200円 【大穴】\n"
        "⑥ ＋ ② ＋ ⑧  200円 【穴　】\n"
        "─────────────────\n\n"
        "合計：5,000円\n\n"
        "#馬券 #エンプレス杯 #川崎競馬\n"
        "#競馬好きと繋がりたい"
    )
    r4.font.size = Pt(11)

    note(doc, "目安：約340字　目的：馬券種の説明付きで初心者にもわかりやすく")
    doc.add_paragraph()

    # ══════════════════════════════════════
    # シナリオ別回収シミュレーション
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【参考】シナリオ別回収シミュレーション", size=12, color=C_TITLE)
    add_sep(doc)
    doc.add_paragraph()

    body(doc, "■ 5,000円投資 → 目標払戻 15,000〜25,000円（300〜500%）", bold=True, size=10)
    doc.add_paragraph()

    scenarios = [
        ("A", "⑥→①→④（本命決着）",
         "単勝⑥660 + ワイド①-⑥1,600 + 馬連①-⑥3,500 + 馬連④-⑥1,800 + 3連複①④⑥9,000",
         "16,560円", "331%", "✅"),
        ("B", "⑥→①→②（プロミスト絡み）",
         "単勝⑥660 + ワイド①⑥1,600 + ワイド②⑥1,600 + 馬連①⑥3,500 + 馬連②⑥7,500 + 3連複①②⑥20,000",
         "34,860円", "697%", "✅✅"),
        ("C", "⑥→②→④（展開流し）",
         "単勝⑥660 + ワイド②⑥1,600 + 馬連②⑥7,500 + 馬連④⑥1,800 + 3連複②④⑥20,000",
         "31,560円", "631%", "✅✅"),
        ("D", "⑥→①→⑧（レイナ穴）",
         "単勝⑥660 + ワイド①⑥1,600 + 馬連①⑥3,500 + 3連複①⑥⑧18,000",
         "23,760円", "475%", "✅"),
        ("E", "⑥→①→⑤（マーブル大穴）",
         "単勝⑥660 + ワイド①⑥1,600 + 馬連①⑥3,500 + 3連複①⑤⑥20,000",
         "25,760円", "515%", "🎯"),
        ("F", "⑥→②→⑤（超穴）",
         "単勝⑥660 + ワイド②⑥1,600 + 馬連②⑥7,500 + 3連複②⑤⑥20,000",
         "29,760円", "595%", "🎯"),
        ("G", "②単勝のみ的中（テンカジョウ4着外）",
         "単勝②2,310 + ワイド②⑥1,600",
         "3,910円", "78%", "✗"),
    ]

    tbl = doc.add_table(rows=len(scenarios)+1, cols=5)
    tbl.style = "Table Grid"
    headers = ["ケース", "着順", "ヒット馬券（想定払戻）", "合計払戻", "回収率"]
    for i, hh in enumerate(headers):
        c = tbl.rows[0].cells[i]
        c.text = hh
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
    shade_row(tbl.rows[0], "1E3A8A")
    for cell in tbl.rows[0].cells:
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for idx, (case, order, hits, total, roi, mark) in enumerate(scenarios, start=1):
        row = tbl.rows[idx]
        vals = [f"{case} {mark}", order, hits, total, roi]
        for ci, val in enumerate(vals):
            cell = row.cells[ci]
            cell.text = val
            run = cell.paragraphs[0].runs[0]
            run.font.size = Pt(8.5)
            if "✅" in mark or "🎯" in mark:
                if ci == 3:
                    run.bold = True
                    run.font.color.rgb = C_RED
        if idx % 2 == 0:
            shade_row(row, "F0F4FF")

    doc.add_paragraph()

    # ══════════════════════════════════════
    # 出走馬一覧表（参考）
    # ══════════════════════════════════════
    add_sep(doc)
    h(doc, "【参考】出走馬一覧・予想印", size=12, color=C_TITLE)
    add_sep(doc)
    doc.add_paragraph()

    htbl = doc.add_table(rows=9, cols=7)
    htbl.style = "Table Grid"
    hheaders = ["馬番", "馬名", "騎手", "オッズ", "人気", "馬体重", "予想印"]
    for i, hh in enumerate(hheaders):
        c = htbl.rows[0].cells[i]
        c.text = hh
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
    shade_row(htbl.rows[0], "1E3A8A")
    for cell in htbl.rows[0].cells:
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    horses = [
        ("①", "メモリアカフェ",    "C.ルメール", "3.8倍",   "3人気", "489(+4)", "○"),
        ("②", "プロミストジーン",  "武豊",       "7.7倍",   "4人気", "468(+3)", "△"),
        ("③", "マテリアルガール",  "矢野貴之",   "108.4倍", "7人気", "506(+1)", "×"),
        ("④", "アピーリングルック","戸崎圭太",   "3.0倍",   "2人気", "489(-5)", "▲"),
        ("⑤", "マーブルマウンテン","吉原寛人",   "31.2倍",  "6人気", "492(+3)", "紐"),
        ("⑥", "テンカジョウ",      "松山弘平",   "2.2倍",   "1人気", "489(±0)", "◎"),
        ("⑦", "レクランスリール",  "丸山真一",   "285.8倍", "8人気", "436(+3)", "×"),
        ("⑧", "レイナデアルシーラ","田口貫太",   "18.9倍",  "5人気", "510(±0)", "△"),
    ]

    mark_colors = {"◎": C_RED, "○": C_HEAD, "▲": C_ORANGE, "△": C_GREEN}

    for ri, horse in enumerate(horses, start=1):
        for ci, val in enumerate(horse):
            cell = htbl.rows[ri].cells[ci]
            cell.text = val
            run = cell.paragraphs[0].runs[0]
            run.font.size = Pt(9)
            if ci == 6 and val in mark_colors:
                run.bold = True
                run.font.color.rgb = mark_colors[val]
            if horse[0] == "⑥":  # 本命行
                run.bold = True
        if ri % 2 == 0:
            shade_row(htbl.rows[ri], "FFF8F0")

    doc.add_paragraph()

    # フッター
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = foot.add_run(
        "アスメシ式 競馬予想　2026年5月13日　川崎競馬 エンプレス杯キヨフジ記念　JpnII\n"
        "※オッズは発売前の参考値です。最終オッズは馬券購入前に必ずご確認ください。"
    )
    fr.font.size = Pt(8)
    fr.font.color.rgb = C_GRAY

    doc.save(OUTPUT_PATH)
    print(f"OK: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
