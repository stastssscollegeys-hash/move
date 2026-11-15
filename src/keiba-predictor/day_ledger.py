# -*- coding: utf-8 -*-
"""day_ledger.py — 開催日の収支をレースごとに付け、「あとどれだけ戻れば 1日（または土日2日）が100%を超えるか」を出す（2026-11-16 新設）

きっかけ（2026-11-16 ユーザー指示）: 「1日の回収率、もしくは土日2日での回収率が毎週100%超になるように馬券を組み立てる。
土曜1日でどうなったか、その日の回収率を踏まえて後半のレースの馬券を組み立てる。土曜の回収率を見ての日曜の組み立てにもなる」。

入力:
  買い目  Desktop/競馬予想レポート/{日付}/research/final_bets_{日付}.json   {"東京4": [["単勝","12",2500], ["馬連","5-12",2000], ...], ...}
          （発走前に出した版をレースごとに足していく。11/15 と同じ形）
  結果    daily_pdca/web_live/{日付}_web_results.json（web_results.py / raceday_refresh.py が作る）
使い方:
  python day_ledger.py --date 20261121                 # ここまでの収支・これからのレースに必要な戻り
  python day_ledger.py --date 20261122 --weekend       # 前日（土曜）の台帳も足して2日合計で見る
  python day_ledger.py --date 20261121 --plan 東京11 --budget 10000   # まだ買い目を入れていないレースの「必要な戻り」を先に見る
出力: 標準出力と {日付}/research/day_ledger_{日付}.json

見方:
  「このレースだけで届かせる」＝ここまでの不足額＋このレースの投資。この戻りが出る点を最低1つ入れると、当たればその日が100%を超える。
  「残りで分ける」＝不足額を残りのレース数で割った額＋このレースの投資。
  各点の「必要なオッズ」＝その点だけで届かせるのに必要な倍率（必要な戻り÷その点の金額）。実際のオッズと見比べて、届く点があるかを確かめる。
守ること（SKILL §2）: 1レース上限15,000円は変えない・追い上げで金額を増やさない・届かせるのは券種と組み合わせで行う・期待値0.5未満の点は入れない。
注意: 収支を見て形を変えても、1点ごとの期待値は変わらない（回収率の見込みは上がらない）。高い戻りをねらうぶん当たる頻度は下がる。
"""
import argparse, json, re, sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
WL = BASE / "daily_pdca" / "web_live"
CAP = 15000


def norm(t, c):
    xs = str(c).split("-")
    return "-".join(xs) if t in ("馬単", "3連単", "単勝", "複勝") else "-".join(str(x) for x in sorted(map(int, xs)))


def rkey(k):
    m = re.match(r"(\D+)(\d+)", k)
    return (int(m.group(2)), m.group(1)) if m else (99, k)


def ledger(d):
    """その日の台帳: 結果の出たレース（確定）と、まだのレース（予定）に分けて返す"""
    bf = BASE / d / "research" / f"final_bets_{d}.json"
    bets = json.loads(bf.read_text(encoding="utf-8")) if bf.exists() else {}
    rf = WL / f"{d}_web_results.json"
    res = json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else {}
    done, todo = [], []
    for rk in sorted(bets, key=rkey):
        bl = bets[rk]; cost = sum(a for _, _, a in bl)
        r = res.get(rk)
        if r and r.get("pay") and r.get("rows"):
            pay = {t: {norm(t, p["comb"]): p["yen"] for p in v} for t, v in r["pay"].items()}
            hits = [(t, c, a, pay.get(t, {}).get(norm(t, c), 0)) for t, c, a in bl]
            ret = sum(y * a // 100 for _, _, a, y in hits)
            done.append(dict(race=rk, cost=cost, ret=ret, hits=[h for h in hits if h[3]]))
        else:
            todo.append(dict(race=rk, cost=cost, bets=bl))
    return done, todo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--weekend", action="store_true", help="前日（土曜）の台帳も足して2日合計で見る")
    ap.add_argument("--plan", help="まだ買い目を入れていないレース名（例 東京11）")
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--target", type=float, default=1.0, help="ねらう回収率（既定 1.0＝100%）")
    a = ap.parse_args()
    done, todo = ledger(a.date)
    prev = None
    if a.weekend:
        y = (date(int(a.date[:4]), int(a.date[4:6]), int(a.date[6:])) - timedelta(days=1)).strftime("%Y%m%d")
        pd_, _ = ledger(y)
        prev = dict(date=y, cost=sum(x["cost"] for x in pd_), ret=sum(x["ret"] for x in pd_), races=len(pd_))
    C = sum(x["cost"] for x in done); R = sum(x["ret"] for x in done)
    print(f"## {a.date} ここまでの収支（結果の出た {len(done)} レース）")
    run_c = run_r = 0
    for x in done:
        run_c += x["cost"]; run_r += x["ret"]
        h = " ".join(f"{t}{c}" for t, c, _, _ in x["hits"])
        print(f"  {x['race']:5s} {x['cost']:6,}円 → {x['ret']:7,}円 ｜ 累計 {run_c:7,}→{run_r:7,}（{run_r / run_c * 100:5.1f}%）{'  的中 ' + h if h else ''}")
    if C:
        print(f"  合計 {C:,}円 → {R:,}円（{R / C * 100:.1f}%）")
    tc, tr, label = C, R, "その日"
    if prev:
        print(f"\n## 前日 {prev['date']}: {prev['cost']:,}円 → {prev['ret']:,}円（{(prev['ret'] / prev['cost'] * 100) if prev['cost'] else 0:.1f}%・{prev['races']}レース）")
        tc, tr, label = C + prev["cost"], R + prev["ret"], "2日合計"
        if tc:
            print(f"   2日合計 {tc:,}円 → {tr:,}円（{tr / tc * 100:.1f}%）")
    pend = sum(x["cost"] for x in todo)
    short = a.target * tc - tr                     # ここまでの不足額（マイナスなら貯金）
    print(f"\n## これから（{label}で {a.target * 100:.0f}% をねらう）")
    if short <= 0:
        print(f"  いま {-short:,.0f}円の貯金（{label} {tr / tc * 100 if tc else 0:.1f}%）。残りは当たる頻度を優先して守る形でよい。")
        print(f"  残り {len(todo)} レースの予定投資 {pend:,}円 を全部外しても {tr / (tc + pend) * 100 if tc + pend else 0:.1f}%。")
    else:
        print(f"  いまの不足 {short:,.0f}円（{label} {tr / tc * 100 if tc else 0:.1f}%）。残り {len(todo)} レース・予定投資 {pend:,}円。")
    n_left = max(1, len(todo) + (1 if a.plan and a.plan not in [x["race"] for x in todo] else 0))
    plans = list(todo)
    if a.plan and a.plan not in [x["race"] for x in todo]:
        plans.append(dict(race=a.plan, cost=min(a.budget, CAP), bets=[]))
    out_plans = []
    for x in plans:
        cost = min(x["cost"], CAP) if x["cost"] else min(a.budget, CAP)
        need_all = max(0.0, short) + a.target * cost                      # このレースだけで届かせる
        need_share = max(0.0, short) / n_left + a.target * cost           # 残りで分ける
        print(f"\n  ■ {x['race']}（投資 {cost:,}円{'・上限15,000円を超えている→減らす' if x['cost'] > CAP else ''}）")
        print(f"     このレースだけで届かせる: 戻り {need_all:,.0f}円以上（投資の {need_all / cost:.1f}倍）")
        print(f"     残り{n_left}レースで分ける : 戻り {need_share:,.0f}円以上（投資の {need_share / cost:.1f}倍）")
        if need_share / cost > 5:
            print("     ⚠ 分けても投資の5倍を超える＝このレースだけ・この日だけで取り返す形にはしない。無理に高配当だけの買い目にせず、ふだんの組み方で買い、土日2日の合計（--weekend）や翌日に回す。")
        rows = []
        for t, c, amt in x["bets"]:
            rows.append((t, c, amt, need_all / amt, need_share / amt))
        if rows:
            print("     各点の必要なオッズ（その点だけで届かせる ／ 分ける場合）")
            for t, c, amt, o1, o2 in sorted(rows, key=lambda r: r[3]):
                print(f"       {t} {c:9s} {amt:6,}円  {o1:6.1f}倍 ／ {o2:6.1f}倍")
            print("     → 実際のオッズがこの倍率以上の点が1つも無ければ、本線（一番来そうな組）の金額を厚くするか、券種を上げる（ワイド→馬連→馬単・3連複）。金額の合計は増やさない。")
        out_plans.append(dict(race=x["race"], cost=cost, need_all=round(need_all), need_share=round(need_share)))
    od = BASE / a.date / "research"; od.mkdir(parents=True, exist_ok=True)
    (od / f"day_ledger_{a.date}.json").write_text(json.dumps(dict(date=a.date, done=done, cost=C, ret=R, prev=prev, short=round(short), pending=out_plans), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n保存 {od / ('day_ledger_' + a.date + '.json')}")


if __name__ == "__main__":
    main()
