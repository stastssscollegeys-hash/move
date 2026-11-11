# -*- coding: utf-8 -*-
"""
build_video.py — 競馬動画（縦ショート／横の長尺）を組み立てる（2026-11-06 新規・build_short.py の一般化）
================================================================================
build_short.py（ベースライン）は変えず、解像度・画像フォルダ・字幕の大きさ・出力名を script の "canvas" で変えられるようにした版。
入力: script_*.json（scenes[].image / sec / zoom / subtitle）＋ audio/{tag}_NN.wav（シーンごとのナレーション）
  "image_dir": 画像フォルダ（script.json からの相対パス）
  "out_suffix": 出力名の末尾（{tag}_{suffix}.mp4）。既定 short
  "canvas": {w,h, fg_w,fg_h, y_off, zmax, font, hilite, margin_v, wrap}
     縦ショート既定: 1080x1920 / 前景1080x1651 / 字幕68・黄色72 / 15字で改行
     横長尺の例  : 1920x1080 / 前景1920x1080 / 字幕46・黄色50 / 28字で改行
使い方: python build_video.py <script.json>   → 続けて add_bgm_se.py（同じ script を渡す）
"""
from __future__ import annotations
import json, os, subprocess, sys, wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
FPS = 30
FONT = "HGSoeiKakugothicUB"
PAD = 0.45        # 語尾の余白（add_bgm_se.py と同じ値）


def wav_sec(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()


def esc(s: str) -> str:
    s = s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return s.replace("<BR>", "\\N")


def build_ass(scenes, path: Path, c):
    W, H = c["w"], c["h"]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{FONT},{c['font']},&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{max(5, c['font'] // 8)},2,2,70,70,{c['margin_v']},1
Style: Hilite,{FONT},{c['hilite']},&H0000E5FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{max(5, c['font'] // 8)},2,2,70,70,{c['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(t):
        return f"{int(t // 3600):d}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

    lines, t0 = [], 0.0
    for sc in scenes:
        subs, dur = sc["subtitle"], sc["_sec"]
        each = dur / len(subs)
        for i, text in enumerate(subs):
            st, en = t0 + each * i, t0 + each * (i + 1)
            if len(text) > c["wrap"]:
                cut = len(text) // 2
                for d in range(0, 6):
                    for k in (cut - d, cut + d):
                        if 0 < k < len(text) and text[k] in "　 、。・／/＝=でがはをに":
                            cut = k + 1
                            break
                    else:
                        continue
                    break
                text = text[:cut].rstrip() + "<BR>" + text[cut:].lstrip()
            style = "Hilite" if i == len(subs) - 1 and len(subs) > 1 else "Main"
            lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},{style},,0,0,0,,{esc(text)}")
        t0 += dur
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    sp = Path(sys.argv[1])
    script = json.loads(sp.read_text(encoding="utf-8"))
    base = sp.parent
    c = dict(w=1080, h=1920, fg_w=1080, fg_h=1651, y_off=-86, zmax=1.06, font=68, hilite=72, margin_v=70, wrap=15)
    c.update(script.get("canvas", {}))
    W, H = c["w"], c["h"]
    img_dir = (base / script["image_dir"]).resolve() if "image_dir" in script else base.parent / "images"
    aud_dir, tmp = base / "audio", base / "_tmp"
    tmp.mkdir(exist_ok=True)
    tag = sp.name.replace("script_", "").replace(".json", "")
    suffix = script.get("out_suffix", "short")

    total = 0.0
    for sc in script["scenes"]:
        a = aud_dir / f"{tag}_{sc['id']:02d}.wav"
        sc["_sec"] = round(wav_sec(a) + PAD, 2) if a.exists() else float(sc["sec"])
        sc["_audio"] = a if a.exists() else None
        total += sc["_sec"]
    print(f"■ {script['race']}  {len(script['scenes'])}シーン / 合計 {total:.1f}秒（{total/60:.1f}分）  {W}x{H}")

    clips = []
    zin = f"min(zoom+0.0004,{c['zmax']})"
    zout = f"if(lte(zoom,1.0),{c['zmax']},max(1.0,zoom-0.0004))"
    for sc in script["scenes"]:
        src = img_dir / sc["image"]
        out = tmp / f"{tag}_{sc['id']:02d}.mp4"
        n = int(sc["_sec"] * FPS)
        if os.environ.get("BV_RESUME") and out.exists():     # 2026-11-07: メモリ不足で止まっても続きから（長さが合うクリップは作り直さない）
            d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
            if d and abs(float(d) - sc["_sec"]) < 0.2:
                clips.append(out); print(f"   既存 {out.name}"); continue
        fo = sc.get("focus")      # 2026-11-09: 説明している場所へ寄る／引く {"x":0〜1,"y":0〜1,"z":倍率} ＋ zoom=in/out
        if fo:
            zt = fo.get("z", 1.6)
            zexpr = f"1+({zt}-1)*min(on/{n * 0.7:.0f},1)" if sc["zoom"] != "out" else f"{zt}-({zt}-1)*min(on/{n * 0.7:.0f},1)"
            xy = f"x='max(0,min(iw-iw/zoom,{fo['x']}*iw-iw/zoom/2))':y='max(0,min(ih-ih/zoom,{fo['y']}*ih-ih/zoom/2))'"
        else:
            zexpr = zin if sc["zoom"] == "in" else zout if sc["zoom"] == "out" else "1"
            xy = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        z = f"zoompan=z='{zexpr}':d={n}:{xy}:s={c['fg_w']}x{c['fg_h']}:fps={FPS}"
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,eq=brightness=-0.16[bg];"
              f"[0:v]scale={c['fg_w']*2}:-1,{z}[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2+({c['y_off']})")
        for _try in range(4):          # 長尺（4K経由のzoompan）は不定期に落ちる（2026-11-07）→ 再試行
            r = subprocess.run(["ffmpeg", "-y", "-filter_threads", "1", "-i", str(src), "-filter_complex", vf, "-t", str(sc["_sec"]), "-r", str(FPS),
                                "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out)], capture_output=True)
            if not r.returncode:
                break
            print(f"   再試行 {_try + 1}: {src.name}")
        if r.returncode:
            print(r.stderr.decode("utf-8", "replace")[-900:]); sys.exit(f"クリップ生成に失敗: {src.name}")
        clips.append(out)
        print(f"   クリップ {out.name}")

    lst = tmp / f"{tag}_list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    silent = tmp / f"{tag}_video.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)], check=True, capture_output=True)

    parts = []
    for sc in script["scenes"]:
        pad = tmp / f"{tag}_a{sc['id']:02d}.wav"
        if sc["_audio"]:
            subprocess.run(["ffmpeg", "-y", "-i", str(sc["_audio"]), "-af", f"apad=whole_dur={sc['_sec']}", "-t", str(sc["_sec"]), str(pad)], check=True, capture_output=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(sc["_sec"]), "-c:a", "pcm_s16le", str(pad)], check=True, capture_output=True)
        parts.append(pad)
    alist = tmp / f"{tag}_audio.txt"
    alist.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    combined = tmp / f"{tag}_audio.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist), "-c", "copy", str(combined)], check=True, capture_output=True)

    ass = tmp / f"{tag}.ass"
    build_ass(script["scenes"], ass, c)
    out = base / f"{tag}_{suffix}.mp4"
    ap = str(ass).replace("\\", "/").replace(":", "\\:")
    # 2026-11-11: 長尺(11分)の最後の合成がメモリ不足で2回止まった（get_buffer() failed）→ デコード1スレッド・エンコード2スレッド・先読み10で省メモリ
    r = subprocess.run(["ffmpeg", "-y", "-threads", "1", "-i", str(silent), "-i", str(combined), "-vf", f"ass='{ap}'", "-c:v", "libx264",
                        "-threads", "2", "-x264-params", "rc-lookahead=10", "-preset", "medium", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", str(out)], capture_output=True)
    if r.returncode:
        print(r.stderr.decode("utf-8", "replace")[-1200:]); sys.exit("動画合成に失敗しました")
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(out)], capture_output=True, text=True).stdout.strip()
    print(f"\n✅ 完成: {out}\n   {float(dur):.1f}秒 / {out.stat().st_size/1024/1024:.1f}MB / {W}x{H} {FPS}fps")


if __name__ == "__main__":
    main()
