# -*- coding: utf-8 -*-
"""読み方の検証用: 文字起こしを「ひらがな」で出させる（漢字に直されると読み間違いが隠れるため）。使い方: python asr_kana.py a.mp3 ..."""
import sys
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
P = "これは、すべて ひらがなで かきおこした ぶんしょうです。きょうは、けいばの よそうを おとどけします。さんちゃくないりつは にじゅうろく ぱーせんとです。"
for f in sys.argv[1:]:
    seg, _ = m.transcribe(f, language="ja", beam_size=5, initial_prompt=P, condition_on_previous_text=True)
    print(f.split("/")[-1], "|", "".join(s.text for s in seg), flush=True)
