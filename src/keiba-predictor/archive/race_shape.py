# -*- coding: utf-8 -*-
"""
race_shape.py — レースの「形」から買い方を決める（2026-09-04）
================================================================
【なぜ作るか】
3連複を全レースに使い、指摘を受けてワイドを全レースに使った。中身は同じ誤り。
券種は集計値で一律に決めるものではなく、**そのレースの形と軸の性質**で決まる。

【形の判定軸】
  A. 指数の分布 … 何頭が勝ち負けできるか
     - 2頭が抜けて3番手以下が離れている → 2頭に集中（馬連・ワイド1点）
     - 1頭だけ抜けている → 軸1頭から流す（3連複軸1頭）
     - 上位が密集 → 軸が立たない。見送りか、人気薄1頭に張る
  B. 軸の性質 … 軸自身が儲けの源か、相手が源か
     - 軸が人気濃厚 → 軸で配当は付かない。相手（人気薄）で配当を作る
     - 軸が人気薄 → 軸自身が配当源。軸を絡めた点数を絞って厚く
  C. レースの荒れ度（過去データ）
     - 紐が荒れるレース → 相手を広げる
     - 堅いレース → 点数を絞る。あるいは買わない

【目標との対応】
  堅い 200%＋ / 中位 300〜500%＋ / 大穴 1000%＋
  → 必要配当から逆算して券種を選ぶ。ワイド1点で1000%は無理、
    3連複1点で200%を狙うのも噛み合わない。

使い方: python race_shape.py
"""
from __future__ import annotations
import json, io, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import style_correction

B = Path.home() / 'Desktop' / '競馬予想レポート'

# 過去10年から測ったレースの荒れ度（analyze_history.py の結果）
HIST = {
    '札幌2歳S':   dict(n=5,  top3_1_3=33, over7=27, win_pop='1人気40%・4人気以下3/5勝'),
    '京成杯AH':   dict(n=10, top3_1_3=43, over7=37, win_pop='1人気50%・13人気/14人気の激走あり'),
    '紫苑S':      dict(n=10, top3_1_3=50, over7=17, win_pop='1人気30%・勝ち馬単勝中央値4.5倍'),
    'セントウルS': dict(n=6,  top3_1_3=56, over7=28, win_pop='1人気67%・14人気112倍の年も'),
}

TARGET = [('20260905', '札幌', 11, '札幌2歳S'),
          ('20260905', '中山', 11, '京成杯AH'),
          ('20260906', '中山', 11, '紫苑S'),
          ('20260906', '阪神', 11, 'セントウルS')]


def shape_of(idx):
    """指数分布から形を判定する。idx は降順の総合指数リスト"""
    g12 = idx[0] - idx[1]
    g23 = idx[1] - idx[2]
    g35 = idx[2] - idx[4] if len(idx) > 4 else 0
    # 上位何頭が「1位から5ポイント以内」に入っているか
    close = sum(1 for x in idx if idx[0] - x <= 5)
    if g12 >= 8:
        kind = '1頭抜け'
    elif g12 < 2 and g23 >= 5:
        kind = '2頭抜け'
    elif close >= 4:
        kind = '密集（軸が立たない）'
    elif close == 3:
        kind = '3頭が拮抗'
    else:
        kind = '中間'
    return kind, g12, g23, close


def main():
    recs = json.load(open(sorted(B.glob('**/週末ビッグデータ_20260905*_records.json'))[-1],
                          encoding='utf-8'))['records']
    by = {}
    for r in recs:
        by.setdefault((r['date'], r['競馬場'], int(r['R'])), []).append(r)

    print("=" * 100)
    print("■ レースの形から買い方を決め直す")
    print("=" * 100)

    for date, ven, rno, name in TARGET:
        rs = by[(date, ven, rno)]
        style_correction.apply_style_correction(rs, enabled=True)
        rs.sort(key=lambda r: -(r.get('総合指数') or 0))
        idx = [r.get('総合指数') or 0 for r in rs]
        kind, g12, g23, close = shape_of(idx)
        h = HIST[name]

        print()
        print("─" * 100)
        print(f"■ {name}（{len(rs)}頭）")
        print("─" * 100)
        print(f"  指数: " + " / ".join(f"{x:.1f}" for x in idx[:6]))
        print(f"  形  : {kind}　1-2位差{g12:.1f} 2-3位差{g23:.1f} "
              f"／1位から5pt以内に{close}頭")
        print(f"  荒れ: 過去{h['n']}年 3着内の1-3人気{h['top3_1_3']}% "
              f"／7人気以下{h['over7']}%　{h['win_pop']}")
        print(f"  上位: " + " / ".join(
            f"{r.get('AI印') or '　'}{r.get('馬番')}{str(r.get('馬名',''))[:8]}"
            for r in rs[:5]))

        # ── 形と荒れ度から推奨構造を出す ──
        rec = []
        if kind == '2頭抜け':
            rec.append("2頭が抜けて3番手以下が離れている。3着付けは不要。"
                       "**馬連1点に集中**が最も効率的（当たれば厚い）")
            rec.append("ワイドは的中しても配当が伸びない。目標200%には馬連が要る")
        elif kind == '1頭抜け':
            if h['over7'] >= 35:
                rec.append("軸1頭が抜けているが、紐が荒れるレース。"
                           "**3連複の軸1頭流しで相手を広く**。人気薄を必ず入れる")
            else:
                rec.append("軸1頭が抜けていて紐も堅い。**馬連・ワイドを絞る**")
        elif kind == '3頭が拮抗':
            rec.append("3頭が拮抗。どれが勝つか読めないが3着内には入りやすい。"
                       "**3頭BOXの3連複1点＋ワイド**が噛み合う")
        elif kind == '密集（軸が立たない）':
            rec.append("上位が密集して軸が立たない。**原則は見送り**。"
                       "買うなら人気薄1頭に絞って単勝かワイド")
        else:
            rec.append("中間的な形。軸の人気次第で判断")
        for x in rec:
            print(f"  → {x}")


if __name__ == '__main__':
    main()
