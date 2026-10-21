# -*- coding: utf-8 -*-
"""
jv_to_history.py — JV-Link で取った最新の成績・払戻・オッズを、10年分のデータベースに足す（2026-10-07新規・毎週月〜水に実行）
=========================================================================================================
TARGET（C:/TFJV）の更新を待たずに、データベースを最新にする。
  入力: C:/keiba_db/jv_raw_new/RACE/{RA,SE,HR,O1〜O6}_{年}.txt（jv_extract.ps1 -OutDir C:\\keiba_db\\jv_raw_new。既存の年ファイルを上書きしないよう別フォルダ）
  出力: db/history_target/results_{年}.json・payouts_{年}.json に、まだ無い日付のレースを追加
        C:/keiba_db/jv_raw/RACE/O1〜O6_{年}.txt に、まだ無いレースのオッズを追記
手順: 32bit PowerShell で jv/jv_extract.ps1 -Spec RACE -From {前回の最終日}000000 -Option 1 -Keep RA,SE,HR,O1,O2,O3,O4,O5,O6 -OutDir C:\\keiba_db\\jv_raw_new
      → python jv_to_history.py
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import target_import as T
import jv_odds as J

NEW = Path("C:/keiba_db/jv_raw_new/RACE")
RAW = Path("C:/keiba_db/jv_raw/RACE")
H = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history_target"
OLEN = {"O1": 962, "O2": 2042, "O3": 2654, "O4": 4031, "O5": 12293, "O6": 83285}


def main():
    years = sorted({f.stem.split("_")[1] for f in NEW.glob("SE_*.txt")})
    for y in years:
        ras, ses, hrs = {}, {}, {}
        for f in NEW.glob(f"RA_{y}.txt"):
            b = f.read_bytes()
            for i in range(0, len(b) - 1271, 1272):
                x = T.parse_ra(b[i:i + 1272])
                if x and x["R"]:
                    k = (x["date"], x["venue"], x["R"])
                    if k not in ras or x["made"] >= ras[k]["made"]:
                        ras[k] = x
        for f in NEW.glob(f"SE_{y}.txt"):
            b = f.read_bytes()
            for i in range(0, len(b) - 554, 555):
                x = T.parse_se(b[i:i + 555])
                if x and x["R"] and x["uma"] and x["fin"]:
                    k = (x["date"], x["venue"], x["R"], x["uma"])
                    if k not in ses or x["made"] >= ses[k]["made"]:
                        ses[k] = x
        for f in NEW.glob(f"HR_{y}.txt"):
            b = f.read_bytes()
            for i in range(0, len(b) - 718, 719):
                x = T.parse_hr(b[i:i + 719])
                if x and x["R"] and x["pay"]:
                    k = f"{x['date']}|{x['venue']}|{x['R']}"
                    if k not in hrs or x["made"] >= hrs[k]["made"]:
                        hrs[k] = x
        rows = T.build_rows(ras, ses)
        rf, pf = H / f"results_{y}.json", H / f"payouts_{y}.json"
        old = json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else []
        have = {(r["date"], r["競馬場"], r["R"]) for r in old}
        add = [r for r in rows if (r["date"], r["競馬場"], r["R"]) not in have]
        pays = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
        addp = {k: {t: {"-".join(map(str, c)): v for c, v in d.items()} for t, d in x["pay"].items()} for k, x in hrs.items() if k not in pays}
        if add:
            rf.write_text(json.dumps(old + add, ensure_ascii=False), encoding="utf-8")
        if addp:
            pays.update(addp)
            pf.write_text(json.dumps(pays, ensure_ascii=False), encoding="utf-8")
        days = sorted({r["date"] for r in add})
        print(f"■ {y}年: 成績 +{len({(r['date'], r['競馬場'], r['R']) for r in add})}レース（{len(add):,}頭）・払戻 +{len(addp)}レース  日付 {days[0] if days else '-'}〜{days[-1] if days else '-'}")
        # オッズ（全券種）を追記
        for oid, L in OLEN.items():
            src, dst = NEW / f"{oid}_{y}.txt", RAW / f"{oid}_{y}.txt"
            if not src.exists():
                continue
            have_o = set()
            if dst.exists():
                with open(dst, "rb") as fh:
                    size = dst.stat().st_size
                    for i in range(0, size, L):
                        fh.seek(i)
                        h = fh.read(40)
                        have_o.add(h[11:27])
            b = src.read_bytes()
            n = 0
            with open(dst, "ab") as fo:
                for i in range(0, len(b) - L + 1, L):
                    r = b[i:i + L]
                    if r[11:27] not in have_o and r[:2].decode("ascii", "ignore") == oid:
                        fo.write(r)
                        have_o.add(r[11:27])
                        n += 1
            print(f"  {oid}: +{n}レース")


if __name__ == "__main__":
    main()
