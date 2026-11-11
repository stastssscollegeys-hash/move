# -*- coding: utf-8 -*-
"""
add_bgm_se.py — 完成したショート動画（ナレーション＋字幕入り）に BGM と効果音を足す（2026-11-02新規）
================================================================================
入力: shorts/{tag}_short.mp4（build_short.py の出力）＋ shorts/script_{tag}.json ＋ shorts/audio/{tag}_NN.wav
出力: shorts/{tag}_short.mp4 を BGM・SE入りで置き換える。元の版は shorts/_tmp/{tag}_voice.mp4 に残す。
効果音: 外部素材は使わず ffmpeg で合成する（場面切り替え=シュッ／データ表示=チャイム／最後=ポン）。
BGM: output/shared-bgm の曲を指定（声の邪魔にならないよう小さく、頭と終わりにフェード）。

使い方: python add_bgm_se.py <shorts/script_xxx.json> "<BGM名>.mp3" [--vol 0.10]
"""
from __future__ import annotations
import json, shutil, subprocess, sys, wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BGM_DIR = Path(__file__).resolve().parents[2] / "output" / "shared-bgm"


def wav_sec(p):
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        print(r.stderr.decode("utf-8", "replace")[-1200:]); sys.exit("ffmpeg失敗")


def make_se(tmp: Path):
    whoosh, ding, pop = tmp / "se_whoosh.wav", tmp / "se_ding.wav", tmp / "se_pop.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anoisesrc=d=0.5:c=pink:a=0.6:r=48000",
         "-af", "highpass=f=500,lowpass=f=4500,afade=t=in:d=0.22,afade=t=out:st=0.22:d=0.28,volume=0.9", str(whoosh)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "aevalsrc='0.55*sin(2*PI*1318.5*t)*exp(-5*t)+0.35*sin(2*PI*1975.5*t)*exp(-6*t)':d=0.9:s=48000",
         str(ding)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "aevalsrc='0.7*sin(2*PI*(520+300*t)*t)*exp(-9*t)':d=0.5:s=48000", str(pop)])
    return whoosh, ding, pop


def main():
    sp = Path(sys.argv[1]); bgm = BGM_DIR / sys.argv[2]
    vol = float(sys.argv[sys.argv.index("--vol") + 1]) if "--vol" in sys.argv else 0.10
    script = json.loads(sp.read_text(encoding="utf-8"))
    base = sp.parent; tag = sp.name.replace("script_", "").replace(".json", "")
    tmp = base / "_tmp"; tmp.mkdir(exist_ok=True)
    mp4 = base / f"{tag}_{script.get('out_suffix', 'short')}.mp4"       # 横の長尺は script の out_suffix で出力名を変える（2026-11-06）
    voice = tmp / f"{tag}_voice.mp4"
    if not voice.exists():
        shutil.copy2(mp4, voice)               # 声だけの版は常に元の入力にする（二重掛け防止）
    # 場面の開始時刻 = これまでの(音声長+0.45)の合計（build_short.py と同じ式）
    t, starts = 0.0, []
    for sc in script["scenes"]:
        starts.append(t)
        t += wav_sec(base / "audio" / f"{tag}_{sc['id']:02d}.wav") + 0.45
    total = t
    whoosh, ding, pop = make_se(tmp)

    # SE配置: 場面切り替え(2場面目以降)=シュッ ／ データ場面(tagに「データ」)=開始0.25秒後にチャイム ／ 最終場面=ポン
    ev = []
    for i, (sc, st) in enumerate(zip(script["scenes"], starts)):
        if i > 0:
            ev.append((whoosh, max(st - 0.12, 0), 0.55))
        if "データ" in " ".join(sc["subtitle"]) or sc["image"].endswith(("_2.png", "_3.png", "_4.png")):
            ev.append((ding, st + 0.28, 0.5))
    ev.append((pop, starts[-1] + 0.05, 0.6))

    ins = ["-i", str(voice), "-stream_loop", "-1", "-i", str(bgm)]     # 2026-11-07: BGMが動画より短い（60秒の曲・5分の長尺）ときは繰り返す
    for f in (whoosh, ding, pop):
        ins += ["-i", str(f)]
    idx = {whoosh: 2, ding: 3, pop: 4}
    fc = [f"[1:a]atrim=0:{total + 1:.2f},asetpts=PTS-STARTPTS,volume={vol},"
          f"afade=t=in:d=1.2,afade=t=out:st={max(total - 2.5, 0):.2f}:d=2.4[bgm]"]
    labels = ["[0:a]", "[bgm]"]
    for n, (f, at, v) in enumerate(ev):
        fc.append(f"[{idx[f]}:a]adelay={int(at * 1000)}|{int(at * 1000)},volume={v}[se{n}]")
        labels.append(f"[se{n}]")
    fc.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95[a]")
    out = tmp / f"{tag}_mix.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error"] + ins + ["-filter_complex", ";".join(fc),
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(out)])
    shutil.move(str(out), str(mp4))
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(mp4)],
                       capture_output=True, text=True).stdout.strip()
    print(f"✅ {mp4.name}  {float(d):.1f}秒  BGM={bgm.name} vol={vol}  SE {len(ev)}個")


if __name__ == "__main__":
    main()
