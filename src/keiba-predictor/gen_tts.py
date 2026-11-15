# -*- coding: utf-8 -*-
"""gen_tts.py — 動画のナレーション音声を Gemini TTS（REST）で作る（2026-11-06 新規・gen_short_tts.js の代わり）
node の @google/genai が無くても動く。キーは .env の GEMINI_API_KEY, 2〜5 を順に使う（429で切り替え）。
入力: {shorts|videos}/script_*.json の scenes[].narration ／ 出力: 同じフォルダの audio/{tag}_{id:02d}.wav（24kHz/16bit/mono）
使い方: python gen_tts.py <script.json> [--voice Zephyr] [--only 3,5]
"""
import base64
import json
import os
import re
import sys
import time
import wave
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ENV = Path(__file__).resolve().parents[2] / ".env"
MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")


def keys():
    ks = []
    for ln in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"(GEMINI_API_KEY\d*)=(.+)", ln.strip())
        if m:
            ks.append(m.group(2).strip().strip('"\''))
    return ks


def tts(text, voice, key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    r = requests.post(url, params={"key": key}, json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:120]}")
    pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    return pcm


def main():
    sp = Path(sys.argv[1])
    voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "Zephyr"
    only = set(int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    script = json.loads(sp.read_text(encoding="utf-8"))
    tag = sp.name.replace("script_", "").replace(".json", "")
    out = sp.parent / "audio"
    out.mkdir(exist_ok=True)
    ks = keys()
    ki = 0
    print(f"TTSモデル: {MODEL} ／ 声: {voice} ／ キー {len(ks)}本")
    for s in script["scenes"]:
        if only and s["id"] not in only:
            continue
        wav = out / f"{tag}_{s['id']:02d}.wav"
        for attempt in range(8):
            try:
                pcm = tts(s["narration"], voice, ks[ki % len(ks)])
                with wave.open(str(wav), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
                print(f"  [{s['id']}] {len(pcm)/48000:.1f}秒  {s['narration'][:26]}…")
                break
            except Exception as e:
                print(f"  [{s['id']}] 再試行{attempt+1}: {str(e)[:90]}")
                ki += 1
                time.sleep(6)
        else:
            print(f"  [{s['id']}] 失敗")
        time.sleep(7)                       # flash は 10 req/min
    print("保存:", out)


if __name__ == "__main__":
    main()
