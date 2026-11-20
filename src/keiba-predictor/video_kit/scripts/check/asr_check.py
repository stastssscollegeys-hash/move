# 長尺・ショートの音声を文字起こしして台本と照合する（2026-11-11）。使い方: python asr_check.py small audio/xxx_51.wav ...（馬名リスト P は週ごとに書き換え）
import sys
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[1], device="cpu", compute_type="int8", cpu_threads=2)
P = "競馬の独自指数ランキング。ステレンボッシュ、チェルヴィニア、レーゼドラマ、ケリフレッドアスク、コガネノソラ、レイクラシック、エストゥペンダ、セキトバイースト、ニシノティアモ、ラヴァンダ、ジュウリョクピエロ、クイーンズウォーク、ジョスラン、ラフターラインズ、シャドウメテオ、アクアヴァーナル、ヴーレヴー、カムニャック。"
for f in sys.argv[2:]:
    segs, _ = m.transcribe(f, language="ja", beam_size=5, initial_prompt=P)
    print(f.split("/")[-1], "".join(s.text for s in segs), flush=True)
