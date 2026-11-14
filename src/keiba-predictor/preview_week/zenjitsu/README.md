# 重賞の前日予想（前日オッズで印と買い目を出す版）— 雛形一式（2026-11-14 エリザベス女王杯で確立）

正本の手順は `.claude/skills/keiba-predictor-ss/SKILL.md` §3i。ここは 2026-11-14 夜の実物をそのまま置いた雛形。
`Desktop/競馬予想レポート/{日付}/` にコピーして、レース名・印・買い目・本文を書き換えて使う（パスは絶対パスで書いてあるものが多い）。

| ファイル | 役割 |
|---|---|
| `build_picks2_20261115.py` | 投稿文（X長文1本＋Threads4本）。印・買い目を上、その下に根拠・注目点・短評 |
| `build_note_eri_20261115.py` | note記事（8節。金曜の見立てから変えた理由に1節）。build_picks2 の R を読むので数字が同じ |
| `prompt_zj_rich_image_example.txt` | X・Threads用の絵入り画像（ChatGPT生成・9:16）の指示文。重賞は必ずこの型（文字だけのHTML画像は平場用） |
| `prompt_note_header_example.txt` | noteヘッダー（ChatGPT生成・16:9）の指示文 |
| `build_note_header_20261115.py` | HTML→PNG のヘッダー（使わない。重賞のヘッダーは ChatGPT 生成。残しているのは記録のため） |
| `make_zj_prompts.py` | 本編動画（横長・7〜8分）の画像13枚の指示文とバッチ |
| `make_zj_script.py` | 本編の台本（53場面）。末尾の OV が買い目の場面の差し替え |
| `make_zj_short.py` | ショート（8場面・約50秒）の台本と追加画像2枚の指示文 |
| `grade_picks_20261114.py` | 公開した買い目（picks2 の【印】【買い目】）を確定払戻で照合。引数 `_prev0047` で前夜版も |

買い目は `src/keiba-predictor/web_compose.py --post` で組み、出力の表記（v3）をそのまま使う。
