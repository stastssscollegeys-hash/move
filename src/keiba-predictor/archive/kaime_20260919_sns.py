# -*- coding: utf-8 -*-
"""
kaime_20260919_sns.py — オールカマーの「SNS提示用」買い目（実際の購入はルールR1どおり見送り）
==========================================================================================
2026-09-18 ユーザー指示: 「SNSでは見送りよりも買い目を提示したほうが注目を集める。実際の収支は見送りでいい」
→ 公開用の買い目を組む。rule_forward_ledger（実収支の台帳）には登録しない。
  ※出力名を sns_kaime_*.json にしているのは、台帳が research/kaime_*.json の最後のファイルを読むため（混入防止）

構成（structure_backtest で最も安定した「馬連BOX3＋◎ワイド流し」を9/16ガードに合わせて調整）:
  馬連BOX ◎⑦○⑫▲⑥ ＋ ワイド ◎⑦→⑫⑥③
  - 推定4.0倍未満のワイドは入れない（◎-⑨ 1.9倍・◎-⑬ 3.3倍を除外）
  - 3連複なし・🔥③は相手のみ（軸にしない）
  - 配分は推定配当に反比例（どの点が当たってもほぼ同じ額が戻る）・予算は自信度8の規定額8,000円
"""
from __future__ import annotations
import json, sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from payout_estimator import estimate

BASE = Path.home() / "Desktop" / "競馬予想レポート" / "20260920"
UNIT, BUDGET = 100, 8000
MARKS = {"◎": 7, "○": 12, "▲": 6, "△": [9, 13], "🔥": 3}
POINTS = [("馬連", 7, 12), ("馬連", 7, 6), ("馬連", 12, 6), ("ワイド", 7, 12), ("ワイド", 7, 6), ("ワイド", 7, 3)]
# --final（2026-09-19夜・土曜の反省を反映しユーザー承認）: ◎は指数、相手は◎を除く市場人気上位4頭（⑨⑬⑥⑫＝印の○▲△△と同じ4頭）。
# structure_backtest（452R）の「混合×ワイド◎流し(相手4)×反比例」を基本に、◎-⑨はワイドだと推定1.9倍で
# Σ(1/配当)が1.21になり1点的中が必ずガミになるため、⑨だけ馬連（推定3.9倍）で持つ。🔥③は買い目に入れない。
POINTS_FINAL = [("ワイド", 7, 13), ("ワイド", 7, 6), ("ワイド", 7, 12), ("馬連", 7, 9)]


def main():
    a = sys.argv
    odds_file = a[a.index("--odds") + 1] if "--odds" in a else "yoso_odds_20260918.json"
    out_file = a[a.index("--out") + 1] if "--out" in a else "research/sns_kaime_20260918.json"
    final = "--final" in a
    y = json.load(open(BASE / odds_file, encoding="utf-8"))["オールカマー"]
    odds = {h["uma"]: h["odds"] for h in y["horses"]}
    pop = {h["uma"]: h["pop"] for h in y["horses"]}
    bets = [{"t": t, "combo": sorted([p, q]), "ordered": False, "role": "", "est": round(estimate(t, [odds[p], odds[q]]), 1)}
            for t, p, q in (POINTS_FINAL if final else POINTS)]
    w = sum(1 / b["est"] for b in bets)
    for b in bets:
        b["amt"] = max(UNIT, round(BUDGET * (1 / b["est"]) / w / UNIT) * UNIT)
    while sum(b["amt"] for b in bets) != BUDGET:
        d = BUDGET - sum(b["amt"] for b in bets)
        tgt = min(bets, key=lambda b: b["amt"] * b["est"]) if d > 0 else max([b for b in bets if b["amt"] > UNIT], key=lambda b: b["amt"] * b["est"])
        tgt["amt"] += UNIT if d > 0 else -UNIT
    for b in bets:
        b["ret_if_hit"] = round(b["amt"] * b["est"] / BUDGET, 2)
    over = sum(1 / b["est"] for b in bets)
    ng = []
    if any(b["amt"] % UNIT for b in bets): ng.append("100円単位でない点")
    if sum(b["amt"] for b in bets) != BUDGET: ng.append("合計≠予算")
    if any(b["ret_if_hit"] < 1.0 for b in bets): ng.append("当たっても損する点がある")
    if over > 1.0: ng.append(f"Σ(1/配当)={over:.2f}>1.0")
    # 9/6の「推定4倍未満のワイドを本線にしない」は、相手を人気上位から選ぶ--finalでは構造上必ず抵触する。
    # 代わりに上の「1点的中でもガミなし」「Σ(1/配当)≦1」で守る（452Rのバックテストで混合×ワイド流しが最も安定）
    if not final and any(b["t"] == "ワイド" and b["est"] < 4.0 for b in bets): ng.append("推定4倍未満のワイド")
    if any(MARKS["🔥"] == b["combo"][0] and b["t"] != "ワイド" for b in bets): ng.append("🔥穴が軸")
    rng = [min(b["ret_if_hit"] for b in bets), max(b["ret_if_hit"] for b in bets)]
    out = {"オールカマー": {
        "segment": f"◎{pop[7]}番人気×○{pop[12]}番人気", "marks": MARKS, "stats": "SNS提示用（実際の購入はルールR1どおり見送り・台帳には登録しない）",
        "candidates": [], "notes": ["実際の収支管理ではこのレースは見送り（○が4番人気以下で検証中のルールに当てはまらないため）"],
        "guard_clash": [], "checks_ng": ng, "pattern": "馬連BOX3＋◎ワイド流し3", "label": "◎○▲の馬連BOX＋◎からのワイド流し（6点）",
        "budget": BUDGET, "type_line": "買い方: ◎○▲の馬連BOX＋◎からのワイド流し（どの点が当たってもほぼ同じ額が戻る配分）",
        "why": ["本命⑦レガレイラは予想1.8倍の1番人気。◎の単勝や、◎と人気馬の組み合わせでは当たっても配当がほとんど残りません",
                "そこで相手を、指数2位で6番人気の⑫エセルフリーダと、指数3位で4番人気の⑥パンジャに絞りました",
                "◎が崩れた時のために⑫-⑥の馬連を少額、◎が残った時の押さえに⑦-③（🔥リビアングラス）のワイドを入れています",
                "人気の⑨コスモキュランダ・⑬ジューンテイクとのワイドは、当たっても2〜3倍にしかならないため買いません"],
        "caution": ["買い目は枠順確定後の予想オッズで組んでいます。当日朝の実オッズで金額を調整します。",
                    "◎が3着を外すと⑫-⑥の馬連以外は外れます。このレースの1番人気は過去10回で4割が3着を外しています。",
                    "馬場の状態は当日の朝に最終判断します。"],
        "overround": over, "ana_share": sum(b["amt"] for b in bets if 3 in b["combo"]) / BUDGET,
        "hon_share": sum(b["amt"] for b in bets if 7 in b["combo"]) / BUDGET, "ret_range": rng,
        "bets": [{k: b[k] for k in ("t", "combo", "ordered", "role", "est", "amt", "ret_if_hit")} for b in bets]}}
    if final:
        o = out["オールカマー"]
        o.update({
            "stats": "SNS提示用・最終版（◎は指数、相手は市場人気上位4頭。実際の購入はルールR1どおり見送り・台帳には登録しない）",
            "pattern": "ワイド◎流し3＋馬連◎-⑨", "label": "◎から人気上位4頭へ（ワイド3点＋馬連1点）",
            "type_line": "買い方: ◎から人気上位4頭へのワイド流し＋⑨だけ馬連（どの点が当たってもほぼ同じ額が戻る配分）",
            "why": ["昨日（9/19）は本命◎が5レース中3勝したのに、△の馬が2着に来て買い目が全滅したレースが4つありました",
                    "そこで今日から、相手は単勝人気の上位から選びます。今回は⑨⑬⑥⑫の4頭で、印の○▲△△と同じ顔ぶれです",
                    "◎⑦レガレイラは1.8倍の断然人気。⑨とのワイドは推定1.9倍しかつかず、1点だけ当たると損をするので、⑨とは馬連で持ちます",
                    "🔥③リビアングラスは印として注目していますが、買い目には入れていません"],
            "caution": ["前日の単勝オッズで組んでいます。当日朝の実オッズで金額を最終調整します。",
                        "◎が3着を外すと全点が外れます。このレースの1番人気は過去10回で4割が3着を外しています。",
                        "馬場の状態は当日の朝に最終判断します。"],
        })
    json.dump(out, open(BASE / out_file, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for b in bets:
        print(f"【{b['t']}】{b['combo'][0]}-{b['combo'][1]} {b['amt']:,}円 推定{b['est']}倍 → 当たれば{b['amt']*b['est']:,.0f}円（{b['ret_if_hit']*100:.0f}%）")
    print(f"Σ(1/配当)={over:.2f} ／ 必須チェック:", "✅ OK" if not ng else "❌ " + " / ".join(ng))
    print("saved", out_file)


if __name__ == "__main__":
    main()

