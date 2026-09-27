#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アスメシ式 独自指数 v3.0 — CLI エントリポイント

使い方:
    python run_index.py                              # 最新週末のデータを使用
    python run_index.py --weekend 20260418-19        # 週末を指定
    python run_index.py --output C:/path/to/out.xlsx # 出力先を指定
"""
import sys
import argparse
from pathlib import Path
import yaml

# パス設定
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "races"
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\User\Desktop\競馬予想レポート")

sys.path.insert(0, str(ROOT))
from keiba_index.excel_builder import build


def load_program(weekend_dir: Path) -> tuple[dict, str, str, str]:
    """program.yaml を読み込み、race_program dict を返す"""
    prog_file = weekend_dir / "program.yaml"
    if not prog_file.exists():
        raise FileNotFoundError(f"program.yaml が見つかりません: {prog_file}")

    with open(prog_file, encoding="utf-8") as f:
        prog = yaml.safe_load(f)

    date_sat = prog["weekend"]["date_sat"]
    date_sun = prog["weekend"]["date_sun"]
    output_filename = prog["weekend"]["output_filename"]

    race_program = {}
    for venue_block in prog["venues"]:
        venue = venue_block["venue"]
        day   = venue_block["day"]
        races = []
        for r in venue_block["races"]:
            race = {
                "num":        r["num"],
                "name":       r["name"],
                "grade":      r["grade"],
                "surface":    r["surface"],
                "distance":   r["distance"],
                "conditions": r["conditions"],
                "horses":     [],
            }
            # 馬データファイルが指定されている場合は読み込む
            horses_file = r.get("horses_file")
            if horses_file:
                hf = weekend_dir / horses_file
                if hf.exists():
                    with open(hf, encoding="utf-8") as hfp:
                        hdata = yaml.safe_load(hfp)
                    race["horses"] = hdata.get("horses", [])
                else:
                    print(f"  [WARN] 馬データファイルが見つかりません: {hf}")
            races.append(race)
        race_program[(venue, day)] = races

    return race_program, date_sat, date_sun, output_filename


def find_latest_weekend(data_dir: Path) -> Path:
    """data/races/ 配下の最新ディレクトリを返す"""
    dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()], reverse=True)
    if not dirs:
        raise FileNotFoundError(f"data/races/ 配下にデータが見つかりません: {data_dir}")
    return dirs[0]


def main():
    parser = argparse.ArgumentParser(
        description="アスメシ式 独自指数 v3.0 — Excel指数表生成ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python run_index.py                          最新データで生成
  python run_index.py --weekend 20260418-19    週末を指定して生成
  python run_index.py --output output.xlsx     出力先を指定
  python run_index.py --list                   利用可能な週末データを一覧表示
"""
    )
    parser.add_argument("--weekend", "-w", help="週末ID (例: 20260418-19)")
    parser.add_argument("--output", "-o", help="出力Excelパス")
    parser.add_argument("--list", "-l", action="store_true", help="利用可能なデータを一覧表示")
    args = parser.parse_args()

    # 一覧表示
    if args.list:
        print("利用可能な週末データ:")
        for d in sorted(DATA_DIR.iterdir()):
            if d.is_dir():
                prog = d / "program.yaml"
                if prog.exists():
                    with open(prog, encoding="utf-8") as f:
                        p = yaml.safe_load(f)
                    ds = p["weekend"]
                    print(f"  {d.name}  {ds['date_sat']}・{ds['date_sun']}")
        return

    # 週末ディレクトリ特定
    if args.weekend:
        weekend_dir = DATA_DIR / args.weekend
        if not weekend_dir.exists():
            print(f"[ERROR] 指定された週末データが見つかりません: {weekend_dir}")
            sys.exit(1)
    else:
        weekend_dir = find_latest_weekend(DATA_DIR)
        print(f"最新週末データを使用: {weekend_dir.name}")

    # データ読み込み
    race_program, date_sat, date_sun, out_fname = load_program(weekend_dir)

    # 出力パス決定
    if args.output:
        output_path = str(Path(args.output))
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(DEFAULT_OUTPUT_DIR / out_fname)

    # Excel生成
    print(f"生成中: {output_path}")
    total_races = sum(len(v) for v in race_program.values())
    scored_races = sum(1 for races in race_program.values()
                       for r in races if r["horses"])
    print(f"  レース数: {total_races} (完全スコア済み: {scored_races})")

    wb = build(race_program, output_path, date_sat, date_sun)

    print(f"\n[OK] 生成完了: {output_path}")
    print(f"  シート: {wb.sheetnames}")


if __name__ == "__main__":
    main()
