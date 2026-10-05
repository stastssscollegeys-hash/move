# -*- coding: utf-8 -*-
"""
bias_carry_test.py — 「その日の前半のトラックバイアスは、後半のレースでも続くか」を10年分で測る（2026-10-05新規）
=====================================================================================================
ユーザー指示: 当日のトラックバイアスを見て予想する。その前提（前半の偏りが後半にも続き、しかも人気に織り込まれていない）を確かめる。
方法（リークなし）:
  ・その日・その競馬場・同じ芝ダの、それより前のレース（3R以上）で「前で運んだ馬（逃げ・先行）の3着内 − 人気からの期待」を集計 → 前残り度 B
    同様に「内枠（1〜3枠）の3着内 − 期待」→ 内枠度 W
  ・後のレースで、レース前に分かる「前で運ぶ型」（直近5走で逃げ・先行が6割以上）の馬の 3着内 − 期待 を、B の高低で比べる
    内枠の馬も W の高低で比べる
  ・期待は「人気順位ごとの3着内率（10年平均）」。差がプラス＝人気以上に走った
出力: docs/keiba_bias_carry.md ／ db/bias_carry.json
"""
from __future__ import annotations
import collections, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import ev_engine as E
import predict_day as P

E.SOURCE = P.HIST
rows = [r for r in E.load_rows() if r.get("着順int") and r.get("人気")]
pr = collections.defaultdict(lambda: [0, 0])
for r in rows:
    p = min(int(r["人気"]), 14); pr[p][0] += 1; pr[p][1] += r["着順int"] <= 3
EXP = {p: v[1] / v[0] for p, v in pr.items()}


def exp(r):
    return EXP[min(int(r["人気"]), 14)]


# レース前に分かる脚質（直近5走）
by_h = collections.defaultdict(list)
for r in sorted(rows, key=lambda r: (r["date"], r["R"])):
    by_h[r.get("horse_id") or r["馬名"]].append(r)
pre = {}
for hid, rs in by_h.items():
    for i, r in enumerate(rs):
        past = [x for x in rs[max(0, i - 5):i] if x.get("脚質")]
        if len(past) >= 2:
            sh = sum(x["脚質"] in ("逃げ", "先行") for x in past) / len(past)
            pre[id(r)] = "前" if sh >= 0.6 else "後" if sh <= 0.2 else "中"

days = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    days[(r["date"], r["競馬場"], r["距離"][:1])][r["R"]].append(r)

obs = []        # (B, W, 馬の型, 内枠か, 実-期待, 期待)
for key, races in days.items():
    Rs = sorted(races)
    for i, R in enumerate(Rs):
        if i < 3:
            continue
        prev = [h for x in Rs[:i] for h in races[x]]
        fr = [h for h in prev if h.get("脚質") in ("逃げ", "先行")]
        inn = [h for h in prev if h.get("枠") and h["枠"] <= 3]
        if len(fr) < 8 or len(inn) < 8:
            continue
        B = sum((h["着順int"] <= 3) - exp(h) for h in fr) / len(fr)
        W = sum((h["着順int"] <= 3) - exp(h) for h in inn) / len(inn)
        for h in races[R]:
            obs.append((B, W, pre.get(id(h)), bool(h.get("枠") and h["枠"] <= 3), (h["着順int"] <= 3) - exp(h), exp(h), h["date"][:4], key[2]))
print(f"■ 対象 {len(obs):,}頭（前半3R以上あるレース）")


def table(label, cond, keyf, cuts):
    out = []
    for lo, hi, lab in cuts:
        sub = [o for o in obs if cond(o) and lo <= keyf(o) < hi]
        if not sub:
            continue
        res = sum(o[4] for o in sub)
        var = sum(o[5] * (1 - o[5]) for o in sub)
        ex = sum(o[5] for o in sub)
        out.append(dict(band=lab, n=len(sub), ratio=round((ex + res) / ex, 3), z=round(res / math.sqrt(var), 2)))
        print(f"  {label:<16} {lab:<22} {len(sub):>7,}頭  実際/期待 {(ex + res) / ex:5.3f}  z={res / math.sqrt(var):+5.2f}")
    return out


CB = [(-9, -0.08, "前半は前が止まる(B<-0.08)"), (-0.08, -0.03, "やや止まる"), (-0.03, 0.03, "ふつう"), (0.03, 0.08, "やや前残り"), (0.08, 9, "前残り(B≥0.08)")]
res = {}
print("■ 前で運ぶ型の馬（レース前の判定）× その日の前半の前残り度")
res["front"] = table("前で運ぶ型", lambda o: o[2] == "前", lambda o: o[0], CB)
print("■ 後ろから型の馬 × 前残り度")
res["back"] = table("後ろから型", lambda o: o[2] == "後", lambda o: o[0], CB)
print("■ 内枠（1〜3枠）の馬 × その日の前半の内枠度")
res["inner"] = table("内枠", lambda o: o[3], lambda o: o[1], [(-9, -0.08, "前半は内が不利"), (-0.08, -0.03, "やや不利"), (-0.03, 0.03, "ふつう"), (0.03, 0.08, "やや有利"), (0.08, 9, "前半は内が有利")])
print("■ 外枠（6〜8枠ではなく 4枠以上全体）× 内枠度")
res["outer"] = table("4枠より外", lambda o: not o[3], lambda o: o[1], [(-9, -0.08, "前半は内が不利"), (-0.03, 0.03, "ふつう"), (0.08, 9, "前半は内が有利")])
Path(P.BASE / "daily_pdca" / "db" / "bias_carry.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

print("■ 再現性: 内枠 × 内枠度 を 期間・芝ダ別に")
WC = [(-9, -0.05, "前半は内が不利"), (-0.05, 0.05, "ふつう"), (0.05, 9, "前半は内が有利")]
for lab, cond in (("2016-2020", lambda o: o[6] <= "2020"), ("2021-2026", lambda o: o[6] >= "2021"), ("芝", lambda o: o[7] == "芝"), ("ダート", lambda o: o[7] == "ダ")):
    res["inner_" + lab] = table(f"内枠 {lab}", lambda o, c=cond: o[3] and c(o), lambda o: o[1], WC)
Path(P.BASE / "daily_pdca" / "db" / "bias_carry.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
