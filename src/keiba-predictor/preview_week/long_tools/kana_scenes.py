# -*- coding: utf-8 -*-
"""場面ごとの音声をひらがなで文字起こしして、読み方を台本と見比べる材料を出す（読みの検証用）"""
import json, re, sys
from faster_whisper import WhisperModel
sys.path.insert(0, "."); from tts_yomi import yomi
S = json.load(open("script_mcs_long.json", encoding="utf-8"))["scenes"]
m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
P = "これは、すべて ひらがなで かきおこした ぶんしょうです。きょうは、けいばの よそうを おとどけします。さんちゃくないりつは にじゅうろく ぱーせんとです。ちゅうもくばの たんぴょうです。"
for s in S:
    seg, _ = m.transcribe(f"_raw/mcs_long_{s['id']:02d}.wav", language="ja", beam_size=5, initial_prompt=P, condition_on_previous_text=False)
    print(f"{s['id']:02d} 読|", "".join(x.text for x in seg).strip(), flush=True)
    print(f"   原|", s["narration"], flush=True)
