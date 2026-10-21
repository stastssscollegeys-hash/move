# -*- coding: utf-8 -*-
"""
race_meta.py — レースごとの 開催の回・日目・柵（A/B/C…）を引く表（2026-10-07新規）
  TARGET の SR（2016〜）＋ JV-Link の RA（jv_raw/RACE・RT・RT/entry）から作り、db/race_meta.pkl に保存する。
  柵は RA レコードの 710 バイト目（芝のみ。ダートは空）。
使い方: python race_meta.py --build    ／ 他から: import race_meta; M = race_meta.load(); M[(日付, 場, R)] → (回, 日目, 柵)
"""
from __future__ import annotations
import argparse, glob, pickle, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import target_import as T

OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "race_meta.pkl"


def _add(out, r):
    x = T.parse_ra(r)
    if x and x["R"]:
        out[(x["date"], x["venue"], x["R"])] = (T.seg(r, 22, 2), T.seg(r, 24, 2), r[709:710].decode("ascii", "ignore").strip())


def build():
    out = {}
    for y in range(2016, 2028):
        for f in glob.glob(f"C:/TFJV/SE_DATA/{y}/SR*.DAT"):
            for r in T.records(Path(f), 1272):
                _add(out, r)
    for f in list(Path("C:/keiba_db/jv_raw/RACE").glob("RA_*.txt")) + list(Path("C:/keiba_db/jv_raw/RT").glob("RA_*.txt")) + list(Path("C:/keiba_db/jv_raw/RT/entry").glob("RA_*.txt")):
        b = f.read_bytes()
        for i in range(0, len(b) - 1271, 1272):
            _add(out, b[i:i + 1272])
    OUT.write_bytes(pickle.dumps(out))
    print(f"■ レースの開催・柵 {len(out):,}レース → {OUT}")
    return out


def load(refresh_recent=True):
    out = pickle.loads(OUT.read_bytes()) if OUT.exists() else build()
    if refresh_recent:                                # 当日・直近の出走表（JV）も足す
        for f in list(Path("C:/keiba_db/jv_raw/RT").glob("RA_*.txt")) + list(Path("C:/keiba_db/jv_raw/RT/entry").glob("RA_*.txt")) + list(Path("C:/keiba_db/jv_raw/RACE").glob("RA_2026.txt")):
            b = f.read_bytes()
            for i in range(0, len(b) - 1271, 1272):
                _add(out, b[i:i + 1272])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    if ap.parse_args().build:
        build()
