# -*- coding: utf-8 -*-
"""
oikiri_factor.py — sc[9]（調教）を2ソースの平均点で出す（2026-09-25・ユーザー承認）
====================================================================================
ルール（SKILL.md「sc[9]調教の定量化」と同じ）:
  ・S=9 / A=8 / B=7 / C以下=6 点
  ・**sc[9]は2ソースの平均**（片方しか無ければその値、どちらも無ければ既定6.5）
  ・**追い切りによる印の昇格は「両ソースともS/A」のときだけ**
Why: スプリンターズS2026の15頭で うましる×競馬チャンネル の完全一致は3/15（20%）、
     平均0.93段階のズレ。単独ソースのS/Aを昇格根拠にはできない。

使い方:
  from oikiri_factor import load_oikiri
  f = load_oikiri("20260927", "中山", 11)
  f.point("スターアニス")     -> 9.0（2ソース平均）
  f.can_promote("スターアニス") -> True（両ソースS/A）
  f.detail("スターアニス")     -> "umasiru S / keibachannel S"
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

STORE = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "oikiri.json"
GRADE_PT = {"S": 9.0, "A": 8.0, "B": 7.0, "C": 6.0, "D": 5.0, "E": 4.0}
NEUTRAL = 6.5   # 評価が無い馬（重賞以外など）


class Oikiri:
    def __init__(self, rows: list[dict]):
        self.by_horse: dict[str, dict[str, str]] = defaultdict(dict)
        for r in rows:
            self.by_horse[r["馬名"]][r.get("source", "umasiru")] = r["評価"]

    def point(self, name: str) -> float:
        gs = self.by_horse.get(name)
        if not gs:
            return NEUTRAL
        pts = [GRADE_PT.get(g, NEUTRAL) for g in gs.values()]
        return round(sum(pts) / len(pts), 2)

    def can_promote(self, name: str) -> bool:
        """印1段昇格の可否。2ソース以上あり、すべてS/Aのときだけ True。"""
        gs = self.by_horse.get(name, {})
        return len(gs) >= 2 and all(g in ("S", "A") for g in gs.values())

    def detail(self, name: str) -> str:
        gs = self.by_horse.get(name, {})
        return " / ".join(f"{k} {v}" for k, v in sorted(gs.items())) or "評価なし"

    def sources(self, name: str) -> int:
        return len(self.by_horse.get(name, {}))


def load_oikiri(date: str, venue: str, r: int) -> Oikiri:
    rows = json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []
    return Oikiri([x for x in rows if x["date"] == date and x["venue"] == venue and int(x["R"]) == int(r)])


if __name__ == "__main__":
    import sys, io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    d, v, r = (sys.argv[1:4] + ["20260927", "中山", "11"][len(sys.argv) - 1:])[:3]
    f = load_oikiri(d, v, int(r))
    print(f"■ {d} {v}{r}R の追い切り（sc[9]は2ソース平均・昇格は両ソースS/Aのみ）")
    for name in sorted(f.by_horse, key=lambda n: -f.point(n)):
        mark = " ★昇格可" if f.can_promote(name) else ""
        print(f"  {name:<14} {f.point(name):>5}点  [{f.detail(name)}]{mark}")
