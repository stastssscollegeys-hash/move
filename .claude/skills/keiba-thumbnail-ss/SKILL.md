---
name: keiba-thumbnail-ss
description: 競馬予想noteサムネイル画像を自動生成するスキル。レーステーマを自動リサーチしてnanobanana-proで3バリエーション一括生成。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Task
---

# 競馬予想 noteサムネイル生成スキル

「サムネイル画像を作成して」「オークスのサムネイル作って」という指示で自動的に以下を実行する。

---

## When to Use

- 「[レース名]のサムネイル作って」
- 「noteのヘッダー画像を作って」
- 「競馬予想の画像を作って」

---

## 実行フロー（完全自動）

### Phase 1: レーステーマ自動リサーチ

まず対象レースのテーマ・カラー・モチーフをリサーチする。
メモリ `keiba_race_themes.md` に既知のテーマがある場合はそれを使用。
ない場合はWebで「[レース名] テーマ 色 花 イメージ」を調べてから生成。

**確定済みテーマ（メモリから）:**

| レース | テーマカラー | 主要モチーフ |
|--------|-------------|-------------|
| オークス（優駿牝馬）G1 5月東京 | 深紅`#8B0000` × 新緑`#52B788` × ゴールド`#D4AF37` | 深紅バラ（ローズガーデン）・ケヤキ並木・「樫の女王」 |
| ヴィクトリアマイル G1 5月東京 | 紫・ラベンダー | 藤の花・ライラック |
| 桜花賞 G1 4月阪神 | 桜ピンク | 桜・春・スピード |

### Phase 2: 参照画像の確定

1. **スタイル参照**: 直近の成功サムネイル（先週分）を使用
   - 場所: `C:\Users\User\Desktop\競馬予想レポート\[直近YYYYMMDD]\note_header_*_v2.png`
   - なければ同フォルダ内の最新 `.png`
2. **キャラクターシート（必須）**: `C:/Users/User/Downloads/アスメシキャラクターシート文字なし.png`
   - アスメシくん: ピンク帽子・青と黄色の騎手ユニフォームの可愛い馬キャラ

### Phase 3: 3バリエーション一括連続生成

**確認なしで全バリエーションを順次実行**（ユーザーへの確認不要）。

```powershell
$env:PYTHONUNBUFFERED = "1"
Set-Location "C:\Users\User\dev\move\.claude\skills\nanobanana-pro"
$style = "[直近スタイル参照画像パス]"
$char  = "C:/Users/User/Downloads/アスメシキャラクターシート文字なし.png"
$out   = "C:/Users/User/Desktop/競馬予想レポート/[YYYYMMDD]"

# v1
python scripts/run.py image_generator.py `
  --prompt "[v1プロンプト]" `
  --output "$out/note_header_[slug]2026.png" `
  --attach-image $style --attach-image $char `
  --show-browser --skip-thinking-mode --timeout 600 2>&1

# v2
python scripts/run.py image_generator.py `
  --prompt "[v2プロンプト]" `
  --output "$out/note_header_[slug]2026_v2.png" `
  --attach-image $style --attach-image $char `
  --show-browser --skip-thinking-mode --timeout 600 2>&1

# v3
python scripts/run.py image_generator.py `
  --prompt "[v3プロンプト]" `
  --output "$out/note_header_[slug]2026_v3.png" `
  --attach-image $style --attach-image $char `
  --show-browser --skip-thinking-mode --timeout 600 2>&1
```

**必須フラグ:**
- `--skip-thinking-mode` — 思考モードは画像生成をブロックするため必須
- `--show-browser` — セッション切れ時にログイン可能にするため
- `--timeout 600` — 生成に3〜5分かかるため（600秒）
- `--attach-image` 順序: **スタイル参照を1枚目、キャラシートを2枚目**（順番厳守）

---

## プロンプトテンプレート（3バリエーション）

3つは構図のみ異なる。テーマカラー・テキスト・アスメシくん配置は共通。

```
添付1枚目と全く同じアニメ調・フォント・装飾スタイルで[レース名]([グレード])のnoteサムネイル（横長16:9）。
[レーステーマカラー]（例: オークスのテーマカラーは深紅×新緑×ゴールド）。
構図のみ変えて：[構図描写]。
テキスト：左上白・金縁「[レース名]([グレード])」「2026 AI予想」・中段左「アスメシ競馬予想」・
下部黒バー「【AI全頭診断】[競馬場] [コース] [キャッチコピー]」。
左下に添付2枚目のアスメシくん（ピンク帽子・青と黄色の騎手ユニフォームの可愛い馬キャラ）を[表情]で配置。
```

### 構図バリエーション案（レースごとに調整）

| バリエ | 構図アイデア |
|--------|------------|
| v1 | 最終直線で疾走する馬の正面アングル・迫力 |
| v2 | 最終コーナーを回る馬の斜め後方アングル・スタンド背景 |
| v3 | テーマモチーフ（バラ・桜等）が舞う中のウイニングラン |

### アスメシくんの表情指定

| 場面 | 表情 |
|------|------|
| 迫力の疾走シーン | ドキドキした表情 |
| 優雅な場面 | 目をキラキラさせた表情 |
| 真剣な分析場面 | 真剣な顔 |

---

## レース別テーマ詳細

### オークス（優駿牝馬）G1
- **日程**: 5月第4日曜・東京競馬場・芝2400m・3歳牝馬
- **テーマカラー**: 深紅(`#8B0000`) × 新緑(`#52B788`) × ゴールド(`#D4AF37`)
- **主要モチーフ**: 深紅バラ（東京競馬場ローズガーデン・5月満開）・ケヤキ並木（新緑）・「樫の女王」
- **キャッチ**: 「樫の女王決定戦」「キミには冠がよく似合う」
- **プロンプト骨格**: 深紅バラが咲き誇るローズガーデン・ケヤキ並木の新緑トンネル・ゴールドのティアラ

### ヴィクトリアマイル G1
- **テーマカラー**: 紫・ラベンダー
- **主要モチーフ**: 藤の花・ライラック・初夏の東京

---

## スクロール動作（自動）

`image_generator.py` に組み込み済み:
- **送信直後**: 最下部へスクロール
- **30秒ごと**: 300px上スクロール → 400ms待機 → 最下部へ戻す（上下往復でレンダリング促進）

---

## 参照画像のアップロード（自動）

`image_generator.py` が自動処理:
- 画像を作成モード切替**前**にアップロード（モード切替後はファイルアップロード不可のため）
- `ファイルをアップロード` メニューから2枚同時添付
- 失敗時はDataTransfer APIでドラッグ&ドロップをJS実行

---

## 出力ファイル命名規則

```
note_header_[slug][YYYY].png      ← v1
note_header_[slug][YYYY]_v2.png   ← v2
note_header_[slug][YYYY]_v3.png   ← v3

スラグ例:
oaks2026         ← オークス
victoria2026     ← ヴィクトリアマイル
satsuki2026      ← 皐月賞
derby2026        ← 日本ダービー
tennosho2026     ← 天皇賞
```

保存先: `C:\Users\User\Desktop\競馬予想レポート\[開催日YYYYMMDD]\`

---

## トラブルシューティング

### Chromeロックエラー
```powershell
Get-Process -Name "chrome","chromium" -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item "C:\Users\User\dev\move\.claude\skills\nanobanana-pro\data\browser_profile2\lockfile" -Force -ErrorAction SilentlyContinue
```

### タイムアウト（600s）
- Geminiのレート制限の可能性 → Chrome終了・lockfile削除後に再試行
- プロンプトが長すぎる場合は短縮（300文字目安）

### セッション切れ
- `--show-browser` でブラウザを開いてGoogleアカウントにログイン

---

## 関連メモリ
- `keiba_race_themes.md` — レース別テーマカラー・モチーフ詳細
- `keiba_thumbnail_nanobanana_workflow.md` — 旧ワークフロー（参照用）
- `feedback_asmeshi_reference_image.md` — キャラシート必須ルール
- `feedback_nanobanana_sequential.md` — 連続実行ルール
