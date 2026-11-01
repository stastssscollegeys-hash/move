# -*- coding: utf-8 -*-
"""
influencer_backfill_fetch.py — 予想チャンネルの「レース前の予想動画」を過去分まとめて探し、字幕を保存する（2026-10-30新規）
==============================================================================================================
目的（ユーザー指示 2026-10-30）: インフルエンサーごとの的中率・回収率を出し、重みをつけて独自指数に落とす。
そのために、過去のG1（直近1年・22レース）について、固定リストのチャンネルが出した予想動画を集める。

流れ
  1. 各チャンネルの動画一覧（題名のみ・日本語）を取る
  2. 題名にレース名（略称も）を含む動画を候補にし、投稿日を確認（レース前10日〜当日のものだけ採用）
  3. 自動字幕（日本語）を取り、時刻と重複行を落としたテキストにして保存
出力: daily_pdca/db/influencer_backfill/
  index.json            … [{race_date, race, channel, id, title, date, chars, path}]
  transcripts/{日付}_{チャンネル}_{id}.txt
使い方: python influencer_backfill_fetch.py [--races races.json] [--workers 6]
再実行しても取得済みのものは飛ばす（途中で止まっても続きから）
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, datetime, json, re, subprocess, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path.home() / "Desktop" / "競馬予想レポート" / "daily_pdca" / "db" / "influencer_backfill"
TR = ROOT / "transcripts"

CHANNELS = {
    "アジフライ777": ["UCPspecW20-gD617hl-X-blw"], "競馬全レース予想TV": ["UCztTkAXjEXeQ5yGRn6mKOCQ"],
    "情報通のウマ談義": ["UCXyE9G5akJGoOHyIuc8VphQ"], "しろクロ競馬": ["UCdKD--1CMIRXnR7c0xJOx4g"],
    "うまログ": ["UCN-9wNGk1ouwXISXQmbvW8w"], "アギョウの競馬予想TV": ["UCfCF0xys4sFKkUlRmjWD1Dw"],
    "蓮の競馬予想": ["UClQzuS7GCL_KYX7u1AJydyw", "UC4Xm09PZy1agjMnSfN3nXtg"], "ドンズバ競馬": ["UCsJI68VhqbN8cR2snqg5X_A"],
    "ウマキング": ["UC9Wv6SreCwLZow6XqfzTq6g"], "カリスマ予想": ["UCsZRDf9o-4c0XtvZNTxj_kw"],
    "SPAIA": ["UClg2gn-n8K51xPXRV1rqX8g"], "義英真": ["UCMII-Z1Gr2QErtjj8moEHMQ"],
}
# レース名 → 題名に出やすい語（略称・表記ゆれ）
KW = {
    "天皇賞（秋）": ["天皇賞"], "エリザベス女王杯": ["エリザベス女王杯", "エリ女"], "マイルチャンピオンシップ": ["マイルCS", "マイルチャンピオン", "マイルＣＳ"],
    "ジャパンカップ": ["ジャパンカップ", "ジャパンC", "ジャパンＣ", "JC"], "チャンピオンズカップ": ["チャンピオンズC", "チャンピオンズカップ", "チャンピオンズＣ", "チャンC"],
    "阪神ジュベナイル": ["阪神JF", "阪神ジュベナイル", "阪神ＪＦ"], "朝日杯フューチュリティ": ["朝日杯"], "ホープフルステークス": ["ホープフル"], "有馬記念": ["有馬記念", "有馬"],
    "フェブラリーステークス": ["フェブラリー"], "高松宮記念": ["高松宮"], "大阪杯": ["大阪杯"], "桜花賞": ["桜花賞"], "皐月賞": ["皐月賞"], "天皇賞（春）": ["天皇賞"],
    "NHKマイルカップ": ["NHKマイル", "NHKマイルC"], "ヴィクトリアマイル": ["ヴィクトリアマイル", "ヴィクトリアM"], "優駿牝馬": ["オークス", "優駿牝馬"], "東京優駿": ["ダービー", "日本ダービー", "東京優駿"],
    "安田記念": ["安田記念"], "宝塚記念": ["宝塚記念", "宝塚"], "スプリンターズステークス": ["スプリンターズ"], "秋華賞": ["秋華賞"], "菊花賞": ["菊花賞"],
}
YT = [sys.executable, "-m", "yt_dlp"]


def run(args, timeout=180):
    for i in range(3):
        try:
            p = subprocess.run(YT + args, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
            if p.returncode == 0 or p.stdout.strip():
                return p.stdout
        except subprocess.TimeoutExpired:
            pass
        time.sleep(3 + 5 * i)
    return ""


def list_channel(name, cid):
    out = run([f"https://www.youtube.com/channel/{cid}/videos", "--flat-playlist", "--playlist-end", "900", "--encoding", "utf-8", "--no-warnings",
               "--extractor-args", "youtube:lang=ja", "--print", "%(id)s|%(title)s"], 400)
    vs = []
    for ln in out.splitlines():
        if "|" in ln:
            i, t = ln.split("|", 1)
            vs.append((i, t))
    return name, vs


def video_date(vid):
    out = run([f"https://www.youtube.com/watch?v={vid}", "--skip-download", "--no-warnings", "--print", "%(upload_date)s"], 90)
    s = out.strip().splitlines()[-1].strip() if out.strip() else ""
    return vid, s if re.fullmatch(r"\d{8}", s) else None


def vtt_to_text(p):
    seen, out = set(), []
    for ln in Path(p).read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if not ln or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or "-->" in ln or re.fullmatch(r"\d+", ln):
            continue
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
    return "\n".join(out)


def get_subs(vid, dst):
    tmp = ROOT / "_tmp"
    tmp.mkdir(exist_ok=True)
    run([f"https://www.youtube.com/watch?v={vid}", "--skip-download", "--write-auto-subs", "--sub-langs", "ja", "--sub-format", "vtt", "--no-warnings",
         "-o", str(tmp / f"{vid}.%(ext)s")], 150)
    fs = list(tmp.glob(f"{vid}*.vtt"))
    if not fs:
        return 0
    txt = vtt_to_text(fs[0])
    for f in fs:
        f.unlink()
    dst.write_text(txt, encoding="utf-8")
    return len(txt)


def main(A):
    ROOT.mkdir(parents=True, exist_ok=True); TR.mkdir(exist_ok=True)
    races = json.loads(Path(A.races).read_text(encoding="utf-8"))
    lf = ROOT / "channel_lists.json"
    lists = json.loads(lf.read_text(encoding="utf-8")) if lf.exists() else {}
    jobs = [(n, c) for n, cs in CHANNELS.items() for c in cs if c not in lists]
    with cf.ThreadPoolExecutor(A.workers) as ex:
        for name, vs in ex.map(lambda a: (a[1], list_channel(*a)), jobs):
            lists[name] = dict(channel=vs[0], videos=vs[1])
            print(f"一覧 {vs[0]} {len(vs[1])}本", flush=True)
    lf.write_text(json.dumps(lists, ensure_ascii=False), encoding="utf-8")
    # 候補（題名にレース名）
    cand = {}
    for cid, d in lists.items():
        for vid, title in d["videos"]:
            for r in races:
                if any(k in title for k in KW[r["g1"]]):
                    cand.setdefault(vid, dict(channel=d["channel"], title=title, races=[]))["races"].append(r["date"] + "|" + r["g1"])
    print("候補動画", len(cand), flush=True)
    df = ROOT / "video_dates.json"
    dates = json.loads(df.read_text(encoding="utf-8")) if df.exists() else {}
    todo = [v for v in cand if v not in dates]
    with cf.ThreadPoolExecutor(A.workers) as ex:
        for i, (vid, ds) in enumerate(ex.map(video_date, todo), 1):
            dates[vid] = ds
            if i % 50 == 0:
                print(f"  日付確認 {i}/{len(todo)}", flush=True)
                df.write_text(json.dumps(dates), encoding="utf-8")
    df.write_text(json.dumps(dates), encoding="utf-8")
    # 採用: レース前10日〜当日の動画
    sel = []
    for vid, c in cand.items():
        ds = dates.get(vid)
        if not ds:
            continue
        dv = datetime.datetime.strptime(ds, "%Y%m%d").date()
        for rk in c["races"]:
            rd, g1 = rk.split("|")
            rdt = datetime.datetime.strptime(rd, "%Y%m%d").date()
            if rdt - datetime.timedelta(days=10) <= dv <= rdt:
                sel.append(dict(race_date=rd, race=g1, channel=c["channel"], id=vid, title=c["title"], date=ds))
    print("採用（レース前10日以内）", len(sel), flush=True)
    idx_f = ROOT / "index.json"
    idx = []
    def work(s):
        p = TR / f"{s['race_date']}_{s['channel']}_{s['id']}.txt"
        n = p.stat().st_size if p.exists() else get_subs(s["id"], p)
        return dict(s, chars=n, path=str(p) if n else None)
    with cf.ThreadPoolExecutor(A.workers) as ex:
        for i, r in enumerate(ex.map(work, sel), 1):
            idx.append(r)
            if i % 20 == 0:
                print(f"  字幕 {i}/{len(sel)}", flush=True)
                idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [x for x in idx if x["path"]]
    print(f"完了: 動画{len(idx)}本・字幕あり{len(ok)}本 → {idx_f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--races", default=str(ROOT / "races.json"))
    ap.add_argument("--workers", type=int, default=6)
    main(ap.parse_args())
