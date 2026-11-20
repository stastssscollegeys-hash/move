# -*- coding: utf-8 -*-
"""lang_check.py（2026-11-17 ユーザー指摘「音声が英語で読み上げているところがある」）: 場面ごとの音声が日本語かどうかを調べる。
1) 言語を決めずに判定（日本語以外・確信度が低い場面を出す） 2) 言語を決めずに文字起こしして、英字が多い場面を出す 3) 台本の「◯位」の数より、聞き取った「位」が少ない場面を出す（順位を英語の数字で読むと「位」が消える） 4) 台本の長さに対して音声が長すぎる/短すぎる場面を出す
使い方: python lang_check.py <script.json> <audioフォルダ> <tag>   → 最後に「NG n件」。NG が 0 になるまで作り直す"""
import json, re, sys, wave
from faster_whisper import WhisperModel
sp, ad, tag = sys.argv[1:4]
m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
S = json.load(open(sp, encoding="utf-8"))["scenes"]; ng = 0
for s in S:
    f = f"{ad}/{tag}_{s['id']:02d}.wav"; w = wave.open(f); d = w.getnframes() / w.getframerate()
    seg, info = m.transcribe(f, beam_size=5, condition_on_previous_text=False)
    txt = "".join(x.text for x in seg).strip()
    latin = len(re.findall(r"[A-Za-z]", re.sub(r"\b(G[123]|TOP|S|AH|C)\b", "", txt)))
    cps = len(s["narration"]) / d
    bad = []
    if info.language != "ja": bad.append(f"言語={info.language}({info.language_probability:.2f})")
    elif info.language_probability < 0.80: bad.append(f"日本語の確信度{info.language_probability:.2f}")
    if latin >= 8: bad.append(f"英字{latin}")
    if not 4.0 <= cps <= 11.5: bad.append(f"速さ{cps:.1f}字/秒")
    nr, tr = len(re.findall(r"[一二三四五六七八九十]位", s["narration"])), len(re.findall(r"位", txt))
    if tr < nr: bad.append(f"順位の読み（台本{nr}か所・音声{tr}か所＝「三位」を「スリー」など英語の数字で読んだ疑い）")
    if bad: ng += 1
    print(f"{tag}{s['id']:02d} {'NG ' + '・'.join(bad) if bad else 'ok'} | {d:.1f}s | {txt[:70]}", flush=True)
print(f"NG {ng}件 / {len(S)}場面", flush=True)
