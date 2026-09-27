# -*- coding: utf-8 -*-
"""
payout_correction.py — 想定オッズの実配当補正レイヤー（v6.1 / 2026-09-02）
==========================================================================
【何を直すか】
買い目の期待値は「想定オッズ = 控除率 / Harville確率」で計算してきたが、
確定払戻1,044レースと突き合わせた結果、この想定オッズには配当帯に依存した
系統誤差があることが分かった（payout_validate.py）。

  実配当 / Harville想定オッズ の中央値（n=1,041レース）

    券種      ~5倍   5-15倍  15-50倍  50-200倍  200倍~
    単勝      0.99    0.99    0.99     0.99       -     ← 対照（構造上フラット）
    馬連      1.20    1.09    0.92     0.78     0.68
    ワイド    1.28    1.01    0.77     0.63       -
    馬単      1.13    1.12    0.99     0.87     0.70
    3連複     1.53    1.43    1.03     0.86     0.54
    3連単       -     1.23    1.27     1.06     0.74

つまり **高配当ほど実際には付かない**。モデルが「期待値150%」と判定した
200倍超の3連複は、実際には 150% x 0.54 = 81% しかない。
逆に ◎○▲ の安い3連複は 43〜53% 過小評価していた。

これは競馬統計で知られる Harville 式のバイアス（人気馬の連対確率を過大に、
人気薄を過小に見積もる）と方向が一致しており、理論的裏付けもある。

【頑健性（3点セット・全通過）】
  ① 期間3分割   … 3連複200倍~ は 0.53/0.55/0.54、ワイド50-200倍は 0.66/0.62/0.62
  ② 上位1%除外  … 全項目 ±0.00〜0.02（中央値ベースのため大穴依存ゼロ）
  ③ 対照実験     … 単勝は全帯 0.99 で完全フラット。測定系に帯依存の歪みが無い証拠

【前提・適用条件】
補正値は「市場確率 q を確定単勝オッズから作った場合」で較正している。
したがって **実オッズを渡している時（--odds-file 指定時）に最も正確**。
実オッズなしの推定 q では効きが鈍る可能性があるが、方向は同じなので適用してよい。

【設計方針】
gen_kaime_v5.py の est_odds() から呼ぶだけの後段レイヤー。
ENABLED = False で従来挙動に即座に戻せる。

【更新方法】
開催が進んだら payout_validate.py を再実行し、出力された
daily_pdca/db/payout_correction.json の値で下の COEF を更新する。
"""
from __future__ import annotations
import json
from pathlib import Path

ENABLED = True    # False にすると補正を止められる（切り戻し用）

# 補正値の下限・上限（外挿の暴走防止）
CLAMP = (0.50, 1.60)

# 帯の代表値（幾何中央）と補正係数。想定オッズの対数に対して線形補間する。
# 数値の出所: payout_validate.py（1,044レース・2026/5/16〜8/30）
_X = [3.0, 8.66, 27.4, 100.0, 400.0]      # ~5 / 5-15 / 15-50 / 50-200 / 200~

COEF = {
    '単勝':  [0.99, 0.99, 0.99, 0.99, 0.99],
    '複勝':  [1.17, 0.75, None, None, None],   # 15倍超はサンプル不足→端で頭打ち
    '馬連':  [1.20, 1.09, 0.92, 0.78, 0.68],
    'ワイド': [1.28, 1.01, 0.77, 0.63, None],
    '馬単':  [1.13, 1.12, 0.99, 0.87, 0.70],
    '3連複': [1.53, 1.43, 1.03, 0.86, 0.54],
    '3連単': [None, 1.23, 1.27, 1.06, 0.74],
}


def _log(x: float) -> float:
    import math
    return math.log(max(x, 1.01))


def factor(btype: str, est_odds: float) -> float:
    """券種と想定オッズから補正係数を返す（対数線形補間）。"""
    tbl = COEF.get(btype)
    if not tbl:
        return 1.0
    pts = [(x, c) for x, c in zip(_X, tbl) if c is not None]
    if not pts:
        return 1.0
    if len(pts) == 1:
        return pts[0][1]
    lx = _log(est_odds)
    # 端は頭打ち（外挿しない）
    if lx <= _log(pts[0][0]):
        return pts[0][1]
    if lx >= _log(pts[-1][0]):
        return pts[-1][1]
    for (x0, c0), (x1, c1) in zip(pts, pts[1:]):
        if _log(x0) <= lx <= _log(x1):
            t = (lx - _log(x0)) / (_log(x1) - _log(x0))
            return c0 + t * (c1 - c0)
    return pts[-1][1]


def apply(btype: str, est_odds: float, enabled: bool | None = None) -> float:
    """想定オッズに実配当補正を掛けて返す。

    gen_kaime_v5.est_odds() の戻り値をこの関数に通すだけで、
    期待値計算が実配当ベースになる。
    """
    if enabled is None:
        enabled = ENABLED
    if not enabled:
        return est_odds
    f = min(CLAMP[1], max(CLAMP[0], factor(btype, est_odds)))
    return max(1.1, est_odds * f)


def load_from_json(path: str | Path | None = None) -> dict:
    """payout_validate.py が書き出した係数JSONを読み込んで COEF 形式に変換する。
    （開催が進んだあとの更新作業用。読み込んだ辞書を返すだけで自動反映はしない）"""
    if path is None:
        path = (Path.home() / 'Desktop' / '競馬予想レポート' /
                'daily_pdca' / 'db' / 'payout_correction.json')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    bands = [b[0] for b in data['bands']]
    out: dict[str, list] = {}
    for key, v in data['coef'].items():
        t, b = key.split('|')
        out.setdefault(t, [None] * len(bands))[bands.index(b)] = v
    return out


def describe() -> str:
    """レポートへの注記用の1行説明。"""
    return ("実配当補正 v6.1（1,044レース較正: 3連複200倍~ x0.54 / ワイド50-200倍 x0.63 / "
            "◎○▲級の安い3連複 x1.43-1.53）")


if __name__ == '__main__':
    print(describe())
    print()
    print(f"{'券種':6s}" + "".join(f"{x:>10.0f}倍" for x in (2, 5, 10, 30, 80, 200, 500)))
    print("-" * 84)
    for t in COEF:
        print(f"{t:6s}" + "".join(f"{factor(t, o):>11.2f}" for o in (2, 5, 10, 30, 80, 200, 500)))
