# -*- coding: utf-8 -*-
"""トラックコード（JV-Link・smartrc の track・JV-Data のコード表）から、courses.json のコースの名前を決める（2026-11-20）
  例: 京都 + 18（芝・右・外回り）→ 京都_芝外 ／ 京都 + 17（芝・右）→ 京都_芝 ／ 東京 + 23（ダート・左）→ 東京_ダート
  外回り＝12（芝・左・外）・16（芝・左・外2周）・18（芝・右・外）・22（芝・右・外2周）・13／19（内→外＝ゴールは外回り）
  10（芝・直線）＝新潟の直線1000m（周回のコースが無い）。29（ダート・直線）も同じ
確かめた例（JV-Link の races.jsonl）：京都 18 の 3000m・3200m（菊花賞・天皇賞（春））／新潟 12 の 1600m・1800m／中山 18 の 1200m・1600m
"""

OUTER = {"12", "13", "16", "18", "19", "22"}
STRAIGHT = {"10", "29"}


def course_key(venue: str, track_cd) -> str:
    t = str(track_cd or "").strip().zfill(2)
    if t in STRAIGHT:
        return f"{venue}_直線"
    turf = t.startswith("1") or t in {"20", "21", "22"}
    if not turf:
        return f"{venue}_ダート"
    return f"{venue}_芝外" if t in OUTER else f"{venue}_芝"
