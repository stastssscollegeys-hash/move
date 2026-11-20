# -*- coding: utf-8 -*-
"""長尺の場面に合わせて曲を切り替えたBGMを1本にする（2026-11-15 ユーザー「長尺は場面に応じてBGMを切り替えてよい」）。
区間: 冒頭〜過去10年〜最新情報＝American Idle ／ 指数のつくり方〜穴の型＝Before I Go ／ ランキング＝All Hail the Queen ／ まとめ＝American Idle
各曲は同じ大きさ（-16LUFS）にそろえ、切り替えは1.5秒のクロスフェード。出力 _bgm_sections.mp3 → add_bgm_se.py に絶対パスで渡す"""
import json, subprocess, wave, re
from pathlib import Path
D = Path(__file__).resolve().parent
V2 = Path(__import__("os").environ.get("KVC_BGM_DIR", "assets/bgm"))
A, B, C = V2 / "American Idle - RKVC.mp3", V2 / "Before I Go - RKVC.mp3", V2 / "All Hail the Queen - Dan Lebowitz.mp3"
S = json.loads((D / "script_tospo_long.json").read_text(encoding="utf-8"))["scenes"]
def sec(i):
    w = wave.open(str(D / "audio" / f"tospo_long_{i:02d}.wav")); return w.getnframes() / w.getframerate() + 0.45
SONG = {**{f"T{n:02d}.png": A for n in (1, 2, 3, 4, 5, 16, 15)}, **{f"T{n:02d}.png": B for n in (6, 7, 9, 10, 17, 8, 11)}, **{f"T{n:02d}.png": C for n in (12, 13, 14)}}
segs, t = [], 0.0
for s in S:
    d = sec(s["id"]); song = SONG[s["image"]]
    if segs and segs[-1][0] == song: segs[-1][2] += d
    else: segs.append([song, t, d])
    t += d
XF = 1.5; parts = []
for k, (song, st, d) in enumerate(segs):
    o = D / "_tmp" / f"bgm_part{k}.wav"; need = d + (XF if k < len(segs) - 1 else 1.0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(song), "-t", f"{need:.2f}", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", str(o)], check=True)
    parts.append(o); print(f"{st/60:5.2f}分〜 {d:6.1f}秒  {song.name}")
cmd = ["ffmpeg", "-y", "-loglevel", "error"]; [cmd.extend(["-i", str(p)]) for p in parts]
fc, last = [], "[0:a]"
for k in range(1, len(parts)):
    fc.append(f"{last}[{k}:a]acrossfade=d={XF}:c1=tri:c2=tri[x{k}]"); last = f"[x{k}]"
cmd += ["-filter_complex", ";".join(fc), "-map", last, "-b:a", "192k", str(D / "_bgm_sections.mp3")]
subprocess.run(cmd, check=True); print("total", round(t, 1))
