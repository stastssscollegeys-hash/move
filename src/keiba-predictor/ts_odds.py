# -*- coding: utf-8 -*-
"""
ts_odds.py — 時系列オッズ（JV速報 0B41・単勝）で「発走直前に売れた馬」を検証する（2026-10-05新規・提案3）
=========================================================================================================
入力: C:/keiba_db/jv_raw/TS/{レースキー}.txt（jv/jv_ts.ps1 で取得。O1 レコードが数分おきに並ぶ）
      発走時刻は TARGET の SR（RA）874〜877バイト目、結果は history_target の results_*.json
見るもの: 発走30分前・60分前・前日最終 と 締切直前（発走時刻までの最後の発表）の単勝オッズの変化
   → 直前に売れた（オッズが下がった）馬は、締切直前のオッズが示す確率より勝つか（＝買える価値があるか）
   払い戻しは締切後の確定オッズで決まるので、「直前のオッズ×勝ち」で回収率を測る（確定オッズ≒締切直前）
使い方: python ts_odds.py --build   # TS を読んで db/ts_odds.pkl にまとめる
        python ts_odds.py           # 分析
"""
from __future__ import annotations
import argparse, collections, glob, json, math, pickle, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import jv_odds as J
import target_import as T

TS = Path("C:/keiba_db/jv_raw/TS")
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
OUT = DB / "ts_odds.pkl"


def post_times(years=("2023", "2024", "2025", "2026")):
    out = {}
    for y in years:
        for f in glob.glob(f"C:/TFJV/SE_DATA/{y}/SR*.DAT"):
            for r in T.records(Path(f), 1272):
                k = T.seg(r, 12, 4) + T.seg(r, 16, 4) + T.seg(r, 20, 2) + T.seg(r, 22, 2) + T.seg(r, 24, 2) + T.seg(r, 26, 2)
                hm = r[873:877].decode("ascii", "ignore")
                if hm.isdigit():
                    out[k] = hm
        f = Path(f"C:/keiba_db/jv_raw/RACE/RA_{y}.txt")
        if f.exists():
            b = f.read_bytes()
            for i in range(0, len(b) - 1271, 1272):
                r = b[i:i + 1272]
                k = T.seg(r, 12, 4) + T.seg(r, 16, 4) + T.seg(r, 20, 2) + T.seg(r, 22, 2) + T.seg(r, 24, 2) + T.seg(r, 26, 2)
                hm = r[873:877].decode("ascii", "ignore")
                if hm.isdigit():
                    out.setdefault(k, hm)
    return out


def build(src=TS, tag="", delete=False):
    """src のファイルを読み、締切前90分＋前日最終だけを残して db/ts_odds{tag}.pkl に保存。delete=True なら読んだ生ファイルを消す（容量節約）"""
    pt = post_times()
    races = {}
    for f in sorted(Path(src).glob("*.txt")):
        key = f.stem
        hm = pt.get(key)
        if not hm:
            continue
        t = f.read_bytes().decode("ascii", "ignore")
        snaps = []
        for i in range(0, len(t), 962):
            rec = t[i:i + 962]
            if not rec.startswith("O1"):
                continue
            ann = rec[27:35]                                  # 発表 月日時分
            tan = J.parse_record("O1", rec)["単勝"]
            if tan:
                snaps.append((ann, {k[0]: v for k, v in tan.items()}))
        if snaps:
            snaps.sort(key=lambda x: x[0])
            post = mm(key[4:8] + hm)
            prev = [s for s in snaps if s[0][:4] < key[4:8]]
            keep = ([prev[-1]] if prev else []) + [s for s in snaps if post - 90 <= mm(s[0]) <= post + 5]
            races[key] = dict(post=key[4:8] + hm, snaps=keep)
        if delete:
            f.unlink()
    out = DB / f"ts_odds{tag}.pkl"
    out.write_bytes(pickle.dumps(races))
    print(f"■ 時系列オッズ {len(races):,}レース → {out}")


def mm(s):
    """MMDDHHMM → 分（年内の通し）"""
    return ((int(s[:2]) * 31 + int(s[2:4])) * 24 + int(s[4:6])) * 60 + int(s[6:8])


def analyze():
    races = {}
    for f in sorted(DB.glob("ts_odds*.pkl")):
        races.update(pickle.loads(f.read_bytes()))
    res = {}
    for f in sorted((DB / "history_target").glob("results_202[3-6].json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            if r.get("着順int"):
                res[(r["date"], r["競馬場"], int(r["R"]), int(r["馬番"]))] = r["着順int"]
    vcode = {v: k for k, v in J.VENUE.items()}
    rows = []
    for key, d in races.items():
        date, venue, R = key[:8], J.VENUE.get(key[8:10]), int(key[14:16])
        post = mm(d["post"])
        pre = [s for s in d["snaps"] if mm(s[0]) <= post]
        if len(pre) < 3:
            continue
        last = pre[-1][1]

        def at(minutes):
            c = [s for s in pre if mm(s[0]) <= post - minutes]
            return c[-1][1] if c else None
        o30, o60 = at(30), at(60)
        prev = [s for s in pre if s[0][:4] < d["post"][:4]]
        oprev = prev[-1][1] if prev else None
        inv = sum(1 / v for v in last.values() if v > 0)
        for u, o in last.items():
            f_ = res.get((date, venue, R, u))
            if not f_ or o <= 0:
                continue
            rows.append(dict(o=o, p=(1 / o) / inv, win=f_ == 1, top3=f_ <= 3, period="検証(2025/10〜)" if date >= "20251004" else "過去(2023〜2025/9)",
                             d30=math.log(o30[u] / o) if o30 and o30.get(u) else None,
                             d60=math.log(o60[u] / o) if o60 and o60.get(u) else None,
                             dprev=math.log(oprev[u] / o) if oprev and oprev.get(u) else None))
    print(f"■ 対象 {len(rows):,}頭（{len(races):,}レース）。回収率は締切直前の単勝オッズで計算（確定オッズとほぼ同じ）")
    base = sum(r["o"] * r["win"] for r in rows) / len(rows) * 100
    print(f"  全体の単勝回収率 {base:.1f}%")

    def table(label, key, cuts):
        print(f"■ {label}（プラス＝その時点から締切までにオッズが下がった＝売れた）")
        for lo, hi, lab in cuts:
            for band, olo, ohi, per in [(b_, l_, h_, pp) for (b_, l_, h_) in (("1〜9.9倍", 0, 10), ("10〜49.9倍", 10, 50)) for pp in ("過去(2023〜2025/9)", "検証(2025/10〜)")]:
                sub = [r for r in rows if r[key] is not None and lo <= r[key] < hi and olo <= r["o"] < ohi and r["period"] == per]
                if len(sub) < 200:
                    continue
                roi = sum(r["o"] * r["win"] for r in sub) / len(sub) * 100
                exp = sum(r["p"] for r in sub)
                w = sum(r["win"] for r in sub)
                z = (w - exp) / math.sqrt(sum(r["p"] * (1 - r["p"]) for r in sub))
                print(f"  {lab:<14}{band:<10}{per:<16}{len(sub):>7,}頭  勝ち{w:>5} (期待{exp:7.1f}) 実際/期待 {w/exp:5.3f} z={z:+5.2f}  単勝回収 {roi:6.1f}%")
    C = [(-9, -0.25, "大きく売れなくなった"), (-0.25, -0.08, "やや売れなくなった"), (-0.08, 0.08, "ほぼ変わらず"), (0.08, 0.25, "やや売れた"), (0.25, 9, "大きく売れた")]
    table("発走30分前→締切", "d30", C)
    table("発走60分前→締切", "d60", C)
    table("前日最終→締切", "dprev", C)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--src", default=str(TS))
    ap.add_argument("--tag", default="")
    ap.add_argument("--delete", action="store_true")
    a = ap.parse_args()
    if a.build:
        build(a.src, a.tag, a.delete)
    analyze()
