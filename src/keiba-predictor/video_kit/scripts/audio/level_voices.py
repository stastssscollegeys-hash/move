# -*- coding: utf-8 -*-
"""level_voices.py — 場面ごとの声の大きさをそろえる（2026-11-20。合いの手ありの動画で、聞き役の声が解説役より約6dB小さく「かき消される」とユーザー指摘）
素の声（_raw）を読み、速さ（atempo）をかけ、平均の大きさを target dB にそろえて audio/ に書く。大きくしすぎて割れないようリミッターをかける。
聞き役（voices.json の role＝kikite）は、BGM・効果音に埋もれやすいので、さらに +kikite dB する。
使い方: python scripts/audio/level_voices.py <script.json> [--tempo 1.4] [--target -15] [--kikite 1.5] [--src _raw] [--dst audio]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

def mean_db(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r)
    return float(m.group(1)) if m else None

ap = argparse.ArgumentParser()
ap.add_argument("script"); ap.add_argument("--tempo", type=float, default=1.0); ap.add_argument("--target", type=float, default=-15.0)
ap.add_argument("--kikite", type=float, default=1.5); ap.add_argument("--src", default="_raw"); ap.add_argument("--dst", default="audio")
a = ap.parse_args()
sp = Path(a.script).resolve(); S = json.load(open(sp, encoding="utf-8"))
tag = sp.name.replace("script_", "").replace(".json", "")
vj = Path(__file__).resolve().parents[2] / "templates" / "voices.json"
spk = json.load(open(vj, encoding="utf-8"))["speakers"]; spk.update(S.get("speakers", {}))
src, dst = sp.parent / a.src, sp.parent / a.dst; dst.mkdir(exist_ok=True)
for s in S["scenes"]:
    f = f"{tag}_{s['id']:02d}.wav"; who = s.get("speaker") or "narrator"
    m = mean_db(src / f)
    if m is None: sys.exit(f"測れません: {f}")
    gain = a.target - m + (a.kikite if spk.get(who, {}).get("role") == "kikite" else 0.0)
    af = (f"atempo={a.tempo}," if a.tempo != 1.0 else "") + f"volume={gain:.1f}dB,alimiter=limit=0.93:level=disabled"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src / f), "-af", af, "-ar", "24000", "-ac", "1", str(dst / f)], check=True)
    print(f"  {f} {who:<9} {m:6.1f}dB → {mean_db(dst / f):6.1f}dB（{gain:+.1f}dB）")
