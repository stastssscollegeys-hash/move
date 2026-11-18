# -*- coding: utf-8 -*-
"""作り直しの音声（数場面を2秒の間で区切って1本にしたもの）を、長い無音の上位 n-1 か所で切って場面の音声に差し替える。使い方: python fx_split.py <グループ番号>"""
import json, re, subprocess, sys
from pathlib import Path
D = Path(__file__).resolve().parent; k = int(sys.argv[1]); G = json.load(open(D / "_fx_groups.json"))[k - 1]
src = D / "_muse" / f"fx_g{k}.mp3"
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", "silencedetect=noise=-35dB:d=0.8", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", log).group(3)) + 60 * int(re.search(r"Duration: (\d+):(\d+)", log).group(2))
sil = [(a, b) for a, b in zip(st, en) if a > 0.3 and b < dur - 0.3]
sil = sorted(sorted(sil, key=lambda x: x[0] - x[1])[: len(G) - 1])
assert len(sil) == len(G) - 1, (len(sil), len(G))
cuts = [0.0] + [(a + b) / 2 for a, b in sil] + [dur]
TR = "silenceremove=start_periods=1:start_threshold=-40dB,areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse"
for (kind, i), a, b in zip(G, cuts, cuts[1:]):
    out = (D.parent / "shorts" / "_raw" / f"tospo_{i:02d}.wav") if kind == "s" else (D / "_raw" / f"tospo_long_{i:02d}.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src), "-af", TR, "-ar", "24000", "-ac", "1", str(out)], check=True)
    print(kind, i, f"{b - a:.1f}s")
