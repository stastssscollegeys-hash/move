---
name: keiba-video-solo-ss
description: 【合いの手なし】競馬の重賞動画（本編の横長・ショートの縦）を、これまでどおり1人の語りで作る。ユーザーが「合いの手なし」「合いの手は入れない」「1人で」「いつもどおりの語り」と指定したときだけ使う。手順と道具は、高評価だったこれまでの流れ（keiba-predictor-ss §3b-v2・§3h、playbook §4 ⑤b・4b-2〜4b-4・§4c）。合いの手ありの指定なら keiba-video-aiai-ss を使う。
---

# keiba-video-solo-ss — 合いの手なしの競馬動画（1人の語り）

## いつ使うか（使い分け・2026-11-20 ユーザー指示）
- ユーザーは動画を頼むとき、**合いの手の有無を必ず指定する**。
  - 「合いの手なし」→ **このスキル**
  - 「合いの手あり」→ `keiba-video-aiai-ss`
- 🔴 有無が書かれていない依頼では、どちらかを勝手に決めない。「合いの手はありとなし、どちらにしますか」と聞いてから始める
- 2つを混ぜない。台本に `"speaker"` を書かない（書くと対話モードになる）

## 正本（この順に読んでそのとおりに作る・短縮しない）
- 1週前プレビュー
  - keiba-predictor-ss **§3b-v2**
  - `docs/keiba_week_before_preview_playbook.md` **§4 ⑤・⑤b・⑤c・⑤d**
- 枠順確定のあと
  - keiba-predictor-ss **§3h**
  - playbook **§4c**
  - 雛形 `src/keiba-predictor/preview_week/draw_version/after_draw/`
- 長尺の音声
  - playbook **§4b-2**（Muse の Marisol・段落ごとに読む → `long_tools/split_chunks.py`）
  - playbook **§4b-3**（サムネ）
  - playbook **§4b-4**（英語読みの検証 `lang_check.py`）
  - 雛形 `src/keiba-predictor/preview_week/long_tools/`
- ショート
  - `preview_week/images.py` → `gen_short_tts.js` → `build_short.py`（落ちたら `build_short_lowmem.py`）→ `add_bgm_se.py`
  - 最初の5秒で結論

## 流れ（要点・細かいところは正本）
1. **材料と構成**
   - 本編は約70場面の型（冒頭の結論 → レースの特徴 → 過去10年 → 最新情報 → 独自指数のつくり方 → 有力馬 → ランキングは1頭1場面 → まとめ）
   - ショートは最初の5秒で結論
2. **台本**
   - 1人の語り。`"speaker"` は書かない
   - 読み上げは、順位を文頭に置かない
   - 次の言葉はかなで書く: 「しるし」「ジーワン」「ジーツー」
3. **画像**
   - ChatGPT で作る（`cdp_chatgpt.mjs batch`・キャラシートを添付）
   - 重賞は絵入りで中身の濃い画像
4. **音声**
   - 本編: Muse の Marisol で段落ごとに読む → `split_chunks.py`。Gemini TTS で作る場合も1人の声
   - ショート: `gen_short_tts.js`
5. **検証（NG 0件まで作り直す）**
   - ひらがなの文字起こし（読み間違い）
   - `lang_check.py`（英語読み・長さ）
   - `asr_check.py`（順位・点数・馬名）
6. **組み立て**
   - 本編: `build_video.py`（10分を超える・メモリ不足なら `final_mux_split.py`）
   - ショート: `build_short.py`
7. **音の仕上げ**
   - BGM は「American Idle - RKVC」
   - 本編は `mix_long.py`
   - ショートは `add_bgm_se.py`（-26LUFS・効果音1.6倍）
8. **目視 → その後**
   - 目視で、字幕・数字・絵が合っているか見る
   - そのあと、サムネ → YouTube素材 → YouTube下書き（公開はしない）

## 道具について
- 使うのは、これまでの道具（`preview_week/`・`after_draw/`・`long_tools/`）
- `video_kit/` の道具でも、`"speaker"` を書かなければ1人の語りになる。ただし声（Zephyr・gemini-3.8-flash-tts）と画面が、これまでの動画と変わる
- 🔴 ユーザーが「video_kit で」と言わない限り、これまでの道具で作る

## 決まり
- 印・買い目・オッズの数字は、枠順確定・発売の前の動画に入れない
- 「穴」と呼ぶのは想定6番人気以下だけ
- 題名は「意外な数字」か「問いを1つ」（keiba-predictor-ss §3l）
