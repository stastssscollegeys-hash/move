---
name: slide-creator-ss
description: |
  プレゼンスライド（PPTX）と原稿（DOCX）を一括生成する複合スキル。
  python-pptx + python-docx でデザイン付きスライドと原稿を自動生成。
  Use when: (1) user says「スライド作って」「プレゼン作って」「PPTX作って」,
  (2) user wants「資料作成」「発表資料」「プレゼン資料」,
  (3) user mentions「スライドと原稿」「提出資料」「選考資料」.
  Do NOT use for: 動画制作（video-agentを使用）、LP制作（lp-designを使用）。
---

# Slide Creator - プレゼン資料一括生成スキル

ヒアリング → 構成設計 → スライド（PPTX）+ 原稿（DOCX）を一括生成。

## When to Use This Skill

- 「スライド作って」「プレゼン作りたい」
- 「PPTXを生成して」「パワポ作って」
- 「発表資料と原稿をまとめて」
- 「選考用のスライドを準備して」
- 「〇〇というテーマでプレゼンを」

## 全体フロー（6フェーズ）

```
Phase 1: ヒアリング
   │  目的・ターゲット・発表時間・必須項目を確認
   ▼
Phase 2: コンセプト設計
   │  スライドの軸・トーン・構成方針を決定 → ユーザー承認
   ▼
Phase 3: スライド構成設計
   │  各スライドの内容・レイアウトを設計 → ユーザー承認
   ▼
Phase 4: Pythonスクリプト作成
   │  python-pptx / python-docx でスクリプト作成
   ▼
Phase 5: ファイル生成
   │  スクリプト実行 → PPTX + DOCX を生成
   ▼
Phase 6: レビュー・修正
   │  ユーザーが確認 → フィードバック反映
   ▼
完成！
```

## 生成物の仕様

| 項目 | 内容 |
|------|------|
| スライド形式 | PPTX（python-pptx） |
| 原稿形式 | DOCX（python-docx） |
| スライドサイズ | 16:9（13.333 x 7.5 inch）|
| フォント | 游ゴシック（デフォルト） |
| 出力先 | `output/` 配下にプロジェクト別フォルダ |

## Phase 1: ヒアリング（必須確認事項）

以下を必ず確認してから設計に進む：

```
┌─────────────────────────────────────────────────────────────┐
│  1. 目的：何のためのプレゼンか（選考？提案？教育？）        │
│  2. ターゲット：誰に見せるか（審査員？顧客？学生？）        │
│  3. 発表時間：何分か（3分？15分？時間制限なし？）            │
│  4. 必須項目：含めなければならない項目があるか               │
│  5. トーン：フォーマル？カジュアル？親しみやすい？            │
│  6. 既存資料：参考にする資料やスライドがあるか               │
│  7. 原稿の要否：スライドだけか、原稿も必要か                 │
└─────────────────────────────────────────────────────────────┘
```

## Phase 2: コンセプト設計

### 設計思想：「セールストーク型」

スライドは「情報を並べるもの」ではなく「相手を動かすもの」。
以下の原則に従う：

```
┌─────────────────────────────────────────────────────────────┐
│  原則1: Show, Don't Tell                                    │
│    → 「私は〇〇ができます」ではなく、                       │
│      スライド自体がその能力の証明になる構成にする            │
│                                                             │
│  原則2: Before → After                                      │
│    → 変化のストーリーで語る                                  │
│      課題・不安 → 解決・発見 → 結論                          │
│                                                             │
│  原則3: 理念 → 現場 → 体験                                  │
│    → 抽象的な理念を、具体的な体験に落として伝える            │
│      理念が「お題目」ではなく「生きている」ことを見せる      │
│                                                             │
│  原則4: 数字に体験を乗せる                                  │
│    → 「年間休日126日」ではなく                               │
│      「年間126日休めて、映画も楽しめている」                  │
│                                                             │
│  原則5: 宣言しない、感じさせる                               │
│    → 「私は共感力があります」とは言わない                    │
│      語り口で自然に伝わる構成にする                          │
└─────────────────────────────────────────────────────────────┘
```

### NG パターン（避けるべき）

| NG | 理由 | OK（改善例） |
|----|------|-------------|
| 機能・スペックの羅列 | 面白くない、会社説明になる | 体験を通じて伝える |
| 「〇〇に挑戦したい」直接宣言 | 言わなくても伝わるべき | スライド自体が能力の証明 |
| 「私の強みは〇〇です」 | 自己主張が強い | エピソードで自然に伝わる |
| データ表・グリッドの多用 | 読みにくく退屈 | データに体験を乗せる |
| 説教的な締め | 聞き手が引く | 自然な着地 |

## Phase 3: スライド構成設計

### 構成テンプレート（発表時間別）

#### 3分プレゼン（5〜6枚）

```
1. 表紙（フック）         ← 聞き手の心を掴む一言
2. 課題提起（共感）       ← Before: 相手と同じ立場だった
3. 解決①（体験）         ← After: こう変わった
4. 解決②（体験）         ← After: こう変わった
5. 解決③（体験）         ← After: こう変わった
6. まとめ（自然な着地）   ← 宣言ではなく、感じさせる
```

#### 5〜10分プレゼン（8〜12枚）

```
1. 表紙
2. 自己紹介（人柄が伝わる）
3. 課題提起
4-6. 本題（Before→After × 3）
7-8. 深掘り（理念×現場×体験）
9. データ（体験に乗せた数字）
10. まとめ
```

#### 15分プレゼン（自己紹介4枚 + 本題8〜10枚）

```
[自己紹介パート: 4枚]
1. 表紙（名前・所属）
2. 経歴（Before→Afterストーリー）
3. 趣味・人柄（自然に強みが伝わる）
4. キーワード（宣言ではなくストーリーで着地）

[本題パート: 8〜10枚]
5. 導入（フック）
6. 課題提起（共感）
7-9. 本題×3（体験ベース）
10-11. 深掘り
12. まとめ（自然な着地）
```

## Phase 4: Pythonスクリプト作成

### 技術仕様

```python
# 必須ライブラリ
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# 原稿用
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
```

### スライドサイズ

```python
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
```

### ヘルパー関数テンプレート

```python
def rect(slide, l, t, w, h, color):
    """矩形"""
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    return s

def rrect(slide, l, t, w, h, color):
    """角丸矩形"""
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    return s

def circle(slide, l, t, sz, color):
    """円"""
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, l, t, sz, sz)
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    return s

def line(slide, l, t, w, color):
    """水平線"""
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, Pt(3))
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    return s

def txt(slide, l, t, w, h, text, sz=18, color=DARK, bold=False,
        align=PP_ALIGN.LEFT, fn="游ゴシック"):
    """テキストボックス"""
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = text
    p.font.size = Pt(sz); p.font.color.rgb = color; p.font.bold = bold
    p.font.name = fn; p.alignment = align
    return tb
```

### カラーパレットテンプレート

```python
# ── 信頼・落ち着き系（ビジネス向け） ──
PRIMARY = RGBColor(0x1A, 0x5C, 0x6B)      # 深いティール
WARM = RGBColor(0xE8, 0x8D, 0x2A)         # ゴールド（アクセント）
SOFT_TEAL = RGBColor(0x4E, 0xA8, 0xA8)    # 柔らかいティール
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x33, 0x33, 0x33)
LIGHT_BG = RGBColor(0xF7, 0xFB, 0xFB)     # 背景
GRAY = RGBColor(0x88, 0x88, 0x88)

# ── Before/After 用 ──
SOFT_PINK = RGBColor(0xFD, 0xEE, 0xE0)    # Before（不安）
SOFT_GREEN = RGBColor(0xE0, 0xF5, 0xEE)   # After（安心）
```

### スライドレイアウトパターン

#### パターン1: ヘッダー + 2カラム

```python
# ヘッダー（上部帯）
rect(slide, Inches(0), Inches(0), SLIDE_W, Inches(1.2), PRIMARY)
txt(slide, Inches(0.8), Inches(0.1), Inches(8), Inches(0.3),
    "ENGLISH LABEL", sz=13, color=RGBColor(0xB0, 0xD8, 0xD8))
txt(slide, Inches(0.8), Inches(0.45), Inches(10), Inches(0.7),
    "日本語タイトル", sz=28, color=WHITE, bold=True)
line(slide, Inches(0.8), Inches(1.5), Inches(3), WARM)

# 背景
rect(slide, Inches(0), Inches(1.2), SLIDE_W, Inches(6.3), LIGHT_BG)

# 左カラム
rrect(slide, Inches(0.6), Inches(1.6), Inches(5.8), Inches(5.4), WHITE)

# 右カラム
rrect(slide, Inches(6.9), Inches(1.6), Inches(5.8), Inches(5.4), WHITE)
```

#### パターン2: Before → After

```python
# Beforeラベル
rrect(slide, Inches(0.9), Inches(1.8), Inches(2.0), Inches(0.4), SOFT_PINK)
txt(slide, ..., "入社前のイメージ", color=RGBColor(0xC0, 0x60, 0x40))

# 矢印
txt(slide, ..., "▼", sz=20, color=WARM)

# Afterラベル
rrect(slide, Inches(0.9), Inches(3.7), Inches(2.0), Inches(0.4), SOFT_GREEN)
txt(slide, ..., "入社後の現実", color=RGBColor(0x2A, 0x80, 0x60))
```

#### パターン3: 全面カバー（表紙・まとめ用）

```python
rect(slide, Inches(0), Inches(0), SLIDE_W, SLIDE_H, PRIMARY)
circle(slide, Inches(10), Inches(-1), Inches(4), SECONDARY)  # 装飾
circle(slide, Inches(-1.5), Inches(5.5), Inches(3), SECONDARY)

# 中央カード
rect(slide, Inches(1.5), Inches(1.0), Inches(10.333), Inches(5.5), WHITE)
```

#### パターン4: 3カードレイアウト

```python
items = [("01", "タイトル1", "説明1"), ("02", "タイトル2", "説明2"), ...]
for i, (num, title, desc) in enumerate(items):
    x = 0.8 + i * 4.1
    rrect(slide, Inches(x), Inches(1.8), Inches(3.7), Inches(5.0), WHITE)
    circle(slide, Inches(x + 1.35), Inches(2.1), Inches(1.0), ACCENT)
    txt(slide, ..., num)
    txt(slide, ..., title)
    txt(slide, ..., desc)
```

### 原稿テンプレート（python-docx）

```python
doc = Document()
style = doc.styles['Normal']
style.font.name = '游ゴシック'
style.font.size = Pt(11)

# スライドラベル
def add_slide_label(doc, label):
    p = doc.add_paragraph()
    run = p.add_run(f"【{label}】")
    run.font.bold = True; run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x1A, 0x5C, 0x6B)

# タイムスタンプ
def add_time_note(doc, time_text):
    p = doc.add_paragraph()
    run = p.add_run(f"⏱ {time_text}")
    run.font.size = Pt(10); run.font.bold = True
    run.font.color.rgb = RGBColor(0xE8, 0x8D, 0x2A)

# 原稿テキスト
def add_script_text(doc, text):
    p = doc.add_paragraph(text)
    p.paragraph_format.line_spacing = Pt(22)

# 演出ポイント
def add_point_note(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(f"💡 {text}")
    run.font.size = Pt(10); run.font.italic = True
    run.font.color.rgb = RGBColor(0x4E, 0xA8, 0xA8)
```

## Phase 5: ファイル生成

```bash
# スクリプト実行
cd {output_dir}
python create_slide_pptx.py
python create_script_docx.py
```

### 出力フォルダ構成

```
output/{プロジェクト名}/
├── create_slide_pptx.py        ← スライド生成スクリプト
├── create_script_docx.py       ← 原稿生成スクリプト
├── {スライド名}.pptx           ← 生成されたスライド
└── {原稿名}.docx               ← 生成された原稿
```

## Phase 6: レビュー・修正

ユーザーのフィードバックに基づいてスクリプトを修正し、再生成する。

### よくある修正依頼

| 修正内容 | 対応方法 |
|---------|---------|
| テキスト変更 | スクリプト内の文字列を修正 → 再実行 |
| レイアウト変更 | 座標・サイズを調整 → 再実行 |
| カラー変更 | RGBColor値を変更 → 再実行 |
| スライド追加/削除 | セクションを追加/削除 → 再実行 |
| コンセプト変更 | Phase 2に戻って再設計 |

## 原稿の構成ルール

### 発表時間の目安

| 発表時間 | 文字数目安 | 話速 |
|---------|-----------|------|
| 1分 | 約300字 | ゆっくり |
| 3分 | 約900字 | ゆっくり |
| 5分 | 約1,500字 | 普通 |
| 10分 | 約3,000字 | 普通 |
| 15分 | 約4,500字 | 普通 |

### 原稿の書き方ガイド

```
┌─────────────────────────────────────────────────────────────┐
│  1. 話し言葉で書く（書き言葉にしない）                      │
│  2. 一文は短く（40字以内を目安）                             │
│  3. 体験ベースで語る（スペックを並べない）                   │
│  4. 間（ま）を意識（改行 = 一呼吸）                          │
│  5. 各スライドに演出ポイント💡を付ける                       │
│  6. タイムスタンプ⏱で時間配分を明示                         │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| python-pptx がない | `pip install python-pptx` |
| python-docx がない | `pip install python-docx` |
| フォントが表示されない | 游ゴシックがインストールされているか確認 |
| 文字化けする | `PYTHONIOENCODING=utf-8` を設定 |
| レイアウトが崩れる | Inches値を微調整して再生成 |

## Best Practices

- スライドは**1枚1メッセージ**。詰め込みすぎない
- カラーは**2〜3色**に絞る。統一感が大事
- テキストは**最小限**。口頭で補足する設計にする
- 修正は**スクリプトを直して再生成**。PPTXを直接編集しない
- 原稿は**必ずスライドと同時に更新**。乖離させない
