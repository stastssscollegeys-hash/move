# asr_check.py（preview_week）の写し。馬名リストを環境変数 ASR_P で渡す版（2026-11-13・枠順確定版）
import os, sys
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[1], device="cpu", compute_type="int8", cpu_threads=2)
P = os.environ.get("ASR_P", "")
for f in sys.argv[2:]:
    segs, _ = m.transcribe(f, language="ja", beam_size=5, initial_prompt=P)
    print(f.replace("\\", "/").split("/")[-1], "".join(s.text for s in segs), flush=True)
