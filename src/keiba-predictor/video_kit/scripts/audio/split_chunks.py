# -*- coding: utf-8 -*-
"""split_chunks.py（2026-11-13）: tts_chunks.js のチャンク音声を場面ごとに切り分ける。
境目の候補＝無音区間（silencedetect）。各境目は「文字数の割合から見た位置」に近く、長い無音ほど良いものを、順序を保って選ぶ（DP）。
出力: <scriptのフォルダ>/_raw/{tag}_{id:02d}.wav（素の声）→ 倍速は別工程。切り分けの正しさは文字起こし照合で確かめる。
使い方: python split_chunks.py <script_long.json> [チャンク番号 ...] [チャンク:境目:+1 ...]"""
import json, os, re, subprocess, sys, tempfile, wave
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
def align_pick(wav, texts, cand, n):
    """2026-11-19 文字起こしと台本を突き合わせて切れ目を決め（align_cuts.py・ローカルの faster-whisper）、前後2秒でいちばん長い無音に寄せる。
    無音と見込みの位置だけで選ぶと、場面の中の文の間（「強い馬です。」のあと）を場面の切れ目と取り違えた（霜月S の試し）。
    決められない（faster-whisper が無い・一致率0.6未満・順番が崩れる）ときは None"""
    if os.environ.get("KVC_NO_ALIGN") == "1": return None
    tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8"); json.dump(texts, tf, ensure_ascii=False); tf.close()
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("align_cuts.py")), str(wav), tf.name], capture_output=True, text=True, encoding="utf-8", errors="replace")
    os.unlink(tf.name)
    try: res = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception: return None
    if len(res.get("cuts", [])) != n or res.get("score", 0) < 0.6: return None
    pick = []
    for t in res["cuts"]:
        best, bs = None, -1e9
        for j, (a, b) in enumerate(cand):
            d = abs((a + b) / 2 - t)
            if d <= 2.0 and (b - a) - 0.3 * d > bs: best, bs = j, (b - a) - 0.3 * d
        if best is None: return None
        pick.append(best)
    if any(pick[k] <= pick[k - 1] for k in range(1, n)): return None
    print(f"  （文字起こしで切れ目を決めた・一致率 {res['score']}）")
    return pick
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
    if len(ids) == 1:   # 2026-11-19 対話モード: 話し手が変わるたびに区切るので1場面だけのまとめが多い → 区切らず前後の無音だけ落とす
        out = base / "_raw" / f"{tag}_{ids[0]:02d}.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), "-ss", f"{max(0.0, s0 - 0.25):.3f}", "-to", f"{e0 + 0.15:.3f}",
                        "-af", "areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse", str(out)], check=True)
        print(f"c{ci} 場面{ids}  {T:.1f}秒（1場面）"); continue
    L = [len(re.sub(r"[、。・\s]", "", nar[i])) for i in ids]; tot = sum(L); sp_len = e0 - s0
    exp = [s0 + sp_len * sum(L[:k + 1]) / tot for k in range(len(ids) - 1)]
    n, m = len(exp), len(cand)
    if m < n: print(f"c{ci}: 候補不足（無音{m}・必要{n}）→ 場面ごとに作り直す"); continue
    def sc(k, j):
        a, b = cand[j]; mid = (a + b) / 2
        return (b - a) * 2.0 - abs(mid - exp[k]) / max(1.0, sp_len / tot * 6)   # 長い無音を優先・予想位置からのずれに罰
    pick = align_pick(f, [nar[i] for i in ids], cand, n)
    if pick is None:   # 文字起こしで決められないときだけ、今までの「無音の長さ×見込みの位置」で選ぶ
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
    cuts = [max(0.0, s0 - 0.25)] + [(cand[j][0] + cand[j][1]) / 2 for j in pick] + [e0 + 0.15]
    for k, i in enumerate(ids):
        a = max(0, cuts[k] if k == 0 else cuts[k] ); b = cuts[k + 1]
        out = base / "_raw" / f"{tag}_{i:02d}.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-af", ("areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse" if k == 0 else   # 2026-11-15: 段落の先頭の場面は頭を削らない（「まとめです」「ここから」の出だしが欠けた）
                                "silenceremove=start_periods=1:start_threshold=-40dB,areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse"), str(out)], check=True)
    dev = [round((cand[j][0] + cand[j][1]) / 2 - e, 1) for j, e in zip(pick, exp)]
    print(f"c{ci} 場面{ids}  {T:.1f}秒  境目の無音{[round(cand[j][1]-cand[j][0],2) for j in pick]}  予想位置とのずれ{dev}")
    # 2026-11-20 福島記念：Gemini が場面の文を読み終えたあと、ほかの場面の文を繰り返して読んだ（64字で36.5秒）→ 1秒あたりの字数が少ない場面を知らせる
    for i in ids:
        w = base / "_raw" / f"{tag}_{i:02d}.wav"
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(w)], capture_output=True, text=True).stdout.strip() or 0)
        if d and len(nar.get(i, "")) / d < 2.8:
            print(f"   ⚠ 場面{i}: {len(nar.get(i, ''))}字で {d:.1f}秒（1秒に {len(nar.get(i, '')) / d:.1f}字）＝ほかの場面の文を繰り返して読んだ疑い。kana_scenes.py で確かめ、文の終わりの無音で切る")
