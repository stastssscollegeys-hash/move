"""align_cuts.py — まとめて読ませた音声の「場面の切れ目」の秒を、文字起こしと台本の突き合わせで決める（2026-10-21 作・2026-11-19 競馬の split_chunks.py 用に写した）

split_chunks.py から呼ぶ。API は使わない（ローカルの faster-whisper）。
無音と字数の割合だけで切ると、文の途中の長い間を行の切れ目と取り違え、そこから後ろが1行ずつずれた（LW11 の1回目で 14行×2か所）。
→ ① Whisper で言葉ごとの秒を取る ② 台本の文字と文字起こしの文字を突き合わせ（difflib）、行の終わりの文字が何秒目かを出す
  ③ その近く（±0.6秒）でいちばん長い無音の真ん中に寄せる。

使い方: python align_cuts.py <batch.wav> <lines.json>   → 標準出力に {"cuts": [秒, …], "score": 一致率}
lines.json = ["行1の文", "行2の文", …]
"""
import difflib
import json
import re
import sys
import unicodedata
import wave

import numpy as np

_MODEL = None


def norm(s):
    s = unicodedata.normalize("NFKC", s).upper()
    return re.sub(r"[\s、。，．,.!！?？「」『』（）()・…ー〜~\-—:：;；\"'%％]", "", s)


def main():
    wav_path, lines_path = sys.argv[1], sys.argv[2]
    lines = json.load(open(lines_path, encoding="utf-8"))
    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    total = len(pcm) / rate

    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    # initial_prompt に台本を渡すと文字起こしが崩れた（2026-10-21・一致率 0.298）→ 渡さない
    segs, _ = model.transcribe(wav_path, language="ja", word_timestamps=True, vad_filter=False)
    # ★Whisper は、間のあとの言葉の始まりを「間が始まった秒」として返す（2026-10-21 実測・8か所すべて）。
    #   → 行の切れ目＝【次の行の最初の文字の始まりの秒】から始まる無音。各文字の「始まりの秒」を持っておく
    chars, times = [], []
    for seg in segs:
        for wd in seg.words or []:
            t = norm(wd.word)
            if not t:
                continue
            for k, ch in enumerate(t):
                chars.append(ch)
                times.append(wd.start + (wd.end - wd.start) * k / len(t))
    T = "".join(chars)

    S_parts = [norm(x) for x in lines]
    S = "".join(S_parts)
    sm = difflib.SequenceMatcher(None, S, T, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    score = sum(b.size for b in blocks) / max(1, len(S))

    # 台本の位置 i → 文字起こしの秒（一致した区間の間は線形に補う）
    anchors = [(0, 0.0)]
    for b in blocks:
        anchors.append((b.a, times[b.b]))
        anchors.append((b.a + b.size - 1, times[b.b + b.size - 1]))
    anchors.append((len(S), total))
    anchors.sort()
    ax = np.array([a for a, _ in anchors], dtype=float)
    at = np.maximum.accumulate(np.array([t for _, t in anchors], dtype=float))

    def time_at(i):
        return float(np.interp(i, ax, at))

    # 10ms ごとの音の大きさ（無音さがし）
    fr = int(rate * 0.01)
    n = len(pcm) // fr
    rms = np.sqrt((pcm[: n * fr].reshape(n, fr) ** 2).mean(axis=1))
    th = max(rms.max() * 0.03, 120)
    quiet = rms < th

    # 無音の続き（120ms 以上）
    runs = []
    s = -1
    for f in range(n + 1):
        qq = f < n and quiet[f]
        if qq and s < 0:
            s = f
        if not qq and s >= 0:
            if f - s >= 12:
                runs.append((s / 100, f / 100))
            s = -1

    # 台本の位置 → 文字起こしの文字の位置（一致した区間ならそのまま、間は前後から線形に）
    pairs = []
    for b in blocks:
        for k in range(b.size):
            pairs.append((b.a + k, b.b + k))
    pa = np.array([p for p, _ in pairs], dtype=float) if pairs else np.array([0.0])
    pb = np.array([q for _, q in pairs], dtype=float) if pairs else np.array([0.0])

    def start_time_of(i):
        j = int(round(float(np.interp(i, pa, pb))))
        j = min(max(j, 0), len(times) - 1)
        return times[j] if times else time_at(i)

    cuts = []
    acc = 0
    prev = 0.0
    for part in S_parts[:-1]:
        acc += len(part)
        ws = start_time_of(acc)  # 次の行の最初の文字の「始まりの秒」＝間の頭
        # 前の行の終わりと次の行の頭が1つの言葉につながると、文字の秒がずれる（LW11 で2か所）。
        # → 切れ目の前後2文字の秒の範囲に始まる無音のうち、いちばん長いもの（行のあいだは1秒あけさせている）
        lo = min(start_time_of(acc - 2), ws) - 0.1
        hi = max(start_time_of(acc + 2), ws) + 0.4
        cand = [r for r in runs if r[0] > prev + 0.05 and lo <= r[0] <= hi]
        if cand:
            r = max(cand, key=lambda r: (r[1] - r[0]) - abs(r[0] - ws) * 0.6)
            c = (r[0] + r[1]) / 2
        else:
            c = ws
        c = max(c, prev + 0.05)
        cuts.append(round(c, 3))
        prev = c
    print(json.dumps({"cuts": cuts, "score": round(score, 3), "total": round(total, 3)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
