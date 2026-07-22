"""Generate the profile hero banner.

Usage:  python gen_banner.py OUT.png [AVATAR.png]

Palette (matches README design system) - ORANGE / BLACK:
  bg #0A0A0A | orange #FF7A00 | amber #FFB800 | ember #E23C00 | grey #919196
"""
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 2400, 540
BG = (10, 10, 10)
ORANGE = (255, 122, 0)
AMBER = (255, 184, 0)
EMBER = (226, 60, 0)
GREY = (145, 145, 150)
WHITE = (247, 244, 240)


def font(names, size):
    for n in names:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + n, size)
        except OSError:
            continue
    return ImageFont.load_default()


BOLD = ["segoeuib.ttf", "arialbd.ttf"]
MONO = ["consola.ttf", "cour.ttf"]


def glow_blob(cx, cy, radius, color, intensity=1.0):
    """Soft additive radial light, rendered small then upscaled for smoothness."""
    s = 6
    layer = Image.new("RGB", (W // s, H // s), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 48
    for i in range(steps, 0, -1):
        f = i / steps
        r = int(radius * f / s)
        a = (1 - f) ** 2 * intensity
        d.ellipse(
            [cx // s - r, cy // s - r, cx // s + r, cy // s + r],
            fill=(int(color[0] * a), int(color[1] * a), int(color[2] * a)),
        )
    return layer.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))


def tracked_text(draw, xy, text, fnt, fill, tracking=0, center=False):
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if center:
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking
    return total


def gradient_bar(w, h, c1, c2):
    bar = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(bar)
    for x in range(w):
        f = x / max(1, w - 1)
        d.line([(x, 0), (x, h)], fill=tuple(int(c1[k] * (1 - f) + c2[k] * f) for k in range(3)))
    return bar


def circular_avatar(path, size=340, ring=16):
    """Avatar cropped to a circle with an orange->amber gradient ring + glow."""
    box = size + ring * 2 + 60
    av = Image.open(path).convert("RGB")
    side = min(av.size)
    av = av.crop(((av.width - side) // 2, (av.height - side) // 2,
                  (av.width + side) // 2, (av.height + side) // 2)).resize((size, size), Image.LANCZOS)

    # triangle-wave interpolation so the gradient ends meet seamlessly
    ring_img = Image.new("RGB", (box, box), (0, 0, 0))
    rd = ImageDraw.Draw(ring_img)
    o = 30
    segs = 240
    for i in range(segs):
        f = i / segs
        t = 1 - abs(2 * f - 1)
        col = tuple(int(ORANGE[k] * (1 - t) + AMBER[k] * t) for k in range(3))
        rd.arc([o, o, box - o, box - o], start=-90 + f * 360,
               end=-90 + (f + 1) / segs * 360 + 1.5, fill=col, width=ring)

    glow = ring_img.filter(ImageFilter.GaussianBlur(24))

    # ring + glow are additive light; the avatar itself must NOT be, or its
    # colours blow out. Returned separately so build() composites correctly.
    light = ImageChops.add(glow, ring_img)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    return light, av, mask, box, o + ring


def build(out_path, avatar_path=None):
    img = Image.new("RGB", (W, H), BG)

    # ambient warm lighting -------------------------------------------------
    img = ImageChops.add(img, glow_blob(int(W * 0.22), int(H * 0.45), 900, ORANGE, 0.40))
    img = ImageChops.add(img, glow_blob(int(W * 0.80), int(H * 0.55), 900, EMBER, 0.36))

    # subtle dot grid -------------------------------------------------------
    dots = Image.new("RGB", (W, H), (0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for y in range(0, H, 40):
        for x in range(0, W, 40):
            dd.ellipse([x, y, x + 2, y + 2], fill=(38, 30, 24))
    img = ImageChops.add(img, dots)

    # avatar ----------------------------------------------------------------
    text_cx = W // 2
    if avatar_path:
        light, av, av_mask, box, inner = circular_avatar(avatar_path)
        ax, ay = 250, (H - box) // 2
        img.paste(ImageChops.add(img.crop((ax, ay, ax + box, ay + box)), light), (ax, ay))
        img.paste(av, (ax + inner, ay + inner), av_mask)
        text_cx = (ax + box + W - 160) // 2

    # typography ------------------------------------------------------------
    name_f = font(BOLD, 128)
    sub_f = font(MONO, 40)
    name_y = H // 2 - 116
    sub_y = H // 2 + 56

    halo = Image.new("RGB", (W, H), (0, 0, 0))
    tracked_text(ImageDraw.Draw(halo), (text_cx, name_y), "AYUSH GUPTA", name_f, ORANGE, 10, center=True)
    img = ImageChops.add(img, halo.filter(ImageFilter.GaussianBlur(30)))

    d = ImageDraw.Draw(img)
    tracked_text(d, (text_cx, name_y), "AYUSH GUPTA", name_f, WHITE, 10, center=True)
    tracked_text(d, (text_cx, sub_y), "CS STUDENT  ·  FULL-STACK DEVELOPER", sub_f, GREY, 6, center=True)

    # gradient accent underline ---------------------------------------------
    bw, bh = 340, 7
    img.paste(gradient_bar(bw, bh, ORANGE, AMBER), (text_cx - bw // 2, sub_y + 92))

    img.save(out_path, "PNG", optimize=True)
    print("wrote", out_path, img.size)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
