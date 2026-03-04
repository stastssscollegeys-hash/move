# SESSION HANDOFF DOCUMENT

> **CRITICAL**: 次のセッションは必ずこのファイルを読んでから作業を開始すること

**最終更新**: 2026-02-24
**作業ディレクトリ**: /Users/shimizusubaru/claude code/kaihatu1（Mac mini）

---

## OpenClaw セキュリティ強化（2026-02-24）

### 完了

1. **openclaw.json セキュリティ設定**（`~/.openclaw/openclaw.json` — PC固有）
   - `groupPolicy: "allowlist"` + guilds/channels で指定チャンネルのみ応答
   - 許可チャンネル: `1475380502251700317`（サーバー: `1475380501773684737`）
   - `allowBots: false` / `workspaceOnly: true` / `tools.deny`
   - `denyCommands` に `location.get`, `sms.send`, `canvas.eval`, `system.run` 追加

2. **.gitignore 保護設定** — `openclaw-workspace/memory/`, `.env`, `.pi/` を除外

3. **Discord動作確認済み**
   - `@SubaClaw` でコーディング指示 → openclaw-workspace内にファイル作成OK
   - workspace外（src/等）へのアクセスはブロック確認済み

### 不採用

- `claude-code-skill`（openclaw-claude-code-skill）— バックエンドAPIサーバーが無く動作しない。OpenClaw自体がClaude Codeで動いているため不要。削除済み。

### 万が一の復旧

```bash
cd ~/claude\ code/kaihatu1
git checkout -- openclaw-workspace/
```

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

## 今回のセッションでの修正（2026-02-24）

### YouTubeリサーチツール（Web版）ジャンル・国フィルタ修正

#### 完了した修正

1. **ジャンルポストフィルタ追加** (`src/youtube-research/service.ts`)
   - バックエンドに17ジャンルのキーワードマップ（`GENRE_KEYWORDS`）を追加
   - `scoreGenreRelevance()` 関数: タイトル(重み50%) + タグ(30%) + 説明文(20%) でスコアリング
   - `searchWithBuzz()` でYouTube APIの結果をジャンルスコアでフィルタ＆ソート
   - スコア0（キーワード一致ゼロ）の動画を除外

2. **国フィルタ強化** (`src/youtube-research/service.ts`)
   - Before: タイトルに日本語がなければ全件返すフォールバック
   - After: 3段階フィルタ（タイトル/説明文の文字種 → YouTube APIの言語メタデータ → 全件フォールバック）

3. **投稿期間フィルタ補完** (`src/youtube-research/service.ts` + `types.ts`)
   - `2weeks`(14日) と `6months`(180日) をバックエンド側でも直接サポート

4. **Anthropic APIキーバリデーション修正** (`src/youtube-research/controller.ts`)
   - `^sk-ant-` → `^sk-` に変更。新フォーマットのキーも受け付ける

5. **エラーメッセージ改善** (`src/youtube-research/controller.ts`)
   - 「サーバー内部エラー」→ 具体的な原因（APIキー無効、レート制限、モデルエラー等）を表示

6. **エラートースト表示時間延長** (`public/js/youtube-research.js`)
   - エラー通知: 4秒 → 10秒に延長 + クリックで閉じる機能追加

#### 未解決の問題

- **ユーザーが「サーバー内部エラーが発生しました」と報告** → エラーメッセージ改善＋トースト延長をデプロイ済み
- 次回セッションでユーザーに再度試してもらい、表示されるエラーメッセージの内容を確認する
- どの操作（検索/トレンド判定/ターゲット分析）でエラーが出たかを特定する

#### コミット履歴

- `93bac95` - YouTubeリサーチツール: ジャンル・国フィルタ強化
- `109b511` - Anthropic APIキーバリデーションを新フォーマット対応に修正
- `3bfd878` - エラーメッセージ改善: 具体的なエラー原因をユーザーに表示
- `1cab729` - エラートースト表示時間を10秒に延長+クリックで閉じる機能追加

---

## 別件: 電子書籍+漫画3段階自動生成ツール

要件定義書を `docs/ebook-manga-tool-requirements.md` に作成済み。実装はまだ未着手。

---

## 【進行中】Claude Code入門書 電子書籍プロジェクト（2026-03-01）

### 概要
**ebook-creator-ss スキル** を使って、Claude Code入門書の電子書籍を作成中。

- **テーマ**: Claude Code 超入門（非エンジニア向け）
- **書籍タイトル案**: 「AIがあなたの右腕になる！ Claude Code超入門 -- 非エンジニアのためのAIエージェント活用術」
- **出力先**: `output/ebook-claude-code/`
- **使用スキル**: ebook-creator-ss（6フェーズ制）

### ターゲット読者（清水さん指定）
**非エンジニアのマーケター・コンテンツクリエイター・個人事業主・中小企業**
- マーケティング・コンテンツ制作でAIを活用したい
- プログラミング経験なし
- 「非エンジニアのマーケティング・コンテンツ制作する企業・個人の目に留まる本にしたい」（清水さんの言葉）

### 進捗状況
- Phase 1（参考資料受け取り）: ✅ 完了
- Phase 2（リサーチ）: ✅ 完了 → `output/ebook-claude-code/research.md` に保存済み
- Phase 3（構成設計）: ✅ 完了・ユーザー承認済み
- **Phase 4（原稿執筆）: ⬜ 次にやること**
- Phase 5（画像一括生成）: ⬜ 未着手
- Phase 5.5（表紙作成）: ⬜ 未着手
- Phase 6（DOCX変換）: ⬜ 未着手

### 参考資料（Phase 1で受領）
原文テキストはコンテキスト圧縮で消失。要点はresearch.mdに反映済み。
1. **セットアップマニュアル**: `c:\Users\baseb\OneDrive\デスクトップ\Claudecodeメモ\Claude code完全セットアップマニュアル_v3.docx`
2. **ミーティング文字起こし** (~1時間28分): Claude Code/エージェント/スキル/OpenCrawl/MCP/N8N
3. **YouTube動画文字起こし** (~12分35秒): AI進化論（プロンプト→ツール→エージェント→スキル）

### 承認済み目次構成（Phase 3）

```
【はじめに】この本を手に取ったあなたへ（800〜1,000字）
- AIの進化の大きな流れ（プロンプト→ツール→エージェント→スキル）
- なぜ「今」Claude Codeなのか
- この本で得られること

【第1章】AIエージェント時代がやってきた（2,500〜3,000字）
- ChatGPTの次に来たもの
- 「お願いするだけ」で仕事が終わる世界
- プロンプト→ツール→エージェント→スキルの進化
- Claude Codeは「AIの秘書」

【第2章】ゼロから始めるClaude Code環境構築（2,500〜3,000字）
- Cursorをインストールしよう
- Node.jsとGitを入れよう（Cursorに手伝ってもらう）
- Claude Codeを起動する
- 最初の「こんにちは」を試す

【第3章】AIへの指示の出し方 -- 非エンジニアの武器（2,500〜3,000字）
- 「何をしたいか」を伝えるだけでいい
- 良い指示 vs 悪い指示（実例比較）
- CLAUDE.md -- AIに自分のことを覚えてもらう方法
- 失敗パターンと回避策

【第4章】実践！コンテンツ制作をAIで加速する（2,500〜3,000字）
- 電子書籍を一冊まるごと作る
- note記事を図解入りで量産する
- メルマガ・セールスレターを書く
- LP（ランディングページ）を分析・改善する

【第5章】もっと使いこなす -- スキル・MCP・自動化（2,500〜3,000字）
- スキル = AIに覚えさせた「必殺技」
- MCP = AIと外部ツールをつなぐ橋
- N8Nで業務フローを自動化する
- 2026年の最新機能とこれからのAI

【おわりに】AIと一緒に働く時代へ（800〜1,000字）
```

### ビジュアルトーン設定
- メインカラー: #6C5CE7（Claude紫）
- サブカラー: #00B894（テクノロジーグリーン）
- アクセントカラー: #FF6B6B（アクション赤）
- イラストスタイル: flat design
- 雰囲気: professional yet approachable

### Phase 4の実行手順
1. ebook-creator-ss スキルを呼び出す
2. research.md と上記目次をもとに15,000字の原稿を執筆
3. 画像タグ（HEADER_IMAGE / INLINE_IMAGE）を埋め込む
4. `output/ebook-claude-code/manuscript_raw.md` に保存
5. 執筆ルール: です・ます調、テーブル禁止、コードブロック禁止、\newpage挿入

---

## 【進行中】はやかわさやか LPツール開発 — LP Creator セミナー簡易版（Stage 1）（2026-03-04〜）

### 概要
3つの入力（商品名・ターゲット・強み）からAIがコピーを生成し、プロ品質のLP（HTML/CSS）をリアルタイムに表示するWebアプリ。
既存のYouTube Research ツール（`src/youtube-research/`）と同じ Express + 単一HTMLのパターン。

### 3段階構成
| Stage | 内容 | 状態 |
|-------|------|------|
| **Stage 1** | セミナー簡易版（3入力→LP） | **実装中** |
| Stage 2 | テンプレート複数 + カスタマイズ | 未着手 |
| Stage 3 | フル機能版（画像生成・A/Bテスト等） | 未着手 |

### Stage 1 完了タスク
- [x] types.ts — 型定義（LPGenerateRequest, LPCopyJSON 11セクション, SSEEvent）
- [x] prompts.ts — AIDA/PAS/FAB/QUEST + 5心理トリガー + JSON出力スキーマ
- [x] service.ts — Claude APIストリーミング、JSON抽出、デフォルト補完、HTML生成
- [x] controller.ts — SSEハンドラー、バリデーション、エラー分類、設定API
- [x] routes.ts — GET /, POST /api/generate, GET/POST /api/settings, GET /api/health
- [x] public/lp-creator.html — 入力フォーム + ストリーミング表示 + iframe LPプレビュー
- [x] public/lp-creator-settings.html — 管理画面（APIキー・モデル・トークン数設定）
- [x] settings-store.ts — JSON永続化（data/lp-creator-settings.json）
- [x] app.ts修正 — ルーター登録 + 専用レート制限（15分10回）+ CSP frameSrc
- [x] tsconfig.yt.json修正 — lp-creator-ssをinclude追加
- [x] .gitignore — data/ 追加

### Stage 1 未完了タスク
- [ ] 実際のAI生成テスト（APIキー設定→LP作成ボタン→ストリーミング→プレビュー確認）
- [ ] 要件定義書のC.U.T.E.スコア項目との突き合わせ確認
- [ ] Renderデプロイ
- [ ] LP HTMLのダウンロード機能
- [ ] エラーハンドリングの実機テスト

### ファイル構成

```
src/lp-creator-ss/
├── docs/
│   ├── requirements.md    # 要件定義書（C.U.T.E. 98点）
│   ├── decisions.md       # 設計判断ログ
│   ├── critique.md        # レビュー指摘
│   └── score.json         # スコア記録
├── types.ts               # 型定義
├── prompts.ts             # コピーライティングプロンプト
├── service.ts             # Claude API連携・HTML生成
├── controller.ts          # SSE・バリデーション・設定API
├── settings-store.ts      # 設定永続化（→ data/lp-creator-settings.json）
└── routes.ts              # Expressルーター

public/
├── lp-creator.html            # ユーザー向けLP作成画面
└── lp-creator-settings.html   # 管理者向け設定画面
```

### URL
- LP作成: `http://localhost:3000/lp-creator`
- 管理設定: `http://localhost:3000/lp-creator/settings`
- ヘルスチェック: `http://localhost:3000/lp-creator/api/health`

### 設定の優先順位
1. 管理画面で設定したAPIキー（`data/lp-creator-settings.json`）
2. 環境変数 `ANTHROPIC_API_KEY`（フォールバック）

### 技術方針
| 項目 | 方針 |
|------|------|
| ストリーミング | SSE via fetch + ReadableStream（POSTのためEventSource不使用） |
| LPプレビュー | iframe srcdoc（CSS完全分離） |
| XSS対策 | escapeHtml()で全挿入値エスケープ |
| APIキー | サーバーサイドのみ。ユーザーフォームには露出しない |
| JSONパース失敗時 | 最大2回リトライ |
| 欠落セクション | デフォルトテキストで補完 |

### 今回のセッションでの進捗（2026-03-04 セッション2）

1. **CSP修正**: `scriptSrc` に `'unsafe-inline'` 追加 → 管理画面のJS動作を修正
2. **APIキー設定**: 管理画面で保存できるようになった。ただしユーザーのキーはclaude.aiサブスクのもので、APIキーではなかった（401エラー）
3. **テスト生成ボタン追加**: `POST /api/generate-demo` エンドポイント + フロントに緑色の「テスト生成（API不要）」ボタン追加。デモデータでストリーミング→プレビューの全UI動作確認が可能
4. **test-runner.ts**: CLIからデモデータでHTML生成（`node dist-yt/lp-creator-ss/test-runner.js --demo`）

### テスト方針の議論（未決定）

ユーザーはAPIコストを避けたい。以下の選択肢が議論された：
- **Claude Code生成方式**: Claude Code（Opus）がコピーJSONを生成→サーバーがrenderHTML。サブスク内で完結するが、Opus品質になるため本番（Sonnet/Haiku）との品質差が懸念
- **Anthropic API無料クレジット**: console.anthropic.com で$5無料クレジット取得→Haikuで数百回テスト可能
- **結論**: 未決定。清水さんが次回判断する

### 次のセッションでやること
1. **テスト方式を決める**: Claude Code生成 or API無料クレジット or 両方
2. AI生成テスト（LP作成ボタン→ストリーミング→プレビュー確認）
3. LP生成の品質確認・プロンプト調整
4. HTMLダウンロード機能の追加
5. Renderデプロイ

---

## 未コミットの変更

1. `hokan/YouTubeサムネ/youtube_thumbnail_meta_prompt_v1.1.md` - v1.1更新
2. `.claude/skills/youtube-thumbnail-ss/SKILL.md` - v1.1更新
3. `.claude/CLAUDE.md` - メタプロンプト連動テーブル更新
4. `output/ebook-claude-code/research.md` - ebook用リサーチ結果
5. `SESSION_HANDOFF.md` - この引き継ぎ情報

---

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
