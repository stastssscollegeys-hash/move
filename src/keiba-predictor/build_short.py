# -*- coding: utf-8 -*-
"""
build_short.py — 競馬のYouTubeショート動画を組み立てる（2026-09-28新規）
================================================================================
入力: shorts/script_*.json（scenes[].image / sec / zoom / subtitle）＋ shorts/audio/*.wav
出力: shorts/{race}_short.mp4（1080x1920・30fps・H.264/AAC）

作り: 既存の注目馬インフォグラフィック（9:16）をそのまま素材に使い、
      ・Ken Burns（ゆっくりズームイン/アウト）で静止画に動きを付ける
      ・ナレーション音声の実長に合わせてシーン尺を決める（台本のsecは目安）
      ・字幕はASSで焼き込む（下部中央・白文字＋極太黒縁、SNSで読める大きさ）
ffmpegだけで完結する（Remotion不要）。

使い方: python build_short.py <script.json>
"""
from __future__ import annotations
import json, re, shutil, subprocess, sys, wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
W, H, FPS = 1080, 1920, 30
FONT = "HGSoeiKakugothicUB"          # 確定スタイル（project_preview_short_style）
IMG_DIR_NAME = "images"


def wav_sec(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()


def ass_escape(s: str) -> str:
    # ASSの制御文字を無害化してから、目印の <BR> だけを改行コマンド(\N)に戻す。
    # 先にエスケープしないと、こちらで入れた改行までバックスラッシュが二重化されてしまう。
    s = s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return s.replace("<BR>", "\\N")


def build_ass(scenes, path: Path):
    """下部中央の字幕。1シーンに複数行ある場合は行数で等分して順に出す"""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{FONT},68,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,9,3,2,70,70,70,1
Style: Hilite,{FONT},72,&H0000E5FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,9,3,2,70,70,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def ts(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f"{h:d}:{m:02d}:{s:05.2f}"

    lines, t0 = [], 0.0
    for sc in scenes:
        subs = sc["subtitle"]
        dur = sc["_sec"]
        each = dur / len(subs)
        for i, text in enumerate(subs):
            st, en = t0 + each * i, t0 + each * (i + 1)
            if len(text) > 15:          # 画面幅に収まらない行は中央付近で2行に割る
                cut = len(text) // 2
                for d in range(0, 6):   # 区切りやすい位置（記号・助詞）を探す
                    for c in (cut - d, cut + d):
                        if 0 < c < len(text) and text[c] in "　 、。・／/＝=でがはをに":
                            cut = c + 1
                            break
                    else:
                        continue
                    break
                text = text[:cut].rstrip() + "<BR>" + text[cut:].lstrip()
            # 最後の行（結論・数字）だけ黄色で強調する
            style = "Hilite" if i == len(subs) - 1 and len(subs) > 1 else "Main"
            lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},{style},,0,0,0,,{ass_escape(text)}")
        t0 += dur
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    sp = Path(sys.argv[1])
    script = json.loads(sp.read_text(encoding="utf-8"))
    base = sp.parent
    img_dir = base.parent / IMG_DIR_NAME
    aud_dir = base / "audio"
    tmp = base / "_tmp"
    tmp.mkdir(exist_ok=True)
    tag = sp.name.replace("script_", "").replace(".json", "")

    # ── 各シーンの実尺 = ナレーション音声長 + 余白 ────────────────────
    total = 0.0
    for sc in script["scenes"]:
        a = aud_dir / f"{tag}_{sc['id']:02d}.wav"
        if not a.exists():
            print(f"[WARN] 音声が無い: {a.name} → 台本の秒数を使う")
            sc["_sec"] = float(sc["sec"])
        else:
            sc["_sec"] = round(wav_sec(a) + 0.45, 2)      # 語尾の余白
        sc["_audio"] = a if a.exists() else None
        total += sc["_sec"]
    print(f"■ {script['race']}  {len(script['scenes'])}シーン / 合計 {total:.1f}秒")
    for sc in script["scenes"]:
        print(f"   [{sc['id']}] {sc['_sec']:>5.2f}秒  {sc['image']}")

    # ── シーンごとに Ken Burns 付きの無音クリップを作る ────────────────
    clips = []
    for sc in script["scenes"]:
        src = img_dir / sc["image"]
        out = tmp / f"{tag}_{sc['id']:02d}.mp4"
        n = int(sc["_sec"] * FPS)
        # zoompanは入力を大きくしてからズームするとジャギが出にくい
        # 元画像は四隅まで文字があるので、拡大すると端が切れる。
        # 画面いっぱいに収めた(contain)うえで、ズームは1.06倍までに抑える。
        # 下部は字幕帯が重なるので、画像をやや上寄せ(y=H*0.40)にして文字の重なりを避ける。
        if sc["zoom"] == "in":
            zexpr = "min(zoom+0.0004,1.06)"
        elif sc["zoom"] == "out":
            zexpr = "if(lte(zoom,1.0),1.06,max(1.0,zoom-0.0004))"
        else:
            zexpr = "1"
        z = (f"zoompan=z='{zexpr}':d={n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
             f":s={W}x{int(H*0.86)}:fps={FPS}")
        # 背景はぼかし拡大した同じ画像（黒帯より見栄えがいい）
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"boxblur=28:2,eq=brightness=-0.16[bg];"
              f"[0:v]scale={W*2}:-1,{z}[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2-{int(H*0.045)}")
        r = subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(src),
                            "-filter_complex", vf,
                            "-t", str(sc["_sec"]), "-r", str(FPS), "-pix_fmt", "yuv420p",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out)],
                           capture_output=True)
        if r.returncode != 0:
            print(r.stderr.decode("utf-8", "replace")[-900:])
            sys.exit(f"クリップ生成に失敗: {src.name}")
        clips.append(out)
        print(f"   クリップ {out.name}")

    # ── 連結 → 音声を重ねる → 字幕を焼く ──────────────────────────────
    lst = tmp / f"{tag}_list.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    silent = tmp / f"{tag}_video.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(silent)], check=True, capture_output=True)

    auds = [sc["_audio"] for sc in script["scenes"] if sc["_audio"]]
    if auds:
        alist = tmp / f"{tag}_audio.txt"
        alist.write_text("".join(f"file '{a.as_posix()}'\n" for a in auds), encoding="utf-8")
        combined = tmp / f"{tag}_audio.wav"
        # シーンごとの余白ぶんを無音で足してから連結すると映像とズレない
        parts = []
        for i, sc in enumerate(script["scenes"]):
            pad = tmp / f"{tag}_a{sc['id']:02d}.wav"
            if sc["_audio"]:
                subprocess.run(["ffmpeg", "-y", "-i", str(sc["_audio"]), "-af",
                                f"apad=whole_dur={sc['_sec']}", "-t", str(sc["_sec"]), str(pad)],
                               check=True, capture_output=True)
            else:
                # ナレーションが無いシーン（CTAカード等）は同じ長さの無音を挟む。
                # ここを飛ばすと以降の音声が前倒しになって映像とズレる。
                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                                "anullsrc=r=24000:cl=mono", "-t", str(sc["_sec"]),
                                "-c:a", "pcm_s16le", str(pad)],
                               check=True, capture_output=True)
            parts.append(pad)
        alist.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist),
                        "-c", "copy", str(combined)], check=True, capture_output=True)
    else:
        combined = None

    ass = tmp / f"{tag}.ass"
    build_ass(script["scenes"], ass)
    out = base / f"{tag}_short.mp4"
    cmd = ["ffmpeg", "-y", "-i", str(silent)]
    if combined:
        cmd += ["-i", str(combined)]
    # Windowsのパスは ass フィルタでエスケープが要る
    ap = str(ass).replace("\\", "/").replace(":", "\\:")
    cmd += ["-vf", f"ass='{ap}'", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", str(FPS)]
    if combined:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest"]
    cmd += [str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(r.stderr.decode("utf-8", "replace")[-1200:])
        sys.exit("動画合成に失敗しました")

    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(out)], capture_output=True, text=True).stdout.strip()
    mb = out.stat().st_size / 1024 / 1024
    print(f"\n✅ 完成: {out}\n   {float(dur):.1f}秒 / {mb:.1f}MB / {W}x{H} {FPS}fps")


if __name__ == "__main__":
    main()
