# 枠順確定版のあと（動画・ショート・サムネ・YouTube下書き・告知・note）— 2026-11-13 武蔵野S／デイリー杯2歳S／エリザベス女王杯で確立

正本の手順は SKILL.md §3h と docs/keiba_week_before_preview_playbook.md §4c。ここは実物の雛形（Desktop/競馬予想レポート/20261114・20261115 から写し）。
使うときは `Desktop/競馬予想レポート/{日付}/long/` などにコピーして、レース名・R（枠順・数字）・台本の文を書き換える。パスは絶対パスで書いてあるものが多い（先頭の ROOT・CHAR 等を確認）。

| ファイル | 役割 |
|---|---|
| `_make_short_prompts.py` / `_make_short_scripts.py` | ショート用の追加画像2枚／レース（軸候補と相手の筆頭・穴候補と軸にしない馬と追い切り）の指示文、ショート台本8場面 |
| `build_short_lowmem.py` | build_short.py の写し（空き仮想メモリ不足で落ちるときだけ。zoompan の入力を2本に分けた）。ベースラインは触らない |
| `asr_check_draw.py` | 文字起こし照合（馬名リストは環境変数 ASR_P）。small で十分。正しい語を手がかりに入れる |
| `make_draw_long_prompts.py` | 本編の画像17枚（D01〜D17）の指示文。レースごとに R（theme・枠順・追い切り・sim・横比較・軸・相手・軸にしない・穴・ランキング）を書く |
| `make_draw_long_script.py` | 本編台本（70場面前後）。ランキングは1頭1場面・zoom none・「続いて、N位は、馬名。指数は、…」・「しるし」「ジーツー」「ジーワン」「ひゃくまん回」とかな書き |
| `tts_chunks.js` / `split_chunks.py` | 数場面まとめ読み（無料枠対策）→ 無音で切り分け（ずれは `チャンク:境目:±n`）。倍速 atempo 1.3 |
| `run_images.sh` / `gen1.sh` | 画像を1枚ずつ生成（添付画像が保存される不具合は md5 とサイズで検出・40秒待って grab） |
| `final_mux_split.py` | build_video.py の最後の字幕焼き込みを3分ずつの区間に分ける（1回10分を超えないように）→ join |
| `make_thumbs_v4.py` | 長尺サムネ（レース名を最大・軸候補と穴候補の馬名の名札・アスメシくんは小さく・レース風景・ノア先生サムネの勢い） |
| `make_youtube_text.py` | タイトル案3つ・概要欄・目次（音声の長さから計算）・タグ |
| `yt_draft.sh` | YouTube Studio に1本下書き保存（公開しない） |
| `make_promo_posts.py` | 公開後の告知投稿案（X3本・Threads2本／レース） |
| `make_note_articles.py` | note記事（見出し h2/h3・太字・目次ブロック用の目印・YouTube埋め込み）の HTML と txt |
| `make_note_promo.py` | note記事を公開したあとの告知投稿案（X1本・Threads1本／レース・URLは公開ページで確認） |
