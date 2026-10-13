# -*- coding: utf-8 -*-
"""
raceday_auto.py — 土日の当日の流れを自動で回す（2026-10-05新規）
================================================================
先週は台帳への登録が3レースしかできず検証が進まなかった。発走前の作業を人の手順に頼らず回す。
5分ごとに:
  ① JV速報で 成績・払戻（0B12）と 馬体重（0B11）を取る → day_review（当日の馬場の特徴）
  ② 発走まで35分以内に入ったレースがあれば:
       オッズ（netkeiba と JV-Link の両方。JV への切り替え前の並走）→ ev_live --register（そのレースだけ・1回）
       → predict_day（予想カード・版を残す）→ gen_flat_sns / gen_cards_sns（投稿案）
  ③ 全レースが終わったら ev_live --settle と weekend 用の day_review を回して終了
発走時刻は JV の RA レコード（874〜877バイト目・HHMM）から読む。
使い方: python raceday_auto.py --date 20261010 [--lead 35] [--interval 300]
ログ: daily_pdca/db/raceday_logs/{日付}.log
"""
from __future__ import annotations
import argparse, datetime, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import target_import as T

HERE = Path(__file__).resolve().parent
PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
RAW = Path("C:/keiba_db/jv_raw")
MAX_TRIES = 3
LOGD = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "raceday_logs"


def log(msg):
    LOGD.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.datetime.now():%H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOGD / f"{A.date}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(args, timeout=1800):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=HERE)
    tail = (r.stdout or "").strip().splitlines()[-2:]
    log(f"  {' '.join(str(x) for x in args[1:4])} → {r.returncode} {' / '.join(tail)}")
    return r


def jv_rt(spec, outdir=None):
    args = [PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "jv" / "jv_rt.ps1"), "-Spec", spec, "-Key", A.date]
    if outdir:
        args += ["-OutDir", outdir]
    return sh(args, timeout=300)


def post_times():
    """{(場, R): datetime}（RT と蓄積の RA から）"""
    out = {}
    for f in [RAW / "RT" / "entry" / f"RA_{A.date}.txt", RAW / "RT" / f"RA_{A.date}.txt", RAW / "RACE" / f"RA_{A.date[:4]}.txt"]:
        if not f.exists():
            continue
        b = f.read_bytes()
        for i in range(0, len(b) - 1271, 1272):
            r = b[i:i + 1272]
            x = T.parse_ra(r)
            if not x or x["date"] != A.date or not x["R"]:
                continue
            hm = r[873:877].decode("ascii", "ignore")
            if hm.isdigit() and (x["venue"], x["R"]) not in out:
                out[(x["venue"], x["R"])] = datetime.datetime.strptime(A.date + hm, "%Y%m%d%H%M")
    return out


def finished():
    """成績が出たレース"""
    f = RAW / "RT" / f"HR_{A.date}.txt"
    done = set()
    if f.exists():
        b = f.read_bytes()
        for i in range(0, len(b) - 718, 719):
            h = T.parse_hr(b[i:i + 719])
            if h and h["date"] == A.date:
                done.add((h["venue"], h["R"]))
    return done


def main():
    py = sys.executable
    handled = set()
    tries = {}
    log(f"■ {A.date} 自動運転を開始（発走{A.lead}分前に登録・{A.interval}秒ごと）")
    while True:
        jv_rt("0B15", str(RAW / "RT" / "entry"))        # 出走表・馬場・発走時刻（RA/SE）。0B12 の成績を上書きしないよう別フォルダ
        jv_rt("0B11", str(RAW / "RT" / "wh"))           # 馬体重
        jv_rt("0B12")                                   # 成績・払戻
        sh([py, "day_review.py", "--date", A.date])
        pt = post_times()
        done = finished()
        if not pt:
            log("発走時刻が読めません（RA 未取得）。待機")
        now = datetime.datetime.now()
        due = sorted(k for k, t in pt.items() if k not in handled and k not in done and t - datetime.timedelta(minutes=A.lead) <= now < t)
        if due:
            names = ",".join(f"{v}{r}" for v, r in due)
            log(f"発走前の処理: {names}")
            sh([py, "odds_snapshot.py", "--date", A.date])
            sh([py, "jv_live_odds.py", "--date", A.date, "--races", names, "--compare"])
            rc = sh([py, "ev_live.py", "--date", A.date, "--register", "--races", names]).returncode
            if rc != 0:
                # 失敗（MemoryError等）のレースは次の周期で再試行する。発走を過ぎたら due から外れるので無限には回らない
                for k in due:
                    tries[k] = tries.get(k, 0) + 1
                give_up = [k for k in due if tries[k] >= MAX_TRIES]
                log(f"  ev_live 失敗（{names}）。再試行 {', '.join(f'{v}{r}:{tries[(v, r)]}回' for v, r in due)}")
                handled.update(give_up)
                time.sleep(A.interval)
                continue
            sh([py, "predict_day.py", "--date", A.date])
            sh([py, "gen_flat_sns.py", "--dir", A.date])
            if any(r == 11 for _, r in due):
                sh([py, "gen_cards_sns.py", "--dir", A.date])
            sh([py, "word_order_by_ev.py", "--dir", A.date])    # 期待値の取れるレースを上・それ以外を参考として下（冪等）
            handled.update(due)
        rest = [k for k in pt if k not in done]
        if pt and not rest:
            sh([py, "ev_live.py", "--settle"])
            sh([py, "ev_live.py", "--report"])
            log("■ 全レース終了。精算して終了")
            return
        nxt = min((t for k, t in pt.items() if k not in handled and k not in done), default=None)
        log(f"待機（次の発走 {nxt:%H:%M}）" if nxt else "待機")
        time.sleep(A.interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--lead", type=int, default=35)
    ap.add_argument("--interval", type=int, default=300)
    A = ap.parse_args()
    main()
