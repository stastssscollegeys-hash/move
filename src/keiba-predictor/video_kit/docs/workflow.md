# 詳しい手順・数値・落とし穴

フォルダの形（1レース・{日付}=例 20261123・{tag}=例 tospo）:

```
work/{日付}/
├─ research/score_{tag}.json   … 独自指数（name・rank・score ほか）。台本と画像の数字はここから
├─ images/                     … ショート用 9:16 と本編用 3:2 の画像
├─ prompts/                    … 画像の指示文と batch JSON
├─ shorts/script_{tag}.json  audio/  _tmp/
├─ long/script_{tag}_long.json  _chunks/  _raw/  audio/  _tmp/  （本編。templates/long の4本をここに写して書き換える）
└─ youtube/                    … タイトル・概要欄・サムネ
```

## 1. 台本 JSON の形

```json
{ "race": "…", "date": "2026-11-23", "image_dir": "images", "out_suffix": "long",
  "canvas": {"w":1920,"h":1080,"fg_w":1620,"fg_h":1080,"y_off":0,"zmax":1.04,"font":46,"hilite":50,"margin_v":40,"wrap":28},
  "scenes": [ {"id":1, "image":"T01.png", "sec":8.0, "zoom":"in|out|none",
               "narration":"読ませる文", "subtitle":["字幕1行目","2行目"], "focus":{"x":0.25,"y":0.8,"z":1.8}} ] }
```
- ショートは canvas を省略（1080x1920・字幕68）。場面の長さは音声の実長＋0.45秒で決まる（sec は目安）
- 字幕は場面の時間を行数で等分して順に出す → 1場面1つの話にする

## 2. 画像（ChatGPT）

- `templates/long/make_long_prompts.py` で17枚（結論・特徴・過去10年×3・最新情報・指数のつくり方・横比較・軸候補・注目馬・狙わない馬・穴・ランキング×3・TOP3 など）
- 1枚目を配色の参照にし、2枚目以降は1枚目を添付して色をそろえる。参照画像は「レイアウトの骨格だけ」と書く（色や飾りを写されないため）
- `node scripts/image/cdp_chatgpt.mjs batch <batch.json>` は**1件ずつ**流す
- 🔴 添付したキャラクターシートがそのまま保存されることがある → **画像の大きさ**（キャラシートと同じ寸法）で見分けて作り直す。待ってから `grab <out.png>` で取り出す手もある
- 🔴 画像生成はクリップボードを使う → 同時に別の貼り付け作業（Muse など）をすると中身がぶつかる

## 3. 音声

### A. Gemini TTS
- ショート: `node scripts/tts/gen_short_tts.js <script.json> [--voice=Zephyr]`（キーは GEMINI_API_KEY〜5 を順に使う）
  - 対話（話し手が2人以上）のショートは、話し手ごとにまとめ読みして場面に切る（中で tts_chunks.js → split_chunks.py を通す）。場面ごとに作るなら `--per-scene`
- 本編: `node scripts/tts/tts_chunks.js <script_long.json> --max=8 --chars=700` → `python scripts/audio/split_chunks.py <script_long.json>`
  - 切り分けがずれたら `split_chunks.py <script> チャンク:境目:+1` で次の無音へ動かす
- 素の声は長い → `ffmpeg -i in.wav -af atempo=1.3 out.wav`（ショート 1.30〜1.45・本編 1.25〜1.30）

### B. Muse（muse.ai・ブラウザで操作）
- 台本を段落（同じ画像が続く3〜6場面・520字まで）に分け、1段落ずつ「同じ声・同じ速さで、文章は一字も変えない・段落のあいだは2秒あける」と頼む
- 段落の間に約2.7秒の無音が入る → `split_chunks.py` で切りやすい。段落の頭の場面は頭を削らない
- Muse は素で約5.4字/秒と遅い → 場面内の無音を0.3秒に詰めて atempo 1.25〜1.30
- 声によっては文によって崩れる（80場面で3場面）→ 言い回しを変えてその場面だけ作り直す（同じ文だと同じ音声が返る）
- 数場面まとめて作り直した音声は `fx_split.py`（`_fx_groups.json` に場面idのグループを書く）

### 読み替え（tts_yomi.py）
TTS に渡す文章だけひらがなにする（字幕は漢字のまま）。見つかった読み違い: 注目馬・桜花賞・勝ち馬・全馬・外国馬・新馬戦・牡馬・古馬・美浦・順位（「三位」を英語で読んだ）など。新しく見つけたら表に足す。

## 4. 検証（NG 0件まで）

| 何を | 道具 | 見るところ |
|---|---|---|
| 読み方 | `kana_scenes.py`・`asr_kana.py` | ひらがなの文字起こしと台本を並べる（漢字に直されると読み違いが隠れる） |
| 英語読み・長さ | `lang_check.py <script> <audio> <tag>` | 日本語以外・確信度0.80未満・英字8字以上・4.0〜11.5字/秒の外 |
| ランキング | `asr_check.py small <wav…>` | 順位・点数・馬名（馬名を initial_prompt に入れる） |

- 英語由来の馬名は、ひらがなで渡して「すべて日本語で読む」と添える。それでも英字で出るときは人が聴いて判断
- 文字起こし・長い合成は、PC のメモリが少ないとバックグラウンドで止められることがある → 別プロセスで起動して終わりを待つ

## 5. 組み立てと音

- 本編: `BV_RESUME=1 python scripts/video/build_video.py long/script_{tag}_long.json`（止まっても続きから）
  - 最後の合成が長い（17分かかった例）→ `final_mux_split.py <script> seg 0`, `seg 1`, … → `join`
- ショート: `python scripts/video/build_short.py shorts/script_{tag}.json`（メモリ不足なら `build_short_lowmem.py`）
- BGM（本編）: `long/make_bgm_sections.py` で章ごとに3曲を切り替え（1.5秒のクロスフェード）→ `long/mix_long.py`
  - 声 -15LUFS・BGM -30LUFS。効果音は「章の切り替え／データ／馬の紹介／注意／ランキング／TOP3／まとめ」で別の音
- BGM（ショート）: `add_bgm_se.py <script> "<曲>.mp3" --bgm-lufs -26 --sevol 1.6 [--se-ding "file.mp3:開始:長さ"]`
  - 🔴 作り直すときは `shorts/_tmp/{tag}_voice.mp4` を消す（残っていると古い声を使う）。仕上げの音量は本編と同じ -15LUFS 前後に
- 最後に映像を数か所切り出して目視（字幕・数字・絵の一致）

## 6. サムネイル（本編のみ）

- ひな型 `templates/thumbnail/THUMB_long_adopted.txt`（採用された型）:
  レース名を**真ん中〜少し上に横幅70%以上の特大**・上段にバッジと気になるデータの吹き出し・下段に名札3つ（軸候補×2・穴候補）・最下部にデータの帯・余白を作らない
- 生成は 3:2（1536x1024）で出る → 上下を切らず、左右をぼかしで埋めて16:9に:
  ```
  ffmpeg -i raw.png -filter_complex "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,boxblur=30:3,eq=brightness=-0.12[bg];[0:v]scale=-1:720[fg];[bg][fg]overlay=(W-w)/2:0" -frames:v 1 thumb_long.png
  ```
- 文字（馬名・数字）は全部目で確認。印・買い目・オッズの数字は入れない

## 7. YouTube 素材

- `templates/youtube/youtube_post_template.txt`: タイトル案3つ／先に結論／過去10年／注意書き（印と買い目は枠順のあと・予想人気は目安・20歳未満は馬券を買えない）／目次／ハッシュタグ／タグ
- 目次の時刻は「各場面＝音声の長さ＋0.45秒」の積み上げで、章の最初の場面の開始時刻（`make_youtube_text.py`。または `_tmp/{tag}.ass` で章の最初の字幕を探す）
- 題名は「意外な数字」か「問いを1つ」

## 8. YouTube に下書き（yt_studio_cdp.mjs）

Claude in Chrome のファイル添付は10MBまでなので、デバッグポートの Chrome に CDP でつなぐ。
1. Studio の「作成」→「動画をアップロード」。**ファイル選択の画面が出ているのを確かめてから** `files <tab> "ytcp-uploads-file-picker input[type=file]" <mp4>`
2. タイトル欄がファイル名になったら `type "#title-textarea #textbox" <txt>`・`type "#description-textarea #textbox" <txt>`
3. 本編はサムネ `files … "input#file-loader" thumb_long.png`・子ども向けではない・タグ
4. 「非公開として保存済み」を見てから閉じる。次の動画は「作成」から開き直す
- 🔴 アップロード中にそのタブで再読み込み・移動をしない（固まる・止まる）。確認は新しいタブで
- 🔴 アップロード前に Studio 左上のチャンネル名を確認（複数のチャンネルを持っている場合）
- 公開ボタンは押さない

## 9. 時間の目安（1レース）

画像17＋2枚 約40分／音声と検証 約40分／組み立て 約30分／サムネ・素材・下書き 約30分。
