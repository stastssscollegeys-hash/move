# -*- coding: utf-8 -*-
"""
market_calib_audit.py — 市場オッズそのものの歪み（人気馬が過小評価・人気薄が過大評価）を測る（2026-10-02）
======================================================================================================
prob_core は 単勝オッズ → 1/odds を正規化 → そのまま勝率 としている（γ=1）。
競馬の単勝市場は一般に「人気薄が買われすぎる」ことが知られており、もしそれが自前データでも再現するなら
    p_i ∝ q_i^γ   （γ>1 で人気馬を上げ、人気薄を下げる）
と1つの係数で直すほうが、確率の土台として正確になる。

馬ごとの因子ではなく**市場の読み方**の補正なので、結果リークの心配はない（使うのは確定単勝オッズと着順だけ）。
ただし在サンプルの発見をそのまま使わない、というルールは同じ:
  関門1（全体）   : 全期間で γ=1 より対数尤度が良い（レース単位ブートストラップの95%区間が0をまたがない）
  関門2（後半）   : 前半だけで決めた γ を、後半にそのまま当てて γ=1 より良い
通っても **候補登録どまり**（db/factor_candidates.json・gate_passes=1）。次の開催が貯まってもう一度通ったら prob_core に入れる。

使い方: python market_calib_audit.py [--register]
"""
from __future__ import annotations
import argparse, collections, json, math, random, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"


def fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "").strip()
    return int(s) if s.isdigit() else None


def load():
    races = collections.defaultdict(list)
    for r in json.loads((DB / "race_results.json").read_text(encoding="utf-8")):
        try:
            o = float(r.get("単勝オッズ"))
        except (TypeError, ValueError):
            continue
        f = fin(r)
        if o > 0 and f:
            races[(r["date"], r["競馬場"], int(float(r["R"])))].append((o, f))
    out = []
    for k, hs in sorted(races.items()):
        if len(hs) < 8 or sum(1 for o, f in hs if f == 1) != 1:
            continue
        s = sum(1 / o for o, f in hs)
        if not 1.15 <= s <= 1.40:          # 単勝の控除率20%→Σ(1/odds)≒1.25。外れるレースは頭数欠け
            continue
        q = [(1 / o) / s for o, f in hs]
        out.append(dict(key=k, q=q, fin=[f for o, f in hs], odds=[o for o, f in hs]))
    return out


def ll(race, g):
    """勝ち馬の対数尤度（γで歪みを直した確率）"""
    w = [x ** g for x in race["q"]]
    return math.log(w[race["fin"].index(1)] / sum(w))


def fit(races):
    best = max((sum(ll(r, g / 100) for r in races), g / 100) for g in range(80, 141))
    return best[1]


def boot(diffs, n=4000, seed=1):
    rng = random.Random(seed)
    m = len(diffs)
    xs = sorted(sum(diffs[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return xs[int(0.025 * n)], xs[int(0.975 * n)]


def roi_table(races, g):
    """オッズ帯ごとの 実測勝率 / γ=1の想定 / γ補正後の想定 / 単勝回収率"""
    bands = [(1, 2), (2, 3), (3, 5), (5, 10), (10, 20), (20, 50), (50, 1e9)]
    rows = []
    for lo, hi in bands:
        n = win = ret = 0
        e1 = eg = 0.0
        for r in races:
            w = [x ** g for x in r["q"]]
            sw = sum(w)
            for o, f, q, wi in zip(r["odds"], r["fin"], r["q"], w):
                if lo <= o < hi:
                    n += 1
                    win += f == 1
                    ret += o if f == 1 else 0
                    e1 += q
                    eg += wi / sw
        if n:
            rows.append((f"{lo}〜{hi if hi < 1e8 else ''}倍", n, win / n, e1 / n, eg / n, ret / n))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", action="store_true")
    a = ap.parse_args()
    races = load()
    half = len(races) // 2
    first, second = races[:half], races[half:]
    g_all, g_first = fit(races), fit(first)
    print(f"■ 対象 {len(races):,}レース（{races[0]['key'][0]}〜{races[-1]['key'][0]}） 前半{len(first):,} / 後半{len(second):,}")
    print(f"  γ（全体で最良）= {g_all:.2f} ／ γ（前半だけで決定）= {g_first:.2f}   ※1.00なら今の prob_core と同じ")

    d_all = [ll(r, g_all) - ll(r, 1.0) for r in races]
    lo1, hi1 = boot(d_all)
    d_sec = [ll(r, g_first) - ll(r, 1.0) for r in second]
    lo2, hi2 = boot(d_sec)
    gate1, gate2 = lo1 > 0, lo2 > 0 and g_first != 1.0
    print(f"\n■ 関門1（全体）  対数尤度の改善 {sum(d_all)/len(d_all):+.5f}/レース  95%区間［{lo1:+.5f}, {hi1:+.5f}］ → {'通過' if gate1 else '不通過'}")
    print(f"■ 関門2（後半）  前半のγ={g_first:.2f}を後半に適用 {sum(d_sec)/len(d_sec):+.5f}/レース  95%区間［{lo2:+.5f}, {hi2:+.5f}］ → {'通過' if gate2 else '不通過'}")

    print(f"\n■ オッズ帯ごとの勝率（後半{len(second):,}レース・γは前半で決めた{g_first:.2f}）")
    print(f"{'単勝オッズ':<10}{'頭数':>7}{'実測勝率':>9}{'今の想定':>9}{'補正後':>8}{'単勝回収':>9}")
    for lab, n, act, e1, eg, roi in roi_table(second, g_first):
        print(f"{lab:<10}{n:>8,}{act*100:>8.1f}%{e1*100:>8.1f}%{eg*100:>7.1f}%{roi*100:>8.1f}%")

    verdict = gate1 and gate2
    print(f"\n判定: {'両関門を通過 → 候補登録（1回目）。次の開催でもう一度通ったら prob_core に入れる' if verdict else '不通過 → 入れない'}")
    if a.register and verdict:
        p = DB / "factor_candidates.json"
        cand = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        box = cand if isinstance(cand, list) else cand.setdefault("candidates", [])
        name = "市場の歪み補正 p∝q^γ"
        if not any((c.get("name") == name) for c in box):
            box.append(dict(name=name, kind="market_calibration", gamma=g_first, gamma_all=g_all,
                            registered="2026-10-02", eval_from=str(int(races[-1]["key"][0]) + 1), gate_passes=1,
                            n_races=len(races), ll_gain_all=round(sum(d_all) / len(d_all), 5),
                            ll_gain_second=round(sum(d_sec) / len(d_sec), 5), ci_second=[round(lo2, 5), round(hi2, 5)],
                            note="馬の因子ではなく市場オッズの読み方の補正。2回連続通過で prob_core.market_probs に入れる",
                            script="market_calib_audit.py"))
            p.write_text(json.dumps(cand, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"候補登録: {p}")
        else:
            print("候補は登録済み")


if __name__ == "__main__":
    main()
