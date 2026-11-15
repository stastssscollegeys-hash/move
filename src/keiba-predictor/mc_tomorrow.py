# -*- coding: utf-8 -*-
"""mc_tomorrow.py — 明日の1レースを100万回（既定）シミュレーションして、確率・期待値・買い目の収支の分布を出す（2026-11-07新規）
  python mc_tomorrow.py --date 20261108 --race 東京11 --tickets "5-11:400,5-9:1100,..." [--N 1000000]
シナリオ（同じ100万回を3通りで回す）:
  A 素のモデル   : web_live のモデル確率 → λ-Harville（1着 p・2着 p^0.8・3着 p^0.7）を Gumbel で1回ずつ着順を引く
  B 確率の不確かさ: 1回ごとに「モデルと市場の混ぜ具合 a〜U(0,1)」と「強さの揺らぎ（ディリクレ κ=100）」を引いてから着順を引く
  C 昨日の偏りが続く: Bに加え、半分の回で 前に行く馬（直近4走の最初のコーナー位置）と外枠を強める（β=0.3・γ=0.2・標準化した特徴量）
オッズ: Yahoo の中間オッズ（ワイドは下限）。払戻は確定オッズで決まるので、ここでの期待値は目安
🔴 シミュレーションは入れた確率を再現するだけ（2026-11-01 検証）。Bの結果で崩れない買い目＝確率の誤りに強い買い目、として使う"""
import argparse, json, sys, itertools
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
import web_live as W, web_frontier as F

def run(p, q, front, outer, N, mode, seed=7, chunk=100_000, kappa=100.0, beta=0.3, gamma=0.2):
    rng = np.random.default_rng(seed); n = len(p); res = []
    lp0, lq = np.log(p / p.sum()), np.log(q / q.sum())
    done = 0
    while done < N:
        m = min(chunk, N - done)
        if mode == "A":
            lp = np.broadcast_to(lp0, (m, n)).copy()
        else:
            a = rng.random((m, 1)); lp = (1 - a) * lq + a * lp0
            pr = np.exp(lp - lp.max(1, keepdims=True)); pr /= pr.sum(1, keepdims=True)
            g = rng.gamma(kappa * pr + 1e-9); lp = np.log(g / g.sum(1, keepdims=True) + 1e-300)
            if mode == "C":
                on = (rng.random((m, 1)) < 0.5)
                lp = lp + on * (beta * front[None, :] + gamma * outer[None, :])
        gum = lambda: rng.gumbel(size=(m, n))
        s = lp + gum(); A = s.argmax(1)
        s = 0.8 * lp + gum(); s[np.arange(m), A] = -np.inf; Bb = s.argmax(1)
        s = 0.7 * lp + gum(); s[np.arange(m), A] = -np.inf; s[np.arange(m), Bb] = -np.inf; Cc = s.argmax(1)
        res.append(np.stack([A, Bb, Cc], 1)); done += m
    return np.concatenate(res)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--race", required=True)
    ap.add_argument("--tickets", required=True); ap.add_argument("--N", type=int, default=1_000_000); a = ap.parse_args()
    race = json.load(open(W.OUT / f"{a.date}_web_probs.json", encoding="utf-8"))["races"][a.race]
    hs = race["horses"]; uma = [h["uma"] for h in hs]; ix = {u: i for i, u in enumerate(uma)}; n = len(uma)
    p = np.array([h["p_model"] for h in hs]); q = np.array([1 / h["odds"] for h in hs]); q /= q.sum()
    facts = {f["uma"]: f for f in json.load(open(W.OUT / f"{a.date}_{a.race}_facts.json", encoding="utf-8"))}
    _, rows = W.parse_race(race["rid"]); waku = {r["uma"]: r["waku"] for r in rows}
    fr = np.array([-(facts.get(u, {}).get("first_corner_avg") or 0.5) for u in uma]); fr = (fr - fr.mean()) / (fr.std() + 1e-9)
    ou = np.array([waku.get(u, 4) for u in uma], float); ou = (ou - ou.mean()) / (ou.std() + 1e-9)
    PO = F.pair_odds(race["rid"]); po = PO["ワイド"]
    # 券種つき: "u4-5:1200"（馬連）／"4-5:1200" または "w4-5:1200"（ワイド）
    tk = []
    for x in a.tickets.split(","):
        kind = "u" if x[0] == "u" else "w"; body = x.lstrip("uw")
        tk.append((kind, tuple(sorted(map(int, body.split(":")[0].split("-")))), int(body.split(":")[1])))
    tot = sum(s for _, _, s in tk)
    print(f"■ {race['title']} {race['dist']} {n}頭 ／ 買い目 {len(tk)}点 {tot:,}円 ／ {a.N:,}回 × 3シナリオ")
    out = {}
    for mode, lab in (("A", "A 素のモデル"), ("B", "B 確率の不確かさ込み"), ("C", "C 昨日の偏りが続く")):
        top = run(p, q, fr, ou, a.N, mode)
        in3 = np.zeros((len(top), n), bool); in3[np.arange(len(top))[:, None], top] = True
        win = np.bincount(top[:, 0], minlength=n) / len(top); t3 = in3.mean(0)
        ret = np.zeros(len(top))
        top2 = np.zeros((len(top), n), bool); top2[np.arange(len(top))[:, None], top[:, :2]] = True
        for kind, (x, y), s in tk:
            if kind == "u":
                ret += (top2[:, ix[x]] & top2[:, ix[y]]) * s * PO["馬連"].get((x, y), 0)
            else:
                ret += (in3[:, ix[x]] & in3[:, ix[y]]) * s * po.get((x, y), 0)
        roi = ret / tot
        # 全ワイド組の確率と期待値（下限オッズ）
        pairs = []
        for x, y in itertools.combinations(uma, 2):
            pw = (in3[:, ix[x]] & in3[:, ix[y]]).mean(); o = po.get((x, y))
            if o: pairs.append((pw * o, pw, o, x, y))
        pairs.sort(reverse=True)
        print(f"\n[{lab}]  買い目: 何か当たる {np.mean(ret > 0):.1%} ／ 期待回収 {roi.mean():.2f} ／ プラス収支になる回 {np.mean(roi > 1):.1%} ／ 当たったときの戻りの中央値 {np.median(roi[ret > 0]) if (ret > 0).any() else 0:.2f}倍")
        order = np.argsort(-t3)[:7]
        print("   3着内の確率: " + " ".join(f"{uma[i]}:{t3[i]:.0%}" for i in order) + " ／ 勝つ確率: " + " ".join(f"{uma[i]}:{win[i]:.0%}" for i in np.argsort(-win)[:5]))
        print("   期待値の高いワイド: " + " ／ ".join(f"{x}-{y} {e:.2f}（{pw:.0%}×{o}倍）" for e, pw, o, x, y in pairs[:6]))
        out[mode] = dict(hit=float(np.mean(ret > 0)), roi=float(roi.mean()), plus=float(np.mean(roi > 1)), t3={uma[i]: float(t3[i]) for i in range(n)}, win={uma[i]: float(win[i]) for i in range(n)},
                         top_pairs=[(f"{x}-{y}", round(e, 3), round(pw, 4), o) for e, pw, o, x, y in pairs[:15]])
    (W.OUT / f"{a.date}_{a.race}_mc.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
main()
