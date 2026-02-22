# YouTube動画リサーチツール - 設計ドキュメント

> **このファイルはプロジェクトの設計原本です。変更があれば必ず更新すること。**
> 最終更新: 2026-02-21

---

## 1. プロジェクト概要

YouTube動画を検索し、バズ比率・トレンド判定・ターゲット分析・キーワード抽出を行うリサーチツール。
「YouTubeリサーチ → 売れるコンテンツ（本・記事・動画）の企画」を支援する。

### コア機能

| 機能 | Claude必要 | 説明 |
|------|-----------|------|
| YouTube検索 + バズ比率 | 不要 | YouTube Data API v3で検索、views/subscribersでバズ比率算出 |
| トレンド判定 | 必要 | 企画テーマの検索トレンド・競合度・タイミング判定 |
| ターゲット分析 | 必要 | 動画視聴者のデモグラフィック・興味関心・課題推定 |
| キーワード抽出 | 必要 | タイトル+概要欄+タグからSEOキーワード分析 |
| 国フィルタ | 不要 | regionCode + 言語フィルタ（日本/米国/韓国等） |

---

## 2. 3つのバージョン

```
┌────────────────────────────────────────────────────────────────┐
│  Web版          MCP版              会員制版                     │
│  （事業者向け）  （身内向け）        （一般ユーザー向け）         │
│                                                                │
│  ユーザーが      GitHub Privateで    運営がAPIを負担             │
│  APIキー自前     友人に共有          会員登録で利用可能          │
│                                                                │
│  Render          ローカル実行        Vercel（決定）              │
│  稼働中✅       稼働中✅           未着手❌                    │
└────────────────────────────────────────────────────────────────┘
```

### 2.1 Web版（事業者販売版）- 稼働中

- **対象**: 事業者・依頼者（自分でAPIキーを取得できる人）
- **URL**: https://kaihatu1.onrender.com/youtube-research
- **デプロイ先**: Render（無料枠）
- **APIキー**: ユーザーが自分で YouTube API Key + Anthropic API Key を取得
- **ソースコード**: `開発1/src/youtube-research/`, `開発1/public/youtube-research*`
- **方針**: このバージョンのソースコードは上書き禁止

### 2.2 MCP版（身内向け）- 稼働中

- **対象**: 自分 + 友人（Claude Codeユーザー）
- **GitHub**: https://github.com/subaru-blip/youtube-research-mcp (Private)
- **ソースコード**: `dev/youtube-research-mcp/`
- **実行方法**: `node dist/server.js`（stdio経由でClaude Codeと接続）
- **APIキー**: 各ユーザーが自分で設定（環境変数 YOUTUBE_API_KEY, ANTHROPIC_API_KEY）
- **配布方法**: GitHubコラボレーター招待（npmは使わない）
- **3ツール**: youtube_search, youtube_trend_check, youtube_analyze

**npm公開しない理由と、npmとMCPの違い：**

| 用語 | 意味 |
|------|------|
| **npm** | Node.jsの「アプリストア」的な配布サービス。公開すると誰でも `npx youtube-research-mcp` でインストールできる |
| **MCP** | Claude Codeと外部ツールを繋ぐ通信プロトコル。配布方法とは無関係 |

npmに公開すれば配布は楽になるが、**全世界に公開される**（Privateプランは有料）。
現時点では身内限定なのでGitHub Privateで十分。
将来もし広く配布したくなったら、npm公開に切り替えることもできる（コード変更は不要）。

### 2.3 会員制版 - 未着手

- **対象**: 一般ユーザー（APIキーの取得方法を知らない人）
- **コンセプト**: 運営（自分）がAPIキーを負担し、ユーザーは会員登録だけで使える
- **決済**: ツール外で処理（銀行振込、PayPal等）→ AI経由でプラン変更
- **会員管理**: Claude Code（AI）+ 管理用MCPで自然言語管理
- **方針**: 別ディレクトリ `dev/youtube-research-members/` で新規作成

---

## 3. 会員制版の設計（確定事項）

### 3.1 技術スタック（決定済み）

| 役割 | ツール | 料金 | 選定理由 |
|------|--------|------|----------|
| 画面+API | **Next.js** | 無料（OSS） | 画面もAPIも1つで書ける、React最大のFW |
| 認証 | **Clerk** | 無料〜（1万人まで） | ログイン機能を丸ごと提供、Next.js公式プラグイン |
| DB | **Supabase** | 無料〜（500MB） | PostgreSQL、管理画面が見やすい、無料枠が大きい |
| 課金 | **外部で処理** | - | 銀行振込やPayPal等。ツール内には組み込まない |
| 会員管理 | **自作MCP** | 無料 | Claude Codeから自然言語で管理（管理画面UI不要） |
| デプロイ | **Vercel** | 無料〜 | Next.jsとの相性最高、GitHubからの自動デプロイ |
| YouTube | **YouTube Data API v3** | 無料（1万units/日） | Google公式 |
| AI分析 | **Anthropic API** | 従量課金 | Claude使用 |

**過去に検討した選択肢と却下理由**:

| 項目 | 却下した選択肢 | 理由 |
|------|--------------|------|
| デプロイ | Cloudflare Workers | Node.js互換性に制限、Next.jsにはVercelの方が楽 |
| 認証 | Supabase Auth | UIを自前で作る必要あり |
| 認証 | Cloudflare Access | 設定が複雑、上級者向け |
| 課金 | Stripe | 少人数なら手動管理で十分、組み込みが複雑 |
| 課金 | Lemon Squeezy | 同上 |

### 3.2 アーキテクチャ（確定）

```
┌─────────────────────────────────────────────────────────┐
│                    ユーザー側                             │
│                                                         │
│  一般ユーザー → ブラウザ → 会員サイト → リサーチ実行     │
│                  （ログイン必要）                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    サーバー側                             │
│                                                         │
│  Next.js（Vercelにデプロイ）                             │
│  ├── 画面: ログイン / リサーチ / マイページ              │
│  ├── API: 認証チェック → 利用回数チェック → 検索実行     │
│  └── DB: 会員情報 / 利用履歴 / プラン状態               │
│                                                         │
│  APIキーはサーバーの環境変数に保存（ユーザーには見えない）│
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    管理者側（自分）                       │
│                                                         │
│  Claude Code → 管理用MCP → 会員の追加/停止/確認/削除     │
│               （AIに話しかけるだけで管理できる）          │
│                                                         │
│  決済は外部で行う（銀行振込、PayPal等）                  │
│  → 入金確認したらClaude Codeに「この人有料にして」と指示 │
└─────────────────────────────────────────────────────────┘
```

### 3.3 AI管理の仕組み（最大の特徴）

普通は管理画面をWebで作るが、**AIに任せる**ことで：
- 管理画面のUI開発が不要（大幅な工数削減）
- 自然言語で操作できる（「先月20回以上使った人を教えて」）
- 複雑な条件の検索もAIが理解してやってくれる

**管理用MCPが提供するツール**:

| ツール | 機能 |
|--------|------|
| member_list | 会員一覧を表示 |
| member_get | 特定の会員情報を取得 |
| member_update | プラン変更・アカウント停止/再開 |
| member_delete | 会員削除 |
| usage_stats | 利用統計（月間ランキング等） |
| usage_report | 月次レポート生成 |

**運用例**:
```
自分: 「田中さんの会員情報を確認して」
Claude Code: 「田中太郎さん（tanaka@example.com）
              登録日: 2026-03-01、プラン: 有料、今月利用回数: 12回」

自分: 「山田さん今月の決済できてないから、アカウント停止して」
Claude Code: 「山田花子さんのアカウントを停止しました。」

自分: 「先月の利用者ランキング見せて」
Claude Code: 「1位: 鈴木さん（42回）、2位: 田中さん（28回）...」
```

### 3.4 決済フロー（ツール外で処理）

ツールに決済機能は**組み込まない**。理由：
- Stripe等の組み込みは複雑で工数がかかる
- 少人数なら手動管理で十分
- AIで管理するから手間もかからない

```
1. ユーザーが「使いたい」と連絡してくる
2. 料金を案内して、銀行振込 or PayPal等で支払ってもらう
3. 入金確認したら、Claude Codeで:
   「〇〇さんを有料プランにして」→ MCP経由でDB更新
4. ユーザーがログインすると有料機能が使える
5. 毎月の支払い確認も自分で行う
6. 未払いの人は:
   「〇〇さんアカウント停止して」→ MCP経由でDB更新
```

将来ユーザーが増えて手動管理が大変になったら、その時にStripe等を組み込む。

### 3.5 DB設計（Supabase）

```
┌──────────────────────────────────────────────────────┐
│ members テーブル                                      │
│ ─────────────────────────────────────────────────── │
│ id | name | email | plan | status | created_at       │
│ 1  | 田中太郎 | tanaka@.. | paid | active | 2026-03.. │
│ 2  | 山田花子 | yamada@.. | paid | suspended | ...    │
│ 3  | 佐藤次郎 | sato@..   | free | active | ...      │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ usage_logs テーブル                                    │
│ ─────────────────────────────────────────────────── │
│ id | member_id | action | query | created_at          │
│ 1  | 1         | search | AI副業 | 2026-03-15 10:00   │
│ 2  | 1         | analyze | ...   | 2026-03-15 10:02   │
└──────────────────────────────────────────────────────┘
```

### 3.6 Web版との違い

| 項目 | Web版（現行） | 会員制版（予定） |
|------|-------------|----------------|
| APIキー | ユーザー負担 | 運営負担 |
| 認証 | なし | 会員登録必須（Clerk） |
| 課金 | なし（無料） | 外部決済（銀行振込等） |
| 使用制限 | なし | 月N回まで等 |
| デプロイ | Render | Vercel |
| 会員管理 | - | AI管理（管理用MCP） |

---

## 4. 現在のAPI仕様（Web版）

### エンドポイント

| メソッド | パス | 機能 | Claude使用 |
|---------|------|------|-----------|
| GET | `/youtube-research` | Web UI | - |
| POST | `/youtube-research/api/search` | 検索+バズ | 不要 |
| POST | `/youtube-research/api/analyze-selected` | ターゲット+KW | 必要 |
| POST | `/youtube-research/api/trend` | トレンド判定 | 必要 |
| GET | `/youtube-research/api/health` | ヘルスチェック | - |
| GET | `/youtube-research/api-key-guide` | APIキー取得ガイド | - |

### リクエスト/レスポンス

**POST /api/search**
```json
{
  "query": "検索キーワード",
  "filters": {
    "lengthCategory": "all",
    "uploadPeriod": "month",
    "regionCode": "JP"
  },
  "maxResults": 20,
  "youtubeApiKey": "ユーザーのキー",
  "anthropicApiKey": "ユーザーのキー（オプション）"
}
```

**POST /api/analyze-selected**
```json
{
  "videos": [VideoMeta配列],
  "anthropicApiKey": "ユーザーのキー"
}
```

**POST /api/trend**
```json
{
  "titles": ["動画タイトル1", "動画タイトル2"],
  "anthropicApiKey": "ユーザーのキー（オプション）"
}
```

---

## 5. ファイル構成

### Web版（開発1）- 既存・変更しない
```
src/youtube-research/
  ├── types.ts        # 型定義（VideoMeta, BuzzResult等）
  ├── prompts.ts      # Claudeプロンプト（改善済み）
  ├── service.ts      # メインロジック（検索/バズ/トレンド/ターゲット/KW）
  ├── controller.ts   # リクエスト処理（Express handler）
  └── routes.ts       # ルーター定義

public/
  ├── youtube-research.html       # メインUI
  ├── youtube-research-api-guide.html  # APIキー取得ガイド
  ├── css/youtube-research.css    # スタイル
  └── js/youtube-research.js      # フロントJS
```

### MCP版（youtube-research-mcp）- 既存・完成済み
```
dev/youtube-research-mcp/
  ├── src/server.ts    # MCPサーバー本体
  ├── src/service.ts   # YouTubeResearchService（Web版と同じロジック）
  ├── src/types.ts     # 型定義
  ├── src/prompts.ts   # プロンプト
  ├── bin/cli.mjs      # エントリポイント
  ├── dist/            # ビルド済み
  └── package.json
```

### 会員制版（youtube-research-members）- これから作る
```
dev/youtube-research-members/
  ├── src/app/                    # Next.js ページ
  │   ├── page.tsx                # トップページ
  │   ├── sign-in/                # ログインページ（Clerk）
  │   ├── sign-up/                # 会員登録ページ（Clerk）
  │   ├── dashboard/              # リサーチツール画面
  │   └── api/                    # API Routes
  │       ├── search/             # YouTube検索API
  │       ├── analyze/            # ターゲット分析API
  │       └── trend/              # トレンド判定API
  ├── src/lib/                    # 共通ロジック
  │   ├── youtube-service.ts      # service.tsをベースにコピー
  │   ├── types.ts                # 型定義
  │   └── prompts.ts              # プロンプト
  └── .env.local                  # APIキー（gitに含めない）
```

### 管理用MCP（youtube-research-admin-mcp）- これから作る
```
dev/youtube-research-admin-mcp/
  └── src/
      ├── server.ts               # MCPサーバー（会員管理ツール）
      └── db.ts                   # Supabase接続
```

---

## 6. ロードマップ

### Phase 0: 現状（完了済み）
- [x] Web版の開発・Renderデプロイ
- [x] キーワード分析「不明」問題の修正（tags活用+プロンプト改善）
- [x] バズ比率・トレンド判定の修正
- [x] 国フィルタ機能追加
- [x] MCP版の作成（スタンドアロンパッケージ）
- [x] GitHub Private化
- [x] 設計ドキュメント作成
- [x] SESSION_HANDOFF.md 更新

### Phase 1: 依頼者デモ + フィードバック
- [ ] Web版を依頼者に見せる
- [ ] フィードバックを元にUI改善
- [ ] 必要なら機能追加

### Phase 2: 会員制版のプロジェクト作成
- [ ] `dev/youtube-research-members/` ディレクトリ作成（新規）
- [ ] GitHubに新リポジトリ作成（Private）
- [ ] Next.js プロジェクト初期化（`npx create-next-app`）
- [ ] Clerkアカウント作成 + 組み込み
- [ ] 今のWeb版のUI（HTML/CSS/JS）をNext.jsに移植
- [ ] ログイン必須のページ保護

### Phase 3: バックエンド + DB
- [ ] Supabaseプロジェクト作成
- [ ] members テーブル、usage_logs テーブル作成
- [ ] API Routes実装（認証チェック → プランチェック → 利用回数チェック → 検索実行）
- [ ] 運営のAPIキーを環境変数に設定（ユーザーには見えない）

### Phase 4: 管理用MCP
- [ ] `dev/youtube-research-admin-mcp/` 作成
- [ ] Supabase接続 + 会員CRUD + 利用統計のMCPツール実装
- [ ] Claude Codeの `.mcp.json` に登録
- [ ] テスト（「会員一覧」「〇〇さんの情報」「停止して」等）

### Phase 5: デプロイ + テスト
- [ ] Vercelアカウント作成 + デプロイ
- [ ] 独自ドメイン設定（オプション）
- [ ] E2Eテスト（会員登録 → ログイン → リサーチ → 結果確認）
- [ ] 管理MCPテスト（会員管理が自然言語で動くか確認）
- [ ] dev の SYNC_LIST.md と .gitignore 更新

### Phase 6: 運用
- [ ] 月次のAPIコスト確認
- [ ] 未払い者の確認・アカウント管理（AI経由）
- [ ] ユーザーフィードバック対応
- [ ] 将来: ユーザー数が増えたらStripe組み込み検討

---

## 7. 重要な決定事項

| 日付 | 決定 | 理由 |
|------|------|------|
| 2026-02-20 | Web版のソースコードは上書き禁止 | 事業者販売版として保持するため |
| 2026-02-20 | 会員制版は別ディレクトリで作成 | Web版を壊さないため |
| 2026-02-21 | MCP版はnpm公開しない、GitHub Private | 身内限定にするため |
| 2026-02-21 | MCP版の配布はGitHubコラボレーター招待 | アクセス制御が簡単 |
| 2026-02-21 | デプロイ先: **Vercel** | Next.jsとの相性最高、初心者でも簡単 |
| 2026-02-21 | 認証: **Clerk** | UIコンポーネント付き、Next.js公式プラグイン |
| 2026-02-21 | DB: **Supabase** | PostgreSQL、管理画面あり、無料枠大きい |
| 2026-02-21 | 決済: **ツール外で処理** | Stripe組み込みは複雑、少人数なら手動で十分 |
| 2026-02-21 | 会員管理: **AI管理（管理用MCP）** | 管理画面UI不要、自然言語で操作可能 |
| 2026-02-21 | Cloudflare Workers は却下 | Node.js互換性に制限、Vercelの方が楽 |

---

## 8. 運営コスト試算

### 運営コスト（ユーザー100人想定）

| 項目 | 月額コスト | 備考 |
|------|-----------|------|
| YouTube Data API | ¥0 | 無料枠内（1万units/日） |
| Anthropic API | 約¥3,000〜¥10,000 | 1回分析約¥3〜¥10 × 利用回数 |
| Vercel | ¥0 | 無料枠内 |
| Supabase | ¥0 | 無料枠内（500MB、50万行） |
| Clerk | ¥0 | 1万人まで無料 |
| **合計** | **約¥3,000〜¥10,000** | Anthropic APIが主なコスト |

### 損益分岐（月額980円の場合）
- 10人 × ¥980 = ¥9,800 → ほぼトントン
- 50人 × ¥980 = ¥49,000 → 十分黒字
- 100人 × ¥980 = ¥98,000 → 大幅黒字

---

## 9. Web版 本番デプロイガイド（依頼者向け）

### 背景

- このツールは依頼者のために作っている
- 現在は自分のRender無料枠でデモ用に公開中（スリープあり）
- 依頼者がGOを出したら、**依頼者のアカウント**で本番デプロイする

### 推奨: Render Starter（$7/月 = 約¥1,050/月）

| 比較項目 | Render | Vercel | Cloudflare Workers | Railway |
|---------|--------|--------|-------------------|---------|
| Express.js対応 | そのまま動く | 要改造 | 未対応 | そのまま動く |
| タイムアウト | 100分 | 10秒（無料）/ 60秒（Pro） | CPU時間制限 | 制限なし |
| Claude API 10〜20秒待ち | 問題なし | 無料枠はNG | 壁時計は問題なし | 問題なし |
| コード変更 | 不要 | 必要 | 必要 | 不要 |
| 月額 | $7 | $0〜$20 | $5 | $5 |
| スリープ | なし | なし | なし | なし |

**Vercel・Cloudflare Workersは非推奨**: Express.jsアプリには不向き（Vercel無料枠はタイムアウト10秒でClaude APIが待てない、Cloudflare WorkersのExpress対応は未完成）。

### 本番デプロイ手順（依頼者のアカウントで）

```
ステップ1: Renderアカウント作成
  → https://render.com でアカウント作成
  → クレジットカード登録

ステップ2: GitHubリポジトリを接続
  → 依頼者のGitHubにリポジトリをfork or transfer
  → Renderダッシュボード → New → Web Service → リポジトリ選択

ステップ3: ビルド設定
  → Build Command: npm install && npx tsc
  → Start Command: npx tsx src/server.ts
  → Environment: Node.js
  → Plan: Starter ($7/月)

ステップ4: 環境変数
  → PORT: 自動設定
  → ANTHROPIC_API_KEY: 依頼者のキー（オプション）

ステップ5: 独自ドメイン設定（オプション）
  → Settings → Custom Domain → ドメイン設定
  → DNS設定を案内

ステップ6: 動作確認
  → URLにアクセス → YouTube検索 → トレンド判定 → ターゲット分析
```

### 他の選択肢

| 選択肢 | 月額 | 備考 |
|--------|------|------|
| Railway | $5〜 | Renderと同等。コード変更不要 |
| VPS（自前サーバー） | $5〜$20 | 依頼者がVPSを持っている場合 |
| Google Cloud Run | $0〜 | 無料枠あり。GCPセットアップが複雑 |

### VPSで運用する場合

```bash
# 1. Node.js 18以上をインストール
# 2. リポジトリをclone
git clone https://github.com/subaru-blip/kaihatu1.git
cd kaihatu1 && npm install

# 3. pm2でプロセス管理
npm install -g pm2
pm2 start "npx tsx src/server.ts" --name youtube-research

# 4. nginx でリバースプロキシ + Let's Encrypt でSSL
```

---

*このドキュメントは設計の原本です。セッションをまたいで参照・更新してください。*
