"""
2026/04/26 振り返りノート記事生成
フローラS・マイラーズC G2ダブル的中 全力振り返り
"""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート\20260426")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "20260426_note振り返り記事_v2.docx"


def set_font(run, size_pt=11, bold=False, color=None, font_name="游明朝"):
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


def set_gothic(run, size_pt=11, bold=False, color=None):
    set_font(run, size_pt=size_pt, bold=bold, color=color, font_name="游ゴシック")


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    if level == 1:
        run = p.add_run(text)
        set_gothic(run, size_pt=18, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    elif level == 2:
        run = p.add_run(f"▍ {text}")
        set_gothic(run, size_pt=14, bold=True, color=RGBColor(0x0F, 0x47, 0x61))
    elif level == 3:
        run = p.add_run(f"◆ {text}")
        set_gothic(run, size_pt=12, bold=True, color=RGBColor(0x33, 0x66, 0x99))


def add_body(doc, text, size_pt=11, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(0.8)
    run = p.add_run(text)
    set_font(run, size_pt=size_pt)
    return p


def add_box(doc, lines, bg_color="EBF5FB", left_border_color=None):
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
        set_gothic(run, size_pt=10.5)
    doc.add_paragraph()


def add_separator(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─")
    set_gothic(run, size_pt=10, color=RGBColor(0xBB, 0xBB, 0xBB))


def main():
    doc = Document()

    # ══ タイトル ══
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("【G2ダブル的中🔥】フローラS＆マイラーズC 全力振り返り")
    set_gothic(run, size_pt=18, bold=True, color=RGBColor(0x0F, 0x47, 0x61))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("2026年4月26日（日）　アスメシ競馬予想")
    set_gothic(run, size_pt=10, color=RGBColor(0x88, 0x88, 0x88))

    doc.add_paragraph()

    # ══ リード文 ══
    add_body(doc, "　4月26日は、フローラステークス（東京G2）と読売マイラーズカップ（京都G2）の2重賞が開催されました。")
    add_body(doc, "　結果から先に言うと——")
    doc.add_paragraph()

    add_box(doc, [
        "🌸 フローラS G2",
        "◎ラフターラインズ → 🥇1着✅",
        "○エンネ → 🥈2着✅",
        "単勝220円・馬連970円・ワイド310円 的中",
        "投資10,000円 → 回収22,500円（回収率225%）",
        "",
        "🏇 マイラーズC G2",
        "◎アドマイヤズーム → 🥇1着✅",
        "▲ベラジオボンド → 🥉3着✅",
        "単勝410円・ワイド900円 的中",
        "投資10,000円 → 回収30,300円（回収率303%）",
        "",
        "📊 2レース合計",
        "投資20,000円 → 回収52,800円（回収率264%）🔥",
    ], bg_color="FFF3E0")

    add_body(doc, "　G2 2レース連続で本命が1着。会心の予想になりました。")
    add_body(doc, "　今日の振り返りを徹底的にやっていきます。")

    doc.add_page_break()

    # ══ 第1章 ══
    add_heading(doc, "1. 事前予想の根拠を振り返る", level=2)
    doc.add_paragraph()

    add_heading(doc, "フローラステークス（東京芝2000m）", level=3)
    doc.add_paragraph()

    add_body(doc, "　本命◎に選んだのは5番ラフターラインズでした。AIモデルが弾き出した能力スコア1位（全馬中15.3%）の馬です。")
    doc.add_paragraph()

    add_body(doc, "選んだ3つの理由：", size_pt=11)
    add_body(doc, "① 過去5走の上がり3F平均が32.5秒（今回の出走馬でダントツ最速）", indent=True)
    add_body(doc, "② きさらぎ賞でも上がり1位を記録しており、末脚の安定性が高い", indent=True)
    add_body(doc, "③ 東京芝2000mの長い直線は末脚特化型の馬に最も有利なコース形態", indent=True)
    doc.add_paragraph()

    add_body(doc, "　対抗○にはエンネ（3人気）。こちらもAIスコア2位で、東京コースへの適性を評価しました。")
    add_body(doc, "　消しにしたゴバド（前走クイーンC13着）・ラベルセーヌ（2人気ながらAIスコア低位）も両馬とも着外で、消し判断は完璧でした。")

    doc.add_paragraph()
    add_separator(doc)
    doc.add_paragraph()

    add_heading(doc, "読売マイラーズカップ（京都芝1600m）", level=3)
    doc.add_paragraph()

    add_body(doc, "　本命◎にアドマイヤズーム（9番）。AIスコア1位（12.4%）、そして武豊騎手という最強コンビです。")
    doc.add_paragraph()

    add_body(doc, "選んだ3つの理由：", size_pt=11)
    add_body(doc, "① テンスピード337秒（18頭中断然最速）→ 京都内回りの逃げに最適なペース設定", indent=True)
    add_body(doc, "② 武豊騎手×京都内回り芝の組み合わせは過去の成績で高勝率", indent=True)
    add_body(doc, "③ 同コース（京都芝1600m）1走1勝の実績があり、適性は証明済み", indent=True)
    doc.add_paragraph()

    add_body(doc, "　消しにしたシックスペンス（前走フェブラリーS＝ダートから転戦）とエルトンバローズ（前走1人気13着惨敗）も両馬とも着外。消しの精度も100%でした。")

    doc.add_page_break()

    # ══ 第2章 ══
    add_heading(doc, "2. レース結果と予想の照合", level=2)
    doc.add_paragraph()

    add_heading(doc, "フローラS 予想 vs 結果", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "【予想】               【結果】",
        "◎5番 ラフターラインズ  → 🥇1着 ✅",
        "○13番 エンネ          → 🥈2着 ✅",
        "▲11番 ファムクラジューズ → 着外",
        "△6番 ペンダント        → 着外",
        "消 ゴバド・ラベルセーヌ  → 着外 ✅✅",
        "",
        "3着: リアライズルミナス（5人気）",
    ], bg_color="E8F5E9")

    add_body(doc, "　◎と○がワンツーフィニッシュ。D.レーン騎手が直線でスパートをかけると後続との差をグングン広げていき、AIが能力1位と評価した末脚をそのまま発揮してくれました。")
    add_body(doc, "　唯一の誤算は▲ファムクラジューズの着外でした。「テン最速」を評価しましたが、東京芝2000mでは前半の速さより後半の末脚が決め手になるため、この指標の適用が間違っていました。後述のPDCA分析で改善策を検討しています。")

    doc.add_paragraph()
    add_separator(doc)
    doc.add_paragraph()

    add_heading(doc, "マイラーズC 予想 vs 結果", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "【予想】                  【結果】",
        "◎9番 アドマイヤズーム     → 🥇1着 ✅",
        "○12番 ファーヴェント       → 着外",
        "▲7番 ベラジオボンド        → 🥉3着 ✅",
        "△10番 ウォーターリヒト     → 着外",
        "消 シックスペンス          → 着外 ✅",
        "消 エルトンバローズ         → 着外 ✅",
        "",
        "2着: ドラゴンブースト（9人気）→ ノーマーク",
    ], bg_color="E8F5E9")

    add_body(doc, "　武豊騎手のアドマイヤズームはスタートから先手を奪い、そのままコーナーを綺麗に回って後続を完封。まさにAIが描いたシナリオ通りの逃げ切りでした。")
    add_body(doc, "　2着に9人気のドラゴンブースト（丹内騎手）が突っ込んできたのは完全な想定外。馬連・3連複は惜しくも外れましたが、単勝・ワイドでしっかり回収できました。")
    add_body(doc, "　対抗○のファーヴェントは、AIのEV（期待値）指標が7.1倍と高く穴本命として期待していましたが不発。EVが高い低人気馬への投資は今後も慎重にしていく必要があります。")

    doc.add_page_break()

    # ══ 第3章 ══
    add_heading(doc, "3. 買い目の結果と収支", level=2)
    doc.add_paragraph()

    add_heading(doc, "フローラS 収支内訳", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "券種              投資額    払戻単価   回収額",
        "─────────────────────────────────────",
        "✅ 単勝 5番       3,000円  ×  220円  =  6,600円",
        "✅ ワイド 5-13    2,000円  ×  310円  =  6,200円",
        "✅ 馬連 5-13      1,000円  ×  970円  =  9,700円",
        "─────────────────────────────────────",
        "   合計           投資10,000円 → 回収22,500円",
        "   回収率 225%🎯",
    ], bg_color="F3E5F5")

    add_body(doc, "　単勝・ワイド・馬連の3点が全て的中。最も利益に貢献したのは馬連で、1,000円が9,700円に化けました。「1人気×3人気」の組み合わせで970円という配当は妙味があり、馬連への投資は正解でした。")

    doc.add_paragraph()

    add_heading(doc, "マイラーズC 収支内訳", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "券種              投資額    払戻単価   回収額",
        "─────────────────────────────────────",
        "✅ 単勝 9番       3,000円  ×  410円  = 12,300円",
        "✅ ワイド 9-7     2,000円  ×  900円  = 18,000円",
        "─────────────────────────────────────",
        "   合計           投資10,000円 → 回収30,300円",
        "   回収率 303%🔥",
    ], bg_color="F3E5F5")

    add_body(doc, "　単勝3,000円が12,300円に、ワイド2,000円が18,000円に。特にワイドは900円（9倍）という高配当で、ワイドへの投資が今日の最大の貢献でした。")
    add_body(doc, "　本命◎と▲の組み合わせで単勝・ワイドをしっかり確保できたことが、高回収率の要因です。")

    doc.add_paragraph()

    add_heading(doc, "2レース合計", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "🌸 フローラS  投資10,000円 → 回収22,500円（+12,500円）",
        "🏇 マイラーズC 投資10,000円 → 回収30,300円（+20,300円）",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 合計        投資20,000円 → 回収52,800円（+32,800円）",
        "   総回収率 264% 🔥",
    ], bg_color="FFF9C4")

    doc.add_page_break()

    # ══ 第4章 ══
    add_heading(doc, "4. 今週の傾向と総括", level=2)
    doc.add_paragraph()

    add_body(doc, "　4月26日の開催結果から読み取れる今週の傾向をまとめます。来週の予想に直接活かせるデータです。")
    doc.add_paragraph()

    add_heading(doc, "馬場・展開の傾向", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "【東京競馬場・芝】",
        "・良馬場継続。クッション値良好で末脚型が最大限機能する馬場状態。",
        "・直線の長さ（525m）が活きる「上がり勝負」。テンの速さより後半型が圧倒的有利。",
        "・上がり3Fトップの馬は複勝率80%超。前半のスピード指標は参考外。",
        "",
        "【京都競馬場・芝内回り】",
        "・こちらも良馬場。内回り特有の「コーナー加速＋直線短い」展開が顕著。",
        "・逃げ・先行勢が内ラチ沿いを確保できた場合に止まらないケース多数。",
        "・最終4コーナーの加速で先頭に立てる馬が圧倒的に有利。",
    ], bg_color="E8F5E9")

    doc.add_paragraph()

    add_heading(doc, "騎手・人気傾向", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "【今週の騎手傾向】",
        "・武豊騎手：京都内回り逃げで完封。テン最速×コース適性×同騎手の組み合わせは鉄板。",
        "・D.レーン騎手：東京芝で差し切り。外国人騎手の東京コースにおける安定感を再確認。",
        "・1人気が2/2レースで1着 → 今週は「堅い週」。荒れる要素（多頭数・ハンデ戦等）がなく、",
        "  能力上位馬が素直に結果に出る典型的な開催。",
        "",
        "【消しが機能した条件】",
        "・前走ダートからの転戦（シックスペンス）→ 即着外",
        "・前走10着以下の惨敗（エルトンバローズ13着）→ 即着外",
        "・同距離・同コース0走の初挑戦馬 → 統計的に着外率高",
    ], bg_color="E8F5E9")

    doc.add_paragraph()
    doc.add_page_break()

    # ══ 第5章 ══
    add_heading(doc, "5. 来週の狙い目とキーワード", level=2)
    doc.add_paragraph()

    add_body(doc, "　今週のデータをベースに、来週（5月第1週）の重賞で有効と考えられる指標・狙い目をまとめます。")
    doc.add_paragraph()

    add_heading(doc, "天皇賞・春（5/3 京都芝3200m G1）", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "🔑 キーワード: スタミナ指数・同コース実績・ペース耐性",
        "",
        "【狙い目の条件】",
        "・京都芝3200m実績あり（同コース1勝以上）",
        "・長距離（2400m以上）での上がり3Fが安定して34秒台以下",
        "・前走から距離延長よりも「距離短縮なし＝同距離前後」の馬",
        "・逃げ・先行勢がいる場合、武豊・川田など追込みより先行騎手が有利",
        "",
        "【警戒ポイント】",
        "・今週の傾向通り「良馬場×先行型」が有利。道悪になれば逆転要素あり。",
        "・3200mは出走数が少なくAIデータが薄い距離。同コース実績の有無で判断。",
    ], bg_color="E3F2FD")

    doc.add_paragraph()

    add_heading(doc, "NHKマイルC（5/4 東京芝1600m G1）", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "🔑 キーワード: 3歳マイル適性・東京コース適性・荒れ注意",
        "",
        "【狙い目の条件】",
        "・東京芝1600mの直線を活かせる差し・追込み型（今週の東京傾向と同じ）",
        "・上がり3F最速歴がある馬（33秒台が理想）",
        "・桜花賞・皐月賞からの直行馬よりも、マイル路線を使ってきた専門馬",
        "",
        "【荒れ要因】",
        "・3歳G1は能力差が小さく混戦になりやすい。1人気単勝5倍以上なら荒れる可能性大。",
        "・消し馬（前走二桁着順・距離不向きの短距離馬）を徹底することが回収率向上の鍵。",
    ], bg_color="E3F2FD")

    doc.add_paragraph()

    add_heading(doc, "今週データから導いた来週の「鉄則3か条」", level=3)
    doc.add_paragraph()

    add_box(doc, [
        "鉄則① 上がり3F最速馬を東京芝では最優先指標にする",
        "　　　 → 今週フローラSで完璧に証明。テンスピードは1600m以下専用。",
        "",
        "鉄則② 同コース実績×得意騎手の組み合わせは◎格上げ",
        "　　　 → 武豊×京都内回り、D.レーン×東京芝のパターンは引き続き高信頼。",
        "",
        "鉄則③ 良馬場が続く場合は「堅い日モード」を維持",
        "　　　 → 連続良馬場では1〜3人気が素直に結果を出しやすい。",
        "　　　   単勝・馬連に集中し、3連複・3連単は不要。",
    ], bg_color="FFF9C4")

    doc.add_paragraph()
    add_separator(doc)
    doc.add_paragraph()

    # ══ まとめ ══
    add_heading(doc, "まとめ", level=2)
    doc.add_paragraph()

    add_body(doc, "　2026年4月26日は、AIの能力スコア1位×良馬場×同コース実績×信頼騎手という条件が2レースともに揃い、理想的な的中が生まれました。")
    doc.add_paragraph()
    add_body(doc, "　今週の傾向は「良馬場・末脚型・先行有利（コース次第）」というシンプルなもので、馬場が変わらない限り来週も同じ軸で予想が機能すると考えています。")
    doc.add_paragraph()
    add_body(doc, "　来週は天皇賞・春・NHKマイルCとG1が連続します。今週得たデータをフル活用して、また結果を報告します。")
    doc.add_paragraph()

    add_box(doc, [
        "今週の総括（3行まとめ）",
        "",
        "1. 東京芝は上がり3F最速馬を最優先 / 京都内回りは逃げ×同コース騎手",
        "2. 良馬場継続中 → 堅い日モード有効。単勝・ワイド・馬連に集中",
        "3. 来週G1連続：天皇賞・春はスタミナ+同コース、NHKマイルCは荒れ注意",
    ], bg_color="FFF3E0")

    doc.add_paragraph()
    add_body(doc, "　来週の天皇賞・春とNHKマイルCの予想も全力で取り組みます。フォロー＆スキをいただけると励みになります🙏")
    add_body(doc, "　また来週もよろしくお願いします！")
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("アスメシ競馬予想｜2026.04.26")
    set_gothic(run, size_pt=9, color=RGBColor(0x88, 0x88, 0x88))

    doc.save(str(OUTPUT_PATH))
    print(f"保存完了: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
