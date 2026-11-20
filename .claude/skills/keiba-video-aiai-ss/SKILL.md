---
name: keiba-video-aiai-ss
description: 【合いの手あり】競馬の重賞動画（本編の横長・ショートの縦）を、アスメシ（解説役）と競馬ファン（合いの手の聞き役）の2人の掛け合いで作る。ユーザーが「合いの手あり」「合いの手を入れて」「掛け合いで」「対話で」と指定したときだけ使う。道具は src/keiba-predictor/video_kit（対話モード・gemini-3.8-flash-tts）。合いの手なしの指定なら keiba-video-solo-ss を使う。
---

# keiba-video-aiai-ss — 合いの手ありの競馬動画（2人の掛け合い）

## いつ使うか（使い分け・2026-11-20 ユーザー指示）
- ユーザーは動画を頼むとき、**合いの手の有無を必ず指定する**。
  - 「合いの手あり」→ **このスキル**
  - 「合いの手なし」→ `keiba-video-solo-ss`
- 🔴 有無が書かれていない依頼では、どちらかを勝手に決めない。「合いの手はありとなし、どちらにしますか」と聞いてから始める
- 2つを混ぜない。たとえば「本編はあり・ショートはなし」と言われたら、本編はこのスキル、ショートは solo で作る
- 中身（材料・構成・数字・印や買い目を出さない決まり）は、どちらも keiba-predictor-ss の §3b-v2（1週前）・§3h（枠順確定のあと）に従う。違うのは**台本の書き方・声・画面**だけ

## 道具と準備
- 道具一式: `src/keiba-predictor/video_kit/`。詳しい説明は同じフォルダの `SKILL.md` の「対話モード」の節と `docs/workflow.md`。取り込みの経緯は playbook §4b-5
- 使う前に PowerShell で `. .\src\keiba-predictor\video_kit\set_env.ps1` を実行する（作業場所・キャラシート・BGM・効果音のパス。APIキーはリポジトリ直下の .env）
- 話し手の設定: `video_kit/templates/voices.json`
  - asumeshi: 解説役・声 Leda・右下の丸アイコン
  - fan: 聞き役・声 Puck・字幕は水色・左下の丸アイコン

## 流れ（上から順に・省かない）
1. **材料と構成**
   - これまでどおり作る（本編は約70場面の型、ショートは最初の5秒で結論）
   - 雛形は `video_kit/templates/` と、これまでの週の台本
2. **台本**: 全場面に `"speaker"` を書く（`asumeshi` か `fan`）
   - **アスメシ（解説役）**
     - データ・数字・結論・まとめは、すべてアスメシが言う
     - 口癖「明日のメシ、何にする？」「この展開、熱いね！」は1本で数回まで
     - 「勝てば豪華なトッピング／負ければ白ご飯」のネタも1本で数回まで
   - **ファン（聞き役）**: 見ている人が頭の中で思うことを口に出す。せりふは次の3種類だけ
     - ①言い換え（「〇〇ってこと？」）
     - ②次へのつなぎ（「じゃあ今回の馬は？」）
     - ③用語の質問（「上がりって何？」）
   - ファンが出る目安
     - 数字・％・用語を言った直後
     - 20〜30秒に1回
   - ファンに結論・予想・数字を言わせない
3. **検品（音声を作る前に必ず）**
   - `python src/keiba-predictor/video_kit/scripts/check/dialog_check.py <script.json>` を回し、NG 0件まで直す
   - たとえば、数字・用語の場面が3つ続いてファンが出ないと NG
4. **画像**
   - これまでどおり ChatGPT で作る（`scripts/image/cdp_chatgpt.mjs batch`）
   - 画像の中にアスメシが描かれているので、立ち絵は重ねない
5. **音声**: **Gemini TTS だけ**（gemini-3.8-flash-tts。Muse は使わない）
   - 本編
     - `node scripts/tts/tts_chunks.js <script_long.json>` で、話し手ごとにまとめて読ませる
     - そのあと `python scripts/audio/split_chunks.py` で場面ごとに切る
   - ショート: `node scripts/tts/gen_short_tts.js <script.json>`（対話なら自動でまとめ読み）
   - 声に渡す文だけ、tts_yomi でひらがなにする
   - 速さは ffmpeg の atempo
     - 本編: 1.25〜1.30倍
     - ショート: 1.30〜1.45倍
6. **検証（NG 0件まで作り直す）**
   - `kana_scenes.py`: 読み間違いがないか
   - `lang_check.py`: 英語で読まれていないか・長さがおかしくないか
   - `asr_check.py`: 順位・点数・馬名が合っているか
   - 加えて、**話し手の声が入れ替わっていないか**を確かめる（ファンの場面がアスメシの声になっていないか）
7. **組み立て**: `BV_RESUME=1 python scripts/video/build_video.py <script.json>`
   - 🔴 対話のショートも `build_short.py` ではなく `build_video.py` で組む（縦の設定が既定）
   - 丸アイコンは、話している方が光って口パクする
8. **音の仕上げ**
   - 本編: `make_bgm_sections.py` → `mix_long.py`
   - ショート: `add_bgm_se.py <script.json> "<曲>.mp3" --bgm-lufs -26 --sevol 1.6`
   - BGM は「American Idle - RKVC」。歌入りの曲は使わない
9. **目視**
   - 数か所を切り出して見る
   - 字幕・数字・絵が合っているか
   - アイコンが光る側と話し手が一致しているか
10. **その後**: サムネ → YouTube素材 → YouTube下書き
    - keiba-predictor-ss §3h・playbook §4c と同じ
    - 公開はしない

## 決まり
- 印・買い目・オッズの数字は、枠順確定・発売の前の動画に入れない
- 「穴」と呼ぶのは想定6番人気以下だけ
- 題名は「意外な数字」か「問いを1つ」（keiba-predictor-ss §3l）
- 🟡 対話モードは 2026-11-19 にできたばかり。1本目は、できたものをユーザーに見てもらってから下書きに上げる
