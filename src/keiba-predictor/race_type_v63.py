# -*- coding: utf-8 -*-
"""
race_type_v63.py — v6.3 型判定＋型別買い目生成＋出力前チェック
================================================================
年間回収率120% ＝ 的中率 × 的中時回収率。
この2つはトレードオフなので、レースごとに型を先に決めて別々に組む。

  S 的中率重視型  堅い決着を予想   的中68% × 195%  本線=8〜15倍帯   4〜6点  1点上限30%
  H 高配当型      狙える穴馬あり   的中26% × 460%  本線=20〜50倍帯  6〜10点 1点上限25%
  D 見送り        軸が立たない     —

配当の推定は payout_estimator.py（確定払戻1,044レースで較正済み）を使う。

使い方
------
  python race_type_v63.py --demo            # 9/6の7レースで型判定と買い目を再現
  python race_type_v63.py --json <records.json> --date YYYYMMDD

  from race_type_v63 import judge_type, build_bets, precheck
"""
from __future__ import annotations
import argparse, json, sys, io
from pathlib import Path
from itertools import combinations

sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from payout_estimator import estimate

# ── 型の設計値（SKILL.md v6.3 と一致させること）────────────────
SPEC = {
    "S": {"name": "S 的中率重視型", "hit": 0.68, "ret": 1.95,
          "band": (8.0, 15.0), "pts": (4, 6), "cap": 0.30},
    "H": {"name": "H 高配当型",     "hit": 0.26, "ret": 4.60,
          "band": (20.0, 50.0), "pts": (6, 10), "cap": 0.25},
    "D": {"name": "D 見送り",       "hit": 0.0,  "ret": 0.0,
          "band": (0, 0), "pts": (0, 0), "cap": 0.0},
}


def judge_type(horses: list[dict], n_field: int, odds_rise_pct: float | None = None) -> tuple[str, list[str]]:
    """
    horses: [{"num","name","score","odds","pop","style"}] を総合指数の降順で
    n_field: 頭数
    odds_rise_pct: ◎の実オッズが前日比で何%上がったか（v6.2ガード③用）
    戻り値: (型, 判定根拠のリスト)
    """
    why = []
    ranked = sorted([h for h in horses if h.get("score") is not None],
                    key=lambda h: -h["score"])
    if len(ranked) < 3:
        return "D", ["採点できた頭数が3頭未満"]

    gap12 = ranked[0]["score"] - ranked[1]["score"]
    gap13 = ranked[0]["score"] - ranked[2]["score"]
    top = ranked[0]

    # ── D 見送りの判定（最優先）────────────────────
    if gap13 < 2.0:
        return "D", [f"上位3頭が団子（1位-3位差 {gap13:.1f}pt）。軸が立たない"]
    if odds_rise_pct is not None and odds_rise_pct >= 50:
        why.append(f"◎の実オッズが前日比+{odds_rise_pct:.0f}%。信頼が崩れている")
        return "D", why
    if top.get("pop") and top["pop"] >= 8:
        return "D", [f"モデル1位が市場{top['pop']}番人気。乖離が大きすぎる"]

    # ── 穴馬候補（モデル上位5位以内 × 市場6番人気以下）──
    ana = [h for h in ranked[:5]
           if h.get("pop") and h["pop"] >= 6 and h.get("odds") and h["odds"] >= 8.0]

    # ── H 高配当型 ──────────────────────────────
    if ana:
        why.append(f"狙える穴馬あり: " + " / ".join(
            f"{h['num']}番{h['name']}（{h['pop']}番人気{h['odds']}倍・モデル{ranked.index(h)+1}位）" for h in ana))
        if n_field >= 14:
            why.append(f"{n_field}頭の多頭数で紛れやすい")
        return "H", why

    # ── S 的中率重視型 ──────────────────────────
    if gap12 >= 3.0:
        why.append(f"1位が2位に{gap12:.1f}pt差で抜けている")
    if n_field <= 12:
        why.append(f"{n_field}頭の少頭数")
    if top.get("pop") and top["pop"] <= 3:
        why.append(f"モデル1位が市場{top['pop']}番人気で評価が一致")
    if not why:
        return "D", ["S型の条件（上位が抜けている／少頭数／評価一致）をどれも満たさない"]
    return "S", why


def _r100(x: int) -> int:
    """100円単位に丸める（最低100円）"""
    return max(100, int(round(x / 100.0)) * 100)


def build_bets(rtype: str, budget: int, marks: dict, odds: dict) -> dict:
    """
    型に応じた買い目を組む。
    marks: {"◎":num, "○":num, "▲":num, "△":[num,...]}
    odds:  {num: 単勝オッズ}
    戻り値: {"bets":[{"t","combo","amt","est"}], "total":int, "type":str}
    """
    spec = SPEC[rtype]
    lo, hi = spec["band"]
    hon, tai, tan = marks.get("◎"), marks.get("○"), marks.get("▲")
    deltas = list(marks.get("△") or [])
    cands = [x for x in [hon, tai, tan, *deltas] if x]

    def est3(a, b, c):
        return estimate("3連複", [odds.get(a), odds.get(b), odds.get(c)])

    def estw(a, b):
        return estimate("ワイド", [odds.get(a), odds.get(b)])

    # 3連複の候補を全部作り、推定配当で並べる
    tri = []
    for c in combinations(cands, 3):
        e = est3(*c)
        if e:
            tri.append((set(c), e))
    tri.sort(key=lambda x: x[1])

    bets = []
    if rtype == "S":
        # 本線: 帯（8〜15倍）に最も近い◎を含む3連複
        inband = [t for t in tri if hon in t[0] and lo <= t[1] <= hi]
        main = inband[0] if inband else (
            min([t for t in tri if hon in t[0]], key=lambda x: abs(x[1] - (lo + hi) / 2)) if tri else None)
        if main:
            bets.append(("3連複", sorted(main[0]), int(budget * spec["cap"]), main[1]))
        # 準本線: ◎を含む3連複を配当昇順で2点
        for t in [x for x in tri if hon in x[0] and (not main or x[0] != main[0])][:2]:
            bets.append(("3連複", sorted(t[0]), int(budget * 0.16), t[1]))
        # ◎○の馬連（着順を問わない保険）
        if tai:
            e = estimate("馬連", [odds.get(hon), odds.get(tai)])
            bets.append(("馬連", sorted([hon, tai]), int(budget * 0.14), e))
        # ワイドは保険（本線にしない）
        if tai:
            bets.append(("ワイド", sorted([hon, tai]), int(budget * 0.12), estw(hon, tai)))
        # ◎を含まない点を1つ（v5.9ガード）
        nohon = [t for t in tri if hon not in t[0]]
        if nohon:
            t = nohon[len(nohon) // 2]
            bets.append(("3連複", sorted(t[0]), int(budget * 0.10), t[1]))
    elif rtype == "H":
        # 本線: 帯（20〜50倍）に入る3連複を配当昇順で最大3点
        inband = [t for t in tri if lo <= t[1] <= hi]
        for i, t in enumerate(inband[:3]):
            bets.append(("3連複", sorted(t[0]), int(budget * (spec["cap"] - i * 0.05)), t[1]))
        # 帯に入らなければ配当の高い順に補完
        if not inband:
            for i, t in enumerate(sorted(tri, key=lambda x: -x[1])[:3]):
                bets.append(("3連複", sorted(t[0]), int(budget * (spec["cap"] - i * 0.05)), t[1]))
        # ◎×穴のワイド（8倍以上なら本線級）
        for d in deltas[:2]:
            e = estw(hon, d)
            if e and e >= 8.0:
                bets.append(("ワイド", sorted([hon, d]), int(budget * 0.12), e))
        # 押さえ: ◎○▲の3連複（本命決着の保険・v5.9ガード②）
        if hon and tai and tan:
            e = est3(hon, tai, tan)
            bets.append(("3連複", sorted([hon, tai, tan]), int(budget * 0.08), e))
        # ◎を含まない点
        nohon = [t for t in tri if hon not in t[0]]
        if nohon:
            t = max(nohon, key=lambda x: x[1])
            bets.append(("3連複", sorted(t[0]), int(budget * 0.08), t[1]))
    else:
        return {"bets": [], "total": 0, "type": rtype}

    # 100円単位に丸めたうえで、1点上限を守りながら合計を予算に合わせる
    cap_amt = int(budget * spec["cap"] / 100) * 100      # 上限も100円単位に丸める
    out = [{"t": t, "combo": c, "amt": min(_r100(a), cap_amt), "est": e} for t, c, a, e in bets]

    def total():
        return sum(b["amt"] for b in out)

    # 不足分は上限に余裕のある点へ100円ずつ配る／超過分は大きい点から100円ずつ削る
    guard = 0
    while total() != budget and guard < 500:
        guard += 1
        if total() < budget:
            room = [b for b in out if b["amt"] + 100 <= cap_amt]
            if not room:
                break
            min(room, key=lambda b: b["amt"])["amt"] += 100
        else:
            room = [b for b in out if b["amt"] - 100 >= 100]
            if not room:
                break
            max(room, key=lambda b: b["amt"])["amt"] -= 100
    return {"bets": out, "total": total(), "type": rtype}


def precheck(res: dict, marks: dict, budget: int) -> list[str]:
    """出力前の機械チェック（v6.2の5項目）。問題があれば文字列で返す"""
    ng = []
    bets = res["bets"]
    if not bets:
        return ["買い目が空"]
    # 1. 100円単位
    bad = [b for b in bets if b["amt"] % 100 != 0]
    if bad:
        ng.append(f"100円単位でない点が{len(bad)}件: " +
                  " / ".join(f"{b['t']}{b['combo']} {b['amt']}円" for b in bad))
    # 2. 合計＝予算
    if res["total"] != budget:
        ng.append(f"合計{res['total']:,}円が予算{budget:,}円と一致しない")
    # 3. △が3連複に最低1回
    used = set()
    for b in bets:
        used |= set(b["combo"])
    miss = [d for d in (marks.get("△") or []) if d not in used]
    if miss:
        ng.append(f"△に付けたが買い目に不在: {miss}（v5.8ルール違反）")
    # 4. ◎を含まない点が最低1点
    hon = marks.get("◎")
    if hon and all(hon in b["combo"] for b in bets):
        ng.append("全点が◎を含む（単一馬依存・v5.9ルール違反）")
    # 5. 1点上限
    cap = SPEC[res["type"]]["cap"]
    over = [b for b in bets if b["amt"] > budget * cap + 1]
    if over:
        ng.append(f"1点上限{cap*100:.0f}%超: " +
                  " / ".join(f"{b['t']}{b['combo']} {b['amt']}円" for b in over))
    # 6. 本線の推定配当が帯に入っているか
    lo, hi = SPEC[res["type"]]["band"]
    main = max(bets, key=lambda b: b["amt"])
    if main.get("est") and not (lo * 0.7 <= main["est"] <= hi * 1.5):
        ng.append(f"本線の推定配当{main['est']:.1f}倍が{res['type']}型の帯({lo}〜{hi}倍)から外れる")
    return ng


def render(res: dict, budget: int, marks: dict, why: list[str]) -> str:
    spec = SPEC[res["type"]]
    L = [f"【型判定】{spec['name']}",
         *[f"　・{w}" for w in why]]
    if res["type"] == "D":
        L.append("　→ 買いません")
        return "\n".join(L)
    L += [f"　目標: 的中率{spec['hit']*100:.0f}% × 的中時回収{spec['ret']*100:.0f}% = 寄与{spec['hit']*spec['ret']*100:.0f}%",
          "",
          f"💰 買い目 合計{len(res['bets'])}点・{res['total']:,}円"]
    by = {}
    for b in res["bets"]:
        by.setdefault(b["t"], []).append(b)
    for t, lst in by.items():
        L.append(f"【{t}】{len(lst)}点 {sum(x['amt'] for x in lst):,}円")
        for b in lst:
            e = f"（推定{b['est']:.1f}倍）" if b.get("est") else ""
            L.append(f"　{'-'.join(map(str,b['combo']))} {b['amt']:,}円{e}")
    main = max(res["bets"], key=lambda b: b["amt"])
    if main.get("est"):
        L.append(f"役割: 本線={main['t']}{'-'.join(map(str,main['combo']))} "
                 f"推定{main['est']:.1f}倍 × 配分{main['amt']/budget*100:.0f}% "
                 f"= 的中時{main['est']*main['amt']/budget*100:.0f}%")
    return "\n".join(L)


# ── デモ: 2026/9/6 の実データで再現 ─────────────────────
DEMO = [
 {"label": "阪神11R セントウルS", "budget": 5000, "n": 16,
  "marks": {"◎": 3, "○": 9, "▲": 5, "△": [8, 11, 1]},
  "odds": {3: 3.2, 9: 5.1, 5: 6.9, 8: 4.2, 11: 18.9, 1: 9.9, 15: 23.3, 16: 28.2},
  "horses": [{"num":3,"name":"フリッカージャブ","score":63.9,"odds":3.2,"pop":1,"style":"逃げ"},
             {"num":5,"name":"ダイヤモンドノット","score":61.6,"odds":6.9,"pop":4,"style":"逃げ"},
             {"num":8,"name":"ファストネットワーク","score":54.0,"odds":4.2,"pop":2,"style":"—"},
             {"num":16,"name":"タマモイカロス","score":53.7,"odds":28.2,"pop":9,"style":"差し"},
             {"num":1,"name":"ママコチャ","score":53.3,"odds":9.9,"pop":5,"style":"差し"}],
  "actual": ("3連複", [1,3,9], 15.60)},
 {"label": "中山11R 紫苑S", "budget": 10000, "n": 11,
  "marks": {"◎": 9, "○": 3, "▲": 2, "△": [6, 10, 4]},
  "odds": {9: 2.5, 3: 4.4, 2: 8.5, 6: 12.6, 10: 6.0, 4: 15.4, 11: 15.0},
  "horses": [{"num":2,"name":"サムシングスイート","score":64.7,"odds":8.5,"pop":4,"style":"差し"},
             {"num":9,"name":"ドリームコア","score":60.3,"odds":2.5,"pop":1,"style":"先行"},
             {"num":3,"name":"リアライズルミナス","score":56.7,"odds":4.4,"pop":2,"style":"先行"},
             {"num":10,"name":"ジッピーチューン","score":53.1,"odds":6.0,"pop":3,"style":"差し"},
             {"num":4,"name":"マスターソアラ","score":52.4,"odds":15.4,"pop":7,"style":"差し"}],
  "actual": ("3連複", [2,4,9], 37.20)},
]


def _demo():
    print("═══ v6.3 型判定＋買い目生成 デモ（2026/9/6の実データ）═══\n")
    for d in DEMO:
        t, why = judge_type(d["horses"], d["n"])
        res = build_bets(t, d["budget"], d["marks"], d["odds"])
        print(f"■ {d['label']}　予算{d['budget']:,}円")
        print(render(res, d["budget"], d["marks"], why))
        ng = precheck(res, d["marks"], d["budget"])
        print("　チェック: " + ("✅ 全項目通過" if not ng else "⚠ " + " / ".join(ng)))
        # 実際の結果と突き合わせ
        at, ac, ao = d["actual"]
        got = sum(b["amt"] * ao for b in res["bets"]
                  if b["t"] == at and sorted(b["combo"]) == sorted(ac))
        print(f"　実際の決着: {at}{'-'.join(map(str,ac))} = {ao}倍"
              f" → この買い目での払戻 {int(got):,}円（回収率{got/d['budget']*100:.0f}%）\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    _demo()
