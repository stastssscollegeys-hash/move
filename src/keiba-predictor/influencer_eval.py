# -*- coding: utf-8 -*-
"""
influencer_eval.py — 予想家（チャンネル）ごとの的中率・回収率と、重み・独自指数への効果を測る（2026-10-30新規）
================================================================================================================
入力: daily_pdca/db/influencer_backfill/signals_hist/{日付}.json（エージェントが字幕から抽出した印）と races.json（結果）
見るもの
  1. チャンネル × 印の種類（本命・推奨・穴・消し・追い切り1位）ごとの 件数／勝率／3着内率／単勝回収率／複勝回収率
     ＋「人気（市場）から期待される勝率・3着内率」との差 → 人気馬を選んでいるだけなのか、人気を超えているのか
  2. 重み: 重み = 1 ＋ 係数 × (3着内率 − 期待3着内率) × 信頼度  信頼度 = n/(n+N0)  上下限 0.7〜1.4（件数が少ないほど1.0に寄せる）
  3. 独自指数への効果: 全馬について「市場の3着内確率のlogit」に「予想家スコア」を足すと対数尤度が改善するか（レース単位のブートストラップ）。
     スコアの重みは、そのレースを除いた分だけで作る（leave-one-race-out）＝自分の結果で重みを作って自分を測らない
使い方: python influencer_eval.py
"""
from __future__ import annotations
import collections, datetime, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import bet_engine as B
import combo_backtest as C

ROOT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "influencer_backfill"
POINTS = {"honmei": 3.0, "ana": 2.0, "posi": 1.0, "nega": -2.0, "oikiri1": 1.0}
KINDS = ["honmei", "posi", "ana", "nega", "oikiri1"]
N0, COEF, WMIN, WMAX = 10, 6.0, 0.7, 1.4
MIN_SHOW = 8


def load():
    races = {r["date"]: r for r in json.loads((ROOT / "races.json").read_text(encoding="utf-8"))}
    pay = C.load_pay()
    R = {}
    def num(x, d=99.0):
        try:
            return float(x)
        except (TypeError, ValueError):
            return d
    for d, r in races.items():
        hs = [dict(h, finish=num(h["finish"]), odds=num(h["odds"], 999.0), pop=num(h["pop"], 99.0)) for h in r["horses"]]
        q = np.array([1.0 / max(h["odds"], 1.0) for h in hs]); q /= q.sum()
        uma = [h["uma"] for h in hs]
        p3 = B.tables(q, uma)["複勝"][1]
        pp = pay.get(f"{d}|{r['venue']}|{r['R']}", {})
        H = {}
        for i, h in enumerate(hs):
            H[h["name"]] = dict(uma=h["uma"], finish=h["finish"], pop=h["pop"], odds=h["odds"], q=float(q[i]), p3=float(p3[i]),
                                win=1.0 if h["finish"] == 1 else 0.0, top3=1.0 if h["finish"] <= 3 else 0.0,
                                tan=pp.get("単勝", {}).get(str(h["uma"]), 0) / 100.0, fuku=pp.get("複勝", {}).get(str(h["uma"]), 0) / 100.0)
        R[d] = dict(name=r["name"], H=H)
    sig = []
    for f in sorted((ROOT / "signals_hist").glob("*.json")):
        try:
            for s in json.loads(f.read_text(encoding="utf-8")):
                if s["race_date"] in R and not s.get("flags", {}).get("post_race"):
                    sig.append(s)
        except Exception as e:
            print("読めない", f.name, e)
    return R, sig


def rows_from(sig, R):
    """(日付, チャンネル, 種類, 馬名) をチャンネル・レース・種類・馬ごとに1回だけ数える"""
    seen, out = set(), []
    for s in sig:
        for k in KINDS:
            for h in s.get(k, []) or []:
                nm = h["horse"] if isinstance(h, dict) else h
                if nm not in R[s["race_date"]]["H"]:
                    continue
                key = (s["race_date"], s["channel"], k, nm)
                if key not in seen:
                    seen.add(key)
                    out.append(key)
    return out


def boot_mean(x, n=2000, seed=1):
    a = np.asarray(x, float)
    if len(a) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    m = rng.choice(a, (n, len(a))).mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def stats(rows, R):
    if not rows:
        return None
    H = [R[d]["H"][nm] for d, _, _, nm in rows]
    n = len(H)
    top3 = np.array([h["top3"] for h in H]); p3 = np.array([h["p3"] for h in H])
    win = np.array([h["win"] for h in H]); q = np.array([h["q"] for h in H])
    tan = np.array([h["tan"] for h in H]); fuku = np.array([h["fuku"] for h in H])
    ex3 = top3 - p3
    lo, hi = boot_mean(ex3)
    return dict(n=n, win=win.mean(), exp_win=q.mean(), top3=top3.mean(), exp_top3=p3.mean(), excess3=ex3.mean(), ex3_lo=lo, ex3_hi=hi,
                tan=tan.mean(), fuku=fuku.mean(), pop=np.mean([h["pop"] for h in H]))


def weights(rows, R, exclude=None):
    """チャンネル×種類の重み（excludeのレース日付は使わない）"""
    by = collections.defaultdict(list)
    for r in rows:
        if r[0] != exclude:
            by[(r[1], r[2])].append(r)
    W = {}
    for key, rs in by.items():
        S = stats(rs, R)
        rel = S["n"] / (S["n"] + N0)
        sign = -1.0 if key[1] == "nega" else 1.0           # 消しは「3着内に来なかった」ほど価値がある
        W[key] = float(np.clip(1.0 + sign * COEF * S["excess3"] * rel, WMIN, WMAX))
    return W


def score_table(rows, R, W):
    """日付→馬名→スコア"""
    sc = collections.defaultdict(lambda: collections.defaultdict(float))
    cnt = collections.defaultdict(lambda: collections.defaultdict(set))
    for d, ch, k, nm in rows:
        sc[d][nm] += POINTS[k] * W.get((ch, k), 1.0)
        if k in ("honmei", "posi", "ana"):
            cnt[d][nm].add(ch)
    return sc, cnt


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def fit_logit(X, y, l2=1e-3, it=60):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        z = X @ b; pr = 1 / (1 + np.exp(-z))
        g = X.T @ (y - pr) - l2 * b
        Hm = (X * (pr * (1 - pr))[:, None]).T @ X + l2 * np.eye(X.shape[1])
        b = b + np.linalg.solve(Hm, g)
    return b


def loglik(b, X, y):
    z = X @ b; return float(np.sum(y * z - np.log1p(np.exp(z))))


def main():
    R, sig = load()
    rows = rows_from(sig, R)
    chans = sorted({s["channel"] for s in sig})
    print(f"レース {len({s['race_date'] for s in sig})}／動画 {len(sig)}／印の延べ {len(rows)}／チャンネル {len(chans)}")
    rep = dict(run=datetime.date.today().isoformat(), races=len(R), videos=len(sig), channels={})
    print("\n■ 全チャンネル合計（人気から期待される値との差）")
    print(f"  {'印':<8}{'件数':>6} 勝率  期待  3着内率 期待   差[95%区間]            単勝回収 複勝回収 平均人気")
    for k in KINDS:
        S = stats([r for r in rows if r[2] == k], R)
        if S:
            print(f"  {k:<8}{S['n']:>6} {S['win']*100:4.0f}% {S['exp_win']*100:4.0f}%  {S['top3']*100:4.0f}%  {S['exp_top3']*100:4.0f}%  {S['excess3']*100:+5.1f}pt[{S['ex3_lo']*100:+5.1f},{S['ex3_hi']*100:+5.1f}]  {S['tan']*100:6.0f}% {S['fuku']*100:6.0f}%  {S['pop']:.1f}")
            rep.setdefault("all", {})[k] = S
    print("\n■ チャンネル別（件数8以上の印だけ表示）")
    W_all = weights(rows, R)
    for ch in chans:
        lines = []
        for k in KINDS:
            S = stats([r for r in rows if r[1] == ch and r[2] == k], R)
            if S and S["n"] >= MIN_SHOW:
                lines.append(f"    {k:<8}{S['n']:>4}件 勝{S['win']*100:3.0f}%(期待{S['exp_win']*100:3.0f}) 3着内{S['top3']*100:3.0f}%(期待{S['exp_top3']*100:3.0f}) 差{S['excess3']*100:+5.1f}pt[{S['ex3_lo']*100:+5.1f},{S['ex3_hi']*100:+5.1f}] 単回{S['tan']*100:4.0f}% 複回{S['fuku']*100:4.0f}% 平均人気{S['pop']:.1f} → 重み{W_all.get((ch,k),1.0):.2f}")
            if S:
                rep["channels"].setdefault(ch, {})[k] = dict(S, weight=W_all.get((ch, k), 1.0))
        nv = sum(1 for s in sig if s["channel"] == ch)
        print(f"  ● {ch}（動画{nv}本）")
        print("\n".join(lines) if lines else "    （件数が少なく判定不能）")
    # 独自指数への効果（leave-one-race-out）
    print("\n■ 独自指数への効果（全馬・市場の3着内確率に予想家スコアを足す。重みはそのレースを除いて作成）")
    X, Y, G, SC, CN = [], [], [], [], []
    for d in sorted(R):
        if d not in {s["race_date"] for s in sig}:
            continue
        W = weights(rows, R, exclude=d)
        sc, cnt = score_table([r for r in rows if r[0] == d], R, W)
        for nm, h in R[d]["H"].items():
            X.append(logit(h["p3"])); Y.append(h["top3"]); G.append(d); SC.append(sc[d].get(nm, 0.0)); CN.append(len(cnt[d].get(nm, ())))
    X, Y, G, SC, CN = map(np.asarray, (X, Y, G, SC, CN))
    for lab, f in (("予想家スコア（重みつき）", SC), ("推した予想家の数", CN.astype(float))):
        A0 = np.c_[np.ones(len(X)), X]; A1 = np.c_[A0, f]
        b0, b1 = fit_logit(A0, Y), fit_logit(A1, Y)
        dll = loglik(b1, A1, Y) - loglik(b0, A0, Y)
        rng = np.random.default_rng(3); ds = sorted(set(G)); bs = []
        for _ in range(300):
            pick = rng.choice(ds, len(ds))
            idx = np.concatenate([np.where(G == d)[0] for d in pick])
            try:
                bs.append(fit_logit(np.c_[np.ones(len(idx)), X[idx], f[idx]], Y[idx])[2])
            except Exception:
                pass
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f"  {lab:<22} 係数 {b1[2]:+.3f} [{lo:+.3f}〜{hi:+.3f}]  対数尤度の改善 {dll:+.2f}（{len(Y)}頭・{len(ds)}レース）  → {'区間が0をまたぐ＝効果は確認できない' if lo <= 0 <= hi else '0を含まない＝効果あり'}")
        rep.setdefault("incremental", {})[lab] = dict(coef=float(b1[2]), lo=float(lo), hi=float(hi), dll=dll, n=int(len(Y)))
    (ROOT / "eval_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("\n保存:", ROOT / "eval_report.json")


if __name__ == "__main__":
    main()
