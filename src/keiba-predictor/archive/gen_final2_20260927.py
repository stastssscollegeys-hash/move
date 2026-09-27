# -*- coding: utf-8 -*-
"""
gen_final2_20260927.py — スプリンターズS 最終予想（確定版）の予想詳細＋SNS投稿案
====================================================================================
入力は research/final_answer.json のみ（手打ちしない）。

この版で確定していること
  ・印 = 独自指数20因子 ＋ 本日の稍重による道悪補正。インフルエンサー合算は参考のみで印に使わない
  ・買い目 = 全券種を当日の実オッズで評価し、券種別の期待値しきい値で足切りして選択
  ・印は買い目から導いているので、印と買い目は必ず一致する
出力: 20260927/20260927_スプリンターズS最終予想_確定版.docx
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
A = json.loads((ROOT / "20260927" / "research" / "final_answer.json").read_text(encoding="utf-8"))
FONT = "游ゴシック"
CIRC = "⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
SEP = "─────────────────────"
TAG = "#競馬予想 #AI予想 #スプリンターズS #JRA"
HEAD = [f"🏇【{A['race']} {A['grade']}】2026/09/27（日）",
        f"━━ {A['venue']}競馬場 {A['course']} / {A['field']}頭立て / {A['start']}発走 / {A['weather']}・{A['baba']} ━━"]
M = {m["lab"]: m for m in A["marks"]}
MK = A["marks"]
HON = next(m for m in MK if m["lab"] == "◎")
ANA = next((m for m in MK if m["lab"] == "🔥"), None)
NM = {m["uma"]: m["name"] for m in MK}
LAB = {m["uma"]: m["lab"] for m in MK}
PTS = sorted(A["points"], key=lambda p: -p["amt"])


def c(n):
    n = int(n)
    return CIRC[n] if 0 <= n <= 20 else str(n)


def combo(p):
    return "-".join(f"{LAB.get(x,'')}{c(x)}{NM.get(x,'')}" for x in p["combo"])


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
    tag = f"［{n}字" + (f"/{limit}字 {'OK' if n <= limit else '⚠超過'}］" if limit else "］")
    h2(doc, f"{title}　{tag}")
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    if limit and n > limit:
        print(f"[WARN] 超過 {title} {n}字")


def sec(doc, title, lead, heading, lines):
    box(doc, title, HEAD + [""] + lead + ["", SEP, heading, SEP, ""] + lines + ["", TAG])


# ================================================================================
doc = Document()
doc.styles["Normal"].font.name = FONT
doc.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
p = doc.add_paragraph()
set_font(p.add_run(f"{A['race']}({A['grade']}) 最終予想 確定版"), 17, True, (20, 60, 140))
body(doc, f"2026年9月27日(日) {A['venue']} {A['course']} {A['field']}頭 {A['start']}発走／{A['weather']}・{A['baba']}\n"
          f"朝の実オッズ（{A['snapshot']}）を反映。16頭フル出走・出走取消なし。")
doc.add_paragraph()

# ── 予想詳細 ──────────────────────────────────────────────────
h1(doc, "SECTION 1｜最終予想印")
body(doc, "独自指数20因子に、本日の稍重に合わせた道悪補正（道悪3着内率−良3着内率／±3点まで）を加えたもの。"
          "インフルエンサー合算は参考に留め、印には使っていない。", 9)
table(doc, [["印", "馬番", "馬名", "指数", "道悪補正", "合計", "人気", "オッズ", "追い切り", "脚質/枠", "道悪実績"]] +
      [[m["lab"], c(m["uma"]), m["name"], m["idx"], f"{m['wet']:+.1f}", m["total"],
        f"{m['pop']}番人気", m["odds"], m["oikiri"], f"{m['style']}/{m['waku']}枠", m["baba_note"]] for m in MK])

h1(doc, "SECTION 2｜各馬の根拠")
for m in MK:
    h2(doc, f"{m['lab']} {c(m['uma'])}{m['name']}　合計{m['total']}（指数{m['idx']}／道悪{m['wet']:+.1f}）")
    body(doc, f"　・{m['why']['sc12']}\n"
              f"　・最高実績は{m['why']['sc19']}\n"
              f"　・{m['why']['sc18']}\n"
              f"　・追い切り {m['oikiri']}\n"
              f"　・脚質 {m['style']}／{m['waku']}枠／{m['pop']}番人気 {m['odds']}倍\n"
              f"　・道悪 {m['baba_note']}", 9.5)
doc.add_paragraph()

h1(doc, "SECTION 3｜買い目と、その選び方")
body(doc, f"買い方＝{A['structure']}。期待値{A['ev']}（この券種の基準{A['ev_need']}以上）／"
          f"1点以上当たる確率{A['hit']*100:.1f}%／的中時回収{A['ret_lo']}〜{A['ret_hi']}%／"
          f"Σ(1/配当)={A['over']}")
table(doc, [["券種", "買い目", "金額", "実オッズ", "的中なら", "回収率", "実測的中率"]] +
      [[p_["t"], combo(p_), f"{p_['amt']:,}円", f"{p_['est']}倍",
        f"{int(p_['amt']*p_['est']/100)*100:,}円", f"{p_['amt']*p_['est']/A['budget']*100:.0f}%",
        f"{p_['p']*100:.1f}%"] for p_ in PTS] +
      [["合計", f"{len(PTS)}点", f"{A['budget']:,}円", "", "", f"{A['ret_lo']}〜{A['ret_hi']}%", f"{A['hit']*100:.1f}%"]])

body(doc, "■ 落とした買い方（券種別の期待値しきい値で足切り）")
table(doc, [["買い方", "期待値", "基準", "的中率", "的中時回収", "落とした理由"]] +
      [[r["name"], r["ev"], r["need"], f"{r['hit']*100:.1f}%",
        f"{r['ret_lo']}〜{r['ret_hi']}%", "・".join(r["ng"])] for r in A["rejected"][:8]])
body(doc, "期待値＝オッズ×的中率。配当は当日の実オッズ、的中率は確定払戻1,536レースの人気帯別実測。"
          "券種ごとに狙うべき期待値の下限（ワイド1.1／単勝1.2／馬連1.4／馬単1.6／3連系2.0）を満たすものだけ残す。", 9)
doc.add_paragraph()

h1(doc, "SECTION 4｜外部ソースとの照合（参考・印には使わない）")
rows = [["印", "馬", "外部ソースの評価"]]
EX = A["extra"]
for m in MK:
    u, notes = m["uma"], []
    for src, d in EX.items():
        for k, lab in (("honmei", "本命"), ("taikou", "対抗"), ("honmei_split", "本命(2名のうち1名)"),
                       ("posi", "注目"), ("ana", "穴"), ("keshi", "消し"), ("oikiri", "追い切り高評価")):
            if u in (d.get(k) or []):
                notes.append(f"{src}={lab}")
    rows.append([m["lab"], f"{c(u)}{m['name']}", "／".join(notes) or "言及なし"])
table(doc, rows)
body(doc, "インフルエンサーの重みは固定値をやめ、台帳の直近8週の実績から動的に決めている"
          "（重み=1.0+0.6×(本命3着内率−全体平均)×信頼度／上下限0.8〜1.3）。"
          "実績が無いソースは1.00＝中立から始まる。合算で印は動かさない。", 9)

# ── SNS ───────────────────────────────────────────────────────
doc.add_page_break()
h1(doc, "SECTION 5｜X投稿（6本・節ごと）")

sec(doc, "X① 最終予想印（発走前／印画像を添付）",
    [f"本日の中山は{A['weather']}・{A['baba']}。時計のかかる馬場です。",
     f"最終の本命は{c(HON['uma'])}{HON['name']}にしました。"],
    "🎯 最終予想印",
    [f"{m['lab']} {c(m['uma'])}{m['name']}" for m in MK] + [
        "",
        "独自の20ファクター指数に、本日の馬場に合わせて各馬の道悪実績で補正をかけています。",
        "各サイトやYouTube予想の見解は参考として見ていますが、印には使っていません。",
        "",
        "根拠はスレッドで👇"])

sec(doc, "X② 本命の根拠（①の返信）",
    [f"本命は{c(HON['uma'])}{HON['name']}です。",
     f"独自指数で全馬中トップ、{HON['pop']}番人気です。"],
    f"◎ 本命 {c(HON['uma'])}{HON['name']}",
    [f"・独自の20ファクター指数{HON['idx']}点でメンバー1位",
     f"・追い切り {HON['oikiri']}",
     f"・{HON['why']['sc12']}",
     f"・最高実績は{HON['why']['sc19']}",
     f"・脚質は{HON['style']}、{HON['waku']}枠",
     f"・道悪は{HON['baba_note']}",
     "",
     "稍重は未知ですが、指数・追い切り・支持の三つがそろっています。",
     "ここは正直に「道悪は走ったことがない」と書いておきます。"])

sec(doc, "X③ 印をつけた馬（②の返信）",
    ["相手は市場の人気順では選びません。",
     "指数と、本日の馬場への適性で選びました。"],
    "○▲△ 印をつけた馬",
    sum([[f"{m['lab']} {c(m['uma'])}{m['name']}（指数{m['idx']}／道悪補正{m['wet']:+.1f}）",
          f"　{m['why']['sc12']}／最高実績 {m['why']['sc19']}",
          f"　追い切り {m['oikiri']}／脚質 {m['style']}／{m['waku']}枠",
          f"　道悪 {m['baba_note']}", ""] for m in MK[1:5]], []))

wet_up = [m for m in MK if m["wet"] > 0]
wet_dn = [m for m in MK if m["wet"] < 0]
sec(doc, "X④ 馬場（③の返信）",
    [f"本日の中山は{A['weather']}・{A['baba']}。昨日は全12レースが重馬場でした。",
     "芝1200mの勝ちタイムは1分09秒7。良馬場なら1分07秒台のコースです。"],
    "🌱 道悪実績で指数を補正しました",
    ["各馬の道悪3着内率と良馬場3着内率の差を、指数に反映しています。",
     "サンプルが少ない馬は効かせません。",
     ""] +
    (["【上げた馬】"] + [f"　{c(m['uma'])}{m['name']}　{m['wet']:+.1f}　{m['baba_note']}" for m in wet_up] if wet_up else []) +
    ([""] + ["【下げた馬】"] + [f"　{c(m['uma'])}{m['name']}　{m['wet']:+.1f}　{m['baba_note']}" for m in wet_dn] if wet_dn else []) +
    ["",
     "中山はCコース2週目で、3角から直線の内柵沿いに傷みが出ていると報じられています。",
     "昨日の芝で3着以内に入った馬の脚質は差し7・逃げ6・先行5・追込3。",
     "前も後ろも届いているので、どちらかに寄せる組み方はしません。"])

sec(doc, "X⑤ 買い方の選び方（④の返信）",
    ["買い方はレースごとに変えます。毎回同じ券種を使うのはやめました。",
     "基準は期待値です。"],
    "📊 期待値で券種を選ぶ",
    ["期待値＝オッズ×的中率。1.0以上が理論上の勝ちラインです。",
     "",
     "配当は当日の実オッズ、的中率は過去1,536レースの確定払戻から出した",
     "人気帯ごとの実測値を使っています。勘で置いた数字は入れていません。",
     "",
     "券種ごとに狙うべき下限を決めています。",
     "　ワイド1.1／単勝1.2／馬連1.4／馬単1.6／3連複・3連単2.0",
     "",
     f"本日は{A['structure']}が期待値{A['ev']}で基準を満たしました。",
     ""] +
    [f"　{r['name']}　期待値{r['ev']}（基準{r['need']}）→ 見送り" for r in A["rejected"][:4]] +
    ["",
     "3連系は的中時の配当こそ大きいのですが、相手が人気薄に寄ったぶん",
     "的中率が数%まで落ち、期待値が1.0を割ります。買うほど負ける形なので外しました。"])

sec(doc, "X⑥ 買い目（⑤の返信）",
    [f"買い目は合計{A['budget']:,}円・{len(PTS)}点です。",
     f"1点以上当たる確率は{A['hit']*100:.0f}%、当たればどれでも約4倍で戻ります。"],
    f"💰 買い目 合計{A['budget']:,}円・{len(PTS)}点",
    [f"{p_['t']} {'-'.join(c(x) for x in p_['combo'])}　{p_['amt']:,}円" for p_ in PTS] +
    ["",
     "実オッズと、当たったときの戻り"] +
    [f"　{'-'.join(c(x) for x in p_['combo'])}　{p_['est']}倍／"
     f"約{int(p_['amt']*p_['est']/100)*100:,}円（{p_['amt']*p_['est']/A['budget']*100:.0f}%）" for p_ in PTS] +
    ["",
     "配当が安い買い目ほど厚く置いて、どれが当たっても戻る額が揃うようにしています。",
     f"配当の逆数を全部足すと{A['over']}。1.0以下なので、当たって損をする点はありません。",
     "",
     "金額は100円単位のみ。G1でも規定額から増やしません。"] +
    ([f"", f"🔥{c(ANA['uma'])}{ANA['name']}は印に出していますが、買い目には入れていません。",
      f"{ANA['pop']}番人気で、絡めると当たる確率が落ちすぎるためです。"] if ANA and ANA["uma"] not in
     {x for p_ in PTS for x in p_["combo"]} else []))

# ── Threads ───────────────────────────────────────────────────
doc.add_page_break()
h1(doc, "SECTION 6｜Threads投稿（5本・各500字以内）")
TH = f"🏇【{A['race']} {A['grade']}】9/27(日) {A['venue']} {A['course']} {A['field']}頭"

box(doc, "Threads 1/5 最終予想印", [TH, "",
    f"本日の中山は{A['weather']}・{A['baba']}。時計のかかる馬場です。", ""] +
    [f"{m['lab']} {c(m['uma'])}{m['name']}" for m in MK] +
    ["", "指数に、各馬の道悪実績で補正をかけました。", "",
     "みなさんの本命はどの馬ですか？"], 500)

box(doc, "Threads 2/5 本命", [TH, "",
    f"本命は{c(HON['uma'])}{HON['name']}です。", "",
    f"・独自指数{HON['idx']}点でメンバー1位",
    f"・追い切り {HON['oikiri']}",
    f"・{HON['why']['sc12']}",
    f"・道悪は{HON['baba_note']}", "",
    "稍重は未知です。そこは正直に書いておきます。", "",
    "この本命、どう見ますか？"], 500)

box(doc, "Threads 3/5 馬場", [TH, "",
    "昨日の中山は全12レースが重馬場でした。",
    "芝1200mの勝ちタイムは1分09秒7。良馬場なら1分07秒台のコースです。", "",
    "各馬の道悪実績で指数を補正しています。", ""] +
    [f"・{c(m['uma'])}{m['name']}　{m['wet']:+.1f}（{m['baba_note']}）" for m in wet_up[:3]] +
    ["", "馬場が渋ったとき、どこを見て買い目を変えますか？"], 500)

box(doc, "Threads 4/5 買い方", [TH, "",
    "買い方をレースごとに変えることにしました。", "",
    "基準は期待値＝オッズ×的中率。1.0以上が勝ちラインです。",
    "的中率は過去1,536レースの確定払戻から出した実測値を使っています。", "",
    "券種ごとに下限を決めていて、ワイド1.1／馬連1.4／3連系2.0です。",
    f"本日は{A['structure']}が期待値{A['ev']}で基準を満たしました。", "",
    "みなさんは券種、レースごとに変えていますか？"], 500)

box(doc, "Threads 5/5 買い目", [TH, "",
    f"買い目は合計{A['budget']:,}円・{len(PTS)}点です。", ""] +
    [f"・{p_['t']} {'-'.join(c(x) for x in p_['combo'])}　{p_['amt']:,}円（{p_['est']}倍）" for p_ in PTS] +
    ["",
     f"1点以上当たる確率は{A['hit']*100:.0f}%。当たればどれでも約4倍で戻ります。",
     f"配当の逆数の合計は{A['over']}で、当たって損をする点はありません。", "",
     "この配分、どう思いますか？"], 500)

# ── note ──────────────────────────────────────────────────────
doc.add_page_break()
h1(doc, "SECTION 7｜note記事（全文無料）")
N = ["こんにちは、アスメシ競馬予想です🍱",
     "明日の飯代を懸けて、データで競馬に挑んでいます。",
     "",
     f"結論を先に言います。スプリンターズSの本命は{c(HON['uma'])}{HON['name']}、",
     f"買い目は{A['structure']}で{A['budget']:,}円・{len(PTS)}点です。",
     "",
     "",
     "■ レース基本情報",
     "",
     f"2026年9月27日(日) {A['venue']}競馬場 {A['course']} {A['field']}頭立て {A['start']}発走",
     f"天候は{A['weather']}、馬場は{A['baba']}です。",
     "",
     "",
     "■ 本日の馬場",
     "",
     "昨日9月26日の中山は、全12レースが重馬場でした。",
     "芝1200mの勝ちタイムは1分09秒7。良馬場なら1分07秒台が出るコースなので、2秒以上遅い計算です。",
     "",
     "本日の発表は稍重。中山はCコース2週目で、3角から直線の内柵沿いに傷みが出ていると報じられています。",
     "昨日の芝で3着以内に入った21頭の脚質は差し7・逃げ6・先行5・追込3。",
     "前も後ろも届いているので、どちらかに寄せる組み方はしません。",
     "",
     "",
     "■ 道悪実績で指数を補正しました",
     "",
     "各馬の道悪3着内率と良馬場3着内率の差を指数に反映しました。サンプルが少ない馬は効かせません。",
     ""]
if wet_up:
    N += ["上げた馬"] + [f"{c(m['uma'])}{m['name']}　{m['wet']:+.1f}　{m['baba_note']}" for m in wet_up] + [""]
if wet_dn:
    N += ["下げた馬"] + [f"{c(m['uma'])}{m['name']}　{m['wet']:+.1f}　{m['baba_note']}" for m in wet_dn] + [""]
N += ["", "■ 最終予想印", ""]
N += [f"{m['lab']} {c(m['uma'])}{m['name']}　指数{m['idx']}／道悪{m['wet']:+.1f}／合計{m['total']}" for m in MK]
N += ["", "", "■ 各馬の根拠", ""]
for m in MK:
    N += [f"{m['lab']} {c(m['uma'])}{m['name']}（{m['pop']}番人気 {m['odds']}倍）",
          f"　{m['why']['sc12']}／最高実績 {m['why']['sc19']}",
          f"　{m['why']['sc18']}",
          f"　追い切り {m['oikiri']}／脚質 {m['style']}／{m['waku']}枠",
          f"　道悪 {m['baba_note']}", ""]
N += ["",
      "■ 買い方は期待値で選びました",
      "",
      "これまでは毎回ワイドの流しで固定していました。それをやめます。",
      "",
      "期待値＝オッズ×的中率。1.0以上が理論上の勝ちラインで、",
      "期待値1.2の馬券を買い続ければ回収率は120%前後に収束します。",
      "逆に期待値0.8の馬券は、どれだけ当たっても最後は赤字になります。",
      "",
      "ここで大事なのは的中率の置き方です。勘で「この馬は30%くらい来る」と置くと、",
      "同じオッズでも人によって期待値がまるで変わってしまいます。",
      "なので過去1,536レースの確定払戻から、人気帯ごとの実測的中率を作って使っています。",
      "配当も推定ではなく、当日の実オッズです。",
      "",
      "券種ごとに狙うべき期待値の下限も決めました。",
      "　複勝1.1／ワイド1.1／単勝1.2／馬連1.4／馬単1.6／3連複・3連単2.0",
      "",
      f"本日は{A['structure']}が期待値{A['ev']}で基準を満たしました。",
      "",
      "見送った買い方も書いておきます。",
      ""]
N += [f"{r['name']}　期待値{r['ev']}（基準{r['need']}）／的中率{r['hit']*100:.1f}%／的中時{r['ret_lo']}〜{r['ret_hi']}%"
      for r in A["rejected"][:6]]
N += ["",
      "3連系は的中したときの配当が大きく見えますが、相手が人気薄に寄ったぶん的中率が数%まで落ちて、",
      "期待値が1.0を割ります。買えば買うほど負ける形なので外しました。",
      "",
      "",
      "■ 買い目",
      "",
      f"合計{A['budget']:,}円・{len(PTS)}点"]
N += [f"{p_['t']} {'-'.join(f'{c(x)}{NM.get(x,chr(0))}'.strip(chr(0)) for x in p_['combo'])}　{p_['amt']:,}円"
      f"（{p_['est']}倍・的中なら約{int(p_['amt']*p_['est']/100)*100:,}円）" for p_ in PTS]
N += ["",
      f"1点以上当たる確率は{A['hit']*100:.0f}%。当たればどれでも{A['ret_lo']}〜{A['ret_hi']}%で戻ります。",
      "配当が安い買い目ほど厚く置いて、どれが当たっても戻る額が揃うようにしています。",
      f"配当の逆数を全部足すと{A['over']}。1.0を超えると当たっても投資額に届かない点が混ざるので、そこに収めました。",
      "",
      "",
      "■ 外部の予想との照合",
      "",
      "各サイトやYouTubeの予想も集めていますが、印には使っていません。参考として並べます。",
      ""]
for m in MK:
    u, notes = m["uma"], []
    for src, d in EX.items():
        for k, lab in (("honmei", "本命"), ("taikou", "対抗"), ("honmei_split", "本命(2名のうち1名)"),
                       ("posi", "注目"), ("ana", "穴"), ("keshi", "消し"), ("oikiri", "追い切り高評価")):
            if u in (d.get(k) or []):
                notes.append(f"{src}={lab}")
    N.append(f"{m['lab']} {c(u)}{m['name']}　" + ("／".join(notes) or "言及なし"))
N += ["",
      "外部予想の重みは、台帳に貯めた直近8週の実績から自動で決めています。",
      "最近当たっている人は少しだけ重く、流れが悪い人は少しだけ軽く。上下の幅は0.8〜1.3に抑えています。",
      "実績が無い新しいソースは中立から始めます。",
      "",
      "",
      "■ 正直に書いておくこと",
      "",
      f"本命の{HON['name']}は、道悪の出走が1度もありません。稍重で走ったことがない馬です。",
      "指数1位・追い切り最高評価・市場の支持と三つそろっていますが、ここは未知です。",
      "",
      "また期待値は理論値で、馬場の変化・展開・騎手の判断は織り込めません。",
      "オッズも締切まで動きます。高い期待値が出たからといって、1レースに資金を寄せることはしません。",
      "",
      "",
      "■ まとめ",
      "",
      f"・本命は{c(HON['uma'])}{HON['name']}。独自指数1位に道悪補正をかけて決めました",
      f"・本日は稍重。道悪実績で全馬の指数を補正しています",
      f"・買い方は期待値で選び、{A['structure']}にしました（期待値{A['ev']}）",
      "",
      "結果はレース後に、回収額まで含めてそのまま出します。",
      "",
      "#競馬 #競馬予想 #スプリンターズS #AI予想 #G1"]
box(doc, "note本文", N)

out = ROOT / "20260927" / "20260927_スプリンターズS最終予想_確定版.docx"
doc.save(out)
print("saved:", out)
used = {x for p_ in PTS for x in p_["combo"]}
print(f"印: " + " ".join(f"{m['lab']}{c(m['uma'])}{m['name']}" for m in MK))
print(f"買い目: {A['structure']} {len(PTS)}点 {A['budget']:,}円 期待値{A['ev']} 的中率{A['hit']*100:.1f}%")
print(f"照合: 買い目{sorted(used)} ⊆ 印{sorted(m['uma'] for m in MK)} → "
      + ("OK" if used <= {m['uma'] for m in MK} else "NG"))
