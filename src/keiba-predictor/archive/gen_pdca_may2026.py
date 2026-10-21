"""
PDCA総合分析レポート — 2026年4月〜5月13日
4月35ラウンドPDCA + 5月重賞結果（天皇賞春/NHKマイルC/エンプレス杯）を統合
出力: Wordファイル
"""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260513")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "PDCA総合分析レポート_202604-0513.docx"

# ─────────────────────────────────────────
# スタイルヘルパー
# ─────────────────────────────────────────
def set_font(run, size_pt=10.5, bold=False, color=None, font_name="游ゴシック"):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:hint"), "eastAsia")
    rFonts.set(qn("w:eastAsia"), font_name)
    rpr.insert(0, rFonts)

def h1(doc, text, color=RGBColor(0x0A, 0x34, 0x5C)):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(f"■ {text}")
    set_font(run, size_pt=15, bold=True, color=color)

def h2(doc, text, color=RGBColor(0x1A, 0x5C, 0x96)):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f"▍ {text}")
    set_font(run, size_pt=12, bold=True, color=color)

def h3(doc, text, color=RGBColor(0x33, 0x66, 0x99)):
    p = doc.add_paragraph()
    run = p.add_run(f"◆ {text}")
    set_font(run, size_pt=11, bold=True, color=color)

def body(doc, text, size=10.5, indent=False, color=None):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(0.8)
    run = p.add_run(text)
    set_font(run, size_pt=size, color=color)
    return p

def divider(doc, color="D0D0D0"):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)

def shade_row(row, fill_hex):
    for cell in row.cells:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill_hex)
        tcPr.append(shd)

def make_table(doc, headers, rows, header_fill="1A5C96", col_widths=None):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    # ヘッダー行
    for i, h in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        p = cell.paragraphs[0]
        run = p.add_run(h)
        set_font(run, size_pt=9.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), header_fill)
        tcPr.append(shd)
    # データ行
    for ri, row_data in enumerate(rows):
        for ci, val in enumerate(row_data):
            cell = tbl.rows[ri + 1].cells[ci]
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            set_font(run, size_pt=9.5)
        if ri % 2 == 1:
            shade_row(tbl.rows[ri + 1], "EEF4FB")
    doc.add_paragraph()

def badge(doc, text, fill="FFF3CD", text_color=RGBColor(0x66, 0x44, 0x00)):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.rows[0].cells[0]
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)
    for line in text.strip().split("\n"):
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10.5, color=text_color)
    doc.add_paragraph()


# ─────────────────────────────────────────
# データ定義
# ─────────────────────────────────────────

# 4月累計（35ラウンドPDCAより）
APR_STATS = {
    "total_R": 217, "correct_R": 144, "rate": 66.4,
    "turf_R": 101, "turf_ok": 74, "turf_rate": 73.3,
    "dirt_R": 116, "dirt_ok": 70, "dirt_rate": 60.3,
}

# 5月重賞・予想vs結果
MAY_RACES = [
    {
        "date": "5/2(土)",
        "name": "京王杯スプリングC G2",
        "venue": "東京・芝1400m",
        "result": [("1着", "ワールズエンド(16番)", "中穴"),
                   ("2着", "セフィロ", ""),
                   ("3着", "マイネルチケット", "")],
        "prediction": "◎不明 ※予想あり",
        "hit": "確認中",
        "note": "外枠16番が差し切り。荒れレースパターン",
    },
    {
        "date": "5/3(日)",
        "name": "天皇賞・春 G1",
        "venue": "京都・芝3200m",
        "result": [("1着", "クロワデュノール(7番) ○対抗予想", "1番人気 2.3倍"),
                   ("2着", "ヴェルテンベルク", "印なし"),
                   ("3着", "アドマイヤテラ(3番) ◎本命予想", "2番人気 3.6倍")],
        "prediction": "◎アドマイヤテラ → 3着（複勝的中）\n○クロワデュノール → 1着（対抗が本命を逆転）",
        "hit": "複勝○ / 馬連×",
        "note": "3連単70,630円の大荒れ。◎本命が3着、○対抗が1着という逆転パターン",
    },
    {
        "date": "5/10(日)",
        "name": "NHKマイルC G1",
        "venue": "東京・芝1600m",
        "result": [("1着", "ロデオドライブ(17番)", ""),
                   ("2着", "アスクイキゴミ(16番)", ""),
                   ("3着", "アドマイヤクワッズ(11番)", "")],
        "prediction": "SNS投稿案あり（予想印の詳細は別ファイル参照）",
        "hit": "確認中",
        "note": "3連複11-16-17 = 6,160円。外枠3頭が上位独占",
    },
    {
        "date": "5/13(火)",
        "name": "エンプレス杯キヨフジ記念 JpnII",
        "venue": "川崎・ダート2100m（地方交流）",
        "result": [("1着", "①メモリアカフェ ○対抗予想", "3番人気 3.8倍"),
                   ("2着", "⑥テンカジョウ ◎本命予想", "1番人気 2.2倍"),
                   ("3着", "⑧レイナデアルシーラ △穴馬予想", "5番人気 18.9倍")],
        "prediction": "◎テンカジョウ→2着 / ○メモリアカフェ→1着 / △⑧→3着",
        "hit": "3連複①-⑥-⑧ 的中 ✅",
        "note": "投資5,000円→回収5,910円（118%）。対抗が本命を逆転するパターン再現",
    },
]

# 重賞収支
KESSAN = [
    ("5/2 京王杯SC",    "確認中", "確認中", "確認中"),
    ("5/3 天皇賞春",    "複勝的中（◎3着）", "詳細未確認", "要精算"),
    ("5/13 エンプレス杯", "3連複的中 ✅",  "5,000円", "5,910円 (118%)"),
]

# 直近6週 的中率推移
WEEKLY_TREND = [
    ("2026-W13（3月末）", "68.9%", "31/45"),
    ("2026-W14（4月第1週）", "68.1%", "47/69"),
    ("2026-W15（4月第2週）", "63.8%", "44/69"),
    ("2026-W16（4月第3週）", "64.7%", "22/34"),
    ("2026-W17（4月第4週・青葉賞）", "▼（青葉賞本命外れ）", "要集計"),
    ("2026-W18〜19（5月重賞週）", "▼（天皇賞春・馬連外れ）", "要集計"),
]

# 会場別成績（4月実績）
VENUE_STATS = [
    ("京都", "81.8%", "9/11", "◎最優秀"),
    ("阪神", "71.0%", "49/69", "○良好"),
    ("中山", "67.2%", "45/67", "△平均"),
    ("福島", "58.6%", "34/58", "▼要改善"),
    ("東京", "58.3%", "7/12", "▼要改善"),
    ("川崎(地方)", "初測定", "1/1", "◎3連複的中"),
]

# 外れパターン分析（4月）
MISS_PATTERN = [
    ("ダートで外れ", "46件", "外れ全体の63%", "最重要課題"),
    ("荒れレース(荒れ度6+)", "33件", "的中率59.8%", "見送り検討"),
    ("惜敗(4〜6着)", "41件", "外れ全体の50%", "ワイド追加で救済可"),
    ("大敗(7着以下)", "32件", "外れ全体の44%", "本命選択を見直し"),
    ("逃げ馬本命", "青葉賞で典型", "東京長距離逃げ馬1着率12%", "即時減点ルール適用"),
    ("◎より○が上回るパターン", "天皇賞春・エンプレス杯で発生", "2戦連続", "新規課題として追加"),
]

# 距離帯別成績（4月）
DIST_STATS = [
    ("〜1200m(短距離)", "58.5%", "31/53", "▼"),
    ("1201〜1400m", "66.7%", "14/21", "△"),
    ("1401〜1600m(マイル)", "65.2%", "15/23", "△"),
    ("1601〜1800m", "66.2%", "49/74", "△"),
    ("1801〜2000m(中距離)", "71.4%", "20/28", "○"),
    ("2001〜2200m", "83.3%", "5/6", "◎"),
    ("2201m+(長距離)", "83.3%", "10/12", "◎"),
]

# PDCAアクションリスト（4月分→5月時点の進捗）
ACTIONS = [
    ("HIGH", "逃げ馬×東京長距離0.75減点", "未実装（青葉賞で失敗後も未適用）", "🔴 緊急"),
    ("HIGH", "騎手×コース×距離 複合補正", "未実装", "🟡 今月"),
    ("HIGH", "ダートモデル分離・再学習", "未実装", "🟡 今月"),
    ("MED",  "新種牡馬 +10%上方補正", "未実装（コントレイル産駒等）", "🟡 今月"),
    ("MED",  "荒れ度6+ EV閾値を1.2に引上げ", "未実装", "🟡 今月"),
    ("MED",  "惜敗時のワイド追加推奨", "部分的に運用中（手動）", "🟢 継続"),
    ("NEW",  "◎より○が先着パターンの検知", "5月に2戦連続発生→対抗ワイド購入必須化", "🔴 新規追加"),
    ("NEW",  "地方競馬（南関東）予想の精度追跡", "エンプレス杯で3連複的中→追跡開始", "🟢 継続"),
    ("NEW",  "外枠馬の評価補正（NHKマイルC）", "外枠3頭が上位独占→外枠ペナルティ見直し", "🟡 今月"),
]

# モデル更新計画
MODEL_PLAN = [
    ("v44（現行）", "基本モデル", "2026年4月時点 使用中"),
    ("v45（計画）", "逃げ馬ペナルティ + 新種牡馬補正 + 騎手複合補正 + ダート分離", "5月中に実装予定"),
    ("v46（将来）", "外枠評価見直し + 地方競馬対応 + 対抗逆転パターン検知", "6月以降"),
]

# KPI目標
KPI = [
    ("総合的中率", "66.4%（4月）", "68.4%以上", "+2pt改善"),
    ("ダート的中率", "60.3%（4月）", "63%以上", "+3pt改善"),
    ("重賞本命的中率", "複勝2/4戦", "馬連的中率50%以上", "本命確信度向上"),
    ("荒れ度6+見送り率", "ほぼ0%", "30%以上", "高リスクレース排除"),
    ("逃げ馬◎率", "推定15%+", "5%以下", "脚質×コース適性評価徹底"),
    ("地方競馬的中率", "初測定（1/1）", "継続追跡", "エンプレス杯が初事例"),
]


# ─────────────────────────────────────────
# ドキュメント生成
# ─────────────────────────────────────────
def build_doc():
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    # ── 表紙 ──────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("PDCA 総合分析レポート")
    set_font(run, size_pt=22, bold=True, color=RGBColor(0x0A, 0x34, 0x5C))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026年4月〜5月13日 | 累計217レース + 重賞5戦")
    set_font(run, size_pt=12, color=RGBColor(0x44, 0x44, 0x44))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("keiba-predictor v44 モデル評価 + v45改善計画")
    set_font(run, size_pt=11, bold=True, color=RGBColor(0x1A, 0x5C, 0x96))

    doc.add_paragraph()
    divider(doc, "1A5C96")
    doc.add_paragraph()

    # ── SECTION 1: エグゼクティブサマリー ──
    h1(doc, "SECTION 1: エグゼクティブサマリー")

    badge(doc,
        "【総合評価】\n"
        "4月累計的中率 66.4% は目標値66%をわずかに超過しているが、\n"
        "5月重賞2戦（天皇賞春・エンプレス杯）で「◎本命より○対抗が先着」という\n"
        "新パターンが2戦連続で発生。これはモデルの本命選択精度に構造的な課題がある\n"
        "ことを示す。ダート弱さ（60.3%）も継続課題。v45モデルの早期実装が急務。",
        fill="DBEAFE", text_color=RGBColor(0x1E, 0x3A, 0x5F)
    )

    make_table(doc,
        ["指標", "現状", "目標", "状態"],
        [
            ["4月累計的中率", "66.4% (144/217R)", "68.4%以上", "🟡 要改善"],
            ["芝レース的中率", "73.3%", "75%以上", "🟡 良好"],
            ["ダート的中率", "60.3%", "63%以上", "🔴 重点課題"],
            ["重賞本命的中", "複勝2/4戦", "馬連50%以上", "🟡 改善中"],
            ["◎本命が2着止まり", "2戦連続（5月）", "発生率10%以下", "🔴 新規課題"],
            ["地方競馬予測", "3連複1/1的中", "継続追跡", "🟢 初的中"],
        ]
    )

    divider(doc)

    # ── SECTION 2: 4月累計分析 ──
    h1(doc, "SECTION 2: 4月累計分析（35ラウンドPDCA）")

    h2(doc, "2-1. 全体成績")
    body(doc,
        f"対象: {APR_STATS['total_R']}レース  "
        f"的中: {APR_STATS['correct_R']}レース  "
        f"的中率: {APR_STATS['rate']}%（目標66%を0.4pt超過）"
    )

    h2(doc, "2-2. 芝 vs ダート 乖離（最重要課題）")
    make_table(doc,
        ["種別", "的中率", "レース数", "的中数", "評価"],
        [
            ["芝", "73.3%", "101R", "74R", "○良好"],
            ["ダート", "60.3%", "116R", "70R", "🔴 要強化"],
            ["差分", "13.0pt差", "—", "—", "ダート特化モデルが急務"],
        ]
    )
    body(doc, "ダート外れの内訳: ダート〜1400m(短距離)の的中率が特に低い（推定52%前後）。\n"
              "ダート1401m以上は65〜80%と安定しているため、短距離ダートに問題が集中。",
         indent=True)

    h2(doc, "2-3. 距離帯別成績")
    make_table(doc,
        ["距離帯", "的中率", "成績", "評価"],
        DIST_STATS
    )

    h2(doc, "2-4. 会場別成績")
    make_table(doc,
        ["会場", "的中率", "成績", "評価"],
        VENUE_STATS
    )

    h2(doc, "2-5. 週間トレンド")
    make_table(doc,
        ["週", "的中率", "成績"],
        WEEKLY_TREND
    )

    h2(doc, "2-6. 外れパターン分析")
    make_table(doc,
        ["パターン", "件数", "割合/備考", "優先度"],
        MISS_PATTERN
    )

    divider(doc)

    # ── SECTION 3: 5月重賞 予想vs結果 ──
    h1(doc, "SECTION 3: 5月重賞レース — 予想 vs 結果")

    for race in MAY_RACES:
        h2(doc, f"{race['date']} {race['name']} （{race['venue']}）")

        # 結果テーブル
        result_rows = [(r[0], r[1], r[2]) for r in race["result"]]
        make_table(doc,
            ["着順", "馬名（予想印）", "人気/オッズ"],
            result_rows,
            header_fill="2C6E49"
        )

        body(doc, f"予想: {race['prediction']}", indent=True)
        body(doc, f"結果: {race['hit']}", indent=True,
             color=RGBColor(0x0A, 0x6A, 0x1A) if "的中" in race["hit"] else RGBColor(0x8B, 0x00, 0x00))
        body(doc, f"分析: {race['note']}", indent=True,
             color=RGBColor(0x55, 0x55, 0x55))
        doc.add_paragraph()

    h2(doc, "5月重賞 収支サマリー")
    make_table(doc,
        ["レース", "的中状況", "投資", "回収"],
        KESSAN
    )

    divider(doc)

    # ── SECTION 4: 重要発見事項 ──
    h1(doc, "SECTION 4: 重要発見事項（新規パターン）")

    h2(doc, "4-1. 【新発見】◎本命より○対抗が先着するパターン（2戦連続）")
    badge(doc,
        "【天皇賞春】◎アドマイヤテラ(3着) < ○クロワデュノール(1着)\n"
        "【エンプレス杯】◎テンカジョウ(2着) < ○メモリアカフェ(1着)\n\n"
        "→ 2戦連続で「本命が対抗に逆転される」パターンが発生。\n"
        "   モデルが「安定感・人気」を過大評価し、\n"
        "   「能力最大化できる条件」を過小評価している可能性がある。",
        fill="FEE2E2", text_color=RGBColor(0x7F, 0x1D, 0x1D)
    )
    body(doc, "対応策: 本命と対抗の差が5%以内の場合、両者のワイドを必ず購入。\n"
              "　　　　「逆転の可能性あり」フラグを設けて複数点購入を推奨。", indent=True)

    h2(doc, "4-2. 外枠馬の台頭（NHKマイルC）")
    body(doc, "NHKマイルC: 1着(17番)・2着(16番)・3着(11番) → 外枠3頭が上位を独占。\n"
              "東京芝マイルにおける外枠評価を見直す必要がある。\n"
              "現行モデルは枠順の影響を軽視している可能性。", indent=True)

    h2(doc, "4-3. 地方競馬（南関東）初的中")
    badge(doc,
        "エンプレス杯（川崎ダート2100m）で3連複的中。回収率118%。\n"
        "南関東・地方交流重賞への予想展開が有効であることを確認。\n"
        "→ 今後は大井・浦和・川崎の重要交流重賞を定期的に予想対象に追加する。",
        fill="DCFCE7", text_color=RGBColor(0x14, 0x53, 0x2D)
    )

    h2(doc, "4-4. 穴馬（△）の3着好走パターン")
    body(doc, "エンプレス杯: △⑧レイナデアルシーラ(5番人気18.9倍)が3着で3連複高配当に貢献。\n"
              "△評価馬が3着に来るとき、3連複の配当が跳ね上がる。\n"
              "→ △印馬との3連複は投資優先度を高める。", indent=True)

    divider(doc)

    # ── SECTION 5: PDCAアクションリスト ──
    h1(doc, "SECTION 5: PDCAアクションリスト（優先度順）")

    h2(doc, "5-1. アクション一覧")
    make_table(doc,
        ["優先度", "改善項目", "現状", "ステータス"],
        ACTIONS,
        header_fill="7C3AED"
    )

    h2(doc, "5-2. 即時適用ルール（コード変更なしで実施可能）")
    badge(doc,
        "【ルール1】逃げ馬×東京長距離 → 本命から除外（減点0.75倍）\n"
        "【ルール2】本命・対抗の能力差5%以内 → 両者ワイドを必ず購入\n"
        "【ルール3】荒れ度6以上のレース → EV1.2以上でないと推奨しない\n"
        "【ルール4】△穴馬が2頭以上いる場合 → 3連複の点数を増やす\n"
        "【ルール5】地方交流重賞（南関東） → 予想対象に積極的に追加",
        fill="F0FDF4", text_color=RGBColor(0x14, 0x53, 0x2D)
    )

    divider(doc)

    # ── SECTION 6: モデルv45 更新計画 ──
    h1(doc, "SECTION 6: モデル v45 更新計画")

    h2(doc, "6-1. バージョン比較")
    make_table(doc,
        ["バージョン", "主な変更点", "状況"],
        MODEL_PLAN
    )

    h2(doc, "6-2. v45 実装仕様（コード変更箇所）")
    body(doc,
        "① 逃げ馬ペナルティ\n"
        "   if 脚質=='逃げ' and コース in ['東京','京都','阪神'] and 距離>=2000:\n"
        "       score *= 0.75\n\n"
        "② 新種牡馬補正（データ50件未満）\n"
        "   NEW_SIRES = ['コントレイル','エフフォーリア','ダノンキングリー','サートゥルナーリア']\n"
        "   if father in NEW_SIRES and data_count < 50:\n"
        "       score *= 1.10\n\n"
        "③ 対抗逆転フラグ\n"
        "   if abs(rank1_score - rank2_score) < 0.05:\n"
        "       recommend_wide_rank1_rank2 = True\n\n"
        "④ ダートモデル分離\n"
        "   芝とダートで重みパラメータを独立化（dist_model_turf, dist_model_dirt）\n\n"
        "⑤ 荒れ度連動EV閾値\n"
        "   ev_threshold = 1.2 if upset_score >= 6 else 1.0",
        indent=True
    )

    divider(doc)

    # ── SECTION 7: KPI目標 ──
    h1(doc, "SECTION 7: KPI目標（次の4週間）")

    make_table(doc,
        ["KPI", "現状", "目標", "改善幅"],
        KPI
    )

    doc.add_paragraph()
    body(doc, "評価日: 2026年6月第1週末（ダービー週）終了後にKPIを再確認する。", indent=True)

    divider(doc)

    # ── SECTION 8: 次回PDCA計画 ──
    h1(doc, "SECTION 8: 次回PDCA計画")

    badge(doc,
        "次回実施: 2026年5月25日（日）〜 ヴィクトリアマイル・オークス含む週末終了後\n"
        "対象レース: ヴィクトリアマイルG1（5/17）・オークスG1（5/24）\n"
        "重点チェック項目:\n"
        "  ・ルール1〜5（即時適用ルール）の効果検証\n"
        "  ・◎本命の先着率改善（目標: 天皇賞春/エンプレス杯の逆転パターン再発なし）\n"
        "  ・v45モデル実装状況の確認",
        fill="EEF2FF", text_color=RGBColor(0x1E, 0x1B, 0x4B)
    )

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("生成日: 2026年5月15日　keiba-predictor v44")
    set_font(run, size_pt=9, color=RGBColor(0x88, 0x88, 0x88))

    return doc


if __name__ == "__main__":
    print("PDCAレポートを生成中...")
    doc = build_doc()
    doc.save(OUTPUT_PATH)
    print(f"✅ 完了: {OUTPUT_PATH}")
