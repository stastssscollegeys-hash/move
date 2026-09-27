# -*- coding: utf-8 -*-
"""
gen_weekend_20260926.py — 9/26シリウスS・9/27スプリンターズS のSNS投稿案（X6／Threads5／Note）
================================================================================================
2026-09-19に承認された買い方（◎は指数1位・相手は市場人気上位・ワイド流し・Σ(1/配当)≦1）で作る。
本文の数字はすべて生成物から引く（手打ちしない）:
  research/score20_20260925.json … 20因子・追い切り2ソース・根拠
  research/kaime_sirius.json / kaime_sprinters.json … 印と買い目（kaime_mixed.py）
出力: 20260926/20260926-27_重賞2本_SNS投稿案.docx
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

ROOT = Path.home() / "Desktop" / "競馬予想レポート"
BASE = ROOT / "20260926"
OUT = BASE / "20260926-27_重賞2本_SNS投稿案.docx"
FONT = "游ゴシック"
CIRC = "⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱"
SEP = "─────────────────────"
TAGS = "#競馬予想 #AI予想 #JRA"

SCORE = json.loads((BASE / "research" / "score20_20260925.json").read_text(encoding="utf-8"))
KAIME = {"シリウスS": json.loads((BASE / "research" / "kaime_sirius.json").read_text(encoding="utf-8")),
         "スプリンターズS": json.loads((BASE / "research" / "kaime_sprinters.json").read_text(encoding="utf-8"))}

META = {
    "シリウスS": dict(name="シリウスステークス", grade="G3", date="2026/09/26（土）", when="土曜",
                    place="阪神競馬場", course="ダート2000m", field="16頭立て", start="15:45発走",
                    sub="秋のダート重賞・ハンデ戦", style_note="逃げ30.8%・差し29.2%が多く、追い込みは9.7%です",
                    hist=["過去6回（阪神ダート2000mで行われた年）の3連単の中央値は111,770円。10万円を超えた年が半分",
                          "勝ち馬の人気は1・2・3・6・8・11番人気とばらばら。1〜3番人気が勝ったのは半分",
                          "3着以内の脚質は逃げ30.8%・差し29.2%が高く、追い込みは9.7%",
                          "枠は2枠38%・3枠36%が良く、1枠は0%・6枠は8%"],
                    course_note=["阪神のダート2000mは、スタートしてすぐ坂を上り、向こう正面から下ってコーナー4回を回る形です。",
                                 "ハンデ戦で実績馬に重い斤量がかかる一方、軽ハンデの上がり馬が来やすいレースです。",
                                 "過去6回では前に行った馬と差し馬が半々で、後方からの追い込みはほとんど届いていません。"]),
    "スプリンターズS": dict(name="スプリンターズステークス", grade="G1", date="2026/09/27（日）", when="日曜",
                    place="中山競馬場", course="芝1200m（外回り）", field="16頭立て", start="15:40発走",
                    sub="秋のスプリント王決定戦", style_note="先行30.4%が最も多く、追い込みは12.3%です",
                    hist=["過去10回の3連単の中央値は106,170円。10万円超えが10回中5回",
                          "近3年の勝ち馬は8番人気・9番人気・11番人気。上位人気で決まらない年が続いています",
                          "1番人気は勝率40%・複勝率60%で、10年通算では単勝回収率126%",
                          "3着以内の脚質は先行30.4%が最も高く、追い込みは12.3%",
                          "枠は1枠40%・3枠30%が良く、6枠は5%・8枠は10%"],
                    course_note=["中山の芝1200mは、外回りのスタートから下り坂で加速し、ゴール前に急坂が待つコースです。",
                                 "前に行った馬がそのまま止まらない年と、坂で差し込まれる年がはっきり分かれます。",
                                 "近3年は2桁人気の伏兵が勝っており、上位人気だけで決まると考えないほうがよいレースです。"]),
}


def c(n):
    return CIRC[int(n)] if 0 <= int(n) <= 18 else str(n)


def set_font(run, size=10, bold=False, color=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def h1(doc, t, col=(20, 60, 140)):
    p = doc.add_paragraph(); set_font(p.add_run(t), 13, True, col)


def h2(doc, t, col=(70, 70, 70)):
    p = doc.add_paragraph(); set_font(p.add_run(t), 11, True, col)


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


def post(doc, title, lines, limit=None):
    n = len("\n".join(lines))
    tag = f"（{n}字/{limit}字 {'OK' if n <= limit else '⚠超過'}）" if limit else f"（{n}字）"
    h2(doc, f"{title} {tag}")
    tb = doc.add_table(rows=1, cols=1); tb.style = "Table Grid"
    cell = tb.cell(0, 0); cell.text = ""
    for i, ln in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        set_font(p.add_run(ln), 9.5)
    doc.add_paragraph()
    if limit and n > limit:
        print(f"[WARN] 超過 {title} {n}字")
    return n


class R:
    """1レース分のデータをまとめて扱う"""
    def __init__(self, key):
        self.key = key
        self.meta = META[key]
        self.sc = SCORE[key]
        self.k = KAIME[key]
        self.horses = {h["uma"]: h for h in self.sc["horses"]}
        self.rank = {h["uma"]: i + 1 for i, h in enumerate(self.sc["horses"])}
        self.name = {int(k): v for k, v in self.k["name"].items()}
        self.pop = {int(k): v for k, v in self.k["pop"].items()}
        self.odds = {int(k): v for k, v in self.k["odds"].items()}
        d = self.k["design"]
        self.hon = d["hon"]
        self.aite = d["aite"]
        self.bets = d.get("bets", [])
        self.budget = d.get("budget", 0)
        self.over = d.get("over")
        # 🔥穴: 指数3位以内で印が付いていない馬のうち、最も人気が無い馬
        marked = {self.hon, *self.aite}
        cand = [h["uma"] for h in self.sc["horses"][:4] if h["uma"] not in marked]
        self.ana = max(cand, key=lambda u: self.pop[u]) if cand else None

    def mark_rows(self):
        rows = [["印", "馬番", "馬名", "人気", "指数順位", "指数", "追い切り(2ソース)", "決め手"]]
        for lab, u in [("◎", self.hon)] + list(zip(("○", "▲", "△", "△"), self.aite)):
            h = self.horses[u]
            rows.append([lab, c(u), self.name[u], f"{self.pop[u]}番人気 {self.odds[u]}倍",
                         f"{self.rank[u]}位", h["final170"], h["oikiri"], h["why"]["sc12"]])
        if self.ana:
            h = self.horses[self.ana]
            rows.append(["🔥", c(self.ana), self.name[self.ana], f"{self.pop[self.ana]}番人気 {self.odds[self.ana]}倍",
                         f"{self.rank[self.ana]}位", h["final170"], h["oikiri"], h["why"]["sc12"]])
        return rows

    def kaime_lines(self):
        if not self.bets:
            return ["💰 買い目 このレースは見送り"]
        L = [f"💰 買い目 合計{len(self.bets)}点・{self.budget:,}円"]
        for t in ("ワイド", "馬連"):
            items = [b for b in self.bets if b["t"] == t]
            if items:
                L.append(f"【{t}】（{len(items)}点 {sum(b['amt'] for b in items):,}円）")
                L += [f"　{c(self.hon)}-{c(b['u'])} {b['amt']:,}円" for b in items]
        lo = min(b["ret"] for b in self.bets); hi = max(b["ret"] for b in self.bets)
        L.append(f"1点的中の回収率: 約{lo*100:.0f}〜{hi*100:.0f}%（どの点が当たってもほぼ同じ額が戻る配分）")
        return L

    def head(self):
        m = self.meta
        return [f"🏇【{m['name']} {m['grade']}】{m['date']}",
                f"━━ {m['place']} {m['course']} / {m['sub']} / {m['field']} ━━"]


def x_posts(r: R):
    m, out = r.meta, []
    L = r.head() + ["", m["hist"][0] + "。", f"本命は{c(r.hon)}{r.name[r.hon]}です。", "", SEP, "🎯 予想印", SEP, ""]
    for lab, u in [("◎", r.hon)] + list(zip(("○", "▲", "△", "△"), r.aite)):
        L.append(f"{lab} {c(u)}{r.name[u]}")
    if r.ana:
        L.append(f"🔥 {c(r.ana)}{r.name[r.ana]}")
    L += ["", "本命は独自の20ファクター指数の1位。相手は単勝人気の上位から選んでいます。",
          "先週、指数だけで相手を決めて全滅した反省を反映した形です。", "", "根拠はスレッドで👇", "", TAGS, f"#{m['name']}"]
    out.append(("【X投稿①】予想印一覧", L))

    h = r.horses[r.hon]
    L = r.head() + ["", SEP, f"◎ 本命 {c(r.hon)}{r.name[r.hon]}", SEP, "",
                    f"・独自の20ファクター指数{h['final170']}点でメンバー1位",
                    f"・最終追い切りの評価は「{h['oikiri']}」" + ("（2つの評価がそろって高評価）" if h["oikiri_promote"] else ""),
                    f"・{h['why']['sc12']}", f"・{h['why']['sc18']}", f"・最高実績は{h['why']['sc19']}",
                    f"・脚質は{h['style']}。このレースで3着以内に入った馬は{m['style_note']}", "", TAGS, f"#{m['name']}"]
    out.append(("【X投稿②】本命の根拠", L))

    L = r.head() + ["", SEP, "○▲△ 相手（単勝人気の上位から）", SEP, ""]
    for lab, u in zip(("○", "▲", "△", "△"), r.aite):
        hh = r.horses[u]
        L += [f"{lab} {c(u)}{r.name[u]}（指数{r.rank[u]}位）",
              f"　{hh['why']['sc12']}／追い切り {hh['oikiri']}", ""]
    L += ["相手を人気上位から選ぶのは、過去452レースで一番安定していた組み方だからです（的中率43.8%）。", "", TAGS, f"#{m['name']}"]
    out.append(("【X投稿③】相手の根拠", L))

    L = r.head() + ["", SEP, "📊 過去データが示すこと", SEP, ""] + [f"・{x}" for x in m["hist"]] + ["", TAGS, f"#{m['name']}"]
    out.append(("【X投稿④】過去データ", L))

    L = r.head() + ["", SEP, "🏟 コースと展開", SEP, ""] + m["course_note"]
    L += ["", f"今回の想定: はっきり逃げそうな馬は{r.sc['n_nige']}頭です。", "", TAGS, f"#{m['name']}"]
    out.append(("【X投稿⑤】コースと展開", L))

    L = r.head() + ["", SEP, "🎯 買い方と買い目", SEP, "",
                    "本命は指数1位、相手は単勝人気の上位。◎からのワイド流しで、どの点が当たってもほぼ同じ額が戻るように配分しています。", ""]
    L += r.kaime_lines()
    L += ["", (f"推定配当の逆数を足すと{r.over}（1.00以下）。どの1点が当たっても投資額を下回りません。" if r.over else ""),
          "", "※前日オッズで組んでいます。当日朝の実オッズと馬場で最終調整します🐴", "",
          f"⚠ このレースは荒れる型です。{m['hist'][1]}", "", TAGS, f"#{m['name']}"]
    out.append(("【X投稿⑥】買い目", [x for x in L if x != ""] if False else L))
    return out


def threads_posts(r: R):
    m = r.meta
    head = f"🏇【{m['name']} {m['grade']}】{m['date']}\n━━ {m['place']} {m['course']} / {m['field']} ━━"
    T = []
    T.append(("【Threads 1/5】印", [head, "", "🎯 予想印（1/5）", ""] +
              [f"{lab} {c(u)}{r.name[u]}" for lab, u in [("◎", r.hon)] + list(zip(("○", "▲", "△", "△"), r.aite))] +
              ([f"🔥 {c(r.ana)}{r.name[r.ana]}"] if r.ana else []) +
              ["", m["hist"][0], "", "あなたの本命はどの馬ですか？"]))
    h = r.horses[r.hon]
    T.append(("【Threads 2/5】本命", [head, "", f"◎{c(r.hon)}{r.name[r.hon]}（2/5）", "",
                                   f"・指数{h['final170']}点で1位", f"・追い切り {h['oikiri']}",
                                   f"・{h['why']['sc12']}", "", "この本命、どう見ますか？"]))
    T.append(("【Threads 3/5】相手", [head, "", "相手は人気上位から（3/5）", ""] +
              [f"{lab} {c(u)}{r.name[u]}" for lab, u in zip(("○", "▲", "△", "△"), r.aite)] +
              ["", "先週、指数だけで相手を選んで全滅した反省です。"]))
    T.append(("【Threads 4/5】過去データ", [head, "", "📊 このレースの傾向（4/5）", ""] +
              [f"・{x}" for x in m["hist"][:3]] + ["", "荒れる型です。"]))
    T.append(("【Threads 5/5】買い目", [head, "", "💰 買い目（5/5）", ""] + r.kaime_lines() +
              ["", "当日朝の実オッズで最終調整します🎯"]))
    return T


def note_article(rs: list[R]):
    N = [f"【9/26-27 AI予想】{rs[0].meta['name']}は◎{rs[0].name[rs[0].hon]}／{rs[1].meta['name']}は◎{rs[1].name[rs[1].hon]}", "",
         "1. はじめに", "こんにちは、アスメシ競馬予想です🍱", "「明日の飯代」を懸けて、AIとデータで競馬に挑む予想アカウントです。",
         "今週末は土曜にシリウスステークス(G3)、日曜にスプリンターズステークス(G1)。2レースまとめてお届けします。", "",
         "結論を先に言います。" + "／".join(f"{r.meta['name']}は{c(r.hon)}{r.name[r.hon]}" for r in rs) + "です。", "",
         "2. 今週の買い方（先週の反省）",
         "先週は本命が5レース中3勝したのに回収率18%でした。相手を指数の2位・3位から選んでいて、人気上位の馬が2着に来たレースで全滅したからです。",
         "そこで今週も、本命は独自指数の1位、相手は単勝人気の上位から選びます。過去452レースで比べて一番安定していた組み方です（的中率43.8%）。",
         "買い目は本命からのワイド流しで、どの点が当たってもほぼ同じ額が戻るように配分します。1点だけ当たって損になる組み合わせは外します。", ""]
    for i, r in enumerate(rs, start=3):
        m = r.meta
        N += [f"{i}. {m['name']}（{m['grade']}）", f"{m['date']} {m['start']}　{m['place']} {m['course']}　{m['field']}　{m['sub']}", ""]
        N += m["course_note"] + ["", "過去データのポイント"] + [f"・{x}" for x in m["hist"]] + ["", "予想印"]
        for lab, u in [("◎", r.hon)] + list(zip(("○", "▲", "△", "△"), r.aite)):
            h = r.horses[u]
            N.append(f"{lab} {c(u)}{r.name[u]}（指数{r.rank[u]}位 {h['final170']}点）"
                     f"　追い切り {h['oikiri']}　{h['why']['sc12']}")
        if r.ana:
            h = r.horses[r.ana]
            N.append(f"🔥 {c(r.ana)}{r.name[r.ana]}（指数{r.rank[r.ana]}位）　{h['why']['sc12']}"
                     "　※印としては注目していますが、買い目には入れていません")
        N += ["", "全頭の指数"]
        for j, h in enumerate(r.sc["horses"], 1):
            N.append(f"{j}位 {c(h['uma'])}{h['name']} {h['final170']}点／追い切り {h['oikiri']}／{h['why']['sc12']}")
        N += ["", "買い目"] + r.kaime_lines() + [""]
    N += [f"{len(rs)+3}. 注意点",
          "どちらも「荒れる型」のレースです。スプリンターズSは近3年の勝ち馬が8・9・11番人気で、人気上位から相手を取る今の買い方とは相性が良くありません。",
          "それでも同じ物差しで続けて、当たり外れを毎週そのまま報告します。",
          "前日のオッズで組んでいるので、当日朝の実オッズと馬場を見て金額を調整します。", "",
          f"{len(rs)+4}. まとめ"]
    for r in rs:
        N.append(f"・{r.meta['name']}は{c(r.hon)}{r.name[r.hon]}が本命。相手は{('・'.join(c(u)+r.name[u] for u in r.aite))}")
    N += ["・買い目は合計" + f"{sum(r.budget for r in rs):,}円。どの1点が当たっても損にならない配分にしています",
          "", "結果もそのまま報告します。フォローしてお待ちください🐴", "",
          "#競馬予想 #AI予想 #JRA #シリウスステークス #スプリンターズステークス #競馬"]
    return N


def main():
    rs = [R("シリウスS"), R("スプリンターズS")]
    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.8); s.left_margin = Cm(2.0); s.right_margin = Cm(2.0)
    t = doc.add_heading("2026/9/26-27 重賞2本 SNS投稿案（枠順確定版）", level=0)
    for x in t.runs:
        set_font(x, 16)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(f"シリウスS(G3) / スプリンターズS(G1)　各レース X6投稿＋Threads5投稿＋Note記事（合同）"
                            f"　総投資{sum(r.budget for r in rs):,}円　2026-09-25作成")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for x in sub.runs:
        set_font(x, 9.5)
    body(doc, "【買い方】◎は独自指数1位・相手は単勝人気の上位4頭・◎からのワイド流し（2026-09-19ユーザー承認）。"
              "1点的中で損になる組み合わせは馬連に替えるか外す（Σ(1/配当)≦1）。3連複・3連単は使わない。", 9)
    body(doc, "【オッズ】前日オッズ（9/25取得）。当日朝の実オッズで金額を再計算する。現在は集客フェーズのため実際には購入しない。", 9)
    body(doc, "【追い切り】うましる×競馬チャンネルの2ソース平均。両ソースがS/Aの馬だけ「昇格候補」として扱う。", 9)
    doc.add_paragraph()

    for r in rs:
        m = r.meta
        h1(doc, f"■ {m['name']}（{m['grade']}）　{m['date']}　{m['place']} {m['course']}　{m['start']}")
        body(doc, f"{m['field']} ／ {m['sub']} ／ レース型: {r.sc['type']} ／ 予算{r.budget:,}円", 9.5)
        h2(doc, "最終予想印")
        table(doc, r.mark_rows())
        h2(doc, "過去データ")
        body(doc, "\n".join(f"・{x}" for x in m["hist"]))
        h2(doc, "買い目")
        body(doc, "\n".join(r.kaime_lines()))
        h2(doc, "全頭の20ファクター指数")
        table(doc, [["順", "枠-番", "馬名", "脚質", "指数", "追い切り(2ソース)", "前走", "同コース実績"]] +
              [[i, f"{h['waku']}-{h['uma']}", h["name"], h["style"], h["final170"], h["oikiri"],
                h["why"]["sc12"], h["why"]["sc18"]] for i, h in enumerate(r.sc["horses"], 1)])
        h2(doc, "── X（Twitter）投稿 6本 ──", (20, 100, 50))
        for title, lines in x_posts(r):
            post(doc, title, lines)
        h2(doc, "── Threads 投稿 5本（各500字以内）──", (150, 60, 120))
        for title, lines in threads_posts(r):
            post(doc, title, lines, limit=500)
        doc.add_page_break()

    h1(doc, "■ Note記事（2レース合同・全文無料）", (120, 70, 0))
    body(doc, "\n".join(note_article(rs)), 10)
    doc.save(str(OUT))
    print("[保存]", OUT)
    print(f"　投稿数: {(6+5)*len(rs)} / 総投資 {sum(r.budget for r in rs):,}円")


if __name__ == "__main__":
    main()
