# keiba-video-creator-ss（競馬の本編動画・ショート動画づくり）

競馬の重賞プレビューを、YouTube の**横長の本編（約9〜12分）**と**縦のショート（約45〜50秒）**にする道具一式です。
Claude Code のスキルとしても、手で順番にコマンドを打っても使えます。

## 中身

```
keiba-video-creator-ss/
├─ SKILL.md            … Claude Code 用の手順（流れ・決まり）
├─ README.md           … これ（準備と最初の1本）
├─ docs/workflow.md    … 詳しい手順・数値・落とし穴
├─ .env.example        … APIキーと置き場所の設定（.env にコピーして使う）
├─ requirements.txt / package.json
├─ scripts/
│  ├─ video/   build_video.py（本編・ショート共通）・build_short.py・build_short_lowmem.py・add_bgm_se.py・final_mux_split.py
│  ├─ tts/     gen_short_tts.js（場面ごと）・tts_chunks.js（まとめ読み）・tts_yomi.py（読み替え表）
│  ├─ audio/   split_chunks.py（まとめ読みを場面に切る）・fx_split.py（作り直した音声を切る）
│  ├─ check/   kana_scenes.py・asr_kana.py（ひらがな文字起こし）・lang_check.py（英語読み）・asr_check.py（順位・点数）
│  ├─ image/   cdp_chatgpt.mjs（ChatGPT で画像を作る・Chrome のデバッグポート経由）
│  └─ youtube/ yt_studio_cdp.mjs（Studio に下書き）・make_youtube_text.py（タイトル・概要欄・目次）
├─ templates/  … 週ごとにデータを書き換えるひな型（台本・画像の指示文・BGM・ミックス・サムネ・概要欄）
├─ examples/20261123/ … 実例（東スポ杯2歳S の台本JSONと独自指数）
└─ assets/README.md   … 自分で用意する素材（キャラ・BGM・効果音）
```

## 準備

1. **ソフト**: Python 3.11 以上・Node.js 22 以上（WebSocket を標準で使う）・ffmpeg（PATH に通す）・Google Chrome
2. **Python**: `pip install -r requirements.txt`（faster-whisper。初回にモデル small を自動で落とします）
3. **Node**: `npm install`（@google/genai・dotenv）
4. **設定**: `.env.example` を `.env` にコピーして、Gemini の APIキーと置き場所を書く
   （Python の道具は環境変数を読むので、PowerShell なら `$env:KVC_WORK_ROOT="D:\keiba\work"` のように先に設定）
5. **フォント**: 字幕は「HG創英角ゴシックUB」（Windows/Office 付属）。無ければ `build_video.py`・`build_short.py` の `FONT` を変える
6. **画像生成**: Chrome をデバッグポートつきで起動し、ChatGPT にログインしておく（`scripts/image/cdp_chatgpt.mjs` の先頭に起動方法）
7. **素材**: `assets/README.md` のとおり、キャラクターシート・BGM・効果音を用意する

## まず1本（ショート）

```bash
# 例のデータで組み立てだけ試す（画像と音声は自分で作る）
mkdir -p work/20261123/shorts && cp examples/20261123/shorts/script_tospo.json work/20261123/shorts/
# 画像 pv2_tospo_*.png を work/20261123/images/ に置く（templates/short/images_short.py で指示文を作れる）
node scripts/tts/gen_short_tts.js work/20261123/shorts/script_tospo.json
python scripts/video/build_short.py work/20261123/shorts/script_tospo.json
python scripts/video/add_bgm_se.py work/20261123/shorts/script_tospo.json "あなたの曲.mp3" --bgm-lufs -26 --sevol 1.6
```

本編は `docs/workflow.md` の §2〜5。

## 置き換えるところ

- ひな型の中の `〇〇競馬予想`（チャンネル名）と `マスコットくん`（キャラクター名・見た目の説明）
- `templates/` の馬名・数字・配色（その週のレースに合わせて書き換える前提のひな型です）
- `scripts/check/asr_check.py` の馬名リスト `P`、`kana_scenes.py` の台本ファイル名

## 注意

- YouTube へは**下書き（非公開）まで**。公開はご自身で
- 印・買い目・オッズは、枠順や発売の前の動画には入れない運用にしています
- BGM・効果音・画像のライセンスは各自で確認してください
