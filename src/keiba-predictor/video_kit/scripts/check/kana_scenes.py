# -*- coding: utf-8 -*-
"""場面ごとの音声をひらがなで文字起こしして、読み方を台本と見比べる材料を出す（読みの検証用）
使い方: python kana_scenes.py <script.json> [音声フォルダ（既定＝台本と同じフォルダの _raw）] [場面id ...]
2026-11-19 台本の名前（script_mcs_long.json）が中に書き込まれていて、ほかのレースで動かなかった → 引数で渡す形にした"""
import json, sys
from pathlib import Path
from faster_whisper import WhisperModel
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tts")); from tts_yomi import yomi
sp = Path(sys.argv[1])
tag = sp.name.replace("script_", "").replace(".json", "")
adir = Path(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].isdigit() else sp.parent / "_raw"
only = {int(a) for a in sys.argv[2:] if a.isdigit()}
S = json.load(open(sp, encoding="utf-8"))["scenes"]
m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
P = "これは、すべて ひらがなで かきおこした ぶんしょうです。きょうは、けいばの よそうを おとどけします。さんちゃくないりつは にじゅうろく ぱーせんとです。ちゅうもくばの たんぴょうです。"
for s in S:
    if only and s["id"] not in only: continue
    seg, _ = m.transcribe(str(adir / f"{tag}_{s['id']:02d}.wav"), language="ja", beam_size=5, initial_prompt=P, condition_on_previous_text=False)
    print(f"{s['id']:02d} 読|", "".join(x.text for x in seg).strip(), flush=True)
    print(f"   渡|", yomi(s["narration"]), flush=True)
