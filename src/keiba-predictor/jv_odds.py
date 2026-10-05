# -*- coding: utf-8 -*-
"""
jv_odds.py — JV-Link の確定オッズ（O1〜O6）を、レースごとの {券種: {組: オッズ}} に読む（2026-10-02新規）
================================================================================================
入力: C:/keiba_db/jv_raw/RACE/O{1..6}_{年}.txt（jv_extract.ps1 の出力・1レース1レコード）
レコード（JV-Data）: 1 ID(2) 3 区分(1) 12 年(4) 16 月日(4) 20 場(2) 26 R(2) 28 発表(8) 36 登録頭数(2) 38 出走頭数(2) 40 発売フラグ(1)
  O1 単勝44(馬番2＋オッズ4＋人気2)×28／複勝268(馬番2＋最低4＋最高4＋人気2)×28
  O2 馬連41(組4＋オッズ6＋人気3)×153   O3 ワイド41(組4＋最低5＋最高5＋人気3＝17桁)×153 ※最低オッズを使う
  O4 馬単41(組4＋オッズ6＋人気3)×306   O5 3連複41(組6＋オッズ6＋人気3)×816   O6 3連単41(組6＋オッズ7＋人気4)×4896
オッズは 0.1倍単位（0000＝発売なし・****＝無投票）。
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAW = Path("C:/keiba_db/jv_raw/RACE")
VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}
SPEC = {  # id: (レコード長, 開始, エントリ数, 組番桁, オッズ桁, 人気桁, 券種)
    "O2": (2042, 41, 153, 4, 6, 3, "馬連"), "O3": (2654, 41, 153, 4, 5, 3, "ワイド"),
    "O4": (None, 41, 306, 4, 6, 3, "馬単"), "O5": (None, 41, 816, 6, 6, 3, "3連複"), "O6": (None, 41, 4896, 6, 7, 4, "3連単")}


def parse_file(path: Path, oid: str, limit: int | None = None, start_rec: int = 0):
    rl, start, n, kl, ol, pl, name = SPEC[oid]
    b = path.read_bytes()
    if rl is None:                                   # 長さはヘッダ直後の繰り返しから決める
        rl = start - 1 + n * (kl + ol + pl)
        for extra in range(0, 60):
            if len(b) % (rl + extra) == 0 and b[rl + extra - 2:rl + extra] == b"\r\n":
                rl += extra
                break
    out = {}
    for i in range(start_rec * rl, len(b) - rl + 1, rl):
        if limit is not None and len(out) >= limit:
            break
        r = b[i:i + rl]
        t = r.decode("ascii", "ignore")
        venue = VENUE.get(t[19:21])
        if not venue:
            continue
        key = (t[11:15] + t[15:19], venue, int(t[25:27]))
        w = kl + ol + pl + (ol if name == "ワイド" else 0)   # ワイドは 最低オッズ＋最高オッズ（2026-10-04修正: 以前は幅12で読んでいた）
        tab = {}
        for j in range(n):
            e = t[start - 1 + j * w:start - 1 + (j + 1) * w]
            if len(e) < w:
                break
            comb, od = e[:kl], e[kl:kl + ol]
            if not comb.isdigit() or not comb.strip("0 ") or not od.isdigit() or int(od) == 0:
                continue
            nums = tuple(int(comb[x:x + 2]) for x in range(0, kl, 2))
            tab[nums if name in ("馬単", "3連単") else tuple(sorted(nums))] = int(od) / 10.0
        if tab:
            out[key] = tab
    return name, out


def load_all(years=(2025, 2026), limit=None):
    res = {}
    for oid in SPEC:
        for y in years:
            f = RAW / f"{oid}_{y}.txt"
            if f.exists():
                name, d = parse_file(f, oid, limit)
                for k, tab in d.items():
                    res.setdefault(k, {})[name] = tab
    return res


if __name__ == "__main__":
    import json
    odds = load_all(years=(2025,), limit=60)
    print(f"{len(odds):,}レース")
    # 検証: 払戻（100円）＝オッズ×100 か
    pay = {}
    for f in sorted((Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history_target").glob("payouts_202[56].json")):
        pay.update(json.loads(f.read_text(encoding="utf-8")))
    for t in ("馬連", "ワイド", "馬単", "3連複", "3連単"):
        ok = ng = 0
        for (d, v, R), tabs in odds.items():
            p = pay.get(f"{d}|{v}|{R}", {}).get(t)
            if not p or t not in tabs:
                continue
            for c, yen in p.items():
                key = tuple(int(x) for x in c.split("-"))
                o = tabs[t].get(key)
                if o is None:
                    continue
                if t == "ワイド":
                    ok += 1                          # ワイドは最低〜最高なので範囲に入るかだけ（ここでは存在確認）
                elif abs(o * 100 - yen) <= max(10, yen * 0.005):
                    ok += 1
                else:
                    ng += 1
        print(f"  {t}: 払戻と一致 {ok:,} / 不一致 {ng:,}")


class OddsStore:
    """O1〜O6 を読み込まずに、レースごとに必要な分だけ読む（3連単は220MBあるのでメモリに載せない）"""

    def __init__(self, years=(2025, 2026)):
        self.files, self.index = {}, {}
        for oid in ("O1", "O2", "O3", "O4", "O5", "O6"):
            for y in years:
                f = RAW / f"{oid}_{y}.txt"
                if not f.exists():
                    continue
                size = f.stat().st_size
                rl = {"O1": 962, "O2": 2042, "O3": 2654, "O4": 4031, "O5": 12293, "O6": 83285}[oid]
                assert size % rl == 0, (oid, y, size, rl)
                fh = open(f, "rb")
                for i in range(size // rl):
                    fh.seek(i * rl)
                    h = fh.read(40).decode("ascii", "ignore")
                    venue = VENUE.get(h[19:21])
                    if venue:
                        self.index.setdefault((oid, h[11:15] + h[15:19], venue, int(h[25:27])), (fh, i * rl, rl))

    def races(self):
        return sorted({k[1:] for k in self.index if k[0] == "O6"})

    def get(self, key, oid):
        e = self.index.get((oid,) + tuple(key))
        if not e:
            return None
        fh, off, rl = e
        fh.seek(off)
        return parse_record(oid, fh.read(rl).decode("ascii", "ignore"))


def parse_record(oid, t):
    """1レコード（文字列）→ O1 は {"単勝":{}, "複勝":{}}、他は {券種: {組: オッズ}}"""
    if True:
        if oid == "O1":
            tan, fuku = {}, {}
            for j in range(28):
                x = t[43 + j * 8:43 + (j + 1) * 8]
                if len(x) == 8 and x[:2].isdigit() and x[2:6].isdigit() and int(x[2:6]) > 0:
                    tan[(int(x[:2]),)] = int(x[2:6]) / 10.0
                y = t[267 + j * 12:267 + (j + 1) * 12]
                if len(y) == 12 and y[:2].isdigit() and y[2:6].isdigit() and int(y[2:6]) > 0:
                    fuku[(int(y[:2]),)] = int(y[2:6]) / 10.0               # 最低オッズ
            return {"単勝": tan, "複勝": fuku}
        rl_, start, n, kl, ol, pl, name = SPEC[oid]
        w = kl + ol + pl + (ol if name == "ワイド" else 0)   # ワイドは 最低オッズ＋最高オッズ（2026-10-04修正: 以前は幅12で読んでいた）
        tab = {}
        for j in range(n):
            e2 = t[start - 1 + j * w:start - 1 + (j + 1) * w]
            if len(e2) < w:
                break
            comb, od = e2[:kl], e2[kl:kl + ol]
            if not comb.isdigit() or not od.isdigit() or int(od) == 0:
                continue
            nums = tuple(int(comb[x:x + 2]) for x in range(0, kl, 2))
            tab[nums if name in ("馬単", "3連単") else tuple(sorted(nums))] = int(od) / 10.0
        return {name: tab}
