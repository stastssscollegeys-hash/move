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
FONT = os.environ.get("KVC_FONT") or ("Hiragino Sans" if sys.platform == "darwin" else "HGSoeiKakugothicUB")   # 2026-11-19 Mac には HG創英角ゴシックUB が無い（字幕の字は KVC_FONT で変えられる）
PAD = 0.45        # 語尾の余白（add_bgm_se.py と同じ値）


def wav_sec(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()


def speech_ranges(p: Path, fps: int = FPS, peak_ratio=0.12, abs_floor=0.015, close_gap=3, min_open=2) -> list:
    """口パク用：wav の波形から「声が出ている時間」を秒で返す（2026-11-19。rich-explain-video-ss の lib/speech-envelope.js と同じ決まり）
    動画の1コマ幅で音の強さ（RMS）を測り、そのファイルの一番強い所の12%（かつ -36dB）未満は無音。3コマ以下の切れ目は埋め、2コマ未満の声は捨てる
    → 句読点の間・文末では口が閉じる"""
    import array
    with wave.open(str(p), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        return [(0.0, n / sr)]
    a = array.array("h", raw)
    if ch > 1:
        a = a[::ch]
    per = sr / fps
    rms = []
    for f in range(int(len(a) / per) + 1):
        seg = a[int(f * per):int((f + 1) * per)]
        rms.append((sum(v * v for v in seg) / len(seg)) ** 0.5 / 32768 if len(seg) else 0.0)
    thr = max(abs_floor, max(rms or [0]) * peak_ratio)
    on = [v >= thr for v in rms]
    i = 0
    while i < len(on):                       # 短い無音を埋める
        if on[i]:
            i += 1; continue
        j = i
        while j < len(on) and not on[j]:
            j += 1
        if i > 0 and j < len(on) and j - i <= close_gap:
            on[i:j] = [True] * (j - i)
        i = j
    out, i = [], 0
    while i < len(on):                       # 区間にする（短すぎる声は捨てる）
        if not on[i]:
            i += 1; continue
        j = i
        while j < len(on) and on[j]:
            j += 1
        if j - i >= min_open:
            out.append((i / fps, j / fps))
        i = j
    return out


def esc(s: str) -> str:
    s = s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return s.replace("<BR>", "\\N")


def wrap_sub(text: str, wrap: int) -> list:
    """字幕の1つを、画面に出る行に分ける（build_ass の折り返しと同じ決まり。2026-11-19 アイコンの位置を合わせるために共通にした）"""
    if len(text) <= wrap:
        return [text]
    cut = len(text) // 2
    for d in range(0, 6):
        for k in (cut - d, cut + d):
            if 0 < k < len(text) and text[k] in "　 、。・／/＝=でがはをに":
                return [text[:k + 1].rstrip(), text[k + 1:].lstrip()]
    return [text[:cut].rstrip(), text[cut:].lstrip()]


def text_w(s: str) -> float:
    """字幕1行の幅（文字の大きさを1とした目安）。全角＝1・半角＝0.55"""
    return sum(0.55 if ord(ch) < 0x2E80 else 1.0 for ch in s)


def build_ass(scenes, path: Path, c):
    W, H = c["w"], c["h"]
    al, ml = (1, c["_beside"]) if c.get("_beside") else (2, 70)   # 2026-11-19 横長の対話＝字幕を左寄せにして、左に話し手のアイコン
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{FONT},{c['font']},&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{max(5, c['font'] // 8)},2,{al},{ml},70,{c['margin_v']},1
Style: Hilite,{FONT},{c['hilite']},&H0000E5FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{max(5, c['font'] // 8)},2,{al},{ml},70,{c['margin_v']},1
Style: Kikite,{FONT},{c['font']},{c.get('_kikite_color', '&H00C88CFF')},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{max(5, c['font'] // 8)},2,{al},{ml},70,{c['margin_v']},1
Style: IconName,{FONT},{int(c['font'] * 0.55)},&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{max(3, c['font'] // 12)},1,8,0,0,0,1
Style: KikiteName,{FONT},{int(c['font'] * 0.62)},&H00FFFFFF,&H006E3CE6,&H00000000,-1,0,0,0,100,100,0,0,3,{max(4, c['font'] // 10)},0,2,70,70,{c['margin_v'] + int(c['font'] * 1.75)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(t):
        return f"{int(t // 3600):d}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

    lines, t0 = [], 0.0
    total = sum(sc["_sec"] for sc in scenes)
    for k, x, y, nm in c.get("_icons", []):     # 対話モードの丸アイコンの下の名前（全編）
        if nm:
            lines.append(f"Dialogue: 2,{ts(0)},{ts(total)},IconName,,0,0,0,,{{\\an8\\pos({x},{y + 4})}}{esc(nm)}")
    for sc in scenes:
        subs, dur = sc["subtitle"], sc["_sec"]
        each = dur / len(subs)
        # 2026-11-19 対話モード: 聞き役（voices.json の role＝kikite）の場面は、字幕を聞き役の色にする。アイコンが無いときは上に名前の札
        kikite = (sc.get("speaker") or "narrator") in c.get("_kikite", ())
        label = c.get("_labels", {}).get(sc.get("speaker") or "narrator", "")
        if kikite and label and not c.get("_icons") and not c.get("_beside") and not c.get("_corner"):
            lines.append(f"Dialogue: 1,{ts(t0)},{ts(t0 + dur)},KikiteName,,0,0,0,,{esc(' ' + label + ' ')}")
        for i, text in enumerate(subs):
            st, en = t0 + each * i, t0 + each * (i + 1)
            text = "<BR>".join(wrap_sub(text, c["wrap"]))
            style = "Kikite" if kikite else ("Hilite" if i == len(subs) - 1 and len(subs) > 1 else "Main")
            lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},{style},,0,0,0,,{esc(text)}")
        t0 += dur
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    sp = Path(sys.argv[1]).resolve()   # 2026-11-19: 相対パスで呼ぶと、つなぎ（concat）のリストの中の場所がずれて止まった
    script = json.loads(sp.read_text(encoding="utf-8"))
    base = sp.parent
    c = dict(w=1080, h=1920, fg_w=1080, fg_h=1651, y_off=-86, zmax=1.06, font=68, hilite=72, margin_v=70, wrap=15)
    c.update(script.get("canvas", {}))
    # 話し手の名前の札（templates/voices.json の label。台本の "speakers" で上書き可）。名前の札は聞き役だけ（アイコンが無いとき）
    vj = Path(__file__).resolve().parents[2] / "templates" / "voices.json"
    spk = json.loads(vj.read_text(encoding="utf-8"))["speakers"] if vj.exists() else {}
    spk.update(script.get("speakers", {}))
    c["_labels"] = {k: v.get("label", "") for k, v in spk.items()}
    c["_kikite"] = tuple(k for k, v in spk.items() if v.get("role") == "kikite")
    main_spk = next((k for k, v in spk.items() if v.get("role") == "kaisetsu"), "narrator")   # speaker の無い場面で光らせる解説役
    col = next((v.get("subtitle_color") for v in spk.values() if v.get("role") == "kikite" and v.get("subtitle_color")), None)
    if col:
        r, g, b = (int(col.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        c["_kikite_color"] = f"&H00{b:02X}{g:02X}{r:02X}"
    W, H = c["w"], c["h"]
    # 2026-11-19 対話モードの丸アイコン（taidan-movie-creator-ss の見せ方）：voices.json の "icon"（_on.png／_off.png の頭の名前）と "side"（left／right）を持つ話し手
    # 台本に話し手（narrator 以外）が1つでもあれば、全場面に左右のアイコンを出し、その場面の話し手を光らせる。話し手の無い場面は解説役（role＝kaisetsu）を光らせる
    root = vj.parents[1]
    icons = [(k, v["side"], root / f"{v['icon']}_on.png", root / f"{v['icon']}_off.png", v.get("name", v.get("label", "")))
             for k, v in spk.items() if v.get("icon") and v.get("side")]
    icons = [x for x in icons if x[2].exists() and x[3].exists()]
    dialogue = any((s.get("speaker") or "narrator") != "narrator" for s in script["scenes"]) and len(icons) >= 2
    # 既定＝"corner"（2026-11-19 ユーザー・参考 https://youtu.be/KwEuGnJ_1kI 「配置のイメージ自体はこんな感じ」「説明してる側…を右側に、反応する側を左側に」）
    #   2人の丸アイコンを画面の下の左右の角に固定（voices.json の side）。字幕は真ん中。話している方＝光る＋口パク、話していない方＝少し暗い
    #   ショートは右下の角に YouTube のボタン（いいね・コメント）が縦に並ぶので、アイコンを字幕の1段上に置き、右のアイコンはボタンの列より内側に寄せる
    # "beside"＝話している方だけ字幕のすぐ左（行ごとに動く・ユーザー「ポンポン動くのが結構嫌」で既定から外した）／"sides"＝横長は左右の余白・ショートは上の帯
    mode = script.get("icon_mode", "corner")
    corner = dialogue and mode == "corner"
    beside = dialogue and mode == "beside"
    dialogue_sides = dialogue and mode == "sides"
    isz = int(script.get("icon_size", round(W * (0.0875 if W > H else 0.16))))      # 光の分も入れた大きさ（横長 168px・縦 173px）
    if corner:
        isz = int(script.get("icon_size", round(H * 0.25 if W > H else W * 0.21)))   # 光の分も入れて 横長 270px・縦 227px（顔はその2/3）
        gap = int(isz * 0.06)
        if W > H:
            side_x = {"left": gap, "right": W - gap - isz}
            icon_y = H - isz + int(isz * 0.06)                                     # 光の余白ぶん、少しはみ出させて角に寄せる
        else:
            side_x = {"left": int(W * 0.03), "right": W - isz - int(W * 0.13)}    # 右はボタンの列（右端から約140px）より内側
            icon_y = int(H - c["margin_v"] - 2 * c["hilite"] * 1.25 - isz * 0.92)  # 字幕2行分の上（行数が変わっても動かない）
        c["_corner"] = True
    elif beside:
        isz = int(script.get("icon_size", round(min(W, H) * 0.14)))                 # 光の分も入れて 151px
        if H > W and "canvas" not in script:
            c["wrap"] = min(c["wrap"], 12)                                        # 縦は1行を短くして、アイコンの場所をあける
        side_x, icon_y = {"left": 0, "right": 0}, 0
    elif W > H:   # 横長：左右のぼかした余白の真ん中・上下は 42% の高さ
        side_x = {"left": (W - c["fg_w"]) // 4 - isz // 2, "right": W - (W - c["fg_w"]) // 4 - isz // 2}
        icon_y = int(H * 0.42) - isz // 2
    else:       # 縦（ショート）：画像に空きが無く、右下はショートの「いいね」ボタンに隠れる → 画像を9割にして下にずらし、上に帯を作って左右に置く（2026-11-19）
        top_band = int(H * 0.105)                                  # 約200px
        if dialogue_sides and "canvas" not in script:
            c["fg_w"], c["fg_h"] = int(c["fg_w"] * 0.9) // 2 * 2, int(c["fg_h"] * 0.9) // 2 * 2
            c["y_off"] = top_band - (H - c["fg_h"]) // 2
        side_x = {"left": int(W * 0.05), "right": W - int(W * 0.05) - isz}
        icon_y = int((top_band - isz * 0.84 - c["font"] * 0.6) / 2)
    c["_icons"] = [(k, side_x[sd] + isz // 2, icon_y + int(isz * 0.84), nm) for k, sd, _, _, nm in icons] if dialogue_sides else []
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
        extra = []
        if beside:     # 真ん中の字幕のすぐ左に、話している方のアイコンだけ（字幕の行が変わるたびに、その行の幅に合わせて動かす）
            who = sc.get("speaker") or "narrator"
            who = main_spk if who == "narrator" else who
            on_p = next((x[2] for x in icons if x[0] == who), None)
            if on_p:
                kikite = who in c["_kikite"]
                subs = sc["subtitle"]; each = sc["_sec"] / len(subs)
                extra += ["-loop", "1", "-i", str(on_p)]
                vf += f"[v0];[1:v]scale={isz}:{isz},split={len(subs)}" + "".join(f"[ic{i}]" for i in range(len(subs)))
                for i, text in enumerate(subs):
                    fs = c["font"] if (kikite or not (i == len(subs) - 1 and len(subs) > 1)) else c["hilite"]
                    rows = wrap_sub(text, c["wrap"])
                    tw = max(text_w(r) for r in rows) * fs
                    x = max(8, int(W / 2 - tw / 2 - isz * 0.74))
                    y = int(H - c["margin_v"] - len(rows) * fs * 1.22 / 2 - isz / 2)
                    vf += (f";[v{i}][ic{i}]overlay={x}:{y}:shortest=1:enable='between(t,{each * i:.3f},{each * (i + 1):.3f})'"
                           + (f"[v{i + 1}]" if i + 1 < len(subs) else ""))
        elif corner:     # 下の左右の角に2人を固定。話している方＝_on（＋_on_open があれば声の出ている間だけ1秒に5回 口を開ける）／ほか＝_off
            who = sc.get("speaker") or "narrator"
            who = main_spk if who == "narrator" else who
            vf += "[v0]"; k_in, lab = 1, 0
            for k, sd, on_p, off_p, _ in icons:
                extra += ["-loop", "1", "-i", str(on_p if k == who else off_p)]
                vf += f";[{k_in}:v]scale={isz}:{isz}[ic{lab}];[v{lab}][ic{lab}]overlay={side_x[sd]}:{icon_y}:shortest=1[v{lab + 1}]"
                k_in += 1; lab += 1
                open_p = on_p.with_name(on_p.stem + "_open.png")
                if k == who and open_p.exists() and sc["_audio"]:
                    rg = speech_ranges(sc["_audio"])
                    if rg:
                        cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in rg)
                        extra += ["-loop", "1", "-i", str(open_p)]
                        vf += (f";[{k_in}:v]scale={isz}:{isz}[ic{lab}];[v{lab}][ic{lab}]overlay={side_x[sd]}:{icon_y}:shortest=1"
                               f":enable='gt({cond},0)*lt(mod(t,0.2),0.1)'[v{lab + 1}]")
                        k_in += 1; lab += 1
            vf = vf[: vf.rfind(f"[v{lab}]")]                                     # 最後の出口のラベルは付けない
        elif dialogue:   # 丸アイコンを重ねる（話している方＝_on・ほか＝_off）
            who = sc.get("speaker") or "narrator"
            who = main_spk if who == "narrator" else who
            vf += "[v0]"
            for i, (k, sd, on_p, off_p, _) in enumerate(icons):
                extra += ["-loop", "1", "-i", str(on_p if k == who else off_p)]
                vf += f";[{i + 1}:v]scale={isz}:{isz}[ic{i}];[v{i}][ic{i}]overlay={side_x[sd]}:{icon_y}:shortest=1"
                vf += f"[v{i + 1}]" if i + 1 < len(icons) else ""
        for _try in range(4):          # 長尺（4K経由のzoompan）は不定期に落ちる（2026-11-07）→ 再試行
            r = subprocess.run(["ffmpeg", "-y", "-filter_threads", "1", "-i", str(src), *extra, "-filter_complex", vf, "-t", str(sc["_sec"]), "-r", str(FPS),
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
