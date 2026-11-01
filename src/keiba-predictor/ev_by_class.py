# -*- coding: utf-8 -*-
"""
ev_by_class.py — 市場の効率はクラス（新馬／未勝利／1勝／2勝／3勝／オープン／重賞）で違うか、モデル÷市場≧閾値の単勝はどのクラスで取れるか（2026-11-01新規）
==============================================================================================================
・対象: ev_engine の年ごと前向き予測（2019〜2026・25,440R）の p（モデル勝率）と q（市場勝率）、確定単勝オッズ
・見る数字: ①クラス別に全馬100円ずつ買った単勝回収率（市場そのものの効率）
            ②比 p/q ≧ 1.2 / 1.3 の馬を100円ずつ買った回収率［ブートストラップ95%区間］、年別の安定
            ③上位10件の高配当を除いた回収率（少数の大当たり依存の確認）
・🔴クラスで分けるほど標本が減り偶然が混ざる（クラス7×閾値2×年8）。区間が100%をまたぐものは「傾向」止まりで、台帳（B1）で前向きに確かめる
"""
from __future__ import annotations
import json, pickle, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import combo_backtest as C
import ev_engine as E

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
CACHE = DB / "ev_by_class.pkl"


def klass(r):
    c = (r.get("条件") or "") + (r.get("レース名") or "")
    for k, lab in (("新馬", "新馬"), ("未勝利", "未勝利"), ("1勝", "1勝"), ("500万", "1勝"), ("2勝", "2勝"), ("1000万", "2勝"),
                   ("3勝", "3勝"), ("1600万", "3勝"), ("G1", "重賞"), ("G2", "重賞"), ("G3", "重賞"), ("GⅠ", "重賞"), ("GⅡ", "重賞"), ("GⅢ", "重賞"),
                   ("オープン", "OP"), ("OP", "OP"), ("リステッド", "OP")):
        if k in c:
            return lab
    return "他"


def build():
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    cls = {}
    for f in sorted((C.SRC).glob("results_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            k = (r["date"], r["競馬場"], int(float(r["R"])))
            if k not in cls:
                cls[k] = klass(r)
    preds = {tuple(p["key"]): p for p in C.predictions()}
    E.SOURCE = C.SRC
    races, _ = E.build()
    out = []
    for r in races:
        k = tuple(r["key"])
        if k not in preds:
            continue
        p = preds[k]
        if len(p["uma"]) != len(r["fins"]):
            continue
        out.append(dict(key=k, cls=cls.get(k, "他"), p=np.asarray(p["p"], float), q=np.asarray(p["q"], float),
                        odds=np.asarray(r["odds"], float), fins=np.asarray(r["fins"])))
    CACHE.write_bytes(pickle.dumps(out))
    return out


def stats(rows):
    """rows: [(払戻倍率(外れ0), 年)] → 回収率, 区間, 上位10除き"""
    x = np.array([a for a, _ in rows])
    if len(x) == 0:
        return None
    rng = np.random.default_rng(1)
    bs = [rng.choice(x, len(x)).mean() for _ in range(1500)]
    top10 = np.sort(x)[:-10].mean() if len(x) > 10 else float("nan")
    return x.mean() * 100, np.percentile(bs, 2.5) * 100, np.percentile(bs, 97.5) * 100, top10 * 100


def main():
    rs = build()
    order = ["新馬", "未勝利", "1勝", "2勝", "3勝", "OP", "重賞", "他"]
    print(f"{len(rs):,}R／クラス別レース数: " + " ".join(f"{k}{sum(r['cls'] == k for r in rs)}" for k in order))
    print("\n① 全馬100円ずつ買った単勝回収率（市場の効率）")
    for k in order:
        rows = [(float(o) if f == 1 else 0.0, r["key"][0][:4]) for r in rs if r["cls"] == k for o, f in zip(r["odds"], r["fins"])]
        s = stats(rows)
        if s:
            print(f"  {k:<4} n={len(rows):>7,} 回収 {s[0]:5.1f}% ［{s[1]:.1f}〜{s[2]:.1f}］")
    for th in (1.2, 1.3):
        print(f"\n② 比 p/q ≧ {th} の単勝（モデルが市場より高く見る馬）")
        for k in order + ["全体"]:
            rows = []
            for r in rs:
                if k != "全体" and r["cls"] != k:
                    continue
                pn, qn = r["p"] / r["p"].sum(), r["q"] / r["q"].sum()
                for i in range(len(pn)):
                    if qn[i] > 0 and pn[i] / qn[i] >= th:
                        rows.append((float(r["odds"][i]) if r["fins"][i] == 1 else 0.0, r["key"][0][:4]))
            s = stats(rows)
            if s and len(rows) >= 100:
                yrs = {}
                for a, y in rows:
                    yrs.setdefault(y, []).append(a)
                ys = " ".join(f"{np.mean(v) * 100:.0f}" for _, v in sorted(yrs.items()))
                print(f"  {k:<4} n={len(rows):>6,} 回収 {s[0]:5.1f}% ［{s[1]:.1f}〜{s[2]:.1f}］ 上位10除き {s[3]:5.1f}% ｜年別 {ys}")


if __name__ == "__main__":
    main()
