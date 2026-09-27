# -*- coding: utf-8 -*-
"""
factor_ablation.py — 1因子ずつ外して、印が良くなるかを直接試す
==========================================================================
なぜこの形なのか
----------------
因子監査v2(factor_audit_v2.py)は「同じ人気帯の中で差がつくか」を測ったが、
7因子（厩舎・枠・馬番・距離・斤量・性別・年齢＝重み35%）は
**期間によって符号が反転**して判定不能だった。

判別力の指標をこねるより、**外したら◎の質が上がるのか**を直接測るほうが速く、
かつ実際に運用で効く値そのものを見ている。F01ではこの方法で答えが出た
（0.15→0で ◎3着内率 45.5%→50.4%、95%区間[+1.3〜+8.8]pt）。

⚠ この探索は17回の比較なので**多重比較になる**。
  人気帯スキャンで300帯を検定して2帯生き残り、hold-outで両方棄却された教訓から、
  ①ブートストラップ ②時期5分割 の両方を通ったものだけを採用する。
  「改善確率が高い順に上から採用」は**やってはいけない**。

使い方
------
    python factor_ablation.py            # 全因子を1つずつ外して比較
    python factor_ablation.py --boot 2000
"""
from __future__ import annotations
import argparse, random, sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import weight_experiment as W

# F01は既に0にしたので、現行の重みを基準にする
CURRENT = {k: v for k, v in W.BASE.items() if k != "F01_後3F"}
CURRENT = W.norm(CURRENT)


def hits_per_race(races: list, w: dict) -> list[int]:
    """
    その重みで各レースの◎が3着内に来たか（1/0）を1回だけ計算する。

    ⚠ 高速化の要点: ブートストラップは**レースを再抽出するだけ**なので、
      並べ替えをやり直す必要がない。ここで1回ランク付けして0/1の列にしておけば、
      以降のリサンプルは足し算だけで済む（16因子×800回の再ソートが消える）。
    """
    out = []
    for rc in races:
        best = max(rc["rows"], key=lambda r: W.score(r, w, False))
        out.append(1 if best["top3"] else 0)
    return out


def rate(h: list[int]) -> float:
    return sum(h) / len(h) if h else 0.0


def main(boot: int) -> None:
    races = W.load()
    base_h = hits_per_race(races, CURRENT)
    base = rate(base_h)
    print(f"═══ 1因子ずつ外した効果（{len(races)}レース・F01除去後を基準）═══\n")
    print(f"　基準（現行）の ◎3着内率 = {base*100:.1f}%")
    print("　外して**上がる**なら、その因子は害。下がるなら効いている。\n")
    print("　⚠ 17回の比較＝多重比較。ブートストラップと時期5分割の**両方**を")
    print("　　通ったものだけ採用する（上位を機械的に採るのは禁止）\n")

    n = len(races)
    k = n // 5
    bounds = [(i*k, (i+1)*k if i < 4 else n) for i in range(5)]

    print(f"{'外した因子':<12}{'重み':>6}{'3着内率':>9}{'差':>8}{'95%区間':>18}"
          f"{'改善確率':>9}{'5分割':>7}")
    print("─" * 72)

    rows = []
    for k in CURRENT:
        w = W.norm({a: b for a, b in CURRENT.items() if a != k})
        h = hits_per_race(races, w)
        v = rate(h)
        d = v - base

        # レース単位の差分（+1 / 0 / -1）を並べ、これをリサンプルするだけでよい
        delta = [h[i] - base_h[i] for i in range(n)]
        random.seed(11)
        diffs = sorted(sum(random.choices(delta, k=n)) / n for _ in range(boot))
        lo, hi = diffs[int(boot*.025)], diffs[int(boot*.975)]
        p = sum(1 for x in diffs if x > 0) / boot
        wins = sum(1 for a, b in bounds if sum(h[a:b]) > sum(base_h[a:b]))

        ok = lo > 0 and wins >= 4          # 両方を通ったものだけ
        mark = "  ★採用候補" if ok else ""
        rows.append((k, d, lo, hi, p, wins, ok))
        print(f"{k:<12}{CURRENT[k]*100:>5.0f}%{v*100:>8.1f}%{d*100:>+7.1f}pt"
              f"{f'[{lo*100:+.1f}〜{hi*100:+.1f}]':>18}{p*100:>8.1f}%{wins:>5}/5{mark}")

    keep = [r for r in rows if r[6]]
    print(f"\n═══ 判定 ═══\n")
    if not keep:
        print("　✅ **両方の関門を通った因子は無い。**")
        print("　　 つまり現行の重み構成から、これ以上『外して良くなる』因子は見つからない。")
        print("　　 監査で怪しく見えた7因子も、外して改善するとは言えない＝そのまま残す。")
        print("　　 → 指数の改善は**既存因子の取捨選択では頭打ち**。新しい情報源が要る。")
    else:
        for k, d, lo, hi, p, wins, _ in keep:
            print(f"　★ {k}: 外すと {d*100:+.1f}pt（区間[{lo*100:+.1f}〜{hi*100:+.1f}]・"
                  f"5分割{wins}/5）")
        print("\n　⚠ 採用前に、これらを同時に外した場合も測ること（単独と挙動が違う）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=800)
    main(ap.parse_args().boot)
