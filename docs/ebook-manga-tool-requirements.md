# 電子書籍+漫画 3段階自動生成ツール 要件定義書

**作成日**: 2026-02-24
**プロジェクト名**: ebook-manga-pipeline（仮称）
**ステータス**: リサーチ完了 → 設計フェーズ

---

## 1. プロジェクト概要

### 1.1 目的

現在 Claude Code のスキル（ebook-creator-ss / manga-creator-ss）として存在する電子書籍・漫画生成機能を、**ブラウザ操作に依存しないAPI ベースのツール**として再構築する。

### 1.2 現状の課題

| 課題 | 詳細 |
|------|------|
| ブラウザ依存 | nanobanana-pro が Puppeteer でGeminiブラウザを操作 → 不安定、他PCで再現困難 |
| セットアップの複雑さ | ブラウザプロファイル・認証管理・venv構築が必要 |
| スケーラビリティ | 1枚ずつブラウザ操作 → 50枚の図解に数時間 |
| ポータビリティ | PC固有の環境に強く依存、別PCへの移行が困難 |

### 1.3 ゴール

```
テーマを入力 → 文章生成 → 挿絵挿入 → 漫画挿入 → EPUB/DOCX出力
```

これを **APIベース** で実現し、**別PCでも1コマンドでセットアップ**できるツールにする。

---

## 2. システムアーキテクチャ

### 2.1 推奨構成: MCPサーバー + Claude Codeスキル ハイブリッド

リサーチの結果、以下の理由から **MCPサーバー** をコアに採用する：

| 比較項目 | MCPサーバー | CLIツール | Webアプリ | スキルのみ |
|---------|-----------|----------|----------|----------|
| 別PCセットアップ | `claude mcp add` 1コマンド | `npm i -g` | デプロイ必要 | git clone必要 |
| Claude Code統合 | ネイティブ（ツールとして呼べる） | Bash経由 | API経由 | ネイティブ |
| ポータビリティ | npm公開で最高 | 高 | 低 | 中（git依存） |
| 開発の容易さ | 中 | 高 | 高 | 最高 |

### 2.2 全体構成図

```
Claude Code スキル（オーケストレーター）
  │
  │  MCPツール呼び出し
  ▼
MCPサーバー: ebook-manga-pipeline
  │
  ├── Phase 1: generate_text()
  │   └── Claude API / Gemini API（文章生成）
  │
  ├── Phase 2: generate_illustrations()
  │   └── Gemini 2.5 Flash Image API / gpt-image-1 API（挿絵生成）
  │
  ├── Phase 3: generate_manga()
  │   └── Gemini API / Flux API / ComfyUI API（漫画コマ生成）
  │
  └── Phase 4: export()
      └── Pandoc / ebooklib（EPUB/DOCX出力）
```

### 2.3 ディレクトリ構成案

```
ebook-manga-pipeline/
├── src/
│   ├── index.ts              # MCPサーバー エントリーポイント
│   ├── tools/
│   │   ├── generate-text.ts       # Phase 1: 文章生成ツール
│   │   ├── generate-illustrations.ts  # Phase 2: 挿絵生成ツール
│   │   ├── generate-manga.ts     # Phase 3: 漫画生成ツール
│   │   └── export.ts             # Phase 4: 出力ツール
│   ├── pipeline/
│   │   ├── phase1-text.ts         # 文章生成パイプライン
│   │   ├── phase2-illustration.ts # 挿絵パイプライン
│   │   └── phase3-manga.ts       # 漫画パイプライン
│   ├── api/
│   │   ├── gemini.ts             # Gemini API ラッパー
│   │   ├── openai.ts             # OpenAI API ラッパー（オプション）
│   │   └── flux.ts               # Flux API ラッパー（オプション）
│   └── utils/
│       ├── epub-builder.ts        # EPUB構築
│       ├── docx-builder.ts        # DOCX構築（Pandoc連携）
│       └── retry.ts               # リトライ・エラーハンドリング
├── package.json
├── tsconfig.json
└── README.md
```

---

## 3. Phase 1: 文章生成

### 3.1 機能要件

| 項目 | 内容 |
|------|------|
| 入力 | テーマ、ターゲット読者、参考資料（任意） |
| 出力 | 構造化JSON（chapters.json） |
| 文字数 | 約15,000字（5章構成） |
| 1章あたり | 2,500〜3,000字 |
| 文体 | です・ます調（カスタマイズ可能） |

### 3.2 パイプライン設計（コンパイラ方式）

50,000冊以上の生成実績を持つアーキテクチャ（earezki.com）に基づく：

```
Step 1: メタデータ生成
  Input:  テーマ + ターゲット
  Output: { title, genre, tone, style, target_audience }
  Model:  Gemini Flash（安価・高速）

Step 2: 構成設計（アウトライン）
  Input:  メタデータ + 参考資料
  Output: { chapters: [{ id, title, key_points, illustration_hint, manga_hint }] }
  Model:  Claude Sonnet（構造化出力で品質確保）

Step 3: 章ごとの本文生成（逐次）
  Input:  メタデータ + アウトライン + 当該章の情報
  Output: { chapter_id, title, content, word_count }
  Model:  Claude Haiku（コスト最適） or Sonnet（品質重視）
  ★ 1 APIコール = 1章（5,000字超えると品質低下するため）

Step 4: 画像タグ挿入
  Input:  各章の本文
  Output: 画像タグ（HEADER_IMAGE / INLINE_IMAGE）が埋め込まれた本文
  Model:  Claude Haiku（パターン選定のみ）
```

### 3.3 コスト試算（1冊あたり）

| モデル | 用途 | 推定コスト |
|--------|------|-----------|
| Gemini Flash-Lite | メタデータ生成 | $0.004 |
| Claude Sonnet 4 | 構成設計 | $0.05 |
| Claude Haiku 3.5 | 本文生成（5章） | $0.30 |
| Claude Haiku 3.5 | 画像タグ挿入 | $0.03 |
| **合計** | | **約 $0.38** |

### 3.4 品質管理

- **文体サンプル**: ユーザーの文章サンプル3〜5件をプロンプトに含める → 手動編集量67%削減（実績データ）
- **構造化出力**: Claude API の Structured Outputs で JSON Schema を強制 → 出力形式のブレを防止
- **一貫性チェック**: 章間でのキーワード・用語の統一を後処理で検証

---

## 4. Phase 2: 挿絵生成・挿入

### 4.1 機能要件

| 項目 | 内容 |
|------|------|
| 入力 | 画像タグ（HEADER_IMAGE / INLINE_IMAGE）付き原稿 |
| 出力 | 画像ファイル + 画像が埋め込まれた原稿 |
| 画像枚数 | 約40〜60枚（章ヘッダー5枚 + 本文中図解35〜55枚） |
| スタイル | フラットベクター/インフォグラフィック（統一） |

### 4.2 画像生成API選定

**重要: Nano Banana Pro（Gemini 3 Pro Image）でないと品質が出ない**

清水さんの実運用経験から、Gemini 2.5 Flash Image 等の通常APIでは図解・インフォグラフィック・漫画の品質が不十分。**Nano Banana Pro（`gemini-3-pro-image-preview`）が必須**。

| API | 料金/枚 | 日本語テキスト | 図解品質 | 漫画品質 | 推奨度 |
|-----|---------|--------------|---------|---------|--------|
| **Nano Banana Pro** | $0.134〜$0.24 | ★★★★★（94%） | ★★★★★ | ★★★★ | **必須** |
| gpt-image-1 (High) | $0.167 | ★★★★★ | ★★★★★ | ★★★★ | 代替候補 |
| Ideogram V3 | $0.08 | ★★★★ | ★★★★★ | ★★★ | テキスト精度重視時 |
| Gemini 2.5 Flash Image | $0.039 | ★★★★ | ★★★★ | ★★★ | **品質不足（非推奨）** |
| Pollinations.ai | **無料** | ★★★ | ★★★ | ★★★ | テスト・開発専用 |

**確定: Nano Banana Pro（`gemini-3-pro-image-preview`）**
- 日本語テキスト精度94%（業界最高水準）
- 4K対応、多言語テキスト最強
- 現在ブラウザ操作で使っている品質をAPI経由でも維持できる

### 4.3 コスト試算（挿絵50枚の場合）

| API | 50枚のコスト |
|-----|-------------|
| **Nano Banana Pro（低解像度）** | **$6.70** |
| **Nano Banana Pro（高解像度）** | **$12.00** |
| gpt-image-1 (High) | $8.35 |

### 4.4 実装方法

```typescript
// Nano Banana Pro（Gemini 3 Pro Image）での生成
import { GoogleGenAI } from "@google/genai";

const client = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

async function generateIllustration(prompt: string, outputPath: string) {
  const response = await client.models.generateContent({
    model: "gemini-3-pro-image-preview",  // Nano Banana Pro
    contents: prompt,
  });

  for (const part of response.parts) {
    if (part.inlineData) {
      const buffer = Buffer.from(part.inlineData.data, "base64");
      fs.writeFileSync(outputPath, buffer);
    }
  }
}
```

### 4.5 既存プロンプト資産の活用

現在の ebook-creator-ss に定義されている **26パターンの図解プロンプトテンプレート** はそのまま流用可能。NanoBanana用のプロンプト形式はGemini APIでもそのまま使える。

---

## 5. Phase 3: 漫画生成・挿入

### 5.1 機能要件

| 項目 | 内容 |
|------|------|
| 入力 | 原稿テキスト + キャラクター設定 |
| 出力 | 漫画パネル画像（896x1200px） |
| コマ数 | 100〜200+ コマ（原稿の長さに応じる） |
| スタイル | アニメ/マンガスタイル（フルカラー） |

### 5.2 漫画生成の最大課題: キャラクター一貫性

| アプローチ | 品質 | 実装難易度 | API対応 | 推奨度 |
|-----------|------|-----------|---------|--------|
| **テキスト埋め込み（現行方式）** | ★★★ | 低 | 全API | 最低限 |
| **IPAdapter / InstantID** | ★★★★ | 中 | ComfyUI API | 推奨 |
| **StoryDiffusion** | ★★★★★ | 中〜高 | セルフホスト | 最高品質 |
| **LoRA訓練** | ★★★★★ | 高 | ComfyUI API | 最高制御 |
| **Gemini API + 参照画像** | ★★★★ | 低 | Gemini API | **現実的最適解** |

**推奨: Gemini API + キャラクターシート参照画像**

現在の manga-creator-ss で使っている「キャラクターシートを添付して毎回参照させる」方式は、Gemini APIでもそのまま実現可能。`--attach-image` の代わりにAPIのマルチモーダル入力を使う。

```typescript
// Gemini API でキャラクターシート参照 + コマ生成
const response = await client.models.generateContent({
  model: "gemini-2.5-flash-image",
  contents: [
    {
      inlineData: {
        mimeType: "image/png",
        data: characterSheetBase64  // キャラクターシート画像
      }
    },
    {
      text: panelPrompt  // コマのプロンプト（英語 + 日本語セリフ）
    }
  ],
});
```

### 5.3 パイプライン設計

```
Step 1: ストーリー構成（LLM）
  Input:  原稿テキスト
  Output: story_structure.json（シーン分割 + コマ割り）

Step 2: キャラクターシート生成（画像API）
  Input:  キャラクター設定テキスト
  Output: all_characters.png（1600x900px）

Step 3: コマプロンプト生成（LLM）
  Input:  story_structure + character_prompts
  Output: page_prompts.json（全コマ分）

Step 4: コマ画像生成（画像API × N枚）
  Input:  各コマのプロンプト + キャラクターシート参照
  Output: panels/page_001.png 〜 page_NNN.png
```

### 5.4 コスト試算（漫画100コマの場合）

| API | 100コマのコスト |
|-----|---------------|
| **Nano Banana Pro（低解像度）** | **$13.40** |
| **Nano Banana Pro（高解像度）** | **$24.00** |
| gpt-image-1 (High) | $16.70 |

---

## 6. Phase 4: 出力（EPUB / DOCX）

### 6.1 出力形式

| 形式 | 用途 | 実装方法 |
|------|------|---------|
| DOCX | Kindle出版（KDP）、Word編集 | Pandoc |
| EPUB | 電子書籍ストア | ebooklib (Python) or html-to-epub (Node.js) |
| PDF | 印刷・配布 | Pandoc経由 |
| Markdown | 中間形式・編集用 | そのまま出力 |

### 6.2 ライブラリ選定

| ライブラリ | 言語 | 特徴 |
|-----------|------|------|
| **Pandoc** | CLI | 現行で使用中。Markdown→DOCX/EPUB/PDF全対応 |
| **ebooklib** | Python | EPUB2/EPUB3の読み書き。最も広く使われている |
| **@lesjoursfr/html-to-epub** | Node.js | 最も活発にメンテされているnpmパッケージ |
| **ebook-mcp** | Python (MCP) | MCP経由でClaude Codeから直接EPUB操作可能 |

**推奨: Pandoc（現行維持）+ ebook-mcp（MCP連携用）**

---

## 7. 利用するAPI・サービスまとめ

### 7.1 APIキー一覧

| API | 用途 | 取得先 | 料金目安 |
|-----|------|--------|---------|
| **Gemini API** | 画像生成（挿絵・漫画） | [Google AI Studio](https://aistudio.google.com/app/apikey) | 無料枠500枚/日 |
| **Claude API** | 文章生成 | [Anthropic Console](https://console.anthropic.com/) | $0.38/冊 |
| **OpenAI API**（オプション） | 画像生成の代替 | [OpenAI Platform](https://platform.openai.com/) | $0.009〜/枚 |

### 7.2 MCP関連ツール（発見済み）

| ツール | 機能 | URL |
|--------|------|-----|
| **ebook-mcp** | Claude CodeからEPUB操作 | `pip install ebook-mcp` |
| **fal.ai MCP** | 600+モデルの画像生成 | Smithery経由 |
| **Together AI FLUX MCP** | FLUX.1 Schnell（3ヶ月無料） | Smithery経由 |
| **Stability AI MCP** | Stable Diffusion API | GitHub |
| **Pollinations.ai** | 完全無料の画像生成 | APIキー不要 |

---

## 8. セットアップ手順（別PCでの再現）

### 8.1 ゴール: 1コマンドセットアップ

```bash
# MCPサーバーとして追加（npmに公開後）
claude mcp add ebook-manga-pipeline -- npx -y ebook-manga-pipeline

# 環境変数設定
export GEMINI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"  # 文章生成用
```

### 8.2 開発中のセットアップ（npm公開前）

```bash
cd ~/dev/開発1/ebook-manga-pipeline
npm install
npm run build

# ローカルMCPとして追加
claude mcp add ebook-manga-pipeline -- node ~/dev/開発1/ebook-manga-pipeline/dist/index.js
```

---

## 9. 既存スキルとの関係

### 9.1 移行マップ

| 現行スキル | 新ツールでの対応 | 変更点 |
|-----------|----------------|--------|
| ebook-creator-ss | Phase 1 + Phase 2 + Phase 4 | ブラウザ操作 → API |
| manga-creator-ss | Phase 3 | ブラウザ操作 → API |
| nanobanana-pro | Phase 2, 3の画像生成部分 | Puppeteer → Gemini API直接呼び出し |

### 9.2 既存資産の流用

- **26パターンの図解プロンプトテンプレート** → そのまま流用
- **漫画コマ割りテンプレート（10種類）** → そのまま流用
- **キャラクター外見プロンプトDB方式** → API版に移植
- **5層リサーチ手法** → スキル側で継続使用（ツール化対象外）
- **DOCX変換（Pandoc）** → そのまま流用

### 9.3 共存方針

新ツールが完成するまで既存スキルは**そのまま維持**。
新ツールが安定したら、スキル側をMCPツール呼び出しに切り替える。

---

## 10. 参考事例・オープンソース

### 10.1 最も参考になるOSS

| プロジェクト | 特徴 | URL |
|-------------|------|-----|
| **wesleyscholl/book-generator** | KDP実績あり、Gemini/OpenAI/Groq対応、EPUB/PDF/MOBI出力 | [GitHub](https://github.com/wesleyscholl/book-generator) |
| **neshani/illumination_pipeline** | EPUB→LLM→挿絵生成→EPUB書き戻しのフルパイプライン | [GitHub](https://github.com/neshani/illumination_pipeline) |
| **AI Comic Factory** | LLM+SDXL、Next.js、Apache-2.0 | [GitHub](https://github.com/jbilcke-hf/ai-comic-factory) |
| **StoryDiffusion** | NeurIPS 2024、キャラクター一貫性の最先端 | [GitHub](https://github.com/HVision-NKU/StoryDiffusion) |
| **comics_generator** | Python、OpenAI+Stability SDK、シンプル構成 | [GitHub](https://github.com/Aschen/comics_generator) |

### 10.2 SaaS事例

| サービス | 特徴 | 価格 |
|---------|------|------|
| **Automateed** | テーマ→10-15分でEPUB完成、AI挿絵+表紙+KDPガイド | 月額SaaS |
| **KindleBlitz**（日本発） | Gemini/OpenAI APIキー自前方式、EPUB/DOCX+KDP拡張 | 月額SaaS |
| **Dashtoon** | Webtoon向け、キャラDB参照で一貫性確保 | Series A $12.8M調達 |
| **LlamaGen** | コミック・Webtoon、4K対応、API提供 | 無料〜$6/月 |

### 10.3 市場規模

- **AI生成コミックブック市場**: 2024年 $1.15B → 2029年 $4.6B（CAGR 32.2%）
- **AI Comic Generator市場**: 2034年に $20.5B 到達予測（CAGR 23.4%）

---

## 11. 実装ロードマップ（提案）

### Phase A: MVP（文章生成のみ）

- MCPサーバーの骨格構築
- Claude API で文章生成パイプライン実装
- Markdown出力 + Pandoc DOCX変換
- **成果物**: テーマ → 15,000字原稿 → DOCX

### Phase B: 挿絵追加

- Gemini 2.5 Flash Image API 連携
- 既存の26パターンプロンプト移植
- 画像生成 + 原稿への埋め込み
- **成果物**: テーマ → 原稿+挿絵40-60枚 → DOCX

### Phase C: 漫画追加

- キャラクターシート生成
- コマプロンプト生成（LLM）
- 漫画パネル画像生成（Gemini API + キャラ参照）
- **成果物**: テーマ → 原稿+挿絵+漫画100-200コマ

### Phase D: パッケージ化

- npm公開
- `claude mcp add` で1コマンドセットアップ
- README / 使い方ドキュメント整備
- **成果物**: 別PCで即使えるツール

---

## 12. コスト総括（1冊あたり）

**Nano Banana Pro（Gemini 3 Pro Image）前提のコスト**

| 項目 | 低解像度 | 高解像度 |
|------|---------|---------|
| 文章生成（Claude Haiku） | $0.38 | $0.38 |
| 挿絵50枚（Nano Banana Pro） | $6.70 | $12.00 |
| 漫画100コマ（Nano Banana Pro） | $13.40 | $24.00 |
| **合計** | **約 $20.48/冊（約3,100円）** | **約 $36.38/冊（約5,500円）** |

**コスト削減の選択肢:**
- 挿絵のみ（漫画なし）: 約 $7〜$12/冊（約1,000〜1,800円）
- 漫画のコマ数を減らす（50コマ）: 合計 約 $13〜$24/冊
- 一部の図解をFlash Image（安価版）で生成し、重要な図解のみNano Banana Proにする

---

## 13. 法的注意事項

- **Amazon KDP**: AI生成コンテンツは出版時に申告が必要（AI「補助」は申告不要）
- **著作権**: 自分のオリジナルアイデア・設定で生成し、既存キャラクターに類似させない
- **文化庁ガイドライン（2024年）**: 人間が設計・設定を行ったAI生成コンテンツは著作権保護の可能性あり

---

## 14. リサーチソース一覧

### API・技術ドキュメント
- [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Imagen 4 API](https://developers.googleblog.com/imagen-4-now-available-in-the-gemini-api-and-google-ai-studio/)
- [Claude API Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Claude API Batch Processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- [OpenAI Image Pricing](https://platform.openai.com/docs/pricing)
- [fal.ai](https://fal.ai/)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)

### オープンソース
- [wesleyscholl/book-generator](https://github.com/wesleyscholl/book-generator)
- [neshani/illumination_pipeline](https://github.com/neshani/illumination_pipeline)
- [AI Comic Factory](https://github.com/jbilcke-hf/ai-comic-factory)
- [StoryDiffusion](https://github.com/HVision-NKU/StoryDiffusion)
- [comfyui-panelforge](https://github.com/lisaks/comfyui-panelforge)
- [ebook-mcp](https://github.com/onebirdrocks/ebook-mcp)
- [epub-gen](https://github.com/cyrilis/epub-gen)
- [ebooklib](https://github.com/aerkalov/ebooklib)
- [KCC (Kindle Comic Converter)](https://github.com/ciromattia/kcc)

### 市場・事例
- [Compiler-Style AI Pipeline for Books (50K冊実績)](https://earezki.com/ai-news/2026-02-22-i-built-an-ai-pipeline-for-books-heres-the-architecture/)
- [n8n Community: AI comic pipeline](https://community.n8n.io/t/built-an-ai-pipeline-that-turns-text-into-full-comic-book-storyboards-feels-like-a-goldmine-but-i-need-some-discuss/225002)
- [AI-Generated Comic Book Market Report 2025](https://www.globenewswire.com/news-release/2026/01/29/3228444/)
- [LLM API Pricing 2026](https://intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude)
