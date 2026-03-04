# LP Creator 開発ステータス

**最終更新**: 2026-03-04

## Stage 1（セミナー簡易版）進捗

### 完了（2026-03-04）

| # | タスク | ファイル |
|---|--------|---------|
| 1 | 型定義 | `types.ts` |
| 2 | プロンプト設計 | `prompts.ts` |
| 3 | サービス層（Claude API + HTML生成） | `service.ts` |
| 4 | コントローラー（SSE + バリデーション + 設定API） | `controller.ts` |
| 5 | ルーティング | `routes.ts` |
| 6 | 設定永続化 | `settings-store.ts` |
| 7 | ユーザー向けUI | `public/lp-creator.html` |
| 8 | 管理画面UI | `public/lp-creator-settings.html` |
| 9 | app.ts統合 | ルーター登録 + レート制限 + CSP |
| 10 | ビルド設定 | `tsconfig.yt.json` 更新 |
| 11 | セキュリティ | `.gitignore` に `data/` 追加 |

### 追加完了（2026-03-04 セッション2）

| # | タスク | ファイル |
|---|--------|---------|
| 12 | CSP修正（inline script許可） | `app.ts` |
| 13 | テスト生成エンドポイント | `controller.ts` + `routes.ts` |
| 14 | テスト生成ボタン（UI） | `public/lp-creator.html` |

### 未完了

| # | タスク | 優先度 |
|---|--------|--------|
| 1 | テスト方式決定（Claude Code生成 or API無料クレジット） | 高 |
| 2 | AI生成の実機テスト（ストリーミング→プレビュー確認） | 高 |
| 3 | LP HTMLダウンロード機能 | 中 |
| 4 | プロンプト品質調整 | 中 |
| 5 | Renderデプロイ | 中 |
| 6 | 要件定義書との突き合わせ | 低 |

## 設計判断

- APIキーはユーザーに見せない（管理画面のみ）→ DECISION-003
- 設定は `data/lp-creator-settings.json` にJSON永続化
- フォールバック: 設定ファイル → 環境変数
- claude.aiサブスクのキーはAPIでは使えない（別課金体系）
- CSPで `scriptSrc: 'unsafe-inline'` が必要（インラインJS使用のため）
