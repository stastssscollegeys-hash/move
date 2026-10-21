# -*- coding: utf-8 -*-
"""
friday_prep.py — 週末の予想の前に要るデータを1回で取り込み、足りないものを点検する（2026-10-08新規）
=====================================================================================
取り忘れると、調教の欄や「先週の傾向」の欄が古いまま予想が出てしまう。金曜（重賞の枠順確定後）と土曜の夜に回す。
  ① 出走表・発走時刻・柵（JV 0B15 → RT/entry）と 馬場の前日発表・天候（JV 0B14 → RT/info の WE）を 週末の各日について取る
  ② 調教（JV SLOP/WOOD）を TARGET の最終日から取り直し → chokyo.py --build
  ③ 点検: 日ごと・場ごとのレース数／柵（先週と比べて柵替えか）／開催替わりか／馬場の発表（先週と比べて悪化・回復）
           ／出走馬のうち直近21日に調教がある割合／先週の振り返り（day_review）の有無／オッズ（前日発売）の有無
  ④ --cards を付けると、オッズがある日について ev_live → predict_day → 投稿案 まで作る（1日ずつ・メモリ対策）
使い方: python friday_prep.py [--dates 20261010,20261011,20261012] [--skip-chokyo] [--cards]
出力: 画面と daily_pdca/db/raceday_logs/prep_{最初の日}.log
"""
from __future__ import annotations
import argparse, collections, datetime, glob, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import target_import as T
import jv_odds as J

HERE = Path(__file__).resolve().parent
PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
RAW = Path("C:/keiba_db/jv_raw")
BASE = Path.home() / "Desktop" / "競馬予想レポート"
LOGD = BASE / "daily_pdca" / "db" / "raceday_logs"
LINES = []


def say(msg=""):
    print(msg, flush=True)
    LINES.append(msg)


def ps(args, timeout):
    r = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, cwd=HERE)
    return r.returncode, (r.stdout or "").strip().splitlines()


def py(args, timeout=3600):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=HERE)
    tail = (r.stdout or "").strip().splitlines()[-3:] + (r.stderr or "").strip().splitlines()[-2:]
    say(f"  {' '.join(args[:3])} → {'OK' if r.returncode == 0 else '失敗 ' + str(r.returncode)}  " + " / ".join(tail))
    return r.returncode


def weekend_dates():
    d = datetime.date.today()
    sat = d + datetime.timedelta(days=(5 - d.weekday()) % 7)
    return [(sat + datetime.timedelta(days=k)).strftime("%Y%m%d") for k in range(3)]   # 土日月（月曜開催がなければ空で返るだけ）


def races_of(date):
    """{(場, R): (回, 日目, 柵, 距離)}（RT/entry の RA）"""
    out = {}
    f = RAW / "RT" / "entry" / f"RA_{date}.txt"
    if not f.exists():
        return out
    b = f.read_bytes()
    for i in range(0, len(b) - 1271, 1272):
        r = b[i:i + 1272]
        x = T.parse_ra(r)
        if x and x["date"] == date and x["R"]:
            out[(x["venue"], x["R"])] = (T.seg(r, 22, 2), T.seg(r, 24, 2), r[709:710].decode("ascii", "ignore").strip(), x["dist"])
    return out


def entrants(date):
    f = RAW / "RT" / "entry" / f"SE_{date}.txt"
    out = collections.defaultdict(list)
    if not f.exists():
        return out
    b = f.read_bytes()
    for i in range(0, len(b) - 554, 555):
        x = T.parse_se(b[i:i + 555], entry=True) or T.parse_se(b[i:i + 555])
        if x and x["date"] == date and x["hid"] not in out[x["venue"]]:
            out[x["venue"]].append(x["hid"])
    return out


def ck_last_target():
    fs = sorted(glob.glob("C:/TFJV/CK_DATA/*/*/*.DAT"))
    return max(Path(f).stem[-8:] for f in fs) if fs else "20260801"


def main(A):
    dates = A.dates.split(",") if A.dates else weekend_dates()
    say(f"■ 週末の準備 {datetime.datetime.now():%m/%d %H:%M}  対象 {', '.join(dates)}")

    say("① 出走表・柵・発走時刻（0B15）と馬場の発表（0B14）")
    for d in dates:
        c1, o1 = ps([str(HERE / "jv" / "jv_rt.ps1"), "-Spec", "0B15", "-Key", d, "-OutDir", str(RAW / "RT" / "entry")], 600)
        c2, o2 = ps([str(HERE / "jv" / "jv_rt.ps1"), "-Spec", "0B14", "-Key", d, "-OutDir", str(RAW / "RT" / "info")], 300)
        say(f"  {d}: 出走表 {'取得' if any('records=' in x and 'records=0' not in x for x in o1) else 'まだ無し'}"
            f"／馬場・天候 {'取得' if any('records=' in x and 'records=0' not in x for x in o2) else 'まだ無し'}")

    if not A.skip_chokyo:
        frm = ck_last_target()
        say(f"② 調教（TARGET の最終日 {frm} 以降を JV から）")
        for spec, keep in (("SLOP", "HC"), ("WOOD", "WC")):
            c, o = ps([str(HERE / "jv" / "jv_extract.ps1"), "-Spec", spec, "-From", frm + "000000", "-Option", "1", "-Keep", keep], 1800)
            say(f"  {spec}: {'OK' if c == 0 else '失敗'} " + " / ".join(o[-2:]))
        py(["chokyo.py", "--build"])

    say("③ 点検")
    import chokyo, race_meta as RM
    import predict_day as P
    CK = chokyo.load()
    M = RM.load()
    for d in dates:
        rs = races_of(d)
        if not rs:
            say(f"  {d}: 出走表なし（開催が無いか、まだ配信前。JRAの発表は木曜午後〜金曜）")
            continue
        d0 = datetime.date(int(d[:4]), int(d[4:6]), int(d[6:]))
        lim = (d0 - datetime.timedelta(days=21)).strftime("%Y%m%d")
        ent = entrants(d)
        say(f"  {d}（{'月火水木金土日'[d0.weekday()]}）")
        for v in sorted({v for v, _ in rs}):
            mine = {R: x for (vv, R), x in rs.items() if vv == v}
            kai, nichi = collections.Counter(x[0] for x in mine.values()).most_common(1)[0][0], max(x[1] for x in mine.values())
            rail = collections.Counter(x[2] for x in mine.values() if x[2]).most_common(1)
            rail = rail[0][0] if rail else "?"
            pw = {(d0 - datetime.timedelta(days=k)).strftime("%Y%m%d") for k in range(5, 10)}   # 先週末（predict_day.week_bias_note と同じ窓）
            prev = [(k, x) for k, x in M.items() if k[1] == v and k[0] in pw and x[2]]
            prv_rail = collections.Counter(x[2] for k, x in prev).most_common(1)[0][0] if prev else ""
            prv_kai = collections.Counter(x[0] for k, x in prev).most_common(1)[0][0] if prev else ""
            if prev and prv_kai != kai:
                change = "開催替わり → 先週の傾向は持ち越さない"
            elif prv_rail and prv_rail != rail:
                change = f"柵替え（{prv_rail}→{rail}）→ 偏りリセット・内枠やや有利"
            elif prev:
                change = f"同じ開催・同じ柵（{rail}）→ 先週の芝の内外の偏りが続きやすい"
            else:
                change = "先週この場の開催なし"
            g_t, g_d = P.going_now(d, v, "芝"), P.going_now(d, v, "ダ")
            hids = ent.get(v, [])
            fresh = sum(1 for h in hids if any(x[0] >= lim for x in (CK.get(h) or [])))
            say(f"    {v} {int(kai)}回{int(nichi)}日目 {len(mine)}R ／ {change}")
            pg = collections.Counter()
            for dd in sorted(pw):
                f = BASE / dd / "research" / f"day_review_{dd}.json"
                if f.exists():
                    pg.update(json.loads(f.read_text(encoding="utf-8"))["venues"].get(f"{v}芝", {}).get("baba", {}))
            pgs = "・".join(f"{k}{n}R" for k, n in pg.most_common()) or "—"
            say(f"       先週の芝の馬場: {pgs} ／ 今週の発表: 芝 {g_t or '未発表'}・ダ {g_d or '未発表'} ／ 調教あり（直近21日）{fresh}/{len(hids)}頭"
                + ("" if not hids or fresh / len(hids) >= 0.8 else "  🔴少ない（調教データの取り込み漏れの疑い）"))
        for k in range(5, 10):
            dd = (d0 - datetime.timedelta(days=k)).strftime("%Y%m%d")
            if (BASE / dd / "research" / f"cards_{dd}.json").exists() and not (BASE / dd / "research" / f"day_review_{dd}.json").exists():
                say(f"    🔴 先週 {dd} の振り返りが無い → python day_review.py --date {dd}")
        snap = list((BASE / "daily_pdca" / "db" / "odds_snapshots").glob(f"*{d}*")) if (BASE / "daily_pdca" / "db" / "odds_snapshots").exists() else []
        say(f"    オッズ（前日発売）: {'あり' if snap else 'まだ（前日発売の開始後に odds_snapshot.py --date ' + d + '）'}")

    if A.cards:
        say("④ 予想カードと投稿案（オッズがある日だけ）")
        for d in dates:
            if not races_of(d):
                continue
            if py(["odds_snapshot.py", "--date", d], 1800) != 0:
                continue
            if py(["ev_live.py", "--date", d]) == 0 and py(["predict_day.py", "--date", d]) == 0:
                py(["gen_flat_sns.py", "--dir", d], 600)
                py(["gen_cards_sns.py", "--dir", d], 600)

    LOGD.mkdir(parents=True, exist_ok=True)
    (LOGD / f"prep_{dates[0]}.log").write_text("\n".join(LINES) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", default="")
    ap.add_argument("--skip-chokyo", action="store_true")
    ap.add_argument("--cards", action="store_true", help="オッズがある日について予想カードと投稿案まで作る")
    main(ap.parse_args())
