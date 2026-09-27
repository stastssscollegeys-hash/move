# -*- coding: utf-8 -*-
"""
gen_final_sns_20260927.py — スプリンターズS 最終予想（当日版）のSNS投稿案
==========================================================================
前日版（20260927_スプリンターズS前日予想_SNS投稿案.docx）は残し、これは新規ファイル。

反映しているもの
  ・朝の実オッズ（08:42取得・16頭フル出走・取消なし）
  ・本日の馬場（曇・稍重）と、各馬の道悪実績による指数補正
  ・インフルエンサー/競馬サイト合算（4並列収集・日付検証済み）
  ・型判定 → 実測ROIによる買い方の選択（kaime_patterns / pattern_roi）

構成は確立済みフォーマット（2行ヘッダー → リード文 → ───── で挟んだ見出し1つ）。
1投稿1節。Threadsは500字以内。noteはマークダウン記号を使わない。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
R27 = ROOT / "20260927" / "research"
AM = json.loads((R27 / "final_am.json").read_text(encoding="utf-8"))
FN = json.loads((R27 / "final_sprinters.json").read_text(encoding="utf-8"))
BABA = json.loads((R27 / "baba_form.json").read_text(encoding="utf-8"))
SC = json.loads((ROOT / "20260926" / "research" / "score20_20260925.json").read_text(encoding="utf-8"))["スプリンターズS"]
H = {h["uma"]: h for h in SC["horses"]}

FONT = "游ゴシック"
CIRC = "⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
SEP = "─────────────────────"
TAG = "#競馬予想 #AI予想 #スプリンターズS #JRA"
HEAD = ["🏇【スプリンターズS G1】2026/09/27（日）",
        "━━ 中山競馬場 芝1200m / 16頭立て / 15:40発走 / 曇・稍重 ━━"]

T = {r["uma"]: r for r in FN["total_rank"]}
NAME = {u: r["name"] for u, r in T.items()}
RANKED = sorted(T.values(), key=lambda r: -r["total"])
M = FN["marks"]
HON, ANA = AM["hon"], AM["ana"]
MK = [("◎", M["◎"]), ("○", M["○"]), ("▲", M["▲"])] + [("△", u) for u in M["△"]]
PTS = AM["points"]
WET = {int(k): v for k, v in AM["wet_adj"].items()}


def c(n):
    n = int(n)
    return CIRC[n] if 0 <= n <= 20 else str(n)


def bf(u):
    d = BABA.get(str(u)) or BABA.get(u)
    if not d or not d["bad_n"]:
        return "道悪の出走なし"
    return f"道悪{d['bad_t3']}/{d['bad_n']}・良{d['good_t3']}/{d['good_n']}"


def set_font(run, size=10, bold=False, color=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def h1(doc, t):
    p = doc.add_paragraph(); set_font(p.add_run(t), 13, True, (20, 60, 140))


def h2(doc, t):
    p = doc.add_paragraph(); set_font(p.add_run(t), 11, True, (70, 70, 70))


def body(doc, t, size=10):
    for ln in str(t).split("\n"):
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2); set_font(p.add_run(ln), size)


def table(doc, rows):
    tb = doc.add_table(rows=0, cols=len(rows[0])); tb.style = "Table Grid"
    for i, row in enumerate(rows):
        cells = tb.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = ""
            set_font(cells[j].paragraphs[0].add_run(str(v)), 8.5, i == 0)
    doc.add_paragraph()


def box(doc, title, lines, limit=None):
    n = len("\n".join(lines))
    tag = f"［{n}字{'' if not limit else f'/{limit}字 ' + ('OK' if n <= limit else '⚠超過')}］"
    h2(doc, f"{title}　{tag}")
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    if limit and n > limit:
        print(f"[WARN] 超過 {title} {n}字")
    return n


def sec(doc, title, lead, heading, lines):
    box(doc, title, HEAD + [""] + lead + ["", SEP, heading, SEP, ""] + lines + ["", TAG])


# ================================================================================
doc = Document()
doc.styles["Normal"].font.name = FONT
doc.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
p = doc.add_paragraph()
set_font(p.add_run("スプリンターズS(G1) 最終予想（当日版）SNS投稿案"), 16, True, (20, 60, 140))
body(doc, "2026年9月27日(日) 中山 芝1200m 16頭 15:40発走／曇・稍重\n"
          f"朝の実オッズ（{FN['fetched_at'][11:16]}取得・16頭フル出走・出走取消なし）を反映した最終版。"
          "前日版とは別ファイル。")
doc.add_paragraph()

h1(doc, "SECTION 1｜最終予想印と買い目")
table(doc, [["印", "馬番", "馬名", "総合指数", "独自指数", "合算補正", "道悪補正", "人気", "道悪実績"]] +
      [[lab, c(u), NAME[u], T[u]["total"], T[u]["idx"], f"{T[u]['adj']:+.1f}",
        f"{WET.get(u, 0):+.1f}", f"{T[u]['pop']}番人気 {T[u]['odds']}倍", bf(u)] for lab, u in MK] +
      [["🔥", c(ANA), NAME[ANA], T[ANA]["total"], T[ANA]["idx"], f"{T[ANA]['adj']:+.1f}",
        f"{WET.get(ANA, 0):+.1f}", f"{T[ANA]['pop']}番人気 {T[ANA]['odds']}倍", bf(ANA)]])
table(doc, [["券種", "買い目", "金額", "推定配当", "的中なら", "実測的中率"]] +
      [[p_["t"], "-".join(f"{c(x)}{NAME[x]}" for x in p_["combo"]), f"{p_['amt']:,}円",
        f"約{p_['est']}倍", f"約{int(p_['amt'] * p_['est'] / 100) * 100:,}円", f"{p_['p'] * 100:.1f}%"]
       for p_ in sorted(PTS, key=lambda x: -x["amt"])] +
      [["合計", f"{len(PTS)}点", f"{AM['budget']:,}円", f"Σ(1/配当)={AM['over']}",
        f"1点以上当たる確率 {AM['hit'] * 100:.1f}%", ""]])
doc.add_paragraph()

h1(doc, "SECTION 2｜X投稿（7本・節ごと）")

sec(doc, "X① 最終予想印（発走2〜3時間前／印画像を添付）",
    ["本日の中山は曇・稍重。時計のかかる馬場です。",
     f"最終の本命は{c(HON)}{NAME[HON]}にしました。"],
    "🎯 最終予想印",
    [f"{lab} {c(u)}{NAME[u]}" for lab, u in MK] + [
        f"🔥 {c(ANA)}{NAME[ANA]}",
        "",
        "独自の20ファクター指数に、各競馬サイトとYouTube予想の見解を合算し、",
        "さらに本日の馬場（稍重）に合わせて各馬の道悪実績で補正しています。",
        "",
        "根拠はスレッドで👇"])

sec(doc, "X② 本命の根拠（①の返信）",
    [f"本命は{c(HON)}{NAME[HON]}です。",
     "指数そのものより、各サイトの評価が集まったことを重く見ました。"],
    f"◎ 本命 {c(HON)}{NAME[HON]}",
    [f"・総合指数{T[HON]['total']}（独自{T[HON]['idx']} ＋ 合算補正{T[HON]['adj']:+.1f}）でメンバー1位",
     f"・6つのソースが本命に指名（合算の補正がメンバー最大）",
     f"・追い切り {H[HON]['oikiri']}",
     f"・{H[HON]['why']['sc12']}",
     f"・最高実績は{H[HON]['why']['sc19']}",
     f"・脚質は{H[HON]['style']}、{H[HON]['waku']}枠",
     f"・道悪は{bf(HON)}",
     "",
     "本日の中山は稍重。昨日の芝は3着以内が差し7・逃げ6・先行5・追込3で、",
     "前も後ろも届いています。極端に前や後ろへ寄せる組み方はしません。"])

sec(doc, "X③ 印をつけた馬（②の返信）",
    ["相手は指数だけでなく、各サイトの評価と道悪実績を合わせて選びました。"],
    "○▲△ 印をつけた馬",
    sum([[f"{lab} {c(u)}{NAME[u]}（総合{T[u]['total']}・独自指数{T[u]['idx']}）",
          f"　{H[u]['why']['sc12']}／最高実績 {H[u]['why']['sc19']}",
          f"　追い切り {H[u]['oikiri']}／脚質 {H[u]['style']}／{H[u]['waku']}枠",
          f"　道悪 {bf(u)}", ""] for lab, u in MK[1:]], []))

sec(doc, "X④ 穴馬（③の返信）",
    [f"穴は{c(ANA)}{NAME[ANA]}です。",
     "選んだ理由は指数ではなく、道悪の実績です。"],
    f"🔥 穴 {c(ANA)}{NAME[ANA]}",
    [f"・道悪は{bf(ANA)}",
     f"・追い切り {H[ANA]['oikiri']}",
     f"・{H[ANA]['why']['sc12']}",
     f"・最高実績は{H[ANA]['why']['sc19']}",
     f"・脚質は{H[ANA]['style']}、{H[ANA]['waku']}枠",
     "",
     "良馬場では勝ちきれていませんが、道悪では崩れていません。",
     "市場は良馬場の成績で評価するので、馬場が渋るほど価値が上がる形です。"])

wet_up = sorted((u for u in WET if WET[u] > 0), key=lambda u: -WET[u])
wet_dn = sorted((u for u in WET if WET[u] < 0), key=lambda u: WET[u])
sec(doc, "X⑤ 馬場（④の返信）",
    ["本日の中山は曇・稍重。昨日は全12レースが重馬場でした。",
     "芝1200mの勝ちタイムは1分09秒7。良馬場なら1分07秒台のコースです。"],
    "🌱 馬場と道悪補正",
    ["各馬の道悪3着内率と良馬場3着内率の差を、指数に反映しました。",
     "",
     "【上げた馬】"] +
    [f"　{c(u)}{NAME[u]}　{WET[u]:+.1f}　{bf(u)}" for u in wet_up] +
    ["", "【下げた馬】"] +
    [f"　{c(u)}{NAME[u]}　{WET[u]:+.1f}　{bf(u)}" for u in wet_dn] +
    ["",
     "中山はCコース2週目で、3角から直線の内柵沿いに傷みが出ていると報じられています。",
     "昨日の3着以内の枠は2枠4・3枠4・7枠3・8枠3で、内外の偏りは小さめでした。"])

sec(doc, "X⑥ 買い方の選び方（⑤の返信）",
    ["買い方はレースごとに変えています。",
     "毎回同じ券種を使うのはやめました。"],
    "📊 この型に何が効くか",
    [f"本日は「{AM['pattern']['name']}」という型です。",
     f"（{AM['pattern']['desc']}）",
     "",
     "過去496レースの確定払戻で、型ごとにどの買い方が効くかを数えています。",
     "採用するのは、期間を前半と後半に分けて両方とも100%を超えたものだけ。",
     "片方だけ良い数字は偶然とみなします。",
     "",
     f"本日の型で選んだのは「{AM['structure']}」（{AM['kind']}）。",
     "先週まで使っていたワイドの流しは、この型では回収87%で下位でした。",
     "",
     "当たり外れより、この選び方が正しいかを見てもらえたらうれしいです。"])

sec(doc, "X⑦ 買い目（⑥の返信）",
    [f"買い目は合計{AM['budget']:,}円・{len(PTS)}点です。",
     f"1点以上当たる確率は{AM['hit'] * 100:.0f}%、当たればおよそ4倍で戻る形にしています。"],
    f"💰 買い目 合計{AM['budget']:,}円・{len(PTS)}点",
    [f"{p_['t']} {'-'.join(c(x) for x in p_['combo'])}　{p_['amt']:,}円"
     for p_ in sorted(PTS, key=lambda x: -x["amt"])] +
    ["",
     "推定配当と、当たったときの戻り"] +
    [f"　{'-'.join(f'{c(x)}{NAME[x]}' for x in p_['combo'])}　推定約{p_['est']}倍"
     f"／約{int(p_['amt'] * p_['est'] / 100) * 100:,}円" for p_ in sorted(PTS, key=lambda x: -x["amt"])] +
    ["",
     "推定配当が安い買い目ほど厚く、高い買い目ほど薄く置いています。",
     "どれが当たっても戻る額が揃うようにするためです。",
     f"推定配当の逆数を全部足すと{AM['over']}。1.0以下に収めました。",
     "",
     "金額は100円単位のみ。G1でも規定額から増やしません。"])

doc.add_page_break()
h1(doc, "SECTION 3｜Threads投稿（6本・各500字以内）")
TH = "🏇【スプリンターズS G1】9/27(日) 中山 芝1200m 16頭"

box(doc, "Threads 1/6 最終予想印", [
    TH, "",
    "本日の中山は曇・稍重。時計のかかる馬場です。", "",
] + [f"{lab} {c(u)}{NAME[u]}" for lab, u in MK] + [
    f"🔥 {c(ANA)}{NAME[ANA]}", "",
    "独自指数に各サイトの見解を合算し、道悪実績で補正しました。", "",
    "みなさんの本命はどの馬ですか？"], 500)

box(doc, "Threads 2/6 本命", [
    TH, "",
    f"本命は{c(HON)}{NAME[HON]}です。", "",
    f"・総合指数{T[HON]['total']}でメンバー1位",
    "・6つのソースが本命に指名",
    f"・{H[HON]['why']['sc12']}",
    f"・道悪は{bf(HON)}", "",
    "指数の高さより、各サイトの評価が集まったことを重く見ました。", "",
    "この本命、どう見ますか？"], 500)

box(doc, "Threads 3/6 馬場", [
    TH, "",
    "昨日の中山は全12レースが重馬場でした。",
    "芝1200mの勝ちタイムは1分09秒7。良馬場なら1分07秒台のコースです。", "",
    "各馬の道悪実績で指数を補正しています。", "",
] + [f"・{c(u)}{NAME[u]}　{WET[u]:+.1f}（{bf(u)}）" for u in wet_up[:3]] + [
    "",
    "馬場が渋ったとき、どこを見て買い目を変えますか？"], 500)

box(doc, "Threads 4/6 穴馬", [
    TH, "",
    f"穴は{c(ANA)}{NAME[ANA]}です。", "",
    f"・道悪{bf(ANA)}",
    f"・{H[ANA]['why']['sc12']}",
    f"・脚質は{H[ANA]['style']}", "",
    "良馬場では勝ちきれていませんが、道悪では崩れていません。",
    "市場は良馬場の成績で評価するので、馬場が渋るほど価値が出ます。", "",
    "穴馬、どうやって選んでいますか？"], 500)

box(doc, "Threads 5/6 買い方", [
    TH, "",
    "買い方をレースごとに変えることにしました。",
    "毎回同じ券種を使うのはやめます。", "",
    f"本日は「{AM['pattern']['name']}」という型です。",
    "過去496レースの払戻で、型ごとにどの買い方が効くかを数えました。",
    "前半と後半に分けて、両方100%を超えたものだけ採用します。", "",
    f"本日選んだのは「{AM['structure']}」です。", "",
    "みなさんは券種、レースごとに変えていますか？"], 500)

box(doc, "Threads 6/6 買い目", [
    TH, "",
    f"買い目は合計{AM['budget']:,}円・{len(PTS)}点です。", "",
] + [f"・{p_['t']} {'-'.join(c(x) for x in p_['combo'])}　{p_['amt']:,}円"
     for p_ in sorted(PTS, key=lambda x: -x["amt"])] + [
    "",
    "推定配当が安い買い目ほど厚く置いて、どれが当たっても戻る額が揃うようにしています。",
    f"推定配当の逆数の合計は{AM['over']}で、1.0以下に収めました。", "",
    "この配分、どう思いますか？"], 500)

doc.add_page_break()
h1(doc, "SECTION 4｜note記事（全文無料）")
N = ["こんにちは、アスメシ競馬予想です🍱",
     "明日の飯代を懸けて、データで競馬に挑んでいます。",
     "",
     f"結論を先に言います。スプリンターズSの本命は{c(HON)}{NAME[HON]}、",
     f"買い目は{AM['structure']}で{AM['budget']:,}円・{len(PTS)}点です。",
     "",
     "",
     "■ レース基本情報",
     "",
     "2026年9月27日(日) 中山競馬場 芝1200m 16頭立て 15時40分発走",
     "天候は曇、馬場は稍重です。",
     "",
     "",
     "■ 本日の馬場",
     "",
     "昨日9月26日の中山は、全12レースが重馬場でした。",
     "芝1200mの勝ちタイムは1分09秒7。良馬場なら1分07秒台が出るコースなので、",
     "2秒以上遅い計算になります。かなり時計のかかる馬場です。",
     "",
     "本日の発表は稍重。中山はCコース2週目で、3角から直線の内柵沿いに",
     "傷みが出ていると報じられています。",
     "",
     "昨日の芝で3着以内に入った21頭の脚質は、差し7・逃げ6・先行5・追込3。",
     "枠は2枠4・3枠4・7枠3・8枠3で、内外の偏りは小さめでした。",
     "前も後ろも届いているので、どちらかに寄せる組み方はしません。",
     "",
     "",
     "■ 道悪実績による補正",
     "",
     "各馬の道悪3着内率と良馬場3着内率の差を、指数に反映しました。",
     "サンプルが少ない馬は効かせないようにしています。",
     "",
     "上げた馬"]
N += [f"{c(u)}{NAME[u]}　{WET[u]:+.1f}　{bf(u)}" for u in wet_up]
N += ["", "下げた馬"]
N += [f"{c(u)}{NAME[u]}　{WET[u]:+.1f}　{bf(u)}" for u in wet_dn]
N += ["",
      "",
      "■ 総合指数",
      "",
      "独自の20ファクター指数に、各競馬サイトとYouTube予想の見解を合算しました。",
      "本命指名には重み、消し評価にはマイナスを付けています。",
      ""]
N += [f"{i}位 {c(r['uma'])}{r['name']}　総合{r['total']}（独自{r['idx']} 合算{r['adj']:+.1f}）"
      for i, r in enumerate(RANKED, 1)]
N += ["",
      "",
      "■ 最終予想印",
      ""]
N += [f"{lab} {c(u)}{NAME[u]}" for lab, u in MK] + [f"🔥 {c(ANA)}{NAME[ANA]}"]
N += ["",
      "",
      "■ 有力馬の詳細",
      ""]
for lab, u in MK:
    N += [f"{lab} {c(u)}{NAME[u]}（総合{T[u]['total']}・独自指数{T[u]['idx']}）",
          f"　追い切り {H[u]['oikiri']}／脚質 {H[u]['style']}／{H[u]['waku']}枠",
          f"　{H[u]['why']['sc12']}／最高実績 {H[u]['why']['sc19']}",
          f"　道悪 {bf(u)}", ""]
N += [f"🔥 {c(ANA)}{NAME[ANA]}（道悪{bf(ANA)}）",
      f"　{H[ANA]['why']['sc12']}／脚質 {H[ANA]['style']}",
      "　良馬場では勝ちきれていませんが、道悪では崩れていません。",
      "",
      "",
      "■ 買い方をレースごとに変えます",
      "",
      "これまでは毎回ワイドの流しで固定していました。それをやめます。",
      "",
      "過去496レースの確定払戻を使って、レースの型ごとにどの買い方が効くかを数えました。",
      "型はレース前に分かる情報だけで判定します。オッズの並び、指数1位の人気、頭数などです。",
      "",
      f"本日の型は「{AM['pattern']['name']}」。{AM['pattern']['desc']}。",
      "",
      "採用するのは、期間を前半と後半に分けて両方とも100%を超えた買い方だけにしています。",
      "片方だけ良い数字は偶然とみなします。",
      "",
      f"本日選んだのは「{AM['structure']}」です。",
      "先週まで使っていたワイドの流しは、この型では回収87%で下位でした。",
      "",
      "",
      "■ 買い目",
      "",
      f"合計{AM['budget']:,}円・{len(PTS)}点"]
N += [f"{p_['t']} {'-'.join(f'{c(x)}{NAME[x]}' for x in p_['combo'])}　{p_['amt']:,}円"
      f"（推定約{p_['est']}倍・的中なら約{int(p_['amt'] * p_['est'] / 100) * 100:,}円）"
      for p_ in sorted(PTS, key=lambda x: -x["amt"])]
N += ["",
      "推定配当が安い買い目ほど厚く、高い買い目ほど薄く置いています。",
      "どれが当たっても戻る額が揃うようにするためです。",
      f"推定配当の逆数を全部足すと{AM['over']}。1.0を超えると当たっても投資額に届かない点が",
      "混ざるので、そこに収めました。",
      "",
      f"1点以上当たる確率は{AM['hit'] * 100:.0f}%です。",
      "",
      "",
      "■ 正直に書いておくこと",
      "",
      "本日の型は過去496レースのうち36レースしかサンプルがありません。",
      "この型での買い方は、まだ実証できたとは言えない段階です。",
      "",
      f"また{c(M['◎'])}以外に、単勝1番人気の馬がいます。",
      "この馬は道悪の出走が1度もなく、稍重で走ったことがありません。",
      "本線の相手には入れていますが、軸からは外しました。",
      "",
      "",
      "■ まとめ",
      "",
      f"・本命は{c(HON)}{NAME[HON]}。各サイトの評価が最も集まった馬です",
      "・本日は稍重。道悪実績で指数を補正しました",
      f"・買い方は型に合わせて{AM['structure']}を選びました",
      "",
      "結果はレース後に、回収額まで含めてそのまま出します。",
      "",
      "#競馬 #競馬予想 #スプリンターズS #AI予想 #G1"]
box(doc, "note本文", N)

out = ROOT / "20260927" / "20260927_スプリンターズS最終予想_SNS投稿案.docx"
doc.save(out)
print("saved:", out)
print(f"型={AM['pattern']['id']} {AM['pattern']['name']} / 買い方={AM['structure']} / "
      f"◎={HON}{NAME[HON]} 🔥={ANA}{NAME[ANA]} / {AM['budget']:,}円 {len(PTS)}点 Σ={AM['over']}")
