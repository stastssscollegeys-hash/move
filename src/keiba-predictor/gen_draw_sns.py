# -*- coding: utf-8 -*-
"""
gen_draw_sns.py — 枠順確定後の重賞 SNS投稿案（X6／Threads6／note12セクション＋docx）を汎用生成する（2026-10-02）
==========================================================================================================
入力（すべて {日付フォルダ}/research/ ）:
  draw_final.json          … draw_final.py の出力（枠・確率・指数・想定脚質・枠の実測）
  sns_kaime_{dir}.json     … draw_final.py の買い目ステージの出力（印・金額・検査結果）
  draw_content.json        … 本文（リード・レースの型・枠順の見どころ・各馬の根拠・前回からの変更）
  oikiri_final.json        … 最終追い切りの評価
出力: {日付フォルダ}/{dir}_重賞_枠順確定版_SNS投稿案.docx ／ 同名の note 用 .txt

docx 構成（keiba-draw-complete-ss Step 2）:
  冒頭: 実施状況（済み／当日に残る作業）
  SECTION 1 最終予想印 ／ 2 コース特性と枠順 ／ 3 有力馬個別診断 ／ 4 買い目 ／ 5 的中シナリオ ／ 6 SNS投稿案
ルール（SKILL v4.0 §2）: 2行ヘッダー→リード→───見出し／印の直後に人気を書かない／媒体名・内部用語を書かない／
  Threadsは500字以内／金額は100円単位／noteはマークダウン記号なし・冒頭フック定型
使い方: python gen_draw_sns.py --dir 20261004
"""
from __future__ import annotations
import argparse, itertools, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from kaime_format import circ, fmt_manual

BASE = Path.home() / "Desktop" / "競馬予想レポート"
SEP = "─────"
THREADS_LIMIT = 500
BAN = ["netkeiba", "SPAIA", "うましる", "競馬ラボ", "重賞ナビ", "ウマニティ", "東スポ", "サンスポ", "スポニチ", "日刊スポーツ",
       "デイリー", "PDCA", "EV", "sc[", "インフルエンサー", "両関門", "z=", "在サンプル", "Harville", "lift", "合算",
       "仮版", "暫定版では買", "お待ちください"]
MARKS = ("◎", "○", "▲", "△", "🔥")

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
a = ap.parse_args()
D = BASE / a.dir
R = D / "research"
FINAL = json.loads((R / "draw_final.json").read_text(encoding="utf-8"))
KAIME = json.loads((R / f"sns_kaime_{a.dir}.json").read_text(encoding="utf-8"))
CONT = json.loads((R / "draw_content.json").read_text(encoding="utf-8"))
OIK = json.loads((R / "oikiri_final.json").read_text(encoding="utf-8"))["races"]
DATE, TAGS = CONT["post_date_label"], CONT["hashtags"]
ODDS_CAVEAT = "発売前の予想オッズで組んだ参考の買い目です。当日朝に実際のオッズで金額を組み直します。"


class Race:
    def __init__(self, c):
        self.c = c
        self.f = next(r for r in FINAL["races"] if r["name"] == c["name"])
        self.k = KAIME["races"][c["name"]]
        self.h = {x["umaban"]: x for x in self.f["horses"]}
        self.oik = OIK.get(c["name"], {})
        m = self.k["marks"]
        self.marked = [("◎", m["◎"]), ("○", m["○"]), ("▲", m["▲"])] + [("△", u) for u in m["△"]] + \
                      ([("🔥", m["🔥"])] if m.get("🔥") else [])
        self.mark_of = {u: lab for lab, u in self.marked}
        self.caution = self.k.get("caution", [])

    def nm(self, u):
        return f"{circ(u)}{self.h[u]['name']}"

    def head(self):
        return f"🏇【{self.c['name']} {self.c['grade']}】{DATE}\n━━ {self.c['venue']} {self.c['course']} / {self.f['n']}頭 ━━"

    def tag(self):
        return f"{TAGS} {self.c['tag']}"

    def mark_lines(self):
        return [f"{lab} {self.nm(u)}" for lab, u in self.marked]

    def text(self, u):
        return self.c["horses"][str(u)]

    def kaime_lines(self):
        blocks, by = [], {}
        for p in self.k["points"]:
            by.setdefault(p["t"], []).append(p)
        hon = self.k["marks"]["◎"]
        for t, pts in by.items():
            axis = [p for p in pts if hon in p["combo"]]
            rest = [p for p in pts if hon not in p["combo"]]
            if axis:
                aite = "".join(circ(x) for p in axis for x in p["combo"] if x != hon)
                blocks.append((t, f"◎{circ(hon)}軸 ― 相手 {aite}",
                               [("-".join(circ(x) for x in sorted(p["combo"])), p["amt"]) for p in axis]))
            for p in rest:
                blocks.append((t, None, [("-".join(circ(x) for x in sorted(p["combo"])), p["amt"])]))
        return fmt_manual(blocks)

    def scenarios(self):
        pts, B = self.k["points"], self.k["budget"]
        m = self.k["marks"]

        def pay(top2, top3):
            tot, hit = 0, []
            for p in pts:
                c = set(p["combo"])
                ok = (p["t"] == "馬連" and c == set(top2)) or (p["t"] == "ワイド" and c <= set(top3)) or \
                     (p["t"] == "単勝" and p["combo"][0] == top2[0])
                if ok:
                    tot += p["back"]
                    hit.append(f"{p['t']}{'-'.join(circ(x) for x in sorted(p['combo']))}")
            return tot, hit

        def line(label, top2, third):
            tot, hit = pay(top2, list(top2) + [third])
            order = "→".join(circ(x) for x in list(top2) + [third])
            return f"{label}（{order}）: " + (f"{'・'.join(hit)} 的中 → 約{tot:,}円（回収率{tot / B * 100:.0f}%）" if hit
                                              else "的中なし → 0円")
        o, t, d1, d2 = m["○"], m["▲"], m["△"][0], m["△"][1]
        h, ana = m["◎"], m.get("🔥")
        out = [line("① 本命と対抗で決まる", (h, o), t),
               line("② 本命と単穴で決まる", (h, t), o),
               line("③ 本命が勝ち、2着に△", (h, d1), o),
               line("④ 本命が3着、対抗と単穴が1・2着", (o, t), h),
               line("⑤ 本命が着外、対抗と単穴が1・2着", (o, t), d1)]
        if ana:
            out.append(line("⑥ 人気薄の🔥が2着", (h, ana), o))
        out.append(f"⑦ 上のどれにも当てはまらない: 的中なし → 0円（投資{B:,}円）")
        return out


RACES = [Race(c) for c in CONT["races"]]


def pub_changes(c):
    """公開文用の変更点。docxの表は「△ → ○」と書くが、暫定印は公開していないので公開文では言葉で書く"""
    return [f"{x[1]}（{x[4] if len(x) > 4 else x[2]}）{x[3]}" for x in c["changes"]]


def odds_txt(o):
    return "予想オッズなし" if o is None or o >= 999 else f"{o}倍"


# ── X 6本 ─────────────────────────────────────────────────────────────
def x_posts(r: Race):
    c, m = r.c, r.k["marks"]
    P = []
    L = [r.head(), "", c["x_lead"], "", SEP, "🎯 予想印（枠順確定版）", SEP] + r.mark_lines()
    if r.caution:
        L += ["", "人気でも軸にしない馬: " + "・".join(r.nm(u) for u in r.caution)]
    L += ["", SEP, "枠順が出て変えたところ", SEP] + pub_changes(c)
    L += ["", "1頭ずつの根拠はスレッドで👇", r.tag()]
    P.append(("X① 予想印と変更点", L))

    for no, lab, u in (("②", "◎ 本命", m["◎"]), ("③", "○ 対抗", m["○"])):
        t = r.text(u)
        L = [r.head(), "", f"{lab} {r.nm(u)}", t["lead"], "", SEP, "根拠", SEP] + [f"・{x}" for x in t["detail"]] + ["", r.tag()]
        P.append((f"X{no} {lab}", L))

    L = [r.head(), "", f"▲ 単穴 {r.nm(m['▲'])}", r.text(m["▲"])["lead"], ""] + [f"・{x}" for x in r.text(m["▲"])["detail"]]
    if m.get("🔥"):
        L += ["", SEP, f"🔥 穴 {r.nm(m['🔥'])}", SEP, r.text(m["🔥"])["lead"]] + [f"・{x}" for x in r.text(m["🔥"])["detail"]]
    L += ["", r.tag()]
    P.append(("X④ ▲単穴と🔥穴", L))

    L = [r.head(), "", "△ 相手の2頭と、人気でも軸にしない馬です。", ""]
    for u in m["△"]:
        L += [f"△ {r.nm(u)}", r.text(u)["lead"]] + [f"・{x}" for x in r.text(u)["detail"]] + [""]
    for u in r.caution:
        L += [SEP, f"軸にしない馬 {r.nm(u)}", SEP] + [f"・{x}" for x in c["caution"][str(u)]] + [""]
    L += [SEP, "枠順の見どころ", SEP] + [f"・{x}" for x in c["draw_points"]] + ["", r.tag()]
    P.append(("X⑤ △と消し・枠順の見どころ", L))

    L = [r.head(), "", c["kaime_view"], ""] + r.kaime_lines() + ["", SEP, "決まり方ごとの戻り", SEP] + r.scenarios()[:5]
    L += ["", f"※{ODDS_CAVEAT}", f"※{CONT['rain_note']}", "", r.tag()]
    P.append(("X⑥ 買い目", L))
    return [(t, "\n".join(x)) for t, x in P]


# ── Threads 6本（各500字以内）──────────────────────────────────────────
def fit(lines_fixed_head, bullets, tail, limit=THREADS_LIMIT):
    """500字に収まるまで根拠を後ろから削る"""
    b = list(bullets)
    while True:
        body = "\n".join(lines_fixed_head + b + tail)
        if len(body) <= limit or len(b) <= 1:
            return body
        b.pop()


def threads_posts(r: Race):
    c, m = r.c, r.k["marks"]
    T = []
    T.append(("Threads 1/6 予想印", "\n".join([r.head(), "（1/6）予想印・枠順確定版", "", c["lead"], ""] + r.mark_lines() +
                                              ["", "根拠は次の投稿から👇", c["tag"]])))
    t = r.text(m["◎"])
    T.append(("Threads 2/6 本命", fit([r.head(), f"（2/6）◎ {r.nm(m['◎'])}", "", t["lead"], ""],
                                      [f"・{x}" for x in t["detail"]], ["", c["tag"]])))
    t1, t2 = r.text(m["○"]), r.text(m["▲"])
    T.append(("Threads 3/6 対抗と単穴", fit([r.head(), "（3/6）○と▲", "", f"○ {r.nm(m['○'])}", t1["lead"]] +
                                            [f"・{x}" for x in t1["detail"][:2]] + ["", f"▲ {r.nm(m['▲'])}", t2["lead"]],
                                            [f"・{x}" for x in t2["detail"][:2]], ["", c["tag"]])))
    L = [r.head(), "（4/6）△と🔥", ""]
    for lab, u in [("△", m["△"][0]), ("△", m["△"][1])] + ([("🔥", m["🔥"])] if m.get("🔥") else []):
        L += [f"{lab} {r.nm(u)}", f"・{r.text(u)['detail'][0]}", ""]
    T.append(("Threads 4/6 相手と穴", "\n".join(L + [c["tag"]])))
    L = [r.head(), "（5/6）枠順の見どころ", ""]
    cz = [f"軸にしない馬 {r.nm(u)}: {c['caution'][str(u)][0]}" for u in r.caution]
    T.append(("Threads 5/6 枠順の見どころ", fit(L, [f"・{x}" for x in c["draw_points"][:3]], [""] + cz[:1] + ["", c["tag"]])))
    T.append(("Threads 6/6 買い目", "\n".join([r.head(), "（6/6）買い目", ""] + r.kaime_lines() +
                                             ["", "予想オッズで組んだ参考の買い目です。当日朝に実際のオッズで組み直します。", c["tag"]])))
    return T


# ── note 12セクション（マークダウン記号なし）─────────────────────────
def note_article(r: Race):
    c, m, f = r.c, r.k["marks"], r.f
    hon = m["◎"]
    N = [f"【{c['name']}2026 予想】本命は{r.nm(hon)}｜枠順確定版・全頭診断と買い目", "",
         "1. はじめに",
         "こんにちは、アスメシ競馬予想です🍱",
         "「明日の飯代」を懸けて、AIとデータで競馬に挑む予想アカウントです。",
         f"結論を先に言います。{c['name']}の本命は{r.nm(hon)}、対抗は{r.nm(m['○'])}、単穴は{r.nm(m['▲'])}です。",
         c["lead"], "",
         "2. レース基本情報",
         f"{c['name']}（{c['grade']}）", f"{DATE} {c['start']}", f"{c['venue']} {c['course']} ／ {f['n']}頭立て", c["cond"], "",
         "3. コース特性と今回の狙い"] + c["course_note"] + ["", "このレースの過去10回"] + [f"・{x}" for x in c["profile"]] + \
        ["", "枠順の見どころ"] + [f"・{x}" for x in c["draw_points"]] + ["",
         "4. 予想オッズ一覧（発売前・全頭）", "馬券の発売前なので、ここに並べるのは予想オッズです。実際のオッズは当日朝に入れ替えます。"]
    for x in sorted(f["horses"], key=lambda x: x["pop"]):
        N.append(f"{x['pop']}番人気 {circ(x['umaban'])}{x['name']} {odds_txt(x['odds'])}")
    N += ["", "5. 追い切り評価", CONT["oikiri_note"]]
    order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    for u, o in sorted(r.oik.items(), key=lambda kv: (order.get(kv[1]["main"], 9), int(kv[0]))):
        g = "評価なし（映像がなく採点できず）" if o["main"] == "E" else f"評価{o['main']}／{o['agree']}"
        N.append(f"{circ(int(u))}{r.h[int(u)]['name']} {g}／{o['work']}")
    N += ["", "6. 枠順が出て変えたところ"] + pub_changes(c) + ["",
          "7. 有力馬 詳細分析"]
    for lab, u in r.marked:
        t = r.text(u)
        N += [f"{lab} {r.nm(u)}（{r.h[u]['jockey']}・{r.h[u]['kin']:g}kg・{r.h[u]['waku']}枠）", t["lead"]] + t["detail"] + [""]
    for u in r.caution:
        N += [f"軸にしない馬 {r.nm(u)}"] + c["caution"][str(u)] + [""]
    N += ["8. 全頭短評 & AI指数", "指数は20の要素を採点して100点に換算した数字です。枠順と馬番を入れて計算し直しました。"]
    for x in f["horses"]:
        u = x["umaban"]
        s = c["horses"][str(u)]["decide"] if str(u) in c["horses"] else \
            (c["caution"][str(u)][0] if str(u) in c.get("caution", {}) else c["others"].get(str(u), ""))
        N.append(f"{x['waku']}枠{circ(u)}{x['name']}（{x['sexage']}・{x['jockey']}）指数{x['index']} {r.mark_of.get(u, '')} {s}".replace("  ", " "))
    N += ["", "9. AI指数ランキング TOP5"]
    for x in sorted(f["horses"], key=lambda x: x["index_rank"])[:5]:
        prev = f"（枠順前は{x['prev_rank']}位）" if x.get("prev_rank") and x["prev_rank"] != x["index_rank"] else ""
        N.append(f"{x['index_rank']}位 {circ(x['umaban'])}{x['name']} {x['index']}{prev}")
    N += ["指数の順位と印は一致しません。指数は国内の過去の成績を機械的に採点したもので、距離の変化・休み明け・追い切り・海外での実績は入っていないからです。", "",
          "10. 最終予想印まとめ"] + [f"{lab} {r.nm(u)}　{r.text(u)['decide']}" for lab, u in r.marked] + ["",
          "11. 買い目設計", c["kaime_view"]] + r.kaime_lines() + ["", "決まり方ごとの戻り"] + r.scenarios() + \
        ["", ODDS_CAVEAT, CONT["rain_note"], "",
         "12. まとめ",
         f"・本命は{r.nm(hon)}。{r.text(hon)['decide']}",
         f"・相手は{r.nm(m['○'])}と{r.nm(m['▲'])}。△は{'・'.join(r.nm(u) for u in m['△'])}",
         f"・買い目は合計{r.k['budget']:,}円。当日朝に実際のオッズと馬場を見て組み直します",
         "", "結果もそのまま報告します。フォローしてお待ちいただけると嬉しいです🐴", "",
         f"{TAGS} {c['tag']} #競馬 #重賞予想"]
    return N


# ── 検査 ─────────────────────────────────────────────────────────────
PROBLEMS = []


def check(label, text, limit=None):
    hits = [b for b in BAN if b in text]
    if hits:
        PROBLEMS.append(f"{label}: 禁止語 {hits}")
    if limit and len(text) > limit:
        PROBLEMS.append(f"{label}: {len(text)}字（上限{limit}）")
    if re.search(r"[◎○▲△🔥] ?[①-⑱][^\n（]{2,12}（\d+番人気）", text):
        PROBLEMS.append(f"{label}: 印の直後に人気")
    for ln in text.split("\n"):
        if "3連単" in ln or "中央値" in ln:          # 過去の配当の記述は馬券の金額ではない
            continue
        for amt in re.findall(r"([\d,]+)円", ln):
            v = int(amt.replace(",", ""))
            if 0 < v < 100000 and v % 100:
                PROBLEMS.append(f"{label}: 100円単位でない金額 {amt}円")


# ── docx ─────────────────────────────────────────────────────────────
from docx import Document
from docx.shared import Pt

doc = Document()
doc.styles["Normal"].font.size = Pt(10)


def table(rows):
    tb = doc.add_table(rows=0, cols=len(rows[0]))
    tb.style = "Table Grid"
    for i, row in enumerate(rows):
        cells = tb.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = ""
            run = cells[j].paragraphs[0].add_run(str(v))
            run.font.size = Pt(8.5)
            run.font.bold = i == 0
    doc.add_paragraph()


def box(title, text, limit=None):
    tag = f"{len(text)}字" + (f"/{limit}字 {'OK' if len(text) <= limit else '⚠超過'}" if limit else "")
    doc.add_heading(f"{title}　{tag}", 3)
    tb = doc.add_table(rows=1, cols=1)
    tb.style = "Table Grid"
    tb.cell(0, 0).text = text
    doc.add_paragraph()
    check(title, text, limit)


doc.add_heading(f"重賞 枠順確定版 SNS投稿案 — {DATE}", 0)
doc.add_paragraph("・".join(f"{r.c['name']}（{r.c['grade']}）" for r in RACES) +
                  f"　各レース X6投稿＋Threads6投稿＋note記事　{CONT['compiled']}作成")
doc.add_heading("実施状況（この版でどこまで済んでいるか）", 1)
checks_ok = all(all(r.k["checks"].values()) for r in RACES)
table([["項目", "状態", "内容"],
       ["枠順・馬番", "済み", FINAL.get("draw_confirmed") or ""],
       ["出走取消", "済み", "／".join(f"{r.c['name']}: {'・'.join(r.f['scratched_from_predraw']) or 'なし'}" for r in RACES)],
       ["過去10回の型", "済み", "人気別・脚質別・枠別・配当を自前で集計"],
       ["最終追い切り", "済み", "全頭の時計を2つのページで照合。評価は媒体ごとに突き合わせ、台帳に保存"],
       ["指数", "済み", "枠・馬番を入れて再計算（枠順前の順位と比較）"],
       ["確率", "済み（予想オッズ）", "単勝オッズを確率に直し、実測で確認済みの消し要素（軽い斤量）だけを掛けた"],
       ["買い目の検査", "済み" if checks_ok else "⚠未通過あり",
        "100円単位／合計＝予算／推定配当の逆数の合計が1以下／本線4倍以上／1頭に依存しない／印の馬が1回は入る"],
       ["実際のオッズ", "当日朝", "発売前のため未反映。この版の買い目は参考（投資の推奨ではない）"],
       ["馬体重・馬場", "当日", "日曜は雨の予報。馬場を見て最終版を出す"],
       ["前向き台帳への登録", "当日朝", "実オッズのスナップショットを取ってから登録する"]])

for r in RACES:
    c, f, m = r.c, r.f, r.k["marks"]
    doc.add_page_break()
    doc.add_heading(f"■ {c['name']}（{c['grade']}）{DATE} {c['start']}　{c['venue']} {c['course']}　{f['n']}頭", 1)
    doc.add_paragraph(c["cond"])

    doc.add_heading("SECTION 1　最終予想印", 2)
    table([["印", "馬番", "馬名", "騎手", "AI指数（順位）", "勝つ確率／3着以内", "決め手"]] +
          [[lab, f"{r.h[u]['waku']}枠{circ(u)}", r.h[u]["name"], r.h[u]["jockey"],
            f"{r.h[u]['index']}（{r.h[u]['index_rank']}位）", f"{r.h[u]['p']*100:.1f}%／{r.h[u]['p_top3']*100:.1f}%",
            r.text(u)["decide"]] for lab, u in r.marked])
    doc.add_paragraph("前回（登録段階の暫定印）からの変更")
    table([["印", "馬名", "変更", "理由"]] + [x[:4] for x in c["changes"]])

    doc.add_heading("SECTION 2　コース特性と枠順", 2)
    for x in c["course_note"]:
        doc.add_paragraph(x)
    doc.add_paragraph("このレースの過去10回")
    for x in c["profile"]:
        doc.add_paragraph(f"・{x}")
    doc.add_paragraph("枠順の見どころ")
    for x in c["draw_points"]:
        doc.add_paragraph(f"・{x}")
    w = f["waku_measured"]
    doc.add_paragraph(f"枠ごとの実測（{c['venue']}{c['course']}・{w['races']}レース。人気から期待される3着以内の数に対する実際の数）")
    table([["枠"] + [f"{k}枠" for k in w["by_waku"]],
           ["実測÷期待"] + [v["ratio"] for v in w["by_waku"].values()],
           ["3着以内／期待"] + [f"{v['top3']}／{v['expected']}" for v in w["by_waku"].values()]])
    doc.add_paragraph("全頭一覧（枠順・予想オッズ・確率・指数・追い切り）")
    table([["枠", "番", "印", "馬名", "性齢", "斤量", "騎手", "想定脚質", "予想オッズ", "勝つ確率", "3着以内", "指数（順位←前）",
            "枠で動いた点", "追い切り"]] +
          [[x["waku"], x["umaban"], r.mark_of.get(x["umaban"], "注" if x["umaban"] in r.caution else ""), x["name"],
            x["sexage"], f"{x['kin']:g}", x["jockey"], x["style"] or "不明", f"{x['odds']}（{x['pop']}人気）",
            f"{x['p']*100:.1f}%", f"{x['p_top3']*100:.1f}%", f"{x['index']}（{x['index_rank']}←{x['prev_rank'] or '-'}）",
            f"{x['draw_delta']:+.2f}", f"{r.oik.get(str(x['umaban']), {}).get('main', '-')}／{r.oik.get(str(x['umaban']), {}).get('agree', '')}"]
           for x in f["horses"]])
    doc.add_paragraph("※指数の順位の変化には、枠・馬番のほかに厩舎の成績を新しく入れた分も含みます。枠・馬番だけで動いた点数は「枠で動いた点」の列です。")

    doc.add_heading("SECTION 3　有力馬個別診断", 2)
    for lab, u in r.marked:
        t = r.text(u)
        o = r.oik.get(str(u), {})
        doc.add_heading(f"{lab} {r.nm(u)}（{r.h[u]['sexage']}・{r.h[u]['kin']:g}kg・{r.h[u]['jockey']}）", 3)
        doc.add_paragraph(t["lead"])
        for x in t["detail"]:
            doc.add_paragraph(f"・{x}")
        doc.add_paragraph(f"最終追い切り: {o.get('work', '')}／評価 {o.get('main', '-')}（{o.get('agree', '')}）")
    for u in r.caution:
        doc.add_heading(f"軸にしない馬 {r.nm(u)}", 3)
        for x in c["caution"][str(u)]:
            doc.add_paragraph(f"・{x}")

    doc.add_heading("SECTION 4　買い目（参考・予想オッズ）", 2)
    doc.add_paragraph(c["kaime_view"])
    for ln in r.kaime_lines():
        doc.add_paragraph(ln)
    table([["券種", "組み合わせ", "金額", "推定配当", "的中時の戻り", "推定的中率", "役割"]] +
          [[p["t"], "-".join(circ(x) for x in sorted(p["combo"])), f"{p['amt']:,}円", f"{p['est']}倍", f"{p['back']:,}円",
            f"{p['p']*100:.1f}%", p["role"]] for p in r.k["points"]])
    doc.add_paragraph("検査: " + "　".join(f"{'✅' if v else '❌'}{k}" for k, v in r.k["checks"].items())
                      + f"　（推定配当の逆数の合計 {r.k['over']}）")
    if r.k.get("hit_any") is not None:
        doc.add_paragraph(f"どれか1点以上が当たる確率（推定）: {r.k['hit_any']*100:.0f}%　※全頭の着順確率から計算。2,388レースの実測と照合済みの方式")
    doc.add_paragraph(f"⚠ {ODDS_CAVEAT}")

    doc.add_heading("SECTION 5　的中シナリオ", 2)
    for x in r.scenarios():
        doc.add_paragraph(x)

    doc.add_heading("SECTION 6　SNS投稿案", 2)
    doc.add_heading("X（6本）", 3)
    xs = x_posts(r)
    for t, p in xs:
        box(f"{c['name']} {t}", p)
    doc.add_heading("Threads（6本・各500字以内）", 3)
    ts = threads_posts(r)
    for t, p in ts:
        box(f"{c['name']} {t}", p, THREADS_LIMIT)
    doc.add_heading("note記事（12セクション・全文無料）", 3)
    note = "\n".join(note_article(r))
    check(f"{c['name']} note", note)
    if re.search(r"^#{1,6} |\*\*", note.replace(TAGS, ""), re.M):
        PROBLEMS.append(f"{c['name']} note: マークダウン記号")
    doc.add_paragraph(note)
    (D / f"{a.dir}_{c['name']}_note記事_枠順確定版.txt").write_text(note, encoding="utf-8")
    print(f"■ {c['name']}: X {[len(p) for _, p in xs]}字 ／ Threads {[len(p) for _, p in ts]}字 ／ note {len(note):,}字")

out = D / f"{a.dir}_重賞_枠順確定版_SNS投稿案.docx"
try:
    doc.save(out)
except PermissionError:
    out = D / f"{a.dir}_重賞_枠順確定版_SNS投稿案_new.docx"
    doc.save(out)
print("検査: " + ("問題なし" if not PROBLEMS else f"{len(PROBLEMS)}件"))
for x in PROBLEMS:
    print("  ⚠", x)
print("保存:", out)
