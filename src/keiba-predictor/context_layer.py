# -*- coding: utf-8 -*-
"""
context_layer.py — 「レース側の文脈」を層として持ち込む（2026-09-27 新設・ユーザー指示）
=========================================================================================
馬単体の因子（20因子・17因子）は市場に織り込まれていて上乗せが無い（index_audit_leakfree.py）。
残る情報源は **レースそのもの・その日・前日・馬場** の文脈。これを4層に分け、
それぞれ「同じ人気帯の中で差が出るか」を実測してから確率に掛ける（context_audit.py）。

層と、レース前に使ってよい材料（結果リークを防ぐため、必ず「そのレースより前」の情報だけ）
  L1 レース層   : 距離帯×馬場 の脚質別3着内率（pace_style.json・全期間の実測）
  L2 当日層     : 同じ日・同じ競馬場で **既に終わった** レースの 脚質別／枠帯別 3着内率
  L3 前日層     : 同じ競馬場の直前の開催日（7日以内）12Rの 脚質別／枠帯別 3着内率
  L4 馬場変化層 : 当日の馬場状態が朝から変わったか（良→稍重 等）と、直近レースの馬場

各層の出力は「その脚質／枠帯の3着内率が基準より何倍か」（log比）。サンプルが少ない日は
縮約（n/(n+K)）して1倍に寄せる。**層ごとにON/OFFでき、監査を通った層だけ確率に使う。**

使い方:
    from context_layer import ContextDB, multipliers
    cdb = ContextDB()                                  # 蓄積DBを読み込む（1回）
    ctx = cdb.context("20260927", "中山", 11, surface="芝", meters=1200, baba="稍重")
    m   = multipliers(ctx, style="逃げ", waku=3, layers=("L1","L2"))   # 有効層だけ掛ける
    p_adj = {u: p[u] * m[u] ... }  → 正規化
"""
from __future__ import annotations
import collections, json, math
from pathlib import Path

DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
STYLES = ("逃げ", "先行", "差し", "追込")


def enabled_layers():
    """確率に掛けてよい層。context_audit.py の両関門を通った層だけを db/context_layers.json に書く。
    2026-09-27時点: 1,888R・19,872頭で **通った層なし** → 空（文脈はSNSの説明材料としてのみ使う）。
    474Rでは L2+L3 が通ったが、4倍のデータで消えた＝偶然。"""
    p = DB / "context_layers.json"
    if not p.exists():
        return ()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return tuple(d.get("enabled", []))
    except Exception:
        return ()
WAKU_BAND = {1: "内", 2: "内", 3: "内", 4: "中", 5: "中", 6: "中", 7: "外", 8: "外"}
K_DAY, K_PREV = 30, 60          # 縮約の強さ（頭数）。当日は少数でも効かせ、前日は弱く
CLIP = (0.6, 1.6)               # 1層あたりの倍率の上下限


def _fin(r):
    v = r.get("着順int")
    if v:
        return int(v)
    s = str(r.get("着順") or "")
    return int(s) if s.isdigit() else None


def _dist_band(d):
    s = str(d or "")
    surf = "芝" if s.startswith("芝") else ("ダ" if s.startswith("ダ") else None)
    num = "".join(c for c in s if c.isdigit())
    if not surf or not num:
        return None
    m = int(num)
    return surf + ("〜1200" if m <= 1200 else "1300-1400" if m <= 1400 else "1500-1600" if m <= 1600
                   else "1700-1800" if m <= 1800 else "1900-2000" if m <= 2000 else "2100-")


def _baba_band(b):
    s = str(b or "")
    return "良" if s.startswith("良") else "稍重" if s.startswith("稍") else \
        "重・不良" if s[:1] in ("重", "不") else "全馬場"


class ContextDB:
    def __init__(self, rows=None):
        self.rows = rows or json.loads((DB / "race_results.json").read_text(encoding="utf-8"))
        self.pace = json.loads((DB / "pace_style.json").read_text(encoding="utf-8")) if (DB / "pace_style.json").exists() else {}
        self.by_day = collections.defaultdict(list)          # (date, venue) -> rows
        for r in self.rows:
            if r.get("date") and r.get("競馬場"):
                self.by_day[(r["date"], r["競馬場"])].append(r)
        self.venue_dates = collections.defaultdict(list)
        for d, v in self.by_day:
            self.venue_dates[v].append(d)
        for v in self.venue_dates:
            self.venue_dates[v].sort()
        # 全期間の基準率（脚質・枠帯）
        self.base_style = self._rates(self.rows, "style")
        self.base_waku = self._rates(self.rows, "waku")
        # 馬ごとの時系列（脚質予測用）
        self.by_horse = collections.defaultdict(list)
        for r in self.rows:
            if r.get("脚質") in STYLES and r.get("馬名") and r.get("date"):
                self.by_horse[r["馬名"]].append(r)
        for v in self.by_horse.values():
            v.sort(key=lambda r: (r["date"], r["競馬場"], int(float(r.get("R") or 0))))

    def style_forecast(self, horse_name, before_date, n_recent=5):
        """レース前の想定脚質＝その馬の before_date より前の直近n走の多数決（同数は直近優先）。
        style_forecast_audit.py の実測: 一致率41.9%（recordsの想定脚質は27.6%・偶然25%）。
        4分類の予測は本質的に難しい（隣接1段階以内なら81%）ので、層の倍率はこの不確かさを前提に縮約している。"""
        hist = [r for r in self.by_horse.get(horse_name, []) if r["date"] < before_date][-n_recent:]
        if not hist:
            return None
        c = collections.Counter(h["脚質"] for h in hist)
        top = max(c.values())
        cands = {s for s, n in c.items() if n == top}
        for h in reversed(hist):
            if h["脚質"] in cands:
                return h["脚質"]

    @staticmethod
    def _rates(rows, kind):
        cnt = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            f = _fin(r)
            if not f:
                continue
            if kind == "style":
                k = r.get("脚質")
                if k not in STYLES:
                    continue
            else:
                try:
                    k = WAKU_BAND.get(int(float(r.get("枠"))))
                except (TypeError, ValueError):
                    continue
                if not k:
                    continue
            cnt[k][0] += 1
            cnt[k][1] += 1 if f <= 3 else 0
        return {k: (v[1] / v[0], v[0]) for k, v in cnt.items() if v[0]}

    def _layer_ratios(self, rows, K):
        """基準率に対する比（縮約つき）を 脚質・枠帯 ごとに返す"""
        out = {}
        for kind, base in (("style", self.base_style), ("waku", self.base_waku)):
            obs = self._rates(rows, kind)
            for k, (b_rate, _) in base.items():
                if k in obs and b_rate > 0:
                    rate, n = obs[k]
                    w = n / (n + K)
                    ratio = (rate / b_rate) ** w        # 幾何的に縮約
                    out[(kind, k)] = (max(CLIP[0], min(CLIP[1], ratio)), n)
                else:
                    out[(kind, k)] = (1.0, 0)
        return out

    def context(self, date, venue, R, surface=None, meters=None, baba=None):
        today = self.by_day.get((date, venue), [])
        done = [r for r in today if int(float(r.get("R") or 0)) < int(R)]
        ctx = {"date": date, "venue": venue, "R": int(R), "n_done": len({r["R"] for r in done})}
        # L1 レース層
        key = None
        if surface and meters:
            db = _dist_band(f"{surface}{meters}")
            for k in (f"{db}|全ペース|{_baba_band(baba)}", f"{db}|全ペース|全馬場"):
                if k in self.pace and self.pace[k].get("n", 0) >= 120:
                    key = k
                    break
        ctx["L1"] = {}
        if key:
            rates = {s: v for s, v in self.pace[key]["rates"].items() if v is not None}
            mean = sum(rates.values()) / len(rates)
            ctx["L1"] = {("style", s): (max(CLIP[0], min(CLIP[1], v / mean)), self.pace[key]["n"]) for s, v in rates.items()}
            ctx["L1_key"] = key
        # L2 当日層（終わったレースだけ）
        ctx["L2"] = self._layer_ratios(done, K_DAY) if done else {}
        # L3 前日層
        prev = [d for d in self.venue_dates.get(venue, []) if d < date]
        ctx["L3"], ctx["L3_date"] = {}, None
        if prev:
            pd = prev[-1]
            gap = (int(date[:4]) * 372 + int(date[4:6]) * 31 + int(date[6:])) - (int(pd[:4]) * 372 + int(pd[4:6]) * 31 + int(pd[6:]))
            if gap <= 8:
                ctx["L3"] = self._layer_ratios(self.by_day[(pd, venue)], K_PREV)
                ctx["L3_date"] = pd
        # L4 馬場変化層
        seq = [str(r.get("馬場状態") or "")[:1] for r in sorted(done, key=lambda r: int(float(r["R"])))]
        ctx["L4"] = {"first": seq[0] if seq else None, "last": seq[-1] if seq else None,
                     "changed": len(set(seq)) > 1, "now": str(baba or "")[:1] or None}
        return ctx


def multipliers(ctx, style, waku, layers=("L1", "L2", "L3")):
    """1頭ぶんの倍率（層ごと）と合成値。監査を通った層だけ layers に入れる"""
    try:
        wb = WAKU_BAND.get(int(float(waku)))
    except (TypeError, ValueError):
        wb = None
    per = {}
    for L in layers:
        d = ctx.get(L) or {}
        m = 1.0
        if ("style", style) in d:
            m *= d[("style", style)][0]
        if wb and ("waku", wb) in d:
            m *= d[("waku", wb)][0]
        per[L] = m
    total = 1.0
    for v in per.values():
        total *= v
    return {"per_layer": per, "total": total}


def describe(ctx):
    """SNS・docx 用の文脈テキスト（数字は実測。予想の根拠の説明に使う）"""
    lines = []
    if ctx.get("L1_key"):
        lines.append(f"コース実測（{ctx['L1_key'].split('|')[0]}）: " + "／".join(
            f"{s}{v[0]:.2f}倍" for (kind, s), v in ctx["L1"].items() if kind == "style"))
    if ctx.get("L2"):
        st = {s: v for (kind, s), v in ctx["L2"].items() if kind == "style" and v[1] > 0}
        if st:
            hi = max(st, key=lambda s: st[s][0])
            lo = min(st, key=lambda s: st[s][0])
            lines.append(f"本日ここまで{ctx['n_done']}R: {hi}が走り{lo}が苦戦（{hi}{st[hi][0]:.2f}倍／{lo}{st[lo][0]:.2f}倍）")
    if ctx.get("L3_date"):
        st = {s: v for (kind, s), v in ctx["L3"].items() if kind == "style"}
        hi = max(st, key=lambda s: st[s][0])
        lines.append(f"前開催（{ctx['L3_date'][4:6]}/{ctx['L3_date'][6:]}）は{hi}有利（{st[hi][0]:.2f}倍）")
    if ctx.get("L4", {}).get("changed"):
        lines.append(f"馬場は本日 {ctx['L4']['first']}→{ctx['L4']['last']} に変化")
    return lines
