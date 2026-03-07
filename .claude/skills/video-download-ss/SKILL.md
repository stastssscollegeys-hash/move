---
name: video-download-ss
description: 動画ダウンロード統合スキル。Loom・Google Drive・YouTube等に対応。yt-dlpをメインツールとして使用し、プラットフォームごとの制限を突破してダウンロード可能。
argument-hint: "[動画URL] [--output=出力先フォルダ]"
allowed-tools: Bash, Read, Write, Glob
model: haiku
---

# video-download-ss - 動画ダウンロード統合スキル

## 概要

各種プラットフォームの動画をダウンロードする統合スキル。
`yt-dlp` をメインツールとし、プラットフォームごとの最適な方法でダウンロードする。

## 対応プラットフォーム

| プラットフォーム | 方法 | 備考 |
|-----------------|------|------|
| **Loom** | yt-dlp | ページにDLボタンがなくてもAPI経由で取得可能 |
| **Google Drive** | yt-dlp > gdown > curl | gdownが権限エラーでもyt-dlpで突破できる |
| **YouTube** | yt-dlp | 最高画質 or 指定画質でDL |
| **その他** | yt-dlp | yt-dlp対応サイトなら基本OK |

## デフォルト出力先

```
C:/Users/baseb/dev/開発1/output/動画ダウンロード/
```

※ 指定がなければ上記に保存する

---

## プラットフォーム別手順

### Loom

ページ上にダウンロードボタンがなくても、yt-dlpがLoomの内部APIを解析して動画URLを取得できる。

```bash
# 基本コマンド
yt-dlp -o "{出力先}/%(title)s.%(ext)s" "https://www.loom.com/share/{VIDEO_ID}"
```

**対応URLフォーマット:**
- `https://www.loom.com/share/{VIDEO_ID}`
- `https://www.loom.com/share/{VIDEO_ID}?sid=xxx`

**注意:**
- ffmpegがない場合、`WARNING: ffmpeg not found` が出るが、mp4でダウンロードは可能
- ffmpegがあればDASH形式で最高画質を結合できる
- タイムアウトは長めに設定（timeout: 600000 = 10分）

---

### Google Drive

`gdown`が「オーナーと編集者のみ」制限で失敗するケースでも、`yt-dlp`で突破できる。

```bash
# 第一選択: yt-dlp（推奨）
yt-dlp -o "{出力先}/%(title)s.%(ext)s" "{Google DriveのURL}"
```

**対応URLフォーマット:**
- `https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing`
- `https://drive.google.com/file/d/{FILE_ID}/view`
- `https://drive.google.com/open?id={FILE_ID}`

**注意:** `WARNING: [GoogleDrive] Only the owner and editors can download this file` が出ても、
ダウンロードが開始されていれば成功する場合がある。

#### フォールバック1: gdown
```bash
gdown --fuzzy "{Google DriveのURL}" -O "{出力先}/"
```

#### フォールバック2: curl（ファイルIDを抽出して直接アクセス）
```bash
curl -L -o "{出力先}/output.mp4" "https://drive.google.com/uc?export=download&id={FILE_ID}&confirm=t"
```

---

### YouTube

```bash
# 最高画質（1080p以下）
yt-dlp -f "best[height<=1080]" -o "{出力先}/%(title)s.%(ext)s" "{YouTube URL}"

# 音声のみ抽出
yt-dlp -x --audio-format mp3 -o "{出力先}/%(title)s.%(ext)s" "{YouTube URL}"
```

---

### その他のサイト

yt-dlpは1000以上のサイトに対応。まずそのまま試す。

```bash
yt-dlp -o "{出力先}/%(title)s.%(ext)s" "{URL}"
```

---

## 共通手順

### Step 1: 出力フォルダの準備

```bash
mkdir -p "{出力先パス}"
```

### Step 2: yt-dlpでダウンロード

```bash
yt-dlp -o "{出力先}/%(title)s.%(ext)s" "{URL}"
```

### Step 3: ダウンロード確認

```bash
ls -la "{出力先}/"
```

---

## 前提条件

- `yt-dlp` がインストール済み（`pip install yt-dlp`）
- `gdown` がインストール済み（`pip install gdown`）※Google Driveフォールバック用
- `ffmpeg` は推奨（なくても基本的なDLは可能）

## トラブルシューティング

| 症状 | 対処法 |
|------|--------|
| gdownで権限エラー | yt-dlpを使う（Google Drive） |
| yt-dlpでも完全に失敗 | ファイルオーナーに共有設定変更を依頼 |
| ダウンロードが途中で止まる | `--retries 10` オプション追加 |
| ファイル名が文字化けする | `-o` で明示的にファイル名を指定 |
| 大容量ファイル（1GB+） | タイムアウトを延長（timeout: 600000） |
| ffmpeg not found警告 | mp4でDLは可能。最高画質が必要なら `pip install ffmpeg-python` |
| Loomでフォーマット選択できない | ffmpegなしだと`http-transcoded`形式のみ |
