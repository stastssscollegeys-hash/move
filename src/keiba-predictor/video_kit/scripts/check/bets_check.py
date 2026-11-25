"""予算1万円の買い目を確かめて、画面と台本に写す表を出す（2026-11-20）。

使い方: python scripts/check/bets_check.py <bets.json>
  ふつうは bets_allocate.py が書き出した JSON を渡す。手で配ったときも同じ形（各行に type・combo・yen。odds があれば払い戻しも出す）。
確かめること: 合計が budget（既定 10000円）ちょうど／1点100円以上・100円単位／券種ごとの馬の数／同じ組み合わせの重複。
NG が1つでもあれば終了コード1。
"""
import json
import sys
from pathlib import Path

SIZE = {"単勝": 1, "複勝": 1, "枠連": 2, "馬連": 2, "ワイド": 2, "馬単": 2, "3連複": 3, "3連単": 3}
ORDERED = {"馬単", "3連単"}   # 順番に意味がある券種


def main(path: str) -> int:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    budget = int(d.get("budget", 10000))
    bets = d.get("bets", [])
    ng, seen, groups = [], set(), {}
    for i, b in enumerate(bets, 1):
        t, combo, yen = b.get("type"), b.get("combo", []), b.get("yen", 0)
        if t not in SIZE:
            ng.append(f"{i}行目: 券種「{t}」が分からない（{'・'.join(SIZE)}）")
            continue
        if len(combo) != SIZE[t]:
            ng.append(f"{i}行目: {t}は馬（枠）が{SIZE[t]}つ。いまは{len(combo)}つ")
        if len(set(combo)) != len(combo) and t != "枠連":
            ng.append(f"{i}行目: 同じ馬番が2回入っている {combo}")
        if not isinstance(yen, int) or yen < 100 or yen % 100:
            ng.append(f"{i}行目: 金額 {yen}円＝1点100円以上・100円単位にする")
        key = (t, tuple(combo) if t in ORDERED else tuple(sorted(combo)))
        if key in seen:
            ng.append(f"{i}行目: {t} {combo} が重複している")
        seen.add(key)
        groups.setdefault(t, []).append(b)
    total = sum(b.get("yen", 0) for b in bets if isinstance(b.get("yen"), int))
    if total != budget:
        ng.append(f"合計 {total:,}円＝予算 {budget:,}円と合わない（差 {budget - total:+,}円）")

    print(f"■ {d.get('race', '')}　予算 {budget:,}円　{len(bets)}点")
    if d.get("why"):
        print(f"  配分の考え方: {d['why']}")
    sep = "→" 
    for t, rows in groups.items():
        sub = sum(r.get("yen", 0) for r in rows)
        print(f"\n{t}　{len(rows)}点　{sub:,}円")
        for r in rows:
            c = (sep if t in ORDERED else "－").join(str(x) for x in r.get("combo", []))
            line = f"  {c:<12} {r.get('yen', 0):>6,}円"
            if r.get("odds"):
                line += f"　オッズ {r['odds']}倍 → 当たれば {int(r['yen'] * r['odds']):,}円"
            print(line)
    print(f"\n合計 {total:,}円")
    if d.get("odds_asof") and any(b.get("odds") for b in bets):
        print(f"※ オッズは {d['odds_asof']} 時点")
    if ng:
        print("\n✖ NG")
        for m in ng:
            print("  - " + m)
        return 1
    print("\n✅ OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
