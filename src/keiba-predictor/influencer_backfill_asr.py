# -*- coding: utf-8 -*-
"""
influencer_backfill_asr.py — 字幕が取れなかった予想動画だけ、音声を文字起こしで補う（2026-10-30新規）
====================================================================================================
influencer_backfill_fetch.py の index.json で chars==0（自動字幕なし）の動画が対象。
faster-whisper（CPU・int8・small）。GPUが無いので1本あたり動画時間の0.5〜1倍かかる → 上限 --max-min（既定45分）を超える動画と、
メンバー限定で音声が取れない動画は飛ばす。結果は transcripts/ に同じ命名で保存し、index.json の chars・path・asr=True を更新する。
使い方: python influencer_backfill_asr.py [--max-min 45] [--limit 40]
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "influencer_backfill"
TR = ROOT / "transcripts"


def main(A):
    idx_f = ROOT / "index.json"
    idx = json.loads(idx_f.read_text(encoding="utf-8"))
    todo = [x for x in idx if not x.get("path")][: A.limit]
    print(f"文字起こし対象 {len(todo)}本", flush=True)
    if not todo:
        return
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    tmp = ROOT / "_tmp"
    tmp.mkdir(exist_ok=True)
    for i, x in enumerate(todo, 1):
        url = f"https://www.youtube.com/watch?v={x['id']}"
        meta = subprocess.run([sys.executable, "-m", "yt_dlp", url, "--skip-download", "--no-warnings", "--print", "%(duration)s"],
                              capture_output=True, text=True, encoding="utf-8", timeout=120).stdout.strip().splitlines()
        dur = float(meta[-1]) if meta and meta[-1].replace(".", "", 1).isdigit() else 0
        if not dur or dur > A.max_min * 60:
            print(f"  [{i}/{len(todo)}] 飛ばす（長さ {dur/60:.0f}分 or 不明） {x['channel']} {x['title'][:30]}", flush=True)
            continue
        out = tmp / f"{x['id']}.m4a"
        subprocess.run([sys.executable, "-m", "yt_dlp", url, "-f", "bestaudio[ext=m4a]/bestaudio", "--no-warnings", "-o", str(out)],
                       capture_output=True, text=True, encoding="utf-8", timeout=900)
        f = next(iter(tmp.glob(f"{x['id']}.*")), None)
        if not f:
            print(f"  [{i}/{len(todo)}] 音声取得できず（メンバー限定？） {x['channel']}", flush=True)
            continue
        segs, _ = model.transcribe(str(f), language="ja", vad_filter=True, beam_size=1)
        txt = "\n".join(s.text.strip() for s in segs if s.text.strip())
        f.unlink()
        p = TR / f"{x['race_date']}_{x['channel']}_{x['id']}.txt"
        p.write_text(txt, encoding="utf-8")
        x.update(chars=len(txt), path=str(p), asr=True)
        idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  [{i}/{len(todo)}] 文字起こし {len(txt):,}字 {x['channel']} {x['title'][:30]}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-min", type=int, default=45)
    ap.add_argument("--limit", type=int, default=40)
    main(ap.parse_args())
