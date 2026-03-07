---
name: manga-produce-creator-ss
description: 電子書籍を漫画化することに特化したスキル。章構成を解析し、各章3-5ページの漫画を生成。重要ポイントを抽出して漫画化し、章の主旨を分かりやすく伝える。
---

# Manga Produce Creator - 書籍漫画化特化スキル

電子書籍 → 章ごと解析 → 重要ポイント抽出 → 漫画化（各章3-5ページ）。

## When to Use This Skill

- **「書籍を作った後に漫画作りたい」と言われた時**
- 「電子書籍を漫画化して」
- 「この本を漫画で分かるようにして」
- 「各章を漫画にして」
- ebook-creator-ss で作成した書籍の漫画化

## Do NOT Use for

- ゼロから漫画を作る → `manga-creator-ss` を使用
- 単発の漫画パネル1枚 → `nanobanana-pro` を使用
- キャラクターシートのみ → `custom-character` を使用
- アニメ動画制作 → `anime-production` を使用

## 📚 書籍漫画化の特化機能

### 1. 章ベースの構成
- 原稿に含まれる**各章を対象**とする
- 章タイトル（`## 第N章`）を自動検出
- 各章を独立した漫画シーンとして構成

### 2. ページ数の最適化
- **各章につき3-5ページ程度**の漫画を作成
- 全5章なら合計15-25ページ
- 章の長さに応じて3-5ページの範囲で調整

### 3. 重要ポイントの抽出
- 章全体の内容を、**重要度に応じて取捨選択**して構成してよい
- **すべてを網羅する必要はない**
- **章の主旨が伝わることを最重視**
- 具体例・エピソード・数字など、インパクトのある部分を優先

### 4. 教育的な内容の漫画化
- ビジネス書・ハウツー本など、教育的内容を分かりやすく
- データ・図解を漫画のコマに組み込む
- 「解説役」と「学ぶ役」の対話形式で構成

## Do NOT Use for

- 単発の漫画パネル1枚 → `nanobanana-pro` を使用
- キャラクターシートのみ → `custom-character` を使用
- 漫画制作のガイド・相談 → `ai-manga-generator` を使用
- アニメ動画制作 → `anime-production` を使用

## 参考フォルダ

テンプレート画像やリファレンス画像は以下に格納:

```
.claude/shared/manga-templates/
├── テンプレ1.jpg     # テンプレ1: ページ全体を使った1コマ
├── テンプレ2.jpg     # テンプレ2: 上下2分割（上段→下段）
├── テンプレ3.jpg     # テンプレ3: 上下2分割（上段小→下段大）
├── テンプレ4.jpg     # テンプレ4: 上下2分割（上段大→下段小）
├── テンプレ5.jpg     # テンプレ5: 上・中・下の3段構成
├── テンプレ6.jpg     # テンプレ6: 上段1コマ+下段左右2コマ
├── テンプレ7.jpg     # テンプレ7: 上段左右2コマ+下段1コマ
├── テンプレ8.jpg     # テンプレ8: 上段横長+中段左右+下段横長
├── テンプレ9.jpg     # テンプレ9: 上段横長+下段右縦長+左上下分割
└── テンプレ10.jpg    # テンプレ10: 上段横長+下段左縦長+右上下分割
```

## 全体フロー（5ステップ + 画像生成）

**前提: ebook-creator-ss が先に `output/{slug}/` フォルダを作成済み。**
**本スキルは同じフォルダに漫画関連ファイルを追加していく。**

```
Step 1: ストーリー構成案の作成
   │  ユーザーから原稿/文章を受け取る（必須）
   │  ★ 元原稿は output/{slug}/manuscript.md にある
   │  神話の法則で感情曲線設計
   │  書籍の長さに合わせたコマ数で細かいカット割り台本作成
   │  → 確認なしで即Step 2へ
   ▼
Step 2: キャラクター設計画
   │  2回以上登場する全キャラの設計画プロンプトを作成
   │  全キャラを1枚に並べた画像を nanobanana-pro で生成
   │  各キャラの外見プロンプトテキストをDBとして保存（後のStep 3で毎回使用）
   │  → 確認なしで即Step 3へ
   ▼
Step 3: ページ別プロンプト生成
   │  各ページのNanoBanana用プロンプトを英語で作成（セリフ部分のみ日本語）
   │  ★ 毎回キャラの外見詳細テキストを埋め込む（一貫性確保）
   │  全ページ分を一括出力
   │  → 確認なしで画像一括生成へ
   ▼
画像一括生成:
   │  nanobanana-pro で全ページ順次生成
   │  生成後 896x1200px にリサイズ
   │  進捗トラッキング + 中断再開対応
   ▼
Step 4: 表紙作成（cover-master-ss 連携）
   │  漫画ページ完成後、ユーザーに表紙作成を確認
   │  cover-master-ss スキルを呼び出し
   │  ★ all_characters.png を参照画像として自動提供
   │  キャラクターの外見情報をcover-master-ssに引き継ぎ
   ▼
Step 5: DOCX統合（原稿+漫画ページの統合Word）
   │  元の電子書籍原稿（manuscript.md）を読み込み
   │  各章の末尾に対応する漫画ページを挿入
   │  Pandoc で原稿テキスト+漫画統合DOCXに変換
   │  final_book.docx として出力
   ▼
完成！
```

### キャラクター一貫性の確保方法

**2つの方法を併用して一貫性を最大化する:**

#### 1. テキスト埋め込み（必須）
- Step 2で各キャラの外見プロンプト（英語テキスト）を定義する
- Step 3の英語プロンプト（Part B）で、登場キャラの外見テキストを毎回埋め込む
- 「Character name & details」フィールドに毎回同じ外見定義を記述する

#### 2. キャラクターシート画像の添付（`--attach-image`）
- nanobanana-pro の `--attach-image` を使い、キャラクターシート画像をGeminiチャットに添付する
- テキストだけでは回を重ねるうちにキャラの外見がブレるため、画像参照で補強する
- Step 2で生成した `all_characters.png` を毎回添付する

**注意:** `--reference-image` はスタイル抽出用（YAML分析→メタプロンプト生成）であり、キャラクター一貫性には使えない。`--attach-image` を使うこと。

---

## Step 1: ストーリー構成案の作成（書籍特化版）

### 最初に必ずやること

**ユーザーに原稿/文章の添付を求める。**

```
書籍を漫画化します。まず原稿（テキストまたはファイル）を添付してください。
各章を解析し、重要ポイントを抽出して漫画化します。
```

### 📚 書籍漫画化のストーリー構成ルール

1. **章ベースで構成**: `## 第N章` を検出し、各章を独立したシーンとして扱う
2. **各章3-5ページ**: 章の長さ・重要度に応じて3-5ページ（12-20コマ）で構成
3. **重要ポイント優先**: 章の主旨が伝わる重要な部分を抽出し、細部は省略してOK
4. **具体例を活用**: 数字・エピソード・実例など、インパクトのある部分を漫画化
5. **対話形式**: 解説役（先生）と学ぶ役（主人公）の会話で展開
6. **図解をコマに**: 原稿内の図解・データは漫画のコマとして視覚化

### 章ごとのページ配分ガイドライン

| 章の特徴 | ページ数 | 理由 |
|---------|---------|------|
| 導入章（第1章など） | 4-5ページ | 読者の共感を得る、世界観の提示が重要 |
| 具体例が多い章 | 5ページ | 実例・エピソードは漫画向き |
| 手順・ステップ系の章 | 3-4ページ | リスト形式は簡潔に |
| まとめ・結論の章 | 3ページ | 要点を凝縮 |

### 取捨選択の基準

**漫画化すべき内容（優先度高）:**
- 読者の悩み・共感ポイント
- 具体的な数字・報酬例
- 実績者のエピソード
- ビフォーアフターの対比
- 驚きや発見の瞬間

**省略してよい内容:**
- 細かい補足説明
- 繰り返しの内容
- 抽象的な理論
- 詳細なリスト（要点のみ抽出）

### コマ分割テクニック（必須遵守）

- **会話の1往復**（Aが話す→Bが話す）でページを分ける
- **3行以上の長ゼリフ**は、文節や句読点でページを分割する
- **「驚き」「沈黙」「強調」**などのリアクション単体で1ページ使う
- 場面転換、時間経過、視点変化でもページを分ける

### 📚 書籍漫画化の手順

1. **章構成の解析**
   - `## 第N章` のタイトルを抽出
   - 各章の小見出し（`### N.N`）も確認
   - 章ごとの文字数・内容量を把握

2. **重要ポイントの抽出**
   - 各章から、以下を優先的に抽出:
     - 読者の悩み・共感ポイント
     - 具体的な数字・報酬例
     - 実績者のエピソード
     - ビフォーアフター
     - 驚きや発見の瞬間
     - アクションステップ

3. **ページ配分の決定**
   - 全章数を確認
   - 各章3-5ページで配分
   - 重要な章は5ページ、まとめ章は3ページなど調整

4. **漫画シーンへの変換**
   - 抽出したポイントを漫画の「シーン」として構成
   - 対話形式で展開（主人公が学ぶ、先生が教える）
   - データや図解は漫画のコマとして視覚化

### 出力形式

`output/{slug}/story_structure.md` に保存:

```markdown
# 漫画ストーリー構成案（全{N}ページ）

タイトル：{書籍タイトル}

**原稿の章構成:**
- 第1章: {タイトル} → 漫画{X}ページ
- 第2章: {タイトル} → 漫画{Y}ページ
- 第3章: {タイトル} → 漫画{Z}ページ
...

**ページ配分の理由:**
{なぜこの配分にしたか、各章の重要度を簡潔に説明}

---

## シーン1：{第1章のタイトル}（ページ1〜{N}）

**原稿の要点:**
{第1章から抽出した重要ポイント}

**漫画化方針:**
{どのように漫画化するか。対話形式、ビフォーアフターなど}

場所：{場所}
登場人物：{キャラ名一覧}

**ページ1**
コマ1：{場面の詳細な描写。キャラの行動、表情、背景を具体的に記述。}
コマ2：{次のコマ。前のコマからの自然なつながりを明記。}
コマ3：{キャラ名}「{セリフ原文}」{キャラの動作や表情の補足}
コマ4：{リアクション。驚きの表情のアップなど。}「{セリフ}」

**ページ2**
...

## シーン2：{第2章のタイトル}（ページ{N+1}〜{M}）
...

（最後のページまで全て記述）
```

---

## Step 2: キャラクター設計画

### 概要

2回以上登場する**全キャラクター**について:
1. 全員を1枚に並べたキャラクターシート画像を生成する
2. 各キャラの外見プロンプトテキスト（英語）をDBとして保存する（Step 3で使用）

### キャラクターシート画像プロンプト

全キャラを1枚に横並びにした設計画:

```
(best quality, masterpiece:1.2), anime style, webtoon style, character sheet,
{N} people standing side by side, white background, full body, flat color, clean lines,
with text labels in katakana below each character identifying them,
({キャラ1カタカナ名}): {キャラ1の外見詳細を英語で}, text label below feet reads "{キャラ1カタカナ名}",
({キャラ2カタカナ名}): {キャラ2の外見詳細を英語で}, text label below feet reads "{キャラ2カタカナ名}",
...
```

### キャラクター外見プロンプトDB

各キャラの外見テキスト（英語）を `character_prompts.md` に保存する。
これがStep 3で毎回プロンプトに埋め込まれるマスターデータになる。

**注意: 以下はフォーマット例です。実際のキャラクターは書籍のテーマ・世界観に合わせて毎回新しく設計してください。前回のプロジェクトのキャラを引き継がないこと。**

```markdown
# キャラクター外見プロンプトDB

## {主人公名}（主人公）
{性別, 国籍, 年齢, 髪型・色, 目の色, 体型, 服装, アクセサリー, 全体の印象}
例: 1girl, Japanese, late 20s, medium-length straight black hair, large dark brown eyes, average build, wearing casual office clothes, warm approachable appearance

## {先生名}（先輩/メンター）
{性別, 国籍, 年齢, 髪型・色, 目の色, 体型, 服装, 全体の印象}
例: 1boy, Japanese, early 30s, neat dark hair, intelligent eyes, casual smart style, friendly and knowledgeable demeanor

## {マスコット名}（マスコット）
{テーマに合ったマスコットの外見。書籍の題材に関連するデザインにする}
例: cute small mascot character, round body, big friendly eyes, chibi proportions, kawaii style, theme-related design elements
```

### キャラクターシートプロンプトのルール

プロンプトの末尾に `--ar 16:9` を入れて横長で生成する。
横長にすることで全キャラが余裕を持って並び、Geminiがキャラの特徴を読み取りやすくなる。

### 画像生成

**重要：相対パスは `../../../` で開発フォルダのルートに戻ること。**
nanobanana-proは `開発1/.claude/skills/nanobanana-pro/` にあるので、`../../` だと `.claude/` で止まる。`../../../` で正しく `開発1/` に到達する。

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "{キャラクターシートプロンプト}, --ar 16:9" \
  --output "../../../output/{slug}/characters/all_characters.png" \
  --timeout 240
```

### リサイズ（生成後必須）

リサイズはファイルのある場所にcdしてから実行する（日本語パスの文字化け回避）。

```bash
cd "{開発フォルダ}/output/{slug}/characters"

PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  "../../../.claude/skills/nanobanana-pro/.venv/Scripts/python.exe" -c "
from PIL import Image
img = Image.open('all_characters.png')
img = img.resize((1600, 900), Image.LANCZOS)
img.save('all_characters.png')
"
```

---

## Step 3: ページ別プロンプト生成

### 概要

Step 1のストーリーを元に、各ページのNanoBanana用プロンプトを作成する。
プロンプトは**英語**で記述し、**セリフ・文字入れ部分のみ日本語**を含める。
**★ キャラの外見テキストはStep 2のDBから毎回同じものを埋め込む（一貫性確保の要）。**

**📚 書籍漫画化の重要ルール:**
- **全ページ分のプロンプトを必ず最後まで作成する**
- サンプルだけで終わらない（「残りも作成しますか？」と聞かない）
- Step 1で決めたページ数（15〜25ページ）すべてを完成させる
- 途中で確認を求めず、一気に全ページ分を出力する

全ページ分を `output/{slug}/page_prompts.md` に一括出力する。

### プロンプトテンプレート

```markdown
### Page {N}

**Page layout**
{ページ全体のシーン・感情の流れを英語で自然な文章で表現。
各コマがどのように展開・対比・連続しているかを簡潔かつ詳細にまとめる。}
**Reading order: Right-to-left (Japanese manga style)** ← 必須記載
Template: {テンプレ1〜10から選択}

---
重要: Panel番号は読む順番（1→2→3→4）。
横並びコマの場合、Panel1=右側、Panel2=左側。
---

**Panel1** ← 読む順番の1番目（横並びなら右側のコマ）
**Description** {シーンの説明を英語で}
**panel shape and size** {horizontal-large / vertical-medium / square-small 等}
**panel position** {top / middle-right / middle-left / bottom 等、コマの位置を明記}
**Character name & details** {キャラ名} — {★Step 2のDBの外見テキストをそのまま埋め込む}, (MUST match the character labeled '{キャラのカタカナ名}' in attached 'all_characters.png')
**Character expression** {表情を英語で}
**Character facing** {facing left / facing right / front}
**Character pose** {ポーズを英語で}
**Background** {背景を英語で}
**speech bubble** 「{日本語セリフそのまま}」
  ⚠️  1コマに複数の吹き出しがある場合の順序（厳守）:
  - 右側の吹き出しが最初（speech bubble 1）
  - 左側の吹き出しが次（speech bubble 2）
  - 例: speech bubble 1 (right side): 「右のセリフ」, speech bubble 2 (left side): 「左のセリフ」
  - 2人の会話の場合: 右側のキャラのセリフ → 左側のキャラのセリフ
**camera angle** {eye-level / top-down / low-angle / side view}
**art style** anime-style, modern manga illustration, soft light and smooth shading, delicate linework, expressive eyes, clean and bright overall tone, --ar 3:4
**color theme** {配色を英語で}

**Panel2** ← 読む順番の2番目（横並びなら左側のコマ）
**panel position** {位置を明記}
...
```

**注意（縦長生成の保証 — 必須）:**
- プロンプトの**先頭**に以下のブロックを必ず挿入すること：
  ```
  --ar 3:4 MUST generate in PORTRAIT orientation (taller than wide, 3:4 ratio). DO NOT use landscape.
  ```
- プロンプトの**末尾**にも `--ar 3:4` を含めること（二重保証）
- キャラクターシート（16:9横長）を添付するため、明示的にPORTRAIT指定しないと横長で出力されるリスクがある

**注意（キャラクター一貫性 + アートスタイル統一の保証 — 必須）:**
- プロンプトの**先頭**（`--ar 3:4` の直後）に以下のブロックを必ず挿入すること：
  ```
  CRITICAL CHARACTER REFERENCE: The attached image 'all_characters.png' is the official character reference sheet. You MUST faithfully reproduce each character's appearance exactly as shown in the reference.

  ART STYLE CONSISTENCY: You MUST also match the art style, color palette, line quality, shading technique, and overall visual touch of the attached 'all_characters.png'. All panels must look like they belong to the same manga series with the same illustrator.
  ```
- 各コマの `**Character name & details**` フィールドで `(MUST match the character labeled '{キャラカタカナ名}' in attached 'all_characters.png')` を記載し、どのキャラを参照するか明示する
- プロンプトの**末尾**に以下を追加する：
  ```
  anime-style, modern manga illustration, soft light and smooth shading, delicate linework, expressive eyes, clean and bright overall tone, full color manga page

  IMPORTANT: All characters MUST exactly match their appearance in the attached 'all_characters.png' reference sheet. The art style, line quality, coloring, and shading must also match the attached reference. --ar 3:4
  ```

### コマ割りテンプレート選択ルール

**1コマ:**
- テンプレ1: ページ全体を使った1コマ（見開き・クライマックス・タイトル）

**2コマ:**
- テンプレ2: 上下2分割（上段→下段）（会話・対比）
- テンプレ3: 上下2分割（上段小→下段大）（導入→メイン）
- テンプレ4: 上下2分割（上段大→下段小）（メイン→リアクション）

**3コマ:**
- テンプレ5: 上・中・下の3段構成（テンポのよい展開）
  ```
  ┌─────────┐
  │ Panel1  │ ← 上段
  ├─────────┤
  │ Panel2  │ ← 中段
  ├─────────┤
  │ Panel3  │ ← 下段
  └─────────┘
  ```

- テンプレ6: 上段1コマ+下段左右2コマ
  ```
  ┌───────────────┐
  │    Panel1     │ ← 上段
  ├────────┬──────┤
  │ Panel3 │Panel2│ ← 下段: 右(Panel2)→左(Panel3)
  └────────┴──────┘
  ```

- テンプレ7: 上段左右2コマ+下段1コマ
  ```
  ┌────────┬──────┐
  │ Panel2 │Panel1│ ← 上段: 右(Panel1)→左(Panel2)
  ├───────────────┤
  │    Panel3     │ ← 下段
  └───────────────┘
  ```

**4コマ:**
- テンプレ8: 上段横長+中段左右+下段横長
  ```
  ┌───────────────┐
  │    Panel1     │ ← 上段
  ├────────┬──────┤
  │ Panel3 │Panel2│ ← 中段: 右(Panel2)→左(Panel3)
  ├───────────────┤
  │    Panel4     │ ← 下段
  └───────────────┘
  ```

- テンプレ9: 上段横長+下段右縦長+左上下分割
  ```
  ┌────────────────┐
  │    Panel1      │ ← 上段
  ├─────┬──────────┤
  │Panel4│ Panel2   │ ← 下段: 右(Panel2)→左上(Panel3)→左下(Panel4)
  │─────│          │
  │Panel3│          │
  └─────┴──────────┘
  ```

- テンプレ10: 上段横長+下段左縦長+右上下分割
  ```
  ┌────────────────┐
  │    Panel1      │ ← 上段
  ├──────────┬─────┤
  │          │Panel2│ ← 下段: 右上(Panel2)→右下(Panel3)→左(Panel4)
  │  Panel4  │─────│
  │          │Panel3│
  └──────────┴─────┘
  ```

### テンプレートバリエーション強制ルール（必須遵守）

```
┌─────────────────────────────────────────────────────────────────────┐
│  同じテンプレを3ページ連続で使用することは絶対禁止                  │
│  全体で最低4種類以上のテンプレートを使い分けること                  │
└─────────────────────────────────────────────────────────────────────┘
```

**ルール1: 連続使用制限**
- 同じテンプレートは**最大2ページ連続**まで。3ページ連続は禁止
- テンプレ8を3ページ連続で使いたい場合、間に別テンプレを1つ挟む

**ルール2: 最低バリエーション数**
- 全体ページ数に応じた最低テンプレ種類数:

| 総ページ数 | 最低テンプレ種類数 |
|-----------|------------------|
| 5-10ページ | 3種類以上 |
| 11-15ページ | 4種類以上 |
| 16-20ページ | 5種類以上 |
| 21ページ以上 | 6種類以上 |

**ルール3: シーン別テンプレ推奨マッピング**

| シーンの内容 | 推奨テンプレ | 理由 |
|-------------|------------|------|
| 章の冒頭・導入 | テンプレ3（上小+下大）| 小さい導入→大きいメインの流れ |
| 会話が中心 | テンプレ5（3段）/ テンプレ7（2+1）| テンポよく会話を展開 |
| 説明・解説シーン | テンプレ8（4コマ）/ テンプレ6（1+2）| 情報量を確保 |
| 驚き・衝撃の瞬間 | テンプレ1（全面1コマ）/ テンプレ4（大+小）| インパクト最大化 |
| クライマックス | テンプレ1（全面）/ テンプレ9 / テンプレ10 | 変則レイアウトで緊張感 |
| まとめ・振り返り | テンプレ2（上下均等）/ テンプレ5（3段）| 落ち着いた構成 |
| 感動・余韻 | テンプレ4（上大+下小）/ テンプレ1 | 余白で感情を表現 |

**ルール4: ページ配分の目安（19ページの場合）**
```
テンプレ1（1コマ）: 1-2ページ（冒頭タイトルやクライマックス）
テンプレ2-4（2コマ）: 3-4ページ（導入・対比・リアクション）
テンプレ5-7（3コマ）: 4-5ページ（会話・テンポ重視）
テンプレ8-10（4コマ）: 8-10ページ（情報量が多いシーン）
```

### 読み順ルール（厳守）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️  重要: すべての漫画は右→左読み（日本式）で作成すること        │
└─────────────────────────────────────────────────────────────────────┘
```

**基本ルール:**
- **日本の漫画形式**: 右上から左下へ
- **横並びのコマ**: 必ず「右側」が先、「左側」が後
- **Panel番号**: 読む順番を示す（Panel1=最初に読む、Panel2=次に読む）
- **位置と番号は別**: Panel1が左側にあることもある（読む順番が1番目という意味）
- **1コマ内の吹き出し順序**: 複数の吹き出しがある場合、右側の吹き出しが最初、左側の吹き出しが次
  - 例: 1コマに2人が会話 → 右側キャラのセリフが先、左側キャラのセリフが後

**具体例（テンプレ8の場合）:**
```
┌─────────────────────────┐
│   Panel1（上段横長）      │  ← 最初に読む
├───────────┬─────────────┤
│  Panel3   │   Panel2    │  ← Panel2（右）を先に読み、次にPanel3（左）
│ (中段左)  │  (中段右)   │
├─────────────────────────┤
│   Panel4（下段横長）      │  ← 最後に読む
└─────────────────────────┘

読み順: Panel1 → Panel2（右） → Panel3（左） → Panel4
```

**Page layoutに必須記載:**
- すべてのページのPage layout説明に「Right-to-left reading order (Japanese manga style)」を含めること

### 絶対遵守ルール

1. **セリフ完全維持**: 原稿のセリフは一文字も要約・省略・変更しない
2. **サイズ**: 896x1200px
3. **必ずフルカラー**: 白黒漫画は絶対に禁止
4. **（）の中の言葉**は吹き出しに記載しない
5. **同じ言葉を二回以上**吹き出しに記載しない
6. **1コマ内の吹き出し順序**: 右側の吹き出しが1番目、左側の吹き出しが2番目（右→左読み）

### オノマトペ（活用する）

ぱぁっ / パァァ / ビクッ / ギクッ / キュン / イライラ / じーっ / ガーン / むすっ / テクテク / ダダダダ / ガチャ / チラッ / カタカタ / シーン / ドキドキ / ザワザワ / キラキラ / パチパチ / ゴゴゴ

### 背景パターン（30+種類から選択）

水玉模様 / 半円 / ドット模様 / フラッシュエフェクト / ストライプ / グラデーション / 幾何学模様 / 集中線 / 放射線 / 斜線ハッチング / 花びら散り / 泡エフェクト / 暗転 / 白飛び / ぼかし背景 / 都市風景 / 室内 / 自然風景 / ハートパターン / 星パターン / 雷エフェクト / 炎エフェクト / パステルグラデーション / モノクロ反転 / セピア調 / 夕焼け色 / 雨粒エフェクト / 雪結晶 / 桜吹雪 / 紅葉 / デジタルエフェクト / 回路パターン / 光の粒子

---

## 画像生成

### 生成方法

各ページの英語プロンプト（Part B）全体を1つのテキストとしてnanobanana-proに送信する。

**重要：相対パスは `../../../` でプロジェクトルートに戻ること。**

```bash
cd "C:\Users\baseb\dev\開発1\.claude\skills\nanobanana-pro"

PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/run.py image_generator.py \
  --prompt "--ar 3:4 MUST generate in PORTRAIT orientation (taller than wide, 3:4 ratio). DO NOT use landscape. CRITICAL CHARACTER REFERENCE: The attached image 'all_characters.png' is the official character reference sheet. You MUST faithfully reproduce each character's appearance exactly as shown in the reference. ART STYLE CONSISTENCY: You MUST also match the art style, color palette, line quality, shading technique, and overall visual touch of the attached 'all_characters.png'. All panels must look like they belong to the same manga series with the same illustrator. {ページNの英語プロンプト全文} anime-style, modern manga illustration, soft light and smooth shading, delicate linework, expressive eyes, clean and bright overall tone, full color manga page. IMPORTANT: All characters MUST exactly match their appearance in the attached 'all_characters.png' reference sheet. The art style, line quality, coloring, and shading must also match the attached reference. --ar 3:4" \
  --attach-image "../../../output/{slug}/characters/all_characters.png" \
  --output "../../../output/{slug}/panels/page_NNN.png" \
  --timeout 240
```

**プロンプト構造（必須）:**
```
[HEAD] --ar 3:4 MUST generate in PORTRAIT orientation... + CRITICAL CHARACTER REFERENCE... + ART STYLE CONSISTENCY...
[BODY] ページNの英語プロンプト全文（各コマのキャラ詳細含む）
[TAIL] IMPORTANT: All characters must match... + art style must match... + --ar 3:4
```

`--attach-image` でキャラクターシート画像（`all_characters.png`）を毎回Geminiに添付することで、キャラの外見一貫性を確保する。テキスト埋め込み + 画像添付の二重方式でブレを最小化する。

### 生成後の検証（必須）

生成された画像が**縦長（portrait）**であることを必ず検証する。
横長で出力された場合はリサイズせず、**再生成する**。

```bash
cd "{開発フォルダ}/output/{slug}/panels"

PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  "../../../.claude/skills/nanobanana-pro/.venv/Scripts/python.exe" -c "
from PIL import Image
img = Image.open('page_NNN.png')
w, h = img.size
print(f'Size: {w}x{h}')
if w > h:
    print('ERROR: LANDSCAPE detected. Must regenerate this page.')
elif (w, h) != (896, 1200):
    img = img.resize((896, 1200), Image.LANCZOS)
    img.save('page_NNN.png')
    print('Resized to 896x1200')
else:
    print('OK: Already 896x1200')
"
```

**ルール:**
- 横長（width > height）→ **リサイズ禁止、再生成する**
- 縦長だがサイズが違う（例: 765x1024）→ 896x1200にリサイズOK
- すでに896x1200 → そのまま

### 出力ファイル名

- `panels/page_001.png`, `panels/page_002.png`, ... `panels/page_NNN.png`

### バッチ生成

全ページを順次生成。10枚ごとに進捗報告。
中断後はまだ生成されていないページから再開可能。
横長で出力されたページは自動検出し、再生成キューに追加する。

---

## Step 4: 表紙作成（cover-master-ss 連携）

### 概要

漫画ページの画像一括生成が完了した後、**表紙作成**に進む。
漫画で生成したキャラクターシート（`all_characters.png`）を参照画像として活用し、
キャラクターの外見を表紙にも一貫して反映する。

### 手順

#### 1. ユーザーに表紙作成を確認

漫画ページ生成完了後、以下を確認する:

```
漫画ページの生成が完了しました！

続けて表紙を作成しますか？
漫画のキャラクターを活かした表紙を cover-master-ss で作ります。
```

AskUserQuestion で確認:
- 「表紙を作る」→ Step 4 を続行
- 「今はスキップ」→ Step 4 をスキップして完了

#### 2. cover-master-ss に引き継ぐ情報

cover-master-ss を呼び出す際に、以下の情報を自動的に提供する:

| 情報 | 引き継ぎ元 | cover-master-ss での用途 |
|------|-----------|------------------------|
| 書籍タイトル | Step 1 のストーリー構成案 | Step 1: ヒアリング（タイトル） |
| ジャンル・ターゲット | 元の電子書籍情報 | Step 1: ヒアリング |
| キャラクター画像 | `characters/all_characters.png` | Step 2: 参照画像 |
| キャラクター外見テキスト | `character_prompts.md` | Step 2: キャラ描写 |
| 漫画ページサンプル | `panels/page_001.png` 等 | Step 2: スタイル参考 |

#### 3. cover-master-ss の呼び出し

Skill ツールで `cover-master-ss` を呼び出し、以下を伝える:

```
cover-master-ss で表紙を作成します。

■ 書籍情報:
- タイトル: {書籍タイトル}
- ジャンル: {ジャンル}
- ターゲット: {ターゲット読者}

■ 参照画像（漫画から引き継ぎ）:
- キャラクターシート: output/{slug}/characters/all_characters.png
  → このキャラクターの外見を表紙にも反映してください

■ キャラクター外見:
{character_prompts.md の内容}

■ 漫画スタイルとの統一:
- 漫画ページと同じアートスタイル・色彩で表紙を作成
- スタイルC（マンガ・アニメ型）を推奨
```

cover-master-ss のフローに従い、スタイル選択→カラーパレット→YAML生成→画像生成まで進める。

#### 4. 表紙画像の保存

cover-master-ss で生成された表紙画像は以下に保存する:

```
output/{slug}/
├── cover.png                   # 表紙画像（本文埋め込み用）
└── cover_prompt_amazon.md      # Amazon KDP提出用プロンプト
```

電子書籍と漫画は同じ `output/{slug}/` フォルダ内にあるため、
表紙画像（cover.png）は自動的に共有される。

---

## Step 5: DOCX統合（原稿+漫画ページの統合Word）

### 概要

**元の電子書籍の原稿テキストと漫画ページを統合した1つのWordファイル（DOCX）を作成する。**
漫画画像だけを並べるのではなく、各章の文章の後に対応する漫画ページを挿入し、
「テキストで学ぶ → 漫画で理解を深める」という構成の完成品を出力する。

### 前提条件

- 元の電子書籍原稿（`output/{slug}/manuscript.md`）が同じフォルダに存在すること
- Step 1の `story_structure.md` に章→漫画ページの対応が記載されていること
- 全漫画ページ画像が `panels/` フォルダに揃っていること
- 表紙画像（`cover.png`）が生成済みであること

### 手順

#### 1. 章→漫画ページの対応表を作成

`story_structure.md` の「原稿の章構成」セクションから、各章に対応する漫画ページ番号を抽出する。

例:
```
第1章 → 漫画ページ 1〜4
第2章 → 漫画ページ 5〜7
第3章 → 漫画ページ 8〜11
第4章 → 漫画ページ 12〜16
第5章 → 漫画ページ 17〜19
```

#### 2. 統合Markdownファイルの生成

元の原稿（`manuscript.md`）をベースに、各章の末尾に対応する漫画ページを挿入した
統合Markdownファイルを生成する。

`output/{slug}/manga_compiled.md` を作成:

```markdown
![表紙](cover.png){ width=100% }

\newpage

## はじめに

{はじめにの本文テキスト}

\newpage

## 第1章 {章タイトル}

{第1章の本文テキスト（節・小見出し含む）}

\newpage

### 第1章 まんがでわかる

![Page 1](panels/page_001.png){ width=100% }

\newpage

![Page 2](panels/page_002.png){ width=100% }

\newpage

![Page 3](panels/page_003.png){ width=100% }

\newpage

![Page 4](panels/page_004.png){ width=100% }

\newpage

## 第2章 {章タイトル}

{第2章の本文テキスト}

\newpage

### 第2章 まんがでわかる

![Page 5](panels/page_005.png){ width=100% }

\newpage

...（全章分繰り返し）

\newpage

## おわりに

{おわりにの本文テキスト}
```

**統合ルール:**
- 表紙（cover.png）を最初に配置
- 元の原稿のテキスト構造（見出し・段落・箇条書き）を維持する
- 元の原稿に含まれる図解画像（`images/` フォルダ内）も維持する
  - 同じフォルダ内の `images/` を参照するため、パス修正は不要
- 各章の本文テキストの後に「### 第N章 まんがでわかる」の見出しを追加
- 見出しの後に対応する漫画ページを順番に挿入
- 各漫画ページの間に `\newpage`（改ページ）を挿入
- すべての画像に `{ width=100% }` を付与
- 画像行の前後に必ず空行1行ずつ
- 「はじめに」と「おわりに」には漫画を挿入しない

#### 3. Pandoc でDOCX変換

```bash
cd "output/{slug}"

pandoc manga_compiled.md \
  -o final_book.docx \
  --from markdown \
  --to docx \
  --resource-path=. \
  --standalone \
  --dpi=150
```

**Pandocが利用できない場合のフォールバック:**

python-docxを使用してDOCXを生成する。
Markdownのヘッダー（`##`, `###`）をWordの見出しスタイルに変換し、
画像を埋め込み、`\newpage` を改ページに変換する。

#### 4. 出力確認

- `final_book.docx` が生成されたことを確認
- ファイルサイズが妥当か確認（原稿テキスト+図解+漫画ページで30-50MB程度が目安）
- テキストと漫画が正しい章順で統合されているか確認

### 出力ファイル

```
output/{slug}/
├── manga_compiled.md           # 中間Markdown（原稿+漫画統合済み）
└── final_book.docx         # ★ 最終成果物（原稿テキスト+漫画ページ統合Word）
```

---

## 出力先

**電子書籍（ebook-creator-ss）と同じフォルダ（`output/{slug}/`）に漫画関連ファイルを追加する。**
1冊の書籍タイトルにつき1フォルダで、原稿・図解・漫画すべてを統合管理する。

```
output/{slug}/
│
│  ── 電子書籍スキル（ebook-creator-ss）が先に生成済み ──
├── manuscript.md             # 電子書籍原稿（Markdown）
├── manuscript_raw.md         # 中間ファイル
├── manuscript.docx           # 原稿+図解のみのWord（中間成果物）
├── research.md               # リサーチ結果
├── images/                   # 図解画像（40〜60枚）
│   ├── ch1_header.png
│   ├── ch1_img1.png
│   └── ...
│
│  ── 本スキル（manga-produce-creator-ss）が追加するファイル ──
├── story_structure.md        # ストーリー構成案（全コマ詳細）
├── character_prompts.md      # キャラクター外見プロンプトDB
├── page_prompts.md           # 全ページのプロンプト
├── characters/
│   └── all_characters.png    # 全キャラ並んだ設計画（1600x900px, 16:9横長）
├── panels/                   # 漫画ページ画像（896x1200px）
│   ├── page_001.png
│   ├── page_002.png
│   └── ...
├── cover.png                 # 漫画風表紙（Step 4で生成）
├── cover_prompt.md           # 表紙プロンプト Version A + B
├── cover_prompt_amazon.md    # Amazon KDP用プロンプト
├── manga_compiled.md         # 中間Markdown：原稿テキスト+漫画統合済み
├── final_book.docx           # ★ 最終成果物（原稿+図解+漫画の統合Word）
└── generate_panels.py        # バッチ生成スクリプト（オプション）
```

**最終成果物は `final_book.docx`**。
- 元の原稿テキスト + 図解画像 + 各章末尾に漫画ページを挿入した統合Word
- `manuscript.docx`（原稿+図解のみ）は中間成果物として残る

---

## 関連スキル

| スキル | 用途 |
|--------|------|
| `nanobanana-pro` | Gemini NanoBanana で画像生成 |
| `custom-character` | キャラクター設計パターン参考 |
| `nanobanana-prompts` | 画像プロンプト最適化の黄金ルール |
| `cover-master-ss` | Step 4: 表紙作成（キャラシートを参照画像として連携） |
| `doc-convert-pandoc` | Step 5: Markdown → DOCX 変換 |
| `ebook-creator-ss` | 電子書籍作成（漫画化の前工程） |

## 使用例

```
# 電子書籍作成後に
「書籍を作った後に漫画作りたい」
「この電子書籍を漫画化して」
「各章を漫画で分かるようにして」

# ebook-creator-ss との連携
/ebook-creator-ss でテーマの書籍作成
  ↓
/manga-produce-creator-ss で書籍を漫画化
```

## 📖 書籍漫画化の実行例

```
ユーザー: 「書籍を作った後に漫画作りたい」

AI: manga-produce-creator-ss スキルを起動
  1. 原稿ファイルを読み込む（manuscript.md）
  2. 章構成を解析（## 第1章、## 第2章...）
  3. 各章の重要ポイントを抽出
  4. 各章3-5ページの漫画ストーリーを構成（Step 1）
  5. キャラクター設計（Step 2）
  6. ページ別プロンプト生成（Step 3）
  7. 画像一括生成（15-25ページ）
  8. cover-master-ss で表紙作成（Step 4）
     → キャラクターシートを参照画像として自動連携
     → 漫画と統一感のある表紙を生成
  9. 原稿テキスト+漫画ページをDOCXに統合（Step 5）
     → 元の電子書籍原稿に各章の漫画ページを挿入
     → Pandocで原稿+漫画統合Word出力
```
