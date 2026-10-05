# -*- coding: utf-8 -*-
"""
gen_zentou_sns.py — 出走全頭の短評をSNS投稿案（X＋Threads・docx）にする（2026-09-29新規）
==============================================================================================
入力: {日付フォルダ}/research/zentou_tanpyo.json
出力: X＝1レース5投稿（①導入+レースの型 ②〜④短評を分割 ⑤まとめ）
      Threads＝1投稿に3〜4頭（各500字以内・自動チェック）
      docx＝上記すべて

gen_watch_sns.py（注目馬だけ）の全頭版。全頭やると分量が多いので、
評価ティア（A→D）順に並べ、Xは6頭ずつ・Threadsは500字に収まる頭数ずつに機械的に割る。
ルール（SKILL v4.0 §2 SNS）: 2行ヘッダー→リード→───見出し／印の直後に人気を書かない／
      サイト名・人物名・内部用語を書かない／noteは作らない
使い方: python gen_zentou_sns.py --dir 20261004
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
BAN = ["netkeiba", "SPAIA", "うましる", "競馬ラボ", "重賞ナビ", "アジフライ", "しろクロ", "うまログ",
       "ウマキング", "カリスマ", "PDCA", "EV", "sc[", "インフルエンサー", "指数", "両関門", "z=",
       "川田", "ルメール", "津村", "横山", "池添", "松山", "浜中", "岩田", "佐々木", "坂井"]
THREADS_LIMIT = 500

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
a = ap.parse_args()
D = BASE / a.dir
J = json.loads((D / "research" / "zentou_tanpyo.json").read_text(encoding="utf-8"))
DATE, TAGS = J["post_date_label"], J["hashtags"]


def header(r):
    return f"🏇【{r['name']} {r['grade']}】{DATE}\n━━ {r['venue']} {r['course']} / {r['entries']} ━━"


def sec(t):
    return f"─────\n{t}\n─────"


def horse_line(h):
    head = h["name"]
    sub = "・".join(x for x in (h.get("age"), h.get("kin")) if x)
    if sub:
        head += f"（{sub}）"
    return f"◆ {head}\n{h['text']}"


def chunks(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def x_posts(r):
    hs = r["horses"]
    out = [ "\n".join([header(r), "", r["lead"], "", sec("レースの型（過去10回の自前集計）")]
                      + [f"・{x}" for x in r["profile"]]
                      + ["", "全頭の短評をスレッドで出します👇", f"{TAGS} {r['tag']}"]) ]
    groups = chunks(hs, 6)
    for i, g in enumerate(groups, 1):
        out.append("\n".join([header(r), f"【全頭短評 {i}/{len(groups)}】", ""]
                             + [horse_line(h) + "\n" for h in g] + [f"{TAGS} {r['tag']}"]))
    top = [h["name"] for h in hs if h.get("tier") == "A"]
    out.append("\n".join([header(r), "【まとめ】", "",
                          "この中から上位に取りたいのは次の3頭です。", "",
                          *[f"・{n}" for n in top], "",
                          "枠順と当日の馬体重が出たら、最終予想と買い目を出します。",
                          f"{TAGS} {r['tag']}"]))
    return out


def threads_posts(r):
    hs = r["horses"]
    posts, cur = [], []
    head = header(r)
    for h in hs:                       # 500字に収まる範囲で詰める
        cand = cur + [h]
        body = "\n\n".join(horse_line(x) for x in cand)
        if len(head) + len(body) + len(r["tag"]) + 20 > THREADS_LIMIT and cur:
            posts.append(cur)
            cur = [h]
        else:
            cur = cand
    if cur:
        posts.append(cur)
    total = len(posts) + 1
    out = ["\n".join([head, f"（1/{total}）レースの型と出走頭数", "", r["lead"], ""]
                     + [f"・{x}" for x in r["profile"][:2]]
                     + ["", "全頭短評は次の投稿から👇", r["tag"]])]
    for i, g in enumerate(posts, 2):
        out.append("\n".join([head, f"（{i}/{total}）全頭短評", ""]
                             + [horse_line(h) for h in g] + ["", r["tag"]]))
    return out


from docx import Document
from docx.shared import Pt
doc = Document()
doc.styles["Normal"].font.size = Pt(10)
doc.add_heading(f"出走全頭 短評 SNS投稿案（X＋Threads）— {DATE}", 0)
doc.add_paragraph(J["note"])
nban = 0


def check(text, label):
    hits = [b for b in BAN if b in text]
    if hits:
        print(f"  ⚠ {label}: 禁止語 {hits}")
    return hits


for r in J["races"]:
    doc.add_heading(f"{r['name']}（{r['grade']}・{r['venue']} {r['course']}／{r['entries']}）", 1)
    xs, ts = x_posts(r), threads_posts(r)
    doc.add_heading(f"X投稿（{len(xs)}本）", 2)
    for k, p in enumerate(xs, 1):
        doc.add_heading(f"X{k}　{len(p)}字", 3)
        doc.add_paragraph(p)
        nban += len(check(p, f"{r['name']} X{k}"))
    doc.add_heading(f"Threads投稿（{len(ts)}本）", 2)
    for k, p in enumerate(ts, 1):
        ok = "OK" if len(p) <= THREADS_LIMIT else "⚠超過"
        doc.add_heading(f"Threads {k}/{len(ts)}　{len(p)}字/{THREADS_LIMIT}字 {ok}", 3)
        doc.add_paragraph(p)
        nban += len(check(p, f"{r['name']} T{k}"))
    over = [len(p) for p in ts if len(p) > THREADS_LIMIT]
    print(f"■ {r['name']}: {len(r['horses'])}頭 ／ X {len(xs)}本{[len(p) for p in xs]} ／ "
          f"Threads {len(ts)}本{'（超過あり:' + str(over) + '）' if over else '（全て500字以内）'}")

out = D / f"{a.dir}_出走全頭短評_SNS投稿案.docx"
try:
    doc.save(out)
except PermissionError:
    out = D / f"{a.dir}_出走全頭短評_SNS投稿案_new.docx"
    doc.save(out)
print(f"禁止語検出 {nban}件 ／ 保存: {out}")
