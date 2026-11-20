---
name: keiba-video-creator-ss
description: 競馬の重賞プレビューを、YouTubeの横長の本編動画（約9〜12分・1920x1080）と縦のショート動画（約45〜50秒・1080x1920）にする。台本JSON→AI画像（ChatGPT）→ナレーション音声（Gemini TTS か Muse）→読み方・英語読みの検証→字幕つきの組み立て（ffmpeg）→BGM・効果音→サムネイル→YouTube投稿素材→YouTubeに下書き保存、までを同じ型で作る。「重賞の動画を作って」「本編とショートを」「1週前プレビューの動画」「長尺動画」「ショート動画」で使う。
---

# keiba-video-creator-ss — 競馬の本編動画・ショート動画を作る

重賞1レースぶんの「本編（横長）」と「ショート（縦）」を、毎週同じ構成で作るための手順と道具一式。
**1週前プレビュー（登録の段階）**の構成で磨いたもの。枠順確定版・前日予想にも同じ道具が使える。

- 道具は全部 `scripts/`、週ごとに書き換えるひな型は `templates/`、実例は `examples/20261123/`（東スポ杯2歳S）
- 詳しい手順と落とし穴は `docs/workflow.md`。準備（インストール・APIキー・素材）は `README.md`
- 作業フォルダ: 環境変数 `KVC_WORK_ROOT`（既定 `work/`）の下に `{日付}/` を作り、`images/ prompts/ shorts/ long/ research/ youtube/` を置く

## 成果物（1レース）

| もの | 形 | 道具 |
|---|---|---|
| ショート | 1080x1920・約45〜50秒・8場面前後・最初の5秒で結論 | `templates/short/images_short.py` → `gen_short_tts.js` → `build_short.py` → `add_bgm_se.py` |
| 本編 | 1920x1080・約9〜12分・約70場面・画像17枚 | `templates/long/make_long_script.py`・`make_long_prompts.py` → 音声 → `build_video.py` → `mix_long.py` |
| サムネイル | 1280x720（本編のみ。ショートは公開時に1コマを選ぶ） | `templates/thumbnail/*.txt` → `cdp_chatgpt.mjs` → ffmpeg で16:9 |
| YouTube素材 | タイトル案3つ・概要欄（目次つき）・タグ | `templates/youtube/youtube_post_template.txt`・`scripts/youtube/make_youtube_text.py` |
| YouTube下書き | 非公開のドラフト（公開は人が押す） | `scripts/youtube/yt_studio_cdp.mjs` |

## 本編の構成（変えない型・約70場面）

1. 冒頭の結論（独自指数TOP3・軸候補・穴候補・狙わない馬）
2. レースの特徴
3. 過去10年（人気と配当／脚質・枠・年齢／一番大事な型と間隔）
4. 最新情報（回避・1週前追い切り・予想オッズ）
5. 独自指数のつくり方（例: 近走40・型20・適性20・脚質10・状態10＝100点）
6. 有力馬の横比較 → 軸候補 → 注目馬 → 狙わない馬 → 穴候補
7. 指数ランキング（下位→4位は**1頭1場面**、最後にTOP3）
8. まとめ（印・買い目は枠順のあと、と言って終える）

ショート: 結論（軸候補・穴の型）→ レースの特徴 → 注目馬 → 穴馬 → 面白いデータ3つ → 本編への誘導。

## 流れ（上から順に）

```
① 材料: 登録馬・過去10年の傾向・独自指数（research/score_{tag}.json: name/rank/score ほか）
② 台本: templates/long/make_long_script.py を週のデータに書き換え → long/script_{tag}_long.json
         templates/short/images_short.py の RACES を書き換え → shorts/script_{tag}.json と画像の指示文
③ 画像: templates/long/make_long_prompts.py → prompts/ と batch JSON → scripts/image/cdp_chatgpt.mjs batch（1枚ずつ）
         配色はレースごとに変える（冠名の企業カラー・開催地の風土・国旗など由来で決める）。毛色は実物を調べる
④ 音声: A) Gemini TTS（gemini-3.8-flash-tts・2026-11-19〜。声と読み方は templates/voices.json）:
                       node scripts/tts/gen_short_tts.js <script.json>（ショート・場面ごと）
                       node scripts/tts/tts_chunks.js <script_long.json>（本編・数場面まとめ読み）→ python scripts/audio/split_chunks.py
         B) Muse（muse.ai・ブラウザ）: 段落ごとに読ませて mp3 → split_chunks.py（docs/workflow.md §3）
         TTS に渡す文章だけ tts_yomi.py でひらがなに置き換える（字幕は漢字のまま）
         速さ: ffmpeg atempo（本編 1.25〜1.30・ショート 1.30〜1.45）。素の声は _raw/ に残す
⑤ 検証（必ず・NG 0件まで作り直す）:
         python scripts/check/kana_scenes.py   … ひらがなで文字起こし→読み間違いを台本と見比べる
         python scripts/check/lang_check.py <script.json> <audioフォルダ> <tag>   … 英語で読まれた場面・長さの異常
         python scripts/check/asr_check.py small <wav...>   … ランキングの順位・点数・馬名
⑥ 組み立て: BV_RESUME=1 python scripts/video/build_video.py <script_long.json>
         （10分を超える・メモリ不足なら scripts/video/final_mux_split.py seg 0.. → join）
         ショート: python scripts/video/build_short.py <script.json>（落ちたら build_short_lowmem.py）
⑦ 音の仕上げ: 本編 templates/long/make_bgm_sections.py（場面で3曲切り替え）→ mix_long.py（声 -15LUFS・BGM -30LUFS・効果音を場面の種類で変える）
         ショート: python scripts/video/add_bgm_se.py <script.json> "<曲>.mp3" --bgm-lufs -26 --sevol 1.6
⑧ 目視: 映像を数か所切り出して、字幕・数字・絵が合っているか見る
⑨ サムネ → YouTube素材 → YouTube下書き（docs/workflow.md §6〜8）
```

## 決まり（実際に直されたこと）

- **字幕と声**: 1場面に1つの話（ランキングは1頭1場面）。字幕は場面の時間を等分して出すので、詰め込むとずれる
- **寄り・引き**: 表・一覧・ランキングの場面は `zoom: "none"`（寄ると見たい行が切れる）。寄りは馬の絵・図の一部を指すときだけ
- **ランキングの画像**: 上が上位・下が下位。各行「順位／馬名／指数＋棒／短い説明」
- **読み上げ**: 順位を文頭に置かない（「続いて、十八位は、〇〇。指数は、四十八点九。」）。「三十一」の「一」は落ちやすい→かなで書く。「しるし」「ジーワン」「ジーツー」「ひゃくまん回」とかなで渡す
- **英語読み**: 英語由来の馬名は英語の発音で読まれることがある → ひらがなで渡し「すべて日本語で読む」と添える。lang_check で NG 0件まで
- **長さ**: 本編は約4,850字で10〜12分（約7字/秒）。1.45倍は速すぎると言われた
- **BGM**: 歌入りの曲は使わない（曲名に feat. があるものは要注意。文字起こしでの歌声判定は当てにならない＝人が聴く）
- **印・買い目・オッズの数字**は1週前の動画・サムネに入れない（枠順・発売のあと）。「穴」は想定6番人気以下だけ
- **YouTube**: 公開ボタンは押さない（下書きまで）。アップロード前に Studio 左上のチャンネル名を確認。ファイル選択の画面を確かめてから入れる（前の動画を上書きした事故あり）
- **題名**: 「意外な数字」か「問いを1つ」（例:「予想15番人気が独自指数2位!?」）。決まり文句の型は伸びなかった

## 対話モード（アスメシが解説・競馬ファンが合いの手の2人の掛け合い・2026-11-19）

台本の場面に `"speaker"` を書くと対話モードになる。書かない場面は今までどおり1人の語り（`narrator`）。

| speaker | 役 | 声（Gemini TTS） | 画面 |
|---|---|---|---|
| `asumeshi` | 解説役（role＝kaisetsu）：アスメシが自分で調べたデータ・数字・結論を話す | Leda・かわいい子馬が自信をもって説明する読み方 | 丸アイコン（ピンクの縁）・字幕は今までどおり白と黄色 |
| `fan` | 聞き役（role＝kikite）：見ている人が頭の中で思うことを口に出す競馬ファン | Puck・親しみやすい20代の男性が素直に驚き聞き返す読み方 | 丸アイコン（水色の縁・耳に赤ペンの男性）・字幕が水色 |

```json
{"id": 12, "image": "T05.png", "speaker": "asumeshi", "narration": "1番人気は5勝で、3着以内は10回のうち7回です。", "subtitle": ["1番人気は5勝", "3着以内は10回のうち7回"]},
{"id": 13, "image": "T05.png", "speaker": "fan", "narration": "えっ、7割も！？　じゃあ今年も、1番人気から買えばいいってこと？", "subtitle": ["えっ、7割も！？", "1番人気から買えばいいってこと？"]},
{"id": 14, "image": "T05.png", "speaker": "asumeshi", "narration": "そう、堅いレースなんです。だから穴は、条件をしぼって探します。", "subtitle": ["そう、堅いレース", "穴は条件をしぼって探す"]}
```

- **台本の書き方**：解説はアスメシ（口癖「明日のメシ、何にする？」「この展開、熱いね！」・勝てば豪華なトッピング／負ければ白ご飯のネタは、解説の中に1本で数回まで）。ファンのセリフは3種類だけ＝①言い換え（「〇〇ってこと？」）②次へのつなぎ（「じゃあ今回の馬は？」）③用語の質問（「上がりって何？」）。数字・％・用語を言った直後、20〜30秒に1回が目安。結論・まとめはアスメシが言う。speaker を書かない場面はアスメシ（解説役）が話す
- **検品（音声を作る前に必ず）**：`python scripts/check/dialog_check.py <script.json>`（数字・用語の場面が3つ続いてファンが出ないと NG。聞き役は voices.json の role＝kikite で決まる）
- **声**：Gemini TTS だけ（Muse は1人の語りのとき）。対話のときは、話し手ごとに台本じゅうのせりふを集めてまとめ読みし（tts_chunks.js）、split_chunks.py で場面に切って元の順に並べる＝掛け合いでも回数が増えない（ショートの gen_short_tts.js も対話なら自動でこの形・--per-scene で場面ごと）。1場面だけのまとめも split_chunks.py がそのまま切り出す
- **画面**：画像の中にもアスメシが描かれているので、立ち絵は重ねない。既定は【2人の丸アイコンを画面の下の左右の角に固定・字幕は真ん中】（voices.json の side：説明する側アスメシ＝right・反応する側ファン＝left）。話している方は光って、声が出ている間だけ口が1秒に5回開け閉めする（_on_open.png があるとき。各場面の wav の波形で判定し、句読点の間・文末は閉じる＝rich-explain-video-ss の speech-envelope と同じ決まり）。話していない方は少し暗く口を閉じる。ショートは右下に YouTube のボタンの列が来るので、アイコンを字幕の1段上に置き、右のアイコンは右端から約140px 内側に寄せる。台本の "icon_mode" で "beside"（話している方だけ字幕のすぐ左・行ごとに動く）／"sides"（横長は左右の余白・ショートは上の帯）に切り替えられる。**対話のショートは build_short.py ではなく build_video.py で組む**（縦の設定が既定）
- アイコンを作り直す：`python scripts/image/make_icons.py <口を閉じた丸い顔.png> assets/icon_<名前> "#色" --size 220 --open <口を開けた丸い顔.png>`（Pillow が要る）。口を開けた（閉じた）顔は、元の顔を chatgpt-image-devtools-ss で --attach して「口だけ変えた同じ絵」を作り、`python scripts/image/merge_mouth.py <元の顔> <生成した絵> <出力> --mouth x,y,横半径,縦半径` で口の所だけ元の顔に移す（ほかが動かないので顔が揺れない）。voices.json の `icon`・`side`・`name`

## 置き換えが必要なもの（共有用に伏せた所）

- `〇〇競馬予想` → あなたのチャンネル名、`マスコットくん` → あなたのキャラクター名（ひな型の台本・指示文の中）
- キャラクターシート・BGM・効果音・サムネの参考画像は同梱していない → `assets/README.md`
