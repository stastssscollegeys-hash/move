---
name: gdrive-download-ss
description: Google Driveの動画・ファイルをダウンロードするスキル。アクセス制限付きファイルにも対応。yt-dlpをメインツールとして使用し、gdownでは権限エラーになるファイルもダウンロード可能。
argument-hint: "[GoogleDriveのURL] [--output=出力先フォルダ]"
allowed-tools: Bash, Read, Write, Glob
model: haiku
---

# gdrive-download-ss - Google Drive動画ダウンロードスキル

## 概要

Google Driveの動画・ファイルをダウンロードする。
`gdown`が権限エラーで失敗するケースでも、`yt-dlp`で突破できる。

## 重要な知見

```
┌─────────────────────────────────────────────────────────────────────┐
│  gdown → 「オーナーと編集者のみ」制限で失敗することがある          │
│  yt-dlp → 同じファイルでもダウンロードできる（別のアクセス方法）    │
│  優先順位: yt-dlp > gdown > curl                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## ダウンロード手順

### Step 1: 出力フォルダの準備

```bash
mkdir -p "{出力先パス}"
```

### Step 2: yt-dlpでダウンロード（推奨・第一選択）

```bash
yt-dlp -o "{出力先パス}/%(title)s.%(ext)s" "{Google DriveのURL}"
```

**対応URLフォーマット:**
- `https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing`
- `https://drive.google.com/file/d/{FILE_ID}/view`
- `https://drive.google.com/open?id={FILE_ID}`

**注意:** WARNING が出ても実際にはダウンロードが進行・完了する場合がある。
`WARNING: [GoogleDrive] Only the owner and editors can download this file` が出ても、
ダウンロードが開始されていれば成功する。

### Step 3: yt-dlpが失敗した場合のフォールバック

#### フォールバック1: gdown

```bash
gdown --fuzzy "{Google DriveのURL}" -O "{出力先パス}/"
```

#### フォールバック2: curl（ファイルIDを抽出して直接アクセス）

```bash
# URLからFILE_IDを抽出
# https://drive.google.com/file/d/{FILE_ID}/view → FILE_IDを取得

curl -L -o "{出力先パス}/output.mp4" "https://drive.google.com/uc?export=download&id={FILE_ID}&confirm=t"
```

### Step 4: ダウンロード確認

```bash
ls -la "{出力先パス}/"
```

## デフォルト出力先

指定がない場合: `C:/Users/baseb/dev/開発1/output/動画ダウンロード/`

## 前提条件

- `yt-dlp` がインストール済み（`pip install yt-dlp`）
- `gdown` がインストール済み（`pip install gdown`）※フォールバック用

## トラブルシューティング

| 症状 | 対処法 |
|------|--------|
| gdownで権限エラー | yt-dlpを使う |
| yt-dlpでも完全に失敗 | ファイルオーナーに共有設定変更を依頼 |
| ダウンロードが途中で止まる | `--retries 10` オプション追加 |
| ファイル名が文字化けする | `-o` で明示的にファイル名を指定 |
| 大容量ファイル（1GB+） | タイムアウトを延長（timeout: 600000） |
