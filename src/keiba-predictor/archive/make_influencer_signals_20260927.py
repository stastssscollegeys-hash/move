# -*- coding: utf-8 -*-
"""
make_influencer_signals_20260927.py — influencer_final_summary.json を台帳形式に変換する
========================================================================================
influencer_ledger.py --add-week は `*_influencer.json`（{"race":…, "signals":[{source,horse,kind,confidence}]}）
を読む。2026-09-27のリサーチは influencer_final_summary.json という別形式で保存されていたため、
そのままでは台帳に入らず、動的重み（influencer_weight.py）の母数が増えない。

変換ルール（feedback_keiba_influencer_sources.md の数え方に従う）:
  honmei      → kind=honmei
  honmei_split→ kind=posi（番組内で複数人が別々の本命。本命に数えない）
  taikou      → kind=posi
  ana         → kind=ana
  keshi/nega  → kind=nega
  oikiri      → kind=oikiri1
使い方: python make_influencer_signals_20260927.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path.home() / "Desktop" / "競馬予想レポート" / "20260927" / "research"
src = json.loads((R / "influencer_final_summary.json").read_text(encoding="utf-8"))

MAP = [("honmei", "honmei"), ("honmei_split", "posi"), ("taikou", "posi"),
       ("ana", "ana"), ("keshi", "nega"), ("nega", "nega"), ("oikiri", "oikiri1")]

signals, per_kind = [], {}
for s in src.get("sources", []):
    name = s.get("name")
    if not name:
        continue
    for field, kind in MAP:
        for horse in s.get(field) or []:
            signals.append({"source": name, "horse": horse, "kind": kind, "confidence": "stated"})
            per_kind[kind] = per_kind.get(kind, 0) + 1

out = {"race": "スプリンターズS", "date": "2026-09-27",
       "note": "influencer_final_summary.json から機械変換（make_influencer_signals_20260927.py）",
       "counting_rule": src.get("counting_rule"), "signals": signals}
p = R / "sprinters_influencer.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"ソース {len(src.get('sources', []))}件 → シグナル {len(signals)}件")
print("  内訳:", ", ".join(f"{k}={v}" for k, v in sorted(per_kind.items())))
print("保存:", p)
