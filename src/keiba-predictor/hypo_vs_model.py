# -*- coding: utf-8 -*-
"""
hypo_vs_model.py — hypo_audit の仮説（H1〜H3b）は、確率モデル p（ev_engine 前向き予測）に無い情報か（2026-11-01新規）
人気との比較ではなく、モデルの勝率 p・市場の勝率 q との比較: 該当馬の実際の勝ち数 vs Σp・Σq（二項分散で z）
対象は 2019年〜の前向き予測 25,440R。ev_engine は前走4角の位置・上がり順位を特徴量に持つので、H3 は既に織り込み済みのはず
"""
import pickle, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import mc_scenario_test as T

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
flags = pickle.loads((DB / "hypo_flags.pkl").read_bytes())
rs = T.build_slim()
names = ("H1 前走ハイペース逃げ失速", "H2 前走 上がり上位で凡走", "H3 前走 後方から上がり最速級", "H3b 前走 先頭付近で3着内")
acc = {i: dict(n=0, win=0, sp=0.0, sq=0.0, var=0.0) for i in range(4)}
for r in rs:
    d, v, R = r["key"]
    p = r["p"] / r["p"].sum(); q = r["q"] / r["q"].sum()
    win = r["fins"] == 1
    for j, u in enumerate(r["uma"]):
        fl = flags.get((d, v, int(R), int(u)))
        if not fl:
            continue
        for i in range(4):
            if fl[i]:
                a = acc[i]; a["n"] += 1; a["win"] += int(win[j]); a["sp"] += p[j]; a["sq"] += q[j]; a["var"] += p[j] * (1 - p[j])
for i, nm in enumerate(names):
    a = acc[i]
    if a["n"] < 200:
        print(f"{nm}: n={a['n']}（少なすぎ）"); continue
    z = (a["win"] - a["sp"]) / np.sqrt(a["var"])
    print(f"{nm}: n={a['n']:>6} 勝ち{a['win']:>5} ／ モデル期待{a['sp']:7.1f}（z={z:+.2f}）／ 市場期待{a['sq']:7.1f}")
