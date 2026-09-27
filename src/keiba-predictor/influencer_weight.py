# -*- coding: utf-8 -*-
"""
influencer_weight.py — インフルエンサーの重みを直近成績から動的に決める（2026-09-27新規）
============================================================================================
ユーザー指示（2026-09-27）:
  「2人のインフルエンサーの予想はあくまで情報の一部。重視しすぎない。他と同じ扱いにする。
    ただし最近当たっている人はちょっとだけ比重を重く、流れが悪い人はちょっと軽くしてよい」

これまでの重み（アジフライ×1.5 等）は2026-08-18に「仮」で決めて「4週で確定」としたまま未確定だった。
本モジュールは台帳 `influencer_ledger.json` の**実績だけ**から重みを出す。

方式
----
  基準 = そのソースが本命に挙げた馬の3着内率
  比較対象 = 同じ台帳の全ソース平均（＝「普通」の水準）
  重み = 1.0 + 0.6 × (そのソースの3着内率 − 全体平均) × 信頼度
  信頼度 = n / (n + 10)  … サンプルが少ないほど1.0（＝中立）へ縮める
  重みの上下限 = 0.8 〜 1.3（「ちょっとだけ」に留める。1.5のような大きな差は付けない）
  直近を重く見るため、既定では**直近8週分**だけを使う

使い方
------
  python influencer_weight.py                # 現在の重み一覧
  python influencer_weight.py --weeks 12     # 集計期間を変える
  from influencer_weight import weights       # {ソース名: 重み}
"""
from __future__ import annotations
import argparse, collections, datetime, json, sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
LEDGER = DB / "influencer_ledger.json"
LO, HI = 0.8, 1.3          # 重みの上下限（ちょっとだけ動かす）
K = 0.6                    # 差をどれだけ重みに反映するか
SHRINK = 10                # この件数で信頼度が50%になる


def load(weeks: int = 8):
    if not LEDGER.exists():
        return []
    rows = json.loads(LEDGER.read_text(encoding="utf-8"))
    if not rows:
        return []
    last = max(r["date"] for r in rows if r.get("date"))
    d = datetime.date(int(last[:4]), int(last[4:6]), int(last[6:]))
    cut = (d - datetime.timedelta(weeks=weeks)).strftime("%Y%m%d")
    return [r for r in rows if r.get("date", "") >= cut]


def weights(weeks: int = 8, kind: str = "honmei"):
    """{ソース名: 重み} を返す。実績が無いソースは 1.0（中立）"""
    rows = [r for r in load(weeks) if r.get("kind") == kind and r.get("finish")]
    if not rows:
        return {}, 0.0, {}
    agg = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        e = agg[r["source"]]
        e[0] += 1
        e[1] += 1 if r["finish"] <= 3 else 0
    base = sum(e[1] for e in agg.values()) / sum(e[0] for e in agg.values())
    out, detail = {}, {}
    for src, (n, h) in agg.items():
        rate = h / n
        conf = n / (n + SHRINK)
        w = 1.0 + K * (rate - base) * conf
        w = round(max(LO, min(HI, w)), 2)
        out[src] = w
        detail[src] = dict(n=n, hit=h, rate=round(rate, 3), conf=round(conf, 2), weight=w)
    return out, base, detail


def weight_of(src: str, table: dict) -> float:
    """部分一致で引く。未知のソースは 1.0（中立）"""
    for k, w in table.items():
        if k in src or src in k:
            return w
    return 1.0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=8)
    a = ap.parse_args()
    tbl, base, detail = weights(a.weeks)
    print(f"直近{a.weeks}週の台帳から算出（本命シグナルの3着内率ベース）")
    print(f"全ソース平均の3着内率 = {base*100:.1f}%　これを1.0とする\n")
    print(f"{'ソース':<28}{'本命':>5}{'3着内':>6}{'率':>8}{'信頼度':>8}{'重み':>7}  流れ")
    for src, d in sorted(detail.items(), key=lambda kv: -kv[1]["weight"]):
        mark = "↑やや重く" if d["weight"] > 1.02 else ("↓やや軽く" if d["weight"] < 0.98 else "＝中立")
        print(f"{src[:27]:<28}{d['n']:>5}{d['hit']:>6}{d['rate']*100:>7.1f}%{d['conf']:>8.2f}{d['weight']:>7.2f}  {mark}")
    print(f"\n※ 上下限 {LO}〜{HI}。サンプルが少ないソースは自動的に1.0へ縮む（n={SHRINK}で信頼度50%）")
    print("※ 台帳に実績が無いソース（ウマキング・カリスマ予想など新規）は 1.0＝中立で始まる")
