"""
2026/04/26 フローラS + マイラーズC 合成サムネイル v3
- 右下キャラクター除去（125%拡大→左側クロップで右端を画面外へ）
- テキストスタイル: v3準拠（白文字 + 太い黒アウトライン）
"""
import sys, math
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont
import numpy as np

FLORA_PATH  = r"C:\Users\User\Desktop\競馬予想レポート\note_bg_flora2026.png"
MILERS_PATH = r"C:\Users\User\Desktop\競馬予想レポート\note_bg_milers2026.png"
OUTPUT_PATH = r"C:\Users\User\Desktop\競馬予想レポート\20260426\note_header_20260426_combined.png"

W, H = 1280, 720

# ── 1. 画像読み込み ──
flora = Image.open(FLORA_PATH).convert("RGB").resize((W, H), Image.LANCZOS)

# マイラーズC: 125%幅に拡大→左側をクロップ（右端のキャラを画面外へ押し出す）
milers_src = Image.open(MILERS_PATH).convert("RGB")
mw = int(W * 1.25)  # 125% = 1600px
milers_large = milers_src.resize((mw, H), Image.LANCZOS)
milers = milers_large.crop((0, 0, W, H))   # 左端から取る → 右端のキャラが消える

fa = np.array(flora,  dtype=np.float32)
ma = np.array(milers, dtype=np.float32)

# ── 2. S字（コサイン）グラデーションブレンド ──
half  = W // 2
blend = 320

alpha = np.ones(W, dtype=np.float32)
alpha[half + blend // 2 :] = 0.0
for i in range(blend):
    x = half - blend // 2 + i
    if 0 <= x < W:
        t = i / blend
        alpha[x] = 0.5 * (1.0 + math.cos(math.pi * t))

a3 = alpha[np.newaxis, :, np.newaxis]
merged = Image.fromarray((fa * a3 + ma * (1 - a3)).astype(np.uint8))
result = merged.convert("RGBA")

# ── 3. 上下バー ──
def add_rect(img, x1, y1, x2, y2, color):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([(x1, y1), (x2, y2)], fill=color)
    return Image.alpha_composite(img, ov)

result = add_rect(result, 0, 0,     W, 150,   (0, 0, 0, 185))
result = add_rect(result, 0, H-190, W, H,     (0, 0, 0, 210))

# ── 4. フォント ──
FONTS = [
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
]

def get_font(size):
    for p in FONTS:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()

def txt(draw, pos, text, font, color=(255, 255, 255), stroke_color=(0, 0, 0), stroke=5):
    """v3スタイル: 白文字 + 太い黒アウトライン（Pillowのstroke機能）"""
    x, y = pos
    draw.text(
        (x, y), text, font=font,
        fill=(*color, 255),
        stroke_width=stroke,
        stroke_fill=(*stroke_color, 255),
        anchor="mm"
    )

draw = ImageDraw.Draw(result)

# ── 5. 上バー：レース名 ──
txt(draw, (W//4,   75), "フローラS(G2)",
    get_font(72), (255, 255, 255), (20, 0, 30), stroke=6)

txt(draw, (3*W//4, 75), "マイラーズC(G2)",
    get_font(72), (255, 255, 255), (0, 10, 40), stroke=6)

# ── 6. 下バー：投資→回収（最大化）+ 回収率 ──
txt(draw, (W//2, H - 125),
    "20,000円  →  52,800円",
    get_font(94), (255, 215, 0), (60, 30, 0), stroke=7)

txt(draw, (W//2, H - 40),
    "回収率  264%",
    get_font(54), (255, 255, 255), (0, 0, 0), stroke=5)

# ── 7. 保存 ──
result.convert("RGB").save(OUTPUT_PATH, quality=95)
print(f"完了: {OUTPUT_PATH}")
