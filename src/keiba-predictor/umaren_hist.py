# -*- coding: utf-8 -*-
"""
umaren_hist.py — 過去の馬連の確定前オッズ（JV速報 0B42 の時系列の、発走時刻までの最後の発表）を集める（2026-10-07新規）
=========================================================================================================
JV-Link は 0B30（全券種の確定オッズ）の過去分を出さないが、0B42（馬連の時系列）は2023年以降が取れる。
その最後の発表（発走時刻まで）を「確定オッズ」として使い、実オッズでの買い方の検証を1年→約3年に広げる。
ディスクが少ないので、500レースずつ取得→最後の発表だけ残す→生ファイルを消す。
出力: db/umaren_final_{年}.pkl = {レースキー16桁: {(馬番, 馬番): オッズ}}
使い方: python umaren_hist.py --year 2023
"""
from __future__ import annotations
import argparse, pickle, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import jv_odds as J
import ts_odds as TO

PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
TS_PS = str(Path(__file__).resolve().parent / "jv" / "jv_ts.ps1")
TMP = Path("C:/keiba_db/jv_raw/O2TS")
DB = TO.DB
L = 2042


def main(year):
    keys = [k for k in Path(f"C:/keiba_db/jv_raw/ts_keys_{year}.txt").read_text().split() if k]
    out_f = DB / f"umaren_final_{year}.pkl"
    out = pickle.loads(out_f.read_bytes()) if out_f.exists() else {}
    pt = TO.post_times(years=(year,))
    todo = [k for k in keys if k not in out]
    print(f"■ {year}年 {len(keys):,}レース（済み {len(out):,}）", flush=True)
    TMP.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(todo), 500):
        chunk = todo[i:i + 500]
        kf = TMP / "keys.txt"
        kf.write_text("\n".join(chunk))
        subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", TS_PS, "-KeyFile", str(kf), "-Spec", "0B42", "-OutDir", str(TMP)],
                       capture_output=True, timeout=3600)
        for k in chunk:
            f = TMP / f"{k}.txt"
            if not f.exists():
                continue
            hm = pt.get(k)
            t = f.read_bytes().decode("ascii", "ignore")
            best = None
            for j in range(0, len(t) - L + 1, L):
                rec = t[j:j + L]
                if not rec.startswith("O2"):
                    continue
                ann = rec[27:35]
                if hm and TO.mm(ann) > TO.mm(k[4:8] + hm):
                    continue
                if best is None or ann >= best[0]:
                    best = (ann, rec)
            if best:
                out[k] = J.parse_record("O2", best[1])["馬連"]
            f.unlink()
        out_f.write_bytes(pickle.dumps(out))
        print(f"  {i + len(chunk):,}/{len(todo):,} 済み", flush=True)
    print(f"→ {out_f}（{len(out):,}レース）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True)
    main(ap.parse_args().year)
