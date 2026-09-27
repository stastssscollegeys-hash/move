# -*- coding: utf-8 -*-
"""
band_tracker.py — 有望な人気帯を「発見後のデータ」だけで追跡する
==========================================================================
なぜ必要か
----------
2026-09-08の185帯スキャンで、頑健性スクリーニングを通った帯が2つ出た。

    馬連 4-6人気     122%（的中23／3期とも100%超）
    3連複 1-3-8人気  122%（的中23／3期とも100%超）

しかし **これは見つけたデータそのもので測った数字**であり、証拠にはならない。
185帯を検定して2帯なので、多重比較で偶然生き残った可能性を排除できない。
ブートストラップでも P(本当に100%超) は 77% / 76% にとどまる。

    → 発見に使った期間（〜2026-09-06）は **in-sample＝検証に使えない**。
    → 2026-09-12 以降のデータだけを **forward＝本物の検証** として貯める。

この分離をコードで強制するのがこのスクリプトの役割。
in-sample の数字を「実績」として報告しないための歯止めでもある。

実際に賭けなくても、払戻DBから毎週自動でペーパートレードの結果が入る。
（現段階は確定エッジではないので、実弾は薄く張るか張らない。
  [[bankroll_kelly]] のとおり、未実証のエッジに厚く張るのは破産経路）

使い方
------
    python band_tracker.py                 # 現況レポート
    python band_tracker.py --update        # 払戻DBから最新まで取り込む
    python band_tracker.py --add-band 馬連 3-5    # 監視対象を追加
"""
from __future__ import annotations
import argparse, json, random, sys, io
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
LEDGER = DB / "band_tracking.json"

# 発見に使ったデータの範囲。**この期間だけが in-sample（検証に使えない）**
#
# ⚠ 「これ以前は全部 in-sample」ではない。スキャン時の蓄積DBは
#   2026-05-16〜2026-09-06 しか無かったので、**それより前の期間は
#   発見に一度も使われていない＝正当な hold-out** になる。
#   （backfill_history.py で後から取得した1〜5月分がこれに当たる）
#   帯の定義は人気順位だけの機械的ルールなので、時間的に過去でも検証に使える。
DISCOVERY_START = "20260516"
DISCOVERY_END = "20260906"


def phase(d: str) -> str:
    """その日付が in-sample か、検証に使える hold-out / forward か"""
    if DISCOVERY_START <= d <= DISCOVERY_END:
        return "insample"
    return "holdout" if d < DISCOVERY_START else "forward"

# 監視対象。スキャンで頑健性を通ったものだけを入れる
WATCHLIST = [
    {"t": "馬連",  "pops": [4, 6],    "found": "20260908", "insample_roi": 1.22},
    {"t": "3連複", "pops": [1, 3, 8], "found": "20260908", "insample_roi": 1.22},
]

# 1ベットあたりの回収率の標準偏差（券種別・実測ベース）。
# 配当が高い券種ほど大きく、必要サンプル数を押し上げる。
SIGMA = {"単勝": 1.39, "ワイド": 1.80, "馬連": 2.90, "馬単": 3.50,
         "3連複": 4.20, "3連単": 5.08}


def needed_bets(ticket: str, effect: float) -> int:
    """
    その効果量を検出するのに必要なベット数（両側95%・検出力80%）。
        n = (z_α/2 + z_β)² σ² / Δ²      Δ = 観測された超過分（例 120%なら0.20）

    ⚠ 効果量で必要数は激変する。110%を証明するには馬連6,500ベット要るが、
      本当に120%あるなら1,650ベットで足りる（Δが2倍→必要数は1/4）。
      「110%基準」で一律に語ると、検証が非現実的に見えて手が止まる。
    """
    sigma = SIGMA.get(ticket, 3.0)
    delta = max(0.05, abs(effect - 1.0))     # 5pt未満の効果は現実的に検出不能とみなす
    return int(7.849 * sigma * sigma / (delta * delta))


def _key(b: dict) -> str:
    return f'{b["t"]} {"-".join(str(x) for x in b["pops"])}人気'


def collect() -> dict[str, list]:
    """払戻DBと結果DBから、各帯の1レースごとの払戻（外れは0）を作る"""
    pays = json.load(open(DB / "payouts.json", encoding="utf-8"))
    rows = json.load(open(DB / "race_results.json", encoding="utf-8"))

    races: dict = defaultdict(dict)
    for r in rows:
        try:
            races[(str(r.get("date")), r.get("競馬場"), r.get("R"))][int(r["馬番"])] = \
                int(float(r["人気"]))
        except (TypeError, ValueError, KeyError):
            continue

    out: dict[str, list] = {_key(b): [] for b in WATCHLIST}
    for rec in pays.values():
        m = races.get((str(rec.get("date")), rec.get("venue"), rec.get("R")))
        if not m or len(m) < 8:
            continue
        P = rec.get("payouts") or {}
        if not P.get("馬連"):        # 払戻が取れていない日は飛ばす
            continue
        date = str(rec.get("date"))
        pop2num = {v: k for k, v in m.items()}
        mx = max(m.values())

        cache: dict = {}
        for b in WATCHLIST:
            t, pops = b["t"], b["pops"]
            if max(pops) > mx:
                continue
            nums = [pop2num.get(p) for p in pops]
            if not all(nums):
                continue
            if t not in cache:
                d = {}
                for w in (P.get(t) or []):
                    try:
                        parts = [int(x) for x in
                                 str(w["combo"]).replace("-", " ").replace(">", " ").split()]
                        d[tuple(parts) if t == "馬単" else tuple(sorted(parts))] = int(w["yen"])
                    except (ValueError, KeyError, TypeError):
                        continue
                cache[t] = d
            k = tuple(nums) if t == "馬単" else tuple(sorted(nums))
            out[_key(b)].append({"date": date, "yen": cache[t].get(k, 0)})
    return out


def _stats(v: list) -> dict:
    n = len(v)
    if not n:
        return {"n": 0, "hits": 0, "roi": 0.0}
    yens = [x["yen"] for x in v]
    hits = [y for y in yens if y > 0]
    return {"n": n, "hits": len(hits), "roi": sum(yens) / (n * 100),
            "med": sorted(hits)[len(hits) // 2] if hits else 0}


def _bootstrap(v: list, iters: int = 10000) -> tuple[float, float, float]:
    """(95%下限, 95%上限, P(回収率>100%))"""
    yens = [x["yen"] for x in v]
    n = len(yens)
    if n < 30:
        return 0.0, 0.0, 0.0
    random.seed(42)
    bs = sorted(sum(random.choices(yens, k=n)) / (n * 100) for _ in range(iters))
    return bs[iters // 40], bs[iters - iters // 40 - 1], sum(1 for x in bs if x > 1.0) / iters


def report(update: bool) -> None:
    data = collect()
    if update:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        json.dump({"discovery_end": DISCOVERY_END, "data": data},
                  open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"取り込み完了 → {LEDGER}\n")

    print("═══ 有望帯の追跡 ═══\n")
    print(f"　発見に使った期間: {DISCOVERY_START}〜{DISCOVERY_END}"
          f"（**この期間の成績は検証に使えない**）")
    print(f"　検証に使えるのは、その前(hold-out)と後(forward)のデータ\n")

    for b in WATCHLIST:
        k = _key(b)
        v = data.get(k) or []
        ins = [x for x in v if phase(x["date"]) == "insample"]
        # hold-out（発見より前の期間）と forward（発見より後）は
        # どちらも「発見に使っていない」ので、検証としては同格に扱える
        val = [x for x in v if phase(x["date"]) != "insample"]
        hold = [x for x in v if phase(x["date"]) == "holdout"]
        fwd = [x for x in v if phase(x["date"]) == "forward"]
        si, sf = _stats(ins), _stats(val)

        print(f"■ {k}")
        print(f"　発見時(in-sample) {si['n']:>5,}R  的中{si['hits']:>3}  "
              f"回収率 {si['roi']*100:>5.0f}%   ← 参考値。証拠にならない")
        if hold:
            h = _stats(hold)
            print(f"　　└ 検証の内訳: hold-out(発見より前) {h['n']:,}R 的中{h['hits']} "
                  f"{h['roi']*100:.0f}%  ／  forward(発見より後) {_stats(fwd)['n']:,}R")

        # この帯は1開催日あたり何ベット発生するか（実データから数える）
        ins_days = len({x["date"] for x in ins}) or 1
        per_day = si["n"] / ins_days
        need_opt = needed_bets(b["t"], b["insample_roi"])          # 観測どおりなら
        need_safe = needed_bets(b["t"], 1.0 + (b["insample_roi"] - 1.0) / 2)  # 効果が半分なら

        if sf["n"] == 0:
            print(f"　検証(hold-out+forward)  0R  ← **まだ1レースも無い。判定不能**")
            print(f"　　次の開催から蓄積が始まる（この帯は1日あたり約{per_day:.0f}ベット発生）")
            print(f"　　必要ベット: {need_opt:,}（実測{b['insample_roi']*100:.0f}%が本物なら）"
                  f" ／ {need_safe:,}（効果が半分だったら）")
            print(f"　　所要: 約{need_opt/(per_day*2)/4.3:.0f}ヶ月"
                  f"（効果が半分なら約{need_safe/(per_day*2)/4.3:.0f}ヶ月）\n")
            continue

        lo, hi, p = _bootstrap(val)      # 検証データ全体（hold-out + forward）で評価する
        print(f"　検証(hold-out+forward) {sf['n']:>5,}R  的中{sf['hits']:>3}  "
              f"回収率 {sf['roi']*100:>5.0f}%")
        if sf["n"] >= 30:
            print(f"　　95%区間 [{lo*100:.0f}〜{hi*100:.0f}%]  P(本当に100%超) {p*100:.1f}%")
            if lo > 1.0:
                print("　　✅ 区間が100%を上回りきった。エッジが確認できた")
            elif hi < 1.0:
                print("　　❌ 区間が100%を下回りきった。この帯は棄却する")
            else:
                print("　　→ まだ判定できない。積み増す")
        else:
            print("　　※30レース未満は区間を出さない（意味のある推定ができない）")
        print(f"　　必要 {need_opt:,}ベット中 {sf['n']:,} ／ 残り {max(0, need_opt-sf['n']):,}"
              f"（約{max(0, need_opt-sf['n'])/(per_day*2)/4.3:.0f}ヶ月）\n")

    print("─" * 60)
    print("🔴 in-sample の数字を『実績』としてSNS等に出さないこと。")
    print("　 185帯を検定して2帯が残っただけで、多重比較の偶然を排除できていない。")
    print("　 実弾は薄く。未実証のエッジに厚く張るのは破産経路（bankroll_kelly参照）。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="払戻DBから最新まで取り込む")
    ap.add_argument("--add-band", nargs=2, metavar=("券種", "人気"),
                    help='監視対象を追加 例: --add-band 馬連 3-5')
    a = ap.parse_args()
    if a.add_band:
        t, pops = a.add_band
        print(f"※ WATCHLIST に追加するには band_tracker.py を直接編集してください:")
        print(f'   {{"t": "{t}", "pops": {[int(x) for x in pops.split("-")]}, '
              f'"found": "今日の日付", "insample_roi": 実測値}}')
        sys.exit(0)
    report(a.update)
