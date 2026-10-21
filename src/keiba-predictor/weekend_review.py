# -*- coding: utf-8 -*-
"""
weekend_review.py — 週末の振り返り（予想カード × JRA-VAN成績）。weekend_pdca.py の補完（2026-10-13新規）
=====================================================================================================
weekend_pdca.py は「標準」の買い目の収支を表示しない不具合がある（kind が 標準 のとき集計だけして出力しない）ため、
別ファイルで次を出す。元のコードは変えない。
  A 確率の検証   : 勝ち馬の対数尤度（モデル vs 人気が示す確率）・Brier
  B 印別の単勝   : ◎○▲△🔥・1番人気の単勝回収（確定払戻・100円ずつ）
  C 買い目の回収 : 標準V1.1の全体／券種別／勝負馬連（比≧1.3）・レース別。レース単位のブートストラップ95%区間
                   モデルの想定戻り（的中確率×オッズ）と実際の戻りを日別・券種別・想定/実オッズ別に並べる
  D 重賞         : 印と結果の上位3頭
  E バイアス持続 : 前日の傾向が翌日も同じ側に出たか（day_review のJSONから）
使い方: python weekend_review.py --days 20261011 20261012 [--replay 20261010]
  --replay の日は {日付}/research ではなく _replay/{日付}/research の予想カードを使う（再生テスト＝確定オッズ）
"""
from __future__ import annotations
import argparse, collections, json, math, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import day_review as DR

BASE = Path.home() / "Desktop" / "競馬予想レポート"


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", nargs="+", required=True)
    ap.add_argument("--replay", nargs="*", default=[])
    a = ap.parse_args()
    days = list(a.replay) + list(a.days)
    rows, pays, cards = {}, {}, {}
    for d in days:
        rs, py = DR.load_day(d)
        for r in rs:
            if r["着順int"]:
                rows.setdefault((d, r["競馬場"], r["R"]), []).append(r)
        for k, v in py.items():
            pays[(d,) + k] = v
        root = (BASE / "_replay" / d) if d in a.replay else (BASE / d)
        for c in json.loads((root / "research" / f"cards_{d}.json").read_text(encoding="utf-8"))["cards"]:
            cards[(d, c["venue"], c["R"])] = c
    print(f"対象レース {len(cards)} ／ 成績あり {sum(1 for k in cards if k in rows)}（再生テスト: {a.replay or 'なし'}）")

    def payout(k, b):
        key = tuple(b["combo"]) if b["type"] in ("馬単", "3連単") else tuple(sorted(b["combo"]))
        return pays.get(k, {}).get(b["type"], {}).get(key, 0) * b["stake"] / 100.0

    # A
    ll_m = ll_k = n = 0
    br_m = br_k = 0.0
    for k, c in cards.items():
        hs = rows.get(k)
        if not hs:
            continue
        win = next((h["馬番"] for h in hs if h["着順int"] == 1), None)
        H = {h["uma"]: h for h in c["horses"]}
        if win not in H:
            continue
        pm = sum(h["p_model"] for h in H.values()); pk = sum(h["p_market"] for h in H.values())
        ll_m += math.log(max(H[win]["p_model"] / pm, 1e-9)); ll_k += math.log(max(H[win]["p_market"] / pk, 1e-9)); n += 1
        for u, h in H.items():
            y = 1.0 if u == win else 0.0
            br_m += (h["p_model"] / pm - y) ** 2; br_k += (h["p_market"] / pk - y) ** 2
    print(f"\n■A 確率の検証（{n}レース）: 勝ち馬の対数尤度の平均 モデル {ll_m / n:.4f} ／ 人気が示す確率 {ll_k / n:.4f} ／ 差 {(ll_m - ll_k) / n:+.4f}"
          f"　Brier モデル {br_m / n:.4f} 人気 {br_k / n:.4f}")
    # B
    tot = collections.defaultdict(lambda: [0, 0, 0, 0])
    for k, c in cards.items():
        py, hs = pays.get(k), rows.get(k)
        if not py or not hs:
            continue
        fin = {h["馬番"]: h["着順int"] for h in hs}
        for u, m in c["marks"].items():
            x = tot[m]; x[0] += 1; x[2] += 100
            if fin.get(int(u)) == 1:
                x[1] += 1; x[3] += py.get("単勝", {}).get((int(u),), 0)
        fav = min(hs, key=lambda h: h["人気"] or 99)
        x = tot["1番人気"]; x[0] += 1; x[2] += 100
        if fav["着順int"] == 1:
            x[1] += 1; x[3] += py.get("単勝", {}).get((fav["馬番"],), 0)
    print("\n■B 印別の単勝（確定払戻・100円ずつ）")
    for m in ("◎", "○", "▲", "△", "🔥", "1番人気"):
        x = tot[m]
        print(f"  {m:<4} {x[0]:>3}頭 勝ち{x[1]:>2} 単勝回収 {pct(x[3], x[2])}")
    # C
    agg = collections.defaultdict(lambda: [0, 0.0, 0.0, 0, 0.0])    # stake, ret, 想定戻り, 点, 的中
    race_ev, per_race = {}, []
    exp_hit = 0.0
    for k, c in cards.items():
        if k not in rows:
            continue
        s = r = 0.0
        for b in (c["ref_bets"] or c["bets"]):
            got = payout(k, b)
            o = b.get("odds_now") or b.get("odds_est") or 0
            real = b.get("odds_now") is not None or b["type"] == "単勝"
            tags = ["標準V1.1全体", b["type"], f"{k[0][4:]}全体", f"{'実オッズ' if real else '想定オッズ'}"] + (["勝負馬連"] if b.get("value") else [])
            for tg in tags:
                x = agg[tg]; x[0] += b["stake"]; x[1] += got; x[2] += b["stake"] * b["p_model"] * o; x[3] += 1; x[4] += got > 0
            s += b["stake"]; r += got
            if b.get("value"):
                v = race_ev.setdefault(k, [0, 0, 0.0]); v[0] += b["stake"]; v[1] += got; v[2] = max(v[2], b["p_model"] * o)
                exp_hit += b["p_model"]
        per_race.append((s, r))
    print("\n■C 買い目の回収（実際には買っていない・参考）")
    print(f"  {'区分':<12}{'点':>4}{'賭け金':>9}{'実際の戻り':>11}{'回収':>6}{'モデルの想定戻り':>14}{'想定':>6}{'的中':>5}")
    for tg, x in sorted(agg.items()):
        print(f"  {tg:<12}{x[3]:>4}{int(x[0]):>9,}{int(x[1]):>11,}{pct(x[1], x[0]):>6}{int(x[2]):>14,}{pct(x[2], x[0]):>6}{int(x[4]):>5}")
    random.seed(1)
    bs = sorted(sum(x[1] for x in smp) / sum(x[0] for x in smp) for smp in ([random.choice(per_race) for _ in per_race] for _ in range(5000)))
    print(f"  標準V1.1の回収率 {sum(x[1] for x in per_race) / sum(x[0] for x in per_race) * 100:.0f}%  レース単位の95%区間 {bs[125] * 100:.0f}〜{bs[4875] * 100:.0f}%（{len(per_race)}レース）"
          f" ／ 10年の検証は 90.5〜93.1%")
    print(f"\n  勝負馬連が出たレース {len(race_ev)}（期待的中数 {exp_hit:.2f}点 → 0点になる確率 約{math.exp(-exp_hit) * 100:.0f}%）")
    for k, (s, r, ev) in sorted(race_ev.items()):
        print(f"   {k[0][4:]} {k[1]}{k[2]}R 馬連 賭け{int(s):,}→払戻{int(r):,}（朝時点の期待値 {ev:.2f}）")
    # D
    print("\n■D 重賞・リステッドの答え合わせ")
    for k, c in sorted(cards.items()):
        if not c.get("graded") or k not in rows:
            continue
        H = {h["uma"]: h for h in c["horses"]}
        top = sorted(rows[k], key=lambda h: h["着順int"])[:3]
        print(f"  {k[0][4:]} {k[1]}{k[2]}R {c['name'][:14]} 印: " + " ".join(f"{m}{u}{H[int(u)]['name']}" for u, m in c["marks"].items() if int(u) in H))
        print("     結果: " + " / ".join(f"{h['着順int']}着{h['馬番']}{h['馬名']}（{h['人気']}番人気・{c['marks'].get(str(h['馬番']), '無印')}）" for h in top))
    # E
    dr = {}
    for d in sorted(set(days)):
        f = BASE / d / "research" / f"day_review_{d}.json"
        if f.exists():
            dr[d] = json.loads(f.read_text(encoding="utf-8"))["venues"]
    same = diff = 0
    ds = sorted(dr)
    for x, y in zip(ds, ds[1:]):
        for v in dr[x]:
            if v not in dr[y]:
                continue
            for src, items in (("style", ("逃げ", "先行", "差し", "追込")), ("waku", ("内", "中", "外"))):
                for it in items:
                    p, q = dr[x][v][src].get(it), dr[y][v][src].get(it)
                    if not p or not q or p["n"] < 8 or q["n"] < 8 or abs(p["ratio"] - 1) < 0.2:
                        continue
                    s = (p["ratio"] > 1) == (q["ratio"] > 1)
                    same += s; diff += (not s)
    print(f"\n■E バイアスの持続: 前日に1倍から0.2以上離れていた区分 {same + diff}件 → 翌日も同じ側 {same}件（{same / max(same + diff, 1) * 100:.0f}%）")


if __name__ == "__main__":
    main()
