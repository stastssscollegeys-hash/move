# -*- coding: utf-8 -*-
"""
chokyo.py — 調教タイム（TARGET frontier JV の CK_DATA・JRA-VAN の HC/WC）を読む（2026-10-05新規・提案2）
==================================================================================================
C:/TFJV/CK_DATA/{年}/{年月}/HC{トレセン}{日付}.DAT … 坂路（2003〜）  1行47字: トレセン1 日付8 時刻4 血統登録番号10 4F4 ラップ3 3F4 ラップ3 2F4 ラップ3 1F(ラップ)3
                              WC{トレセン}{日付}.DAT … ウッド（2021/07〜） 1行92字: トレセン1 日付8 時刻4 血統登録番号10 コース1 回り1 予備1 10F〜2F(4+3)×9 1F3
  タイムは0.1秒単位（0000＝その距離は計測なし）。トレセン 0=美浦 1=栗東
作るもの: db/chokyo_index.pkl = {血統登録番号: [(日付, 種別, 主タイム, 終い1F, 日差, 終い日差, トレセン), ...]}（日付順）
   主タイム = 坂路は4F、ウッドは6F（なければ5F）。日差 = その日・そのトレセン・その種別の中央値との差（馬場の重さを消す）
使い方: python chokyo.py --build
"""
from __future__ import annotations
import argparse, collections, glob, pickle, statistics, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path("C:/TFJV/CK_DATA")
OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "chokyo_index.pkl"


def t(s):
    return int(s) / 10.0 if s.isdigit() and int(s) > 0 else None


def parse_hc(ln):
    if len(ln) < 47:
        return None
    tc, d, hid = ln[0], ln[1:9], ln[13:23]
    f4, f1 = t(ln[23:27]), t(ln[44:47])
    if not f4 or not (40 <= f4 <= 80):
        return None
    return tc, d, hid, "坂路", f4, f1


def parse_wc(ln):
    if len(ln) < 92:
        return None
    tc, d, hid = ln[0], ln[1:9], ln[13:23]
    hs = {}
    for j, fl in enumerate(range(10, 1, -1)):
        hs[fl] = t(ln[26 + j * 7:30 + j * 7])
    f1 = t(ln[89:92])
    main = hs.get(6) or hs.get(5)
    if not main or not (55 <= main <= 100):
        return None
    return tc, d, hid, "ウッド6F" if hs.get(6) else "ウッド5F", main, f1


def build(first="2016"):
    """省メモリ版（2026-10-07）: 読みながら数値の配列（array）に詰める。タプルのリストで持つとPCのメモリ（7.7GB・空き1GB前後）が尽きる"""
    import array
    import numpy as np
    KIND = {"坂路": 0, "ウッド6F": 1, "ウッド5F": 2}
    A = dict(tc=array.array("b"), date=array.array("i"), hid=array.array("q"), kind=array.array("b"), main=array.array("f"), f1=array.array("f"))
    seen = set()

    def add(x, dedupe):
        tc, d, hid, k, m, f1 = x
        if not hid.isdigit():
            return
        if dedupe:
            key = (int(d), int(hid), KIND[k])
            if key in seen:
                return
            seen.add(key)
        A["tc"].append(int(tc)); A["date"].append(int(d)); A["hid"].append(int(hid)); A["kind"].append(KIND[k]); A["main"].append(m); A["f1"].append(f1 or float("nan"))
    last_target = "0"
    for f in sorted(glob.glob(str(SRC / "*" / "*" / "*.DAT"))):
        name = Path(f).name
        if Path(f).parent.parent.name < first or name[:2] not in ("HC", "WC"):
            continue
        for ln in Path(f).read_bytes().decode("ascii", "ignore").splitlines():
            x = parse_hc(ln) if name[:2] == "HC" else parse_wc(ln)
            if x:
                add(x, False)
                last_target = max(last_target, x[1])
    # JV-Link の通常読み（SLOP/WOOD）: 先頭11字を除くと TARGET と同じ並び。TARGET の最終日以降だけ足す（重複を避ける）
    for sub, kind in (("SLOP", "HC"), ("WOOD", "WC")):
        for f in sorted((Path("C:/keiba_db/jv_raw") / sub).glob(f"{kind}_*.txt")):
            for ln in f.read_bytes().decode("ascii", "ignore").splitlines():
                if ln[:2] != kind:
                    continue
                x = parse_hc(ln[11:]) if kind == "HC" else parse_wc(ln[11:])
                if x and x[1] > last_target:
                    add(x, True)
    tc, date, hid, kind, main, f1 = (np.frombuffer(A[k], dtype=t).copy() for k, t in (("tc", np.int8), ("date", np.int32), ("hid", np.int64), ("kind", np.int8), ("main", np.float32), ("f1", np.float32)))
    del A, seen
    n = len(date)
    # その日・そのトレセン・その種別の中央値（10本以上）
    dif = np.full(n, np.nan, np.float32); dif1 = np.full(n, np.nan, np.float32)
    grp = (date.astype(np.int64) * 100 + tc.astype(np.int64) * 10 + kind.astype(np.int64))
    order = np.argsort(grp, kind="stable")
    g_sorted = grp[order]
    bounds = np.flatnonzero(np.diff(g_sorted)) + 1
    for seg in np.split(order, bounds):
        if len(seg) >= 10:
            dif[seg] = main[seg] - np.median(main[seg])
            ff = f1[seg]
            ok = ~np.isnan(ff)
            if ok.sum() >= 10:
                dif1[seg[ok]] = ff[ok] - np.median(ff[ok])
    del grp, order, g_sorted
    o = np.lexsort((date, hid))
    tc, date, hid, kind, main, f1, dif, dif1 = (x[o] for x in (tc, date, hid, kind, main, f1, dif, dif1))
    starts = np.flatnonzero(np.r_[True, hid[1:] != hid[:-1]])
    ends = np.r_[starts[1:], n]
    rng = {f"{int(hid[a]):010d}": (int(a), int(b)) for a, b in zip(starts, ends)}
    with open(OUT, "wb") as fh:
        pickle.dump(dict(fmt=2, rng=rng, date=date, kind=kind, main=main, f1=f1, dif=dif, dif1=dif1, tc=tc), fh, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"■ 調教 {n:,}本・{len(rng):,}頭 → {OUT}（省メモリ形式）")


class Index:
    """馬ごとの調教を、必要になったときだけ (日付, 種別, 主タイム, 終い1F, 日差, 終い日差, トレセン) のリストにして返す"""
    NAMES = ("坂路", "ウッド6F", "ウッド5F")

    def __init__(self, d):
        self.d = d

    def get(self, hid, default=None):
        r = self.d["rng"].get(str(hid or ""))
        if not r:
            return default
        a, b = r
        D = self.d
        out = []
        for i in range(a, b):
            f1, df, df1 = float(D["f1"][i]), float(D["dif"][i]), float(D["dif1"][i])
            out.append((str(int(D["date"][i])), self.NAMES[D["kind"][i]], round(float(D["main"][i]), 1), None if f1 != f1 else round(f1, 1),
                        None if df != df else round(df, 2), None if df1 != df1 else round(df1, 2), str(int(D["tc"][i]))))
        return out

    def __bool__(self):
        return bool(self.d["rng"])


def load():
    if not OUT.exists():
        return Index(dict(rng={}))
    d = pickle.loads(OUT.read_bytes())
    if isinstance(d, dict) and d.get("fmt") == 2:
        return Index(d)
    return d                                        # 旧形式（dict of list）


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    if a.build:
        build()
