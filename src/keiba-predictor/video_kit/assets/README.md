# 自分で用意する素材（同梱していません）

| 置き場所（環境変数） | 中身 | 使う道具 |
|---|---|---|
| `KVC_CHAR_SHEET`（既定 `assets/character_sheet.png`） | マスコットのキャラクターシート（文字なし）。画像の指示文に添付してキャラをそろえる | templates の画像指示文 |
| `KVC_BGM_DIR`（既定 `assets/bgm/`） | BGM の mp3。本編は3曲（make_bgm_sections.py の A/B/C のファイル名を自分の曲に変える） | add_bgm_se.py・make_bgm_sections.py |
| `KVC_SE_DIR`（既定 `assets/se/`） | 効果音の mp3（mix_long.py の中のファイル名を自分の素材に変える）。無くても多くは ffmpeg で合成する | mix_long.py |
| `assets/thumb_style_ref.png` | サムネの勢い（放射光・紙吹雪・3D文字など）の参考にする画像（任意） | サムネの指示文 |

- 歌入りの曲は解説動画に向かない（声とぶつかる）
- 素材のライセンス（YouTube で使えるか・クレジット表記）は各自で確認してください
