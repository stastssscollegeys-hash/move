# -*- coding: utf-8 -*-
"""
walk_prevday_test.py — 「前日の内枠有利度」特徴量を足すと年ごとの前向き検証が改善するか（2026-10-14）
=====================================================================================================
同じ10年データ（daily_pdca/db/history_target）で ev_engine.run_walk を 2回回して並べる。
  基準 : 現行の特徴量（調教あり・当日バイアスなし）
  前日 : 基準 + 「前日の内枠有利度×内枠」「前日の内枠有利度×外枠」（PREVDAY=1）
使い方: python walk_prevday_test.py          # 約20〜30分・メモリ3GB前後。他の重い処理と同時に回さない
        python walk_prevday_test.py --flag HORSEFIT   # 別の追加特徴量（ev_engine の環境変数スイッチ）を同じ形で比べる（2026-10-14）
"""
from __future__ import annotations
import argparse, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
FLAG = "PREVDAY"


def one(prevday: bool):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop(FLAG, None)
    if prevday:
        env[FLAG] = "1"
    code = ("import sys; sys.path.insert(0, %r); import ev_engine as E, predict_day as P; "
            "E.SOURCE = P.HIST; E.run_walk()" % str(HERE))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=HERE)
    return r.stdout + (("\n[stderr]\n" + r.stderr[-1500:]) if r.returncode else "")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--flag", default="PREVDAY")
    FLAG = ap.parse_args().flag
    for lab, pv in (("基準（現行）", False), (f"{FLAG}=1 を追加", True)):
        print(f"\n==================== {lab} ====================", flush=True)
        print(one(pv), flush=True)
