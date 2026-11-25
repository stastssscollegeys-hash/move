# -*- coding: utf-8 -*-
"""枠順確定版の本編（画像 D01〜D17・合いの手あり）用に、BGM と音の仕上げのスクリプトを作る（2026-11-20）。
雛形 make_bgm_sections.py・mix_long.py（1週前版・画像 T01〜）を読み、台本の名前・画像の対応だけ差し替えて、台本と同じフォルダに書き出す。
  → <long>/make_bgm_{tag}.py・<long>/mix_{tag}.py  （tag＝script_{tag}.json の tag。例 fuku_draw）
違い: 聞き役（fan）の場面では効果音を鳴らさない（合いの手のたびに鳴ると多すぎる）／最後に D01 へ戻る場面も止まらないようにした
使い方: python make_draw_audio_scripts.py <script_{tag}.json>  → 続けて python make_bgm_{tag}.py → python mix_{tag}.py"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
H = Path(__file__).resolve().parent
sp = Path(sys.argv[1]).resolve(); tag = sp.name.replace("script_", "").replace(".json", ""); L = sp.parent
SONG = ('SONG = {**{f"D{n:02d}.png": A for n in (1, 2, 3, 4, 5, 6, 7)}, **{f"D{n:02d}.png": B for n in (8, 9, 10, 11, 12, 13, 14)}, '
        '**{f"D{n:02d}.png": C for n in (15, 16, 17)}}')
KIND = ('KIND = {"D01": "open", "D02": "info", "D03": "data", "D04": "data", "D05": "data", "D06": "table", "D07": "news", "D08": "how", "D09": "table", "D10": "table",\n'
        '        "D11": "horse", "D12": "horse", "D13": "warn", "D14": "horse", "D15": "rank", "D16": "rank", "D17": "top3"}')

def swap_block(src, head, new):
    """head で始まる文（次の行が字下げなら続きも）を new に置き換える"""
    ls = src.split("\n"); i = next(k for k, l in enumerate(ls) if l.startswith(head)); j = i + 1
    while j < len(ls) and ls[j].startswith(" "): j += 1
    return "\n".join(ls[:i] + [new] + ls[j:])

# 場面の長さは build_video.py が書き出した _tmp/{tag}_secs.json（コマの倍数に切り上げた長さ）を使う＝映像・字幕と同じ時刻になる
SEC = ('_SECS = json.loads((D / "_tmp" / "' + tag + '_secs.json").read_text(encoding="utf-8"))\n'
       'def sec(i): return _SECS[str(i)]')
b = (H / "make_bgm_sections.py").read_text(encoding="utf-8")
b = swap_block(b, "def sec(i):", SEC)
b = swap_block(b, "SONG = ", SONG).replace("tospo_long", tag).replace('"_bgm_sections.mp3"', f'"_bgm_{tag}.mp3"').replace('D / "_tmp"', '(D / "_tmp")')
b = b.replace("segs, t = [], 0.0", '(D / "_tmp").mkdir(exist_ok=True)\nsegs, t = [], 0.0')
b = b.replace('song = SONG[s["image"]]', 'song = SONG[s["image"][:3] + ".png"]')   # 場面に動画（D09.mp4＝展開予想の3D）を置いても曲が決まるように
assert '[:3] + ".png"' in b
(L / f"make_bgm_{tag}.py").write_text(b, encoding="utf-8")

m = (H / "mix_long.py").read_text(encoding="utf-8")
m = swap_block(m, "def sec(i):", SEC)
m = swap_block(m, "KIND = ", KIND).replace("tospo_long", tag).replace('"_bgm_sections.mp3"', f'"_bgm_{tag}.mp3"')
m = m.replace('info=SES["ding2"])[kind]', 'info=SES["ding2"]).get(kind, SES["ding2"])')   # 最後に D01 へ戻る場面などで止まらないように
old = "    img = s[\"image\"][:3]; kind = KIND[img]; first = img != prev; n_in = 0 if first else n_in + 1\n"
assert old in m
m = m.replace(old, old + "    if s.get(\"speaker\") == \"fan\" and not first:      # 聞き役の合いの手では効果音を鳴らさない\n        prev = img; t += sec(s[\"id\"]); continue\n")
assert ".get(kind" in m and f"script_{tag}.json" in m
(L / f"mix_{tag}.py").write_text(m, encoding="utf-8")
print("書き出し:", L / f"make_bgm_{tag}.py", "/", L / f"mix_{tag}.py")
