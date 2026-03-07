---
name: line-banner-ss
description: LINE登録を促すバナー画像のYAMLプロンプトを自動生成する。4つのビジュアルスタイル（漫画風/実写風/ミニマル/ポップ）に対応し、どんなテーマ・サービスでも使える汎用メタプロンプト。NanoBanana Pro用YAML形式で出力する。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, Task
---

# LINE Banner v2.0 - LINE登録バナーYAMLプロンプト生成スキル

どんなテーマ・ジャンル・ビジュアルスタイルでも「特典が主役」×「LINE登録を強力に促す」バナー画像のNanoBanana Pro用YAMLプロンプトを生成する。

## When to Use This Skill

- 「LINEバナーを作って」「LINE登録の画像」「LINE誘導バナー」
- 「LINE登録を促すバナー」「LINEの特典バナー」
- 「line-banner」「ラインバナー」
- LINE登録に誘導するための縦長バナー画像が必要な時

## 全体フロー

```
Step 1: ヒアリング（テーマ/特典/ターゲット/スタイル選択）
  ▼
Step 2: 入力情報の整理（YAML形式）
  ▼
Step 3: スタイル別デザイン方針の確定
  ▼
Step 4: YAMLプロンプト生成 + 戦略コンセプト出力
  ▼
(任意) Step 5: nanobanana-pro で画像生成
```

---

## Step 1: ヒアリング（必須）

プロンプト生成の前に、必ずユーザーに以下を確認する：

```
LINE登録バナーを作成します。以下の情報を教えてください：

1. 【テーマ】何のLINE登録ですか？
   （例: 書籍の特典、オンライン講座、コンサル、サービス紹介、物販 等）

2. 【特典/プレゼント名】LINE登録で何がもらえますか？
   （例: 〇〇スタートキット、無料PDF、動画講座、割引クーポン 等）

3. 【特典の中身】具体的に何が含まれますか？（3つ程度）
   （例: ガイドPDF、テンプレート集、動画チュートリアル 等）

4. 【ターゲット】誰に届けたいですか？
   （例: 30代会社員、40-50代女性、副業初心者、経営者 等）

5. 【ターゲットの悩み】その人が抱えている悩みは？
   （例: 何から始めればいいかわからない、時間がない 等）

6. 【キャッチコピー】一言で刺さるフレーズは？
   （例: もう迷わない！、今日から変わる 等）

7. 【ビジュアルスタイル】どんな雰囲気にしますか？
   A) 漫画風（集中線・吹き出し・効果音）
   B) 実写風（フォトリアル・高級感・プロ撮影風）
   C) ミニマル（シンプル・余白・洗練）
   D) ポップ（カラフル・イラスト・元気）

8. 【キャラクター / 人物】使いたいキャラや人物像はありますか？（任意）
   （画像があれば貼り付けてください）

9. 【色テーマ】好みの色はありますか？（任意 / なければ自動提案）
```

---

## Step 2: 入力情報の整理

ユーザーの回答を以下の形式に整理する：

```yaml
input:
  theme: "{テーマ}"
  product_name: "{商品・サービス名（あれば）}"
  gift_name: "{特典/プレゼント名}"
  gift_items:
    - "{特典内容1}"
    - "{特典内容2}"
    - "{特典内容3}"
  target: "{ターゲット}"
  pain_point: "{ターゲットの悩み}"
  catchcopy: "{キャッチコピー}"
  visual_style: "{A/B/C/D}"
  character: "{キャラクター/人物（任意）}"
  character_image: "{参照画像（任意）}"
  color_theme: "{色テーマ（任意）}"
```

---

## Step 3: スタイル別デザイン方針

### ビジュアルスタイル早見表

| | A) 漫画風 | B) 実写風 | C) ミニマル | D) ポップ |
|--|---------|---------|-----------|---------|
| **背景** | 集中線+グラデ | 写真風テクスチャ+ぼかし | 単色/2色グラデ | カラフル幾何学模様 |
| **特典タイトル** | 黄金3D+集中線 | 白/金の洗練フォント | 細身モダンフォント | 太字+影+カラフル |
| **キャッチコピー** | ギザギザ吹き出し | テキストオーバーレイ | 小さめ上品テキスト | 丸い吹き出し |
| **エフェクト** | 集中線・効果音・キラキラ | レンズフレア・ぼかし・光 | なし/最小限 | 星・紙吹雪・虹 |
| **人物/キャラ** | デフォルメ・漫画キャラ | リアルな人物写真風 | アイコン/シルエット | フラットイラスト |
| **ムード** | 熱い！ワクワク！ | 高級・信頼・プロ | 洗練・知的・クリーン | 楽しい・元気・親しみ |
| **最適テーマ** | 書籍・教材・副業 | コンサル・投資・美容 | ビジネス・SaaS | 趣味・生活・子育て |

### 色テーマ自動提案（ユーザー指定がない場合）

| テーマ | 背景メイン | アクセント | 心理効果 |
|--------|-----------|----------|---------|
| 書籍・教材 | #1A237E 紺 | #00BCD4 シアン | 信頼・知性 |
| 副業・稼ぐ系 | #1B2A4A 紺 | #FFD700 金 | 富・成功 |
| 美容・健康 | #4A0E4E 紫 | #FF6B9D ピンク | 美・癒し |
| ビジネス・コンサル | #0D1B2A 黒紺 | #00B4D8 ブルー | 権威・先進性 |
| 料理・生活 | #2D5016 緑 | #FF8C00 オレンジ | 温かみ・活力 |
| 恋愛・人間関係 | #4A1942 ワイン | #FF4081 ローズ | ロマンス・情熱 |
| 子育て・教育 | #1565C0 青 | #FFC107 黄 | 安心・希望 |
| 投資・金融 | #1A1A2E 黒 | #D4AF37 金 | 高級感・信頼 |
| 趣味・エンタメ | #FF6F00 オレンジ | #7C4DFF 紫 | 楽しさ・興奮 |

---

## Step 4: YAMLプロンプト生成

### 出力フォーマット

```
━━━ 戦略コンセプト ━━━
■ テーマ: [テーマ名]
■ ビジュアルスタイル: [選択スタイル]
■ 視覚的フック: [なぜ特典が際立つのか]
■ 演出の意図: [スタイル別の演出意図]
■ ボタンの意図: [LINE登録への視覚的誘導]

━━━ NanoBanana Pro 用プロンプト (YAML) ━━━
{YAMLプロンプト全文}
```

---

### 共通テンプレート（全スタイル共通骨格）

**スタイル別に `type` / `style_direction` / `text_elements` のstyle / `background` を差し替える。**
**固定要素（サイズ・LINEボタン・特典タイトル最優先）は全スタイル共通。**

```yaml
# LINE登録バナー - {theme}: {gift_name}
# NanoBanana Pro YAML prompt / {visual_style}バナーデザイン

type: "{スタイル別type文 - 下記スタイル別指示を参照}"
quality: professional marketing banner, extremely high visual impact
size: 800x1280 pixels, portrait vertical layout
importance: MUST be 800x1280 VERTICAL layout

# === スタイル方向性 / Style Direction ===
style_direction: "{スタイル別の方向性 - 下記参照}"

# === 固定要素 / Fixed Elements（全スタイル共通） ===
fixed_elements:
  line_button:
    position: "absolute bottom of image, within bottom 10%"
    style: "large rounded rectangle button spanning 80% width, centered"
    color: "LINE official green (#06C755), slightly glossy"
    icon: "LINE official logo (white speech bubble) on left side"
    text: "今すぐLINEで特典を受け取る"
    text_color: "bold white (#FFFFFF)"
  annotation:
    text: "※ご登録後、すぐにプレゼントが届きます"
    position: "directly below button, centered"
    color: "light gray or white, small font"

# === テキスト配置 / Text Rendering ===
text_elements:
  gift_title:
    text: "{gift_name}"
    position: "center of image, approximately 35-50% from top"
    style: "{スタイル別 - 下記参照}"
    font_size: "LARGEST text on banner, dominant visual element"

  catchcopy:
    text: "{catchcopy}"
    position: "upper area 15-25%"
    style: "{スタイル別 - 下記参照}"

  gift_list:
    items: ["{特典1}", "{特典2}", "{特典3}"]
    position: "below gift_title, approximately 55-70% from top"
    style: "{スタイル別 - 下記参照}"

# === ビジュアル / Visual ===
visual:
  character_or_element:
    description: "{キャラ/人物/代替演出の記述}"
    position: "{配置}"

# === 構図と配色 / Composition & Colors ===
composition:
  layout: "vertical flow: catchcopy top → gift title center → gift list → LINE button bottom"
  background:
    base: "{スタイル別背景}"
    effects: ["{スタイル別エフェクト}"]

colors:
  background: "{#HEX}"
  accent: "{#HEX}"
  gold: "#FFD700 (特典タイトル用)"
  line_green: "#06C755 (固定)"

# === 制約 / Constraints ===
constraints:
  - "Image size MUST be 800x1280 pixels, vertical portrait"
  - "LINE button MUST be at bottom, clearly visible"
  - "Gift title MUST be the largest and most prominent element"
  - "All Japanese text MUST be clearly readable"
  - "Background MUST NOT be white"
```

---

## スタイル別差し替え指示

### A) 漫画風

```yaml
type: "manga-style promotional banner for LINE registration with Japanese text"
style_direction: "漫画の見開きクライマックスページのような構図, dramatic manga effects"

text_elements:
  gift_title:
    style: "enormous 3D golden text with metallic shine, 集中線 speed lines radiating from behind"
  catchcopy:
    style: "inside a bold manga speech bubble with spiky edges (ギザギザ吹き出し)"
  gift_list:
    style: "each item in a small manga-panel style box, ポップなデザイン"

background:
  base: "{テーマ色} gradient"
  effects: ["集中線 speed lines from center", "キラキラ sparkle particles", "manga halftone dots at 10%"]

# キャラクターありの場合
visual:
  character_or_element:
    description: "Based on '{キャラ名}' from uploaded images: {外見}. Dynamic manga pose presenting the gift."
# キャラクターなしの場合
visual:
  character_or_element:
    description: "glowing treasure chest bursting open with golden light, manga-style explosion effects"
```

### B) 実写風

```yaml
type: "photorealistic professional banner for LINE registration with Japanese text"
style_direction: "high-end professional photo shoot aesthetic, luxury brand quality, studio lighting"

text_elements:
  gift_title:
    style: "elegant serif or sans-serif font, white or gold with subtle shadow, refined and luxurious"
  catchcopy:
    style: "clean text overlay with thin accent line, sophisticated typography"
  gift_list:
    style: "minimal rounded tags with frosted glass effect, modern and clean"

background:
  base: "{テーマ色} with subtle bokeh or gradient blur"
  effects: ["soft lens flare", "subtle light particles", "depth-of-field blur"]

# 人物ありの場合
visual:
  character_or_element:
    description: "photorealistic {ターゲット層に近い人物}, professional studio lighting, confident expression, holding or gesturing toward the gift"
# 人物なしの場合
visual:
  character_or_element:
    description: "elegant product mockup (tablet/book/box) on marble surface with soft studio lighting, premium feel"
```

### C) ミニマル

```yaml
type: "minimalist clean banner for LINE registration with Japanese text"
style_direction: "less is more, generous white space, refined typography, 洗練されたデザイン"

text_elements:
  gift_title:
    style: "thin modern font, single accent color, no 3D effects, clean and readable"
  catchcopy:
    style: "small uppercase text with thin line separator, understated elegance"
  gift_list:
    style: "simple bulleted list with minimal icons, airy spacing"

background:
  base: "solid {テーマ色} or gentle two-tone gradient"
  effects: ["none or single subtle geometric accent"]

visual:
  character_or_element:
    description: "simple flat icon or geometric shape representing the gift concept, minimal line art"
```

### D) ポップ

```yaml
type: "colorful pop-style banner for LINE registration with Japanese text"
style_direction: "fun, energetic, colorful, フレンドリーで親しみやすいデザイン"

text_elements:
  gift_title:
    style: "bold rounded font, multi-color gradient or rainbow effect, playful drop shadow"
  catchcopy:
    style: "inside a rounded pastel speech bubble, friendly and approachable"
  gift_list:
    style: "colorful pill-shaped tags, each a different accent color"

background:
  base: "bright {テーマ色} with geometric patterns (dots, waves, confetti)"
  effects: ["confetti or paper pieces", "rainbow accents", "star sparkles"]

# イラストありの場合
visual:
  character_or_element:
    description: "flat illustration style character, bright colors, waving cheerfully, フラットイラスト風"
# イラストなしの場合
visual:
  character_or_element:
    description: "colorful gift box with ribbons and confetti bursting out, celebration mood"
```

---

## Step 5: 画像生成（任意）

ユーザーが希望すれば、nanobanana-proスキルで画像を生成する。

### 生成前の注意
- ユーザーにGeminiログイン確認を求める
- 思考モードが有効か確認を推奨
- 生成結果が気に入らない場合は、プロンプトを微調整して再生成

---

## 品質ルール

### 固定要素（全スタイル共通・変更不可）
1. **サイズ**: 800x1280（縦長）
2. **LINEボタン**: 最下部、緑(#06C755)、公式ロゴ付き
3. **特典タイトル**: 画面最大要素（スタイルに合った装飾で）
4. **注釈テキスト**: ボタン下「※ご登録後、すぐにプレゼントが届きます」
5. **constraintは5個以内**: 本当に重要なものだけ

### NanoBanana Pro最適化
1. **YAML形式**: 構造化データでGeminiの理解を最大化
2. **日英ミックス**: 日本語でコンテキスト、英語で技術指示
3. **簡潔記述**: 1要素2-3行（過剰なプロパティ分解はしない）
4. **色はHEX値+色名**: 両方記載
5. **constraint最小**: 5個以内

### 参照画像の記述ルール
- 添付画像を見て、外見・色・構図を**英語で**簡潔に描写（1-2行）
- 「from uploaded images」で参照を明示
- キャラデザインを勝手に変えない（参照画像が正）

---

## 使用例

### 例1: 書籍特典 × 漫画風
```
「この本のLINE登録バナーを漫画風で作って」
→ ヒアリング → 集中線+吹き出し+キャラが特典を見せつける構図
```

### 例2: コンサル × 実写風
```
「コンサル用のLINE登録バナーを実写風で」
→ ヒアリング → 高級スタジオ撮影風、プロフェッショナルな雰囲気
```

### 例3: SaaS × ミニマル
```
「SaaSの無料トライアルバナーをミニマルで」
→ ヒアリング → 余白たっぷり、洗練タイポグラフィ
```

### 例4: 子育て教材 × ポップ
```
「子育て講座のLINEバナーをポップで」
→ ヒアリング → カラフル紙吹雪、親しみやすいイラスト
```

---

## 関連スキル

| スキル | 連携 |
|--------|------|
| `nanobanana-pro` | 画像生成の実行 |
| `nanobanana-prompts` | プロンプト最適化の参考 |
| `cover-master-ss` | Kindle表紙プロンプト生成 |
