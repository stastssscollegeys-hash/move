# -*- coding: utf-8 -*-
"""make_icons.py — 対話モードの丸アイコン（話している＝光る／話していない＝少し暗い）を作る（2026-11-19）

見せ方は taidan-movie-creator-ss の CharacterIcon と同じ考え方：
  話している方 ＝ 話し手の色の縁＋外側の光＋少し大きく（1.08倍）
  話していない方 ＝ 白い半透明の縁・全体を少し暗く（不透明度 0.7）
入力: 丸く切り抜いた顔の PNG（正方形）。出力: <名前>_on.png と <名前>_off.png（同じ大きさのキャンバス＝重ねる位置がずれない）
アイコンを作り直すときだけ使う（Pillow が要る: pip install pillow）。動画の組み立て（build_video.py）は出来上がった PNG を重ねるだけ。

使い方: python scripts/image/make_icons.py <顔.png（口を閉じた顔）> <出力の頭の名前> "<話し手の色 #RRGGBB>" [--size 128] [--open <口を開けた顔.png>]
  口を開けた顔の作り方：顔.png を chatgpt-image-devtools-ss で --attach して「口だけ開けた同じ絵」を作り、scripts/image/merge_mouth.py で口の所だけ元の絵に移す（ほかの所が動かない）
例:     python scripts/image/make_icons.py assets/icon_asumeshi.png assets/icon_asumeshi "#FF6EB4"
"""
import argparse
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance


def circle(img, size):
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("face"); ap.add_argument("out"); ap.add_argument("color")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--open", help="口を開けた顔の PNG（顔.png と同じ大きさ・同じ位置。あれば _on_open.png も作る）")
    a = ap.parse_args()
    col = tuple(int(a.color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    S = a.size
    C = int(S * 1.5)                      # キャンバス（光の分の余白）
    face = Image.open(a.face)

    # 話している方：少し大きく・話し手の色の縁・外側の光
    s_on = int(S * 1.08); bw = max(4, S // 22)

    def speaking(fc):
        on = Image.new("RGBA", (C, C), (0, 0, 0, 0))
        # 光：色は話し手の色のまま、ぼかすのは透明度だけ（2026-11-19 ユーザー「この四角い影見たいのなんとかならない?」
        #   前は RGBA ごとぼかして透明な所の黒が混ざり暗い影になり、しかもキャンバスの端で切れて四角に見えていた）
        m = Image.new("L", (C, C), 0)
        r = s_on // 2 + bw + 2
        ImageDraw.Draw(m).ellipse((C // 2 - r, C // 2 - r, C // 2 + r, C // 2 + r), fill=220)
        m = m.filter(ImageFilter.GaussianBlur(S // 16))
        fade = Image.new("L", (C, C), 0)                       # 端の手前で必ず0にする（四角く切れない）
        e = C // 2 - 2
        ImageDraw.Draw(fade).ellipse((C // 2 - e, C // 2 - e, C // 2 + e, C // 2 + e), fill=255)
        fade = fade.filter(ImageFilter.GaussianBlur(4))
        m = Image.composite(m, Image.new("L", (C, C), 0), fade)
        glow = Image.new("RGBA", (C, C), col + (0,))
        glow.putalpha(m)
        on.alpha_composite(glow)
        ring = Image.new("RGBA", (C, C), (0, 0, 0, 0))
        rr = s_on // 2 + bw
        ImageDraw.Draw(ring).ellipse((C // 2 - rr, C // 2 - rr, C // 2 + rr, C // 2 + rr), fill=col + (255,))
        on.alpha_composite(ring)
        on.alpha_composite(circle(fc, s_on), (C // 2 - s_on // 2, C // 2 - s_on // 2))
        return on

    speaking(face).save(a.out + "_on.png")
    if a.open:   # 2026-11-19 口パク用：口を開けた顔で同じ形の _on_open.png（build_video.py が声の出ている間だけ重ねる）
        speaking(Image.open(a.open)).save(a.out + "_on_open.png")

    # 話していない方：白い半透明の縁・少し暗く・不透明度 0.7
    off = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    rr = S // 2 + bw
    ImageDraw.Draw(off).ellipse((C // 2 - rr, C // 2 - rr, C // 2 + rr, C // 2 + rr), fill=(255, 255, 255, 140))
    f = circle(face, S)
    f = ImageEnhance.Brightness(f).enhance(0.78)
    f.putalpha(f.getchannel("A").point(lambda v: int(v * 0.85)))
    off.alpha_composite(f, (C // 2 - S // 2, C // 2 - S // 2))
    off.putalpha(off.getchannel("A").point(lambda v: int(v * 0.8)))
    off.save(a.out + "_off.png")
    print("できた:", a.out + "_on.png", a.out + "_off.png", f"（{C}x{C}）")


if __name__ == "__main__":
    main()
