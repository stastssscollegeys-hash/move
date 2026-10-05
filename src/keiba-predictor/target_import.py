# -*- coding: utf-8 -*-
"""
target_import.py — TARGET frontier JV に保存済みの JRA-VAN データ（2016〜現在）を、ev_engine が読む形式に変換する（2026-10-02新規）
==================================================================================================================
無料体験の JV-Link は過去データの一括取得（セットアップ）を認証エラー(-301)で拒否する。
一方、インストール済みの TARGET frontier JV は C:\\TFJV に1986年〜の成績を持っており、中身は JV-Data の生レコード
（RA=レース詳細 1270バイト＋CRLF／SE=馬毎レース情報 553バイト＋CRLF）がそのまま入っている。形式の根拠は
JV-Link から直接読んだ 2025〜2026年分（C:\\keiba_db\\jv_raw）と同一であることを確認済み。

入力  C:\\TFJV\\SE_DATA\\{年}\\SR{年}{場回}.DAT（RA）／SU{年}{場回}.DAT（SE）
出力  daily_pdca/db/history_target/results_{年}.json   （history_backfill.py と同じ列。ev_engine --source にフォルダを渡す）
      ※ netkeiba 版（db/history）とは別フォルダ。騎手名・厩舎名の表記が違うので、**1回の学習には片方の出所だけを使う**。

読む項目（JV-Data 仕様のバイト位置・1始まり）
  RA: 12 年(4) 16 月日(4) 20 場(2) 22 回(2) 24 日(2) 26 R(2) 33 競走名(60) 615 グレード(1) 617 競走種別(2) 623 条件コード(3×5)
      698 距離(4) 706 トラック(2) 888 天候(1) 889 芝馬場(1) 890 ダ馬場(1)
  SE: 28 枠(1) 29 馬番(2) 31 血統登録番号(10) 41 馬名(36) 79 性別(1) 83 馬齢(2) 91 調教師略称(8) 289 斤量(3) 307 騎手略称(8)
      325 馬体重(3) 328 増減符号(1) 329 増減(3) 332 異常区分(1) 335 確定着順(2) 339 走破タイム(4) 352〜358 コーナー順位(2×4)
      360 単勝オッズ(4) 364 人気(2) 391 後3F(3)
使い方: python target_import.py [--years 2016 2017 ...] [--verify]
"""
from __future__ import annotations
import argparse, collections, datetime, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path("C:/TFJV/SE_DATA")
OUT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history_target"
VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}
GRADE = {"A": "G1", "B": "G2", "C": "G3", "D": "重賞", "E": "特別", "L": "(L)"}
COND = {"701": "新馬", "702": "新馬", "703": "未勝利", "005": "1勝クラス", "010": "2勝クラス", "016": "3勝クラス", "999": "オープン"}
BABA = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}
WEATHER = {"1": "晴", "2": "曇", "3": "雨", "4": "小雨", "5": "雪", "6": "小雪"}


def seg(r: bytes, a: int, n: int) -> str:
    return r[a - 1:a - 1 + n].decode("cp932", "replace").replace("\u3000", " ").strip()


def to_int(s):
    s = s.strip()
    return int(s) if s.isdigit() else None


def style_of(early, n):
    if not early or n <= 0:
        return ""
    if early <= 2:
        return "逃げ"
    if early <= max(2.0, n * 0.35):
        return "先行"
    if early <= n * 0.65:
        return "差し"
    return "追込"


def records(path: Path, size: int):
    b = path.read_bytes()
    for i in range(0, len(b) - size + 1, size):
        yield b[i:i + size]


def parse_ra(r: bytes):
    if seg(r, 1, 2) != "RA":
        return None
    venue = VENUE.get(seg(r, 20, 2))
    if not venue:
        return None
    track = to_int(seg(r, 706, 2))
    if track is None or track >= 51:           # 障害は除く
        return None
    meters = to_int(seg(r, 698, 4))
    surf = "芝" if track <= 22 else "ダ"
    grade = GRADE.get(seg(r, 615, 1), "")
    conds = [seg(r, 623 + 3 * i, 3) for i in range(5)]
    young = conds[4] if conds[4] != "000" else min((c for c in conds if c != "000"), default="")
    cls = COND.get(young, "")
    kind = to_int(seg(r, 617, 2)) or 0
    name = seg(r, 33, 60)
    baba = BABA.get(seg(r, 889 if surf == "芝" else 890, 1), "")
    cond_text = " ".join(x for x in (grade, cls, name) if x)
    return dict(date=seg(r, 12, 4) + seg(r, 16, 4), venue=venue, R=to_int(seg(r, 26, 2)), name=name, dist=f"{surf}{meters}m",
                baba=baba, weather=WEATHER.get(seg(r, 888, 1), ""), cond=cond_text, flag=seg(r, 3, 1), made=seg(r, 4, 8),
                info=f"{surf}{meters}m / 天候 : {WEATHER.get(seg(r, 888, 1), '')} / {surf} : {baba}", kind=kind,
                f3=(to_int(seg(r, 970, 3)) or 0) / 10.0 or None, b3=(to_int(seg(r, 976, 3)) or 0) / 10.0 or None,
                laps=[(to_int(seg(r, 891 + 3 * i, 3)) or 0) / 10.0 for i in range(25) if to_int(seg(r, 891 + 3 * i, 3))])


def parse_se(r: bytes, entry: bool = False):
    """entry=True: 出走表（まだ結果の無い馬）。着順・オッズは要らない"""
    if seg(r, 1, 2) != "SE":
        return None
    venue = VENUE.get(seg(r, 20, 2))
    if not venue:
        return None
    fin = to_int(seg(r, 335, 2))
    odds = to_int(seg(r, 360, 4))
    if entry:
        if seg(r, 3, 1) not in ("1", "2") or to_int(seg(r, 29, 2)) is None:
            return None
        fin, odds = None, 0
    elif not fin or not odds:                  # 確定着順がない・オッズがない（取消・除外・出走前）は成績として使わない
        return None
    t = seg(r, 339, 4)
    time = f"{int(t[0])}:{t[1:3]}.{t[3]}" if t.isdigit() and t != "0000" else ""
    wt, sign, diff = seg(r, 325, 3), seg(r, 328, 1), seg(r, 329, 3)
    if wt.isdigit() and int(wt) > 0:
        if diff.isdigit() and int(diff) == 0:
            weight = f"{int(wt)}(0)"
        elif sign in ("+", "-") and diff.isdigit() and diff != "999":
            weight = f"{int(wt)}({sign}{int(diff)})"
        else:
            weight = str(int(wt))                  # 初出走などで増減が無い場合は体重だけ
    else:
        weight = ""
    cs = [to_int(seg(r, 352 + 2 * i, 2)) for i in range(4)]
    cs = [c for c in cs if c]
    l3 = to_int(seg(r, 391, 3))
    return dict(date=seg(r, 12, 4) + seg(r, 16, 4), venue=venue, R=to_int(seg(r, 26, 2)), waku=to_int(seg(r, 28, 1)), uma=to_int(seg(r, 29, 2)),
                hid=seg(r, 31, 10), name=seg(r, 41, 36), sex={"1": "牡", "2": "牝", "3": "セ"}.get(seg(r, 79, 1), "?"), age=to_int(seg(r, 83, 2)),
                trainer=seg(r, 91, 8), kin=(to_int(seg(r, 289, 3)) or 0) / 10.0, jockey=seg(r, 307, 8), weight=weight,
                fin=fin, time=time, corners=cs, odds=odds / 10.0, pop=to_int(seg(r, 364, 2)),
                l3=l3 / 10.0 if l3 else None, flag=seg(r, 3, 1), made=seg(r, 4, 8))


_PED = None


def pedigree():
    """TARGET の馬マスタ（UM・1609バイト）から 血統登録番号 → (父, 母父)。血統情報は205バイト目から46バイトずつ（番号10＋馬名36）。
    順序は 父・母・父父・父母・母父・母母…（実在の馬の血統表で確認）"""
    global _PED
    if _PED is None:
        _PED = {}
        for f in sorted(Path("C:/TFJV/UM_DATA").rglob("UM*.DAT")):
            b = f.read_bytes()
            for i in range(0, len(b) - 1608, 1609):
                r = b[i:i + 1609]
                if r[:2] != b"UM":
                    continue
                hid = r[11:21].decode("ascii", "ignore")
                _PED[hid] = (seg(r, 205 + 36 + 10 - 36, 36).strip() if False else seg(r, 215, 36), seg(r, 389 + 10, 36))
    return _PED


def build_rows(ras, ses, entry=False):
    by = collections.defaultdict(list)
    for k, x in ses.items():
        by[k[:3]].append(x)
    rows = []
    for rk, hs in by.items():
        ra = ras.get(rk)
        if not ra or len(hs) < 4:
            continue
        n = len(hs)
        l3s = sorted(h["l3"] for h in hs if h["l3"])
        for h in sorted(hs, key=lambda h: h["uma"]):
            rows.append({
                "date": ra["date"], "競馬場": ra["venue"], "R": ra["R"], "race_id": f"{ra['date']}-{ra['venue']}-{ra['R']}",
                "レース名": ra["name"], "距離": ra["dist"], "馬場状態": ra["baba"], "天候": ra["weather"], "条件": ra["cond"], "コース情報": ra["info"],
                "枠": h["waku"], "馬番": h["uma"], "馬名": h["name"], "horse_id": h["hid"], "性齢": f"{h['sex']}{h['age']}",
                "前3F_レース": ra.get("f3"), "後3F_レース": ra.get("b3"), "ラップ": ra.get("laps"), "斤量_kg": h["kin"], "騎手": h["jockey"], "タイム": h["time"], "着差": "", "コーナー通過": "-".join(str(c) for c in h["corners"]),
                "後3F": h["l3"], "単勝オッズ": h["odds"], "人気": h["pop"], "馬体重": h["weight"], "厩舎": h["trainer"],
                "着順": str(h["fin"]) if h["fin"] else "", "着順int": h["fin"], "後3F順位": (l3s.index(h["l3"]) + 1) if h["l3"] else None,
                "脚質": style_of(h["corners"][0], n) if h["corners"] else "", "頭数": n,
                "父": pedigree().get(h["hid"], ("", ""))[0], "母父": pedigree().get(h["hid"], ("", ""))[1]})
    rows.sort(key=lambda r: (r["date"], r["競馬場"], r["R"], r["馬番"]))
    return rows


def convert_year(y: int):
    d = SRC / str(y)
    ras, ses = {}, {}
    for f in sorted(d.glob("SR*.DAT")):
        for r in records(f, 1272):
            x = parse_ra(r)
            if x and x["R"]:
                k = (x["date"], x["venue"], x["R"])
                if k not in ras or x["made"] >= ras[k]["made"]:
                    ras[k] = x
    for f in sorted(d.glob("SU*.DAT")):
        for r in records(f, 555):
            x = parse_se(r)
            if x and x["R"] and x["uma"]:
                k = (x["date"], x["venue"], x["R"], x["uma"])
                if k not in ses or x["made"] >= ses[k]["made"]:
                    ses[k] = x
    rows = build_rows(ras, ses)
    return rows


def add_gaps(rows):
    last = {}
    for r in sorted(rows, key=lambda r: (r["date"], r["R"])):
        k = r["horse_id"] or r["馬名"]
        d = datetime.date(int(r["date"][:4]), int(r["date"][4:6]), int(r["date"][6:]))
        r["中日数"] = (d - last[k]).days if k in last else None
        last[k] = d


def parse_hr(r: bytes):
    """HR（払戻・717バイト）。単勝103(13×3) 複勝142(13×5) 枠連207(13×3) 馬連246(16×3) ワイド294(16×7) 馬単454(16×6) 3連複550(18×3) 3連単604(19×6)。
    各エントリは 組番＋払戻金(9桁・円/100円)＋人気。2025年7/26札幌1Rの単勝（3番480円・3番人気）で位置を確認。"""
    if seg(r, 1, 2) != "HR":
        return None
    venue = VENUE.get(seg(r, 20, 2))
    if not venue:
        return None
    out = {}

    def take(name, start, n, kl, pl, key):
        w = kl + 9 + pl
        for i in range(n):
            e = r[start - 1 + i * w:start - 1 + (i + 1) * w].decode("ascii", "ignore")
            comb, yen = e[:kl], e[kl:kl + 9]
            if comb.strip("0 ") == "" or not yen.isdigit() or int(yen) == 0:
                continue
            nums = tuple(int(comb[j:j + 2]) for j in range(0, kl, 2))
            out.setdefault(name, {})[key(nums)] = int(yen)

    srt, same = (lambda t: tuple(sorted(t))), (lambda t: t)
    take("単勝", 103, 3, 2, 2, same)
    take("複勝", 142, 5, 2, 2, same)
    take("馬連", 246, 3, 4, 3, srt)
    take("ワイド", 294, 7, 4, 3, srt)
    take("馬単", 454, 6, 4, 3, same)
    take("3連複", 550, 3, 6, 3, srt)
    take("3連単", 604, 6, 6, 4, same)
    return dict(date=seg(r, 12, 4) + seg(r, 16, 4), venue=venue, R=to_int(seg(r, 26, 2)), pay=out, made=seg(r, 4, 8))


def convert_payouts(y: int):
    """年ごとの払戻を db/history_target/payouts_{y}.json（キー "日付|場|R"）に保存"""
    res = {}
    for f in sorted((SRC / str(y)).glob("SH*.DAT")):
        b = f.read_bytes()
        for i in range(0, len(b) - 718, 719):
            x = parse_hr(b[i:i + 719])
            if x and x["R"] and x["pay"]:
                k = f"{x['date']}|{x['venue']}|{x['R']}"
                if k not in res or x["made"] >= res[k]["made"]:
                    res[k] = x
    out = {k: {t: {"-".join(map(str, c)): v for c, v in d.items()} for t, d in x["pay"].items()} for k, x in res.items()}
    (OUT / f"payouts_{y}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return len(out)


def verify(y: int):
    """netkeiba で集めた同じ年のデータと、馬ごとに突き合わせる"""
    p = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "history" / f"results_{y}.json"
    if not p.exists():
        print(f"{y}年: netkeiba側のデータなし")
        return
    a = {(r["date"], r["競馬場"], r["R"], r["馬番"]): r for r in json.loads(p.read_text(encoding="utf-8"))}
    b = {(r["date"], r["競馬場"], r["R"], r["馬番"]): r for r in json.loads((OUT / f"results_{y}.json").read_text(encoding="utf-8"))}
    common = set(a) & set(b)
    print(f"■ {y}年 突き合わせ: netkeiba {len(a):,}頭 / TARGET {len(b):,}頭 / 共通 {len(common):,}頭（TARGETのみ {len(set(b)-set(a)):,}・netkeibaのみ {len(set(a)-set(b)):,}）")
    for col in ("着順int", "単勝オッズ", "人気", "後3F", "タイム", "距離", "馬場状態", "天候", "斤量_kg", "馬体重", "コーナー通過", "脚質", "枠", "性齢"):
        ng = [(k, a[k].get(col), b[k].get(col)) for k in common if a[k].get(col) != b[k].get(col)]
        print(f"  {col:<8} 不一致 {len(ng):>6,} / {len(common):,}（{len(ng)/max(len(common),1)*100:5.2f}%）  例: {ng[:2]}")
    nm = sum(1 for k in common if a[k]["馬名"].replace(" ", "") != b[k]["馬名"].replace(" ", ""))
    print(f"  馬名 不一致 {nm}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int, default=list(range(2016, 2027)))
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for y in a.years:
        rows = convert_year(y)
        add_gaps(rows)
        (OUT / f"results_{y}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        print(f"{y}年: {len({r['race_id'] for r in rows}):,}レース {len(rows):,}頭 / 払戻 {convert_payouts(y):,}レース")
        if a.verify:
            verify(y)
