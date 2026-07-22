"""Generate orange/black GitHub stat cards as PNGs.

Usage:  python gen_cards.py OUT_DIR [username]

Pulls live data via the `gh` CLI (available both locally and on GitHub
Actions runners), then renders two matched cards. No third-party image
service is involved, so these can never rate-limit or 503.
"""
import json
import subprocess
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

CW, CH = 1200, 520
BG = (10, 10, 10)
CARD = (16, 15, 14)
ORANGE = (255, 122, 0)
AMBER = (255, 184, 0)
GREY = (145, 145, 150)
WHITE = (247, 244, 240)
BORDER = (48, 34, 20)


def font(names, size):
    for n in names:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + n, size)
        except OSError:
            continue
    for n in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


BOLD = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
REG = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
MONO = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"]


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout.strip()


def fetch(user):
    prof = json.loads(gh("api", f"users/{user}", "--jq", "{public_repos, followers}"))
    contrib = json.loads(gh(
        "api", "graphql", "-f",
        'query={ user(login: "%s") { contributionsCollection { '
        'contributionCalendar { totalContributions } totalCommitContributions } } }' % user,
        "--jq", ".data.user.contributionsCollection",
    ))
    repos = gh("api", f"users/{user}/repos?per_page=100", "--jq", ".[].name").splitlines()
    langs = {}
    for r in repos:
        try:
            data = json.loads(gh("api", f"repos/{user}/{r}/languages"))
        except subprocess.CalledProcessError:
            continue
        for k, v in data.items():
            langs[k] = langs.get(k, 0) + v
    return {
        "repos": prof["public_repos"],
        "followers": prof["followers"],
        "contributions": contrib["contributionCalendar"]["totalContributions"],
        "commits": contrib["totalCommitContributions"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
    }


def tracked(draw, xy, text, fnt, fill, tracking=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x - xy[0]


def new_card(title):
    img = Image.new("RGB", (CW, CH), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, CW - 3, CH - 3], radius=26, fill=CARD, outline=BORDER, width=2)

    t_f = font(BOLD, 36)
    tracked(d, (56, 46), title, t_f, ORANGE, 4)
    # accent underline under the title
    bar = Image.new("RGB", (150, 5))
    bd = ImageDraw.Draw(bar)
    for x in range(150):
        f = x / 149
        bd.line([(x, 0), (x, 5)], fill=tuple(int(ORANGE[k] * (1 - f) + AMBER[k] * f) for k in range(3)))
    img.paste(bar, (56, 104))
    return img, d


def stats_card(s, out):
    img, d = new_card("GITHUB STATS")
    label_f = font(REG, 34)
    value_f = font(BOLD, 46)

    rows = [
        ("Public repositories", s["repos"]),
        ("Contributions (this year)", s["contributions"]),
        ("Commits (this year)", s["commits"]),
        ("Followers", s["followers"]),
    ]
    # pass 1: collect positions and build a single additive glow layer.
    # (Blending per-row would darken the whole card cumulatively.)
    halo = Image.new("RGB", (CW, CH), (0, 0, 0))
    hd = ImageDraw.Draw(halo)
    placed = []
    y = 168
    for label, value in rows:
        txt = str(value)
        x = CW - 56 - hd.textlength(txt, font=value_f)
        hd.text((x, y), txt, font=value_f, fill=ORANGE)
        placed.append((label, txt, x, y))
        y += 82
    img = ImageChops.add(img, halo.filter(ImageFilter.GaussianBlur(16)))

    # pass 2: crisp foreground text on top of the glow
    d = ImageDraw.Draw(img)
    for label, txt, x, y in placed:
        d.text((56, y + 6), label, font=label_f, fill=GREY)
        d.text((x, y), txt, font=value_f, fill=WHITE)
    img.save(out, "PNG", optimize=True)
    print("wrote", out)


def langs_card(s, out, top=5):
    img, d = new_card("TOP LANGUAGES")
    name_f = font(REG, 30)
    pct_f = font(MONO, 28)

    langs = s["langs"][:top]
    total = sum(v for _, v in s["langs"]) or 1
    y = 170
    bar_x, bar_w, bar_h = 56, CW - 112, 14
    for i, (name, val) in enumerate(langs):
        pct = val / total * 100
        d.text((bar_x, y), name, font=name_f, fill=WHITE)
        ptxt = f"{pct:4.1f}%"
        d.text((CW - 56 - d.textlength(ptxt, font=pct_f), y + 3), ptxt, font=pct_f, fill=GREY)

        ty = y + 44
        d.rounded_rectangle([bar_x, ty, bar_x + bar_w, ty + bar_h], radius=7, fill=(34, 28, 22))
        fill_w = max(int(bar_w * pct / 100), 10)
        f = i / max(1, top - 1)
        col = tuple(int(ORANGE[k] * (1 - f) + AMBER[k] * f) for k in range(3))
        d.rounded_rectangle([bar_x, ty, bar_x + fill_w, ty + bar_h], radius=7, fill=col)
        y += 68
    img.save(out, "PNG", optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    out_dir = sys.argv[1].rstrip("/")
    user = sys.argv[2] if len(sys.argv) > 2 else "Ayush-Gupta-0212"
    s = fetch(user)
    print("data:", {k: v for k, v in s.items() if k != "langs"}, "| langs:", s["langs"][:6])
    stats_card(s, f"{out_dir}/card-stats.png")
    langs_card(s, f"{out_dir}/card-langs.png")
