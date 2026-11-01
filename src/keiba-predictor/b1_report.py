# -*- coding: utf-8 -*-
"""
b1_report.py — 前向き台帳 B1（単勝・市場＋木・期待値≧1.0）の累計を、期待値の水準別・オッズ帯別・クラス別に割って見る（2026-11-01新規）
===================================================================================================================
根拠: benter_probs.pkl（20年・確定オッズ）で B1 の期待値の閾値を上げるほど回収率が上がる（≧1.0:101.0% → ≧1.1:107.7% → ≧1.2:115.3% → ≧1.3:122.4%）。
前半(2010-17)・後半(2018-26)の両方で同じ向き。ただし上位10件の高配当を除くと閾値≧1.2で106%、直近5年は86%まで落ちる＝少数の大当たり依存。
そこで B1 のルール自体は動かさず（事前登録）、台帳の ev_now を使って「期待値≧1.2の部分集合」を並行で集計する（新しい台帳は作らない）。
使い方: python b1_report.py
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
LED = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "ledger_b1.json"
es = [e for e in json.loads(LED.read_text(encoding="utf-8")) if e.get("settled")]


def line(label, sub):
    if not sub:
        print(f"  {label:<18} 0点"); return
    st = sum(float(e["stake"]) for e in sub); rt = sum(float(e.get("payout") or 0) for e in sub)
    hit = sum(1 for e in sub if float(e.get("payout") or 0) > 0)
    print(f"  {label:<18} {len(sub):>4}点 賭け{int(st):>7,}円 払戻{int(rt):>7,}円 回収{rt / st * 100:6.1f}%  的中{hit}")


print(f"B1 精算済み {len(es)}点（{min(e['date'] for e in es)}〜{max(e['date'] for e in es)}）")
line("全体（EV≧1.0）", es)
for thr in (1.1, 1.2, 1.3):
    line(f"EV≧{thr}", [e for e in es if float(e.get("ev_now") or 0) >= thr])
for lo, hi in ((1, 6), (6, 10), (10, 20), (20, 40), (40, 9999)):
    line(f"{lo}〜{hi}倍", [e for e in es if lo <= float(e.get("odds_now") or 0) < hi])
