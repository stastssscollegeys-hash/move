"""血統名→JV-Link IDマップ構築スクリプト

data/jvlink_v3/bloodline_parsed.jsonl を読み込み、
父名・母父名 → JV-Link 10桁ID のマッピングを生成する。

2023年以降生まれの馬は bloodline_parsed.jsonl に存在しないため、
netkeiba の血統ページから取得した名前（漢字）で JV-Link IDを引くために使う。

使い方:
  python build_name_to_id_maps.py

出力:
  data/stats/name_to_father_id.json   { "ディープインパクト": "1120208600", ... }
  data/stats/name_to_bms_id.json      { "Storm Cat": "1140193100", ... }
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(SRC_DIR, "data")
BLOODLINE_PATH = os.path.join(DATA_DIR, "jvlink_v3", "bloodline_parsed.jsonl")
STATS_DIR = os.path.join(DATA_DIR, "stats")

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def build_maps() -> tuple[dict, dict]:
    """bloodline_parsed.jsonl から父名→ID・母父名→IDマップを構築する。

    同名で複数IDが存在する場合、より多く出現するIDを優先する。
    """
    father_name_counts: dict[str, dict[str, int]] = {}  # name -> {id: count}
    bms_name_counts: dict[str, dict[str, int]] = {}

    with open(BLOODLINE_PATH, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue

            fname = (d.get("father_name") or "").strip()
            fid = (d.get("father") or "").strip()
            mfname = (d.get("mf_name") or "").strip()
            mfid = (d.get("mf") or "").strip()

            if fname and fid:
                father_name_counts.setdefault(fname, {})
                father_name_counts[fname][fid] = father_name_counts[fname].get(fid, 0) + 1

            if mfname and mfid:
                bms_name_counts.setdefault(mfname, {})
                bms_name_counts[mfname][mfid] = bms_name_counts[mfname].get(mfid, 0) + 1

            if (i + 1) % 100_000 == 0:
                print(f"  {i+1} lines processed...", file=sys.stderr)

    # 各名前で最多出現IDを選択
    name_to_father_id = {
        name: max(id_counts, key=id_counts.get)
        for name, id_counts in father_name_counts.items()
    }
    name_to_bms_id = {
        name: max(id_counts, key=id_counts.get)
        for name, id_counts in bms_name_counts.items()
    }

    return name_to_father_id, name_to_bms_id


def main():
    if not os.path.exists(BLOODLINE_PATH):
        print(f"[ERROR] bloodline file not found: {BLOODLINE_PATH}", file=sys.stderr)
        sys.exit(1)

    print("[1/2] Reading bloodline_parsed.jsonl ...", file=sys.stderr)
    name_to_father_id, name_to_bms_id = build_maps()

    print(f"  father name entries: {len(name_to_father_id)}", file=sys.stderr)
    print(f"  BMS name entries:    {len(name_to_bms_id)}", file=sys.stderr)

    os.makedirs(STATS_DIR, exist_ok=True)

    father_path = os.path.join(STATS_DIR, "name_to_father_id.json")
    bms_path = os.path.join(STATS_DIR, "name_to_bms_id.json")

    print("[2/2] Writing JSON files...", file=sys.stderr)
    with open(father_path, "w", encoding="utf-8") as f:
        json.dump(name_to_father_id, f, ensure_ascii=False, indent=None)
    print(f"  -> {father_path}", file=sys.stderr)

    with open(bms_path, "w", encoding="utf-8") as f:
        json.dump(name_to_bms_id, f, ensure_ascii=False, indent=None)
    print(f"  -> {bms_path}", file=sys.stderr)

    # Sanity check with well-known sires
    print("\n[Sanity check] Known sires:", file=sys.stderr)
    known = [
        "ディープインパクト", "キタサンブラック", "ロードカナロア",
        "ハーツクライ", "モーリス", "エピファネイア", "ドゥラメンテ",
        "シルバーステート", "イクイノックス",
    ]
    for name in known:
        fid = name_to_father_id.get(name, "NOT FOUND")
        print(f"  {name}: {fid}", file=sys.stderr)

    print("\n[OK] Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
