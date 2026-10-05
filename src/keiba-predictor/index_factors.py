# -*- coding: utf-8 -*-
"""
index_factors.py — 指数の因子のうち「実測から作るもの」を1か所にまとめる（2026-10-02新規）
======================================================================================
旧来の式に2つの欠陥があった（engine_fix_audit.py で確認）:
  F02 タイム指数 … 基準が「距離×61秒/km＋3秒」の固定で、芝の66%・ダートの62%の馬が100点に張り付いていた。
                   ±200mの別距離の時計を補正なしで比べるので、前走が長い距離なら0点、短い距離なら100点にもなる。
  F06 枠バイアス … 競馬場ごとの手書きの表（54〜76点）。全期間の実測と合っていなかった。

ここでは両方を蓄積DB（race_results.json）の実測から作る。式を変えても◎の成績は誤差の範囲でしか動かないが
（444Rで3着内 +0.2pt）、「時計が速い馬に高い点が付く」「実測で差が無い枠には差を付けない」という
因子の意味どおりの点数になる。データが増えれば基準も自動で更新される。

  time_index(past, surface)   過去走（新しい順）のうち同じ芝ダの直近3走について、
                              (基準タイム − 走破タイム) ÷ 基準タイム を取り、最良の値を点数にする。
                              基準＝同じ芝ダ・距離・馬場（良／道悪）の全完走馬の中央値。基準より1%速い＝+12.5点、50点が標準（4%速いと100点。全馬の0.9%だけが上限に届く幅）。
  waku_score(venue, waku)     その競馬場のその枠の「実測3着内 ÷ 人気から期待される3着内」。偶然のばらつきで説明できる分は
                              1.0へ寄せる（経験ベイズ）。65点が標準で、偶然を超える差が出てきた枠だけ点が動く。
"""
from __future__ import annotations
import collections, json, statistics
from pathlib import Path

DB_PATH = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "race_results.json"
FACTOR_VERSION = "2026-10-02"        # records に書き込む。前向き検証の切り替わり目印
MIN_N = 30                            # 基準タイムを作る最小件数
TIME_SCALE = 12.5                     # 基準より1%速いと何点上がるか（25だと17%の馬が100点に張り付いた）
WAKU_TAU2 = 0.0                       # 枠の間の「本当の差」の大きさ（_load が実測から推定する）

_std = None
_waku = None


def _sec(t):
    s = str(t or "")
    try:
        if ":" in s:
            m, r = s.split(":", 1)
            return int(m) * 60 + float(r)
        return float(s)
    except ValueError:
        return None


def _fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "").strip()
    return int(s) if s.isdigit() else None


def _load():
    global _std, _waku
    if _std is not None:
        return
    rows = json.loads(DB_PATH.read_text(encoding="utf-8")) if DB_PATH.exists() else []
    full, loose = collections.defaultdict(list), collections.defaultdict(list)
    pop = collections.defaultdict(lambda: [0, 0])
    cells = []
    for r in rows:
        d = str(r.get("距離") or "")
        f = _fin(r)
        if d.startswith("障") or not f:
            continue
        surf = 1 if d.startswith("芝") else 2
        m = "".join(c for c in d if c.isdigit())
        t = _sec(r.get("タイム"))
        if m and t:
            good = str(r.get("馬場状態") or "良")[:1] == "良"
            full[(surf, int(m), good)].append(t)
            loose[(surf, int(m))].append(t)
        try:
            p, w = int(float(r["人気"])), int(float(r["枠"]))
        except (TypeError, ValueError, KeyError):
            continue
        pop[p][0] += 1
        pop[p][1] += f <= 3
        cells.append((r.get("競馬場"), w, p, f <= 3))
    med_full = {k: statistics.median(v) for k, v in full.items() if len(v) >= MIN_N}
    med_loose = {k: statistics.median(v) for k, v in loose.items() if len(v) >= MIN_N}
    # 件数の足りない距離は、芝ダ別に「距離→中央値」の直線で補う
    line = {}
    for surf in (1, 2):
        pts = [(k[1], v) for k, v in med_loose.items() if k[0] == surf]
        if len(pts) >= 2:
            mx, my = sum(x for x, y in pts) / len(pts), sum(y for x, y in pts) / len(pts)
            a = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, y in pts)
            line[surf] = (a, my - a * mx)
    _std = (med_full, med_loose, line)
    exp = {p: v[1] / v[0] for p, v in pop.items() if v[0] >= 50}
    agg = collections.defaultdict(lambda: [0.0, 0.0])
    for venue, w, p, hit in cells:
        if p in exp:
            agg[(venue, w)][0] += hit
            agg[(venue, w)][1] += exp[p]
    # 枠ごとの 実測÷期待 を、偶然のばらつきの分だけ1.0へ寄せる（経験ベイズ）。
    #   枠の間に本当の差があるなら、比のばらつきは偶然で説明できる量（≒0.75/期待数）より大きくなる。
    #   その超過分 tau2 が0なら全枠1.0（＝差なし）、差が積み上がってくれば自動で開く。
    cells2 = {k: (o / e, 0.75 / e) for k, (o, e) in agg.items() if e >= 20}
    global WAKU_TAU2
    if len(cells2) >= 8:
        rs = [r for r, v in cells2.values()]
        m = sum(rs) / len(rs)
        var_obs = sum((r - m) ** 2 for r in rs) / (len(rs) - 1)
        WAKU_TAU2 = max(0.0, var_obs - sum(v for r, v in cells2.values()) / len(cells2))
    _waku = {k: 1.0 + (r - 1.0) * WAKU_TAU2 / (WAKU_TAU2 + v) for k, (r, v) in cells2.items()}


def std_time(surf: int, meters: int, good: bool | None = None):
    """基準タイム（秒）。surf: 1=芝 2=ダート"""
    _load()
    full, loose, line = _std
    if good is not None and (surf, meters, good) in full:
        return full[(surf, meters, good)]
    if (surf, meters) in loose:
        return loose[(surf, meters)]
    if surf in line:
        a, b = line[surf]
        return a * meters + b
    return None


def time_index(past: list, surf_now: int) -> float:
    """past は netkeiba キャッシュ形式（新しい順・distance/trackkind/stime/fr_baba）。50点が標準"""
    figs = []
    for p in [x for x in past if x.get("trackkind") == surf_now and x.get("stime") and x.get("distance")][:3]:
        baba = p.get("fr_baba")
        good = None if baba in (None, "") else (str(baba) in ("A", "良", "1"))
        b = std_time(surf_now, int(p["distance"]), good)
        if b:
            figs.append((b - float(p["stime"])) / b * 100.0)
    return min(100.0, max(0.0, 50.0 + max(figs) * TIME_SCALE)) if figs else 50.0


def waku_score(venue: str, waku) -> float:
    """枠の点数。65点が標準。実測÷期待が1.05なら約68点"""
    _load()
    try:
        r = _waku.get((venue, int(waku)))
    except (TypeError, ValueError):
        r = None
    return 65.0 if not r else min(75.0, max(55.0, 65.0 * r))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    _load()
    print("■ 基準タイム（良馬場・主な距離）")
    for surf, lab in ((1, "芝"), (2, "ダ")):
        print(" ", lab, " ".join(f"{m}m={std_time(surf, m, True):.1f}" for m in (1200, 1400, 1600, 1800, 2000, 2400) if std_time(surf, m, True)))
    print(f"■ 枠の点数（実測から・65点が標準）　枠の間の本当の差の推定 tau2={WAKU_TAU2:.5f}（0なら全枠同点）")
    for v in ("東京", "京都", "中山", "阪神", "新潟", "中京", "小倉", "福島", "札幌", "函館"):
        print(f"  {v}: " + " ".join(f"{w}枠{waku_score(v, w):.1f}" for w in range(1, 9)))
