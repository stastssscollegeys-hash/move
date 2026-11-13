# -*- coding: utf-8 -*-
"""build_video.py の最後の合成（字幕の焼き込み）を区間に分けて行う（2026-11-13）。
1回の実行が10分を超えないように、映像を SEG 秒ずつ書き出して最後につなぎ、音声は全体を1回で重ねる。
エンコード設定は build_video.py の最後の合成と同じ（libx264 medium crf20・aac 192k 48kHz 2ch）。build_video.py が作った _tmp の
{tag}_video.mp4・{tag}_audio.wav・{tag}.ass を使う（先に BV_RESUME=1 で build_video.py を回して作っておく）。
使い方: python final_mux_split.py <script.json> seg <番号>   … 区間を1つ書き出す（0から）
        python final_mux_split.py <script.json> join          … つないで {tag}_long.mp4 を作る"""
import json, subprocess, sys
from pathlib import Path
SEG = 180.0
sp = Path(sys.argv[1]); base = sp.parent; tmp = base / "_tmp"
tag = sp.name.replace("script_", "").replace(".json", "")
S = json.loads(sp.read_text(encoding="utf-8")); suffix = S.get("out_suffix", "long")
silent, audio, ass = tmp / f"{tag}_video.mp4", tmp / f"{tag}_audio.wav", tmp / f"{tag}.ass"
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(silent)], capture_output=True, text=True).stdout)
n = int(dur // SEG) + (1 if dur % SEG > 0.01 else 0)
ap = str(ass).replace("\\", "/").replace(":", "\\:")
if sys.argv[2] == "seg":
    i = int(sys.argv[3]); s = i * SEG; t = min(SEG, dur - s)
    out = tmp / f"{tag}_seg{i:02d}.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-threads", "1", "-ss", f"{s:.3f}", "-t", f"{t:.3f}", "-i", str(silent),
                        "-vf", f"setpts=PTS+{s:.3f}/TB,ass='{ap}',setpts=PTS-STARTPTS", "-c:v", "libx264", "-threads", "2",
                        "-x264-params", "rc-lookahead=10", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-an", str(out)],
                       capture_output=True)
    if r.returncode: print(r.stderr.decode("utf-8", "replace")[-800:]); sys.exit("区間の書き出しに失敗")
    print(f"区間 {i + 1}/{n}  {s:.0f}〜{s + t:.0f}秒  → {out.name}")
elif sys.argv[2] == "join":
    segs = [tmp / f"{tag}_seg{i:02d}.mp4" for i in range(n)]
    miss = [p.name for p in segs if not p.exists()]
    if miss: sys.exit(f"区間が足りない: {miss}")
    lst = tmp / f"{tag}_segs.txt"; lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segs), encoding="utf-8")
    out = base / f"{tag}_{suffix}.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", str(out)], capture_output=True)
    if r.returncode: print(r.stderr.decode("utf-8", "replace")[-800:]); sys.exit("結合に失敗")
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(out)], capture_output=True, text=True).stdout.strip()
    print(f"✅ 完成: {out}  {float(d):.1f}秒（映像 {dur:.1f}秒）／{out.stat().st_size / 1024 / 1024:.1f}MB")
print(f"区間の数: {n}")
