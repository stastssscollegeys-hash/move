# SESSION HANDOFF DOCUMENT

> **CRITICAL**: 次のセッションは必ずこのファイルを読んでから作業を開始すること

**最終更新**: 2026-02-21
**作業ディレクトリ**: C:\Users\baseb\dev\開発1

---

## YouTube動画リサーチツール 開発状況

### 動作するもの（すべて修正済み・稼働中）
- YouTube検索 + バズ比率算出（Claude不要・高速）
- トレンド判定（Claude使用）
- ターゲット＆キーワード分析（Claude使用）- **修正済み**
- 国/地域フィルタ（JP, US, KR等）
- snippet.tags取得 + プロンプト改善（「不明」問題解消済み）
- APIキー管理（localStorage保存）
- UIの使い方ガイド + サムネイル表示
- Renderデプロイ: https://kaihatu1.onrender.com/youtube-research

### 解決済みの課題（記録）
- ~~キーワード分析が「不明」になる~~ → `snippet.tags`活用 + プロンプト改善で解決（commit `68f09ef`）
- ~~字幕取得~~ → YouTube APIの制限で不可能と判明。字幕なしで分析できるようにプロンプトを改善
- 不要パッケージ（youtube-transcript, youtube-caption-extractor）は削除済み

### 3つのバージョン

| バージョン | 状態 | 場所 |
|-----------|------|------|
| **Web版**（事業者向け） | 稼働中 | Render: https://kaihatu1.onrender.com/youtube-research |
| **MCP版**（身内向け） | 稼働中 | `dev/youtube-research-mcp/` (GitHub Private) |
| **会員制版**（一般向け） | 未着手 | 設計ドキュメントのみ |

### 詳細設計ドキュメント
**→ `docs/youtube-research-design.md` を必ず読むこと**
インフラ選定、認証、課金、アーキテクチャ等の設計情報が記載されている。

## ファイル構成

```
src/youtube-research/
  ├── types.ts        # 型定義（tags, regionCode対応済み）
  ├── prompts.ts      # Claudeプロンプト（改善済み）
  ├── service.ts      # メインロジック（検索/バズ/トレンド/ターゲット/KW）
  ├── controller.ts   # リクエスト処理
  └── routes.ts       # ルーター

public/
  ├── youtube-research.html
  ├── youtube-research-api-guide.html
  ├── css/youtube-research.css
  └── js/youtube-research.js

docs/
  ├── youtube-research-design.md    # 設計ドキュメント（原本）
  └── youtube-research-setup-guide.md
```

## 重要な方針（CLAUDE.mdにも記載）

- **事業者販売版（現行）のソースコード上書き禁止**
- 会員制版は別ディレクトリ `dev/youtube-research-members/` で新規作成
- 管理用MCPも別ディレクトリ `dev/youtube-research-admin-mcp/` で新規作成
- MCP版はnpm公開しない、GitHub Private + コラボレーター招待

## 会員制版の技術スタック（決定済み 2026-02-21）

| 役割 | ツール |
|------|--------|
| 画面+API | Next.js |
| 認証 | Clerk |
| DB | Supabase |
| 課金 | ツール外（銀行振込等） |
| 会員管理 | 自作MCP（AI管理） |
| デプロイ | Vercel |

**詳細は `docs/youtube-research-design.md` を参照。**

## MCP版の設定

```json
// 開発1/.mcp.json の youtube-research エントリ
{
  "type": "stdio",
  "command": "node",
  "args": ["C:/Users/baseb/dev/youtube-research-mcp/dist/server.js"],
  "env": {
    "YOUTUBE_API_KEY": "${YOUTUBE_API_KEY}",
    "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
  }
}
```

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
2. **`docs/youtube-research-design.md` を読む** - 設計情報の原本
3. **既存スクリプトを確認** - 新規作成前にReadツールで読む
4. **ユーザー指示を優先** - 推測で作業しない
5. **スキル指定を遵守** - 「〇〇スキルを使って」は必ずSkillツールで
6. **設計変更はファイルに書く** - セッション内の会話だけで終わらせない

### MUST NOT DO（禁止）

1. **既存ファイルを無視して新規作成** - 絶対禁止
2. **「シンプルにする」と称して異なる実装** - 絶対禁止
3. **指定比率を無視した要約** - 絶対禁止
4. **スキル指示を無視した手動実装** - 絶対禁止
5. **設計情報をファイルに残さずにセッション終了** - 絶対禁止

---

*このファイルはセッション終了時に更新されます*
