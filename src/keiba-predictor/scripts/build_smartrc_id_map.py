"""
smartrc f_code/mf_code → JV-Link father/bms ID マッピングテーブル生成

smartrcのhcode（馬ID）がJV-Linkのketto_numと一致する馬を利用して、
smartrcの種牡馬コード体系 → JV-Link血統IDの対応表を構築する。

データが増えるほどカバー率が向上する設計。
smartrcキャッシュとJV-Linkのbloodlineデータの両方が必要。

出力:
  - data/stats/smartrc_fcode_map.json   {smartrc_f_code: jvlink_father_id}
  - data/stats/smartrc_mfcode_map.json  {smartrc_mf_code: jvlink_bms_id}
"""
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(SRC_DIR, 'data')
STATS_DIR = os.path.join(DATA_DIR, 'stats')
CACHE_DIR = os.path.join(SRC_DIR, '_cache')

def main():
    os.makedirs(STATS_DIR, exist_ok=True)

    # Load smartrc runners cache
    runners_path = os.path.join(CACHE_DIR, 'smartrc_runners.json')
    if not os.path.exists(runners_path):
        print("[ERROR] smartrc_runners.json not found", file=sys.stderr)
        return

    print("Loading smartrc cache...", file=sys.stderr)
    with open(runners_path, encoding='utf-8') as f:
        smartrc_data = json.load(f)

    # Load JV-Link bloodline
    blood_path = os.path.join(DATA_DIR, 'jvlink_v3', 'bloodline_parsed.jsonl')
    print("Loading bloodline...", file=sys.stderr)
    blood = {}
    with open(blood_path, encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            blood[d['ketto_num']] = d

    print(f"  {len(blood)} bloodline records", file=sys.stderr)

    # Build mapping: smartrc code → JV-Link ID
    fcode_map = {}
    mfcode_map = {}

    matched = 0
    total = 0

    for rcode, runners in smartrc_data.items():
        for r in runners:
            total += 1
            hcode = r.get('hcode', '')
            if hcode not in blood:
                continue
            matched += 1

            bl = blood[hcode]
            fc = str(r.get('f_code', '')).strip()
            mfc = str(r.get('mf_code', '')).strip()
            father_id = bl.get('father', '')
            bms_id = bl.get('mf', '')

            if fc and father_id:
                fcode_map[fc] = father_id
            if mfc and bms_id:
                mfcode_map[mfc] = bms_id

    print(f"  Matched horses: {matched}/{total} ({matched/total*100:.0f}%)", file=sys.stderr)
    print(f"  Father code mappings: {len(fcode_map)}", file=sys.stderr)
    print(f"  BMS code mappings: {len(mfcode_map)}", file=sys.stderr)

    # Save
    fmap_path = os.path.join(STATS_DIR, 'smartrc_fcode_map.json')
    mfmap_path = os.path.join(STATS_DIR, 'smartrc_mfcode_map.json')

    with open(fmap_path, 'w', encoding='utf-8') as f:
        json.dump(fcode_map, f, ensure_ascii=False)
    with open(mfmap_path, 'w', encoding='utf-8') as f:
        json.dump(mfcode_map, f, ensure_ascii=False)

    print(f"\nSaved:", file=sys.stderr)
    print(f"  {fmap_path}", file=sys.stderr)
    print(f"  {mfmap_path}", file=sys.stderr)

    # Coverage test
    resolved_f = 0
    resolved_mf = 0
    for rcode, runners in smartrc_data.items():
        for r in runners:
            fc = str(r.get('f_code', '')).strip()
            mfc = str(r.get('mf_code', '')).strip()
            if fc in fcode_map:
                resolved_f += 1
            if mfc in mfcode_map:
                resolved_mf += 1

    print(f"\nCoverage:", file=sys.stderr)
    print(f"  Father: {resolved_f}/{total} ({resolved_f/total*100:.0f}%)", file=sys.stderr)
    print(f"  BMS:    {resolved_mf}/{total} ({resolved_mf/total*100:.0f}%)", file=sys.stderr)


if __name__ == '__main__':
    main()
