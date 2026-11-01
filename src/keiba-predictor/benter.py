# -*- coding: utf-8 -*-
"""
benter.py — データの予想と市場の予想を混ぜる「二段のモデル」（ベンター方式・2026-10-21）
=====================================================================================
ユーザー指示（2026-10-21）: 「最強の予想マシンではなく、年間収支がプラスになる予想を組み立てる仕組み。
  昔ビッグデータで予想の精度を上げた人と同じように学習し、データに基づく予想と市場の予想の両方を加味したベストを出す」

考え方（香港でビッグデータを使って勝ち続けた Bill Benter の方式）
  第1段  データだけの予想: オッズを一切見ずに、過去走・調教・騎手・厩舎・コース傾向などから「勝つ確率」を出す
         （条件付きロジット＝説明できる線形モデル と LightGBM＝組み合わせを拾う木のモデル の2本）
  第2段  混ぜる: 勝つ確率 ∝ exp( a×ln(市場の確率) ＋ b×データの予想の点数 )。a・b は「第1段が見ていない期間」で学習する
         → a と b の大きさが「市場とデータをどれだけ信じるか」の答えになる
  第3段  買う: 混ぜた確率×オッズ＞1 の馬だけ。金額はケリー基準の1/4（資金に比例・1R上限1万円・100円単位）

いまの ev_engine.py は「市場の確率を土台に、特徴量で少し動かす」1段の作り。データの予想が独立していないので、
データ側を木のモデルに替えたり、市場との混ぜ具合を確かめたりができない。ここではそれを分けて、年ごとに前向きに測る。

検証の約束（後付けの当たり探しにしない）
  ・Y年の予想 = 第1段は Y年より前だけで学習、第2段は「第1段の前向き予想が出ている Y年より前の年」だけで学習
  ・比べる相手: 市場だけ／いまのエンジン（同じ年ごとの学習）
  ・オッズは確定オッズ（締切直前に近い）。実際に買う時刻のオッズとはずれる → 採用は前向き台帳で確かめてから

使い方
  python benter.py --build      # 特徴量を一度だけ作って _cache/benter_feats.npz に保存（2006年〜の20年分・ev_engine.build・約30分）
  python benter.py              # 年ごとの学習と採点 → docs/keiba_benter.md・_cache/benter_probs.pkl（strategy_tournament と同じ形）
  python strategy_tournament.py --cache _cache/benter_probs.pkl --report docs/keiba_benter_tournament.md   # 馬連・ワイド等も同じ物差しで
"""
from __future__ import annotations
import argparse, math, pickle, sys, time
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings("ignore", message="X does not have valid feature names")

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
FEATS = HERE / "_cache" / "benter_feats.npz"
PROBS = HERE / "_cache" / "benter_probs.pkl"
DOC = HERE.parents[1] / "docs" / "keiba_benter.md"
FIRST = 2009            # 第1段の前向き予想を作り始める年（2006〜2008は学習だけ。20年分・2026-10-21）
L2 = 0.01
BANK0 = 1_000_000       # ケリーの試算の元手（年ごと）
CAP = 10_000            # 1レースの上限


# ── 特徴量を作る（1回だけ） ────────────────────────────────────────
DROP = ("race_id", "天候", "コース情報", "ラップ", "着差", "後3F", "頭数", "中日数")      # ev_engine が使わない列（メモリ節約）


def lean_rows(folders):
    """20年分を載せるため: 使わない列を捨て、騎手名などの繰り返す文字列を1つにまとめる"""
    import json
    rows = []
    for fo in folders:
        for f in sorted(Path(fo).glob("results_*.json")):
            for r in json.loads(f.read_text(encoding="utf-8")):
                if str(r.get("距離") or "").startswith("障"):
                    continue
                for k in DROP:
                    r.pop(k, None)
                for k, v in r.items():
                    if isinstance(v, str) and len(v) < 40:
                        r[k] = sys.intern(v)
                rows.append(r)
            print(f"  読み込み {f.name}: 累計{len(rows):,}頭", flush=True)
    return rows


def build():
    import os
    os.environ["LEAN"] = "1"
    import ev_engine as E
    import predict_day as P
    folders = [Path(P.HIST).parent / "history_target_old", Path(P.HIST)]     # 2006〜2015（target_import --out）＋ 2016〜
    E.load_rows = lambda: lean_rows([f for f in folders if f.exists()])
    E.KEEP = list(range(len(E.F_ALL)))                 # 採用・不採用に関係なく全部の特徴量を作る（第1段はここから学ぶ）
    t0 = time.time()
    races, _ = E.build()
    races = [r for r in races if r["win"] >= 0]
    # 1つの圧縮ファイルに: 馬ごとの行列を縦に積み、レースの区切り（start）を持つ
    n = np.array([len(r["q"]) for r in races])
    start = np.concatenate([[0], np.cumsum(n)])
    FEATS.parent.mkdir(exist_ok=True)
    np.savez_compressed(FEATS, X=np.concatenate([r["X"] for r in races]).astype(np.float32),
                        q=np.concatenate([r["q"] for r in races]).astype(np.float32),
                        odds=np.concatenate([r["odds"] for r in races]).astype(np.float32),
                        uma=np.concatenate([r["uma"] for r in races]).astype(np.int16),
                        fins=np.concatenate([[f or 0 for f in r["fins"]] for r in races]).astype(np.int16),
                        start=start, win=np.array([r["win"] for r in races]),
                        key=np.array(["|".join(map(str, r["key"])) for r in races]), names=np.array(E.F_ALL))
    print(f"保存: {FEATS}（{len(races):,}レース・特徴量{len(E.F_ALL)}・{(time.time()-t0)/60:.1f}分）")


def load_feats():
    z = np.load(FEATS)
    s, X, q, o, u, fi, w = z["start"], z["X"], z["q"], z["odds"], z["uma"], z["fins"], z["win"]
    races = []
    for i, k in enumerate(z["key"]):
        a, b = s[i], s[i + 1]
        d, v, R = k.split("|")
        races.append(dict(key=(d, v, int(R)), X=X[a:b], q=q[a:b], odds=o[a:b], uma=list(u[a:b]), fins=[int(x) or None for x in fi[a:b]], win=int(w[i])))
    return list(z["names"]), races


# ── 条件付きロジット（レースの中で softmax） ─────────────────────────
def pack(races, cols):
    """cols(r) → (頭数, k) の行列。戻り: X(R,H,k) M(R,H) win(R)"""
    R, H = len(races), max(len(r["q"]) for r in races)
    k = cols(races[0]).shape[1]
    X, M, win = np.zeros((R, H, k), np.float32), np.zeros((R, H), bool), np.zeros(R, int)
    for i, r in enumerate(races):
        n = len(r["q"])
        X[i, :n], M[i, :n], win[i] = cols(r), True, r["win"]
    return X, M, win


def _P(X, M, w):
    U = np.where(M, X @ w.astype(np.float32), -1e9)
    U -= U.max(axis=1, keepdims=True)
    E = np.exp(U) * M
    return E / E.sum(axis=1, keepdims=True)


def fit_clogit(X, M, win, l2=L2, free=()):
    """free: 正則化しない列（市場の確率など）"""
    from scipy.optimize import minimize
    R, k = len(win), X.shape[2]
    idx = np.arange(R)
    pen = np.ones(k); pen[list(free)] = 0.0

    def negll(w):
        P = _P(X, M, w)
        ll = np.log(np.maximum(P[idx, win], 1e-300)).sum() / R - 0.5 * l2 * (pen * w * w).sum()
        g = (X[idx, win] - np.einsum("rh,rhk->rk", P, X)).sum(axis=0) / R - l2 * pen * w
        return -ll, -g.astype(np.float64)

    w0 = np.zeros(k)
    return minimize(negll, w0, jac=True, method="L-BFGS-B", options={"maxiter": 600}).x


def probs_of(r, cols, w):
    u = cols(r) @ w
    u -= u.max()
    e = np.exp(u)
    return e / e.sum()


# ── 第1段: データだけ ───────────────────────────────────────────────
class Stage1:
    """オッズを見ない。X は年ごとに学習区間の平均・標準偏差でそろえる。市場に由来する列（市場評価より勝つ度合い等）は過去のレースの結果なので使ってよい"""

    def __init__(self, train, names):
        allX = np.concatenate([r["X"] for r in train])
        self.mu, self.sd = allX.mean(axis=0), allX.std(axis=0) + 1e-6
        self.keep = np.where(allX.std(axis=0) > 1e-6)[0]
        del allX
        z = lambda r: ((r["X"] - self.mu) / self.sd)[:, self.keep]
        self.w = fit_clogit(*pack(train, z))
        self.z = z
        # LightGBM: 馬ごとの「勝ったか」を、レース内の相対値（各特徴量−そのレースの平均）も足して学習
        import lightgbm as lgb
        Xg = np.concatenate([self.rel(r) for r in train])
        yg = np.concatenate([(np.arange(len(r["q"])) == r["win"]).astype(int) for r in train])
        # （2026-10-21 10年分の検証で、オッズを見ない木のモデルは市場に何も足さなかった→外した）
        # 木のモデル（市場の誤りだけを学ぶ）: 出発点を市場の確率（init_score=logit(q)）にして、市場とのずれだけを木で足す（2026-10-21）
        qg = np.concatenate([np.clip(r["q"] / r["q"].sum(), 1e-4, 0.99) for r in train])
        self.gr = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=15, min_child_samples=1000,
                                     subsample=0.8, subsample_freq=1, colsample_bytree=0.5, reg_lambda=5.0, verbose=-1)
        self.gr.fit(Xg, yg, init_score=np.log(qg / (1 - qg)))
        del Xg, yg, qg

    def rel(self, r):
        z = ((r["X"] - self.mu) / self.sd)[:, self.keep]
        return np.hstack([z, z - z.mean(axis=0, keepdims=True)])

    def score(self, r):
        """戻り: (ロジットの点数, LightGBM の点数)。どちらも『レース内の相対的な強さ』として第2段に渡す"""
        s_cl = self.z(r) @ self.w
        s_res = self.gr.predict(self.rel(r), raw_score=True)          # 市場からのずれ（対数オッズの足し分）
        return s_cl - s_cl.mean(), s_res - s_res.mean()


# ── 年ごとの前向き検証 ──────────────────────────────────────────────
def walk():
    names, races = load_feats()
    years = sorted({r["key"][0][:4] for r in races})
    by_y = {y: [r for r in races if r["key"][0][:4] == y] for y in years}
    lq = lambda r: np.log(r["q"])[:, None]
    # 1) 第1段の前向きの点数（Y年 = Y年より前で学習）と、いまのエンジン（市場＋特徴量の1段）の前向き確率
    for y in years:
        if int(y) < FIRST:
            continue
        tr = [r for yy in years if yy < y for r in by_y[yy]]
        t0 = time.time()
        s1 = Stage1(tr, names)
        cur_cols = lambda r: np.hstack([lq(r), s1.z(r)])
        wc = fit_clogit(*pack(tr, cur_cols), free=(0,))
        for r in by_y[y]:
            r["s_cl"], r["s_res"] = s1.score(r)
            r["p_cur"] = probs_of(r, cur_cols, wc)
            r["u_cur"], r["wc0"] = (s1.z(r) @ wc[1:]).astype(np.float32), float(wc[0])     # 発走前のオッズで計算し直すため（--late）
            r["p_d"] = probs_of(r, lambda rr: rr["s_cl"][:, None], np.array([1.0]))      # データだけ（ロジット）
        print(f"  第1段 {y}: 学習{len(tr):,}R → {len(by_y[y]):,}R（{(time.time()-t0)/60:.1f}分）", flush=True)
        del s1
    # 2) 第2段: 混ぜ方を「第1段の前向き点数がある、Y年より前の年」で学習
    variants = {
        "混合（ロジット）": lambda r: np.hstack([lq(r), r["s_cl"][:, None]]),
        "市場＋木（ずれ）": lambda r: np.hstack([lq(r), r["s_res"][:, None]]),
        "市場＋木（ずれ）＋いまのエンジン": lambda r: np.hstack([np.log(r["p_cur"])[:, None], r["s_res"][:, None]]),
    }
    mix_w = {}
    for y in years:
        if int(y) <= FIRST:
            continue
        tr = [r for yy in years if FIRST <= int(yy) < int(y) for r in by_y[yy]]
        for name, cols in variants.items():
            w = fit_clogit(*pack(tr, cols), l2=0.0)
            mix_w[(y, name)] = w
            for r in by_y[y]:
                r.setdefault("pv", {})[name] = probs_of(r, cols, w)
                r.setdefault("mw", {})[name] = w
    test_years = [y for y in years if int(y) > FIRST]
    report(by_y, test_years, mix_w, variants)


# ── 採点 ───────────────────────────────────────────────────────────
def boot(x, n=2000, seed=1):
    rng = np.random.default_rng(seed)
    m = np.concatenate([rng.choice(x, size=(200, len(x))).mean(axis=1) for _ in range(n // 200)])
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def roi_ci(st, rt, n=2000, seed=1):
    if st.sum() == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    xs = []
    for _ in range(n // 200):
        idx = rng.integers(0, len(st), size=(200, len(st)))
        s, r_ = st[idx].sum(axis=1), rt[idx].sum(axis=1)
        xs.append(r_[s > 0] / s[s > 0])
    x = np.concatenate(xs)
    return rt.sum() / st.sum(), np.percentile(x, 2.5), np.percentile(x, 97.5)


def flat(races, pk, thr, cap=None):
    st, rt = [], []
    for r in races:
        p = pk(r)
        sel = np.where((p * r["odds"] >= thr) & ((r["odds"] <= cap) if cap else True))[0]
        st.append(100.0 * len(sel))
        rt.append(100.0 * r["odds"][r["win"]] if r["win"] in sel else 0.0)
    return np.array(st), np.array(rt)


def kelly(races, pk, frac=0.25, thr=1.0):
    """1/4ケリー: 期待値>thr の馬に 資金×frac×(p×o−1)/(o−1)。100円単位に切り下げ・1R上限1万円。戻り: 年末資金／元手, 賭けた総額"""
    bank, total = float(BANK0), 0.0
    for r in sorted(races, key=lambda r: r["key"]):
        p, o = pk(r), r["odds"].astype(float)
        f = np.where(p * o >= thr, frac * (p * o - 1) / np.maximum(o - 1, 1e-9), 0.0)
        stake = np.floor(bank * f / 100) * 100
        if stake.sum() > CAP:
            stake = np.floor(stake * CAP / stake.sum() / 100) * 100
        if stake.sum() <= 0:
            continue
        total += stake.sum()
        bank += stake[r["win"]] * o[r["win"]] - stake.sum()
    return bank / BANK0, total


def report(by_y, years, mix_w, variants):
    models = {"市場だけ": lambda r: r["q"] / r["q"].sum(), "データだけ": lambda r: r["p_d"], "いまのエンジン": lambda r: r["p_cur"]}
    models.update({k: (lambda k: lambda r: r["pv"][k])(k) for k in variants})
    L = ["# データの予想と市場の予想を混ぜる二段のモデル（ベンター方式）\n",
         f"作成 {time.strftime('%Y-%m-%d %H:%M')}。年ごとの前向き検証（{years[0]}〜{years[-1]}）。第1段は各年より前だけで学習、第2段（混ぜ方）は第1段の前向き予想がある前年までで学習。",
         "オッズは確定オッズ。実際に買う時刻のオッズとはずれるので、採用は前向き台帳で確かめてから。\n",
         "## 1. 予想の正確さ（1レースあたりの対数尤度・市場だけとの差。大きいほど良い）\n",
         "| 年 | レース | " + " | ".join(m for m in models if m != "市場だけ") + " |", "|---|---:|" + "---:|" * (len(models) - 1)]
    allg = {m: [] for m in models}
    for y in years:
        rs = by_y[y]
        base = np.array([math.log(max(models["市場だけ"](r)[r["win"]], 1e-300)) for r in rs])
        cells = []
        for m, pk in models.items():
            if m == "市場だけ":
                continue
            g = np.array([math.log(max(pk(r)[r["win"]], 1e-300)) for r in rs]) - base
            allg[m].append(g)
            cells.append(f"{g.mean():+.5f}")
        L.append(f"| {y} | {len(rs):,} | " + " | ".join(cells) + " |")
    L.append("| 全年 | " + f"{sum(len(by_y[y]) for y in years):,} | " + " | ".join(
        f"**{np.concatenate(allg[m]).mean():+.5f}**［{boot(np.concatenate(allg[m]))[0]:+.5f}, {boot(np.concatenate(allg[m]))[1]:+.5f}］" for m in models if m != "市場だけ") + " |")
    L.append("| 市場より良かった年 | | " + " | ".join(f"{sum(1 for g in allg[m] if g.mean() > 0)}/{len(years)}" for m in models if m != "市場だけ") + " |")
    L += ["\n## 2. 混ぜ方（第2段の重み）\n", "市場の重み＝ln(市場の確率)の係数（1なら市場をそのまま信じる）。データの重みが0なら、データは市場に何も足していない。\n",
          "| 年 | " + " | ".join(variants) + " |", "|---|" + "---|" * len(variants)]
    for y in years:
        L.append(f"| {y} | " + " | ".join("市場 {:.2f}・データ {}".format(mix_w[(y, k)][0], "・".join(f"{x:.2f}" for x in mix_w[(y, k)][1:])) for k in variants) + " |")
    L += ["\n## 3. 単勝で買ったら（混ぜた確率×オッズ≧しきい値の馬に100円ずつ）\n",
          "| モデル | しきい値 | 点数 | 回収率 | 95%区間 | 年別 |", "|---|---:|---:|---:|---|---|"]
    allr = [r for y in years for r in by_y[y]]
    for m, pk in models.items():
        if m == "市場だけ":
            continue
        for thr, cap in ((1.0, None), (1.1, None), (1.2, None), (1.1, 20.0)):
            st, rt = flat(allr, pk, thr, cap)
            roi, lo, hi = roi_ci(st, rt)
            if roi is None:
                continue
            yr = []
            for y in years:
                s2, r2 = flat(by_y[y], pk, thr, cap)
                yr.append(f"{r2.sum()/s2.sum()*100:.0f}" if s2.sum() else "-")
            L.append(f"| {m} | {thr:.1f}{'（20倍以下）' if cap else ''} | {int(st.sum()/100):,} | {roi*100:.1f}% | {lo*100:.1f}〜{hi*100:.1f}% | {'・'.join(yr)} |")
    L += ["\n## 4. 資金の増え方（1/4ケリー・元手100万円を毎年リセット・1R上限1万円・100円単位）\n",
          "| モデル | " + " | ".join(years) + " | 年平均 |", "|---|" + "---:|" * (len(years) + 1)]
    for m, pk in models.items():
        if m == "市場だけ":
            continue
        g = [kelly(by_y[y], pk) for y in years]
        L.append(f"| {m} | " + " | ".join(f"{x*100:.0f}%" for x, _ in g) + f" | {np.mean([x for x, _ in g])*100:.0f}% |")
    L.append("\n（100%＝元手どおり。各セルは年末の資金÷元手。）")
    text = "\n".join(L)
    DOC.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n保存: {DOC}")
    best = "市場＋木（ずれ）＋いまのエンジン"
    out = [dict(key=r["key"], uma=r["uma"], odds=r["odds"].astype(float), q=r["q"].astype(float), p=r["pv"][best], fins=r["fins"],
                p_res=r["pv"]["市場＋木（ずれ）"], s_res=r["s_res"].astype(np.float32), w_res=r["mw"]["市場＋木（ずれ）"], u_cur=r["u_cur"], wc0=r["wc0"],
                w_both=r["mw"][best], win=r["win"]) for r in allr]
    PROBS.write_bytes(pickle.dumps(out))
    print(f"保存: {PROBS}（{best}・{len(out):,}レース）")


# ── 本番用（当日の自動運転で使う）: 全年で学習した木のモデル＋混ぜ方 ─────────────────────
LIVE = HERE / "_cache" / "benter_live.pkl"
RULE_B1 = "B1"      # 2026-10-21 事前登録: 市場＋木（ずれ）の単勝・発走30分前ごろのオッズで 確率×オッズ≧1.0 の馬に100円ずつ


class LiveModel:
    """Stage1 の木の部分だけ（ロジットは使わない）。score_res(X) → 市場からのずれ（レース内で平均0）"""

    def __init__(self, names, races, w_res):
        import lightgbm as lgb
        allX = np.concatenate([r["X"] for r in races])
        self.names = list(names)
        self.mu, self.sd = allX.mean(axis=0), allX.std(axis=0) + 1e-6
        self.keep = np.where(allX.std(axis=0) > 1e-6)[0]
        del allX
        Xg = np.concatenate([self.rel(r["X"]) for r in races])
        yg = np.concatenate([(np.arange(len(r["q"])) == r["win"]).astype(int) for r in races])
        qg = np.concatenate([np.clip(r["q"] / r["q"].sum(), 1e-4, 0.99) for r in races])
        self.gr = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=15, min_child_samples=1000,
                                     subsample=0.8, subsample_freq=1, colsample_bytree=0.5, reg_lambda=5.0, verbose=-1)
        self.gr.fit(Xg, yg, init_score=np.log(qg / (1 - qg)))
        self.w_res = np.asarray(w_res, float)
        self.last = max(r["key"][0] for r in races)
        self.n = len(races)

    def rel(self, X):
        z = ((np.asarray(X, np.float32) - self.mu) / self.sd)[:, self.keep]
        return np.hstack([z, z - z.mean(axis=0, keepdims=True)])

    def score_res(self, X):
        s = self.gr.predict(self.rel(X), raw_score=True)
        return s - s.mean()

    def probs(self, s_res, odds):
        """発走前のオッズで市場の確率を作り直して混ぜる"""
        o = np.asarray(odds, float)
        q = (1 / o) / (1 / o).sum()
        u = self.w_res[0] * np.log(q) + self.w_res[1] * s_res
        u -= u.max()
        e = np.exp(u)
        return e / e.sum()


def fit_live():
    """全年（2006〜）で木のモデルを学習。混ぜ方は前向き検証の最新の年の重み（それより前の年の前向き点数で学習したもの）"""
    t0 = time.time()
    names, races = load_feats()
    pr = pickle.loads(PROBS.read_bytes())
    lastp = max(pr, key=lambda r: r["key"])
    w_res = lastp["w_res"]
    del pr
    from benter import LiveModel as LM          # python benter.py で動かしても ev_live から読めるように（__main__ で保存しない）
    m = LM(names, races, w_res)
    imp = sorted(zip(m.gr.feature_importances_, [f"{names[i]}" for i in m.keep] + [f"{names[i]}（レース内の差）" for i in m.keep]), reverse=True)
    LIVE.write_bytes(pickle.dumps(m))
    print(f"保存: {LIVE}（{m.n:,}レース・〜{m.last}・混ぜ方 市場{w_res[0]:.3f}・木{w_res[1]:.3f}・{(time.time()-t0)/60:.1f}分）")
    print("よく使う特徴量（分岐の回数）:")
    for v, n in imp[:25]:
        print(f"  {v:>4}  {n}")


def load_live():
    return pickle.loads(LIVE.read_bytes()) if LIVE.exists() else None


# ── 前日予想の精度（2026-10-21・ユーザー「当日はこのままで、前日予想の精度を上げる方法を探して」） ─────────────
# 前日に分からない列（馬体重・当日の馬場の偏り・今回の道悪）を消した「前日専用の木」を年ごとに前向きで学習し、
# 前日の最終オッズ（時系列オッズ 0B41 の前日分・2023〜）を市場として、①どれだけ当てられるか ②前日に選んだ馬が確定オッズで回収できるか を測る
DAYOF = ["馬体重 増減（10kg単位）", "馬体重 10kg以上減", "馬体重 10kg以上増", "馬体重（470kgとの差・40kg単位）", "馬体重 439kg以下",
         "休み明け×体重の減り（10kg単位）", "中5週以内×12kg以上増", "牝馬×増減の大きさ（10kg単位）", "レースで一番軽い",
         "好走時の体重との離れ（10kg単位）", "ダート×馬体重（470kgとの差）",
         "当日の内枠有利度×内枠", "当日の内枠有利度×外枠", "当日の前残り度×前で運ぶ割合", "今回道悪×道悪で3着内の経験", "今回道悪×道悪の経験なし"]
GROUPS = [("調教", ("調教",)), ("時計の指数", ("時計", "指数")), ("騎手", ("騎手",)), ("厩舎", ("厩舎",)), ("血統", ("種牡馬", "母父")),
          ("コース・条件の傾向", ("傾向", "このレース")), ("前走の内容", ("前走",)), ("近走・経験", ("直近", "キャリア", "経験", "馬自身")),
          ("条件の変化（距離・間隔・クラス）", ("距離", "間隔", "芝ダ", "クラス", "乗り替わり")), ("馬場の偏り（前日・先週）", ("前日の", "先週", "柵")),
          ("展開（先行争い）", ("先行争い", "単騎")), ("斤量・性齢・枠", ("斤量", "牝馬", "歳", "馬番"))]


def group_of(name):
    for g, keys in GROUPS:
        if any(k in name for k in keys):
            return g
    return "その他"


def prevday_odds():
    """{(日付, 場, R): {馬番: 前日の最終オッズ}}（発走日の前日までの最後の発表）"""
    import glob
    from target_import import VENUE
    out = {}
    for f in sorted(glob.glob(str(Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "ts_odds_20*.pkl"))):
        for k, v in pickle.loads(Path(f).read_bytes()).items():
            if v["snaps"] and v["snaps"][0][0][:4] < k[4:8]:
                out[(k[:8], VENUE.get(k[8:10], "?"), int(k[14:16]))] = v["snaps"][0][1]
    return out


def eve(first_test=2016):
    import lightgbm as lgb
    from benter import LiveModel as LM
    names, races = load_feats()
    ix = {n: i for i, n in enumerate(names)}
    cols = [ix[n] for n in DAYOF if n in ix]
    for r in races:
        r["X"][:, cols] = 0.0                         # 前日には分からない（学習でも使わない）
    years = sorted({r["key"][0][:4] for r in races})
    by_y = {y: [r for r in races if r["key"][0][:4] == y] for y in years}
    pv = prevday_odds()
    imp = None
    ck_f = HERE / "_cache" / "benter_eve_s.pkl"           # 途中で止まっても続きから（年ごとの点数を保存）
    ck = pickle.loads(ck_f.read_bytes()) if ck_f.exists() else {}
    for y in years:
        if int(y) < first_test:
            continue
        if y in ck and y != years[-1]:
            for r, sv in zip(by_y[y], ck[y]):
                r["s_eve"] = sv
            print(f"  前日の木 {y}: 保存済み", flush=True)
            continue
        t0 = time.time()
        m = LM(names, [r for yy in years if yy < y for r in by_y[yy]], (1.0, 1.0))
        for r in by_y[y]:
            r["s_eve"] = m.score_res(r["X"]).astype(np.float32)
        ck[y] = [r["s_eve"] for r in by_y[y]]
        ck_f.write_bytes(pickle.dumps(ck))
        imp = (m, m.gr.booster_.feature_importance("gain"))
        print(f"  前日の木 {y}: 学習〜{int(y)-1} → {len(by_y[y]):,}R（{(time.time()-t0)/60:.1f}分）", flush=True)
        del m
    # 混ぜ方: その年より前の前向きの点数で学習（確定オッズの市場）
    test = [y for y in years if int(y) > first_test]
    lq = lambda r: np.log(r["q"] / r["q"].sum())[:, None]
    for y in test:
        tr = [r for yy in years if first_test <= int(yy) < int(y) for r in by_y[yy]]
        w = fit_clogit(*pack(tr, lambda r: np.hstack([lq(r), r["s_eve"][:, None]])), l2=0.0)
        for r in by_y[y]:
            r["w_eve"] = w
    # 採点（前日オッズのある 2023〜）
    def soft(u):
        u = u - u.max(); e = np.exp(u); return e / e.sum()
    rows = []
    for y in test:
        for r in by_y[y]:
            od = pv.get(r["key"])
            if not od:
                continue
            o_pv = np.array([od.get(int(u)) or np.nan for u in r["uma"]], float)
            if np.isnan(o_pv).any() or (o_pv <= 0).any():
                continue
            q_pv = (1 / o_pv) / (1 / o_pv).sum()
            q_fn = r["q"] / r["q"].sum()
            w = r["w_eve"]
            rows.append(dict(key=r["key"], win=r["win"], o_pv=o_pv, o_fn=np.asarray(r["odds"], float), q_pv=q_pv, q_fn=q_fn,
                             p_pv=soft(w[0] * np.log(q_pv) + w[1] * r["s_eve"]), p_fn=soft(w[0] * np.log(q_fn) + w[1] * r["s_eve"]),
                             fins=r["fins"], uma=r["uma"], s_eve=r["s_eve"]))
    ll = lambda k: np.array([math.log(max(x[k][x["win"]], 1e-300)) for x in rows])
    L = ["\n## 6. 前日予想の精度（前日に分からない馬体重・当日の馬場の偏り・今回の道悪を消した前日専用の木）\n",
         f"前日の最終オッズ（時系列オッズの前日分）があるレース {len(rows):,}（{rows[0]['key'][0]}〜{rows[-1]['key'][0]}）。木はその年より前だけで学習。\n",
         "| 比べるもの | 1レースの対数尤度（前日の市場との差） | 1着馬に付けた確率の平均 |", "|---|---:|---:|"]
    base = ll("q_pv")
    for lab, k in (("前日の市場（前日オッズ）", "q_pv"), ("前日の市場＋前日専用の木", "p_pv"), ("確定オッズの市場（参考: 前日から締切までに市場が覚えること）", "q_fn"), ("確定オッズ＋前日専用の木", "p_fn")):
        g = ll(k) - base
        lo, hi = boot(g)
        L.append(f"| {lab} | {g.mean():+.5f}［{lo:+.5f}, {hi:+.5f}］ | {np.mean([x[k][x['win']] for x in rows])*100:.2f}% |")
    # 3着内
    def top3(k):
        h = []
        for x in rows:
            i = int(np.argmax(x[k]))
            h.append(bool(x["fins"][i] and x["fins"][i] <= 3))
        return np.mean(h) * 100
    L += ["\n| 本命（確率1位）の3着内率 | 前日の市場 | 前日の市場＋木 |", "|---|---:|---:|",
          f"| 全レース | {top3('q_pv'):.1f}% | {top3('p_pv'):.1f}% |"]
    # 前日に選んで確定オッズで払う
    L += ["\n| 前日に選ぶ条件（確率は前日オッズ＋木） | 点数 | 回収率（確定オッズで払う） | 95%区間 | 年別 |", "|---|---:|---:|---|---|"]
    for lab, f in (("確率×前日オッズ≧1.0", lambda x: x["p_pv"] * x["o_pv"] >= 1.0), ("確率×前日オッズ≧1.1", lambda x: x["p_pv"] * x["o_pv"] >= 1.1),
                   ("確率×前日オッズ≧1.2", lambda x: x["p_pv"] * x["o_pv"] >= 1.2), ("確率÷前日の市場≧1.3・前日20倍以下", lambda x: (x["p_pv"] / x["q_pv"] >= 1.3) & (x["o_pv"] <= 20)),
                   ("（参考）前日の1番人気", lambda x: np.arange(len(x["q_pv"])) == np.argmax(x["q_pv"]))):
        st, rt, yr = [], [], {}
        for x in rows:
            sel = np.where(f(x))[0]
            a, b = 100.0 * len(sel), (100.0 * x["o_fn"][x["win"]] if x["win"] in sel else 0.0)
            st.append(a); rt.append(b)
            yy = x["key"][0][:4]; yr.setdefault(yy, [0.0, 0.0]); yr[yy][0] += a; yr[yy][1] += b
        roi, lo, hi = roi_ci(np.array(st), np.array(rt))
        L.append(f"| {lab} | {int(sum(st)/100):,} | {roi*100:.1f}% | {lo*100:.1f}〜{hi*100:.1f}% | " + "・".join(f"{k}:{b/a*100:.0f}" for k, (a, b) in sorted(yr.items()) if a) + " |")
    # 何が効いているか（最新年の木・分岐で減らした誤差の合計をグループ別に）
    m, gain = imp
    labs = [names[i] for i in m.keep] * 2
    gg = {}
    for v, n in zip(gain, labs):
        gg[group_of(n)] = gg.get(group_of(n), 0.0) + v
    tot = sum(gg.values())
    L += ["\n| 前日の木がよく使う要素（グループ） | 割合 |", "|---|---:|"] + [f"| {g} | {v/tot*100:.1f}% |" for g, v in sorted(gg.items(), key=lambda t: -t[1])]
    text = "\n".join(L)
    print(text)
    with open(DOC, "a", encoding="utf-8") as fo:
        fo.write("\n" + text + "\n")
    (HERE / "_cache" / "benter_eve.pkl").write_bytes(pickle.dumps(rows))
    print(f"追記: {DOC}")


# ── 発走前のオッズで買ったら（2023〜・JV の時系列オッズ 0B41） ─────────────────────
def late():
    """確定オッズで選ぶと「締切後にしか分からない情報」で選んだことになる。実際に買えるのは発走の数分前。
    ここでは 発走 m 分前の単勝オッズ で確率を計算し直して買う馬を選び、払い戻しは確定オッズで受け取る（パリミュチュエル）。"""
    import glob
    sys.path.insert(0, str(HERE))
    from target_import import VENUE
    races = pickle.loads(PROBS.read_bytes())
    by = {r["key"]: r for r in races}
    ts = {}
    for f in sorted(glob.glob(str(Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "ts_odds_20*.pkl"))):
        for k, v in pickle.loads(Path(f).read_bytes()).items():
            key = (k[:8], VENUE.get(k[8:10], "?"), int(k[14:16]))
            if key in by:
                ts[key] = v
    print(f"時系列オッズのあるレース {len(ts):,}")

    def at(v, mins):
        """発走 mins 分前までの最後の発表"""
        import datetime as dt
        y = 2000
        P = dt.datetime.strptime(f"{y}{v['post']}", "%Y%m%d%H%M")
        cut = P - dt.timedelta(minutes=mins)
        best = None
        for t, od in v["snaps"]:
            T = dt.datetime.strptime(f"{y}{t}", "%Y%m%d%H%M")
            if T <= cut:
                best = od
        return best

    def soft(u):
        u = u - u.max()
        e = np.exp(u)
        return e / e.sum()

    L = ["\n## 5. 発走前のオッズで選んで買ったら（2023年〜・払い戻しは確定オッズ）\n",
         "確定オッズで選ぶのは本当は不可能（締切後に決まる）。発走 m 分前の単勝オッズで確率を計算し直し、そのときの オッズ×確率 で買う馬を選ぶ。\n",
         "| モデル | 選ぶ時点 | しきい値 | レース | 点数 | 回収率 | 95%区間 | 年別 |", "|---|---|---:|---:|---:|---:|---|---|"]
    import os
    names_ = ("市場＋木（ずれ）",) if os.environ.get("LATE_RATIO") == "1" else ("市場＋木（ずれ）", "いまのエンジン", "市場＋木（ずれ）＋いまのエンジン")
    rules = ((1.3, 20.0, "比"), (1.5, 20.0, "比"), (1.2, 20.0, "比")) if os.environ.get("LATE_RATIO") == "1" else ((1.0, None, "EV"), (1.1, None, "EV"), (1.1, 20.0, "EV"))
    for name in names_:
        for mins in (None, 5, 10, 30):
            for thr, cap, kind in rules:
                st, rt, yrs = [], [], {}
                n = 0
                for key, v in ts.items():
                    r = by[key]
                    o_fin = np.asarray(r["odds"], float)
                    if mins is None:
                        o = o_fin
                    else:
                        od = at(v, mins)
                        if not od:
                            continue
                        o = np.array([od.get(int(u)) or np.nan for u in r["uma"]], float)
                        if np.isnan(o).any() or (o <= 0).any():
                            continue
                    q = (1 / o) / (1 / o).sum()
                    lq = np.log(q)
                    if name == "市場＋木（ずれ）":
                        p = soft(r["w_res"][0] * lq + r["w_res"][1] * r["s_res"])
                    else:
                        pc = soft(r["wc0"] * lq + r["u_cur"])
                        p = pc if name == "いまのエンジン" else soft(r["w_both"][0] * np.log(pc) + r["w_both"][1] * r["s_res"])
                    crit = p / q if kind == "比" else p * o           # 比＝モデルの確率÷そのときの市場の確率（2026-10-21 戦略トーナメントで確認期間も下限>100%）
                    sel = np.where((crit >= thr) & ((o <= cap) if cap else True))[0]
                    n += 1
                    s_ = 100.0 * len(sel)
                    r_ = 100.0 * o_fin[r["win"]] if r["win"] in sel else 0.0
                    st.append(s_); rt.append(r_)
                    yy = key[0][:4]
                    yrs.setdefault(yy, [0.0, 0.0]); yrs[yy][0] += s_; yrs[yy][1] += r_
                st, rt = np.array(st), np.array(rt)
                roi, lo, hi = roi_ci(st, rt)
                if roi is None:
                    continue
                L.append(f"| {name} | {'確定オッズ' if mins is None else f'{mins}分前'} | {'比' if kind == '比' else ''}{thr:.1f}{'（20倍以下）' if cap else ''} | {n:,} | {int(st.sum()/100):,} | {roi*100:.1f}% | {lo*100:.1f}〜{hi*100:.1f}% | "
                         + "・".join(f"{y}:{b/a*100:.0f}" for y, (a, b) in sorted(yrs.items()) if a) + " |")
    text = "\n".join(L)
    print(text)
    with open(DOC, "a", encoding="utf-8") as fo:
        fo.write("\n" + text + "\n")
    print(f"追記: {DOC}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--late", action="store_true", help="発走前のオッズで選んだときの回収率（walk の後）")
    ap.add_argument("--fit-live", action="store_true", help="本番用の木のモデルを全年で学習して _cache/benter_live.pkl に保存")
    ap.add_argument("--eve", action="store_true", help="前日予想の精度（前日に分からない列を消した木・前日オッズで採点）")
    a = ap.parse_args()
    build() if a.build else late() if a.late else fit_live() if a.fit_live else eve() if a.eve else walk()
