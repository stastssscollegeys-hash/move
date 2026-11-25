"""予算1万円を、決めた買い目にどう配るかを計算する（2026-11-20）。

動画を作るときに使う。印と買い目（券種・組み合わせ・点数）はチームが決めたもの。この道具は「1点いくらずつ買うか」だけを決める。

使い方:
  python scripts/check/bets_allocate.py <bets.json> [--out <配分を書いた.json>]
  → 配分を書いた JSON を出し、そのまま bets_check.py で確かめる

入れるもの（形は templates/final/bets_alloc_example.json）:
  bets[]      : type・combo・odds（その組み合わせのオッズ。何時時点かを odds_asof に書く）。yen は書かない
  win_prob    : {"馬番": 勝つ見込み(%)} 予想AIの出力。書いていない馬は、残りを field_size の残りの頭数で等分する
  field_size  : 出走頭数
  budget      : 既定 10000

決め方（収支がよくなるように）:
  ① 勝つ見込みから、各組み合わせが当たる見込みを出す（Harville の式＝1着が決まったら残りの馬で同じ比で2着を決める）
  ② どれが当たっても払い戻しが1万円を下回らない（トリガミにならない）最低の金額を先に置く
  ③ 残りを当たる見込みの大きさに比例して足す（全部使い切るときの最適な賭け方＝ケリーの考え方）
  ②が予算に収まらないときは②を外し、③だけで配って、トリガミになる組み合わせを知らせる
  金額は100円単位。合計はちょうど予算にそろえる。
"""
import argparse
import itertools
import json
import math
from pathlib import Path

ORDERED = {"馬単", "3連単"}


def probs(d):
    n = int(d.get("field_size", 0))
    wp = {int(k): float(v) / 100 for k, v in d.get("win_prob", {}).items()}
    if not n or n < len(wp):
        raise SystemExit("field_size（出走頭数）を書いてください")
    rest = [u for u in range(1, n + 1) if u not in wp]
    left = max(0.0, 1 - sum(wp.values()))
    for u in rest:
        wp[u] = left / len(rest) if rest else 0
    s = sum(wp.values())
    return {u: p / s for u, p in wp.items()}


def top3(p):
    """1〜3着の並びごとの見込み（Harville）"""
    out = {}
    us = list(p)
    for a in us:
        pa = p[a]
        ra = 1 - pa
        for b in us:
            if b == a or ra <= 0:
                continue
            pb = p[b] / ra
            rb = ra - p[b]
            for c in us:
                if c in (a, b) or rb <= 0:
                    continue
                out[(a, b, c)] = pa * pb * p[c] / rb
    return out


def hit_prob(t, combo, P3):
    c = list(combo)
    tot = 0.0
    for (a, b, cc), q in P3.items():
        if t == "単勝":
            ok = a == c[0]
        elif t == "複勝":
            ok = c[0] in (a, b, cc)
        elif t == "馬連":
            ok = {a, b} == set(c)
        elif t == "馬単":
            ok = (a, b) == tuple(c)
        elif t == "ワイド":
            ok = set(c) <= {a, b, cc}
        elif t == "3連複":
            ok = {a, b, cc} == set(c)
        elif t == "3連単":
            ok = (a, b, cc) == tuple(c)
        else:
            raise SystemExit(f"券種「{t}」はこの道具では扱えません（枠連は外して手で配る）")
        if ok:
            tot += q
    return tot


def to_100(raw, budget):
    """比例の金額を100円単位にし、合計をちょうど予算にする（端数の大きい順に100円ずつ足す）"""
    units = budget // 100
    fl = [math.floor(x / 100) for x in raw]
    fl = [max(1, f) for f in fl]
    while sum(fl) > units:
        i = max(range(len(fl)), key=lambda k: fl[k] - raw[k] / 100)
        if fl[i] <= 1:
            break
        fl[i] -= 1
    order = sorted(range(len(raw)), key=lambda k: raw[k] / 100 - fl[k], reverse=True)
    k = 0
    while sum(fl) < units:
        fl[order[k % len(order)]] += 1
        k += 1
    return [f * 100 for f in fl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bets")
    ap.add_argument("--out")
    a = ap.parse_args()
    d = json.loads(Path(a.bets).read_text(encoding="utf-8"))
    budget = int(d.get("budget", 10000))
    bets = d["bets"]
    if any(not b.get("odds") for b in bets):
        raise SystemExit("odds が無い行があります。何時時点のオッズかを odds_asof に書き、全部の行に odds を入れてください")
    P3 = top3(probs(d))
    ps = [hit_prob(b["type"], b["combo"], P3) for b in bets]
    mins = [math.ceil(budget / b["odds"] / 100) * 100 for b in bets]   # 当たれば予算以上が戻る最低の金額
    if sum(mins) <= budget:
        rest = budget - sum(mins)
        sp = sum(ps) or 1
        raw = [m + rest * p / sp for m, p in zip(mins, ps)]
        way = "トリガミにならない最低の金額を置き、残りを当たる見込みに比例して足した"
    else:
        sp = sum(ps) or 1
        raw = [budget * p / sp for p in ps]
        way = f"全部をトリガミなしにすると {sum(mins):,}円 要り、予算を超えるので、当たる見込みに比例して配った"
    yen = to_100(raw, budget)
    for b, y, p in zip(bets, yen, ps):
        b["yen"] = y
        b["hit_prob"] = round(p * 100, 1)
    d["alloc_note"] = way

    print(f"■ {d.get('race', '')}　予算 {budget:,}円　{len(bets)}点　オッズ {d.get('odds_asof', '（時点の記入なし）')}")
    print(f"  {way}")
    ev = 0.0
    for b in bets:
        sep = "→" if b["type"] in ORDERED else "－"
        ret = int(b["yen"] * b["odds"])
        ev += b["hit_prob"] / 100 * ret
        flag = "  ⚠ 当たってもトリガミ" if ret < budget else ""
        print(f"  {b['type']:<4} {sep.join(map(str, b['combo'])):<10} {b['yen']:>6,}円  オッズ {b['odds']:>6}倍  当たる見込み {b['hit_prob']:>5}%  当たれば {ret:,}円{flag}")
    print(f"  払い戻しの見込み（当たる見込み×払い戻しの合計）: {int(ev):,}円（予算 {budget:,}円）")
    print("  ※ 見込みは予想AIの勝つ見込みから出した目安。払い戻しはオッズの時点のもので、当日は変わる")
    if a.out:
        Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✅ {a.out}（次に bets_check.py で確かめる）")


if __name__ == "__main__":
    main()
