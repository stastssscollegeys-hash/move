# SESSION HANDOFF DOCUMENT

> **CRITICAL**: 次のセッションは必ずこのファイルを読んでから作業を開始すること

**最終更新**: 2026-02-20
**作業ディレクトリ**: C:\Users\baseb\dev\開発1

---

## YouTube動画リサーチツール 開発状況

### 動作するもの
- YouTube検索 + バズ比率算出（Claude不要・高速）
- トレンド判定（Claude使用）
- ターゲット＆キーワード分析（Claude使用）
- APIキー管理（localStorage保存）
- UIの使い方ガイド
- Renderデプロイ: https://kaihatu1.onrender.com/youtube-research

### 未解決の最重要課題: キーワード分析が「不明」になる

**原因**: YouTube Data APIはタイトル+説明文しか返さない。字幕データがないとClaudeが情報不足で「不明」を返す。

**試して全部失敗したもの**:
1. `youtube-transcript` (npm) → パッケージが壊れている（空配列を返す）
2. `youtube-caption-extractor` (npm) → 同様に0件
3. YouTube動画ページから`captionTracks`URLを直接抽出 → URLは取得できるがレスポンスが空（`ip=0.0.0.0`問題、サーバーサイドからの取得をYouTubeがブロック）
4. YouTube Innertube API (`get_transcript`) → 400 FAILED_PRECONDITION

**次に試すべきアプローチ（優先度順）**:
1. **YouTube Data APIのタグ情報を活用** → `snippet.tags`を現在抽出していない → `searchYouTube()`の返却データにtagsを追加
2. **VideoMeta型にtagsフィールドを追加** → `types.ts`修正
3. **Claudeのプロンプトを改善** → タイトル+説明文+タグ+チャンネル名+再生数+バズ比率で質の高い分析ができるようプロンプト書き直し（`prompts.ts`）
4. 字幕取得の不要パッケージ削除（youtube-transcript, youtube-caption-extractor）

## ファイル構成

```
src/youtube-research/
  ├── types.ts        # 型定義
  ├── prompts.ts      # Claudeプロンプト（← 改善が必要）
  ├── service.ts      # メインロジック（enrichWithTranscriptsは現在動作しない）
  ├── controller.ts   # リクエスト処理
  └── routes.ts       # ルーター

public/
  ├── youtube-research.html
  ├── css/youtube-research.css
  └── js/youtube-research.js

src/app.ts / src/server.ts  # Express設定・起動
docs/APIキー取得ガイド.txt  # ユーザー向けガイド
```

## 重要な方針（CLAUDE.mdに記載済み）

- **事業者販売版（現行）を上書きしない**
- ユーザーが自分のAPIキーを設定して使うモデル
- 将来の会員制版は別ディレクトリ/ブランチで作成

## サーバー起動

```bash
cd ~/dev/開発1
nohup npx tsx src/server.ts > /tmp/yt-research-server.log 2>&1 &
# → http://localhost:3000/youtube-research
```

---

## 既存スクリプト（MUST READ）

```
┌─────────────────────────────────────────────────────────┐
│  「同じワークフロー」指示がある場合、以下を必ず使用    │
└─────────────────────────────────────────────────────────┘
```

- `agent_os/runner.py` (7.0KB, 2026/1/10 12:53:40)
- `dist/scripts/run-benchmarks.js` (9.5KB, 2026/1/18 12:13:30)
- `scripts/ollama-process-transcript.sh` (6.2KB, 2026/1/10 12:38:55)
- `tests/test_runner_retry_stop.py` (1.9KB, 2026/1/10 13:01:05)

## ワークフロー定義

- `config/workflows/content_creation_v1.json`
- `config/workflows/priority_based_v1.json`
- `config/workflows/software_development_v1.json`
- `config/workflows/video_generation_v1.json`
- `config/workflows/wf_coding_change_v1.json`

## 次のセッションへの指示

### MUST DO（必須）

1. **このファイルを読む** - 作業開始前に必ず
2. **既存スクリプトを確認** - 新規作成前にReadツールで読む
3. **ユーザー指示を優先** - 推測で作業しない
4. **スキル指定を遵守** - 「〇〇スキルを使って」は必ずSkillツールで

### MUST NOT DO（禁止）

1. **既存ファイルを無視して新規作成** - 絶対禁止
2. **「シンプルにする」と称して異なる実装** - 絶対禁止
3. **指定比率を無視した要約** - 絶対禁止
4. **スキル指示を無視した手動実装** - 絶対禁止

---

*このファイルはセッション終了時に更新されます*
