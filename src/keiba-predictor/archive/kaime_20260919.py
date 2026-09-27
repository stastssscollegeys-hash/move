# -*- coding: utf-8 -*-
"""
kaime_20260919.py — 2026/9/20 オールカマーの買い目（枠順確定版・予想オッズ）。kaime_20260912.py と同じルールR1
===========================================================================================
経緯（9/11 同日中に3回作り直した）:
  ① 型別の混成（3連複・馬単・ワイド）… ユーザー「一般的でない。理にかなっているか」
  ② 全レース同じ「馬連BOX＋ワイド流し」… ユーザー「全部同じは良くない。◎○の人気でパターンを変えて」
  ③ ◎・○の人気区分ごとに最良の買い方を選ぶ … **policy_validation.py で時系列に当てると固定の買い方に負けた（過学習）**
  ④ 本版: rule_validation.py で唯一「前半／後半・3期間」で大きく崩れなかったルールを使う

採用ルール（検証中・前向きに追跡する）:
  ◎と○がどちらも1〜3番人気のレースだけ、◎○▲の馬連BOX（3点）を推定配当に反比例の配分で買う。それ以外は見送る。
  根拠（レース前の印のみ385R中128R）: 回収率120%［95%区間86〜160%］／上位1除外112%／上位3除外98%／的中35%／
         前半・後半の上位1除外115%・91%／3期間94・173・93%。**下限が100%を割っており未証明**（約450R必要）
併せて分かったこと:
  - 旧ガード（◎ワイド必須）は足すと回収率が下がる（馬連BOX3で−26pt［−63〜−2］）→ 使わない
  - 1点上限30%を付けると下がる → 付けない（反比例配分の効果を消すため）

⚠ 人気は予想オッズ（netkeiba・9/11 17時）で判定している。当日朝の実オッズで判定し直すこと
   （バックテストは確定オッズの人気で判定している）。
"""
from __future__ import annotations
import json, sys, io
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from payout_estimator import estimate

BASE = Path.home() / "Desktop" / "競馬予想レポート" / "20260920"
UNIT = 100
RULE_KEY = "馬連BOX3(◎○▲)|◎1-3人気かつ○1-3人気"
PLAN = {
    # 20因子順位どおり（9/18 score_v33_20260919.py）。予算は自信度連動の規定額（自信度8=8,000円）
    "オールカマー": dict(budget=8000, marks={"◎": 7, "○": 12, "▲": 6, "△": [9, 13], "🔥": 3}),
}


def main():
    # 2026-09-12: 日曜分を組むため、オッズファイル・対象レース・出力先を指定できるようにした
    #   例: python kaime_20260912.py --odds odds_live_20260913.json --races セントライト記念 ローズS --out research/kaime_20260913.json
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--odds", default="yoso_odds_20260918.json")
    ap.add_argument("--races", nargs="*")
    ap.add_argument("--out", default="research/kaime_20260918.json")
    a = ap.parse_args()
    global PLAN
    if a.races:
        PLAN = {k: v for k, v in PLAN.items() if k in a.races}
    # 前日オッズが出ているレースは実オッズ（odds_snapshot.py の保存分）で上書き済みのファイルを使う
    yoso = json.load(open(BASE / a.odds, encoding="utf-8"))
    rv = json.load(open(BASE.parent / "20260912" / "research" / "rule_validation_20260911.json", encoding="utf-8"))["report"][RULE_KEY]
    stats = (f"ルール「◎と○がどちらも1〜3番人気」×馬連BOX3（レース前の印のみ{rv['n']}R）: 回収率{rv['roi']*100:.0f}%"
             f"［95%区間{rv['lo']*100:.0f}〜{rv['hi']*100:.0f}%］／上位1除外{rv['ex1']*100:.0f}%／上位3除外{rv['ex3']*100:.0f}%／的中{rv['hit']*100:.0f}%"
             f"／前半・後半(上位1除外){rv['first_ex1']*100:.0f}%・{rv['second_ex1']*100:.0f}%／100%超えの証明に必要な件数 約{rv['need_races']}R")
    out, all_ok = {}, True
    for race, p in PLAN.items():
        hs = [h for h in yoso[race]["horses"] if h.get("uma") and h.get("odds")]
        odds = {h["uma"]: h["odds"] for h in hs}
        pop = {h["uma"]: h["pop"] for h in hs}
        name = {h["uma"]: h["name"] for h in hs}
        m = p["marks"]
        hp, tp = pop[m["◎"]], pop[m["○"]]
        ok_rule = hp <= 3 and tp <= 3
        common = {"segment": f"◎{hp}番人気×○{tp}番人気", "marks": m, "stats": stats, "candidates": [], "notes": [],
                  "guard_clash": [], "checks_ng": []}
        if not ok_rule:
            weak = "◎" if hp > 3 else "○"
            wp = hp if hp > 3 else tp
            out[race] = {**common, "pattern": "見送り", "label": "見送り", "budget": 0, "bets": [],
                         "type_line": f"買い方: 見送り（{weak}が{wp}番人気のため、検証中のルールに当てはまらない）",
                         "why": ["過去の検証で、◎と○のどちらかが4番人気以下のレースは、どの買い方でも回収率が伸びませんでした",
                                 f"今回は{weak}が{wp}番人気の予想なので、買い目は見送ります。印は参考にしてください",
                                 "当日の実オッズで◎と○がどちらも3番人気以内になった場合は、◎○▲の馬連BOXで買います"],
                         "overround": 0.0, "ana_share": 0.0, "hon_share": 0.0, "ret_range": [0.0, 0.0]}
            print(f"\n═══ {race}: ◎{hp}番人気・○{tp}番人気 → 見送り（ルール非該当）═══")
            continue

        top = [m["◎"], m["○"], m["▲"]]
        budget = p["budget"]
        uren = yoso[race].get("uren")   # 実際の馬連オッズ（前日発売後のみ）
        bets = [{"t": "馬連", "combo": sorted(c), "ordered": False, "role": "",
                 "est": (float(uren[f"{min(c):02d}{max(c):02d}"][0]) if uren else estimate("馬連", [odds[x] for x in c]))}
                for c in combinations(top, 2)]
        tot_w = sum(1 / b["est"] for b in bets)
        for b in bets:
            b["amt"] = max(UNIT, int(budget * (1 / b["est"]) / tot_w / UNIT) * UNIT)
        guard = 0
        while sum(b["amt"] for b in bets) != budget and guard < 500:
            guard += 1
            if sum(b["amt"] for b in bets) < budget:
                min(bets, key=lambda b: b["amt"] * b["est"])["amt"] += UNIT
            else:
                max([b for b in bets if b["amt"] > UNIT], key=lambda b: b["amt"] * b["est"])["amt"] -= UNIT
        for b in bets:
            b["ret_if_hit"] = round(b["amt"] * b["est"] / budget, 2)
        over = sum(1 / b["est"] for b in bets)
        ng = []
        amts = [b["amt"] for b in bets]
        if any(a % UNIT for a in amts): ng.append("100円単位でない点")
        if sum(amts) != budget: ng.append(f"合計{sum(amts):,}円≠予算{budget:,}円")
        if any(b["ret_if_hit"] < 1.0 for b in bets): ng.append("当たっても損する点がある")
        if over > 1.0: ng.append(f"Σ(1/配当)={over:.2f}>1.0")
        all_ok &= not ng
        used = set(top)
        clash = [f"1点の最大配分{max(amts)/budget*100:.0f}%（上限を付けると検証で回収率が下がったため付けない）"] if max(amts) / budget > 0.30 else []
        miss = [f"△{d}" for d in m["△"] if d not in used] + [f"穴{m['🔥']}"]
        clash.append("買い目に入らない印: " + "・".join(miss) + "（この買い方は◎○▲の3頭だけで組む）")
        bets.sort(key=lambda b: -b["amt"])
        print(f"\n═══ {race}: ◎{hp}番人気・○{tp}番人気 → ◎○▲の馬連BOX（予算{budget:,}円）═══")
        print(f"  Σ(1/配当)={over:.2f} ／ 1点的中の回収率 {min(b['ret_if_hit'] for b in bets)*100:.0f}〜{max(b['ret_if_hit'] for b in bets)*100:.0f}%")
        for b in bets:
            print(f"  【馬連】{'-'.join(map(str, b['combo']))} {b['amt']:,}円 推定{b['est']:.1f}倍 → 当たれば{b['ret_if_hit']*100:.0f}% [{'-'.join(name[x] for x in b['combo'])}]")
        for c in clash:
            print("  ⚠", c)
        print("  必須チェック:", "✅ OK" if not ng else "❌ " + " / ".join(ng))
        out[race] = {**common, "pattern": "馬連BOX3(◎○▲)", "label": "◎○▲の馬連BOX（3点）", "budget": budget,
                     "type_line": "買い方: ◎○▲の馬連BOX（3点・どの点が当たってもほぼ同じ額が戻る配分）",
                     "why": ["過去の検証で、印の◎と○がどちらも3番人気以内のレースに絞ると、◎○▲の馬連BOXが期間を分けても崩れにくい結果でした（検証を続けているルールです）",
                             f"今回は{'前日オッズで' if uren else '予想オッズで'}◎が{hp}番人気・○が{tp}番人気。この条件に当てはまります",
                             "金額は、どの点が当たってもほぼ同じ額が戻るように分けています"],
                     "guard_clash": clash, "checks_ng": ng, "overround": over, "ana_share": 0.0,
                     "hon_share": sum(b["amt"] for b in bets if m["◎"] in b["combo"]) / budget,
                     "ret_range": [min(b["ret_if_hit"] for b in bets), max(b["ret_if_hit"] for b in bets)],
                     "bets": [{k: b[k] for k in ("t", "combo", "ordered", "role", "est", "amt", "ret_if_hit")} for b in bets]}
    out_path = BASE / a.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nsaved {a.out}", "／ 必須チェック 全レース通過" if all_ok else "／ ❌ 未通過あり")


if __name__ == "__main__":
    main()

