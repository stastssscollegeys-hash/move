# -*- coding: utf-8 -*-
"""
kaime_sprinters_v2.py — スプリンターズS の買い目を「相手も指数」で組み直す（2026-09-26）
=========================================================================================
きっかけ: ユーザー指摘「予想がまるっきり人気順。それでは馬券的な妙味がない」。

実測で確かめたこと（レース前に作った印のみ・496レース・リーク除外）:
  ワイド◎流し(相手4)・推定配当に反比例配分
    相手も指数で選ぶ（印ベース）… 回収101%（95%下限65% / 上位1除外73%）的中37.1%
    相手は市場人気（混合＝現行）… 回収 82%（95%下限70% / 上位1除外78%）的中44.6%
  馬連◎流し(相手4)・反比例
    印ベース132% ／ 混合75%
  → 的中率は現行のほうが高いが、回収率は「相手も指数」が19pt高い。

  単勝の実測（同496レース）
    指数1位すべて              回収69%（市場1-3番人気を無差別に買う82%より低い）
    指数1-3位 かつ 4番人気以下   回収73%（上位1件除外で59%）… 素朴な「妙味」は成立しない
    指数4-6位 かつ 10番人気以下  回収254%（上位1件除外でも152%／前半317%・後半168%）
      → 3つの検証（大穴除外・期間分割）を通った唯一のセル。n=256と小さいので薄く張る。

⚠ 重要: 単勝オッズから確率を作る限り、どう組み替えても期待値は控除率で固定される。
   現行案も本案も推定期待値は53%で同じ。変わるのは「的中率と配当の置き方」と
   「どの実測構造に賭けるか」であって、期待値が増えるわけではない。
"""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from payout_estimator import estimate

B = Path.home() / "Desktop" / "競馬予想レポート" / "20260926" / "research"
K = json.loads((B / "kaime_sprinters.json").read_text(encoding="utf-8"))
SC = json.loads((B / "score20_20260925.json").read_text(encoding="utf-8"))["スプリンターズS"]

ODDS = {int(a): float(b) for a, b in K["odds"].items()}
NAME = {int(a): b for a, b in K["name"].items()}
POP = {int(a): b for a, b in K["pop"].items()}
RANK = {h["uma"]: i + 1 for i, h in enumerate(SC["horses"])}
H = {h["uma"]: h for h in SC["horses"]}
HON = 9
BUDGET = 8000
L2, L3 = 0.80, 0.70          # Harvilleの実測補正（2026-09-06）

raw = {u: 1 / o for u, o in ODDS.items()}
s = sum(raw.values())
P1 = {u: v / s for u, v in raw.items()}


def p_top3(u):
    others = [x for x in P1 if x != u]
    p = P1[u]
    p2 = sum(P1[a] * p / max(1e-9, 1 - P1[a]) for a in others) * L2
    p3 = 0.0
    for a, b in itertools.permutations(others, 2):
        p3 += P1[a] * (P1[b] / max(1e-9, 1 - P1[a])) * (p / max(1e-9, 1 - P1[a] - P1[b]))
    return min(0.999, p + p2 + p3 * L3)


T3 = {u: p_top3(u) for u in ODDS}
PBOTH = {u: T3[HON] * T3[u] * 0.80 for u in ODDS if u != HON}


def alloc(points, budget):
    """推定配当に反比例（どれが当たっても戻りが揃う）・100円単位"""
    w = [1 / p["est"] for p in points]
    tot = sum(w)
    amts = [max(100, int(round(budget * x / tot / 100)) * 100) for x in w]
    d = budget - sum(amts)
    amts[amts.index(max(amts))] += d       # 端数は最厚の点で吸収
    for p, a in zip(points, amts):
        p["amt"] = a
    return points


def build(label, spec):
    pts = []
    for t, u in spec:
        est = estimate(t, [ODDS[HON], ODDS[u]]) if t != "単勝" else ODDS[u]
        p = T3[HON] * T3[u] * 0.80 if t == "ワイド" else (P1[u] if t == "単勝" else PBOTH[u] * 0.45)
        pts.append(dict(t=t, u=u, est=round(est, 1), p=p))
    return dict(label=label, points=pts)


def show(d, budget=BUDGET, tan_amt=0):
    pts = d["points"]
    tan = [p for p in pts if p["t"] == "単勝"]
    rest = [p for p in pts if p["t"] != "単勝"]
    alloc(rest, budget - tan_amt)
    for p in tan:
        p["amt"] = tan_amt
    ev = sum(p["p"] * p["amt"] * p["est"] for p in pts)
    hit = 1 - 1.0
    # 少なくとも1点当たる確率（ワイドは重なるので上限を取る近似）
    hit = min(0.99, sum(p["p"] for p in rest) * 0.85 + sum(p["p"] for p in tan))
    over = sum(1 / p["est"] for p in pts)
    print(f"\n■ {d['label']}")
    print(f"{'券種':<6}{'買い目':<22}{'金額':>8}{'推定配当':>9}{'的中なら':>10}{'その率':>8}")
    for p in pts:
        lab = f"{HON}-{p['u']} {NAME[p['u']]}" if p["t"] != "単勝" else f"{p['u']} {NAME[p['u']]}"
        back = int(p["amt"] * p["est"] / 100) * 100
        print(f"{p['t']:<6}{lab:<22}{p['amt']:>7,}円{p['est']:>8.1f}倍"
              f"{back:>9,}円{p['p'] * 100:>7.1f}%")
    print(f"  合計{sum(p['amt'] for p in pts):,}円 / {len(pts)}点　"
          f"Σ(1/配当)={over:.2f}　推定期待値{ev / budget * 100:.0f}%　"
          f"少なくとも1点当たる確率 約{hit * 100:.0f}%")
    return d


CUR = build("現行案（相手＝市場人気上位4頭）",
            [("ワイド", 13), ("ワイド", 15), ("ワイド", 14), ("ワイド", 6)])
IDX = build("全振り案（相手＝指数上位）",
            [("ワイド", 15), ("ワイド", 11), ("ワイド", 10), ("ワイド", 5), ("単勝", 7)])
# 採用: 折衷。相手は市場人気上位を残しつつ、推定4.0倍未満の1番人気を外し、
# 指数4位かつ市場6番手の⑪を足す。単勝⑦は3つの検証を通った条件への薄い賭け。
MIX = build("折衷案（採用）", [("ワイド", 15), ("ワイド", 14), ("ワイド", 11),
                            ("ワイド", 6), ("単勝", 7)])

show(CUR)
show(IDX, tan_amt=1000)
show(MIX, tan_amt=1000)

MARKS = {"◎": 9, "○": 15, "▲": 11, "△": [14, 6], "🔥": 7}
print("\n■ 印と根拠")
for lab, u in [("◎", 9), ("○", 15), ("▲", 11), ("△", 14), ("△", 6), ("🔥", 7)]:
    print(f"  {lab}{u}{NAME[u]}　指数{RANK[u]}位／人気{POP[u]}／{ODDS[u]}倍／追い切り {H[u]['oikiri']}")
print(f"\n■ 印を外した1番人気: {13}{NAME[13]} 指数{RANK[13]}位／{ODDS[13]}倍／"
      f"追い切り {H[13]['oikiri']}／◎とのワイド推定{estimate('ワイド', [ODDS[HON], ODDS[13]]):.1f}倍")

out = B / "kaime_sprinters_v2.json"
MIX["hon"] = HON
MIX["race"] = "スプリンターズS"
MIX["marks"] = MARKS
MIX["budget"] = BUDGET
MIX["over"] = round(sum(1 / p["est"] for p in MIX["points"]), 2)
MIX["dropped_fav"] = dict(uma=13, name=NAME[13], rank=RANK[13], odds=ODDS[13],
                          est=round(estimate("ワイド", [ODDS[HON], ODDS[13]]), 1),
                          oikiri=H[13]["oikiri"])
out.write_text(json.dumps(MIX, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n保存: {out}")
