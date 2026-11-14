# -*- coding: utf-8 -*-
"""mc_draw_20261114.py — 11/14の重賞（武蔵野S・デイリー杯2歳S）枠順確定後（11/13・金）。使い方: python mc_draw_20261114.py 武蔵野S [回数]の100万回シミュレーション
入力: draw_input_{race}.json（枠・馬番・想定オッズ〔発売前〕・想定脚質・独自指数）
確率:
  市場 q = 1/想定オッズ を正規化
  見立て p = softmax( log q + K × z(独自指数) )   … K=0.1（2026-11-14 に 0.4 から下げた。index_weight_test.py --graded: 重賞/オープン930Rで、データが選ぶ K は −0.08〜−0.06＝ほぼ0。
      K=0.4 は市場だけより1レースあたり対数尤度が 0.081 悪い。指数は市場がすでに織り込んでいる。0.1 は「想定オッズが実オッズより粗いぶん」の最小限）
  🔴 想定オッズは発売前の目安。土曜朝の実オッズで作り直す（印・買い目の確定はそのあと）
シナリオ（mc_tomorrow.py と同じ。100万回×3）:
  A 見立てそのまま／B 確率の不確かさ込み（市場との混ぜ具合 a〜U(0,1)・ディリクレ κ=100）／C Bに加えて半分の回で前に行く馬・外枠を強める
出力: 勝つ確率・3着内の確率（馬ごと）、割安さ（見立て÷市場）、ワイド・馬連の組の 的中率と見込み期待値（推定オッズ=0.775/市場確率）
"""
import json, sys, itertools
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
K = 0.1
STYLE_POS = {"逃げ": 1.0, "先行": 3.0, "好位": 5.0, "中団": 8.0, "後方": 12.0}

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

def stats(top, n):
    in3 = np.zeros((len(top), n), bool); in3[np.arange(len(top))[:, None], top] = True
    top2 = np.zeros((len(top), n), bool); top2[np.arange(len(top))[:, None], top[:, :2]] = True
    win = np.bincount(top[:, 0], minlength=n) / len(top)
    return win, in3.mean(0), in3, top2

def main():
    race = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 1_000_000
    d = json.load(open(HERE / f"draw_input_{race}.json", encoding="utf-8"))
    hs = d["horses"]; n = len(hs); uma = [h["uma"] for h in hs]; ix = {u: i for i, u in enumerate(uma)}
    odds = np.array([h["odds_est"] for h in hs], float); q = 1 / odds; q /= q.sum()
    sc = np.array([h["score"] for h in hs], float); z = (sc - sc.mean()) / sc.std()
    lp = np.log(q) + K * z; p = np.exp(lp - lp.max()); p /= p.sum()
    fr = np.array([-STYLE_POS[h["style"]] for h in hs]); fr = (fr - fr.mean()) / fr.std()
    ou = np.array([h["waku"] for h in hs], float); ou = (ou - ou.mean()) / ou.std()
    print(f"■ {race} {n}頭 ／ {N:,}回 × 3シナリオ ／ 想定オッズ: {d['odds_note']}")
    print("\n【見立て確率と市場（想定オッズ）】 馬番 馬名 想定人気 市場勝率 見立て勝率 割安さ(見立て÷市場) 指数")
    rank = np.argsort(np.argsort(-q)) + 1
    for i in np.argsort(-p):
        print(f"  {uma[i]:>2} {hs[i]['name']:<10} {rank[i]:>2}人気 {q[i]:5.1%} → {p[i]:5.1%}  ×{p[i]/q[i]:.2f}  指数{sc[i]:.1f}")
    # 市場だけで回した3着内（割安さの3着内版）
    topM = run(q, q, fr, ou, N, "A"); winM, t3M, in3M, top2M = stats(topM, n)
    out = {"p": {uma[i]: float(p[i]) for i in range(n)}, "q": {uma[i]: float(q[i]) for i in range(n)}}
    for mode, lab in (("A", "A 見立てそのまま"), ("B", "B 確率の不確かさ込み"), ("C", "C 前有利・外枠が強まる回を半分混ぜる")):
        top = run(p, q, fr, ou, N, mode); win, t3, in3, top2 = stats(top, n)
        print(f"\n[{lab}]")
        order = np.argsort(-t3)
        print("  3着内: " + " ".join(f"{uma[i]}{hs[i]['name'][:4]}{t3[i]:.0%}" for i in order[:9]))
        print("  勝つ : " + " ".join(f"{uma[i]}{hs[i]['name'][:4]}{win[i]:.0%}" for i in np.argsort(-win)[:7]))
        print("  3着内の割安さ（見立て÷市場）上位: " + " ".join(f"{uma[i]}:{t3[i]/t3M[i]:.2f}" for i in np.argsort(-(t3 / t3M))[:6]))
        pairs = []
        for x, y in itertools.combinations(range(n), 2):
            pw = (in3[:, x] & in3[:, y]).mean(); pwM = (in3M[:, x] & in3M[:, y]).mean()
            pu = (top2[:, x] & top2[:, y]).mean(); puM = (top2M[:, x] & top2M[:, y]).mean()
            ow = 0.775 / max(pwM, 1e-6); ou_ = 0.775 / max(puM, 1e-6)
            pairs.append((uma[x], uma[y], pw, pw * ow, ow, pu, pu * ou_, ou_))
        bw = sorted(pairs, key=lambda t: -t[3])[:8]; bu = sorted(pairs, key=lambda t: -t[6])[:8]
        print("  ワイド 見込み期待値上位: " + " ／ ".join(f"{x}-{y} {e:.2f}（{pw:.0%}×推定{o:.0f}倍）" for x, y, pw, e, o, *_ in bw))
        print("  馬連   見込み期待値上位: " + " ／ ".join(f"{x}-{y} {e:.2f}（{pu:.1%}×推定{o:.0f}倍）" for x, y, _, _, _, pu, e, o in bu))
        out[mode] = {"win": {uma[i]: float(win[i]) for i in range(n)}, "t3": {uma[i]: float(t3[i]) for i in range(n)},
                     "wide": [(x, y, round(pw, 4), round(e, 3), round(o, 1)) for x, y, pw, e, o, *_ in bw],
                     "umaren": [(x, y, round(pu, 4), round(e, 3), round(o, 1)) for x, y, _, _, _, pu, e, o in bu]}
    out["market_t3"] = {uma[i]: float(t3M[i]) for i in range(n)}
    (HERE / f"mc_draw_{race}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→ mc_draw_{race}.json")

if __name__ == "__main__":
    main()
