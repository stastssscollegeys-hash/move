# keiba-predictor v3.2

JRA中央競馬 AI予想ツール

過去15年分のJRAデータ × LightGBM v44 × 17因子モデルによるクオンツ予想システム。

## 実績（PDCA37 / 2026年1〜4月）

| 指標 | 数値 |
|------|------|
| 複勝的中率 | **69.7%**（894R検証） |
| 堅いレース (荒れ度0-2) | **83.3%** |
| 中間荒れ度 (3-5) | **72.3%** |
| 荒れレース (6+) | **61.7%** |
| 最強競馬場 | 阪神 **76.3%** |
| バックテストROI | **273.3%** (LightGBM v44) |

## 必要環境

- Python **3.10以上**
- Windows 10/11 または Mac/Linux
- smartrc.jp の**無料アカウント**（オッズ取得に使用）
- X(Twitter)/note への自動投稿機能を使う場合のみAPIキーが必要

## セットアップ

### Windows（推奨）

```
1. ZIPを展開
2. setup.bat をダブルクリック
3. .env をテキストエディタで開いてAPIキーを設定（投稿機能を使う場合のみ）
```

### Mac / Linux

```bash
cd keiba-predictor-v3.2
bash setup.sh .
cp .env.example .env
# .env を編集してAPIキーを設定（投稿機能を使う場合のみ）
```

## APIキー設定（.env）

投稿機能を使わない場合は設定不要です。

```
X_API_KEY          : X Developer Portal で取得
X_API_SECRET       : 同上
X_ACCESS_TOKEN     : 同上
X_ACCESS_TOKEN_SECRET : 同上
NOTE_EMAIL         : note.com のログインメール
NOTE_PASSWORD      : note.com のパスワード
```

## 使い方

```bash
cd src/keiba-predictor/scripts

# 翌日の重賞予想（ワンコマンド）
python predict_and_report.py --tomorrow

# 当日レースをオッズ込みで予想
python predict_and_report.py --today

# レース指定（例: NHKマイルC）
python predict_and_report.py --date 20260510 --venue tokyo --race NHKマイルC

# 画像+Word+SNS投稿文まで一括生成
python predict_and_report.py --date 20260510 --venue tokyo --race NHKマイルC --with-image

# X・note に自動投稿（APIキー設定済みの場合）
python predict_and_report.py --date 20260510 --venue tokyo --race NHKマイルC --with-image --post-all
```

```bash
# 指数表（Excel）の生成
cd src/keiba-index
python run_index.py                      # 最新週末
python run_index.py --weekend 20260510   # 特定週指定

# バックテスト（PDCA検証）
cd src/keiba-predictor
python bulk_pdca.py --date 20260322 -v
python bulk_pdca.py --from 20260104 --to 20260322
```

## 出力物

| ファイル | 内容 |
|---------|------|
| `report_YYYYMMDD_*.txt` | 全頭診断・予想印・買い目テキスト |
| `sns_*.md` | X/Threads/note 投稿文（3フォーマット） |
| `指数表_*.xlsx` | Excel指数表（セル色分け付き） |
| `*.docx` | Word版レポート |

## 注意事項

- netkeiba.com への大量アクセスはIP BANの恐れあり。`_cache/` を活用すること
- `_cache/` と `netkeiba_cache.json` は `.gitignore` 推奨（個人データ）
- 馬券購入は自己責任。ツールの予想は参考情報です

## ライセンス

個人利用のみ。データの二次配布は各データ提供元の利用規約に従うこと。
