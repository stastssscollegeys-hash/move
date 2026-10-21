"""
天皇賞・春 2026 事前予想 SNS投稿案 + note記事
X / Threads / note の3形式をWordで出力
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
OUTPUT_PATH = OUTPUT_DIR / "20260503_天皇賞春_事前予想SNS.docx"


# ── ヘルパー ──────────────────────────────────────────

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
    set_font(run, size_pt=13, bold=True,
             color=color or RGBColor(0x0F, 0x47, 0x61))


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
        set_font(run, size_pt=10.5)
    doc.add_paragraph()


def add_heading(doc, text, level=2):
    p = doc.add_paragraph()
    if level == 2:
        run = p.add_run(f"▍ {text}")
        set_font(run, size_pt=13, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    elif level == 3:
        run = p.add_run(f"◆ {text}")
        set_font(run, size_pt=11, bold=True, color=RGBColor(0x33, 0x66, 0x99))


def add_body(doc, text, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(0.8)
    run = p.add_run(text)
    set_mincho(run, size_pt=11)


# ── 投稿テキスト ─────────────────────────────────────

# ─── X投稿 ①（本命発表）───
X_HONMEI = """\
🏇【天皇賞・春 2026 事前予想】
5月3日 京都芝3200m G1

現時点での本命はこの2頭

◎ アドマイヤテラ（武豊）
阪神大賞典コースレコード勝ち🔥
武豊×京都の鉄板コンビ
調教S評価・状態は最高潮

◎ クロワデュノール（北村友一）
日本ダービー馬×大阪杯制覇
父キタサンブラックが天皇賞春連覇
唯一の課題は初の3200m

どちらが軸になるかは枠順次第！
馬券組み立ては直前に発表します🙏

#天皇賞春 #競馬予想 #アスメシ競馬"""

# ─── X投稿 ②（穴馬・消し馬）───
X_ANA = """\
🏇【天皇賞・春 2026 穴馬・消し馬】

【狙える穴馬2頭🎯】

△ スティンガーグラス（D.レーン）
ダイヤモンドS（3400m！）勝ちの本格ステイヤー
今週も外国人騎手×長距離は要注目
人気以上に走る可能性あり

△ アクアヴァーナル（松山）
牝馬だが京都コース複勝率100%
阪神大賞典2着・2kg軽い斤量も有利

【即消し馬🚫】
✗ ミステリーウェイ（前走14着・8歳）
✗ ケイアイサンデラ（前走が障害レース）
✗ タガノデュード（3000m超は今回初）

過去10年の勝ち馬は全て1〜3番人気
堅い決着の可能性が高い一戦です！

#天皇賞春 #競馬 #アスメシ競馬"""

# ─── X投稿 ③（今週のポイント）───
X_POINT = """\
📊【天皇賞・春 2026 狙い目キーワード】

先週4/26のG2ダブル的中データから引き継ぐ鉄則👇

✅ 武豊×京都コース
→ マイラーズCで完璧証明済
→ アドマイヤテラで今週も継続

✅ D.レーン×長距離スタミナ戦
→ スティンガーグラスに注目

✅ 同コース実績がある馬を最優先
→ ヘデントールは昨年の勝ち馬（連覇狙い）

✅ 良馬場継続なら堅い決着モード
→ 上位人気に集中投資が正解

枠順確定後に最終予想を発表します！
フォローお忘れなく🙏

#天皇賞春 #AI競馬予想 #アスメシ競馬"""

# ─── Threads投稿（1本にまとめ）───
THREADS = """\
🏇【天皇賞・春 2026 完全事前分析】5月3日 京都芝3200m G1

来週のG1に向けて、現時点での予想をまとめました！

━━━━━━━━━━━━━━━━━
◎ 本命候補 2頭
━━━━━━━━━━━━━━━━━

【アドマイヤテラ（武豊）】
阪神大賞典を阪神芝3000mのコースレコードで圧勝🔥
前哨戦→本番の直結度が高く、武豊騎手×京都の組み合わせは先週マイラーズCでも実証済み。
調教S評価で仕上がりも万全。現時点での1番手候補。

【クロワデュノール（北村友一）】
日本ダービー馬×大阪杯G1制覇。今年最強格の実力。
父キタサンブラックが天皇賞春を連覇しており血統的に3200mは歓迎。
調教もS評価と状態は申し分なし。
唯一の課題は今回が初めての3200m。距離の壁をクリアできれば。

━━━━━━━━━━━━━━━━━
△ 穴馬候補 2頭
━━━━━━━━━━━━━━━━━

【スティンガーグラス（D.レーン）】
ダイヤモンドS（芝3400m）勝ちの本格ステイヤー。
今回の出走馬で最も長距離実績がある。
上位2頭に人気が集中する分オッズが甘くなる見込みで、3連系の相手として最有力。

【アクアヴァーナル（松山弘平）】
牝馬ながら京都コースは【2-3-0-0】で複勝率100%という驚異の相性。
阪神大賞典2着（アドマイヤテラの直後）で実力も証明済み。
牡馬より2kg軽い斤量がスタミナ消耗戦で有利。

━━━━━━━━━━━━━━━━━
🚫 消し馬（確定）
━━━━━━━━━━━━━━━━━
✗ ミステリーウェイ：8歳・前走14着惨敗
✗ ケイアイサンデラ：前走が障害レース
✗ タガノデュード：3000m超は今回が初めて・スピード型

━━━━━━━━━━━━━━━━━
📊 過去10年の鉄則
━━━━━━━━━━━━━━━━━
・勝ち馬は全て1〜3番人気（荒れない）
・4コーナー5番手以内の先行馬が有利
・武豊×アドマイヤテラは過去10年でこのパターンが2勝

馬券の組み立ては枠順確定後に改めて発表します。
引き続きよろしくお願いします🙏

#天皇賞春 #競馬予想 #AI競馬予想 #アスメシ競馬"""


# ─── note記事 本文 ───────────────────────────────────

NOTE_LEAD = """\
　5月3日（日）、京都競馬場で天皇賞・春（G1）が開催されます。距離は芝3200mの長距離王決定戦。4月26日のフローラS・マイラーズCでG2ダブル的中を果たした勢いそのままに、今週も全力で予想します。
　馬券の組み立ては枠順確定後に行いますが、今回は「現時点での有力馬・穴馬・消し馬の整理」をお届けします。"""

NOTE_ENTRY = """\
　今年は16頭が登録（フルゲート18頭のため全馬出走可）。過去10年で勝ち馬が全て1〜3番人気というデータが示す通り、荒れにくい長距離G1です。展開のカギは「折り合いとスタミナ、2周目の下りからのロングスパート戦」への対応力。"""

NOTE_MATOME = """\
　焦点は「クロワデュノールが初の3200mをこなせるか」に尽きます。こなせるなら能力最上位として中心。不安が残るなら阪神大賞典圧勝のアドマイヤテラに集約。穴2頭（スティンガーグラス・アクアヴァーナル）は人気以上の走りが期待でき、3連系の相手として要注目です。
　枠順確定後に最終買い目を発表しますので、フォロー＆スキでお待ちください🙏"""


# ── メイン ────────────────────────────────────────────

def main():
    doc = Document()

    # ══ 表紙 ══
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("天皇賞・春 2026 事前予想 SNS投稿案")
    set_font(run, size_pt=17, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026年5月3日（日）京都競馬場 芝3200m G1")
    set_font(run, size_pt=10, color=RGBColor(0x88, 0x88, 0x88))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("【投稿順】① 本命発表  →  ② 穴馬・消し馬  →  ③ 狙い目キーワード")
    set_font(run, size_pt=9, color=RGBColor(0x88, 0x44, 0x00))

    doc.add_paragraph()

    # ══ X投稿 ══
    add_section_bar(doc, "━━━ X（Twitter）投稿 ━━━", RGBColor(0x1D, 0xA1, 0xF2))
    doc.add_paragraph()

    add_label(doc, "【投稿①】本命発表", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_HONMEI, "EBF5FB",
            note="レース前々日〜前日（5/1〜5/2）に投稿推奨")

    add_label(doc, "【投稿②】穴馬・消し馬", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_ANA, "EBF5FB",
            note="投稿①の数時間後〜翌日")

    add_label(doc, "【投稿③】狙い目キーワード（先週データ引き継ぎ）", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_POINT, "EBF5FB",
            note="枠順確定後・最終予想の前に投稿")

    doc.add_page_break()

    # ══ Threads投稿 ══
    add_section_bar(doc, "━━━ Threads投稿 ━━━", RGBColor(0x00, 0x00, 0x00))
    doc.add_paragraph()

    add_label(doc, "【Threads】完全事前分析（1投稿でまとめ）", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, THREADS, "F5F5F5",
            note="X投稿①②③を1本に統合した長文版。Threadsはスクロール読みが多いので詳しく書く")

    doc.add_page_break()

    # ══ note記事 ══
    add_section_bar(doc, "━━━ note記事 ━━━", RGBColor(0xC2, 0x18, 0x5B))
    doc.add_paragraph()

    # タイトル
    p = doc.add_paragraph()
    run = p.add_run("【天皇賞・春 2026 事前予想】本命・穴馬・消し馬を全部晒す")
    set_font(run, size_pt=16, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    run = p.add_run("2026年5月3日（日）京都競馬場 芝3200m G1　アスメシ競馬予想")
    set_font(run, size_pt=9, color=RGBColor(0x99, 0x99, 0x99))

    doc.add_paragraph()

    # リード
    add_body(doc, NOTE_LEAD)
    doc.add_paragraph()

    # 出走馬概況
    add_heading(doc, "出走馬と概況", level=2)
    doc.add_paragraph()
    add_body(doc, NOTE_ENTRY)
    doc.add_paragraph()

    # 本命
    add_heading(doc, "本命候補 2頭", level=2)
    doc.add_paragraph()

    add_heading(doc, "◎ アドマイヤテラ（武豊）", level=3)
    add_body(doc, "　阪神大賞典を阪神芝3000mのコースレコードで圧勝。長距離G2を制した勢いそのままに本番へ向かう正統派ローテーション。武豊騎手×京都コースの組み合わせは先週のマイラーズCで完璧に機能しており、今週も引き続き最有力パターンです。調教評価もS（最高）で仕上がりは本番直結レベルです。")
    doc.add_paragraph()

    add_heading(doc, "◎ クロワデュノール（北村友一）", level=3)
    add_body(doc, "　日本ダービー馬として大阪杯G1も制した今年最強格の1頭。父キタサンブラックが天皇賞・春を連覇しており、血統的に3200mは歓迎できます。調教もS評価で状態面は申し分なし。唯一の課題は今回が初めての3200m。距離の壁を克服できれば能力最上位の評価は揺るぎません。")
    doc.add_paragraph()

    add_box(doc, """\
先週（4/26）データとの連動：
・武豊×京都コース → マイラーズCで証明。アドマイヤテラで今週も継続案件
・同コース実績×得意騎手パターン → 今週の最重要チェック軸""",
            bg_color="FFF9C4")

    # 穴馬
    add_heading(doc, "穴馬候補 2頭", level=2)
    doc.add_paragraph()

    add_heading(doc, "△ スティンガーグラス（D.レーン）", level=3)
    add_body(doc, "　ダイヤモンドS（芝3400m）勝ちの本格ステイヤー。今回の出走馬で最も長い距離での勝利実績を持ちます。D.レーン騎手は先週フローラSでも末脚型馬を完璧に操っており、長距離スタミナ戦でも能力を発揮できるジョッキー。上位2頭に人気が集中する分だけオッズが甘くなり、3連系の相手として筆頭候補です。")
    doc.add_paragraph()

    add_heading(doc, "△ アクアヴァーナル（松山弘平）", level=3)
    add_body(doc, "　牝馬でありながら京都コース成績は【2-3-0-0】で複勝率100%という驚異の相性を誇ります。阪神大賞典2着（アドマイヤテラの直後）で実力も証明済み。牡馬より2kg軽い斤量（56kg）はスタミナを削り合う長距離戦で有利に働くポイント。人気以上の走りが期待できる隠れた好相性馬です。")
    doc.add_paragraph()

    # 消し馬
    add_heading(doc, "消し馬（確定）", level=2)
    doc.add_paragraph()

    add_box(doc, """\
🚫 即消し馬（データ・実績から除外）

ミステリーウェイ（8歳・前走14着）
→ 年齢と前走惨敗でデータ外。買い要素ゼロ。

ケイアイサンデラ（前走：障害レース11着）
→ 障害→芝G1への転戦。適性・状態ともに対応不可。

タガノデュード（3000m超は今回が初）
→ 大阪杯（2000m）4着のスピード型。距離適性が最大の課題。

ヴェルミセル（海外前走11着）
→ 状態・適性ともに疑問。

サンライズソレイユ（前走11着）
→ 近走に見るべき内容なし。""",
            bg_color="FFEBEE")

    doc.add_paragraph()

    # 傾向
    add_heading(doc, "過去10年データ・今週の鉄則", level=2)
    doc.add_paragraph()

    add_box(doc, """\
📊 過去10年の天皇賞（春）傾向

① 勝ち馬は全て1〜3番人気 → 荒れない。上位人気への集中投資が正解
② 4コーナー5番手以内の馬が80%以上で馬券圏内 → 追込みは届かない
③ 前走2000m組の成績が実は最優秀 → 距離不問、能力重視で判断
④ 同コース実績（京都3200m）がある馬は要注目 → ヘデントール（昨年勝ち馬）

🔑 先週データからの引き継ぎ鉄則

・武豊×京都コース → 今週もアドマイヤテラで継続
・外国人騎手×長距離 → スティンガーグラス（D.レーン）に注目
・良馬場継続なら堅い日モード → 単勝・馬連・ワイドに集中""",
            bg_color="E3F2FD")

    doc.add_paragraph()

    # まとめ
    add_heading(doc, "まとめ・枠順確定後の方針", level=2)
    doc.add_paragraph()
    add_body(doc, NOTE_MATOME)
    doc.add_paragraph()

    # ハッシュタグ
    add_heading(doc, "推奨ハッシュタグ", level=2)
    doc.add_paragraph()
    add_box(doc, """\
#天皇賞春 #天皇賞 #競馬予想 #AI競馬予想 #重賞予想
#競馬 #G1 #京都競馬場 #アドマイヤテラ #クロワデュノール
#アスメシ競馬 #競馬収支 #馬券""",
            bg_color="F3E5F5",
            note="12〜13個を目安に。レース当日はさらに「#天皇賞春2026」を追加推奨")

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
