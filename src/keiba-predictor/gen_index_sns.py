# -*- coding: utf-8 -*-
"""
gen_index_sns.py — 独自指数ランキングをSNS1投稿ずつにする（2026-09-30新規）
================================================================================
入力: {日付フォルダ}/research/index_ranking.json（calc_index_preview.py の出力）
出力: 各レース X1投稿 ＋ Threads1投稿（500字以内）＋ docx

全頭短評（gen_zentou_sns.py）とは別に、「指数順の一覧だけ」を1枚で見せる投稿。
Xは全18頭、Threadsは500字に収まらないので上位10頭＋下位の要約にする。
使い方: python gen_index_sns.py --dir 20261004
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
THREADS_LIMIT = 500
TAGS = "#競馬予想 #AI予想 #JRA"
TAG_OF = {"毎日王冠": "#毎日王冠", "京都大賞典": "#京都大賞典"}
BAN = ["netkeiba", "SPAIA", "うましる", "競馬ラボ", "重賞ナビ", "PDCA", "両関門", "z=", "在サンプル"]

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
a = ap.parse_args()
D = BASE / a.dir
J = json.loads((D / "research" / "index_ranking.json").read_text(encoding="utf-8"))
DATE = "2026年10月4日（日）"

NOTE = ("※枠順・馬体重・オッズは未発表のため、その4因子は全馬同じ値で計算しています"
        "（順位には影響しません）。枠順確定後に更新します。")

# 🔴 指数と印は別物。ユーザー指示（2026-09-30）で必ず明記する。
#    指数は過去走の数字だけの機械採点なので、距離変化・休み明け・追い切り・海外実績は入らない。
#    レースごとに「実際にズレている馬」を具体例として出す。
MISMATCH = {
 "毎日王冠": ["🔴この順位は最終予想の印とは一致しません。",
              "指数は過去走の数字だけを機械的に採点したものです。",
              "距離が変わること、休み明けかどうか、追い切りの内容は点数に入りません。",
              "たとえばリアライズシリウスは指数9位ですが、2400mから1800mへ距離が戻る点は"
              "1点も加算されていません。印はそこまで含めて決めるので、指数1位＝本命にはなりません。"],
 "京都大賞典": ["🔴この順位は最終予想の印とは一致しません。",
                "指数は過去走の数字だけを機械的に採点したものです。",
                "しかも集計しているのは国内のレースだけです。",
                "たとえばディープモンスターは指数13位ですが、これは今年ここまで海外を使っていて"
                "国内の出走がないためで、実際には海外で重賞を勝っています。"
                "印はそこまで含めて決めるので、指数1位＝本命にはなりません。"],
}
MISMATCH_SHORT = ("🔴この順位は印とは一致しません。指数は国内の過去走の数字だけの採点で、"
                  "距離変化・休み明け・追い切り・海外実績は入りません。")


def header(r):
    return f"🏇【{r['race']} G2】{DATE}\n━━ {r['venue']} {r['course']} / {len(r['horses'])}頭 ━━"


def x_post(r):
    lines = [header(r), "", "【AI指数ランキング 全頭】", ""]
    for h in r["horses"]:
        mark = "🥇" if h["rank"] == 1 else "🥈" if h["rank"] == 2 else "🥉" if h["rank"] == 3 else f"{h['rank']:>2}"
        lines.append(f"{mark} {h['name']}　{h['index']}")
    lines += ["", "20の要素を170点満点で採点し、100点換算した数字です。", NOTE, "",
              "─────", "指数と印は別物です", "─────"]
    lines += MISMATCH.get(r["race"], [MISMATCH_SHORT])
    lines += ["", f"{TAGS} {TAG_OF.get(r['race'], '')}"]
    return "\n".join(lines)


def threads_post(r):
    top = r["horses"][:10]
    rest = r["horses"][10:]
    lines = [header(r), "", "【AI指数ランキング】", ""]
    for h in top:
        mark = "🥇" if h["rank"] == 1 else "🥈" if h["rank"] == 2 else "🥉" if h["rank"] == 3 else f"{h['rank']:>2}"
        lines.append(f"{mark} {h['name']} {h['index']}")
    if rest:
        lines.append("")
        lines.append(f"11位以下は {'・'.join(h['name'] for h in rest)}")
    lines += ["", "20の要素を採点した数字です。枠順確定後に更新します。",
              MISMATCH_SHORT, TAG_OF.get(r["race"], "")]
    body = "\n".join(lines)
    if len(body) > THREADS_LIMIT:            # 収まらなければ11位以下の羅列を頭数だけにする
        lines = [x for x in lines if not x.startswith("11位以下は")]
        idx = lines.index("") if "" in lines else len(lines)
        lines.insert(len(lines) - 3, f"（11〜{len(r['horses'])}位は省略）")
        body = "\n".join(lines)
    return body


from docx import Document
from docx.shared import Pt
doc = Document()
doc.styles["Normal"].font.size = Pt(10)
doc.add_heading(f"AI指数ランキング SNS投稿案 — {DATE}", 0)
doc.add_paragraph(J["stage"])
nban = 0
for r in J["races"]:
    doc.add_heading(f"{r['race']}（{r['venue']} {r['course']}）", 1)
    x, t = x_post(r), threads_post(r)
    for lab, p, lim in (("X（1投稿）", x, None), ("Threads（1投稿）", t, THREADS_LIMIT)):
        ok = "" if lim is None else ("OK" if len(p) <= lim else "⚠超過")
        doc.add_heading(f"{lab}　{len(p)}字 {ok}", 2)
        doc.add_paragraph(p)
        hits = [b for b in BAN if b in p]
        if hits:
            print(f"  ⚠ {r['race']} {lab}: 禁止語 {hits}")
            nban += len(hits)
    print(f"■ {r['race']}: X {len(x)}字 ／ Threads {len(t)}字 "
          f"{'（500字以内）' if len(t) <= THREADS_LIMIT else '（⚠超過）'}")

out = D / f"{a.dir}_AI指数ランキング_SNS投稿案.docx"
try:
    doc.save(out)
except PermissionError:
    out = D / f"{a.dir}_AI指数ランキング_SNS投稿案_new.docx"
    doc.save(out)
print(f"禁止語検出 {nban}件 ／ 保存: {out}")
