"""
2026/05/02（土）
ユニコーンステークス（京都ダート1900m G3）
京王杯スプリングカップ（東京芝1400m G2）
事前予想 SNS投稿案 + note記事 Word出力
"""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260502")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "20260502_土曜重賞_事前予想SNS.docx"


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
    if level == 1:
        run = p.add_run(text)
        set_font(run, size_pt=16, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    elif level == 2:
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


# ════════════════════════════════════════════════════
# ユニコーンステークス 投稿テキスト
# 2026/05/02 京都ダート1900m G3 3歳
# ════════════════════════════════════════════════════

UNICORN_X1 = """\
🦄【ユニコーンS 2026 事前予想】
5/2（土）京都ダート1900m G3

◎ メルカントゥール
前走1勝クラスを4馬身差で圧勝🔥
追い切りの動きも力強く状態は最高潮
京都1900mの持続力勝負に最も合う

◎ ケイアイアギト
サウジダービー5着の国際経験馬
帰国後の調整良好・能力は最上位候補
大物感があり頭固定で狙える存在

△ ソルチェリア
京都コース経験豊富な先行馬
追い切りS評価で調子もいい
人気が割れる穴候補として注目

枠順確定後に最終予想を発表します🙏
#ユニコーンステークス #競馬予想 #アスメシ競馬"""

UNICORN_X2 = """\
🦄【ユニコーンS 消し馬・データ傾向】

【即消し🚫】
✗ シャローファースト（追い切りC評価・反応不足）
✗ フクシマブリルハム（前走9着・追い切りC評価）

【データキーワード📊】
・4コーナー3番手以内の馬が過去50走で27勝
→ 前に行ける馬が有利な京都ダート
・向正面からの早仕掛けに対応できるスタミナが必要
→ 1900mは純粋なスプリンターには向かない

3歳世代のダート王者決定戦！
今年の主役は誰だ？

#ユニコーンステークス #競馬 #ダート競馬"""

UNICORN_THREADS = """\
🦄【ユニコーンS 2026 完全事前分析】
2026年5月2日（土）京都ダート1900m G3

3歳限定のダート重賞。将来のダート路線を占う一戦です。

━━━━━━━━━━━━━━
◎ 本命候補
━━━━━━━━━━━━━━

【メルカントゥール】
前走阪神1勝クラスを4馬身差で圧勝。スケールの違いを見せつけた。
追い切りでも力強い伸びを見せており状態は最高潮。
京都ダート1900mの向正面からの持続力勝負に最も適したタイプ。

【ケイアイアギト】
サウジダービー5着の国際経験馬。
帰国後の調整は良好で、精神的な成長と能力の高さが同居する大物。
今回の出走馬で最も「将来のダートG1を狙える」と評価できる一頭。

━━━━━━━━━━━━━━
△ 穴馬候補
━━━━━━━━━━━━━━

【ソルチェリア】
京都コース経験が豊富な先行馬。
追い切りS評価で状態も上向き。
本命2頭に人気が集中すれば単勝妙味が生まれる可能性あり。

【シルバーレシオ】
差し切りを見せた前走から長く脚を使える持続力が魅力。
追い切りA評価で出走馬の中では安定感がある。

━━━━━━━━━━━━━━
🚫 消し馬（確定）
━━━━━━━━━━━━━━
✗ シャローファースト：追い切りC評価・反応不足
✗ フクシマブリルハム：前走9着・追い切りC評価・一変待ち

━━━━━━━━━━━━━━
📊 攻略データ
━━━━━━━━━━━━━━
・4コーナー3番手以内が圧倒的有利（過去50走で27勝）
・スピードのみならずスタミナが必要な1900m
・前走で勝ち切っている馬の好走が目立つ

枠順確定後に最終予想と買い目を発表します🙏

#ユニコーンステークス #競馬予想 #AI競馬予想 #アスメシ競馬"""


# ════════════════════════════════════════════════════
# 京王杯スプリングカップ 投稿テキスト
# 2026/05/02 東京芝1400m G2
# ════════════════════════════════════════════════════

KEIO_X1 = """\
🏇【京王杯スプリングカップ 2026 事前予想】
5/2（土）東京芝1400m G2
安田記念への優先出走権レース

◎ ウイントワイライト
東京コースで4勝の地力トップ🔥
最速上がり33.1秒を連発するキレ者
開幕直後の速い東京芝は絶好条件

△ ダノンセンチュリー（穴）
東京1600m条件戦3連勝の実力馬
最速上がり32.6秒の末脚は全馬中ダントツ
人気より走る可能性のある隠れた一頭

枠順確定後に最終予想🙏
安田記念の前哨戦、要チェック！

#京王杯スプリングカップ #競馬予想 #アスメシ競馬"""

KEIO_X2 = """\
🏇【京王杯SC 消し馬・データ傾向】

【消し候補🚫】
✗ ファンダム（距離が短すぎ・1600〜1800m向き）
✗ ワールズエンド（5ヶ月休養明け・G2対応に疑問）
✗ ヤブサメ（東京初参戦・左回りが苦手の懸念）

【データキーワード📊】
・4歳馬の複勝率31.3%が最高 → 若い馬を優先
・開幕2週目の東京芝は馬場が速い
  → 末脚（上がり3F）最速の馬が有利
・1着馬には安田記念への優先出走権あり
  → 本気度の高いメンバーが集まる

シンプルに「東京で末脚を使える馬」を買う！

#京王杯スプリングカップ #競馬 #アスメシ競馬"""

KEIO_THREADS = """\
🏇【京王杯スプリングカップ 2026 完全事前分析】
2026年5月2日（土）東京芝1400m G2

安田記念（G1）への優先出走権が懸かる重要前哨戦。
スプリンターの頂点を目指す一戦です。

━━━━━━━━━━━━━━
◎ 本命候補
━━━━━━━━━━━━━━

【ウイントワイライト】
東京競馬場で4勝を挙げる圧倒的な東京巧者。
最速上がり33.1秒を連発する末脚が最大の武器。
開幕2週目で馬場が速い時期の東京芝1400mは、まさに得意の土俵。
安田記念を視野に入れた本気の出走で状態面も万全の見込み。

━━━━━━━━━━━━━━
△ 穴馬候補
━━━━━━━━━━━━━━

【ダノンセンチュリー】
東京芝1600mの条件戦を3連勝中の上り馬。
最速上がり32.6秒の末脚は今回の出走馬全体でもトップクラスのキレ。
初の重賞挑戦で人気が割れる可能性があり、オッズ次第では狙い目。
「東京×末脚勝負」のレースパターンは完全にこの馬向き。

━━━━━━━━━━━━━━
🚫 消し馬（確定・候補）
━━━━━━━━━━━━━━
✗ ファンダム：1600〜1800m向きのタイプ。1400mは短すぎる
✗ ワールズエンド：約5ヶ月の休養明けでG2の壁は高い
✗ ヤブサメ：東京初参戦で左回りへの適性に疑問

━━━━━━━━━━━━━━
📊 過去データ・傾向
━━━━━━━━━━━━━━
・4歳馬の複勝率31.3%が全年齢でトップ → 若い世代を重視
・開幕2週目の東京芝はタイムが速くなりやすい
  → 末脚（上がり3F）最速の馬が圧倒的に有利
・1番人気40.0%・2番人気60.0%の連対率 → 堅い傾向
・安田記念優先出走権レース → メンバーの本気度が高い

先週4/26のフローラS同様「東京芝×末脚型」が決め手。
D.レーン騎手など外国人騎手が絡む場合は追加注目🔥

枠順確定後に最終予想と買い目を発表します🙏

#京王杯スプリングカップ #競馬予想 #AI競馬予想 #アスメシ競馬"""


# ════════════════════════════════════════════════════
# note記事（2レースまとめ）
# ════════════════════════════════════════════════════

NOTE_LEAD = """\
　5月2日（土）は京都と東京でダブル重賞開催！ユニコーンステークス（京都ダート1900m G3）と京王杯スプリングカップ（東京芝1400m G2）の2レースを事前分析します。
　先週のG2ダブル的中（回収率264%🔥）の勢いのまま、今週も狙い馬を全部晒します。馬券の組み立ては枠順確定後に発表します。"""


# ── メイン ────────────────────────────────────────────

def main():
    doc = Document()

    # ══ 表紙 ══
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026年5月2日（土）土曜重賞 事前予想 SNS投稿案")
    set_font(run, size_pt=16, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("ユニコーンS（京都ダート1900m G3）／京王杯SC（東京芝1400m G2）")
    set_font(run, size_pt=10, color=RGBColor(0x88, 0x88, 0x88))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("【投稿順】ユニコーンS ①②  →  京王杯SC ①②  →  Threads各1本  →  note記事")
    set_font(run, size_pt=9, color=RGBColor(0x88, 0x44, 0x00))

    doc.add_paragraph()

    # ══════════════════════════════
    # ユニコーンステークス
    # ══════════════════════════════
    add_section_bar(doc, "━━━ 🦄 ユニコーンステークス（京都ダート1900m G3） ━━━",
                    RGBColor(0x6A, 0x1B, 0x9A))
    doc.add_paragraph()

    # X
    add_label(doc, "【X投稿①】本命・穴馬発表", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, UNICORN_X1, "F3E5F5",
            note="レース前日（5/1）または当日朝（5/2）に投稿")

    add_label(doc, "【X投稿②】消し馬・データ傾向", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, UNICORN_X2, "F3E5F5",
            note="投稿①の数時間後に投稿")

    # Threads
    add_label(doc, "【Threads】完全事前分析（1投稿）", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, UNICORN_THREADS, "F5F5F5",
            note="X投稿①②を1本に統合した長文版")

    doc.add_page_break()

    # ══════════════════════════════
    # 京王杯スプリングカップ
    # ══════════════════════════════
    add_section_bar(doc, "━━━ 🏇 京王杯スプリングカップ（東京芝1400m G2） ━━━",
                    RGBColor(0x0D, 0x47, 0xA1))
    doc.add_paragraph()

    # X
    add_label(doc, "【X投稿①】本命・穴馬発表", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, KEIO_X1, "E3F2FD",
            note="レース前日（5/1）または当日朝（5/2）に投稿")

    add_label(doc, "【X投稿②】消し馬・データ傾向", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, KEIO_X2, "E3F2FD",
            note="投稿①の数時間後に投稿")

    # Threads
    add_label(doc, "【Threads】完全事前分析（1投稿）", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, KEIO_THREADS, "F5F5F5",
            note="X投稿①②を1本に統合した長文版")

    doc.add_page_break()

    # ══════════════════════════════
    # note記事（2レースまとめ）
    # ══════════════════════════════
    add_section_bar(doc, "━━━ note記事（2レースまとめ版） ━━━",
                    RGBColor(0xC2, 0x18, 0x5B))
    doc.add_paragraph()

    # タイトル
    p = doc.add_paragraph()
    run = p.add_run("【土曜重賞2026 事前予想】ユニコーンS＆京王杯SC 本命・穴馬・消し馬を全部晒す")
    set_font(run, size_pt=15, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    run = p.add_run("2026年5月2日（土）　アスメシ競馬予想")
    set_font(run, size_pt=9, color=RGBColor(0x99, 0x99, 0x99))

    doc.add_paragraph()
    add_body(doc, NOTE_LEAD)
    doc.add_paragraph()

    # ── ユニコーンS ──
    add_heading(doc, "① ユニコーンステークス（京都ダート1900m G3）", level=2)
    doc.add_paragraph()

    add_heading(doc, "本命候補", level=3)
    add_body(doc, "　◎ メルカントゥール：前走1勝クラスを4馬身差で圧勝。追い切りも力強く、京都1900mの持続力勝負にベストマッチの先行型です。")
    add_body(doc, "　◎ ケイアイアギト：サウジダービー5着の国際経験馬。帰国後の調整良好で、今回の出走馬の中では最も大物感があります。")
    doc.add_paragraph()

    add_heading(doc, "穴馬候補", level=3)
    add_body(doc, "　△ ソルチェリア：京都コース経験豊富な先行馬。追い切りS評価で調子もいい。上位2頭に人気が集中すれば妙味が生まれる。")
    add_body(doc, "　△ シルバーレシオ：長く脚を使える持続力型。追い切りA評価で安定感あり。")
    doc.add_paragraph()

    add_box(doc, """\
🚫 消し馬
・シャローファースト（追い切りC評価・反応不足）
・フクシマブリルハム（前走9着・追い切りC評価）

📊 データキーワード
・4コーナー3番手以内が圧倒的有利（前に行ける馬が勝つコース）
・前走で勝ち切っている馬の好走が目立つ → メルカントゥール・ケイアイアギトが該当""",
            bg_color="FFF9C4")

    doc.add_paragraph()

    # ── 京王杯SC ──
    add_heading(doc, "② 京王杯スプリングカップ（東京芝1400m G2）", level=2)
    doc.add_paragraph()

    add_heading(doc, "本命候補", level=3)
    add_body(doc, "　◎ ウイントワイライト：東京4勝・最速上がり33.1秒を連発する東京巧者。開幕直後の速い馬場は得意条件。安田記念を見据えた本気の出走で状態も万全。")
    doc.add_paragraph()

    add_heading(doc, "穴馬候補", level=3)
    add_body(doc, "　△ ダノンセンチュリー：東京1600m条件戦3連勝・最速上がり32.6秒という全馬トップのキレ。初重賞で人気が割れれば最大の狙い目。先週フローラSと同じ「東京×末脚型」のパターン。")
    doc.add_paragraph()

    add_box(doc, """\
🚫 消し馬
・ファンダム（1400mは短すぎる・1600〜1800m向き）
・ワールズエンド（5ヶ月休養明け・G2対応に疑問）
・ヤブサメ（東京初参戦・左回り適性不明）

📊 データキーワード
・4歳馬の複勝率31.3%が全年齢でトップ → 若い世代を重視
・開幕直後の東京芝は末脚（上がり3F）最速馬が圧倒的有利
・先週フローラSとの共通パターン：東京芝×差し馬×外国人騎手も注目""",
            bg_color="FFF9C4")

    doc.add_paragraph()

    # 総括
    add_heading(doc, "今週の狙い方まとめ", level=2)
    doc.add_paragraph()

    add_box(doc, """\
【土曜2レースの共通テーマ】

ユニコーンS（ダート1900m）
→ 前に行ける持続力型・前走好内容の馬を中心
→ 先行有利コースなので追込み馬は割引

京王杯SC（東京芝1400m）
→ 東京コース実績×上がり最速歴の馬が鉄板
→ 先週フローラSと同じ末脚型パターンを継続

馬券は枠順確定後に最終発表！
フォローお忘れなく🙏""",
            bg_color="E8F5E9")

    doc.add_paragraph()

    # ハッシュタグ
    add_heading(doc, "推奨ハッシュタグ", level=2)
    doc.add_paragraph()

    add_label(doc, "ユニコーンS用", RGBColor(0x6A, 0x1B, 0x9A))
    add_box(doc, """\
#ユニコーンステークス #競馬予想 #AI競馬予想 #ダート競馬
#3歳ダート #重賞予想 #アスメシ競馬 #競馬""",
            bg_color="F3E5F5")

    add_label(doc, "京王杯SC用", RGBColor(0x0D, 0x47, 0xA1))
    add_box(doc, """\
#京王杯スプリングカップ #競馬予想 #AI競馬予想 #重賞予想
#安田記念 #スプリント #アスメシ競馬 #競馬""",
            bg_color="E3F2FD")

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
