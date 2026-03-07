---
name: lp-nanobanana-ss
description: ナレッジプロンプトに基づくLPコピーライティング生成 → 参考LPデザインリサーチ → NanoBanana画像生成プロンプト作成 → セクション画像順次生成。コピーライティング未経験でも反応率の高いLP画像を一気通貫で完成させる。
---

# LP NanoBanana Creator - LP画像一括生成スキル

商品情報入力 → LPタイプ選択 → コピー生成 → デザインリサーチ → プロンプト生成 → 画像順次生成。

## When to Use This Skill

- 「LPを作って」「ランディングページを生成」
- 「LP画像を作成」「LPを一括生成」
- 「セミナー用のLPを作りたい」
- 「商品のランディングページを作って」

## Do NOT Use for

- 単発の画像1枚 → `nanobanana-pro` を使用
- LP分析・改善のみ → `lp-analysis` を使用
- LPデザイン設計のみ → `lp-design` を使用
- LP用JSONテキスト差し替え → `lp-json-generator` を使用

## ナレッジプロンプト（knowledge/）

LPコピーの品質を担保する専門プロンプトテンプレート:

```
.claude/skills/lp-nanobanana-ss/knowledge/
├── 00-input-template.md      # 入力テンプレート（ペイン・ゲイン・コア価値・競合限界）
├── 01-education-lp.md        # 教育型LP（25000文字、見込み客教育、4STEP戦略設計）
├── 02-product-interest-lp.md # 商品興味づけLP（10000文字、商品への興味→登録誘導）
├── 03-expose-lp.md           # 暴露系LP（10000文字、業界の真実暴露→参加促進）
├── 04-cutting-edge-lp-v1.md  # 先端×秘匿LP v1（業種別テンプレート、FOMO最大化）
└── 05-cutting-edge-lp-v2.md  # 先端×秘匿LP v2（詳細版、危機感・経済格差訴求）
```

## 全体フロー（5ステップ）

```
Step 1: 商品情報入力 & LPタイプ選択
   │  ユーザーから商品情報を受け取る（必須）
   │  4つのLPタイプから選択
   │  → 確認なしで即Step 2へ
   ▼
Step 2: LPコピーライティング生成
   │  選択したナレッジプロンプトを読み込み
   │  入力テンプレートの4項目と組み合わせ
   │  全7セクションのコピーテキストを生成
   │  → copy.md に保存して即Step 3へ
   ▼
Step 3: 参考LPデザインリサーチ（任意）
   │  参考URLのスクリーンショット取得
   │  配色・レイアウト・テキスト配置を分析
   │  → analysis.json に保存して即Step 4へ
   │  ※ URLなしの場合はデフォルトデザインを適用
   ▼
Step 4: NanoBanana用画像生成プロンプト作成
   │  コピーテキスト + デザイン分析結果を統合
   │  全7セクション分のプロンプトを英語で作成
   │  日本語テキスト部分はプロンプト内にそのまま含める
   │  → prompts/section_001.txt 〜 section_007.txt に保存
   ▼
Step 5: NanoBanana画像順次生成
   │  section_001 から順番に画像生成
   │  生成後に幅1080pxへリサイズ
   │  進捗トラッキング + 中断再開対応
   │  → sections/section_001.png 〜 section_007.png に保存
   ▼
完成！ → report.md にレポート出力
```

---

## Step 1: 商品情報入力 & LPタイプ選択

### 最初に必ずやること

**ユーザーに以下の情報を確認する。**

```
LP画像を作成します。以下の情報を教えてください。

【必須入力】
1. 商品名:
2. ターゲット:
3. 商品の強み:

【任意入力】
4. 価格:
5. 詳細説明:
6. 参考LPのURL（あれば）:

【LPタイプを選んでください】
A. 教育型LP（見込み客を教育→セミナー誘導、最も詳細で長文）
B. 商品興味づけLP（商品への興味→登録/購入、ストーリー性重視）
C. 暴露系LP（業界の真実暴露→セミナー誘導、心理的圧迫）
D. 先端×秘匿LP（業界トレンド×FOMO→セミナー誘導、緊急性重視）
```

### 入力テンプレートの4項目

ユーザーの商品情報から以下の4項目を抽出・整理する（`00-input-template.md`参照）:

1. **ターゲットが抱える深刻な悩み（ペイン）**
2. **ターゲットが渇望する理想の未来（ゲイン）**
3. **商品のコア機能・提供価値**
4. **競合や既存の解決策とその限界**

### LPタイプとナレッジプロンプトの対応

| 選択 | ナレッジファイル | 文字数目安 | 特徴 |
|------|-----------------|-----------|------|
| A. 教育型 | `01-education-lp.md` | 25000字 | 4STEP戦略設計、心理トリガー段階配置 |
| B. 商品興味づけ | `02-product-interest-lp.md` | 10000字 | 6セクション、ストーリーテリング重視 |
| C. 暴露系 | `03-expose-lp.md` | 10000字 | 5段階心理操作、情報格差への恐怖 |
| D. 先端×秘匿 | `04-cutting-edge-lp-v1.md` + `05-cutting-edge-lp-v2.md` | 10000字 | FOMO・緊急性・権威性 |

---

## Step 2: LPコピーライティング生成

### 概要

選択されたナレッジプロンプトを`knowledge/`から読み込み、Step 1の商品情報と組み合わせてLPコピーを生成する。

### ナレッジプロンプトの読み込み

```
1. Read tool で選択されたナレッジプロンプトファイルを読み込む
2. Read tool で 00-input-template.md を読み込む
3. ナレッジプロンプトの [ ] プレースホルダーにユーザーの商品情報を埋め込む
4. 全7セクション分のコピーテキストを生成する
```

### 7セクション構成（固定）

| # | セクション | 内容 |
|---|-----------|------|
| 1 | ファーストビュー | キャッチコピー + サブコピー + CTA |
| 2 | 問題提起 | ターゲットの悩み言語化、共感 |
| 3 | 解決策 | 商品のコンセプト提示、差別化 |
| 4 | ベネフィット | 具体的な成果・未来像 |
| 5 | お客様の声 | 成功事例、社会的証明 |
| 6 | 特典 | 無料特典、価格アンカリング、緊急性 |
| 7 | CTA | 最終行動喚起、ボタン、フォーム、追伸 |

### 出力

`output/lp-{slug}/copy.md` に保存:

```markdown
# LPコピー: {商品名}

LPタイプ: {選択されたタイプ}
生成日: {日付}

## セクション1: ファーストビュー
{コピーテキスト}

## セクション2: 問題提起
{コピーテキスト}

## セクション3: 解決策
{コピーテキスト}

## セクション4: ベネフィット
{コピーテキスト}

## セクション5: お客様の声
{コピーテキスト}

## セクション6: 特典
{コピーテキスト}

## セクション7: CTA
{コピーテキスト}
```

---

## Step 3: 参考LPデザインリサーチ（任意）

### 参考URLがある場合

ユーザーが参考LPのURLを提供した場合、スクリーンショットを取得しデザインを分析する。

1. patchright またはブラウザツールでページ全体のスクリーンショットを取得
2. セクションごとに分割して `output/lp-{slug}/research/` に保存
3. 以下の要素を分析:
   - **配色**: メインカラー、アクセントカラー、テキストカラー（HEXコード3色以上）
   - **レイアウト**: カラム数、余白比率、セクション間隔
   - **テキスト配置**: 見出し位置、本文配置、CTA位置
4. 分析結果を `output/lp-{slug}/research/analysis.json` に保存

### 参考URLがない場合

高CVR LP実績データに基づくデフォルトデザイン設定を使用:

```json
{
  "colors": {
    "primary": "#2563EB",
    "accent": "#38BDF8",
    "cta_button": "#F97316",
    "cta_text": "#FFFFFF",
    "background": "#FFFFFF",
    "section_bg_alt": "#F0F9FF",
    "heading_color": "#0F172A",
    "body_text": "#374151",
    "subtext": "#6B7280"
  },
  "layout": {
    "max_width": "1200px",
    "content_width": "960px",
    "heading_font_size": "48px",
    "subheading_font_size": "28px",
    "body_font_size": "17px",
    "cta_font_size": "18px",
    "cta_button_padding": "18px 40px",
    "cta_border_radius": "12px",
    "section_padding_vertical": "96px",
    "section_padding_horizontal": "32px",
    "hero_height": "700px",
    "section_gap": "80px"
  },
  "section_styles": {
    "section_1_fv": "cinematic full-width hero, semi-transparent dark gradient overlay, aspirational imagery, bold white heading text, orange CTA button with rounded corners, maximum visual impact",
    "section_2_problem": "light gray (#F8FAFC) background, flat icons with muted palette, X marks or warning symbols, problem cards with subtle red/orange accents, empathetic tone",
    "section_3_solution": "bright clean product showcase, split layout text-left image-right, primary blue (#2563EB) accent elements, clean white background, professional feel",
    "section_4_benefit": "3-column icon cards with soft drop shadow, light blue (#F0F9FF) background, checkmark icons in green (#10B981), benefit headlines in bold dark text",
    "section_5_testimonial": "warm lighting testimonial cards, star ratings in gold (#F59E0B), avatar circles, quote marks, soft background, authentic feel",
    "section_6_pricing": "pricing card comparison layout, highlighted center card with badge, orange (#F97316) recommended badge, clean table structure, value emphasis",
    "section_7_cta": "high-contrast solid primary (#2563EB) background, single prominent orange button, maximum white space, urgency text, trust badges below button"
  }
}
```

### セクション別NanoBananaスタイルキーワード

プロンプト生成時に各セクションに適用するビジュアルスタイルとアスペクト比:

| # | セクション | アスペクト比 | 推奨px | スタイルキーワード |
|---|-----------|------------|--------|-----------------|
| 1 | ファーストビュー | **3:4** | 1080x1440 | cinematic hero, dark gradient overlay, bold white text, orange CTA, aspirational |
| 2 | お客様の声 | **9:16** | 1080x1920 | warm lighting, testimonial cards, star ratings, avatars, authentic |
| 3 | 問題提起 | **4:5** | 1080x1350 | light gray bg, flat icons, muted palette, warning symbols, empathetic |
| 4 | ベネフィット | **4:5** | 1080x1350 | 3-column cards, soft shadow, light blue bg, green checkmarks, structured |
| 5 | 提供者ストーリー | **3:4** | 1080x1440 | clean white bg, narrative layout, blue accent quote box, professional |
| 6 | 特典・料金 | **4:5** | 1080x1350 | pricing cards, highlighted center, orange badge, clean table, value-focused |
| 7 | CTA | **3:4** | 1080x1440 | solid blue bg, orange button, white space, urgency, trust badges |

**アスペクト比の根拠（モバイルファースト設計）:**
- **3:4**: FV・CTA・ストーリー → 画面内にCTAが収まる適度な縦長
- **4:5**: 問題提起・ベネフィット・料金 → テキスト+カード構成に最適
- **9:16**: お客様の声 → 3カード縦並びで十分な高さが必要

### プロンプト必須ルール

```
┌─────────────────────────────────────────────────────────────────────┐
│  英語のセクションラベル（"Section 7: Final CTA"等）は絶対に入れない │
│  Geminiがそのまま画像にレンダリングしてしまうため                    │
│  safe area（全辺80px余白）を必ず指示に含める                        │
│  コンテンツの重複（カードが2回描画される等）を防ぐ指示を入れる      │
└─────────────────────────────────────────────────────────────────────┘
```

プロンプト冒頭に必ず含めるテンプレート:
```
(best quality, professional landing page design, web design, clean modern layout,
Japanese business website, no watermarks, no labels, no section titles in English)

IMPORTANT: Do NOT render any English section titles, labels, or metadata text.
Only render the Japanese text specified below. Ensure all content has generous
padding from all edges - nothing should be cropped. Leave at least 80px safe
margin on all sides. Do NOT duplicate any content.
```

---

## Step 4: NanoBanana用画像生成プロンプト作成

### 概要

Step 2のコピーテキストとStep 3のデザイン分析を統合し、各セクションごとにNanoBanana用の画像生成プロンプト（英語）を作成する。

### プロンプト構成

各セクションのプロンプトには以下を含める:

- **レイアウト指示**: セクションのレイアウト構造（ヒーローセクション、2カラム、フルワイド等）
- **配色指定**: analysis.jsonから取得したHEXカラーコード
- **テキスト内容**: コピーテキスト（日本語はそのまま含める）
- **視覚要素**: アイコン、装飾、背景パターン等の指示
- **アスペクト比**: LP用縦長画像 `--ar 9:16` または `--ar 3:4`

### プロンプトテンプレート

```
Section {N}: {セクション名}
---
(best quality, professional landing page design, web design, clean modern layout)

Layout: {レイアウト構造の英語説明}
Color scheme: background {bg_hex}, accent {accent_hex}, text {text_hex}

Main heading text in Japanese: 「{見出しテキスト}」
Sub heading text: 「{サブテキスト}」
Body text: 「{本文テキスト（要約）}」

{セクション固有のビジュアル指示}

CTA button (if applicable): 「{ボタンテキスト}」 with {accent_color} background

Style: professional, modern, high-conversion landing page, Japanese text,
clean typography, strategic whitespace, --ar 9:16
```

### 出力

`output/lp-{slug}/prompts/section_001.txt` 〜 `section_007.txt` に保存。

---

## Step 5: NanoBanana画像順次生成

### 生成方法

各セクションのプロンプトをNanoBananaに送信して画像を順次生成する。

**重要：相対パスは `../../../` でプロジェクトルートに戻ること。**
nanobanana-proは `開発1/.claude/skills/nanobanana-pro/` にあるので、`../../../` で `開発1/` に到達する。

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{セクションNのプロンプト全文}" \
  --output "../../../output/lp-{slug}/sections/section_{NNN}.png" \
  --timeout 240
```

### 参考LPのデザインスタイルを反映する場合

参考LPのスクリーンショットを `--reference-image` で渡し、スタイルを抽出する:

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{セクションNのプロンプト全文}" \
  --reference-image "../../../output/lp-{slug}/research/{参考スクリーンショット}.png" \
  --output "../../../output/lp-{slug}/sections/section_{NNN}.png" \
  --timeout 240
```

### リサイズ（生成後必須）

リサイズはファイルのある場所にcdしてから実行する（日本語パスの文字化け回避）。

```bash
cd "C:\Users\baseb\dev\開発1\output\lp-{slug}\sections"

PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  "../../../.claude/skills/nanobanana-pro/.venv/Scripts/python.exe" -c "
from PIL import Image
img = Image.open('section_{NNN}.png')
w, h = img.size
new_w = 1080
new_h = int(h * (new_w / w))
img = img.resize((new_w, new_h), Image.LANCZOS)
img.save('section_{NNN}.png')
"
```

### 進捗トラッキング

各セクション生成完了後に `progress.json` を更新:

```json
{
  "slug": "{slug}",
  "total_sections": 7,
  "completed": [1, 2, 3],
  "failed": [],
  "timeout": [],
  "current": 4,
  "last_updated": "2026-03-07T12:00:00"
}
```

ログ出力形式: `[LP-GEN] Section {N}/{Total}: {status} ({elapsed}s)`

### 中断再開

`progress.json` が存在する場合、完了済みセクションをスキップして未完了分から再開する。
`progress.json` が存在しない or 破損している場合、セクション1から全セクション生成する。

---

## 出力先

```
output/lp-{slug}/
├── copy.md              # 全7セクション分のLPコピーテキスト
├── research/            # デザインリサーチ結果
│   ├── screenshot_*.png # 参考LPのスクリーンショット
│   └── analysis.json    # 配色・レイアウト分析結果
├── prompts/             # NanoBanana用プロンプト
│   ├── section_001.txt  # ファーストビュー
│   ├── section_002.txt  # 問題提起
│   ├── section_003.txt  # 解決策
│   ├── section_004.txt  # ベネフィット
│   ├── section_005.txt  # お客様の声
│   ├── section_006.txt  # 特典
│   └── section_007.txt  # CTA
├── sections/            # 生成されたLP画像（幅1080px）
│   ├── section_001.png
│   ├── section_002.png
│   ├── ...
│   └── section_007.png
├── report.md            # 生成結果レポート（ステータス・時間）
└── progress.json        # 進捗管理（中断再開用）
```

---

## UI要件（ツール化時）

### リアルタイム画像表示（プログレッシブ表示）

生成完了したセクションから順次UIに表示する。全セクション完了を待たない。

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◆ 実装意図                                                        │
│  ・実演（デモ）で見せる際に、生成過程が見えて映える                 │
│  ・待っている側がどこまで進んだか一目でわかる                       │
└─────────────────────────────────────────────────────────────────────┘
```

**動作イメージ:**

```
[生成開始]
  ┌──────────────────────┐
  │  Section 1 ✅ 完了    │  ← 画像が表示される
  │  [section_001.png]    │
  ├──────────────────────┤
  │  Section 2 🔄 生成中… │  ← プログレスゲージ表示
  │  [████████░░] 80%     │
  ├──────────────────────┤
  │  Section 3 ⏳ 待機    │  ← グレーアウト
  │  Section 4 ⏳ 待機    │
  │  Section 5 ⏳ 待機    │
  │  Section 6 ⏳ 待機    │
  │  Section 7 ⏳ 待機    │
  └──────────────────────┘
```

### プログレスゲージ

全体の進捗を示すゲージを常時表示:

```
LP生成中… [███████░░░░░░░] 3/7 セクション完了
```

**表示要素:**
- 全体進捗バー: `{完了数}/{全体数}` セクション
- 現在生成中のセクション名
- 経過時間
- 推定残り時間（過去のセクション生成時間から算出）

### 画像表示の仕様

- 生成完了 → リサイズ完了 → UIに画像を表示（リサイズ後の1080px幅で表示）
- 横幅は全セクション1080pxで統一
- 画像クリックで拡大表示（モーダル）
- セクション名ラベル付き（日本語: 「1. ファーストビュー」等）

### 状態遷移

```
⏳ 待機 → 🔄 生成中 → ✅ 完了
                    → ❌ 失敗（リトライボタン表示）
```

### 技術実装メモ

- WebSocket or SSE でバックエンドからフロントにリアルタイム通知
- `progress.json` をバックエンドが更新 → フロントがポーリング or push受信
- 画像はBase64 or URLで返却

---

## 関連スキル

| スキル | 用途 |
|--------|------|
| `nanobanana-pro` | Gemini NanoBanana で画像生成 |
| `nanobanana-prompts` | 画像プロンプト最適化の黄金ルール |
| `lp-analysis` | LP分析・改善 |
| `lp-design` | LP設計 |
| `covermaster-ss` | テキスト差し込み画像生成の参考パターン |

## 使用例

```
/lp-nanobanana AI活用セミナーのLPを作って
/lp-nanobanana この商品のランディングページを生成して
/lp-nanobanana 参考URL付きでLPを一括生成したい
```
