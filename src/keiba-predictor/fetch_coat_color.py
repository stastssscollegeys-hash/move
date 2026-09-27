# -*- coding: utf-8 -*-
"""
fetch_coat_color.py — 馬の実際の毛色をnetkeibaから取得する（2026-09-28新規）
================================================================================
注目馬インフォグラフィックで、馬の毛色を勝手に割り当てていたため実物と違っていた
（ユーザー指摘）。netkeibaの馬プロフィールには「毛色」欄があるのでそこから取る。
取得元: **www.keibalab.jp/db/horse/{netkeiba_horse_id}/** のプロフィール「毛色」行。
  ⚠ db.netkeiba.com/horse/ は2026-09-28時点でプロフィール表がHTMLに無い（有料化）。
  ⚠ WebFetchツールは競馬ラボ・JBISとも403。User-Agent＋Referer＋Accept-Language を付ければ通る。
馬名→horse_id は _cache/name_to_horseid.json を使い、無ければ出馬表キャッシュから補う。

使い方: python fetch_coat_color.py 馬名 馬名 ...
        python fetch_coat_color.py --file 馬名リスト.txt
出力: _cache/coat_color.json （馬名 → {"毛色":..., "生年":..., "horse_id":...}）
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/153.0 Safari/537.36",
       "Accept-Language": "ja,en;q=0.9", "Referer": "https://www.google.com/",
       "Accept": "text/html,application/xhtml+xml"}


def fetch(url: str, enc="utf-8", retry=3):
    for i in range(retry):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25) as r:
                return r.read().decode(enc, "replace")
        except Exception as e:
            if i == retry - 1:
                print(f"[WARN] {url} {e}")
                return ""
            time.sleep(2)
    return ""

HERE = Path(__file__).resolve().parent
IDMAP = HERE / "_cache" / "name_to_horseid.json"
SHUTUBA = HERE / "_cache" / "netkeiba" / "shutuba.json"
OUT = HERE / "_cache" / "coat_color.json"

ap = argparse.ArgumentParser()
ap.add_argument("names", nargs="*")
ap.add_argument("--file")
ap.add_argument("--sleep", type=float, default=1.0)
a = ap.parse_args()

names = list(a.names)
if a.file:
    names += [x.strip() for x in Path(a.file).read_text(encoding="utf-8").splitlines() if x.strip()]
if not names:
    sys.exit("馬名を指定してください")

name2id = json.loads(IDMAP.read_text(encoding="utf-8")) if IDMAP.exists() else {}
if SHUTUBA.exists():
    for v in json.loads(SHUTUBA.read_text(encoding="utf-8")).values():
        for h in v.get("horses", []):
            if h.get("horse_name") and h.get("horse_id"):
                name2id.setdefault(h["horse_name"], h["horse_id"])

out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
print(f"{'馬名':<16}{'毛色':<8}{'生年月日':<14} horse_id")
for nm in names:
    if nm in out and out[nm].get("毛色"):
        print(f"{nm:<16}{out[nm]['毛色']:<8}{out[nm].get('生年',''):<14} (キャッシュ)")
        continue
    hid = name2id.get(nm)
    if not hid:
        print(f"{nm:<16}（horse_id不明・手動で補う）")
        continue
    html = fetch(f"https://www.keibalab.jp/db/horse/{hid}/")
    if not html:
        print(f"{nm:<16}（取得失敗）")
        continue
    txt = re.sub(r"\t+", "\t", re.sub(r"<[^>]+>", "\t", html))
    # 競馬ラボは 「毛色\t\n\t鹿毛」 のように間に改行が入るので \s+ で受ける
    m = re.search(r"毛色\s+([^\t\n]+)", txt)
    coat = m.group(1).strip() if m else ""
    m2 = re.search(r"生年月日\s+([^\t\n]+)", txt)
    born = m2.group(1).strip() if m2 else ""
    out[nm] = {"毛色": coat, "生年": born, "horse_id": hid, "src": "keibalab"}
    print(f"{nm:<16}{coat:<8}{born:<14} {hid}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(a.sleep)

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n保存: {OUT}（{len(out)}頭）")
