# -*- coding: utf-8 -*-
"""merge_mouth.py — 口パク用：生成した「口だけ変えた絵」から、口の所だけを元の顔に移す（2026-11-19）

ChatGPT に元の顔を添付して「口だけ開けた同じ絵」を作ると、目・髪・輪郭も少しずつずれる。そのまま交互に出すと顔全体が揺れて見える。
→ 生成した絵を元と同じ大きさにし、位置のずれを探して合わせてから、口のまわりの楕円（ふちをぼかす）だけ元の顔に貼る。
使い方: python scripts/image/merge_mouth.py <元の顔.png> <生成した絵.png> <出力.png> --mouth 0.50,0.83,0.16,0.10
  --mouth = 口の真ん中 x,y と 横・縦の半径（どれも元の顔の幅に対する割合）
Pillow と numpy が要る。
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base"); ap.add_argument("gen"); ap.add_argument("out")
    ap.add_argument("--mouth", required=True)
    ap.add_argument("--search", type=int, default=12, help="位置のずれを探す幅（px）")
    a = ap.parse_args()
    base = Image.open(a.base).convert("RGBA")
    S = base.width
    gen = Image.open(a.gen).convert("RGBA").resize((S, S), Image.LANCZOS)
    cx, cy, rx, ry = (float(v) * S for v in a.mouth.split(","))

    # 位置合わせ：口の楕円の外（顔の残り）で、元との差が一番小さくなるずらし方を探す
    b = np.asarray(base.convert("L"), dtype=np.float32)
    g = np.asarray(gen.convert("L"), dtype=np.float32)
    yy, xx = np.mgrid[0:S, 0:S]
    ring = (((xx - cx) / (rx * 2.2)) ** 2 + ((yy - cy) / (ry * 2.2)) ** 2 <= 1) & \
           (((xx - cx) / (rx * 1.15)) ** 2 + ((yy - cy) / (ry * 1.15)) ** 2 > 1)   # 口のまわりの輪
    best = (1e18, 0, 0)
    for dy in range(-a.search, a.search + 1):
        for dx in range(-a.search, a.search + 1):
            sh = np.roll(np.roll(g, dy, 0), dx, 1)
            d = float(np.abs(sh - b)[ring].mean())
            if d < best[0]:
                best = (d, dx, dy)
    _, dx, dy = best
    moved = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    moved.paste(gen, (dx, dy))

    # 口の楕円だけ貼る（ふちはぼかす）
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(max(2, S // 80)))
    out = base.copy()
    out.paste(moved, (0, 0), m)
    out.putalpha(base.getchannel("A"))
    out.save(a.out)
    print(f"できた: {a.out}（ずらし dx={dx} dy={dy}・口のまわりの差 {best[0]:.1f}）")


if __name__ == "__main__":
    main()
