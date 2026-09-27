#!/bin/bash
# keiba-predictor-ss セットアップスクリプト
# 使い方: bash setup.sh /path/to/your-project
set -e

PROJECT_DIR="${1:-.}"

echo "=== keiba-predictor-ss セットアップ ==="
echo "プロジェクト: $PROJECT_DIR"

# 1. スキル定義をコピー
SKILL_DIR="$PROJECT_DIR/.claude/skills/keiba-predictor-ss"
mkdir -p "$SKILL_DIR"
cp SKILL.md "$SKILL_DIR/"
echo "[1/4] スキル定義 → $SKILL_DIR/"

# 2. ソースコードをコピー
SRC_DIR="$PROJECT_DIR/src/keiba-predictor"
mkdir -p "$SRC_DIR"
cp -r src/keiba-predictor/* "$SRC_DIR/"
echo "[2/4] ソースコード → $SRC_DIR/"

# 3. 依存関係インストール
echo "[3/4] pip install..."
pip install -r "$SRC_DIR/requirements.txt" -q

# 4. .gitignore追加
GITIGNORE="$PROJECT_DIR/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if ! grep -q "keiba-predictor/_cache" "$GITIGNORE" 2>/dev/null; then
        echo "" >> "$GITIGNORE"
        echo "# keiba-predictor キャッシュ" >> "$GITIGNORE"
        echo "src/keiba-predictor/_cache/" >> "$GITIGNORE"
        echo "src/keiba-predictor/netkeiba_cache.json" >> "$GITIGNORE"
        echo "[4/4] .gitignore にキャッシュ除外を追加"
    else
        echo "[4/4] .gitignore は既に設定済み"
    fi
else
    echo "[4/4] .gitignore が見つかりません（手動でキャッシュ除外を追加してください）"
fi

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "使い方:"
echo "  cd $SRC_DIR"
echo "  python predict.py --race 20260322hanshin11    # 1レース予想"
echo "  python predict.py --all 20260322hanshin       # 開催全レース"
echo "  python bulk_pdca.py --date 20260322 -v        # 過去検証"
