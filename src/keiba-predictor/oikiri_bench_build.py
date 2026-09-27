# -*- coding: utf-8 -*-
"""
oikiri_bench_build.py — 追い切り評価の自動採点ベンチマーク用データを作る（2026-09-25）
=====================================================================================
目的: 手作業で貯めた追い切り評価（oikiri.json・57頭）を正解として、
      「コメント文だけを読んでS〜Eを当てられるか」を測れる形にする。
      当てられるなら、重賞以外にも評価を広げて sc[9] の蓄積を加速できる（今は1サイト・重賞のみ）。

入力: うましるの全頭診断記事の本文（fetch_pages.mjs で取得したJSON）
出力: research/oikiri_bench.json  [{race, 馬名, grade_true, text}]
      ※ text からは「評価Ｓ」等の表記を必ず除く（正解が混ざると検証にならない）
"""
from __future__ import annotations
import json, re, sys, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT = Path.home() / "Desktop" / "競馬予想レポート" / "20260920" / "research" / "oikiri_bench.json"
Z2H = str.maketrans("ＳＡＢＣＤＥ", "SABCDE")
HEAD = re.compile(r"^(?P<name>[ァ-ヴー]{3,12})\s+\d+月\d+日\(.\)\s+評価(?P<g>[ＳＡＢＣＤＥSABCDE])\s*$")


def parse(article: str) -> list[dict]:
    lines = article.split("\n")
    heads = [(i, m.group("name"), m.group("g").translate(Z2H))
             for i, ln in enumerate(lines) if (m := HEAD.match(ln.strip()))]
    out = []
    for k, (i, name, g) in enumerate(heads):
        end = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines)
        body = "\n".join(lines[i + 1:end]).strip()
        body = re.sub(r"評価[ＳＡＢＣＤＥSABCDE]", "", body)          # 正解の混入を防ぐ
        body = re.sub(r"PR .*?当たる無料予想を見る！", "", body, flags=re.S)  # 広告
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if len(body) > 150:
            out.append({"馬名": name, "grade_true": g, "text": body})
    return out


def main():
    src = Path(sys.argv[1])
    arts = [a for a in json.loads(src.read_text(encoding="utf-8")) if a.get("text")]
    # 同じ馬が別の週にも出ているので、レース（日付・場・R）まで込みで突き合わせる
    RACE_KEY = {"チャレンジC": ("20260912", "阪神", 11), "セントライト記念": ("20260913", "中山", 11),
                "ローズS": ("20260913", "阪神", 11), "オールカマー": ("20260920", "中山", 11)}
    truth = {(r["date"], r["venue"], r["R"], r["馬名"]): r["評価"] for r in json.loads(
        (Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "oikiri.json").read_text(encoding="utf-8"))}
    rows, mismatch = [], 0
    for a in arts:
        race = a["title"].split("2026")[0].lstrip("【")
        for r in parse(a["text"]):
            r["race"] = race
            key = RACE_KEY.get(race)
            k = (key[0], key[1], key[2], r["馬名"]) if key else None
            if k and k in truth and truth[k] != r["grade_true"]:
                mismatch += 1
                print(f"[差異] {race} {r['馬名']} 台帳={truth[k]} 記事={r['grade_true']}")
            r["in_ledger"] = bool(k and k in truth)
            rows.append(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"{len(rows)}頭 / 台帳と突き合わせ: 一致{len([r for r in rows if r['in_ledger']]) - mismatch}・差異{mismatch}")
    print("正解の分布:", dict(Counter(r["grade_true"] for r in rows)))
    print("平均文字数:", sum(len(r["text"]) for r in rows) // max(1, len(rows)))
    print("保存:", OUT)


if __name__ == "__main__":
    main()
