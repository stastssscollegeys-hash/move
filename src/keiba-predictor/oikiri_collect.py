# -*- coding: utf-8 -*-
"""
oikiri_collect.py — 追い切り評価を2ソースから集めて突き合わせる（2026-09-25）
=============================================================================
背景: 追い切りによる印の昇格は「2ソース合議」が条件なのに、これまで うましる 1本しか無かった。
      競馬チャンネル（元トラックマン・中西友馬氏）の「全頭調教診断」最終ページに
      馬名×評価(S/A/B/C)の一覧表があり、無料・明記なのでスクレイプだけで2ソース目にできる。
      （2026-09-25の検証では、文章からの自動採点は重賞しか使えず、タイムのみは基準線割れだった）

使い方:
  1) node fetch_pages.mjs <urls.txt> <out.json>   ← うましると競馬チャンネル最終ページのURLを入れる
  2) python oikiri_collect.py <out.json>          ← 突き合わせ表を表示
     python oikiri_collect.py <out.json> --store 20260927 中山 11   ← oikiri.json に保存（source付き）
"""
from __future__ import annotations
import json, re, sys, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

STORE = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "oikiri.json"
Z2H = str.maketrans("ＳＡＢＣＤＥ", "SABCDE")
GRADE = {g: p for g, p in zip("SABCDE", (9.0, 8.0, 7.0, 6.0, 5.0, 4.0))}
UMASIRU = re.compile(r"^(?P<name>[ァ-ヴー]{3,12})\s+\d+月\d+日\(.\)\s+評価(?P<g>[ＳＡＢＣＤＥSABCDE])\s*$")
KC = re.compile(r"^(?P<name>[ァ-ヴー]{3,12})\s+(?P<g>[SABCDE])\s*$")


def parse(article: dict) -> tuple[str, dict]:
    """記事本文から {馬名: 評価} を取り出す。ソース名も返す。"""
    txt, url = article["text"], article["url"]
    if "umasiru" in url:
        return "umasiru", {m.group("name"): m.group("g").translate(Z2H)
                           for ln in txt.split("\n") if (m := UMASIRU.match(ln.strip()))}
    if "keibachannel" in url:
        out = {}
        for ln in txt.split("\n"):
            m = KC.match(ln.strip().replace("\t", " "))
            if m:
                out[m.group("name")] = m.group("g")
        return "keibachannel", out
    return url.split("/")[2], {}


def main():
    arts = [a for a in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if a.get("text")]
    srcs = {}
    for a in arts:
        name, d = parse(a)
        if d:
            srcs.setdefault(name, {}).update(d)
    if len(srcs) < 2:
        print("[WARN] 2ソース揃っていません:", {k: len(v) for k, v in srcs.items()})
    names = sorted({n for d in srcs.values() for n in d})
    keys = list(srcs)
    print(f"■ 追い切り評価の突き合わせ（{'／'.join(keys)}）")
    print(f"{'馬名':<14}" + "".join(f"{k[:10]:>12}" for k in keys) + "   合議")
    agree = both = 0
    rows = []
    for n in names:
        gs = [srcs[k].get(n) for k in keys]
        if all(gs):
            both += 1
            agree += len(set(gs)) == 1
        # 2ソース合議: 両方がS/Aなら昇格候補、片方でもC以下なら据え置き
        hi = all(g in ("S", "A") for g in gs if g)
        lo = any(g in ("C", "D", "E") for g in gs if g)
        verdict = "昇格候補" if (hi and all(gs)) else ("消し寄り" if lo else "")
        rows.append((n, gs, verdict))
        print(f"{n:<14}" + "".join(f"{(g or '—'):>12}" for g in gs) + f"   {verdict}")
    if both:
        print(f"\n2ソースが揃った{both}頭のうち完全一致 {agree}頭（{agree/both*100:.0f}%）")

    if "--store" in sys.argv:
        i = sys.argv.index("--store")
        date, venue, r = sys.argv[i + 1], sys.argv[i + 2], int(sys.argv[i + 3])
        db = json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []
        have = {(x["date"], x["venue"], x["R"], x["馬名"], x.get("source", "umasiru")) for x in db}
        added = 0
        for k in keys:
            for n, g in srcs[k].items():
                if (date, venue, r, n, k) in have:
                    continue
                db.append({"date": date, "venue": venue, "R": r, "馬名": n, "評価": g,
                           "点": GRADE[g], "source": k})
                added += 1
        STORE.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n追加 {added}件 → 累計 {len(db)}件（{STORE.name}）")


if __name__ == "__main__":
    main()
