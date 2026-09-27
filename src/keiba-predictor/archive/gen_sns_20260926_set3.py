# -*- coding: utf-8 -*-
"""
gen_sns_20260926_set3.py — SNS投稿案3本立て（2026-09-26作成）
==============================================================
  ① 本日9/26の結果報告
  ② 明日9/27 スプリンターズS 前日予想
  ③ 明日9/27 平場の注目レース（自信度7以上）

構成ルール（2026-09-25の調査で確定）:
  X投稿は冒頭140字/空行込み8行以内で「さらに表示」に折りたたまれる。
  → 冒頭ブロックだけで言いたいことが完結し、その先に詳細・根拠・データを置く。
  印の直後に「（N番人気）」は書かない（人気は予想時・投稿時・閲覧時で変わるため）。

数字はすべて生成物・確定データから引く（手打ちしない）:
  daily_pdca/db/race_results.json   … 9/26の確定結果・馬場傾向
  daily_pdca/db/payouts.json        … 9/26の確定払戻
  20260926/research/score20_20260925.json, kaime_sprinters.json … スプリンターズS
  20260927/flat_20260927.json       … 日曜平場5レース
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
DB = ROOT / "daily_pdca" / "db"
FONT = "游ゴシック"
CIRC = "⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
SEP = "─────────────────────"


def c(n):
    n = int(n)
    return CIRC[n] if 0 <= n <= 20 else str(n)


# ── データ読み込み ───────────────────────────────────────────────
RES = [x for x in json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
       if x.get("date") == "20260926"]
SC = json.loads((ROOT / "20260926" / "research" / "score20_20260925.json").read_text(encoding="utf-8"))["スプリンターズS"]
K = json.loads((ROOT / "20260926" / "research" / "kaime_sprinters.json").read_text(encoding="utf-8"))
FLAT = json.loads((ROOT / "20260927" / "flat_20260927.json").read_text(encoding="utf-8"))

NAME = {int(k): v for k, v in K["name"].items()}
H = {h["uma"]: h for h in SC["horses"]}
RANK = {h["uma"]: i + 1 for i, h in enumerate(SC["horses"])}
D = K["design"]
HON, AITE, BETS, BUDGET, OVER = D["hon"], D["aite"], D["bets"], D["budget"], D["over"]
TOP_POP = sorted({int(a): b for a, b in K["odds"].items()}, key=lambda u: float(K["odds"][str(u)]))
FAV = TOP_POP[0]
ANA = max([h["uma"] for h in SC["horses"][:4] if h["uma"] not in {HON, *AITE}],
          key=lambda u: K["pop"][str(u)])
PROMOTE = [h["uma"] for h in SC["horses"] if h.get("oikiri_promote")]

# ── 9/26 の確定結果から集計 ─────────────────────────────────────
SIRIUS = {int(float(r["馬番"])): r for r in RES if r["競馬場"] == "阪神" and int(r["R"]) == 11}
S_ORDER = sorted(SIRIUS.values(), key=lambda r: r.get("着順int") or 99)
S_MARK = {6: "◎", 13: "○", 15: "▲", 10: "△", 9: "△"}
S_RANK = {h["uma"]: i + 1 for i, h in enumerate(
    json.loads((ROOT / "20260926" / "research" / "score20_20260925.json").read_text(encoding="utf-8"))["シリウスS"]["horses"])}


def bias(venue):
    rows = [x for x in RES if x["競馬場"] == venue]
    t3 = [x for x in rows if (x.get("着順int") or 99) <= 3]
    st = collections.Counter(x.get("脚質") for x in t3 if x.get("脚質"))
    n = sum(st.values())
    wins = sorted(int(float(x.get("人気") or 99)) for x in rows if (x.get("着順int") or 99) == 1)
    surf = {}
    for s in ("芝", "ダ"):
        sub = [x for x in t3 if str(x.get("距離", "")).startswith(s)]
        surf[s] = collections.Counter(x.get("脚質") for x in sub if x.get("脚質"))
    return dict(n=n, style=st, wins=wins, surf=surf,
                line=" ".join(f"{k}{v / n * 100:.0f}%" for k, v in st.most_common()))


B_NAKAYAMA, B_HANSHIN = bias("中山"), bias("阪神")

# 公開した買い目の実績（review_weekend.py の出力と同じ数字）
PUB = [("シリウスS（阪神11R）", 8000, 0), ("中山6R", 5000, 0),
       ("中山7R", 12000, 9880), ("阪神12R", 5000, 0)]
PUB_INV = sum(x[1] for x in PUB)
PUB_RET = sum(x[2] for x in PUB)
FAV1 = sum(1 for x in RES if int(float(x.get("人気") or 99)) == 1 and (x.get("着順int") or 99) == 1)
FAV3 = sum(1 for x in RES if int(float(x.get("人気") or 99)) == 1 and (x.get("着順int") or 99) <= 3)
NRACE = len({(x["競馬場"], int(x["R"])) for x in RES})


# ── docx ヘルパー ───────────────────────────────────────────────
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


HEAD_EMOJI = [
    ("予想印", "🎯"), ("買い目", "💰"), ("本命", "◎"), ("印をつけた馬", "○▲△"),
    ("穴", "🔥"), ("外した", "❌"), ("過去", "📊"), ("データ", "📊"), ("成績", "📊"),
    ("展開", "🏟"), ("コース", "🏟"), ("馬場", "🌱"), ("材料", "🌱"), ("追い切り", "🐴"),
    ("結果", "📊"), ("答え合わせ", "🏇"), ("根拠", "◎"), ("買わない", "🚫"), ("注意", "⚠"),
]


MARKS_PREFIX = ("◎", "○", "▲", "△", "🔥", "❌", "🎯", "💰", "📊", "🏟", "🌱", "🐴", "🚫", "⚠")


def _emoji(t):
    if t.startswith(MARKS_PREFIX):     # 見出し自体が記号で始まるなら重ねない
        return ""
    for k, e in HEAD_EMOJI:
        if k in t:
            return e
    return "■"


def xpost(doc, title, head, rest, tags):
    """確立済みフォーマットで1投稿を組む。
    head = 2行ヘッダー＋空行＋リード文（＋本命）／rest の '■ 見出し' を区切り線で挟む形に直す。"""
    lines, i = list(head), 0
    while i < len(rest):
        ln = rest[i]
        if ln == SEP:                       # 旧形式の裸の区切り線は捨てる
            i += 1
            continue
        if ln.startswith("■ "):
            t = ln[2:]
            while lines and lines[-1] == "":
                lines.pop()
            lines += ["", SEP, (f"{_emoji(t)} {t}").strip(), SEP, ""]
            i += 1
            continue
        lines.append(ln)
        i += 1
    while lines and lines[-1] == "":
        lines.pop()
    lines += ["", tags]
    total = len("\n".join(lines))
    fold = len("\n".join(head))
    h2(doc, f"{title}　［{total}字／冒頭ブロック {fold}字］")
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    if total > 2000:
        print(f"[WARN] 2000字超 {title} {total}字")
    return total


def sec(doc, title, head2, lead, heading, lines, tags):
    """1投稿＝1節。head2=2行ヘッダー／lead=リード文／heading=節の見出し／lines=節の本文"""
    L = list(head2) + [""] + list(lead) + ["", SEP, heading, SEP, ""] + list(lines)
    while L and L[-1] == "":
        L.pop()
    L += ["", tags]
    n = len("\n".join(L))
    h2(doc, f"{title}　［{n}字］")
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(L):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    if n > 2000:
        print(f"[WARN] 2000字超 {title} {n}字")
    return n


def th(doc, title, lines):
    """Threads投稿。最後は問いかけで締める"""
    n = len("\n".join(lines))
    h2(doc, f"{title}　［{n}字］")
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    return n


def note(doc, title, lines):
    """note記事。マークダウン記号は使わない（見出しはnoteの見出し機能で設定する）"""
    n = len("\n".join(lines))
    h2(doc, f"{title}　［{n}字］")
    body(doc, "記号（#や**）は使わない。見出しはnoteの見出し機能で設定する。全文無料公開。", 9)
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    return n


HOOK = ["こんにちは、アスメシ競馬予想です🍱",
        "明日の飯代を懸けて、データで競馬に挑んでいます。"]


def newdoc(title, sub):
    doc = Document()
    doc.styles["Normal"].font.name = FONT
    doc.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    p = doc.add_paragraph(); set_font(p.add_run(title), 16, True, (20, 60, 140))
    body(doc, sub)
    body(doc, "※X投稿はこれまでと同じ構成（2行ヘッダー → リード文 → 区切り線で挟んだ見出し）。", 9)
    doc.add_paragraph()
    return doc


TAG1 = "#競馬 #競馬予想 #AI予想 #シリウスS"
TAG2 = "#競馬予想 #AI予想 #スプリンターズS #JRA"
TAG3 = "#競馬予想 #AI予想 #JRA #中山競馬場 #阪神競馬場"

# ================================================================================
# ① 本日9/26 の結果報告
# ================================================================================
doc = newdoc("9/26（土）結果報告 SNS投稿案",
             "中山・阪神 全24レース／公開した買い目の答え合わせと、明日へ持ち越す材料")

h1(doc, "SECTION 1｜確定した数字")
table(doc, [["レース", "投資", "払戻", "回収率"]] +
      [[n, f"{i:,}円", f"{r:,}円", f"{r / i * 100:.0f}%"] for n, i, r in PUB] +
      [["合計", f"{PUB_INV:,}円", f"{PUB_RET:,}円", f"{PUB_RET / PUB_INV * 100:.0f}%"]])
body(doc, f"市場の1番人気は 1着 {FAV1}/{NRACE}（{FAV1 / NRACE * 100:.0f}%）／3着内 {FAV3}/{NRACE}"
          f"（{FAV3 / NRACE * 100:.0f}%）。")
doc.add_paragraph()

h1(doc, "SECTION 2｜X投稿")

HEAD_R = ["🏇【結果報告】2026/09/26（土）", "━━ 中山・阪神 全24レース ━━"]

sec(doc, "X① 結果まとめ（レース後すぐ／画像＝印と着順）", HEAD_R, [
    f"公開した買い目は{PUB_INV:,}円 → {PUB_RET:,}円、回収率{PUB_RET / PUB_INV * 100:.0f}%でした。",
    "4レース中1レース的中。負けた日も同じ形で出します。",
], "📊 レースごとの結果",
    [f"{n}　{i:,}円 → {r:,}円（{r / i * 100:.0f}%）" for n, i, r in PUB] + [
    "",
    f"合計 {PUB_INV:,}円 → {PUB_RET:,}円（{PUB_RET / PUB_INV * 100:.0f}%）",
    "",
    f"市場の1番人気は 1着{FAV1}/{NRACE}・3着内{FAV3}/{NRACE}でした。",
    "",
    "詳しい中身はスレッドで👇",
], TAG1)

sec(doc, "X② シリウスS 答え合わせ（①の返信）", HEAD_R, [
    "重賞のシリウスSは、本命が5着で全滅でした。",
    "出していた印がどうなったかを全部出します。",
], "🏇 シリウスS 答え合わせ", [
    f"1着 {c(S_ORDER[0]['馬番'])}{S_ORDER[0]['馬名']}",
    f"2着 {c(S_ORDER[1]['馬番'])}{S_ORDER[1]['馬名']}",
    f"3着 {c(S_ORDER[2]['馬番'])}{S_ORDER[2]['馬名']}",
    "",
] + [f"{S_MARK[u]} {c(u)}{SIRIUS[u]['馬名']} → {SIRIUS[u]['着順int']}着" for u in (6, 13, 15, 10, 9)] + [
    "",
    f"1〜3着の独自指数の順位は {S_RANK[int(float(S_ORDER[0]['馬番']))]}位・"
    f"{S_RANK[int(float(S_ORDER[1]['馬番']))]}位・{S_RANK[int(float(S_ORDER[2]['馬番']))]}位。",
    "指数の上位からは来ていましたが、本命に置いた1位が5着でした。",
    "4点すべて本命からの流しだったので、相手が2着に来ても取れていません。",
], TAG1)

sec(doc, "X③ 当たったレースと反省（②の返信）", HEAD_R, [
    "当たったレースもありました。ただし回収は82%です。",
    "当たっても元が取れない形になっていました。",
], "🔍 反省", [
    "中山7R は本命が1着、△が3着でワイド的中。",
    "それでも回収は82%でした。",
    "",
    "厚く置いた本命-対抗が外れ、薄く置いた側が当たったためです。",
    "推定配当が安い組み合わせを本線に置くと、当たっても届きません。",
    "",
    "明日からは、安すぎる組み合わせを本線に置かないようにします。",
], TAG1)

sec(doc, "X④ 明日へ持ち越す材料（③の返信）", HEAD_R, [
    "明日も同じ2場です。今日の馬場をそのまま持ち越します。",
    "3着以内に入った馬の脚質を並べます。",
], "🌱 今日の馬場", [
    f"中山（3着以内{B_NAKAYAMA['n']}頭）　{B_NAKAYAMA['line']}",
    "　芝だけだと " + "・".join(f"{k}{v}頭" for k, v in B_NAKAYAMA['surf']['芝'].most_common()),
    "",
    f"阪神（3着以内{B_HANSHIN['n']}頭）　{B_HANSHIN['line']}",
    "　芝だけだと " + "・".join(f"{k}{v}頭" for k, v in B_HANSHIN['surf']['芝'].most_common()),
    "",
    "中山の芝は特定の脚質に偏っていません。前も後ろも届いています。",
    "阪神の芝は追い込みが最多でした。",
    "",
    "勝ち馬の人気",
    "中山　" + "・".join(f"{p}番人気" for p in B_NAKAYAMA["wins"]),
    "阪神　" + "・".join(f"{p}番人気" for p in B_HANSHIN["wins"]),
    "",
    "明日はスプリンターズS。予想は今夜出します。",
], TAG1)

h1(doc, "SECTION 3｜Threads投稿（4本）")
body(doc, "Threadsは会話の往復が伸びる媒体なので、最後を問いかけで締める。", 9)

th(doc, "Threads 1/4 結果まとめ", [
    "🏇【結果報告】9/26(土) 中山・阪神 全24レース",
    "",
    f"公開した買い目は{PUB_INV:,}円 → {PUB_RET:,}円。回収率{PUB_RET / PUB_INV * 100:.0f}%でした。",
    "4レース中1レース的中です。",
    "",
] + [f"・{n}　{i:,}円 → {r:,}円" for n, i, r in PUB] + [
    "",
    "負けた日も同じ形で出します。",
    "",
    "みなさんの土曜はどうでしたか？",
])

th(doc, "Threads 2/4 シリウスS", [
    "重賞のシリウスS、本命が5着で全滅でした。",
    "",
    f"1着 {c(S_ORDER[0]['馬番'])}{S_ORDER[0]['馬名']}",
    f"2着 {c(S_ORDER[1]['馬番'])}{S_ORDER[1]['馬名']}",
    f"3着 {c(S_ORDER[2]['馬番'])}{S_ORDER[2]['馬名']}",
    "",
    "1〜3着の独自指数の順位は3位・6位・5位。",
    "指数の上位からは来ていたのに、本命に置いた1位が5着でした。",
    "",
    "4点すべて本命からの流しだったので、相手が2着に来ても取れていません。",
    "",
    "軸が飛んだとき、みなさんはどうしていますか？",
])

th(doc, "Threads 3/4 当たったのに82%", [
    "当たったレースもありました。中山7Rです。",
    "本命が1着、△が3着でワイド的中。",
    "",
    "それでも回収は82%でした。",
    "厚く置いた本命-対抗が外れて、薄く置いた側が当たったからです。",
    "",
    "推定配当が安い組み合わせを本線にすると、当たっても元が取れません。",
    "明日からはそこを直します。",
    "",
    "この「当たったのに減る」やつ、経験ありませんか？",
])

th(doc, "Threads 4/4 明日への材料", [
    "明日も中山と阪神です。今日の馬場を持ち越します。",
    "",
    f"中山 3着以内{B_NAKAYAMA['n']}頭　{B_NAKAYAMA['line']}",
    f"阪神 3着以内{B_HANSHIN['n']}頭　{B_HANSHIN['line']}",
    "",
    "中山の芝は前も後ろも届いていて、脚質の偏りがありません。",
    "阪神の芝は追い込みが最多でした。",
    "",
    "明日はスプリンターズS。予想は今夜出します。",
    "",
    "明日の本命、もう決まっていますか？",
])
doc.add_paragraph()

h1(doc, "SECTION 4｜note記事（全文無料）")
note(doc, "note本文", HOOK + [
    "",
    "結論から言います。9月26日(土)に公開した買い目は、"
    f"{PUB_INV:,}円が{PUB_RET:,}円になりました。回収率{PUB_RET / PUB_INV * 100:.0f}%です。",
    "",
    "",
    "■ 今日の結果",
    "",
] + [f"{n}　{i:,}円 → {r:,}円（{r / i * 100:.0f}%）" for n, i, r in PUB] + [
    "",
    f"合計 {PUB_INV:,}円 → {PUB_RET:,}円（{PUB_RET / PUB_INV * 100:.0f}%）",
    "",
    f"参考までに、市場の1番人気は1着{FAV1}/{NRACE}、3着内{FAV3}/{NRACE}でした。",
    "",
    "",
    "■ シリウスS(G3)の答え合わせ",
    "",
    f"1着 {c(S_ORDER[0]['馬番'])}{S_ORDER[0]['馬名']}",
    f"2着 {c(S_ORDER[1]['馬番'])}{S_ORDER[1]['馬名']}",
    f"3着 {c(S_ORDER[2]['馬番'])}{S_ORDER[2]['馬名']}",
    "",
    "出していた印がどうなったかも全部書きます。",
    "",
] + [f"{S_MARK[u]} {c(u)}{SIRIUS[u]['馬名']} → {SIRIUS[u]['着順int']}着" for u in (6, 13, 15, 10, 9)] + [
    "",
    "1〜3着の独自指数の順位は3位・6位・5位でした。",
    "指数の上位からは来ています。ただ、本命に置いた指数1位が5着でした。",
    "買い目の4点はすべて本命からの流しだったので、相手が2着に来ても取れていません。",
    "",
    "",
    "■ 当たったレースの話",
    "",
    "中山7Rは本命が1着、△が3着でワイドが当たりました。",
    "それでも回収は82%です。当たったのに元が取れていません。",
    "",
    "理由ははっきりしています。厚く置いた本命-対抗が外れて、",
    "薄く置いた側が当たったからです。",
    "推定配当が安い組み合わせを本線にすると、こうなります。",
    "",
    "明日からは、推定4.0倍を切る組み合わせを本線に置かないようにします。",
    "",
    "",
    "■ 明日へ持ち越す材料",
    "",
    "明日も中山と阪神です。今日の馬場をそのまま持ち越します。",
    "",
    f"中山（3着以内{B_NAKAYAMA['n']}頭）　{B_NAKAYAMA['line']}",
    "　芝だけだと " + "・".join(f"{k}{v}頭" for k, v in B_NAKAYAMA['surf']['芝'].most_common()),
    "",
    f"阪神（3着以内{B_HANSHIN['n']}頭）　{B_HANSHIN['line']}",
    "　芝だけだと " + "・".join(f"{k}{v}頭" for k, v in B_HANSHIN['surf']['芝'].most_common()),
    "",
    "中山の芝は特定の脚質に偏っていません。前も後ろも届いています。",
    "阪神の芝は追い込みが最多でした。",
    "",
    "勝ち馬の人気も並べておきます。",
    "中山　" + "・".join(f"{p}番人気" for p in B_NAKAYAMA["wins"]),
    "阪神　" + "・".join(f"{p}番人気" for p in B_HANSHIN["wins"]),
    "",
    "",
    "■ まとめ",
    "",
    f"・公開した買い目は{PUB_INV:,}円 → {PUB_RET:,}円（{PUB_RET / PUB_INV * 100:.0f}%）",
    "・シリウスSは本命が5着。4点とも本命絡みだったので0円でした",
    "・当たった中山7Rも回収82%。安い組み合わせを厚く持ったのが原因です",
    "",
    "明日はスプリンターズS。予想は今夜出します。",
    "",
    "#競馬 #競馬予想 #シリウスS #AI予想",
])
doc.add_paragraph()

try:
    doc.save(ROOT / "20260926" / "20260926_結果報告_SNS投稿案.docx")
except PermissionError:
    print("[SKIP] 開いているため保存せず:", "20260926_結果報告_SNS投稿案.docx")
print("saved ①", ROOT / "20260926" / "20260926_結果報告_SNS投稿案.docx")

# ================================================================================
# ② 明日 スプリンターズS 前日予想
# ================================================================================
doc = newdoc("9/27（日）スプリンターズS(G1) 前日予想 SNS投稿案",
             "中山 芝1200m 16頭 15:40発走／秋G1連載『AI指数 vs 1番人気』第1戦")
HEAD_S = ["🏇【スプリンターズS G1】2026/09/27（日）",
          "━━ 中山競馬場 芝1200m（外回り） / 16頭立て / 15:40発走 ━━"]

V2 = json.loads((ROOT / "20260926" / "research" / "kaime_sprinters_v2.json").read_text(encoding="utf-8"))
PT = V2["points"]
WIDE = [p for p in PT if p["t"] == "ワイド"]
TAN = [p for p in PT if p["t"] == "単勝"]
ANA2 = TAN[0]["u"] if TAN else V2["marks"]["🔥"]
MK = [("◎", V2["marks"]["◎"]), ("○", V2["marks"]["○"]), ("▲", V2["marks"]["▲"])] + \
     [("△", u) for u in V2["marks"]["△"]]
DROP = V2["dropped_fav"]
BUD = V2["budget"]


def why(u):
    w = H[u]["why"]
    return [f"　指数{RANK[u]}位 {H[u]['final170']}点／追い切り {H[u]['oikiri']}",
            f"　脚質 {H[u]['style']}／{H[u]['waku']}枠",
            f"　{w['sc12']}／最高実績 {w['sc19']}"]


h1(doc, "SECTION 1｜最終予想印と買い目")
table(doc, [["印", "馬番", "馬名", "指数順位", "指数", "追い切り(2サイト)", "脚質", "枠"]] +
      [[lab, c(u), NAME[u], f"{RANK[u]}位", H[u]["final170"], H[u]["oikiri"], H[u]["style"], f"{H[u]['waku']}枠"]
       for lab, u in MK + [("🔥", ANA2)]])
table(doc, [["券種", "買い目", "金額", "推定配当", "的中なら"]] +
      [[p["t"], f"{c(HON)}-{c(p['u'])} {NAME[p['u']]}" if p["t"] != "単勝" else f"{c(p['u'])} {NAME[p['u']]}",
        f"{p['amt']:,}円", f"約{p['est']}倍", f"約{int(p['amt'] * p['est'] / 100) * 100:,}円"] for p in PT] +
      [["合計", f"{len(PT)}点", f"{BUD:,}円", f"Σ(1/配当)={V2['over']}", ""]])
body(doc, f"1番人気の{c(DROP['uma'])}{DROP['name']}は買い目から外した（指数{DROP['rank']}位／"
          f"◎とのワイドは推定{DROP['est']}倍で、推定4.0倍未満を本線にしないという自ルールに反するため）。", 9)
doc.add_paragraph()

h1(doc, "SECTION 2｜X投稿")

LEAD_S = ["近3年の勝ち馬は8番人気・9番人気・11番人気。",
          "3年続けて上位人気が勝っていないレースです。"]

sec(doc, "X① 予想印一覧（今夜20-22時／印インフォグラフィックを添付）", HEAD_S,
    LEAD_S + [f"本命は{c(HON)}{NAME[HON]}にしました。"], "🎯 予想印",
    [f"{lab} {c(u)}{NAME[u]}" for lab, u in MK] + [
    f"🔥 {c(ANA2)}{NAME[ANA2]}",
    "",
    "本命は独自の20ファクター指数の1位。",
    "相手は人気上位から取りつつ、指数の上位も1頭入れています。",
    "1番人気は買い目から外しました。理由はスレッドで。",
    "",
    "根拠はスレッドで👇",
], TAG2)

sec(doc, "X② 本命の根拠（①の返信）", HEAD_S, [
    f"本命は{c(HON)}{NAME[HON]}です。",
    "独自指数で1位、追い切りも2サイトそろって最高評価でした。",
], f"◎ 本命 {c(HON)}{NAME[HON]}", [
    f"・独自の20ファクター指数{H[HON]['final170']}点でメンバー1位",
    f"・最終追い切りは「{H[HON]['oikiri']}」（2つの評価がそろって最高）",
    f"・{H[HON]['why']['sc12']}",
    f"・{H[HON]['why']['sc18']}",
    f"・最高実績は{H[HON]['why']['sc19']}",
    f"・脚質は{H[HON]['style']}、{H[HON]['waku']}枠",
    "",
    "このレースで3着以内に入った馬は先行が30.4%で最も多く、追い込みは12.3%。",
    "位置を取れる本命から入ります。",
], TAG2)

sec(doc, "X③ 印をつけた馬（②の返信）", HEAD_S, [
    "相手は単勝人気の上位から取ります。",
    "そこに独自指数の上位を1頭だけ足しました。",
], "○▲△ 印をつけた馬",
    sum([[f"{lab} {c(u)}{NAME[u]}（指数{RANK[u]}位 {H[u]['final170']}点）",
          f"　{H[u]['why']['sc12']}／最高実績 {H[u]['why']['sc19']}",
          f"　追い切り {H[u]['oikiri']}／脚質 {H[u]['style']}／{H[u]['waku']}枠", ""]
         for lab, u in MK[1:]], []) + [
    f"▲{c(V2['marks']['▲'])}{NAME[V2['marks']['▲']]}は相手の中で指数が最も上位です。",
    "人気の並びだけで相手を決めると、当たっても戻りが小さくなるため入れました。",
], TAG2)

sec(doc, "X④ 穴馬（③の返信）", HEAD_S, [
    f"穴は{c(ANA2)}{NAME[ANA2]}です。",
    "指数は上位なのに、単勝の支持は薄いままです。",
], f"🔥 穴 {c(ANA2)}{NAME[ANA2]}", [
    f"・独自指数{RANK[ANA2]}位 {H[ANA2]['final170']}点",
    f"・追い切り {H[ANA2]['oikiri']}",
    f"・{H[ANA2]['why']['sc12']}",
    f"・最高実績は{H[ANA2]['why']['sc19']}",
    f"・脚質は{H[ANA2]['style']}、{H[ANA2]['waku']}枠",
    "",
    "「指数の中位で支持が薄い」という形は、過去データで拾えていた数少ないパターンでした。",
    "当たる回数は少ないので、賭けるのは単勝1,000円だけにします。",
], TAG2)

sec(doc, "X⑤ 1番人気を買い目から外した理由（④の返信）", HEAD_S, [
    f"1番人気の{c(DROP['uma'])}{DROP['name']}は、印も買い目も付けていません。",
    "強いから買う、弱いから切る、という話ではありません。",
], "❌ 1番人気を外した理由", [
    f"{c(DROP['uma'])}{DROP['name']}",
    f"・独自指数は{DROP['rank']}位",
    f"・追い切り {DROP['oikiri']}（2サイトで評価が割れています）",
    f"・本命とのワイドは推定{DROP['est']}倍",
    "",
    "推定4.0倍を切る組み合わせを本線に置かない、というのを自分たちのルールにしています。",
    "当たっても投資額があまり増えないからです。",
    "",
    "今日のシリウスSも、当たったレースの回収が82%止まりでした。",
    "安すぎる組み合わせを厚く持ったことが原因です。",
    "同じことを繰り返さないために、ここは見送ります。",
], TAG2)

sec(doc, "X⑥ コースと展開（⑤の返信）", HEAD_S, [
    "中山の芝1200mは、下り坂で加速してゴール前に急坂が待つコースです。",
    "前が止まらない年と、坂で差し込まれる年がはっきり分かれます。",
], "🏟 コースと過去10回", [
    f"今回、はっきり逃げそうな馬は{SC['n_nige']}頭です。",
    "",
    "過去10回のデータ",
    "・3連単の中央値は106,170円。10万円超えが10回中5回",
    "・近3年の勝ち馬は8番人気・9番人気・11番人気",
    "・3着以内の脚質は先行30.4%が最多。追い込みは12.3%",
    "・枠は1枠40%・3枠30%が良く、6枠は5%・8枠は10%",
    "",
    "本日の中山の芝は、3着以内が " +
    "・".join(f"{k}{v}頭" for k, v in B_NAKAYAMA["surf"]["芝"].most_common()) + "。",
    "特定の脚質に偏っていません。前だけ・後ろだけに寄せる組み方はしません。",
], TAG2)

sec(doc, "X⑦ 買い目（⑥の返信）", HEAD_S, [
    f"買い目は合計{BUD:,}円・{len(PT)}点です。",
    "本命からのワイド流しに、穴馬の単勝を少しだけ足しました。",
], f"💰 買い目 合計{BUD:,}円・{len(PT)}点",
    [f"{p['t']} {c(HON)}-{c(p['u'])}　{p['amt']:,}円" if p["t"] != "単勝"
     else f"{p['t']} {c(p['u'])}　{p['amt']:,}円" for p in PT] + [
    "",
    "推定配当と、当たったときの戻り",
] + [f"　{c(p['u'])}{NAME[p['u']]}　推定 約{p['est']}倍／約{int(p['amt'] * p['est'] / 100) * 100:,}円"
     for p in PT] + [
    "",
    "推定配当が安い買い目ほど厚く、高い買い目ほど薄く置いています。",
    "どのワイドが当たっても戻る額が揃うようにするためです。",
    f"推定配当の逆数を全部足すと{V2['over']}。1.0以下に収めています。",
    "",
    "※前日オッズで組んでいます。明日の朝、実オッズと出走取消を見て組み直します。",
], TAG2)

sec(doc, "X⑧ 追い切り2サイトの答え合わせ（⑦の返信）", HEAD_S, [
    "追い切りの評価を、2つのサイトで見比べました。",
    f"両方そろって高評価だったのは{'と'.join(NAME[u] for u in PROMOTE)}の{len(PROMOTE)}頭だけです。",
], "🐴 追い切り 全16頭", [
    "評価はS・A・B・C・D・Eの6段階。Sが最高です。",
    "2サイトの点数を平均して指数に入れ、印を上げるのは両方がそろって",
    "高評価（SかA）を付けた馬だけに限っています。",
    "",
] + [f"{c(h['uma'])}{h['name']}　{h['oikiri']}" for h in SC["horses"]] + [
    "",
    "並び順は独自指数の順です。",
], TAG2)

h1(doc, "SECTION 3｜Threads投稿（6本）")
body(doc, "Threadsは会話の往復が伸びる媒体なので、最後を問いかけで締める。", 9)

TH_HEAD = "🏇【スプリンターズS G1】9/27(日) 中山 芝1200m 16頭"

th(doc, "Threads 1/6 予想印", [
    TH_HEAD,
    "",
    "近3年の勝ち馬は8番人気・9番人気・11番人気。",
    "3年続けて上位人気が勝っていないレースです。",
    "",
] + [f"{lab} {c(u)}{NAME[u]}" for lab, u in MK] + [
    f"🔥 {c(ANA2)}{NAME[ANA2]}",
    "",
    "本命は独自指数の1位。1番人気は買い目から外しました。",
    "",
    "みなさんの本命はどの馬ですか？",
])

th(doc, "Threads 2/6 本命", [
    TH_HEAD,
    "",
    f"本命は{c(HON)}{NAME[HON]}です。",
    "",
    f"・独自の20ファクター指数{H[HON]['final170']}点で1位",
    f"・追い切りは{H[HON]['oikiri']}。2つの評価サイトがそろって最高でした",
    f"・{H[HON]['why']['sc12']}",
    f"・最高実績は{H[HON]['why']['sc19']}",
    f"・脚質は{H[HON]['style']}",
    "",
    "このレースの3着以内は先行が30.4%で最多、追い込みは12.3%。",
    "位置を取れる馬から入ります。",
    "",
    "この本命、どう見ますか？",
])

th(doc, "Threads 3/6 1番人気を外した", [
    TH_HEAD,
    "",
    f"1番人気の{c(DROP['uma'])}{DROP['name']}は、印も買い目も付けていません。",
    "",
    f"・独自指数は{DROP['rank']}位",
    f"・追い切りは{DROP['oikiri']}で、2サイトの評価が割れています",
    f"・本命とのワイドは推定{DROP['est']}倍",
    "",
    "推定4.0倍を切る組み合わせを本線に置かない、というのを決めています。",
    "当たっても投資額があまり増えないからです。",
    "",
    "1番人気、みなさんなら買いますか？",
])

th(doc, "Threads 4/6 穴馬", [
    TH_HEAD,
    "",
    f"穴は{c(ANA2)}{NAME[ANA2]}です。",
    "",
    f"・独自指数{RANK[ANA2]}位 {H[ANA2]['final170']}点",
    f"・{H[ANA2]['why']['sc12']}",
    f"・最高実績は{H[ANA2]['why']['sc19']}",
    "",
    "指数は上位なのに、単勝の支持は薄いままです。",
    "「指数の中位で支持が薄い」形は、過去データで拾えていた数少ないパターンでした。",
    "当たる回数は少ないので、単勝1,000円だけにします。",
    "",
    "穴馬、どのくらいの金額で買っていますか？",
])

th(doc, "Threads 5/6 追い切り", [
    TH_HEAD,
    "",
    "追い切りの評価って、見るサイトで全然ちがいますよね。",
    "なので2つ並べて、両方が同じことを言っている馬だけ信用することにしました。",
    "",
    f"そろって高評価だったのは{len(PROMOTE)}頭だけです。",
    "",
] + [f"・{c(u)}{NAME[u]}　{H[u]['oikiri']}" for u in PROMOTE] + [
    "",
    "追い切り、どこを見て判断していますか？",
])

th(doc, "Threads 6/6 買い目", [
    TH_HEAD,
    "",
    f"買い目は合計{BUD:,}円・{len(PT)}点です。",
    "",
] + [f"・{p['t']} {c(HON)}-{c(p['u'])}　{p['amt']:,}円" if p["t"] != "単勝"
     else f"・{p['t']} {c(p['u'])}　{p['amt']:,}円" for p in PT] + [
    "",
    "推定配当が安い買い目ほど厚く、高い買い目ほど薄く置いています。",
    "どれが当たっても戻る額が揃うようにするためです。",
    f"推定配当の逆数の合計は{V2['over']}で、1.0以下に収めました。",
    "",
    "明日の朝、実オッズを見て最終調整します。",
    "",
    "この「当たったのに負ける」やつ、経験ありませんか？",
])
doc.add_paragraph()

h1(doc, "SECTION 4｜note記事（全文無料・スプリンターズS＋日曜の注目レース）")
NOTE2 = HOOK + [
    "",
    f"結論を先に言います。スプリンターズSの本命は{c(HON)}{NAME[HON]}、",
    f"買い目は{BUD:,}円・{len(PT)}点です。1番人気は買い目から外しました。",
    "",
    "",
    "■ レース基本情報",
    "",
    "2026年9月27日(日) 中山競馬場 芝1200m（外回り） 16頭立て 15時40分発走",
    "",
    "",
    "■ コース特性と今回の狙いどころ",
    "",
    "中山の芝1200mは、外回りのスタートから下り坂で一気に加速して、",
    "ゴール前に急坂が待つコースです。",
    "前に行った馬がそのまま止まらない年と、坂で差し込まれる年がはっきり分かれます。",
    "",
    f"今回、はっきり逃げそうな馬は{SC['n_nige']}頭です。",
    "",
    "",
    "■ 過去10回のデータ",
    "",
    "・3連単の中央値は106,170円。10万円を超えた年が10回中5回",
    "・近3年の勝ち馬は8番人気・9番人気・11番人気",
    "・3着以内の脚質は先行が30.4%で最多。追い込みは12.3%",
    "・枠は1枠40%・3枠30%が良く、6枠は5%・8枠は10%",
    "",
    "3年続けて上位人気が勝っていません。",
    "上位人気だけで決まる前提で組むと、また置いていかれます。",
    "",
    "",
    "■ 昨日の中山の馬場",
    "",
    "9月26日(土)の中山は、3着以内に入った馬の脚質が " +
    "・".join(f"{k}{v}頭" for k, v in B_NAKAYAMA["surf"]["芝"].most_common()) + "でした。",
    "特定の脚質に偏っていません。前だけ、後ろだけに寄せる組み方はしません。",
    "",
    "",
    "■ 追い切りを2サイトで答え合わせ",
    "",
    "追い切りの評価はサイトによって割れます。そこで2つ並べて、",
    "両方が同じことを言っている馬だけを信用することにしました。",
    "",
    f"2サイトそろって高評価（SまたはA）だったのは{len(PROMOTE)}頭だけです。",
]
for u in PROMOTE:
    NOTE2.append(f"・{c(u)}{NAME[u]}　{H[u]['oikiri']}")
NOTE2 += [
    "",
    "全16頭の評価も出しておきます。並び順は独自指数の順です。",
    "",
] + [f"{c(h['uma'])}{h['name']}　{h['oikiri']}" for h in SC["horses"]] + [
    "",
    "",
    "■ 有力馬の詳細",
    "",
]
for lab, u in MK:
    NOTE2 += [f"{lab} {c(u)}{NAME[u]}（独自指数{RANK[u]}位 {H[u]['final170']}点）",
              f"　追い切り {H[u]['oikiri']}／脚質 {H[u]['style']}／{H[u]['waku']}枠",
              f"　{H[u]['why']['sc12']}／最高実績 {H[u]['why']['sc19']}", ""]
NOTE2 += [
    f"🔥 {c(ANA2)}{NAME[ANA2]}（独自指数{RANK[ANA2]}位 {H[ANA2]['final170']}点）",
    f"　追い切り {H[ANA2]['oikiri']}／脚質 {H[ANA2]['style']}／{H[ANA2]['waku']}枠",
    f"　{H[ANA2]['why']['sc12']}／最高実績 {H[ANA2]['why']['sc19']}",
    "",
    "",
    "■ 1番人気を買い目から外した理由",
    "",
    f"{c(DROP['uma'])}{DROP['name']}は独自指数が{DROP['rank']}位でした。",
    f"追い切りも{DROP['oikiri']}で、2サイトの評価が割れています。",
    f"そして本命とのワイドは推定{DROP['est']}倍です。",
    "",
    "推定4.0倍を切る組み合わせを本線に置かない、というのを決めています。",
    "当たっても投資額があまり増えないからです。",
    "",
    "昨日のシリウスSでも、当たったレースの回収が82%止まりでした。",
    "安すぎる組み合わせを厚く持ったのが原因です。同じことは繰り返しません。",
    "",
    "",
    "■ 全頭の独自指数",
    "",
] + [f"{i}位 {c(h['uma'])}{h['name']}　{h['final170']}点" for i, h in enumerate(SC["horses"], 1)] + [
    "",
    "",
    "■ 最終予想印",
    "",
] + [f"{lab} {c(u)}{NAME[u]}" for lab, u in MK] + [
    f"🔥 {c(ANA2)}{NAME[ANA2]}",
    "",
    "",
    "■ 買い目",
    "",
    f"合計{BUD:,}円・{len(PT)}点",
] + [f"{p['t']} {c(HON)}-{c(p['u'])}　{p['amt']:,}円（推定 約{p['est']}倍）" if p["t"] != "単勝"
     else f"{p['t']} {c(p['u'])}　{p['amt']:,}円（{p['est']}倍）" for p in PT] + [
    "",
    "金額の決め方も書いておきます。",
    "推定配当が安い買い目ほど厚く、高い買い目ほど薄く置いています。",
    "どのワイドが当たっても、戻る額がだいたい揃うようにするためです。",
    f"推定配当の逆数を全部足すと{V2['over']}。1.0を超えると、",
    "当たっても投資額に届かない点が必ず混ざるので、そこに収めました。",
    "",
    "",
    "■ 日曜の注目レース（平場）",
    "",
    f"全24レースを採点して、自信度7以上の{len(FLAT)}レースを選びました。",
    f"合計{sum(r['budget'] for r in FLAT):,}円です。",
    "",
]
for r in FLAT:
    hon = r["marks"][0]
    NOTE2 += [f"{r['venue']}{r['R']}R {r['name']}　{r['course']} {r['field']}頭　自信度{r['conf']}/10",
              f"　本命 {c(hon['uma'])}{hon['name']}（{hon['style']}）",
              "　" + "／".join(f"{b['t']} {b['raw']} {b['amt']:,}円" for b in r["bets"]), ""]
NOTE2 += [
    "",
    "■ まとめ",
    "",
    f"・スプリンターズSの本命は{c(HON)}{NAME[HON]}。独自指数1位で追い切りも2サイトそろって最高評価",
    "・1番人気は指数11位。ワイドの推定配当も安いので買い目から外しました",
    "・近3年の勝ち馬は8番人気・9番人気・11番人気。上位人気だけで決まる前提では組みません",
    "",
    "前日のオッズで組んでいます。明日の朝、実オッズと出走取消を見て組み直します。",
    "",
    "#競馬 #競馬予想 #スプリンターズS #AI予想 #G1",
]
note(doc, "note本文", NOTE2)
doc.add_paragraph()

try:
    doc.save(ROOT / "20260927" / "20260927_スプリンターズS前日予想_SNS投稿案.docx")
except PermissionError:
    print("[SKIP] 開いているため保存せず:", "20260927_スプリンターズS前日予想_SNS投稿案.docx")
print("saved ②", ROOT / "20260927" / "20260927_スプリンターズS前日予想_SNS投稿案.docx")

# ================================================================================
# ③ 明日の平場（自信度7以上）
# ================================================================================
doc = newdoc("9/27（日）平場 注目レース SNS投稿案",
             f"中山・阪神／自信度7以上 {len(FLAT)}レース・合計{sum(r['budget'] for r in FLAT):,}円")

h1(doc, "SECTION 1｜対象レース")
table(doc, [["レース", "条件", "自信度", "◎", "点数", "金額", "Σ(1/配当)"]] +
      [[f"{r['venue']}{r['R']}R {r['name']}", f"{r['course']} {r['field']}頭", f"{r['conf']}/10",
        f"{c(r['marks'][0]['uma'])}{r['marks'][0]['name']}", f"{len(r['bets'])}点",
        f"{r['budget']:,}円", r["over"]] for r in FLAT])

h1(doc, "SECTION 2｜X投稿")

top = sorted(FLAT, key=lambda r: (-r["conf"], r["over"]))
xpost(doc, "X① 明日の注目レース一覧（今夜／画像＝印一覧）", [
    "🏇【明日の注目レース】2026/09/27（日）",
    "━━ 中山・阪神 全24レース / 自信度7以上を厳選 ━━",
    "",
    f"全レースを採点して、自信度7以上の{len(FLAT)}レースだけ出します。",
    f"合計{sum(r['budget'] for r in FLAT):,}円。買わないレースも決めています。",
    f"いちばん自信があるのは{top[0]['venue']}{top[0]['R']}Rです。",
], [
    "",
    SEP,
    "■ 対象レースと本命",
    SEP,
] + sum([[f"{r['venue']}{r['R']}R {r['name']}　{r['course']} {r['field']}頭　自信度{r['conf']}/10",
          f"　◎{c(r['marks'][0]['uma'])}{r['marks'][0]['name']}（{r['marks'][0]['style']}）",
          f"　{len(r['bets'])}点 {r['budget']:,}円"] for r in FLAT], []) + [
    "",
    SEP,
    "■ 買い方",
    SEP,
    "本命は独自指数の1位から選びます。",
    "相手は指数では選ばず、単勝人気の上位から取ります。",
    "本命からのワイド流しで、どの点が当たってもほぼ同じ額が戻るように",
    "推定配当に反比例させて配分しています。",
    "",
    "推定配当の逆数を足した数字が1.0を超えないことを、レースごとに確認しています。",
    "超えると、当たっても投資額に届かない点が必ず混ざるためです。",
    "",
    SEP,
    "■ 買わないもの",
    SEP,
    "3連複と3連単は使いません。狭く絞った3連系は長く測ると回収が落ちるためです。",
    "🔥穴の馬は印には出しますが、軸にはしません。",
    "金額は自信度で決めた規定額のみ。G1の日でも増やしません。",
    "",
    "各レースの詳しい印と買い目は、このあとの返信に1レースずつ出します。",
], TAG3)

for i, r in enumerate(FLAT, 1):
    hon = r["marks"][0]
    tags = f"#競馬予想 #AI予想 #JRA #{r['venue']}競馬場"
    xpost(doc, f"X②-{i} {r['venue']}{r['R']}R {r['name']}（①の返信）", [
        f"🏇【{r['venue']}{r['R']}R {r['name']}】2026/09/27（日）",
        f"━━ {r['venue']}競馬場 {r['course']} / {r['field']}頭立て / AI自信度{r['conf']}/10 ━━",
        "",
        f"本命は{c(hon['uma'])}{hon['name']}（{hon['style']}）です。",
        f"買い目は{len(r['bets'])}点・{r['budget']:,}円。",
    ], [
        "■ 予想印",
    ] + [f"{m['lab']} {c(m['uma'])}{m['name']}　{m['style']}／指数{m['dokuji']}" +
         (f"／{m['why']}" if m["why"] else "") for m in r["marks"]] + [
        "",
        SEP,
        "■ 自信度の根拠",
        SEP,
        r["konkyo"],
        "",
        SEP,
        f"■ 買い目 合計{len(r['bets'])}点・{r['budget']:,}円",
        SEP,
    ] + [f"{b['t']} {b['raw']}　{b['amt']:,}円" for b in r["bets"]] + [
        "",
        f"推定配当の逆数を足すと{r['over']}。1.0以下なので、",
        "どの1点が当たっても投資額は上回ります。",
        "",
        "※明日朝の実オッズと出走取消を確認してから最終調整します。",
    ], tags)

h1(doc, "SECTION 3｜Threads投稿（4本）")
body(doc, "noteは重賞の記事に平場も含めた合併版を出すので、ここではThreadsのみ。", 9)

th(doc, "Threads 1/4 明日の注目レース", [
    "🏇【明日の注目レース】9/27(日) 中山・阪神 全24レース",
    "",
    f"全レースを採点して、自信度7以上の{len(FLAT)}レースだけ出します。",
    f"合計{sum(r['budget'] for r in FLAT):,}円。買わないレースも決めています。",
    "",
] + [f"・{r['venue']}{r['R']}R {r['name']}　自信度{r['conf']}/10" for r in FLAT] + [
    "",
    "みなさんは1日に何レース買いますか？",
])

th(doc, "Threads 2/4 自信度が高い2鞍", [
    "自信度10がついたのは2鞍です。",
    "",
] + sum([[f"{r['venue']}{r['R']}R {r['name']}　{r['course']} {r['field']}頭",
          f"　本命 {c(r['marks'][0]['uma'])}{r['marks'][0]['name']}（{r['marks'][0]['style']}）",
          f"　{r['konkyo'][:60]}", ""]
         for r in FLAT if r["conf"] >= 10], []) + [
    "少頭数で指数が抜けていると、自信度は上がります。",
    "",
    "少頭数のレース、得意ですか？",
])

th(doc, "Threads 3/4 買い方", [
    "平場も重賞と同じ組み方でいきます。",
    "",
    "・本命は独自指数の1位から選ぶ",
    "・相手は指数では選ばず、単勝人気の上位から取る",
    "・本命からのワイド流しで、推定配当に反比例させて配分する",
    "・推定配当の逆数を足した数字が1.0を超えないことをレースごとに確認する",
    "",
    "3連複と3連単は使いません。狭く絞った3連系は長く測ると回収が落ちるからです。",
    "",
    "みなさんは平場、どの券種で勝負していますか？",
])

th(doc, "Threads 4/4 買い目一覧", [
    "5鞍の買い目をまとめて出します。",
    "",
] + sum([[f"{r['venue']}{r['R']}R　{len(r['bets'])}点 {r['budget']:,}円",
          "　" + "／".join(f"{b['raw']} {b['amt']:,}円" for b in r["bets"]), ""]
         for r in FLAT], []) + [
    f"合計 {sum(r['budget'] for r in FLAT):,}円",
    "",
    "明日の朝、実オッズと出走取消を見て最終調整します。",
    "",
    "朝のオッズ、どのくらい気にしていますか？",
])
doc.add_paragraph()

try:
    doc.save(ROOT / "20260927" / "20260927_平場注目レース_SNS投稿案.docx")
except PermissionError:
    print("[SKIP] 開いているため保存せず:", "20260927_平場注目レース_SNS投稿案.docx")
print("saved ③", ROOT / "20260927" / "20260927_平場注目レース_SNS投稿案.docx")
print(f"\n平場合計 {sum(r['budget'] for r in FLAT):,}円 ／ スプリンターズS {BUDGET:,}円 "
      f"／ 日曜合計 {sum(r['budget'] for r in FLAT) + BUDGET:,}円")
