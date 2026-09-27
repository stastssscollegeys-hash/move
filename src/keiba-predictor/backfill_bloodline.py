# -*- coding: utf-8 -*-
"""
backfill_bloodline.py — 蓄積DBに父名・母父名を遡って埋める
==========================================================================
なぜ必要か
----------
2026-09-07 の点検で、蓄積DB（race_results.json・14,982頭）に
**種牡馬名が1件も入っていない**ことが判明した。
持っていたのは `父勝率%` という数値だけで、しかもその5割強が
「0.0＝データ無し」（5/23〜8/30は51〜71%が欠損）だった。

つまり「キズナ産駒は中距離で強い」のような検証を、
**自前データでは一度も行えない状態だった。**

救出経路
--------
    _cache/netkeiba/shutuba.json     馬名 → horse_id（＝血統登録番号 ketto_num）
    data/jvlink_v3/bloodline_parsed.jsonl   ketto_num → father_name / mf_name
                    ↓ 馬名で突合
    race_results.json に 父 / 母父 を追記

これで過去分も種牡馬別に集計できるようになる。
以後の新規収集は collect_weekend_bigdata.py 側で直接 父/母父 を記録する
（2026-09-07に修正済み）ので、このスクリプトは遡及専用。

使い方
------
    python backfill_bloodline.py            # 上書きせず内容を確認（ドライラン）
    python backfill_bloodline.py --write    # race_results.json を更新
"""
from __future__ import annotations
import argparse, json, sys, io, shutil
from pathlib import Path
from collections import Counter

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
DB = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db"
RESULTS = DB / "race_results.json"
SHUTUBA = HERE / "_cache" / "netkeiba" / "shutuba.json"
BLOODLINE = HERE / "data" / "jvlink_v3" / "bloodline_parsed.jsonl"


def name_to_ketto() -> dict[str, str]:
    """出馬表キャッシュから 馬名 → 血統登録番号 を作る"""
    if not SHUTUBA.exists():
        print(f"⚠ 出馬表キャッシュが無い: {SHUTUBA}")
        return {}
    data = json.load(open(SHUTUBA, encoding="utf-8"))
    m: dict[str, str] = {}
    for race in data.values():
        for h in (race.get("horses") or []):
            nm, hid = h.get("horse_name"), h.get("horse_id")
            if nm and hid:
                m[nm] = hid
    return m


def ketto_to_sires(want: set[str]) -> dict[str, tuple[str, str]]:
    """必要な血統登録番号ぶんだけ 父名・母父名 を引く（316MBを1行ずつ流す）"""
    out: dict[str, tuple[str, str]] = {}
    if not BLOODLINE.exists():
        print(f"⚠ 血統DBが無い: {BLOODLINE}")
        return out
    with open(BLOODLINE, encoding="utf-8") as f:
        for line in f:
            # 全件JSONパースすると遅いので、必要な番号を含む行だけ処理する
            if len(out) == len(want):
                break
            try:
                i = line.index('"ketto_num": "') + 14
                k = line[i:i + 10]
            except ValueError:
                continue
            if k not in want or k in out:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[k] = (d.get("father_name", "") or "", d.get("mf_name", "") or "")
    return out


def main(write: bool) -> None:
    rows = json.load(open(RESULTS, encoding="utf-8"))
    print(f"蓄積DB: {len(rows):,}頭\n")

    n2k = name_to_ketto()
    print(f"① 出馬表キャッシュ  馬名→血統登録番号 {len(n2k):,}頭ぶん")

    need = {n2k[r["馬名"]] for r in rows if r.get("馬名") in n2k}
    print(f"② 突合が必要な血統登録番号 {len(need):,}件")

    sires = ketto_to_sires(need)
    print(f"③ 血統DBから引けた {len(sires):,}件\n")

    hit = miss = 0
    fc: Counter = Counter()
    for r in rows:
        k = n2k.get(r.get("馬名", ""))
        s = sires.get(k) if k else None
        if s and s[0]:
            r["父"], r["母父"] = s
            hit += 1
            fc[s[0]] += 1
        else:
            r.setdefault("父", "")
            r.setdefault("母父", "")
            miss += 1

    print(f"═══ 結果 ═══")
    print(f"  父名を埋められた: {hit:,}頭 ({hit/len(rows)*100:.1f}%)")
    print(f"  埋められなかった: {miss:,}頭 ({miss/len(rows)*100:.1f}%)")
    print(f"  出現した種牡馬:   {len(fc):,}頭\n")

    if fc:
        print("  産駒数TOP15（自前DBでの出走数）")
        for nm, c in fc.most_common(15):
            print(f"    {nm:<20}{c:>5}頭")

    if not write:
        print("\n※ ドライラン。実際に書き込むには --write を付けてください。")
        return

    bak = RESULTS.with_suffix(".json.bak_before_bloodline")
    if not bak.exists():
        shutil.copy2(RESULTS, bak)
        print(f"\nバックアップ作成: {bak.name}")
    json.dump(rows, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"更新しました: {RESULTS}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="実際にDBを更新する")
    main(ap.parse_args().write)
