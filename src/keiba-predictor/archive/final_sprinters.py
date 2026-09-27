# -*- coding: utf-8 -*-
"""
final_sprinters.py — スプリンターズS 統合版（総合指数 → 印 → 買い目）
=======================================================================
総合指数 = 独自指数（20因子170点） ＋ インフルエンサー/競馬サイト合算の補正（ソース別重み）

  独自指数   : 20260926/research/score20_20260925.json
  合算シグナル: ensemble_sprinters_20260926.py の RAW（4並列収集・日付検証済み）
  オッズ     : --snapshot で指定（当日朝はこれを差し替えるだけでよい）

印の決め方（SKILL「インフルエンサー合算 v2」準拠）
  ◎○▲△△ = 総合指数の上位5頭
  🔥穴      = 総合上位6位以内で、単勝人気が10番人気以下の馬
  最低保証△ = 本命 or 追い切り1位 が2ソース以上重なった馬は必ず買い目に入れる

買い目
  ◎からのワイド流し（推定配当に反比例配分）＋ 穴の単勝
  ガード: 推定4.0倍未満を本線にしない／Σ(1/配当)≦1.0／100円単位／規定額8,000円

使い方
  python final_sprinters.py                        # 直近スナップショットで作る
  python final_sprinters.py --snapshot <path.json> # 当日朝はこれだけ差し替える
"""
from __future__ import annotations
import argparse, glob, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from ensemble_v2 import ensemble
from payout_estimator import estimate
from ensemble_sprinters_20260926 import RAW, KIND

B = Path.home() / "Desktop" / "競馬予想レポート"
SC = json.loads((B / "20260926" / "research" / "score20_20260925.json").read_text(encoding="utf-8"))["スプリンターズS"]
K = json.loads((B / "20260926" / "research" / "kaime_sprinters.json").read_text(encoding="utf-8"))
NAME = {int(a): b for a, b in K["name"].items()}
N2U = {v: k for k, v in NAME.items()}
H = {h["uma"]: h for h in SC["horses"]}
SC20 = {h["uma"]: h["final170"] for h in SC["horses"]}
IDX_RANK = {h["uma"]: i + 1 for i, h in enumerate(SC["horses"])}
BUDGET, TAN_AMT = 8000, 1000
MIN_HONSEN_EST = 4.0        # 推定4.0倍未満を本線にしない

ap = argparse.ArgumentParser()
ap.add_argument("--snapshot", default=None, help="odds_snapshots の json（省略時は最新）")
ap.add_argument("--label", default="前日版", help="出力に付ける版名（当日朝は '当日版'）")
a = ap.parse_args()

snap = a.snapshot or sorted(glob.glob(str(
    B / "daily_pdca" / "db" / "odds_snapshots" / "20260927" / "202606040911_*.json")))[-1]
S = json.loads(Path(snap).read_text(encoding="utf-8"))
ODDS = {int(k): float(v[0]) for k, v in S["odds"]["単勝"].items()}
POP = {int(k): int(v[2]) for k, v in S["odds"]["単勝"].items()}
print(f"オッズ: {Path(snap).name}（取得 {S['fetched_at']}）／{a.label}\n")

# ── 総合指数 ────────────────────────────────────────────────────
sig = []
for src, pub, conf, d in RAW:
    for key, kind in KIND.items():
        for nm in d.get(key, []) or []:
            if nm in N2U:
                sig.append((src, N2U[nm], kind))
    oik = d.get("oikiri") or []
    if oik and oik[0] in N2U:
        sig.append((src, N2U[oik[0]], "oikiri1"))
ROWS = ensemble(SC20, sig, NAME)
R = {r["num"]: r for r in ROWS}
TOTAL_RANK = {r["num"]: i + 1 for i, r in enumerate(ROWS)}

# ── 印 ──────────────────────────────────────────────────────────
top5 = [r["num"] for r in ROWS[:5]]
HON, AITE = top5[0], top5[1:]
ana_cand = [r["num"] for r in ROWS[:6] if r["num"] not in top5 and POP[r["num"]] >= 10]
if not ana_cand:
    ana_cand = [r["num"] for r in ROWS[:8] if r["num"] not in top5 and POP[r["num"]] >= 10]
ANA = ana_cand[0] if ana_cand else None
GUAR = [r["num"] for r in ROWS if r["min_delta"]]

print("■ 総合指数（独自指数 ＋ インフルエンサー合算補正）")
print(f"{'順':>2} {'馬':>3} {'馬名':<12}{'総合':>7}{'独自':>7}{'補正':>7}{'指数':>6}{'人気':>5}{'オッズ':>7}  印/フラグ")
mark_of = {HON: "◎", **{u: m for u, m in zip(AITE, ("○", "▲", "△", "△"))}}
if ANA:
    mark_of[ANA] = "🔥"
for i, r in enumerate(ROWS, 1):
    u = r["num"]
    f = []
    if r["min_delta"]:
        f.append("最低保証△")
    if r["honmei"]:
        f.append(f"本命{len(r['honmei'])}")
    if r["nega"]:
        f.append(f"消し{len(r['nega'])}")
    print(f"{i:>2} {u:>3} {NAME[u]:<12}{r['total']:>7}{r['base']:>7}{r['adj']:>+7.1f}"
          f"{IDX_RANK[u]:>5}位{POP[u]:>4}番{ODDS[u]:>7}  {mark_of.get(u,'  '):<2} " + " ".join(f))

miss = [u for u in GUAR if u not in mark_of]
print(f"\n最低保証△（本命/追切1位が2ソース以上）: " + "・".join(f"{u}{NAME[u]}" for u in GUAR))
print("  → " + ("全頭が印に入っている" if not miss else "印から漏れ: " + "・".join(f"{u}{NAME[u]}" for u in miss)))

# ── 買い目 ──────────────────────────────────────────────────────
cands = [(u, estimate("ワイド", [ODDS[HON], ODDS[u]])) for u in AITE]
if ANA:
    cands = [c for c in cands if c[0] != ANA]
drop = [c for c in cands if c[1] < MIN_HONSEN_EST]
keep = [c for c in cands if c[1] >= MIN_HONSEN_EST]
if drop:
    print(f"\n[ガード] 推定{MIN_HONSEN_EST}倍未満のため本線から外す: " +
          "・".join(f"{HON}-{u}({e:.1f}倍)" for u, e in drop))
    # 外した相手は馬連で持てるか見る
    for u, _ in drop:
        q = estimate("馬連", [ODDS[HON], ODDS[u]])
        print(f"        → 馬連 {HON}-{u} なら推定{q:.1f}倍。1点だけ馬連で持つ")

pts = [dict(t="ワイド", u=u, est=round(e, 1)) for u, e in keep]
for u, _ in drop:
    pts.append(dict(t="馬連", u=u, est=round(estimate("馬連", [ODDS[HON], ODDS[u]]), 1)))
tan_amt = TAN_AMT if ANA else 0
w = [1 / p["est"] for p in pts]
tot = sum(w)
amts = [max(100, int(round((BUDGET - tan_amt) * x / tot / 100)) * 100) for x in w]
amts[amts.index(max(amts))] += (BUDGET - tan_amt) - sum(amts)
for p, m in zip(pts, amts):
    p["amt"] = m
if ANA:
    pts.append(dict(t="単勝", u=ANA, est=ODDS[ANA], amt=tan_amt))
over = sum(1 / p["est"] for p in pts)

print(f"\n■ 買い目 合計{sum(p['amt'] for p in pts):,}円・{len(pts)}点　Σ(1/配当)={over:.2f}")
print(f"{'券種':<6}{'買い目':<24}{'金額':>8}{'推定配当':>9}{'的中なら':>10}")
for p in pts:
    lab = f"{HON}-{p['u']} {NAME[p['u']]}" if p["t"] != "単勝" else f"{p['u']} {NAME[p['u']]}"
    print(f"{p['t']:<6}{lab:<24}{p['amt']:>7,}円{p['est']:>8.1f}倍"
          f"{int(p['amt'] * p['est'] / 100) * 100:>9,}円")

out = B / "20260927" / "research" / "final_sprinters.json"
out.write_text(json.dumps({
    "race": "スプリンターズS", "label": a.label, "snapshot": Path(snap).name,
    "fetched_at": S["fetched_at"],
    "marks": {"◎": HON, "○": AITE[0], "▲": AITE[1], "△": AITE[2:], "🔥": ANA},
    "guaranteed": GUAR, "missing_from_marks": miss,
    "budget": BUDGET, "over": round(over, 2), "points": pts,
    "total_rank": [{"rank": i + 1, "uma": r["num"], "name": NAME[r["num"]], "total": r["total"],
                    "idx": r["base"], "adj": r["adj"], "idx_rank": IDX_RANK[r["num"]],
                    "pop": POP[r["num"]], "odds": ODDS[r["num"]],
                    "honmei_src": r["honmei"], "nega_src": r["nega"], "oikiri1_src": r["oikiri1"]}
                   for i, r in enumerate(ROWS)],
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n保存: {out}")
