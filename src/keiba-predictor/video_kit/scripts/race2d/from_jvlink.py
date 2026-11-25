# -*- coding: utf-8 -*-
"""終わったレースの展開を、JV-Link のデータ（races.jsonl・horses.jsonl）から race2d の JSON にする（2026-11-19）
使い方: python from_jvlink.py <race_id 16桁> <JV-Linkのフォルダ> <出力.json>
  例: python from_jvlink.py 2026022205010811 <JV-Linkのデータのフォルダ> feb.json

取れるもの（データどおり）:
  ・3コーナー／4コーナーの順位（同じ順位＝併走）
  ・残り600m 地点の差＝各馬の「走破タイム − 上がり3ハロン」の差（0.1秒単位）
  ・ゴールの差＝走破タイムの差／ラップ（先頭の馬の200mごと）
推定になるもの: コーナーとコーナーの間の動き・内か外か（build_frames.py が決める）
騎手名は出さない（2026-11-19 ユーザー「馬番に加えて馬名も」＝馬番と馬名だけ）
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from course_key import course_key   # 2026-11-20 内回り・外回り・直線をトラックコードで分ける

VENUE = {"01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京", "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"}


def tsec(t):          # "1354" → 95.4 秒（1分35秒4）
    t = t.strip()
    return int(t[0]) * 60 + int(t[1:]) / 10 if t and t != "0000" else None


def grep(path, rid):
    key = f'"race_id": "{rid}"'
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if key in l]


def main():
    rid, src, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    races = grep(src / "races.jsonl", rid)
    if not races:
        sys.exit(f"races.jsonl に {rid} がありません（JV-Link のデータは取り込んだ日まで）")
    r = races[-1]
    hs = grep(src / "horses.jsonl", rid)
    surface = "芝" if r["track_cd"].startswith("1") else "ダート"
    laps = [int(x) / 10 for x in r["lap_times"].split(",") if x.strip() and int(x) > 0]
    D = int(r["distance"])
    horses = []
    for h in hs:
        fin = int(h["kakutei_jyuni"] or 0)
        T = tsec(h["time"]); l3 = int(h["haron_l3"]) / 10 if h["haron_l3"].strip("0") else None
        horses.append(dict(
            umaban=int(h["umaban"]), waku=int(h["waku"]), name=h["bamei"].strip(), finish=fin or None,
            time=T, last3f=l3,
            corners={k: (int(h[f"jyuni_{k}"]) or None) for k in ("1c", "2c", "3c", "4c")},
            style=int(h["kyakusitu_kubun"] or 0) or None))          # 1逃げ 2先行 3差し 4追込
    horses.sort(key=lambda x: x["umaban"])
    data = dict(
        source="jvlink", race_id=rid,
        race=dict(name=r["race_name"].strip() or f"{int(r['race_num'])}R", date=f"{r['year']}-{r['month']}-{r['day']}",
                  venue=VENUE.get(r["venue_code"], r["venue_code"]), surface=surface, distance=D,
                  course=course_key(VENUE.get(r['venue_code'], ''), r['track_cd']), laps=laps, runners=len(horses)),
        horses=horses)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for h in horses if h["time"] and h["last3f"] and h["corners"]["4c"])
    print(f"✅ {out}  {data['race']['name']} {data['race']['venue']}{surface}{D}m {len(horses)}頭（タイム・上がり・4角がそろう馬 {ok}頭）ラップ {len(laps)}本")


if __name__ == "__main__":
    main()
