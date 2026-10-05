# -*- coding: utf-8 -*-
"""
jv_live_odds.py — 発売中のオッズ（単勝〜3連単）を JV-Link の速報（0B30）から取る（2026-10-04新規）
==========================================================================================
JRA-VAN に揃えるため、netkeiba のスナップショット（odds_snapshot.py）の代わりに使う予定。
切り替え前に2週ほど両方を取り、--compare で一致を確かめる（決めた手順・2026-10-04）。
  取得: 32bit PowerShell の jv/jv_rt.ps1 -Spec 0B30 -Key {年月日+場+回+日目+R}
  保存: db/jv_odds_snapshots/{日付}/{場}{R}_{発表時刻MMDDHHMM}.json
        {"venue","R","race_key","announced","fetched_at","odds":{"単勝":{"01":3.2},"馬連":{"0102":12.3},...}}
        ※キーは odds_snapshot と同じ「馬番2桁の連結」。ワイド・複勝は最低オッズ
使い方: python jv_live_odds.py --date 20261004 [--races 東京11,京都11] [--compare]
"""
from __future__ import annotations
import argparse, datetime, json, statistics, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import target_import as T
import jv_odds as J

PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
RTPS = str(Path(__file__).resolve().parent / "jv" / "jv_rt.ps1")
RT = Path("C:/keiba_db/jv_raw/RT")
OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "jv_odds_snapshots"


def race_keys(date):
    """RT の RA（なければ蓄積の RA）から {(場, R): JVレースキー}"""
    keys = {}
    for f in [RT / f"RA_{date}.txt"] + sorted(Path("C:/keiba_db/jv_raw/RACE").glob(f"RA_{date[:4]}.txt")):
        if not f.exists():
            continue
        b = f.read_bytes()
        for i in range(0, len(b) - 1271, 1272):
            r = b[i:i + 1272]
            if T.seg(r, 12, 4) + T.seg(r, 16, 4) != date:
                continue
            v = J.VENUE.get(T.seg(r, 20, 2))
            if v:
                keys.setdefault((v, int(T.seg(r, 26, 2))), T.seg(r, 12, 4) + T.seg(r, 16, 4) + T.seg(r, 20, 2) + T.seg(r, 22, 2) + T.seg(r, 24, 2) + T.seg(r, 26, 2))
    return keys


def fetch(date, venue, R, key):
    tmp = RT / "odds" / date
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", RTPS, "-Spec", "0B30", "-Key", key, "-OutDir", str(tmp)],
                   capture_output=True, timeout=180)
    odds, ann = {}, None
    for oid in ("O1", "O2", "O3", "O4", "O5", "O6"):
        f = tmp / f"{oid}_{key}.txt"
        if not f.exists():
            continue
        t = f.read_bytes().decode("ascii", "ignore")
        ann = ann or t[27:35]
        for name, tab in J.parse_record(oid, t).items():
            odds[name] = {"".join(f"{x:02d}" for x in k): v for k, v in tab.items()}
    if not odds:
        return None
    d = dict(venue=venue, R=R, race_key=key, announced=ann, fetched_at=datetime.datetime.now().isoformat(timespec="seconds"), source="JV-Link 0B30", odds=odds)
    o = OUT / date
    o.mkdir(parents=True, exist_ok=True)
    (o / f"{venue}{R}_{ann}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def latest(date):
    """{(場, R): 最新の JV スナップショット}"""
    out = {}
    for f in sorted((OUT / date).glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        k = (d["venue"], int(d["R"]))
        if k not in out or d["announced"] >= out[k]["announced"]:
            out[k] = d
    return out


def compare(date):
    """netkeiba の最新スナップショットと並べる。時刻がずれるので完全一致は期待しない"""
    import odds_snapshot as O
    nk = {}
    for rid, path in O.latest_snapshots(date).items():
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        nk[(d["venue"], int(d["R"]))] = d
    jv = latest(date)
    print(f"■ {date} JV-Link と netkeiba のオッズ比較（各レースの最新どうし）")
    allr = []
    for k in sorted(set(nk) & set(jv)):
        a, b = jv[k], nk[k]
        line = []
        for t in ("単勝", "馬連", "ワイド", "馬単", "3連複", "3連単"):
            ta, tb = a["odds"].get(t) or {}, b["odds"].get(t) or {}
            com = [c for c in ta if c in tb and tb[c] and tb[c][0] not in (None, "")]
            rel = []
            for c in com:
                try:
                    y = float(tb[c][0])
                except (TypeError, ValueError):
                    continue
                if y > 0:
                    rel.append(abs(ta[c] / y - 1))
            if rel:
                same = sum(1 for x in rel if x < 0.005) / len(rel)
                line.append(f"{t} 一致{same*100:3.0f}%・差の中央値{statistics.median(rel)*100:4.1f}%")
                allr += rel
        print(f"  {k[0]}{k[1]:>2}R JV発表{a['announced'][4:6]}:{a['announced'][6:]} netkeiba取得{str(b.get('fetched_at'))[11:16]} | " + " ／ ".join(line))
    if allr:
        print(f"  全体: 組数{len(allr):,} 差の中央値{statistics.median(allr)*100:.2f}%  差1%未満{sum(1 for x in allr if x < 0.01)/len(allr)*100:.0f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--races", default="")
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()
    keys = race_keys(a.date)
    want = {(x[:2], int(x[2:])) for x in a.races.split(",") if x} if a.races else set(keys)
    n = 0
    for (v, R), key in sorted(keys.items()):
        if (v, R) in want:
            d = fetch(a.date, v, R, key)
            n += bool(d)
            if d:
                print(f"  {v}{R:>2}R 発表{d['announced'][4:6]}:{d['announced'][6:]} " + " ".join(f"{t}{len(x)}" for t, x in d["odds"].items()))
    print(f"■ 取得 {n}/{len(want)} レース → {OUT / a.date}")
    if a.compare:
        compare(a.date)
