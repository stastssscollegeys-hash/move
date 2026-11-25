# -*- coding: utf-8 -*-
"""web_forward.py — Web版の前向き台帳。決めたルールを、全レースに機械的に登録して結果で精算する（2026-11-18 新設）

きっかけ: JRA-VAN 終了（2026-11-06）で、前向き台帳（E2.1・U1・B1）が 11/1 から増えていない。台帳がたまらないとルールの良し悪しを判定できない。
ここでは Web の出走表・オッズ（{日付}_web_probs.json）から、発走前のレースだけを登録する。公開した買い目とは別（全レース・1点100円・機械的）。
ルール（2026-11-18 事前登録。docs/keiba_2026_summary_20261118.md §7。数字は10年25,440R・確定オッズ）:
  T1 単勝◎・割安さ1.30以上（S2＝単勝本線）       … 10年 108%
  T2 単勝◎・割安さ1.15〜1.30（通常）            … 10年 94%
  T0 単勝◎・割安さ1.15未満（S1＝見送りの帯）      … 10年 88%（買わない帯が本当に悪いかの確認用）
  W2 ワイド◎-○・◎-▲（割安さ1.15以上のレース）   … 10年 90〜92%
  A3 単勝・穴（S3: 6番人気以下・割安さ1.3以上・確率2%以上）… 10年 109%
  A4 ワイド◎-5頭目（S4: 印なしで割安さ1位・確率3%以上）   … 10年 90%
  P1 複勝・モデル確率1位（比較用: いちばん来そうな馬）     … 10年 86%
  B1 単勝・市場＋木（benter_live.py の B1 と同じ基準。2023〜26年の発走30分前オッズで119.5%）。Web版は当日のトラックバイアスが入らない・
     登録の時刻が発走30分前とは限らない＝JV版の B1（ledger_b1.json・22点で止まっている）とは別の台帳として数える
  N1 単勝・N2 複勝・NW ワイド（新◎-○・新◎-▲）… 2026-11-26 事前登録。新◎＝割安さ1位、ただし確率がPの7割未満ならP（web_picks.marks_of の既定）。
     T・W・A は以前の付け方（web_picks.marks_of_v53）のまま数える。判定は docs/keiba_method_review_20261126.md §5
  python web_forward.py register --date 20261121            # その時点の web_probs で、まだ発走していないレースを登録（同じレースは上書きしない）
  python web_forward.py settle --date 20261121              # {日付}_web_results.json で精算
  python web_forward.py report                              # ルールごとの点数・的中・回収率（前向き／さかのぼり を分けて表示）
  python web_forward.py backfill                            # 11/7〜11/15 を保存済みのオッズでさかのぼって入れる（参考。前向きではない）
決まり: ルールと基準は動かさない。変えるときは新しい記号で足す。発売前の想定オッズ（前夜の早い時刻）では登録しない。
"""
import argparse, collections, datetime, json, sys

sys.stdout.reconfigure(encoding="utf-8")
import web_live as WL
import web_picks as WP

LEDGER = WL.L.DB / "ledger_web.json"
RULES = {"T1": "単勝◎ 割安さ1.30以上", "T2": "単勝◎ 割安さ1.15〜1.30", "T0": "単勝◎ 割安さ1.15未満（見送りの帯）", "W2": "ワイド◎-○・◎-▲（1.15以上）",
         "A3": "単勝 穴（6番人気以下・1.3以上・2%以上）", "A4": "ワイド◎-5頭目（印なしで割安さ1位）", "P1": "複勝 モデル確率1位",
         "B1": "単勝 B1（市場＋木の確率×オッズ≧1.0の全部）",
         "R1": "馬連◎-○（割安さ1.30以上）", "R2": "馬単◎→○（割安さ1.30以上）", "R3": "ワイド◎-○（割安さ1.30以上）",
         "N1": "単勝 新◎（割安さ1位・確率がPの7割未満ならP）", "N2": "複勝 新◎", "NW": "ワイド 新◎-○・新◎-▲（全レース）"}


def load(): return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
def save(L): LEDGER.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8")


def bets_of(race):
    hs, marks = WP.marks_of_v53(race)      # T・W・A のルールは 2026-11-18 に登録した付け方（割安さ1位＝◎）のまま数える
    if not marks:
        return []
    rt = lambda h: h["p_model"] / h["p_market"]
    hon = marks[0][1]; ra = rt(hon); used = {h["uma"] for _, h in marks}
    out = [("T1" if ra >= 1.30 else "T2" if ra >= 1.15 else "T0", "単勝", (hon["uma"],), hon["odds"], ra)]
    if ra >= 1.15:
        for m, h in marks[1:]:
            if m in "○▲":
                out.append(("W2", "ワイド", tuple(sorted((hon["uma"], h["uma"]))), None, ra))
    # 2026-11-26 事前登録（bet_type_by_band_test.py・10年で1.30以上の帯は ◎-○ の1点がそろって100%超）: R1 馬連◎-○・R2 馬単◎→○・R3 ワイド◎-○（どれも割安さ1.30以上のレースだけ）
    maru = [h for m, h in marks[1:] if m == "○"]
    if ra >= 1.30 and maru:
        o_ = maru[0]["uma"]
        out.append(("R1", "馬連", tuple(sorted((hon["uma"], o_))), None, ra)); out.append(("R2", "馬単", (hon["uma"], o_), None, ra)); out.append(("R3", "ワイド", tuple(sorted((hon["uma"], o_))), None, ra))
    c3 = [h for h in hs if h["uma"] not in used and h["pop"] >= 6 and h["p_model"] >= .02 and rt(h) >= 1.3]
    if c3:
        a = max(c3, key=rt); out.append(("A3", "単勝", (a["uma"],), a["odds"], rt(a)))
    c4 = [h for h in hs if h["uma"] not in used and h["p_model"] >= .03]
    if c4:
        a = max(c4, key=rt); out.append(("A4", "ワイド", tuple(sorted((hon["uma"], a["uma"]))), None, rt(a)))
    p1 = max(hs, key=lambda h: h["p_model"]); out.append(("P1", "複勝", (p1["uma"],), None, rt(p1)))
    # 2026-11-26 事前登録（v5.4-A1 の軸＝「割安さ1位。ただし確率がPの7割未満ならP」）: N1 単勝・N2 複勝・NW ワイド 新◎-○・新◎-▲（全レース）
    _, nm = WP.marks_of(race, axis="p70")
    if nm:
        nh = nm[0][1]
        out.append(("N1", "単勝", (nh["uma"],), nh["odds"], rt(nh))); out.append(("N2", "複勝", (nh["uma"],), None, rt(nh)))
        for m, h in nm[1:]:
            if m in "○▲":
                out.append(("NW", "ワイド", tuple(sorted((nh["uma"], h["uma"]))), None, rt(nh)))
    for h in hs:                                           # B1: web_live.py が付けた p_b1（benter_live の確率）。無い日は登録されない
        if h.get("p_b1") and h["p_b1"] * h["odds"] >= 1.0 and h["odds"] < 900:
            out.append(("B1", "単勝", (h["uma"],), h["odds"], h["p_b1"] * h["odds"]))
    return out


def register(date, src=None, backfill=False, after=None):
    f = WL.OUT / (src or f"{date}_web_probs.json")
    d = json.load(open(f, encoding="utf-8")); made = d.get("made_at") or ""
    now = after or (made[11:16] if made[:10].replace("-", "") == date else "00:00")
    L = load(); have = {(x["date"], x["race"]) for x in L}; n = 0
    for k, r in d["races"].items():
        if not r.get("horses") or (date, k) in have or (r.get("start") or "99:99") <= now:
            continue
        for rule, typ, comb, odds, ra in bets_of(r):
            L.append(dict(date=date, race=k, title=r.get("title", ""), start=r.get("start"), rule=rule, type=typ, comb=list(comb), odds_at=odds, ratio=round(ra, 3),
                          stake=100, snap_at=made, backfill=backfill, settled=False, payout=0)); n += 1
    save(L); print(f"登録 {date}: {n}点（オッズ {made}・{now} より後に発走のレース）")


def settle(date):
    R = json.load(open(WL.OUT / f"{date}_web_results.json", encoding="utf-8")); L = load(); n = 0
    for x in L:
        if x["date"] != date or x["settled"] or x["race"] not in R:
            continue
        pay = R[x["race"]].get("pay") or {}
        key = "-".join(map(str, x["comb"]))
        if x["type"] in ("馬単", "3連単"):          # 着順どおりの券種は並べ替えずに比べる（2026-11-26）
            hit = [p["yen"] for p in pay.get(x["type"], []) if "-".join(str(int(v)) for v in str(p["comb"]).replace("→", "-").split("-")) == key]
        else:
            hit = [p["yen"] for p in pay.get(x["type"], []) if "-".join(map(str, sorted(map(int, str(p["comb"]).split("-"))))) == key]
        x["payout"] = hit[0] if hit else 0; x["settled"] = True; n += 1
    save(L); print(f"精算 {date}: {n}点")


def report():
    L = [x for x in load() if x["settled"]]
    for lab, g in (("前向き（登録してから結果を見たもの）", [x for x in L if not x.get("backfill")]), ("さかのぼり（参考・保存済みのオッズで後から入れたもの）", [x for x in L if x.get("backfill")])):
        if not g:
            print(f"■ {lab}: まだ無し"); continue
        days = sorted({x["date"] for x in g}); print(f"■ {lab}: {days[0]}〜{days[-1]}・{len(days)}日")
        print(f"  {'記号':3s} {'ルール':34s} {'点':>5s} {'的中':>4s} {'的中率':>6s} {'回収率':>7s} {'最大の1本を除く':>8s}")
        for rule, nm in RULES.items():
            a = [x for x in g if x["rule"] == rule]
            if not a: continue
            st = 100 * len(a); rt = sum(x["payout"] for x in a); mx = max(x["payout"] for x in a)
            print(f"  {rule:3s} {nm:34s} {len(a):5d} {sum(x['payout']>0 for x in a):4d} {sum(x['payout']>0 for x in a)/len(a)*100:5.1f}% {rt/st*100:6.1f}% {((rt-mx)/(st-100)*100 if len(a)>1 else 0):7.1f}%")
    print("（1点100円・全レースに機械的に登録。100点に満たないうちは、良し悪しを決めない）")


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("register", "settle"):
        p = sp.add_parser(c); p.add_argument("--date", required=True)
    sp.add_parser("report"); sp.add_parser("backfill")
    a = ap.parse_args()
    if a.cmd == "register": register(a.date)
    elif a.cmd == "settle": settle(a.date)
    elif a.cmd == "report": report()
    else:
        for date, src in (("20261108", None), ("20261114", None), ("20261115", "20261115_web_probs_prev0947.json")):   # 11/7 は発売前の想定オッズなので入れない
            register(date, src, backfill=True); settle(date)
        report()


if __name__ == "__main__":
    main()
