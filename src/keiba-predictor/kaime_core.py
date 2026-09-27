# -*- coding: utf-8 -*-
"""
kaime_core.py — 買い目ルールを1本にする（ルールK1・2026-09-27 事前登録）
=========================================================================
再検証で、券種別しきい値・型×買い方ROI・v5〜v7.2の多層ガードは
「情報の無い指数の上でノイズを最適化していた」と分かった。
ここでは **確率＝prob_core（市場オッズ×両関門を通った消し）** を前提に、ルールを1本だけ置く。

ルールK1（事前登録・変更したら版を上げて履歴を残す）
  1. 当日朝のオッズスナップショット（odds_snapshot.py）から 単勝・複勝・馬連・ワイド の実オッズを取る
  2. prob_core で確率 p を作る（市場オッズ → 消し補正 → λ-Harville）
  3. 候補: 単勝 上位3頭 ／ 複勝 上位3頭 ／ ワイド 上位4頭の6組 ／ 馬連 上位3頭の3組
  4. 期待値 = p × 実オッズ（複勝は下限オッズ）。**期待値 1.05 以上** の点だけ買う
     （市場確率をそのまま使えば全点 ≒0.80 になる。1.05を超えるのは消しで確率が動いた馬だけ＝
       「消しが市場より正しいか」を賭ける設計）
  5. 該当なしなら **見送り**（見送りも台帳に残す）
  6. 配分: 予算10,000円を上限に、オッズに反比例（当たったときの払戻を均す）。100円単位。1点上限30%。
     Σ(1/オッズ) が1.0を超える組み合わせは点数を減らす（ガミ排除・kaime_design_v7 の中核）
  7. 印は p の順（◎○▲△△）。買い目と印は同じ p から出るので必ず一致する

判定（rule_forward_ledger と同じ・事前登録）
  採用: 前向き累計の95%区間の下限が100%を超えたとき
  棄却: 買った100レース時点で、最高配当1レース除外の回収率が80%を下回ったとき

使い方:
  python kaime_core.py --snapshot <odds_snapshots/YYYYMMDD/raceid_hhmm.json> [--records <records.json>] [--register]
  python kaime_core.py --day 20260927 --register          # その日の全スナップショット（最新時刻）を一括
  python kaime_core.py --settle                            # 確定払戻で精算
  python kaime_core.py --report
台帳: daily_pdca/db/rule_k1_ledger.json
"""
from __future__ import annotations
import argparse, glob, json, random, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from prob_core import market_probs, adjust, top3_scenarios, ticket_probs, marks

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
LEDGER = DB / "rule_k1_ledger.json"
RULE_VERSION = "K1.0"
REGISTERED = "2026-09-27"
EV_MIN = 1.00     # EV_est = 払戻率 × lift。消しが確率を 1/0.8=25%以上動かした券だけが超える
BUDGET = 10000
CAP = 0.30


def load():
    return json.load(open(LEDGER, encoding="utf-8")) if LEDGER.exists() else []


def save(rows):
    LEDGER.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def read_snapshot(path):
    d = json.load(open(path, encoding="utf-8"))
    o = d["odds"]

    def f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    tan = {int(k): f(v[0]) for k, v in o.get("単勝", {}).items() if f(v[0])}
    fuku = {int(k): f(v[0]) for k, v in o.get("複勝", {}).items() if f(v[0])}     # 下限オッズ
    def pairs(t):
        out = {}
        for k, v in o.get(t, {}).items():
            a, b = int(k[:2]), int(k[2:4])
            if f(v[0]):
                out[tuple(sorted((a, b)))] = f(v[0])
        return out
    return d, tan, fuku, pairs("馬連"), pairs("ワイド")


def flags_from(records_for_race: dict | None, horses_meta: dict | None):
    """消し要素の判定材料。斤量有利はレース前records、馬体重は当日スナップショットの horses から"""
    import re
    flags = {}
    if records_for_race:
        for u, r in records_for_race.items():
            flags.setdefault(u, {})["kin70"] = float(r.get("F10_斤量") or 0) >= 70
    if horses_meta:
        for k, h in horses_meta.items():
            try:
                u = int(h.get("umaban") or h.get("馬番") or k)
            except (TypeError, ValueError):
                continue
            w = str(h.get("weight") or h.get("馬体重") or "")
            m = re.search(r"\(([+-]?\d+)\)", w)
            if m:
                flags.setdefault(u, {})["wt_m10"] = int(m.group(1)) <= -10
    return flags


TAKEOUT = {"単勝": 0.80, "複勝": 0.80, "馬連": 0.775, "ワイド": 0.775}   # 券種別の払戻率（JRA公示）


def build(tan, fuku, uren, wide, flags):
    """
    期待値の定義（K1.0）:
      市場オッズだけから作った確率 q_t と、消しを掛けた確率 p_t を **同じλ-Harville** で出し、
      lift = p_t / q_t を取る。Harvilleの偏り（高配当を過大評価等）は分子分母で打ち消される。
      市場の券は払戻率どおり（EV = TAKEOUT）と仮定し、 EV_est = TAKEOUT × lift。
      → 消しが市場より正しければ、消された馬の相手の券だけ EV_est が 1.0 を超える。
      Harvilleと市場のズレそのものは買わない（それは band_scan で全滅した領域）。
    """
    q = market_probs(tan)
    p = adjust(q, flags)
    tq = ticket_probs(top3_scenarios(q), q)
    tp = ticket_probs(top3_scenarios(p), p)
    order = sorted(p, key=lambda u: -p[u])
    top3, top4 = order[:3], order[:4]
    cands = []
    for u in top3:
        if tan.get(u):
            cands.append(("単勝", (u,), tan[u]))
        if fuku.get(u):
            cands.append(("複勝", (u,), fuku[u]))
    for a, b in ((x, y) for i, x in enumerate(top4) for y in top4[i + 1:]):
        k = tuple(sorted((a, b)))
        if k in wide:
            cands.append(("ワイド", k, wide[k]))
        if k in uren and a in top3 and b in top3:
            cands.append(("馬連", k, uren[k]))
    rows = []
    for t, c, o in cands:
        pq, pp = tq[t].get(c, 0), tp[t].get(c, 0)
        lift = pp / pq if pq > 0 else 1.0
        rows.append(dict(t=t, combo=list(c), odds=o, p=round(pp, 4), lift=round(lift, 3),
                         ev=round(TAKEOUT[t] * lift, 3)))
    rows.sort(key=lambda r: -r["ev"])
    picked = [r for r in rows if r["ev"] >= EV_MIN]
    # Σ(1/オッズ) ≦ 1.0 になるまで期待値の低い点から落とす（ガミ排除）
    while picked and sum(1 / r["odds"] for r in picked) > 1.0:
        picked.pop()
    # 配分: オッズ反比例・100円単位・1点上限
    if picked:
        w = [1 / r["odds"] for r in picked]
        s = sum(w)
        for r, wi in zip(picked, w):
            r["amt"] = int(min(BUDGET * CAP, BUDGET * wi / s) // 100 * 100)
        picked = [r for r in picked if r["amt"] >= 100]
    return dict(p=p, q=q, marks=marks(p, q), all=rows, bets=picked,
                budget=sum(r["amt"] for r in picked), pattern="K1" if picked else "見送り")


def register(snap_path, records_path=None):
    d, tan, fuku, uren, wide = read_snapshot(snap_path)
    recs = None
    if records_path:
        rr = json.load(open(records_path, encoding="utf-8")).get("records", [])
        recs = {int(float(r["馬番"])): r for r in rr
                if r["date"] == d["race_date"] and r["競馬場"] == d["venue"] and int(r["R"]) == int(d["R"])} or None
    fl = flags_from(recs, d.get("horses") if isinstance(d.get("horses"), dict) else None)
    b = build(tan, fuku, uren, wide, fl)
    rows = load()
    rid = d["race_id"]
    if any(r["race_id"] == rid for r in rows):
        print(f"[SKIP] {d['venue']}{d['R']}R 登録済み")
        return b
    pop = {u: i + 1 for i, u in enumerate(sorted(tan, key=lambda u: tan[u]))}
    m = b["marks"]
    rows.append(dict(race_id=rid, date=d["race_date"], venue=d["venue"], R=int(d["R"]), race=d.get("title", "")[:20],
                     rule=RULE_VERSION, registered_at=datetime.now().isoformat(timespec="minutes"),
                     odds_at=d.get("fetched_at"), marks={k: v for k, v in m.items()},
                     hon_pop=pop.get(m["◎"]), flags={str(u): f for u, f in fl.items() if any(f.values())},
                     pattern=b["pattern"], budget=b["budget"],
                     bets=[dict(t=r["t"], combo=r["combo"], amt=r["amt"], odds_at_bet=r["odds"], ev=r["ev"]) for r in b["bets"]],
                     settled=False, payout=None))
    save(rows)
    tag = f"{b['pattern']} 予算{b['budget']:,}円" if b["bets"] else "見送り"
    print(f"[ADD] {d['venue']}{d['R']}R ◎{m['◎']}({pop.get(m['◎'])}人気) {tag}"
          + (f"  消し:{','.join(str(u) for u,f in fl.items() if any(f.values()))}" if any(any(f.values()) for f in fl.values()) else ""))
    return b


def settle():
    pays = json.load(open(DB / "payouts.json", encoding="utf-8"))
    rows, n = load(), 0
    for r in rows:
        if r["settled"]:
            continue
        p = pays.get(r["race_id"])
        if not p:
            continue
        ret = 0
        for b in r["bets"]:
            for x in p["payouts"].get(b["t"], []):
                if sorted(int(v) for v in x["combo"].split("-")) == sorted(b["combo"]):
                    ret += b["amt"] * x["yen"] / 100
        r["payout"], r["settled"] = ret, True
        n += 1
    save(rows)
    print(f"精算 {n}件")


def report():
    rows = [r for r in load() if r["settled"]]
    bet = [r for r in rows if r["budget"] > 0]
    print(f"■ K1 前向き成績（事前登録 {REGISTERED}）  精算済み {len(rows)}R ／ 買った {len(bet)}R ／ 見送り {len(rows)-len(bet)}R")
    if not bet:
        print("  まだ判定できるデータがありません"); return
    inv, ret = sum(r["budget"] for r in bet), sum(r["payout"] for r in bet)
    by = sorted(bet, key=lambda r: -r["payout"])[1:]
    ex1 = sum(r["payout"] for r in by) / sum(r["budget"] for r in by) if by else None
    rng, boots = random.Random(1), []
    for _ in range(4000):
        s = [bet[rng.randrange(len(bet))] for _ in bet]
        boots.append(sum(r["payout"] for r in s) / sum(r["budget"] for r in s))
    boots.sort()
    lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]
    hit = sum(1 for r in bet if r["payout"] > 0) / len(bet)
    print(f"  回収率 {ret/inv*100:.1f}% ［95%区間 {lo*100:.0f}〜{hi*100:.0f}%］ ／ 上位1除外 {ex1*100 if ex1 is not None else 0:.1f}% ／ 的中率 {hit*100:.1f}%")
    v = "【採用】下限>100%" if lo > 1 else ("【棄却】100R時点で上位1除外<80%" if len(bet) >= 100 and ex1 is not None and ex1 < .8 else f"【継続】({len(bet)}/100R)")
    print("  判定:", v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot"); ap.add_argument("--day"); ap.add_argument("--records")
    ap.add_argument("--register", action="store_true"); ap.add_argument("--settle", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.day:
        files = sorted(glob.glob(str(DB / "odds_snapshots" / a.day / "*.json")))
        latest = {}
        for f in files:                       # レースごとに最新時刻のスナップショットだけ使う
            latest[Path(f).name.split("_")[0]] = f
        recs = a.records
        if not recs:
            cand = sorted(glob.glob(str(Path.home() / "Desktop" / "競馬予想レポート" / "*" / f"週末ビッグデータ_*{a.day[4:]}*_records.json")))
            recs = cand[-1] if cand else None
        rr = json.load(open(recs, encoding="utf-8")).get("records", []) if recs else []
        lifts = []
        for f in latest.values():
            if a.register:
                register(f, recs)
                continue
            d, tan, fuku, uren, wide = read_snapshot(f)
            rec = {int(float(r["馬番"])): r for r in rr
                   if r["date"] == d["race_date"] and r["競馬場"] == d["venue"] and int(r["R"]) == int(d["R"])} or None
            fl = flags_from(rec, d.get("horses") if isinstance(d.get("horses"), dict) else None)
            b = build(tan, fuku, uren, wide, fl)
            lifts += [r["lift"] for r in b["all"]]
            ke = [u for u, x in fl.items() if any(x.values())]
            print(f"{d['venue']}{d['R']:>2}R {b['pattern']:<4} ◎{b['marks']['◎']:>2} 消し{ke if ke else '-'} "
                  f"最大lift {max((r['lift'] for r in b['all']), default=1):.3f}"
                  + (f"  → {[(r['t'], r['combo'], r['amt']) for r in b['bets']]}" if b["bets"] else ""))
        if lifts:
            lifts.sort()
            print(f"\nlift分布 n={len(lifts)} 中央{lifts[len(lifts)//2]:.3f} 上位5% {lifts[int(len(lifts)*.95)]:.3f} 最大 {lifts[-1]:.3f}"
                  f"  ／ 1.25以上（EV_est≧1.0）は {sum(1 for x in lifts if x >= 1.25)} 点")
    elif a.snapshot:
        b = register(a.snapshot, a.records) if a.register else None
        if b is None:
            d, tan, fuku, uren, wide = read_snapshot(a.snapshot)
            b = build(tan, fuku, uren, wide, {})
        print(json.dumps({k: b[k] for k in ("marks", "bets", "budget", "pattern")}, ensure_ascii=False, indent=1))
    if a.settle:
        settle()
    if a.report or not (a.day or a.snapshot or a.settle):
        report()


if __name__ == "__main__":
    main()
