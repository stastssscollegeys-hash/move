# -*- coding: utf-8 -*-
"""長尺の仕上げミックス（2026-11-15 ユーザー指摘を反映）
・声を大きく（-15 LUFS 付近へ）・BGMを控えめに（-30 LUFS）・BGMは場面で3曲を切り替え（_bgm_sections.mp3）
・効果音を場面の種類ごとに変える（「決まりきって一辺倒」→ 章の切り替え／データ／馬の紹介／注意／ランキング／TOP3／まとめ で別の音）
入力: tospo_long_long.mp4（build_video.py の出力＝声と字幕だけ）→ _tmp/tospo_long_voice.mp4 に退避して使う。出力: tospo_long_long.mp4 を置き換える"""
import json, subprocess, wave, shutil, re, sys
from pathlib import Path
D = Path(__file__).resolve().parent; TMP = D / "_tmp"; TMP.mkdir(exist_ok=True)
SE = TMP / "se"; SE.mkdir(exist_ok=True)
YA = Path(__import__("os").environ.get("KVC_SE_DIR", "assets/se"))
VOICE_LUFS, BGM_LUFS = -15.0, -30.0
def run(c):
    r = subprocess.run(c, capture_output=True)
    if r.returncode: print(r.stderr.decode("utf-8", "replace")[-900:]); sys.exit("ffmpeg失敗")
def lufs(p, extra=()):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *extra, "-i", str(p), "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr.decode("utf-8", "replace"))[-1])
def synth(name, expr, d, af=""):
    o = SE / f"{name}.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':d={d}:s=48000", *(["-af", af] if af else []), "-ac", "2", str(o)]); return o
def noise(name, d, af):
    o = SE / f"{name}.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=pink:a=0.6:r=48000", "-af", af, "-ac", "2", str(o)]); return o
def cut(name, src, st, du):
    o = SE / f"{name}.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(st), "-t", str(du), "-i", str(src), "-af", f"loudnorm=I=-18:TP=-2,afade=t=in:d=0.01,afade=t=out:st={max(du-0.15,0):.2f}:d=0.15", "-ar", "48000", "-ac", "2", str(o)]); return o
PI = "2*PI"
SES = dict(
 whoosh  = noise("whoosh", 0.5, "highpass=f=500,lowpass=f=4500,afade=t=in:d=0.22,afade=t=out:st=0.22:d=0.28,volume=0.8"),
 whoosh2 = noise("whoosh2", 0.7, "highpass=f=250,lowpass=f=2500,afade=t=in:d=0.4,afade=t=out:st=0.4:d=0.3,volume=0.9"),          # 低めで長い（章の切り替え）
 swish   = noise("swish", 0.3, "highpass=f=1500,lowpass=f=8000,afade=t=in:d=0.08,afade=t=out:st=0.1:d=0.2,volume=0.6"),          # 軽い（場面内の切り替え）
 ding    = synth("ding", f"0.5*sin({PI}*1318.5*t)*exp(-5*t)+0.3*sin({PI}*1975.5*t)*exp(-6*t)", 0.9),
 ding2   = synth("ding2", f"0.45*sin({PI}*880*t)*exp(-4*t)+0.3*sin({PI}*1320*t)*exp(-5*t)", 1.0),                                  # 低めのチャイム
 twotone = synth("twotone", f"0.4*sin({PI}*784*t)*exp(-9*t)+0.4*sin({PI}*1046.5*(t-0.16))*exp(-7*(t-0.16))*gt(t,0.16)", 0.9),    # ピンポン（馬の紹介）
 rise    = synth("rise", f"0.35*sin({PI}*(400+900*t)*t)*min(1,t*6)*exp(-1.5*(0.6-t)*lt(t,0.6))", 0.6, "afade=t=out:st=0.45:d=0.15"),  # 上がる音（期待）
 blip    = synth("blip", f"0.5*sin({PI}*1760*t)*exp(-30*t)", 0.25),                                                              # 短い点（ランキング1頭ごと）
 low     = synth("low", f"0.6*sin({PI}*196*t)*exp(-4*t)+0.3*sin({PI}*147*t)*exp(-3*t)", 1.1),                                    # 低い音（注意・軸にしない馬）
 fanfare = synth("fanfare", f"0.35*(sin({PI}*523.25*t)*lt(t,0.18)+sin({PI}*659.25*t)*gt(t,0.18)*lt(t,0.36)+sin({PI}*783.99*t)*gt(t,0.36)*lt(t,0.54)+(sin({PI}*1046.5*t)+0.5*sin({PI}*1318.5*t))*gt(t,0.54)*exp(-2.5*(t-0.54)))", 1.6, "afade=t=out:st=1.2:d=0.4"),
 pop     = synth("pop", f"0.6*sin({PI}*(520+300*t)*t)*exp(-9*t)", 0.5),
 xylo    = cut("xylo", YA / "Xylophone Tip Toe Scale Up.mp3", 1.50, 1.30),
 thunk   = cut("thunk", YA / "Cartoon Metal Thunk.mp3", 1.80, 1.40),
)
S = json.loads((D / "script_tospo_long.json").read_text(encoding="utf-8"))["scenes"]
def sec(i):
    w = wave.open(str(D / "audio" / f"tospo_long_{i:02d}.wav")); return w.getnframes() / w.getframerate() + PAD
PAD = float((D / "_pad.txt").read_text()) if (D / "_pad.txt").exists() else 0.45
KIND = {"T01": "open", "T02": "info", "T03": "data", "T04": "data", "T05": "data", "T16": "news", "T06": "how", "T07": "table", "T09": "horse", "T10": "horse",
        "T17": "warn", "T08": "table", "T11": "horse", "T12": "rank", "T13": "rank", "T14": "top3", "T15": "end"}
ev, t, prev, n_in = [], 0.0, None, 0     # (音, 時刻, 音量)
for k, s in enumerate(S):
    img = s["image"][:3]; kind = KIND[img]; first = img != prev; n_in = 0 if first else n_in + 1
    if first and k > 0:            # 章の切り替え（画像が変わる）: 種類ごとに別の音
        ev.append((SES["whoosh2"], max(t - 0.15, 0), 0.9))
        ev.append((dict(data=SES["ding"], news=SES["twotone"], how=SES["ding2"], table=SES["xylo"], horse=SES["rise"], warn=SES["low"], rank=SES["rise"], top3=SES["fanfare"], end=SES["ding2"], info=SES["ding2"])[kind], t + 0.25, 0.75))
    elif not first:                # 同じ画像の中の切り替え: 種類と順番で音を変える
        if kind == "rank":   ev.append((SES["blip"] if n_in % 2 else SES["pop"], t + 0.05, 0.6))
        elif kind == "top3": ev.append((SES["xylo"], t + 0.05, 0.8))
        elif kind == "data": ev.append(((SES["ding"], SES["swish"], SES["ding2"])[n_in % 3], t + 0.1, 0.55))
        elif kind == "warn": ev.append(((SES["low"], SES["swish"])[n_in % 2], t + 0.05, 0.55))
        elif kind == "horse": ev.append(((SES["twotone"], SES["swish"], SES["whoosh"])[n_in % 3], t + 0.05, 0.55))
        else:                ev.append(((SES["swish"], SES["whoosh"])[n_in % 2], max(t - 0.1, 0), 0.5))
    prev = img; t += sec(s["id"])
total = t; ev.append((SES["thunk"], total - sec(S[-1]["id"]) + 0.05, 0.6))
mp4 = D / "tospo_long_long.mp4"; voice = TMP / "tospo_long_voice.mp4"
if not voice.exists(): shutil.copy2(mp4, voice)
vg = 10 ** ((VOICE_LUFS - lufs(voice)) / 20); bgm = D / "_bgm_sections.mp3"; bg = 10 ** ((BGM_LUFS - lufs(bgm, ("-t", "120"))) / 20)
uniq = list(dict.fromkeys(f for f, _, _ in ev)); ins = ["-i", str(voice), "-i", str(bgm)]
for f in uniq: ins += ["-i", str(f)]
fc = [f"[0:a]volume={vg:.3f}[v]", f"[1:a]atrim=0:{total + 1:.2f},asetpts=PTS-STARTPTS,volume={bg:.3f},afade=t=in:d=1.2,afade=t=out:st={max(total - 2.5, 0):.2f}:d=2.4[bgm]"]
# 同じ効果音を何度も使うので、入力ごとに asplit する
cnt = {f: sum(1 for g, _, _ in ev if g == f) for f in uniq}; used = {f: 0 for f in uniq}
for i, f in enumerate(uniq):
    fc.append(f"[{i + 2}:a]asplit={cnt[f]}" + "".join(f"[s{i}_{j}]" for j in range(cnt[f])))
labels = ["[v]", "[bgm]"]
for n, (f, at, v) in enumerate(ev):
    i = uniq.index(f); j = used[f]; used[f] += 1
    fc.append(f"[s{i}_{j}]adelay={int(at * 1000)}|{int(at * 1000)},volume={v:.2f}[e{n}]"); labels.append(f"[e{n}]")
fc.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95[a]")
(TMP / "mix_fc.txt").write_text(";\n".join(fc), encoding="utf-8")
out = TMP / "tospo_long_mix.mp4"
run(["ffmpeg", "-y", "-loglevel", "error"] + ins + ["-filter_complex_script", str(TMP / "mix_fc.txt"), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(out)])
shutil.move(str(out), str(mp4))
import collections
print(f"✅ {mp4.name} {total:.1f}秒  声×{vg:.2f}（→{VOICE_LUFS}LUFS） BGM×{bg:.3f}（→{BGM_LUFS}LUFS）  効果音 {len(ev)}個・{len(uniq)}種類", dict(collections.Counter(f.stem for f, _, _ in ev)))
