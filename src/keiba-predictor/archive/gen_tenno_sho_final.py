"""
天皇賞・春 2026 枠順確定後 最終予想
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
OUTPUT_PATH = OUTPUT_DIR / "20260503_天皇賞春_枠順確定後予想SNS.docx"


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
    set_font(run, size_pt=13, bold=True, color=color or RGBColor(0x0F, 0x47, 0x61))

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


# ════════════════════════════════════════════════════
# 投稿テキスト
# ════════════════════════════════════════════════════

# ─── 枠順速報（最初に出す）───
X_WAKU = """\
🏇【天皇賞・春 2026 枠順確定】
5/3（日）京都芝3200m G1 全15頭

⚠️ スティンガーグラス回避
（追い切り後の歩様不良・次走：宝塚記念）

注目の枠順はこちら👇

2枠3番 アドマイヤテラ（武豊）
4枠7番 クロワデュノール（北村友一）
7枠12番 ヘデントール（C.ルメール）
3枠4番 アクアヴァーナル（松山弘平）

枠順確定後の予想は次のツイートで！
#天皇賞春 #競馬 #アスメシ競馬"""

# ─── 最終予想（本命発表）───
X_FINAL = """\
🏇【天皇賞・春 2026 枠順確定後予想】
枠が決まった！本命はこれだ！

◎ 3番 アドマイヤテラ（武豊）
2枠3番・内枠確保🔥
武豊×京都×先行×内枠 = 完璧な条件
阪神大賞典コースレコード圧勝の実力
スティンガーグラス回避で展開もさらに向く

○ 7番 クロワデュノール（北村友一）
4枠7番・中枠で折り合い◎
日本ダービー馬の地力は最上位
初3200mが唯一の壁だが好枠で対応に集中

▲ 12番 ヘデントール（C.ルメール）
7枠12番・やや外がネック
昨年覇者・ルメールのさばきに注目

△ 4番 アクアヴァーナル（松山弘平）
3枠4番・内枠で京都相性100%を発揮🎯
人気以上に走る穴の筆頭

買い目は別ツイートで公開します🙏
#天皇賞春 #競馬予想 #アスメシ競馬"""

# ─── 買い目・消し馬 ───
X_KAIMOKU = """\
🏇【天皇賞・春 2026 買い目・消し馬】

【即消し🚫】
✗ 1番 ヴェルミセル（前走海外11着）
✗ 5番 ケイアイサンデラ（前走障害11着）
✗ 9番 プレシャスデイ（格下・実績なし）
✗ 13番 ミステリーウェイ（8歳・前走14着）

【消し候補】
✗ 11番 タガノデュード（3000m超は今回初）
✗ 10番 マイネルカンパーナ（前走7着止まり）

【買い目（案）💰】
単勝   ③アドマイヤテラ
馬連   ③-⑦
ワイド  ③-⑫  ③-④

過去10年全て1〜3人気が勝利
堅い決着を本線で勝負！

#天皇賞春 #馬券 #アスメシ競馬"""

# ─── Threads（最終予想まとめ）───
THREADS_FINAL = """\
🏇【天皇賞・春 2026 枠順確定後予想】
2026年5月3日（日）京都芝3200m G1

枠順が確定しました。スティンガーグラスの回避もあり、枠順を踏まえた予想を発表します。

━━━━━━━━━━━━━━━━
⚠️ 重要情報：スティンガーグラス回避
━━━━━━━━━━━━━━━━
穴馬候補に挙げていたスティンガーグラスが
追い切り後の歩様不良で回避。次走は宝塚記念。
これにより展開はさらに落ち着いた流れになりやすく、
先行馬のアドマイヤテラに有利に働きます。

━━━━━━━━━━━━━━━━
◎ 本命：3番 アドマイヤテラ（武豊）
━━━━━━━━━━━━━━━━
2枠3番という最高の内枠を引きました。
阪神大賞典コースレコード勝ちの実力＋武豊騎手×京都コース。
先週4/26のマイラーズCで同じパターン（武豊×京都×先行）が完璧に機能したことは記憶に新しいはず。
スティンガーグラスが回避したことで競り合う先行馬が減り、理想のペースで運べる可能性が高まりました。
調教は最終週もポリトラック単走で余裕を持った仕上げ。万全の状態です。

━━━━━━━━━━━━━━━━
○ 対抗：7番 クロワデュノール（北村友一）
━━━━━━━━━━━━━━━━
日本ダービー馬×大阪杯G1制覇の能力最上位。
4枠7番の中枠は「極端な内外ではない好枠」で折り合いに集中できます。
唯一の課題は初の3200m。距離適性の問答は当日走ってみないとわかりませんが、
能力の高さで乗り越えてくる可能性十分です。
1人気（2.3倍）と評価されている以上、軸から外すのはリスクが高い。

━━━━━━━━━━━━━━━━
▲ 3番手：12番 ヘデントール（C.ルメール）
━━━━━━━━━━━━━━━━
昨年の覇者。コースの経験・距離適性はメンバー中で実証済み。
7枠12番はやや外がネックで道中のロスが気になりますが、
ルメール騎手の位置取りの上手さでカバーできれば。
3200mの適性が一番高い馬として、馬券に押さえる価値あり。

━━━━━━━━━━━━━━━━
△ 穴：4番 アクアヴァーナル（松山弘平）
━━━━━━━━━━━━━━━━
3枠4番の内枠！京都コース複勝率100%のこの馬に内枠は最高の条件。
牝馬56kgの軽斤量も長距離スタミナ勝負で有利。
阪神大賞典2着（アドマイヤテラの直後）で実力も証明済み。
12.3倍という人気は明らかに過小評価。3連系の相手として必ず押さえます。

━━━━━━━━━━━━━━━━
🚫 消し馬（確定）
━━━━━━━━━━━━━━━━
✗ 1番 ヴェルミセル（前走海外11着）
✗ 5番 ケイアイサンデラ（前走障害11着）
✗ 9番 プレシャスデイ（格下）
✗ 13番 ミステリーウェイ（8歳・前走14着）
✗ 11番 タガノデュード（3000m超は今回初）

━━━━━━━━━━━━━━━━
💰 買い目（案）
━━━━━━━━━━━━━━━━
単勝   ③ アドマイヤテラ
馬連   ③-⑦
ワイド  ③-⑫ / ③-④

過去10年で勝ち馬は全て1〜3番人気。
堅い決着を本線に、内枠先行のアドマイヤテラを信頼します🙏

#天皇賞春 #競馬予想 #AI競馬予想 #アスメシ競馬"""


# ════════════════════════════════════════════════════
# note記事（最終予想版）
# ════════════════════════════════════════════════════

NOTE_LEAD = """\
　枠順が確定しました。さらにスティンガーグラスの直前回避という情報も飛び込んできたため、枠順を踏まえた予想をお届けします。
　結論から言えば、◎本命は アドマイヤテラ（2枠3番・武豊）に一本化。枠順確定でさらに確信が深まりました。"""


def main():
    doc = Document()

    # ══ 表紙 ══
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("天皇賞・春 2026 枠順確定後予想 SNS投稿案")
    set_font(run, size_pt=16, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026年5月3日（日）京都競馬場 芝3200m G1 ／ 全15頭（スティンガーグラス回避）")
    set_font(run, size_pt=9, color=RGBColor(0x88, 0x88, 0x88))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("◎アドマイヤテラ（2枠3番）  ○クロワデュノール（4枠7番）  ▲ヘデントール（7枠12番）  △アクアヴァーナル（3枠4番）")
    set_font(run, size_pt=10, bold=True, color=RGBColor(0xB7, 0x1C, 0x1C))

    doc.add_paragraph()

    # ══ 確定枠順表 ══
    add_section_bar(doc, "━━━ 枠順確定表（全15頭） ━━━", RGBColor(0x1B, 0x5E, 0x20))
    doc.add_paragraph()
    add_box(doc, """\
枠  馬番  馬名               騎手         オッズ   評価
─────────────────────────────────────────────────────────
1    1   ヴェルミセル        鮫島克駿     110.0倍  即消し
2    2   サンライズソレイユ   池添謙一     100.0倍  消し
2    3   アドマイヤテラ      武豊          3.6倍  ◎本命★
3    4   アクアヴァーナル    松山弘平      12.3倍  △穴★
3    5   ケイアイサンデラ    藤懸貴志     230.0倍  即消し
4    6   エヒト             川田将雅      47.9倍  消し
4    7   クロワデュノール    北村友一       2.3倍  ○対抗★
5    8   シンエンペラー      岩田望来      22.6倍  様子見
5    9   プレシャスデイ      吉村誠之助   200.0倍  消し
6   10   マイネルカンパーナ  津村明秀      78.3倍  消し
6   11   タガノデュード      古川吉洋      26.6倍  消し
7   12   ヘデントール       C.ルメール     5.2倍  ▲3番手★
7   13   ミステリーウェイ    松本大輝     140.0倍  即消し
8   14   ホーエリート       戸崎圭太      32.8倍  様子見
8   15   ヴェルテンベルク    松若風馬     130.0倍  消し
─────────────────────────────────────────────────────────
※ スティンガーグラス：回避（追い切り後の歩様不良・次走宝塚記念）""",
        bg_color="F1F8E9")

    doc.add_page_break()

    # ══ X投稿 ══
    add_section_bar(doc, "━━━ X（Twitter）投稿 ━━━", RGBColor(0x1D, 0xA1, 0xF2))
    doc.add_paragraph()

    add_label(doc, "【投稿①】枠順速報（確定直後すぐ）", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_WAKU, "EBF5FB",
            note="枠順発表直後（4/30〜5/1）に最速投稿")

    add_label(doc, "【投稿②】枠順確定後予想・本命発表", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_FINAL, "EBF5FB",
            note="枠順速報の数時間後〜前日夜に投稿")

    add_label(doc, "【投稿③】買い目・消し馬", RGBColor(0x1D, 0xA1, 0xF2))
    add_box(doc, X_KAIMOKU, "EBF5FB",
            note="レース当日朝（5/3）に投稿")

    doc.add_page_break()

    # ══ Threads ══
    add_section_bar(doc, "━━━ Threads投稿（枠順確定後予想まとめ版） ━━━", RGBColor(0x00, 0x00, 0x00))
    doc.add_paragraph()

    add_label(doc, "【Threads】枠順確定後の予想まとめ（1投稿）", RGBColor(0x00, 0x00, 0x00))
    add_box(doc, THREADS_FINAL, "F5F5F5",
            note="X投稿①〜③を全統合。前日夜〜当日朝に投稿")

    doc.add_page_break()

    # ══ note記事 ══
    add_section_bar(doc, "━━━ note記事（枠順確定後予想版） ━━━", RGBColor(0xC2, 0x18, 0x5B))
    doc.add_paragraph()

    p = doc.add_paragraph()
    run = p.add_run("【天皇賞・春 2026 枠順確定後予想】内枠＆武豊で本命確信。◎アドマイヤテラで勝負する理由")
    set_font(run, size_pt=15, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    run = p.add_run("2026年5月3日（日）京都競馬場 芝3200m G1　アスメシ競馬予想")
    set_font(run, size_pt=9, color=RGBColor(0x99, 0x99, 0x99))

    doc.add_paragraph()
    add_body(doc, NOTE_LEAD)
    doc.add_paragraph()

    # スティンガーグラス回避
    add_heading(doc, "直前情報：スティンガーグラス回避", level=2)
    doc.add_paragraph()
    add_box(doc, """\
スティンガーグラス（友道厩舎）が天皇賞・春を回避。
理由：「追い切り後の歩様がいつもより力強さに欠ける」（友道調教師コメント）
次走：宝塚記念（6月14日・阪神芝2200m）に照準を切り替え。

影響：先行馬が1頭減り、ペースはさらに落ち着く見込み。
     逃げ・先行有利の展開になりやすく、アドマイヤテラにとって追い風。""",
        bg_color="FFEBEE")

    doc.add_paragraph()

    # 本命
    add_heading(doc, "◎ 本命：3番 アドマイヤテラ（武豊）", level=2)
    doc.add_paragraph()
    add_body(doc, "　2枠3番の内枠を引きました。これで本命に確信が持てました。")
    doc.add_paragraph()
    add_box(doc, """\
本命の根拠（4点）

① 阪神大賞典コースレコード圧勝：前哨戦→本番の直結ローテ
② 武豊×京都×先行：先週マイラーズCで完璧に証明したパターン
③ 2枠3番（内枠）：内ラチ沿いを確保しやすく道中のロスが最小
④ スティンガーグラス回避：先行馬が1頭減り展開がさらに向く""",
        bg_color="E8F5E9")

    doc.add_paragraph()

    # 対抗
    add_heading(doc, "○ 対抗：7番 クロワデュノール（北村友一）", level=2)
    doc.add_paragraph()
    add_body(doc, "　4枠7番の中枠。極端な内外でなく折り合いに集中できる「好枠」と評されています。日本ダービー×大阪杯G1の実力は文句なく最上位。初の3200mという課題だけが残りますが、能力と枠の組み合わせを考えると外すのはリスクが高い対抗評価です。")
    doc.add_paragraph()

    # 3番手
    add_heading(doc, "▲ 3番手：12番 ヘデントール（C.ルメール）", level=2)
    doc.add_paragraph()
    add_body(doc, "　7枠12番。昨年の勝ち馬で3200mの経験・適性はメンバー中で最も実証済み。外枠でのロスをルメール騎手がどうさばくかがポイントで、上手くいけば昨年同様の差し込みが期待できます。5.2倍は実績を考えると妙味のあるオッズです。")
    doc.add_paragraph()

    # 穴馬
    add_heading(doc, "△ 穴馬：4番 アクアヴァーナル（松山弘平）", level=2)
    doc.add_paragraph()
    add_body(doc, "　3枠4番の内枠！これがこの馬の最大の武器になります。京都コース複勝率100%の相性に加えて、牝馬56kgの軽斤量もスタミナ消耗戦で有利。12.3倍は明らかに過小評価で、3連系の相手として筆頭に押さえます。")
    doc.add_paragraph()

    # 消し馬
    add_heading(doc, "消し馬（確定）", level=2)
    doc.add_paragraph()
    add_box(doc, """\
即消し
✗  1番 ヴェルミセル      前走海外11着・状態疑問
✗  5番 ケイアイサンデラ   前走障害11着・芝G1は別世界
✗  9番 プレシャスデイ     格下・重賞実績なし
✗ 13番 ミステリーウェイ   8歳・前走14着惨敗

消し候補
✗ 11番 タガノデュード     3000m超は今回が初・スピード型
✗ 10番 マイネルカンパーナ  前走7着止まり・上位馬との差大""",
        bg_color="FFEBEE")

    doc.add_paragraph()

    # 買い目
    add_heading(doc, "買い目（案）", level=2)
    doc.add_paragraph()
    add_box(doc, """\
単勝   ③ アドマイヤテラ         → 軸として最も信頼
馬連   ③-⑦                   → 本命×対抗の鉄板組み合わせ
ワイド  ③-⑫                   → 本命×昨年覇者（5.2倍の妙味）
ワイド  ③-④                   → 本命×穴（内枠×京都100%）

【過去10年データ確認】
勝ち馬は全て1〜3番人気 → 堅い決着を本線に""",
        bg_color="FFF9C4")

    doc.add_paragraph()

    # まとめ
    add_heading(doc, "まとめ", level=2)
    doc.add_paragraph()
    add_body(doc, "　枠順確定とスティンガーグラス回避で、◎アドマイヤテラの信頼度がさらに上がりました。武豊×京都×内枠×前哨戦圧勝という条件が全て揃ったこの馬を中心に据えます。")
    doc.add_paragraph()
    add_body(doc, "　対抗クロワデュノールの初3200mだけが唯一の懸念材料です。当日のパドック・返し馬の状態も確認しながら参考にしてください。結果は当日夕方にご報告します！")
    doc.add_paragraph()

    # ハッシュタグ
    add_heading(doc, "推奨ハッシュタグ", level=2)
    doc.add_paragraph()
    add_box(doc, """\
#天皇賞春 #天皇賞 #競馬予想 #AI競馬予想 #重賞予想
#G1 #京都競馬場 #アドマイヤテラ #クロワデュノール
#武豊 #競馬収支 #アスメシ競馬 #馬券""",
        bg_color="F3E5F5",
        note="13個。レース当日は #天皇賞春2026 を追加推奨")

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
