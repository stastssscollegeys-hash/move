# -*- coding: utf-8 -*-
"""split_chunks.py（2026-11-13）: tts_chunks.js のチャンク音声を場面ごとに切り分ける。
境目の候補＝無音区間（silencedetect）。各境目は「文字数の割合から見た位置」に近く、長い無音ほど良いものを、順序を保って選ぶ（DP）。
出力: <scriptのフォルダ>/_raw/{tag}_{id:02d}.wav（素の声）→ 倍速は別工程。切り分けの正しさは文字起こし照合で確かめる。
使い方: python split_chunks.py <script_long.json> [チャンク番号 ...] [チャンク:境目:+1 ...]"""
import json, re, subprocess, sys, wave
from pathlib import Path
sp = Path(sys.argv[1]); S = json.loads(sp.read_text(encoding="utf-8"))
tag = sp.name.replace("script_", "").replace(".json", ""); base = sp.parent
CH = json.loads((base / "_chunks" / f"{tag}_chunks.json").read_text())
# 指定: チャンク番号 または 「チャンク:境目番号:+1」（その境目を次の無音へ。-1で前へ）。文字起こしで境目のずれを見つけたときに使う
only = set(int(a) for a in sys.argv[2:] if ":" not in a)
SHIFT = {}
for a in sys.argv[2:]:
    if ":" in a:
        c, b, d = a.split(":"); SHIFT[(int(c), int(b))] = int(d); only.add(int(c))
nar = {s["id"]: s["narration"] for s in S["scenes"]}
(base / "_raw").mkdir(exist_ok=True)
def dur(p):
    with wave.open(str(p)) as w: return w.getnframes() / w.getframerate()
for ci, ids in enumerate(CH, 1):
    if only and ci not in only: continue
    f = base / "_chunks" / f"{tag}_c{ci:02d}.wav"
    if not f.exists(): print("なし", f.name); continue
    T = dur(f)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    sil = list(zip(st, en + [T] * (len(st) - len(en))))
    s0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0          # 頭の無音
    e0 = sil[-1][0] if sil and sil[-1][1] >= T - 0.05 else T      # 終わりの無音
    cand = [(a, b) for a, b in sil if a > s0 + 0.5 and b < e0 - 0.5]
    L = [len(re.sub(r"[、。・\s]", "", nar[i])) for i in ids]; tot = sum(L); sp_len = e0 - s0
    exp = [s0 + sp_len * sum(L[:k + 1]) / tot for k in range(len(ids) - 1)]
    n, m = len(exp), len(cand)
    if m < n: print(f"c{ci}: 候補不足（無音{m}・必要{n}）→ 場面ごとに作り直す"); continue
    def sc(k, j):
        a, b = cand[j]; mid = (a + b) / 2
        return (b - a) * 2.0 - abs(mid - exp[k]) / max(1.0, sp_len / tot * 6)   # 長い無音を優先・予想位置からのずれに罰
    INF = -1e9; dp = [[INF] * m for _ in range(n)]; bk = [[-1] * m for _ in range(n)]
    for j in range(m): dp[0][j] = sc(0, j)
    for k in range(1, n):
        best, bj = INF, -1
        for j in range(m):
            if j > 0 and dp[k - 1][j - 1] > best: best, bj = dp[k - 1][j - 1], j - 1
            if bj >= 0: dp[k][j] = best + sc(k, j); bk[k][j] = bj
    j = max(range(m), key=lambda x: dp[n - 1][x]); pick = []
    for k in range(n - 1, -1, -1): pick.append(j); j = bk[k][j]
    pick = pick[::-1]
    for (c, bb), d in SHIFT.items():
        if c == ci: pick[bb - 1] = max(0, min(m - 1, pick[bb - 1] + d))
    cuts = [s0 - 0.05] + [(cand[j][0] + cand[j][1]) / 2 for j in pick] + [e0 + 0.15]
    for k, i in enumerate(ids):
        a = max(0, cuts[k] if k == 0 else cuts[k] ); b = cuts[k + 1]
        out = base / "_raw" / f"{tag}_{i:02d}.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-af", "silenceremove=start_periods=1:start_threshold=-40dB,areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse", str(out)], check=True)
    dev = [round((cand[j][0] + cand[j][1]) / 2 - e, 1) for j, e in zip(pick, exp)]
    print(f"c{ci} 場面{ids}  {T:.1f}秒  境目の無音{[round(cand[j][1]-cand[j][0],2) for j in pick]}  予想位置とのずれ{dev}")
