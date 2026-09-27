"""
ヴィクトリアマイル2026 + 新潟大賞典2026
枠順確定・調教データ反映 最終予想SNS投稿案
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

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260517")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "最終予想_ヴィクトリアマイル_新潟大賞典_20260517.docx"

# ─────────────────────────────────────────
# ヘルパー
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

def divider(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "B0C4DE")
    pBdr.append(bottom)
    pPr.append(pBdr)

def shade_cell(cell, fill_hex):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)

def make_table(doc, headers, rows, header_fill="1A5C96", highlight_rows=None):
    """highlight_rows: {row_index: fill_hex} で特定行を強調"""
    highlight_rows = highlight_rows or {}
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        shade_cell(cell, header_fill)
        p = cell.paragraphs[0]
        run = p.add_run(h)
        set_font(run, size_pt=9.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for ri, row_data in enumerate(rows):
        fill = highlight_rows.get(ri, ("EEF4FB" if ri % 2 == 1 else "FFFFFF"))
        for ci, val in enumerate(row_data):
            cell = tbl.rows[ri + 1].cells[ci]
            shade_cell(cell, fill)
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            set_font(run, size_pt=9.5)
    doc.add_paragraph()

def badge(doc, text, fill="EEF4FB", text_color=RGBColor(0x1A, 0x3C, 0x6E)):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.rows[0].cells[0]
    shade_cell(cell, fill)
    for line in text.strip().split("\n"):
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10.5, color=text_color)
    doc.add_paragraph()

def post_box(doc, label, text, label_color=RGBColor(0x1D, 0xA1, 0xF2)):
    p = doc.add_paragraph()
    run = p.add_run(f"【{label}】")
    set_font(run, size_pt=10, bold=True, color=label_color)
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.rows[0].cells[0]
    shade_cell(cell, "F8FBFF")
    for line in text.strip().split("\n"):
        p = cell.add_paragraph()
        run = p.add_run(line)
        set_font(run, size_pt=10.5)
    doc.add_paragraph()


# ─────────────────────────────────────────
# データ定義
# ─────────────────────────────────────────

# ── ヴィクトリアマイル 枠順確定データ ──
VICTORIA_HORSES = [
    #  枠  馬番  馬名                  騎手         オッズ  人気  調教体重  変化   追切評価  枠評価  予想印
    ("1", "①", "カピリナ",           "横山典弘",  "63.2", "8人気", "474", "-2",  "C",  "◎内枠",  "×"),
    ("1", "②", "ワイドラトゥール",    "横山武史",  "120.0","12人気","450", "+4",  "C",  "◎内枠",  "×"),
    ("2", "③", "マピュース",          "F.ゴンザ",  "75.1", "9人気", "508", "+14", "C",  "○内枠",  "×"),
    ("2", "④", "エリカエクスプレス",  "武豊",      "17.3", "5人気", "474", "+2",  "A",  "○内枠",  "△"),
    ("3", "⑤", "ケリフレッドアスク",  "M.ディー",  "130.0","13人気","460", "+8",  "C",  "△中枠",  "×"),
    ("3", "⑥", "ラヴァンダ",         "岩田望来",  "31.1", "7人気", "508", "+16", "B",  "△中枠",  "×"),
    ("4", "⑦", "クイーンズウォーク",  "西村淳也",  "8.1",  "3人気", "542", "±0",  "A",  "◎好枠",  "▲"),
    ("4", "⑧", "カムニャック",        "川田将雅",  "3.8",  "2人気", "504", "+6",  "A",  "◎好枠",  "○"),
    ("5", "⑨", "ボンドガール",        "北村友一",  "29.4", "6人気", "460", "+6",  "B",  "△中枠",  "△"),
    ("5", "⑩", "ドロップオブライト",  "松若風馬",  "100.0","11人気","450", "+10", "C",  "△中枠",  "×"),
    ("6", "⑪", "ボンドガール",        "丹内祐次",  "80.0", "10人気","460", "+6",  "B",  "△中枠",  "×"),
    ("6", "⑫", "エンブロイダリー",    "C.ルメール","2.5",  "1人気", "498", "+2",  "A+", "○中枠",  "◎"),
    ("7", "⑬", "カナテープ",         "松山弘平",  "39.8", "8人気", "485", "+7",  "B",  "▼外枠",  "×"),
    ("7", "⑭", "ジョスラン",         "戸崎圭太",  "12.7", "4人気", "480", "+8",  "B",  "▼外枠",  "△"),
    ("7", "⑮", "アイサンサン",       "幸英明",    "56.3", "9人気", "470", "+12", "C",  "▼外枠",  "×"),
    ("8", "⑯", "ニシノティアモ",     "津村明秀",  "15.2", "5人気", "459", "+11", "C",  "✕最外",  "×"),
    ("8", "⑰", "パラディレーヌ",     "坂井瑠星",  "42.3", "7人気", "516", "+6",  "B",  "✕最外",  "×"),
    ("8", "⑱", "チェルヴィニア",     "D.レーン",  "23.4", "6人気", "505", "+7",  "B",  "✕最外",  "△"),
]

# 追切・調教詳細コメント
TRAINING_DETAIL = {
    "エンブロイダリー":  ("A+", "美浦坂路 最終追切。脚元の力感あり・スムーズ。+2kgは成長分で問題なし。状態は過去最高レベル"),
    "カムニャック":      ("A",  "栗東坂路単走。行きたがる面あり蛇行も、手綱緩めると素早く反応。推進力◎。+6kgやや気になる"),
    "クイーンズウォーク":("A",  "栗東坂路単走。±0kgで理想の仕上がり。リラックスした走り・フォーム安定。上首尾な仕上がり"),
    "エリカエクスプレス":("A",  "栗東坂路単走。武豊騎乗で最終追切A評価。以前ほど力みなく、リズム・フォーム安定。状態良好"),
    "チェルヴィニア":    ("B",  "美浦W併走。折り合い良好・手前替えスムーズ。仕上がり自体は問題なし。外枠18番が最大のマイナス"),
    "ジョスラン":        ("B",  "最終追切B評価。+8kgやや増量気味。外枠14番で距離ロスが懸念材料"),
    "ボンドガール":      ("B",  "差し追い込み脚質で東京マイルは合う。6枠11番は中枠でまずまず。状態維持"),
    "ラヴァンダ":        ("B",  "+16kgの大幅増量。太め残りの懸念あり。力を出し切れない可能性"),
}

# 枠順ランキング（東京芝1600m）
WAKU_RANK = [
    ("◎最好枠", "4枠（7・8番）", "スタート後コーナーまで距離があり、中枠で折り合いつきやすい"),
    ("○好枠",   "2〜3枠（3〜6番）", "内目で先行しやすく、ロスが少ない"),
    ("○好枠",   "6枠（11・12番）", "中枠〜やや外。差し馬には適切な位置取りが可能"),
    ("△普通",   "5枠（9・10番）", "やや外だが影響は限定的"),
    ("▼やや不利","7枠（13〜15番）", "外枠でコーナーの距離ロスが増加"),
    ("✕不利",   "8枠（16〜18番）", "最外枠。距離ロス大きく先行馬には特に不利"),
]

# 予想印まとめ
YOSO_SUMMARY = [
    ("◎", "⑫エンブロイダリー", "1人気 2.5倍", "6枠12番", "A+", "498(+2)", "変更なし（調教◎・中枠問題なし）"),
    ("○", "⑧カムニャック",      "2人気 3.8倍", "4枠8番", "A",  "504(+6)", "↑格上げ（好枠4枠・川田騎手の好位置争い期待）"),
    ("▲", "⑦クイーンズウォーク","3人気 8.1倍", "4枠7番", "A",  "542(±0)","変更なし（好枠・体重±0・調教A・昨年2着）"),
    ("△", "④エリカエクスプレス","5人気 17.3倍","2枠4番", "A",  "474(+2)", "↑格上げ（内枠2枠・武豊A評価・状態良好）"),
    ("△", "⑭ジョスラン",        "4人気 12.7倍","7枠14番","B",  "480(+8)", "↓格下げ（外枠7枠・+8kgで減点）"),
    ("△", "⑱チェルヴィニア",   "6人気 23.4倍","8枠18番","B",  "505(+7)", "↓格下げ（最外8枠が致命的に不利）"),
    ("△", "⑪ボンドガール",     "穴 80.0倍",   "6枠11番","B",  "460(+6)", "差し追込の東京向き脚質。配当妙味あり"),
]

# ── 買い目設計（PDCAルール適用）──
# PDCA新ルール: 本命・対抗の差5%以内 → 両者ワイドを必須購入
KAIMOKU = [
    ("単勝",    "⑫エンブロイダリー",       "500円", "1人気2.5倍 × 500 = 期待1,250円"),
    ("ワイド",  "⑫-⑧",                    "500円", "【PDCAルール】本命×対抗 必須購入"),
    ("ワイド",  "⑫-⑦",                    "300円", "本命×3番手"),
    ("馬連",    "⑫-⑧",                    "500円", "本命×対抗 本線"),
    ("馬連",    "⑫-⑦",                    "300円", "本命×3番手"),
    ("3連複",   "⑫-⑧-⑦",                 "500円", "【本線】3強決着"),
    ("3連複",   "⑫-⑧-④",                 "400円", "【展開】エリカエクスプレス台頭"),
    ("3連複",   "⑫-⑦-④",                 "300円", "【展開】対抗外れでクイーンズ×エリカ"),
    ("3連複",   "⑫-⑧-⑪",                 "200円", "【穴】ボンドガール差し込み"),
    ("3連複",   "⑧-⑦-④",                 "200円", "【逆転】エンブロイ外れ時の保険"),
]

# ── 新潟大賞典 データ ──
NIIGATA_HORSES = [
    # 枠順未確定のため想定人気ベース
    ("1人気", "⑪", "ドゥラドーレス",   "C.ルメール", "3.1倍", "58kg", "金鯱賞5着→マイル狙い。長い直線で末脚爆発を期待", "◎"),
    ("2人気", "⑥", "シュガークン",     "武豊",       "6.2倍", "57kg", "2年ぶり復帰戦。距離2000mは最適。新潟外回りは合う", "▲"),
    ("3人気", "①", "アンゴラブラック", "岩田康誠",   "7.8倍", "56kg", "中山金杯2着。距離2000mの実績安定。ハンデ有利56kg", "○"),
    ("4人気", "⑨", "セキトバイースト", "横山和生",   "12.5倍","55kg", "府中牝馬S勝ち馬。左回りで実績。軽ハンデ有利",    "△"),
    ("5人気", "⑤", "シンハナーダ",     "松山弘平",   "18.0倍","54kg", "軽ハンデ54kg。新潟外回りの長直線で差し末脚期待",  "△"),
]

NIIGATA_KAIMOKU = [
    ("単勝",   "⑪ドゥラドーレス",  "500円", "3.1倍 × 500 = 期待1,550円"),
    ("ワイド", "⑪-①",              "500円", "【PDCAルール】本命×対抗 必須購入"),
    ("ワイド", "⑪-⑥",              "300円", "本命×3番手"),
    ("馬連",   "⑪-①",              "500円", "本命×対抗 本線"),
    ("3連複",  "⑪-①-⑥",           "600円", "【本線】3強決着"),
    ("3連複",  "⑪-①-⑨",           "300円", "【穴】セキトバイースト"),
    ("3連複",  "⑪-⑥-⑤",           "300円", "【穴】シンハナーダ軽ハンデ"),
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

    # ── 表紙 ──
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("今週末 重賞 最終予想")
    set_font(run, size_pt=22, bold=True, color=RGBColor(0x0A, 0x34, 0x5C))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("ヴィクトリアマイルG1（5/17 日）+ 新潟大賞典G3（5/16 土）")
    set_font(run, size_pt=13, bold=True, color=RGBColor(0xC0, 0x39, 0x2B))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("枠順確定・最終追切データ・PDCA改善ルール適用版 | 2026.05.15更新")
    set_font(run, size_pt=10.5, color=RGBColor(0x55, 0x55, 0x55))

    doc.add_paragraph()
    divider(doc)
    doc.add_paragraph()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PART 1: ヴィクトリアマイル
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(doc, "PART 1: ヴィクトリアマイル G1（5/17 日）東京・芝1600m・18頭")

    badge(doc,
        "【PDCA学習ルール適用】\n"
        "◎vs○の差が5%以内 → ワイド⑫-⑧を必須購入（天皇賞春・エンプレス杯で2戦連続対抗逆転の反省）\n"
        "外枠（8枠18番チェルヴィニア）は前回予想から降格 → 東京マイルの外枠ペナルティ適用",
        fill="FEF3C7", text_color=RGBColor(0x78, 0x35, 0x00)
    )

    # ── 1-1. 枠順確定全頭一覧 ──
    h2(doc, "1-1. 枠順確定 全頭一覧（追切評価・馬体重含む）")
    vm_rows = [
        (h[0], h[1], h[2], h[3], h[4], h[8], f"{h[6]}({h[7]})", h[9], h[10])
        for h in VICTORIA_HORSES
    ]
    make_table(doc,
        ["枠", "馬番", "馬名", "騎手", "オッズ", "追切", "体重(変化)", "枠評価", "予想印"],
        vm_rows,
        header_fill="0A345C",
        highlight_rows={
            11: "FEF3C7",  # ⑫エンブロイダリー
            7:  "DBEAFE",  # ⑧カムニャック
            6:  "EFF6FF",  # ⑦クイーンズウォーク
            3:  "ECFDF5",  # ④エリカエクスプレス
        }
    )

    # ── 1-2. 枠順有利不利分析 ──
    h2(doc, "1-2. 東京芝1600m 枠順有利不利（確定枠ベース）")
    make_table(doc,
        ["評価", "枠", "理由"],
        WAKU_RANK
    )
    badge(doc,
        "【枠順変更による予想修正】\n"
        "▲→○ カムニャック(⑧・4枠好枠) 枠順確定で対抗に格上げ\n"
        "○→▲ クイーンズウォーク(⑦・4枠好枠) 好枠維持だが格は維持\n"
        "△→△ ジョスラン(⑭・7枠外枠) 外枠で減点\n"
        "△→△ チェルヴィニア(⑱・8枠最外) 最外で大幅減点\n"
        "新規△ エリカエクスプレス(④・2枠内枠・武豊A評価) 内枠で浮上",
        fill="EDE9FE", text_color=RGBColor(0x3B, 0x0F, 0x73)
    )

    # ── 1-3. 調教・追切評価 ──
    h2(doc, "1-3. 最終追切・調教評価（5/13〜14）")
    training_rows = []
    for name, (grade, comment) in TRAINING_DETAIL.items():
        training_rows.append((name, grade, comment))
    make_table(doc,
        ["馬名", "評価", "調教コメント"],
        training_rows,
        header_fill="2C6E49"
    )
    body(doc, "※ A+：状態万全、A：良好、B：標準、C：物足りない", indent=True,
         color=RGBColor(0x66, 0x66, 0x66))

    # ── 1-4. 最終予想印 ──
    h2(doc, "1-4. 最終予想印（枠順確定・追切データ反映後）")
    make_table(doc,
        ["印", "馬番・馬名", "人気/オッズ", "枠番", "追切", "体重変化", "変更理由"],
        YOSO_SUMMARY,
        header_fill="8B0000",
        highlight_rows={
            0: "FEF3C7",   # ◎
            1: "DBEAFE",   # ○
            2: "EFF6FF",   # ▲
            3: "F0FDF4",   # △エリカ
        }
    )

    # ── 1-5. 各馬診断コメント ──
    h2(doc, "1-5. 有力馬 個別診断")

    h3(doc, "◎ ⑫エンブロイダリー（1番人気 2.5倍・C.ルメール・6枠12番）")
    body(doc,
        "桜花賞・秋華賞2冠牝馬。前走阪神牝馬S快勝で状態は絶頂。\n"
        "6枠12番は中枠でルメール騎手が好位で立ち回れる理想的な位置。\n"
        "調教はA+評価で脚元の力感も抜群。体重+2kgは成長分で問題なし。\n"
        "→ 実力・状態・枠・騎手の4拍子揃った本命。死角なし。",
        indent=True)
    body(doc, "ただし「◎より○が先着」パターンが2戦連続発生中のため、⑧とのワイドは必須購入。",
         indent=True, color=RGBColor(0x9B, 0x1C, 0x1C))

    h3(doc, "○ ⑧カムニャック（2番人気 3.8倍・川田将雅・4枠8番）")
    body(doc,
        "昨年のオークス馬。前走阪神牝馬S2着で上がり33.2秒最速。\n"
        "4枠8番は今回の出走馬の中で最も有利な枠。川田騎手が好位で折り合えれば能力全開。\n"
        "調教A評価。行きたがる面が課題だが東京マイルの広いコースで緩和される見込み。\n"
        "体重+6kgがやや気になるが許容範囲内。\n"
        "→ 枠順で対抗に格上げ。エンブロイダリーを逆転する可能性が最も高い。",
        indent=True)

    h3(doc, "▲ ⑦クイーンズウォーク（3番人気 8.1倍・西村淳也・4枠7番）")
    body(doc,
        "昨年のヴィクトリアマイル2着馬。リベンジを狙う。\n"
        "4枠7番はカムニャックのすぐ外で好枠。体重±0kgで仕上がり万全。\n"
        "調教A評価で上首尾な仕上がりをアピール。キズナ産駒で東京マイル適性◎。\n"
        "→ 3番手評価。昨年2着の実績と好枠で3連複の核心。",
        indent=True)

    h3(doc, "△ ④エリカエクスプレス（5人気 17.3倍・武豊・2枠4番）")
    body(doc,
        "2枠4番の内枠を引き、武豊騎手がA評価の追切で本番に臨む。\n"
        "内枠から先行して武豊の好騎乗で粘り込む可能性。体重+2kgは問題なし。\n"
        "前回予想では無印だったが、枠順と追切評価で△に格上げ。\n"
        "→ ヒモ穴として3連複に組み込む価値あり（17.3倍の妙味）。",
        indent=True)

    h3(doc, "△ ⑱チェルヴィニア（6人気 23.4倍・D.レーン・8枠18番）")
    body(doc,
        "一昨年の2冠牝馬で実力は上位だが、8枠18番の最外が痛すぎる。\n"
        "東京マイルで最外から先行するのは距離ロスが大きく不利。\n"
        "調教B評価・体重+7kgも加わり前回予想から降格。\n"
        "→ 実力を疑うわけではないが今回は枠で割引き。単穴止まり。",
        indent=True, color=RGBColor(0x77, 0x55, 0x00))

    # ── 1-6. 買い目設計 ──
    h2(doc, "1-6. 買い目設計（予算5,000円）")

    badge(doc,
        "【PDCA改善ルール適用】\n"
        "✅ ルール2: 本命(⑫2.5倍)vs対抗(⑧3.8倍)の差が小さい → ワイド⑫-⑧を必須購入\n"
        "✅ ルール1: 外枠ペナルティ → チェルヴィニア⑱は3連複から外し点数を整理\n"
        "✅ ルール4: △エリカエクスプレス浮上 → 3連複に組み込み",
        fill="DCFCE7", text_color=RGBColor(0x14, 0x53, 0x2D)
    )

    make_table(doc,
        ["馬券種", "組み合わせ", "金額", "根拠・期待値"],
        KAIMOKU,
        header_fill="7C3AED",
        highlight_rows={
            0: "FEF3C7",  # 単勝
            1: "FEE2E2",  # ワイドPDCA
            4: "DBEAFE",  # 馬連本線
            5: "EFF6FF",  # 3連複本線
        }
    )

    p = doc.add_paragraph()
    run = p.add_run("合計: 3,800円（残り1,200円は当日パドック確認後に追加）")
    set_font(run, size_pt=11, bold=True, color=RGBColor(0x0A, 0x34, 0x5C))

    # ── 1-7. SNS投稿案 ──
    h2(doc, "1-7. SNS投稿案（X / Threads）")

    post_box(doc, "投稿①【予想発表】", (
        "🏇 ヴィクトリアマイル G1 最終予想\n"
        "【枠順・追切データ反映版】\n\n"
        "◎⑫エンブロイダリー（2.5倍・C.ルメール）\n"
        "　→ 6枠12番・調教A+・二冠牝馬の底力\n"
        "○⑧カムニャック（3.8倍・川田将雅）\n"
        "　→ 4枠8番の最好枠🔑 逆転の可能性大\n"
        "▲⑦クイーンズウォーク（8.1倍・西村淳也）\n"
        "　→ 4枠7番・体重±0・昨年2着リベンジ\n"
        "△④エリカエクスプレス（17.3倍・武豊）\n"
        "　→ 内枠2番・武豊A評価の穴馬候補✨\n\n"
        "❌ チェルヴィニア（8枠18番最外）は枠で降格\n\n"
        "#ヴィクトリアマイル #競馬予想 #JRA #AI予想"
    ))

    post_box(doc, "投稿②【馬券紹介】", (
        "💰 ヴィクトリアマイル 買い目公開！\n\n"
        "【PDCAルール適用版・5,000円予算】\n\n"
        "単勝 ⑫エンブロイダリー 500円\n\n"
        "ワイド（本命×対抗流し）\n"
        "⑫-⑧ 500円 ← PDCA必須購入🛡\n"
        "⑫-⑦ 300円\n\n"
        "馬連 ⑫-⑧ 500円\n"
        "馬連 ⑫-⑦ 300円\n\n"
        "3連複フォーメーション\n"
        "⑫-⑧-⑦ 500円【本線】\n"
        "⑫-⑧-④ 400円【エリカ台頭】\n"
        "⑫-⑦-④ 300円【対抗外れ保険】\n"
        "⑫-⑧-⑪ 200円【ボンドガール穴】\n\n"
        "合計3,800円 / 残1,200円は当日パドックで決定🐴\n\n"
        "#ヴィクトリアマイル #馬券 #競馬"
    ))

    post_box(doc, "投稿③【枠順分析】", (
        "📊 ヴィクトリアマイル 枠順の勝者と敗者\n\n"
        "✅ 勝者（好枠）\n"
        "4枠⑦⑧（クイーンズW・カムニャック）\n"
        "→ 東京マイルで最も有利な中枠\n\n"
        "✅ 得した馬\n"
        "2枠④エリカエクスプレス（武豊）\n"
        "→ 内枠から先行・G1でこの枠は美味しい\n\n"
        "❌ 敗者（外枠）\n"
        "8枠⑱チェルヴィニア（D.レーン）\n"
        "→ 最外18番は東京マイルで距離ロス大きい\n"
        "7枠⑭ジョスランも外枠で評価下げ\n\n"
        "→ 枠順で最も得したのはカムニャック🏆\n\n"
        "#ヴィクトリアマイル #枠順分析 #競馬"
    ))

    divider(doc)
    doc.add_paragraph()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PART 2: 新潟大賞典
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(doc, "PART 2: 新潟大賞典 G3（5/16 土）新潟・芝外2000m・ハンデ戦")

    badge(doc,
        "※ 枠順は5月16日（金）11:30ごろ確定予定。現時点では想定人気ベースの予想。\n"
        "新潟芝外回り2000m: 日本最長の直線659m。差し・追い込み脚質有利。\n"
        "ハンデ戦のため軽ハンデ馬の台頭も注意。",
        fill="EDE9FE", text_color=RGBColor(0x3B, 0x0F, 0x73)
    )

    h2(doc, "2-1. 出走馬一覧（想定人気ベース・枠順確定後に更新）")
    make_table(doc,
        ["人気", "想定馬番", "馬名", "騎手", "オッズ", "斤量", "注目ポイント", "印"],
        NIIGATA_HORSES,
        header_fill="2E5A8A",
        highlight_rows={
            0: "FEF3C7",   # ◎
            2: "DBEAFE",   # ○
            1: "EFF6FF",   # ▲
        }
    )

    h2(doc, "2-2. 新潟外回り2000m コース特性")
    body(doc,
        "直線659m（日本最長）の特性:\n"
        "  → 末脚勝負になりやすく、差し・追い込み脚質が有利\n"
        "  → 先行馬でも緩いペースなら粘れる（ハンデ軽ければ特に）\n"
        "過去データ:\n"
        "  → 人気馬が堅い傾向（荒れ度は中程度）\n"
        "  → 1番人気成績: 複勝率約65%\n"
        "  → 外枠の影響は少ない（スタートからコーナーまで距離があるため）",
        indent=True)

    h2(doc, "2-3. 最終予想（枠順確定後に再更新予定）")
    h3(doc, "◎ ドゥラドーレス（C.ルメール・3.1倍）")
    body(doc,
        "斤量58kgで最重量だが実力は上位。ルメール騎手が追切で自己ベストを更新。\n"
        "金鯱賞5着は距離短縮の影響で、2000mに戻って本来の末脚が炸裂する可能性大。\n"
        "新潟外回りの長い直線は差し脚を最大限活かせる舞台。",
        indent=True)
    h3(doc, "○ アンゴラブラック（岩田康誠・7.8倍）")
    body(doc,
        "中山金杯2着の安定感。斤量56kgは適正で機動力あり。\n"
        "ハンデ戦で人気の盲点になりやすい馬。3連複の柱として活用。",
        indent=True)
    h3(doc, "▲ シュガークン（武豊・6.2倍）")
    body(doc,
        "2年ぶり復帰戦で状態は未知数だが、武豊騎手が選んだ馬。\n"
        "斤量57kgは適正。新潟外回り2000mは脚質に合う。\n"
        "復帰戦でいきなり激走するパターンは武豊騎手の得意技。",
        indent=True)

    h2(doc, "2-4. 買い目設計（予算3,000円）")
    make_table(doc,
        ["馬券種", "組み合わせ", "金額", "根拠"],
        NIIGATA_KAIMOKU,
        header_fill="2E5A8A"
    )

    body(doc,
        "⚠️ 枠順確定後（5/16 11:30）に内外枠の影響で予想印を再チェック。\n"
        "ドゥラドーレスが外枠を引いた場合でも、新潟外回りは影響が少ないため変更不要。\n"
        "ハンデ軽量馬（⑤シンハナーダ54kgなど）が好枠を引いた場合は△追加を検討。",
        indent=True, color=RGBColor(0x77, 0x44, 0x00))

    post_box(doc, "投稿④【新潟大賞典 予想】", (
        "🏇 新潟大賞典 G3 予想（5/16 土）\n"
        "新潟芝外2000m・日本最長直線659m！\n\n"
        "◎ドゥラドーレス（3.1倍・C.ルメール）\n"
        "　→ 追切自己ベスト更新。末脚炸裂の舞台🔥\n"
        "○アンゴラブラック（7.8倍）\n"
        "　→ 中山金杯2着・56kg安定感あり\n"
        "▲シュガークン（6.2倍・武豊）\n"
        "　→ 2年ぶり復帰戦・武豊マジック炸裂に期待\n\n"
        "買い目: 単勝◎500円 / 馬連◎-○500円\n"
        "3連複 ◎-○-▲600円 合計3,000円\n\n"
        "※枠順は明日朝確定！更新します\n\n"
        "#新潟大賞典 #競馬予想 #JRA"
    ), label_color=RGBColor(0x16, 0xA3, 0x4A))

    divider(doc)

    # ── フッター ──
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("作成: 2026年5月15日 | keiba-predictor v44 + PDCA改善ルール適用")
    set_font(run, size_pt=9, color=RGBColor(0x88, 0x88, 0x88))

    return doc


if __name__ == "__main__":
    print("最終予想レポートを生成中...")
    doc = build_doc()
    doc.save(OUTPUT_PATH)
    print(f"✅ 完了: {OUTPUT_PATH}")
