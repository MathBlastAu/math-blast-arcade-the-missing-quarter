"""
pix.py - shared pixel-art toolkit for Math Blast Arcade.

Every sprite sheet, tile and background in the game is produced by the scripts
in this folder using these helpers, so the whole game shares one palette and
one set of shading rules.  Re-run `python3 art/build_all.py` to regenerate.
"""
from PIL import Image
import math, os, json, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
PREVIEW = os.path.join(ROOT, "art", "_preview")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(PREVIEW, exist_ok=True)


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ----------------------------------------------------------------------------
# MASTER PALETTE.  Ramps run dark -> light.  Use ramp neighbours for shading;
# do not invent new colours without adding them here.
# ----------------------------------------------------------------------------
RAMPS = {
    # outline / deepest shadow first
    "ink":    ["#080a14", "#0d1126", "#141a3a"],
    "navy":   ["#141a3a", "#1e2a5a", "#2b3f7e", "#3f5fae", "#6b8fd6", "#a9c5f0", "#e6f1ff"],
    "steel":  ["#161c2b", "#222c40", "#323f57", "#47566f", "#64758f", "#8c9db3", "#b9c7d6", "#e2eaf2"],
    "cyan":   ["#0a2b3a", "#0e4a5c", "#0f7480", "#12a3a6", "#2de0d0", "#8ff7ea", "#dcfffa"],
    "orange": ["#4a160e", "#8a2c10", "#c9471a", "#f26a22", "#ff9340", "#ffc46b", "#fff0b8"],
    "purple": ["#170c33", "#2a1657", "#472585", "#6f3fc0", "#a26bf0", "#cfa8ff", "#f0e0ff"],
    "green":  ["#08301e", "#0f5a33", "#1f8a4c", "#3fc468", "#7bea8a", "#c6ffc0"],
    "red":    ["#3a0a18", "#7a1228", "#b81f38", "#e8384f", "#ff7a7a", "#ffc0b8"],
    "gold":   ["#5a3300", "#96620a", "#d49a12", "#ffcf33", "#ffe97a", "#fffbd0"],
    "skin":   ["#5c3320", "#8f5433", "#c07d4e", "#e3a472", "#f6c898", "#ffe6c8"],
    "hair":   ["#1c100c", "#33201a", "#553526", "#7d5236"],
    "pink":   ["#5a1240", "#a8256a", "#e84a9a", "#ff8cc0", "#ffd0e6"],
}
C = {}
for _n, _r in RAMPS.items():
    for _i, _h in enumerate(_r):
        C[f"{_n}{_i}"] = hexc(_h)
C["none"] = (0, 0, 0, 0)
C["white"] = hexc("#ffffff")
C["black"] = hexc("#080a14")
OUT = C["ink0"]          # standard outer outline colour
T = (0, 0, 0, 0)


def ramp(name):
    return [hexc(h) for h in RAMPS[name]]


def with_alpha(c, a):
    return (c[0], c[1], c[2], a)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(4))


# ----------------------------------------------------------------------------
# Canvas helpers
# ----------------------------------------------------------------------------
def new(w, h, fill=T):
    return Image.new("RGBA", (w, h), fill)


def px(img, x, y, c):
    x = int(round(x)); y = int(round(y))
    if 0 <= x < img.width and 0 <= y < img.height and c is not None:
        if c[3] == 255 or c[3] == 0:
            img.putpixel((x, y), c)
        else:
            d = img.getpixel((x, y))
            a = c[3] / 255.0
            if d[3] == 0:
                img.putpixel((x, y), c)
            else:
                img.putpixel((x, y), (int(c[0]*a + d[0]*(1-a)), int(c[1]*a + d[1]*(1-a)),
                                      int(c[2]*a + d[2]*(1-a)), max(d[3], c[3])))


def get(img, x, y):
    if 0 <= x < img.width and 0 <= y < img.height:
        return img.getpixel((x, y))
    return T


def rect(img, x, y, w, h, c):
    for yy in range(int(y), int(y + h)):
        for xx in range(int(x), int(x + w)):
            px(img, xx, yy, c)


def hline(img, x0, x1, y, c):
    for x in range(int(min(x0, x1)), int(max(x0, x1)) + 1):
        px(img, x, y, c)


def vline(img, x, y0, y1, c):
    for y in range(int(min(y0, y1)), int(max(y0, y1)) + 1):
        px(img, x, y, c)


def line(img, x0, y0, x1, y1, c):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx = abs(x1 - x0); dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(img, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy


def disc(img, cx, cy, r, c):
    """Filled pixel circle. r may be fractional (x.5 gives even diameters)."""
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.3:
                px(img, x, y, c)


def ellipse(img, cx, cy, rx, ry, c):
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            if ((x - cx) / max(rx, 0.01)) ** 2 + ((y - cy) / max(ry, 0.01)) ** 2 <= 1.0:
                px(img, x, y, c)


def ring(img, cx, cy, r, c, thick=1.0):
    for y in range(int(cy - r - 2), int(cy + r + 3)):
        for x in range(int(cx - r - 2), int(cx + r + 3)):
            d = math.hypot(x - cx, y - cy)
            if r - thick < d <= r + 0.2:
                px(img, x, y, c)


def capsule(img, x0, y0, x1, y1, r, c):
    """Thick rounded segment (limbs, pipes)."""
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        t = i / n
        disc(img, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, c)


def paste(dst, src, x, y):
    dst.alpha_composite(src, (int(x), int(y))) if (0 <= x and 0 <= y and x + src.width <= dst.width and y + src.height <= dst.height) else _safe_paste(dst, src, int(x), int(y))


def _safe_paste(dst, src, x, y):
    for yy in range(src.height):
        for xx in range(src.width):
            c = src.getpixel((xx, yy))
            if c[3]:
                px(dst, x + xx, y + yy, c)


def ascii_sprite(rows, cmap):
    """Build an image from rows of characters. '.' and ' ' are transparent."""
    h = len(rows); w = max(len(r) for r in rows)
    img = new(w, h)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in ". ":
                continue
            if ch not in cmap:
                raise KeyError(f"char {ch!r} not in cmap (row {y}: {r})")
            img.putpixel((x, y), cmap[ch])
    return img


def flip_h(img):
    return img.transpose(Image.FLIP_LEFT_RIGHT)


def outline(img, c=None, diagonal=False, only_empty=True):
    """Add a 1px outline around opaque pixels (drawn only on transparent pixels)."""
    c = c or OUT
    out = img.copy()
    w, h = img.size
    src = img.load()
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diagonal:
        nb += [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 40:
                continue
            for dx, dy in nb:
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and src[xx, yy][3] > 40:
                    out.putpixel((x, y), c)
                    break
    return out


def replace(img, mapping):
    """Palette swap: mapping {rgba_from: rgba_to}."""
    out = img.copy()
    p = out.load()
    for y in range(out.height):
        for x in range(out.width):
            c = p[x, y]
            if c in mapping:
                p[x, y] = mapping[c]
    return out


def ramp_swap(img, src_ramp, dst_ramp):
    a, b = ramp(src_ramp), ramp(dst_ramp)
    m = {}
    for i, c in enumerate(a):
        j = min(len(b) - 1, round(i * (len(b) - 1) / max(1, len(a) - 1)))
        m[c] = b[j]
    return replace(img, m)


def tint_alpha(img, mult):
    out = img.copy(); p = out.load()
    for y in range(out.height):
        for x in range(out.width):
            c = p[x, y]
            p[x, y] = (c[0], c[1], c[2], int(c[3] * mult))
    return out


# 4x4 Bayer matrix for ordered dithering (pixel-art gradients)
BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dither_pick(colors, t, x, y):
    """Pick a colour from an ordered list for position t in 0..1 with Bayer dithering."""
    n = len(colors) - 1
    f = max(0.0, min(1.0, t)) * n
    i = int(math.floor(f))
    frac = f - i
    thr = (BAYER4[y % 4][x % 4] + 0.5) / 16.0
    if frac > thr and i < n:
        i += 1
    return colors[min(i, n)]


def glow_sprite(size, color, power=2.0, max_alpha=255):
    """Soft radial glow for additive lights (smooth, not dithered)."""
    img = new(size, size)
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            a = max(0.0, 1.0 - d) ** power
            img.putpixel((x, y), (color[0], color[1], color[2], int(max_alpha * a)))
    return img


# ----------------------------------------------------------------------------
# Sheets, saving, previews, manifest
# ----------------------------------------------------------------------------
def sheet(frames, cols=None, pad=0):
    fw, fh = frames[0].size
    cols = cols or len(frames)
    rows = (len(frames) + cols - 1) // cols
    img = new(cols * (fw + pad), rows * (fh + pad))
    for i, f in enumerate(frames):
        img.alpha_composite(f, ((i % cols) * (fw + pad), (i // cols) * (fh + pad)))
    return img


def save(img, name):
    path = os.path.join(ASSETS, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)
    return path


def preview(img, name, scale=6, bg="#2b3f7e", grid=None):
    """Write an upscaled preview on a flat background so it can be eyeballed."""
    w, h = img.size
    out = Image.new("RGBA", (w * scale, h * scale), hexc(bg))
    big = img.resize((w * scale, h * scale), Image.NEAREST)
    out.alpha_composite(big)
    if grid:
        gc = (255, 255, 255, 40)
        for gx in range(0, w, grid[0]):
            for y in range(h * scale):
                out.putpixel((gx * scale, y), gc)
        for gy in range(0, h, grid[1]):
            for x in range(w * scale):
                out.putpixel((x, gy * scale), gc)
    path = os.path.join(PREVIEW, name)
    out.convert("RGB").save(path)
    return path


MANIFEST_DIR = os.path.join(ASSETS, "manifest")


def manifest(part, data):
    """Each art script writes its own manifest fragment: assets/manifest/<part>.json
    Format:
      { "sheets": { key: {"file": "sprites/x.png", "fw": 32, "fh": 32,
                           "anims": { name: {"frames": [..], "fps": 10, "loop": true} } } },
        "images": { key: {"file": "bg/x.png"} } }
    """
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    with open(os.path.join(MANIFEST_DIR, part + ".json"), "w") as f:
        json.dump(data, f, indent=1)
