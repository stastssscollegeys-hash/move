# -*- coding: utf-8 -*-
"""
weight_refresh.py — 当日発表の馬体重で、特徴量の「馬体重の列」だけを入れ直す（2026-10-14）
==========================================================================================
なぜ: ev_live.py --quick（本体 v5.1）は朝に作った特徴量（db/ev_cache/{日付}.pkl）にオッズだけ入れ替える。
      馬体重は発走の約1時間前に発表されるので、朝の特徴量では馬体重の列が全部0のまま本番の計算に使われていた
      （学習では確定の馬体重で効いているのに、本番では効いていない）。
使い方（ev_live.py の --quick の中で、liv に入れる直前）:
    import weight_refresh as WR
    wh = load_wh(date)                                    # {(場, R, 馬番): "484(+4)" or "506"}
    X = WR.refresh(c["X"][keep], c["key"], uma, wh, E.F)   # 馬体重の列だけ上書きしたコピーを返す
入れ直す列（ev_engine と同じ式）: 馬体重 増減（10kg単位）・10kg以上減・10kg以上増・470kgとの差（40kg単位）・439kg以下
"""
from __future__ import annotations
import re

import numpy as np


def cols(x, w: str | None, F):
    """1頭分の特徴量ベクトル x（F の並び）の馬体重の列を、馬体重の文字列 w から計算して上書きする"""
    ix = {n: i for i, n in enumerate(F)}
    if not w:
        return x
    m = re.search(r"\(([+-]?\d+)\)", w)
    if m and "馬体重 増減（10kg単位）" in ix:
        d = int(m.group(1))
        x[ix["馬体重 増減（10kg単位）"]] = max(-2.0, min(2.0, d / 10.0))
        x[ix["馬体重 10kg以上減"]], x[ix["馬体重 10kg以上増"]] = float(d <= -10), float(d >= 10)
    mb = re.match(r"(\d+)", w)
    if mb and "馬体重（470kgとの差・40kg単位）" in ix:
        bw = int(mb.group(1))
        x[ix["馬体重（470kgとの差・40kg単位）"]] = max(-2.0, min(2.0, (bw - 470) / 40.0))
        x[ix["馬体重 439kg以下"]] = float(bw <= 439)
    return x


def refresh(X, key, uma, wh: dict, F):
    """1レース分 X（頭数×特徴量）のコピーに、当日の馬体重を入れる。key=(日付, 場, R)。発表前の馬は朝の値のまま"""
    X = np.array(X, dtype=float, copy=True)
    for i, u in enumerate(uma):
        cols(X[i], wh.get((key[1], key[2], int(u))), F)
    return X


def coverage(liv, wh):
    """発表済みの馬の割合（ログ用）"""
    n = sum(len(r["uma"]) for r in liv)
    k = sum(1 for r in liv for u in r["uma"] if (r["key"][1], r["key"][2], int(u)) in wh)
    return k, n
