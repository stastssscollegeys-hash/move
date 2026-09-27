"""
keiba-predictor 配布パッケージ作成スクリプト
実行: python create_package.py
出力: Desktop/keiba-predictor-v3.2_YYYYMMDD/ (フォルダ)
"""
import shutil
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent.parent.parent  # dev/move/
TODAY = date.today().strftime("%Y%m%d")
PKG_NAME = f"keiba-predictor-v3.2_{TODAY}"
DESKTOP = Path.home() / "Desktop"
OUT_DIR = DESKTOP / PKG_NAME

# パッケージに含めるエントリ: (実際のパス, ZIP内アーカイブパス)
INCLUDE_ENTRIES = [
    (BASE / "CLAUDE.md",                          "CLAUDE.md"),
    (BASE / "README.md",                          "README.md"),
    (BASE / "setup.bat",                          "setup.bat"),
    (BASE / "setup.sh",                           "setup.sh"),
    (BASE / ".env.example",                       ".env.example"),
    (BASE / "dot_claude" / "settings.json",       ".claude/settings.json"),
    (BASE / "dot_claude" / "skills",              ".claude/skills"),
    (BASE / "src" / "keiba-predictor",            "src/keiba-predictor"),
    (PROJECT_ROOT / "src" / "keiba-index",        "src/keiba-index"),
    (BASE / "docs",                               "docs"),
]

# 除外パターン（部分一致）
EXCLUDE_DIRS  = {"__pycache__", "_cache", ".git", "node_modules", "browser_profile", "races"}
EXCLUDE_FILES = {".env", "netkeiba_cache.json", ".DS_Store"}
EXCLUDE_EXT   = {".pyc", ".pyo", ".log", ".tmp", ".docx"}


def should_exclude(path: Path) -> bool:
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix in EXCLUDE_EXT:
        return True
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def collect_files(src: Path):
    """srcディレクトリ以下の含めるべきファイルを列挙"""
    if src.is_file():
        yield src
        return
    for p in sorted(src.rglob("*")):
        if p.is_file() and not should_exclude(p):
            yield p


def main():
    print(f"=== keiba-predictor パッケージ作成 ===")
    print(f"出力先: {OUT_DIR}")
    print()

    # 既存フォルダがあれば削除して再作成
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    added = 0
    for src, arc_rel in INCLUDE_ENTRIES:
        if not src.exists():
            print(f"  [SKIP] 存在しない: {src}")
            continue

        for fpath in collect_files(src):
            if src.is_file():
                dest = OUT_DIR / arc_rel
            else:
                dest = OUT_DIR / arc_rel / fpath.relative_to(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fpath, dest)
            added += 1
            print(f"  + {dest.relative_to(DESKTOP)}")

    print()
    print(f"=== 完了 ===")
    print(f"  ファイル数: {added}")
    print(f"  保存先: {OUT_DIR}")


if __name__ == "__main__":
    main()
