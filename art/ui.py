"""
ui.py - UI kit and bitmap fonts for Math Blast Arcade (manifest part "ui").

Produces (see ASSET_SPEC.md, PART "ui", tables "UI" and "Bitmap fonts"):
  images  panel, panel_holo, panel_light, tag, logo
  sheets  button, hud, touch
  fonts   ui20, ui28, ui44 (Fredoka, anti-aliased) and pix8 (Press Start 2P, 1-bit)

Re-run with:  cd art && python3 ui.py            (everything)
              cd art && python3 ui.py fonts hud  (only some sections, previews only -
                                                  the manifest is written on a full run)
"""
import math
import os
import random
import shutil
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

import pix
from pix import C, T, new, px, save, preview, hexc, with_alpha, mix

FONT_SRC = os.path.join(pix.ASSETS, "fonts", "src")
FONT_SCRATCH = "/tmp/claude-0/-home-claude/e591b5bb-0faf-58c8-bbf8-464f19e84f37/scratchpad/fonts"
FONT_FILES = {
    "Fredoka.ttf": "Fredoka-OFL.txt",
    "PressStart2P.ttf": "PressStart2P-OFL.txt",
}


def font_path(name):
    """Fonts live in assets/fonts/src (copied there with their licences on first run)."""
    os.makedirs(FONT_SRC, exist_ok=True)
    for f in (name, FONT_FILES[name]):
        dst = os.path.join(FONT_SRC, f)
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(FONT_SCRATCH, f), dst)
    return os.path.join(FONT_SRC, name)


# =============================================================================
# BITMAP FONTS
# =============================================================================
GLYPHS = [chr(i) for i in range(32, 127)] + list("’‘“”–—…×÷½¼¾←→↑↓°")
ARROWS = "←→↑↓"


def _load(ttf, size, weight=None, raqm=False):
    kw = {"layout_engine": ImageFont.Layout.RAQM} if raqm else {"layout_engine": ImageFont.Layout.BASIC}
    f = ImageFont.truetype(font_path(ttf), size, **kw)
    if weight is not None:
        axes = f.get_variation_axes()
        vals = []
        for a in axes:                       # keep every axis at default except weight
            nm = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
            vals.append(weight if nm.lower().startswith("we") or nm == "wght" else
                        (100 if nm.lower().startswith("wi") or nm == "wdth" else a["default"]))
        f.set_variation_by_axes(vals)
    return f


def _ink(font, ch, size, onebit):
    """Render one glyph; return (alpha image cropped to ink, xoffset, yoffset) relative
    to the pen position / line top.  None if no ink."""
    pad = size * 2
    im = Image.new("L", (size * 5, size * 5), 0)
    d = ImageDraw.Draw(im)
    if onebit:
        d.fontmode = "1"
    d.text((pad, pad), ch, font=font, fill=255, anchor="la")
    bb = im.getbbox()
    if not bb:
        return None
    return im.crop(bb), bb[0] - pad, bb[1] - pad


def _has_glyph(font, ch, size, onebit, notdef):
    if ch == " ":
        return True
    g = _ink(font, ch, size, onebit)
    if g is None:
        return False
    return not (notdef is not None and g[0].size == notdef[0].size and g[0].tobytes() == notdef[0].tobytes())


def _synth_arrow(ch, size, stem, ascent):
    """Fredoka has no arrows: draw round-capped ones that match its stroke weight."""
    ss = 8
    w = int(round(size * 0.80)); h = int(round(size * 0.62))
    W, H = (w, h) if ch in "←→" else (h, w)
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    t = stem * ss

    def seg(a, b):
        d.line([a, b], fill=255, width=int(round(t)))
        for p in (a, b):
            d.ellipse([p[0] - t / 2, p[1] - t / 2, p[0] + t / 2, p[1] + t / 2], fill=255)
    m = t / 2 + ss * 0.25
    L, R, cy = m, w * ss - m, h * ss / 2
    head = h * ss / 2 - m
    pts = [((L, cy), (R, cy)), ((R, cy), (R - head, cy - head)), ((R, cy), (R - head, cy + head))]

    def tf(p):
        x, y = p
        if ch == "→":
            return (x, y)
        if ch == "←":
            return (w * ss - x, y)
        if ch == "↑":
            return (y, w * ss - x)
        return (y, x)                         # ↓
    for a, b in pts:
        seg(tf(a), tf(b))
    im = im.resize((W, H), Image.BOX)
    bb = im.getbbox()
    im = im.crop(bb)
    side = max(1, int(round(size * 0.06)))
    adv = W + side * 2
    mid = ascent - size * 0.36                # optical centre of the lowercase/figures
    return im, side + bb[0], int(round(mid - H / 2.0)) + bb[1], adv


def build_font(key, ttf, size, weight=None, onebit=False, face=None):
    font = _load(ttf, size, weight)          # BASIC layout: renders the (auto-hinted, crisp) glyphs
    try:                                     # RAQM layout: true linear advances + GPOS kerning.
        fadv = _load(ttf, size, weight, raqm=True)   # (BASIC getlength returns hinted advances that
        fadv.getlength("a")                          #  are ~6% too wide for Fredoka at 20px.)
    except Exception as e:
        print("  ! raqm layout unavailable, falling back to hinted advances:", e)
        fadv = None

    def advance(ch):
        return int(round((fadv or font).getlength(ch)))
    ascent, descent = font.getmetrics()
    line_h, base = ascent + descent, ascent
    notdef = _ink(font, chr(0xFFFF), size, onebit)   # the font's "missing glyph" box

    if weight is not None:                   # prove the variable-font weight really applied
        cov = {}
        for w in (300, weight):
            fw = _load(ttf, size, w)
            g = _ink(fw, "H", size, False)[0]
            cov[w] = sum(g.tobytes())
        assert cov[weight] > cov[300] * 1.15, f"variable weight not applied: {cov}"

    stem = None
    if weight is not None:                   # measure the stem of 'l' for the synthetic arrows
        g = _ink(font, "l", size, False)[0]
        row = g.crop((0, g.height // 2, g.width, g.height // 2 + 1))
        stem = sum(row.tobytes()) / 255.0

    glyphs = []                              # (ch, img|None, xoff, yoff, xadv)
    skipped = []
    for ch in GLYPHS:
        if ch == " ":
            glyphs.append((ch, None, 0, 0, advance(ch)))
            continue
        if _has_glyph(font, ch, size, onebit, notdef):
            im, xo, yo = _ink(font, ch, size, onebit)
            glyphs.append((ch, im, xo, yo, advance(ch)))
        elif ch in ARROWS and stem:
            im, xo, yo, adv = _synth_arrow(ch, size, stem, ascent)
            glyphs.append((ch, im, xo, yo, adv))
        else:
            skipped.append(ch)

    # ---- shelf-pack, 2px transparent padding, power-of-two atlas, width <= 512
    PAD = 2
    order = sorted([g for g in glyphs if g[1] is not None], key=lambda g: (-g[1].height, -g[1].width))

    def pack(W):
        x = y = PAD; rowh = 0; pos = {}
        for g in order:
            w, h = g[1].size
            if x + w + PAD > W:
                x = PAD; y += rowh + PAD; rowh = 0
            pos[g[0]] = (x, y)
            x += w + PAD; rowh = max(rowh, h)
        return pos, y + rowh + PAD
    for W in (64, 128, 256, 512):
        pos, used = pack(W)
        Hh = 1
        while Hh < used:
            Hh *= 2
        if Hh <= W or W == 512:
            break
    atlas = Image.new("RGBA", (W, Hh), (255, 255, 255, 0))
    for g in order:
        ch, im = g[0], g[1]
        if onebit:
            im = im.point(lambda v: 255 if v >= 128 else 0)
        white = Image.new("RGBA", im.size, (255, 255, 255, 255))
        white.putalpha(im)
        atlas.paste(white, pos[ch])
    save(atlas, f"fonts/{key}.png")

    # ---- kerning pairs (GPOS, via raqm) - Phaser applies <kerning> when present
    kerns = []
    if weight is not None and fadv is not None:
        try:
            fr = fadv
            chars = [g[0] for g in glyphs if g[1] is not None and g[0] not in ARROWS]
            adv1 = {c: fr.getlength(c, features=["-liga"]) for c in chars}
            for a in chars:
                for b in chars:
                    k = fr.getlength(a + b, features=["-liga"]) - adv1[a] - adv1[b]
                    if abs(k) >= 0.7:
                        kerns.append((ord(a), ord(b), int(round(k)) or (-1 if k < 0 else 1)))
        except Exception as e:               # raqm missing: font still valid, just unkerned
            print("  (no kerning data:", e, ")")

    # ---- BMFont XML
    face = face or ttf.replace(".ttf", "")
    L = ['<?xml version="1.0"?>', "<font>",
         f'  <info face="{face}" size="{size}" bold="0" italic="0" charset="" unicode="1" stretchH="100" '
         f'smooth="{0 if onebit else 1}" aa="{0 if onebit else 1}" padding="0,0,0,0" spacing="{PAD},{PAD}" outline="0"/>',
         f'  <common lineHeight="{line_h}" base="{base}" scaleW="{W}" scaleH="{Hh}" pages="1" packed="0"/>',
         f'  <pages><page id="0" file="{key}.png"/></pages>',
         f'  <chars count="{len(glyphs)}">']
    for ch, im, xo, yo, adv in glyphs:
        if im is None:
            x = y = w = h = 0
        else:
            (x, y), (w, h) = pos[ch], im.size
        L.append(f'    <char id="{ord(ch)}" x="{x}" y="{y}" width="{w}" height="{h}" xoffset="{xo}" '
                 f'yoffset="{yo}" xadvance="{adv}" page="0" chnl="15"/>')
    L.append("  </chars>")
    if kerns:
        L.append(f'  <kernings count="{len(kerns)}">')
        for a, b, k in kerns:
            L.append(f'    <kerning first="{a}" second="{b}" amount="{k}"/>')
        L.append("  </kernings>")
    L.append("</font>")
    with open(os.path.join(pix.ASSETS, "fonts", f"{key}.fnt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"  font {key}: {len(glyphs)} glyphs, atlas {W}x{Hh}, lineHeight {line_h}, base {base}, "
          f"{len(kerns)} kerning pairs, skipped {''.join(skipped) or '-'}")
    return {"png": f"fonts/{key}.png", "fnt": f"fonts/{key}.fnt"}


class BMFont:
    """Minimal BMFont reader/typesetter - reads back OUR OWN .fnt + .png exactly the
    way Phaser does, so previews prove the exported data (not PIL) is right."""

    def __init__(self, key):
        root = ET.parse(os.path.join(pix.ASSETS, "fonts", f"{key}.fnt")).getroot()
        com = root.find("common")
        self.line_h = int(com.get("lineHeight")); self.base = int(com.get("base"))
        self.png = Image.open(os.path.join(pix.ASSETS, "fonts", root.find("pages/page").get("file"))).convert("RGBA")
        assert self.png.size == (int(com.get("scaleW")), int(com.get("scaleH")))
        self.ch = {}
        for c in root.iter("char"):
            self.ch[int(c.get("id"))] = {k: int(c.get(k)) for k in
                                         ("x", "y", "width", "height", "xoffset", "yoffset", "xadvance")}
        self.kern = {(int(k.get("first")), int(k.get("second"))): int(k.get("amount")) for k in root.iter("kerning")}

    def width(self, text):
        x = 0; prev = None
        for chh in text:
            g = self.ch.get(ord(chh))
            if not g:
                continue
            x += self.kern.get((prev, ord(chh)), 0) + g["xadvance"]; prev = ord(chh)
        return x

    def draw(self, dst, x, y, text, color=(255, 255, 255, 255), scale=1):
        """Draw text with its line top at (x, y). Returns the end pen x."""
        pen = x; prev = None
        for chh in text:
            if chh == "\n":
                pen = x; y += self.line_h * scale; prev = None
                continue
            g = self.ch.get(ord(chh))
            if not g:
                continue
            pen += self.kern.get((prev, ord(chh)), 0) * scale
            if g["width"]:
                gi = self.png.crop((g["x"], g["y"], g["x"] + g["width"], g["y"] + g["height"]))
                r, gg, b, a = gi.split()
                a = a.point(lambda v: v * color[3] // 255)
                tinted = Image.merge("RGBA", (r.point(lambda v: v * color[0] // 255),
                                              gg.point(lambda v: v * color[1] // 255),
                                              b.point(lambda v: v * color[2] // 255), a))
                if scale != 1:
                    tinted = tinted.resize((tinted.width * scale, tinted.height * scale), Image.NEAREST)
                dx, dy = pen + g["xoffset"] * scale, y + g["yoffset"] * scale
                layer = Image.new("RGBA", dst.size, (0, 0, 0, 0))
                layer.paste(tinted, (dx, dy))
                dst.alpha_composite(layer)
            pen += g["xadvance"] * scale; prev = ord(chh)
        return pen

    def wrap(self, text, maxw):
        out = []; cur = ""
        for word in text.split(" "):
            t = (cur + " " + word).strip()
            if self.width(t) <= maxw or not cur:
                cur = t
            else:
                out.append(cur); cur = word
        out.append(cur)
        return out


TEST = "Three quarters plus one quarter makes one whole! 1/4 + 2/4 = 3/4 (Jake's goggles — ½ ¼ ¾)"


def font_previews():
    """Typeset the test sentence from the exported .fnt/.png, with metric guides."""
    rows = []
    for key in ("ui20", "ui28", "ui44", "pix8"):
        f = BMFont(key)
        sc = 2 if key == "pix8" else 1
        lines = f.wrap(TEST, 1180 // sc)
        lines += ["AV To Yo Wa P. r, ff fi  gjpqy QJ|_{}[]@#$%&*  0123456789  “quote” ‘q’ … × ÷ ° – ← → ↑ ↓"]
        lines = [l2 for l in lines for l2 in f.wrap(l, 1180 // sc)]
        h = (len(lines) * f.line_h) * sc + 16
        im = Image.new("RGBA", (1220, h), hexc("#141a3a"))
        d = ImageDraw.Draw(im)
        for i in range(len(lines)):
            top = 8 + i * f.line_h * sc
            d.line([(0, top), (1220, top)], fill=(63, 95, 174, 110))                       # line top
            d.line([(0, top + f.base * sc), (1220, top + f.base * sc)], fill=(232, 56, 79, 120))  # baseline
            d.line([(0, top + f.line_h * sc - 1), (1220, top + f.line_h * sc - 1)], fill=(63, 95, 174, 60))
        for i, l in enumerate(lines):
            f.draw(im, 16, 8 + i * f.line_h * sc, l, scale=sc)
        rows.append(im)
        # atlas preview too
        at = Image.new("RGBA", f.png.size, hexc("#141a3a")); at.alpha_composite(f.png)
        at.convert("RGB").save(os.path.join(pix.PREVIEW, f"ui_font_atlas_{key}.png"))
    H = sum(r.height for r in rows) + 6 * (len(rows) - 1)
    out = Image.new("RGBA", (1220, H), hexc("#080a14"))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y)); y += r.height + 6
    out.convert("RGB").save(os.path.join(pix.PREVIEW, "ui_font_test.png"))
    # clean version without guides, as the player would see it (white + tinted)
    rows = []
    for key, col in (("ui20", C["white"]), ("ui28", C["gold3"]), ("ui44", C["cyan4"]), ("pix8", C["white"])):
        f = BMFont(key); sc = 2 if key == "pix8" else 1
        lines = f.wrap(TEST, 1180 // sc)
        im = Image.new("RGBA", (1220, len(lines) * f.line_h * sc + 16), hexc("#141a3a"))
        for i, l in enumerate(lines):
            f.draw(im, 16, 8 + i * f.line_h * sc, l, color=col, scale=sc)
        rows.append(im)
    out = Image.new("RGBA", (1220, sum(r.height for r in rows)), hexc("#141a3a"))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y)); y += r.height
    out.convert("RGB").save(os.path.join(pix.PREVIEW, "ui_font_clean.png"))


def build_fonts():
    out = {}
    out["ui20"] = build_font("ui20", "Fredoka.ttf", 20, 600, face="Fredoka SemiBold")
    out["ui28"] = build_font("ui28", "Fredoka.ttf", 28, 600, face="Fredoka SemiBold")
    out["ui44"] = build_font("ui44", "Fredoka.ttf", 44, 700, face="Fredoka Bold")
    out["pix8"] = build_font("pix8", "PressStart2P.ttf", 8, None, onebit=True, face="Press Start 2P")
    font_previews()
    return out


# =============================================================================
# 9-SLICE PANELS, BUTTON, TAG
# =============================================================================
def rings(W, H, cuts):
    """Inset-ring index and facing side for every pixel of a chamfered rectangle.
    cuts = (tl, tr, br, bl) corner-cut sizes.  ring 0 = outermost pixel ring,
    negative = outside the shape.  side in t,l,b,r,tl,tr,br,bl (which edge is nearest)."""
    tl, tr, br, bl = cuts
    out = {}
    for y in range(H):
        for x in range(W):
            cands = [(y, "t"), (x, "l"), (H - 1 - y, "b"), (W - 1 - x, "r"),
                     (x + y - tl, "tl"), ((W - 1 - x) + y - tr, "tr"),
                     ((W - 1 - x) + (H - 1 - y) - br, "br"), (x + (H - 1 - y) - bl, "bl")]
            out[x, y] = min(cands, key=lambda t: t[0])
    return out


LIGHT = ("t", "l", "tl")                    # sides that face the top-left light


def frame(W, H, cuts, shader):
    """shader(r, side, x, y) -> colour for ring r (>=0)."""
    img = new(W, H)
    for (x, y), (r, side) in rings(W, H, cuts).items():
        if r >= 0:
            c = shader(r, side, x, y)
            if c is not None:
                img.putpixel((x, y), c)
    return img


def check9(img, c, name):
    """A 9-slice source must be uniform along each stretch axis."""
    W, H = img.size
    p = img.load()
    for y in range(H):
        for x in range(c, W - c):
            assert p[x, y] == p[c, y], f"{name}: row {y} not uniform at x={x}"
    for x in range(W):
        for y in range(c, H - c):
            assert p[x, y] == p[x, c], f"{name}: col {x} not uniform at y={y}"


def nine(img, w, h, c):
    """Stretch a 9-slice source to w x h (what Phaser's NineSlice does)."""
    W, H = img.size
    out = new(w, h)
    xs = [(0, c, 0, c), (c, W - c, c, w - c), (W - c, W, w - c, w)]
    ys = [(0, c, 0, c), (c, H - c, c, h - c), (H - c, H, h - c, h)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if dx1 > dx0 and dy1 > dy0:
                out.paste(img.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.NEAREST), (dx0, dy0))
    return out


def corner_zone(x, y, W, H, n):
    """True inside the n x n squares at the four corners (for corner brackets)."""
    return (x < n or x >= W - n) and (y < n or y >= H - n)


def make_panel():
    """Dark navy glass panel: ink keyline, cyan border lit from the top-left with a
    soft teal inner glow, bright 2px corner brackets and gold-tipped cut corners."""
    W = H = 24
    fill = with_alpha(C["navy0"], 235)
    glow1 = with_alpha(mix(C["navy0"], C["cyan1"], 0.75), 245)
    glow2 = with_alpha(mix(C["navy0"], C["cyan0"], 0.60), 240)

    def sh(r, side, x, y):
        cz = corner_zone(x, y, W, H, 7)
        cut = side in ("tl", "br")
        if r == 0:
            return C["ink0"]
        if r == 1:
            if cut:
                return C["gold4"] if side == "tl" else C["gold3"]
            if cz:
                return C["cyan6"] if side in LIGHT else C["cyan5"]
            return C["cyan4"] if side in LIGHT else C["cyan3"]
        if r == 2:
            if cut:
                return C["gold2"] if side == "tl" else C["gold1"]
            if cz:
                return C["cyan4"] if side in LIGHT else C["cyan3"]
            return glow1
        if r == 3:
            return glow2
        return fill
    img = frame(W, H, (6, 2, 6, 2), sh)
    check9(img, 8, "panel")
    return img


def make_panel_holo():
    """Translucent teal console glass: no ink keyline, glowing border, white-hot corners."""
    W = H = 24
    fill = with_alpha(mix(C["cyan0"], C["cyan1"], 0.55), 178)

    def sh(r, side, x, y):
        cz = corner_zone(x, y, W, H, 7)
        if r == 0:
            return with_alpha(C["cyan3"], 120)             # outer glow
        if r == 1:
            if cz:
                return C["cyan6"]
            return C["cyan5"] if side in LIGHT else C["cyan4"]
        if r == 2:
            if cz:
                return with_alpha(C["cyan4"], 240)
            return with_alpha(C["cyan2"], 220)
        if r == 3:
            return with_alpha(mix(C["cyan1"], C["cyan2"], 0.35), 195)
        return fill
    img = frame(W, H, (6, 2, 6, 2), sh)
    check9(img, 8, "panel_holo")
    return img


def make_panel_light():
    """Light results card: pale blue-white paper, navy keyline and trim, cyan corner
    brackets, gold cut corners (same family as `panel`)."""
    W = H = 24

    def sh(r, side, x, y):
        cz = corner_zone(x, y, W, H, 7)
        cut = side in ("tl", "br")
        if r == 0:
            return C["ink0"]
        if r == 1:
            if cut:
                return C["gold3"] if side == "tl" else C["gold2"]
            if cz:
                return C["cyan4"] if side in LIGHT else C["cyan3"]
            return C["navy3"] if side in LIGHT else C["navy2"]
        if r == 2:
            if cut:
                return C["gold4"] if side == "tl" else C["gold3"]
            return C["white"] if side in LIGHT or side == "tr" else C["navy5"]
        if r == 3:
            return C["navy6"] if side in LIGHT or side == "tr" else mix(C["navy5"], C["navy6"], 0.6)
        return C["navy6"]
    img = frame(W, H, (6, 2, 6, 2), sh)
    check9(img, 8, "panel_light")
    return img


def make_button(state):
    """Chunky key-cap button with a 3px lip.  pressed = cap pushed down onto the lip."""
    W, H = 24, 24
    LIP = 3
    if state == "normal":
        edge_l, edge_d, face, hi, lo, lip, key = C["cyan4"], C["cyan3"], C["navy2"], C["navy3"], C["navy1"], C["cyan1"], C["ink0"]
    elif state == "focus":
        edge_l, edge_d, face, hi, lo, lip, key = C["cyan6"], C["cyan5"], mix(C["navy2"], C["navy3"], 0.6), C["navy4"], C["navy2"], C["cyan2"], C["cyan4"]
    else:
        edge_l, edge_d, face, hi, lo, lip, key = C["cyan3"], C["cyan2"], C["navy1"], C["navy0"], C["navy1"], C["cyan1"], C["ink0"]
    cuts = (2, 2, 2, 2)
    fh = H - LIP

    def cap(r, side, x, y):
        if r == 0:
            return key
        if r == 1:
            return edge_l if side in LIGHT or side == "tr" else edge_d
        if r == 2:
            if state == "pressed":
                return hi if side in ("t", "tl", "tr") else face      # inner shadow under the top rim
            return hi if side in ("t", "tl", "tr") else (lo if side in ("b", "br", "bl") else face)
        return face

    def side_(r, side, x, y):
        return key if r == 0 else lip
    img = new(W, H)
    if state == "pressed":
        img.alpha_composite(frame(W, fh, cuts, cap), (0, LIP - 1))
        # 1px of lip still showing
        base = frame(W, fh, cuts, side_)
        out = new(W, H); out.alpha_composite(base, (0, LIP)); out.alpha_composite(img)
        img = out
    else:
        img.alpha_composite(frame(W, fh, cuts, side_), (0, LIP))
        img.alpha_composite(frame(W, fh, cuts, cap), (0, 0))
    check9(img, 8, "button_" + state)
    return img


def make_tag():
    """Speaker name tag: warm orange plate (emphasis colour) for dark or white text."""
    W = H = 12

    def sh(r, side, x, y):
        if r == 0:
            return C["ink0"]
        if r == 1:
            return C["orange5"] if side in ("t", "tl") else (C["orange2"] if side in ("b", "br", "bl", "r") else C["orange4"])
        return C["orange3"]
    img = frame(W, H, (2, 0, 2, 0), sh)
    check9(img, 4, "tag")
    return img


def backdrop():
    """The dock mock-up at 1x (480x272) as a stand-in game screen for previews."""
    try:
        b = Image.open(os.path.join(pix.PREVIEW, "mock_dock.png")).convert("RGBA")
        return b.resize((b.width // 3, b.height // 3), Image.NEAREST)
    except Exception:                        # tiles.py not run yet: plain wall colour
        return Image.new("RGBA", (480, 272), C["ink1"])


def portrait_placeholder():
    """48x48 bust placeholder (the real ones come from characters.py)."""
    try:
        p = Image.open(os.path.join(pix.ASSETS, "sprites", "portraits.png")).convert("RGBA")
        if p.height >= 48 and p.width >= 48:
            return p.crop((0, 0, 48, 48))
    except Exception:
        pass
    im = new(48, 48)
    pix.disc(im, 23.5, 19, 11, C["navy3"])
    pix.ellipse(im, 23.5, 50, 19, 18, C["navy3"])
    return im


def panel_previews(panel, holo, light, btn, tag):
    # --- sources, big
    src = new(24 * 6 + 12 + 7 * 4, 32, T)
    x = 4
    for im in (panel, holo, light, btn[0], btn[1], btn[2], tag):
        src.alpha_composite(im, (x, 4)); x += im.width + 4
    preview(src, "ui_panels_src.png", scale=8, bg="#2b3f7e")

    # --- mock dialogue: 420x70 panel at 1x over the game, x2, ui20 text at screen res
    bg = backdrop()
    scene = bg.copy()
    px0, py0 = 30, 190
    scene.alpha_composite(nine(panel, 420, 70, 8), (px0, py0))
    # portrait well
    well = nine(holo, 56, 56, 8)
    scene.alpha_composite(well, (px0 + 8, py0 + 7))
    scene.alpha_composite(portrait_placeholder(), (px0 + 12, py0 + 11))
    f20 = BMFont("ui20"); f8 = BMFont("pix8")
    name = "JAKE"
    tw = f8.width(name) + 12
    scene.alpha_composite(nine(tag, tw, 14, 4), (px0 + 70, py0 - 7))
    f8.draw(scene, px0 + 70 + 6, py0 - 7 + 3, name, color=C["ink0"])
    try:                                     # "continue" prompt, as the game would show it
        hud = Image.open(os.path.join(pix.ASSETS, "ui", "hud.png")).convert("RGBA")
        i = HUD_NAMES.index("key_e")
        scene.alpha_composite(hud.crop((i * 16, 0, i * 16 + 16, 16)), (px0 + 420 - 26, py0 + 70 - 23))
    except Exception:
        pass
    big = scene.resize((scene.width * 2, scene.height * 2), Image.NEAREST)
    lines = f20.wrap("Three quarters plus one quarter makes one whole! That's 3/4 + 1/4 = 4/4. "
                     "Time to find the Missing Quarter before the Phantom does.", (420 - 70 - 14) * 2)
    for i, l in enumerate(lines[:4]):
        f20.draw(big, (px0 + 72) * 2, (py0 + 11) * 2 + i * (f20.line_h + 3), l, color=C["navy6"])
    big.convert("RGB").save(os.path.join(pix.PREVIEW, "ui_mock_dialogue.png"))

    # --- buttons stretched to 120x24, with labels, on a panel
    card = new(300, 150, hexc("#0d1126"))
    card.alpha_composite(bg.crop((0, 0, 300, 150)))
    card.alpha_composite(nine(panel, 280, 130, 8), (10, 10))
    labels = ["normal", "focus", "pressed"]
    for i in range(3):
        card.alpha_composite(nine(btn[i], 120, 24, 8), (22, 22 + i * 30))
    card.alpha_composite(nine(light, 120, 84, 8), (160, 22))
    card.alpha_composite(nine(holo, 120, 24, 8), (22, 112))
    card.alpha_composite(nine(tag, 60, 14, 4), (166, 16))
    f8.draw(card, 172, 19, "RESULT", color=C["ink0"])
    big = card.resize((600, 300), Image.NEAREST)
    f28 = BMFont("ui28")
    for i, lab in enumerate(("Play", "Options", "Relax mode")):
        w = f20.width(lab)
        dy = 2 if i == 2 else 0
        f20.draw(big, (22 + 60) * 2 - w // 2, (22 + i * 30) * 2 + 8 + dy * 2, lab, color=C["white"])
    f20.draw(big, (22 + 60) * 2 - f20.width("holo panel") // 2, 112 * 2 + 10, "holo panel", color=C["cyan6"])
    f28.draw(big, 172 * 2, 34 * 2, "3/4 + 1/4", color=C["navy1"])
    f20.draw(big, 172 * 2, 34 * 2 + 40, "= one whole!", color=C["navy2"])
    f20.draw(big, 172 * 2, 34 * 2 + 70, "Quarters: 12", color=C["orange2"])
    big.convert("RGB").save(os.path.join(pix.PREVIEW, "ui_buttons.png"))


def build_panels(man):
    panel, holo, light, tag = make_panel(), make_panel_holo(), make_panel_light(), make_tag()
    btn = [make_button(s) for s in ("normal", "focus", "pressed")]
    save(panel, "ui/panel.png"); save(holo, "ui/panel_holo.png"); save(light, "ui/panel_light.png")
    save(tag, "ui/tag.png"); save(pix.sheet(btn), "ui/button.png")
    man["images"]["panel"] = {"file": "ui/panel.png", "slice": 8}
    man["images"]["panel_holo"] = {"file": "ui/panel_holo.png", "slice": 8}
    man["images"]["panel_light"] = {"file": "ui/panel_light.png", "slice": 8}
    man["images"]["tag"] = {"file": "ui/tag.png", "slice": 4}
    man["sheets"]["button"] = {"file": "ui/button.png", "fw": 24, "fh": 24, "slice": 8,
                               "names": {"normal": 0, "focus": 1, "pressed": 2}}
    panel_previews(panel, holo, light, btn, tag)


# =============================================================================
# HUD ICONS (16x16 cells, 1px ink0 outline, bold shapes)
# =============================================================================
PAL = {
    "o": "ink0", "i": "ink1", "W": "white",
    "r": "red3", "R": "red2", "p": "red4", "q": "red5", "d": "red1",
    "g": "gold3", "G": "gold2", "y": "gold4", "Y": "gold5", "b": "gold1", "B": "gold0",
    "c": "cyan4", "C": "cyan3", "k": "cyan5", "K": "cyan6", "t": "cyan2", "T": "cyan1", "u": "cyan0",
    "v": "navy0", "n": "navy1", "N": "navy2", "m": "navy3", "M": "navy4", "l": "navy5", "L": "navy6",
    "x": "steel3", "X": "steel2", "s": "steel5", "S": "steel4", "z": "steel6", "Z": "steel7", "j": "steel1",
    "e": "green3", "E": "green2", "f": "green4", "F": "green5", "D": "green1",
    "a": "orange3", "A": "orange2", "h": "orange4", "H": "orange5",
}
CMAP = {k: C[v] for k, v in PAL.items()}

# auto-bevel materials: char -> (highlight, base, shade)
MATS = {
    "1": ("white", "navy6", "navy5"),      # white UI glyph
    "2": ("cyan5", "cyan4", "cyan3"),      # cyan (interactive)
    "3": ("green4", "green3", "green2"),   # go
    "4": ("red4", "red3", "red2"),         # stop / exit
    "5": ("gold4", "gold3", "gold2"),      # gold
    "6": ("navy3", "navy2", "navy1"),      # empty / disabled
    "7": ("steel7", "steel5", "steel4"),   # metal
    "8": ("orange5", "orange3", "orange2"),
}


def art(rows, w=None):
    """Validate an ASCII block (all rows the same width)."""
    w = w or len(rows[0])
    for r in rows:
        assert len(r) == w, f"row width {len(r)} != {w}: {r!r}"
    return rows


def bevel_sprite(rows, thin=False):
    """ASCII -> image.  Digits are auto-bevelled materials (lit from the top-left:
    top edge highlight, bottom/right edge shade); letters are literal palette colours."""
    rows = art(rows)
    h, w = len(rows), len(rows[0])
    img = new(w, h)

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and rows[y][x] not in ". "
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if ch in ". ":
                continue
            if ch in MATS:
                hi, base, lo = (C[n] for n in MATS[ch])
                up, dn, lf, rt = solid(x, y - 1), solid(x, y + 1), solid(x - 1, y), solid(x + 1, y)
                if not up:
                    c = hi
                elif not dn:
                    c = lo
                elif not rt and not thin:
                    c = lo
                elif not lf and not thin and solid(x + 1, y) and solid(x + 2, y):
                    c = hi
                else:
                    c = base
                img.putpixel((x, y), c)
            else:
                img.putpixel((x, y), CMAP[ch])
    return img


def cell(spr, ox=None, oy=None, outline=True):
    """Centre a sprite in a 16x16 cell and add the ink outline."""
    c = new(16, 16)
    ox = (16 - spr.width) // 2 if ox is None else ox
    oy = (16 - spr.height) // 2 if oy is None else oy
    assert ox >= (1 if outline else 0) and oy >= (1 if outline else 0), "no room for the outline"
    assert ox + spr.width <= (15 if outline else 16) and oy + spr.height <= (15 if outline else 16), "too big"
    c.alpha_composite(spr, (ox, oy))
    return pix.outline(c) if outline else c


def ic(rows, ox=None, oy=None, thin=False):
    return cell(bevel_sprite(rows, thin), ox, oy)


def rot(rows, turns):
    """Rotate an ASCII block clockwise by 90deg * turns."""
    for _ in range(turns % 4):
        rows = ["".join(rows[len(rows) - 1 - y][x] for y in range(len(rows))) for x in range(len(rows[0]))]
    return rows


def mirror(rows):
    return [r[::-1] for r in rows]


# ---- pies: a disc cut into four clear quarter wedges ------------------------------
DISC14 = 52.0        # d^2 limit giving the round 14px pixel circle (rows 6,10,12,12,14...)


def pie_icon(n):
    """n of 4 quarter wedges lit gold, filling clockwise from the top-right wedge.
    The 2px ink cross keeps the four quarters unmistakable; empty wedges are recessed navy."""
    img = new(16, 16)
    cx = cy = 7.5
    for y in range(16):
        for x in range(16):
            dx, dy = x - cx, y - cy
            d2 = dx * dx + dy * dy
            if d2 > DISC14:
                continue
            if x in (7, 8) or y in (7, 8):
                img.putpixel((x, y), C["ink0"])           # the quarter lines
                continue
            quad = 0 if (dx > 0 and dy < 0) else 1 if (dx > 0 and dy > 0) else 2 if (dx < 0 and dy > 0) else 3
            rim = (abs(dx) + 1) ** 2 + dy * dy > DISC14 or dx * dx + (abs(dy) + 1) ** 2 > DISC14
            inner_tl = (y == 9 and dy > 0) or (x == 9 and dx > 0)      # wedge edge facing the light
            inner_br = (y == 6 and dy < 0) or (x == 6 and dx < 0)      # wedge edge facing away
            if quad < n:
                c = C["gold3"]
                if rim:
                    c = C["gold5"] if dx + dy < -2 else (C["gold2"] if dx + dy > 2 else
                                                         (C["gold4"] if dy < 0 else C["gold2"]))
                elif inner_tl:
                    c = C["gold4"]
                elif inner_br:
                    c = C["gold2"]
            else:
                c = C["navy2"]
                if rim:
                    c = C["navy1"] if dx + dy < -2 else (C["navy3"] if dx + dy > 2 else
                                                         (C["navy1"] if dy < 0 else C["navy3"]))
                elif inner_tl:
                    c = C["navy1"]                         # shadow cast by the raised divider
            img.putpixel((x, y), c)
    if n == 4:
        img.putpixel((4, 4), C["white"])
    return pix.outline(img)


def whole_icon():
    """The complete golden fuel orb: one seamless glossy sphere - no quarter lines."""
    img = new(16, 16)
    cx = cy = 7.5
    for y in range(16):
        for x in range(16):
            dx, dy = x - cx, y - cy
            d2 = dx * dx + dy * dy
            if d2 > DISC14:
                continue
            l = math.hypot(x - 4.7, y - 4.7)               # distance from the light spot
            rim = (abs(dx) + 1) ** 2 + dy * dy > DISC14 or dx * dx + (abs(dy) + 1) ** 2 > DISC14
            if l < 3.3:
                c = C["gold5"]
            elif l < 6.0:
                c = C["gold4"]
            elif l < 8.6:
                c = C["gold3"]
            else:
                c = C["gold2"]
            if rim and dx + dy > 3:
                c = C["orange4"]                           # warm bounce light on the shadow rim
            elif rim and dx + dy < -3:
                c = C["gold5"]
            img.putpixel((x, y), c)
    for p_ in ((4, 3), (5, 3), (3, 4), (4, 4), (3, 5)):
        img.putpixel(p_, C["white"])
    img.putpixel((10, 11), C["gold4"])                    # small secondary glint
    return pix.outline(img)


STAR14 = [
    "......##......",
    ".....####.....",
    ".....####.....",
    "....######....",
    "##############",
    ".############.",
    "..##########..",
    "...########...",
    "...########...",
    "..##########..",
    "..####..####..",
    ".####....####.",
    ".##........##.",
]


def key_icon(glyph, gx=None, gy=None):
    """Light key-cap, 16x14, with a dark glyph (ASCII, '#') on its face."""
    rows = art([
        ".ZZZZZZZZZZZZ.",
        "ZWWWWWWWWWWWWz",
        "ZZZZZZZZZZZZZz",
        "ZZZZZZZZZZZZZz",
        "ZZZZZZZZZZZZZz",
        "ZZZZZZZZZZZZZz",
        "ZZZZZZZZZZZZZz",
        "ZZZZZZZZZZZZZz",
        "ZZZZZZZZZZZZzz",
        "zzzzzzzzzzzzzs",
        "sSSSSSSSSSSSSx",
        ".xxxxxxxxxxxx.",
    ])
    spr = pix.ascii_sprite(rows, CMAP)
    g = art(glyph)
    gx = (14 - len(g[0])) // 2 if gx is None else gx
    gy = 1 + (8 - len(g)) // 2 if gy is None else gy
    for y, r in enumerate(g):
        for x, ch in enumerate(r):
            if ch == "#":
                spr.putpixel((gx + x, gy + y), C["ink1"])
            elif ch == "+":
                spr.putpixel((gx + x, gy + y), C["navy3"])
    return cell(spr, 1, 2)


def arc_arrow(cw, col, play=False):
    """Circular arrow (reset = counter-clockwise; replay = clockwise, thinner, with a
    green play triangle in the middle)."""
    N = 14
    c = 6.5
    grid = [["." for _ in range(N)] for _ in range(N)]
    r_out, r_in = (6.5, 4.5) if play else (6.3, 3.6)
    gap0, gap1 = (182, 262) if not play else (170, 250)   # degrees, screen coords (y down)
    for y in range(N):
        for x in range(N):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            a = math.degrees(math.atan2(dy, dx)) % 360
            if r_in <= d <= r_out and not (gap0 < a < gap1):
                grid[y][x] = col
    # arrow head at the gap1 end, pointing counter-clockwise (towards the left/down)
    rm = (r_out + r_in) / 2
    a1 = math.radians(gap1 + 6)
    bx, by = c + rm * math.cos(a1), c + rm * math.sin(a1)
    tx, ty = math.sin(a1), -math.cos(a1)                   # ccw tangent
    nx, ny = math.cos(a1), math.sin(a1)
    hw, hl = (3.3, 4.4) if play else (3.9, 4.8)
    tri = [(bx + nx * hw, by + ny * hw), (bx - nx * hw, by - ny * hw), (bx + tx * hl, by + ty * hl)]

    def in_tri(px_, py_):
        s_ = []
        for i in range(3):
            x1, y1 = tri[i]; x2, y2 = tri[(i + 1) % 3]
            s_.append((px_ - x1) * (y2 - y1) - (py_ - y1) * (x2 - x1))
        return all(v >= -0.01 for v in s_) or all(v <= 0.01 for v in s_)
    for y in range(N):
        for x in range(N):
            if in_tri(x, y):
                grid[y][x] = col
    rows = ["".join(r) for r in grid]
    if cw:
        rows = mirror(rows)
    if play:
        rows = [list(r) for r in rows]
        for y, xs in ((4, (5,)), (5, (5, 6)), (6, (5, 6, 7)), (7, (5, 6, 7)), (8, (5, 6)), (9, (5,))):
            for x in xs:
                rows[y][x] = "3"
        rows = ["".join(r) for r in rows]
    return rows


HUD_NAMES = ["heart_full", "heart_empty", "pie0", "pie1", "pie2", "pie3", "pie4", "starcell",
             "starcell_empty", "whole", "key_e", "key_space", "key_left", "key_right", "key_up", "key_esc",
             "tap", "hint", "reset", "go", "exit", "music", "sfx", "voice", "subs", "pause", "home",
             "replay", "lock", "arrow_l", "arrow_r", "arrow_u", "arrow_d", "relax", "star_full", "star_empty"]


def hud_icons():
    I = {}
    # ---------------------------------------------------------------- hearts
    I["heart_full"] = ic([
        "..prr....prr..",
        ".pWWrr..prrrr.",
        "pWWrrrrrrrrrrR",
        "pWrrrrrrrrrrrR",
        "prrrrrrrrrrrRR",
        "rrrrrrrrrrrrRR",
        ".rrrrrrrrrrRR.",
        "..rrrrrrrrRR..",
        "...rrrrrrRR...",
        "....rrrrRd....",
        ".....rRRd.....",
        "......Rd......",
    ])
    I["heart_empty"] = ic([
        "..NNN....NNN..",
        ".NvvvN..NvvvN.",
        "NvvvvvNNvvvvvm",
        "NvvvvvvvvvvvvN",
        "NvvvvvvvvvvvvN",
        "NvvvvvvvvvvvnN",
        ".NvvvvvvvvvnN.",
        "..NvvvvvvvnN..",
        "...NvvvvvnN...",
        "....NvvvnN....",
        ".....NvnN.....",
        "......NN......",
    ])
    # ---------------------------------------------------------------- pies / whole
    for n in range(5):
        I[f"pie{n}"] = pie_icon(n)
    I["whole"] = whole_icon()
    # ---------------------------------------------------------------- star cell
    I["starcell"] = ic([
        "..SZZZZZZs..",
        ".SzWWzzzzsS.",
        "tckttttttttT",
        "tkcttyyttttT",
        "tctttyyttttT",
        "ttyyyyggggtT",
        "tttyygggGttT",
        "ttttyggGtttT",
        "tttyygggGttT",
        "tttyyttgGttT",
        "ttyyttttgGTT",
        "ttttttttttTT",
        ".SzzzzzzssS.",
        "..SsssssSx..",
    ])
    I["starcell_empty"] = ic([
        "..XxxxxxxX..",
        ".XxssxxxxxX.",
        "vnnnnnnnnnnv",
        "vnnnnvvnnnnv",
        "vnnnnvvnnnnv",
        "vnvvvvvvvvnv",
        "vnnvvvvvvnnv",
        "vnnnvvvvnnnv",
        "vnnvvvvvvnnv",
        "vnnvvnnvvnnv",
        "vnvvnnnnvvnv",
        "vnnnnnnnnnnv",
        ".XxxxxxxxxX.",
        "..XXXXXXXX..",
    ])
    # ---------------------------------------------------------------- keys
    I["key_e"] = key_icon(["#####", "##...", "##...", "####.", "##...", "##...", "#####"])
    I["key_space"] = key_icon(["###.###.###",
                               "#...#.#.#..",
                               "###.###.#..",
                               "..#.#...#..",
                               "###.#...###"])
    I["key_esc"] = key_icon(["###.###.###",
                             "#...#...#..",
                             "##..###.#..",
                             "#.....#.#..",
                             "###.###.###"])
    kr = ["...#...", "...##..", "######.", "#######", "######.", "...##..", "...#..."]
    I["key_right"] = key_icon(kr)
    I["key_left"] = key_icon(mirror(kr))
    ku = ["...#...", "..###..", ".#####.", "#######", "..###..", "..###..", "..###.."]
    I["key_up"] = key_icon(ku)
    # ---------------------------------------------------------------- tap (pointing hand + ripple)
    I["tap"] = ic([
        ".c..WW..c...",
        "c...WW...c..",
        "....WL......",
        "....WL......",
        "....WLWW....",
        "....WLWLWW..",
        "WW..WWWLWLWW",
        "WLW.WWWWWWWL",
        ".WLWWWWWWWWL",
        "..WWWWWWWWWL",
        "..WWWWWWWWLl",
        "...WWWWWWLL.",
        "...LWWWWLLl.",
        "....LLLLLl..",
    ])
    # ---------------------------------------------------------------- hint (light bulb)
    I["hint"] = ic([
        "...yyyy...",
        ".yyYYYygg.",
        ".yYWWYyyg.",
        "yYWWYyyggg",
        "yYWYyyyggG",
        "yYYyybyggG",
        "yyyyybyggG",
        ".yyybbbgG.",
        ".gyygbgGG.",
        "..ggbbGG..",
        "...ZzsS...",
        "...xxxx...",
        "...ZzsS...",
        "....xx....",
    ])
    # ---------------------------------------------------------------- reset / replay
    I["reset"] = ic(arc_arrow(False, "2"))
    I["replay"] = ic([
        "........W.....",
        "....WWWWWW....",
        "..WWWWWWWWW...",
        ".WWW....WL....",
        ".WW.....L.....",
        "WW...f........",
        "WW...fe.....WW",
        "WW...eeE....WL",
        "WW...eE.....WL",
        "WL...E......Ll",
        ".WL........LL.",
        ".WLL......LLl.",
        "..LLLLLLLLLl..",
        "....llllll....",
    ])
    # ---------------------------------------------------------------- go / exit
    I["go"] = ic([
        "...........33.",
        "..........333.",
        ".........3333.",
        "........3333..",
        ".33....3333...",
        "3333..3333....",
        "33333.333.....",
        ".3333333......",
        "..33333.......",
        "...333........",
        "....3.........",
    ], thin=False)
    I["exit"] = ic([
        ".44......44.",
        "4444....4444",
        "44444..44444",
        ".4444444444.",
        "..44444444..",
        "...444444...",
        "...444444...",
        "..44444444..",
        ".4444444444.",
        "44444..44444",
        "4444....4444",
        ".44......44.",
    ])
    # ---------------------------------------------------------------- audio / options
    I["music"] = ic([
        "....1111111111",
        "....1111111111",
        "....1111111111",
        "....11......11",
        "....11......11",
        "....11......11",
        "....11......11",
        "....11......11",
        ".11111...11111",
        "111111..111111",
        "111111..111111",
        ".1111....1111.",
    ], thin=True)
    I["sfx"] = ic([
        ".....11.......",
        "....111...2...",
        "...1111....2..",
        "1111111.2...2.",
        "1111111..2..2.",
        "1111111..2..2.",
        "1111111..2..2.",
        "1111111.2...2.",
        "...1111....2..",
        "....111...2...",
        ".....11.......",
    ], thin=True)
    I["voice"] = ic([
        "..1111111111..",
        ".111111111111.",
        "11111111111111",
        "11111111111111",
        "11NN11NN11NN11",
        "11NN11NN11NN11",
        "11111111111111",
        "11111111111111",
        ".111111111111.",
        "..1111111111..",
        "..1111........",
        "..111.........",
        "..1...........",
    ])
    I["subs"] = ic([
        ".111111111111.",
        "11vvvvvvvvvv11",
        "1vvvvvvvvvvvv1",
        "1vvvvvvvvvvvv1",
        "1vvvvvvvvvvvv1",
        "1vvvvvvvvvvvv1",
        "1vvcccc.ccvvv1".replace(".", "v"),
        "1vvvvvvvvvvvv1",
        "1vvvccccccvvv1",
        "11vvvvvvvvvv11",
        ".111111111111.",
    ], thin=True)
    I["pause"] = ic([
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
        "1111..1111",
    ])
    I["home"] = ic([
        "......22......",
        ".....2222.....",
        "....222222....",
        "...22222222...",
        "..2222222222..",
        ".222222222222.",
        "22222222222222",
        ".WWWWWWWWWWWL.",
        ".WWWWWNNWWWWL.",
        ".WWWWNNNNWWWL.",
        ".WWWWNNNNWWWL.",
        ".WLLLNNNNLLLL.",
    ])
    I["lock"] = ic([
        "...ZZZZZZ...",
        "..Zzs..Zzs..",
        "..Zs....zs..",
        "..Zs....zs..",
        "yyyyyyyyyyyg",
        "yggggggggggG",
        "ygggiiiigggG",
        "ygggiiiigggG",
        "yggggiigggGG",
        "yggggiigggGG",
        "ygggggggggGG",
        "gGGGGGGGGGGb",
    ])
    # ---------------------------------------------------------------- arrows
    ar = [
        "......22......",
        "......222.....",
        "......2222....",
        "222222222222..",
        "2222222222222.",
        "22222222222222",
        "22222222222222",
        "2222222222222.",
        "222222222222..",
        "......2222....",
        "......222.....",
        "......22......",
    ]
    I["arrow_r"] = ic(ar)
    I["arrow_l"] = ic(mirror(ar))
    I["arrow_d"] = ic(rot(ar, 1))
    I["arrow_u"] = ic(mirror(rot(ar, 3)))
    # ---------------------------------------------------------------- relax (calm face)
    I["relax"] = ic([
        "....ffffff....",
        "..ffFFFFfeee..",
        ".fFFFfffeeeee.",
        ".fFffeeeeeeee.",
        "fFfeeeeeeeeeeE",
        "ffeoeeeeeeoeeE",
        "feoeoeeeeoeoeE",
        "feeeeeeeeeeeeE",
        "feeeeeeeeeeeEE",
        "feeeoeeeeoeeEE",
        ".eeeeooooeeEE.",
        ".eeeeeeeeeEEE.",
        "..eeeeeeEEEE..",
        "....EEEEEE....",
    ])
    # ---------------------------------------------------------------- stars
    I["star_full"] = ic([r.replace("#", "5") for r in STAR14])
    I["star_full"].putpixel((6, 6), C["white"]); I["star_full"].putpixel((5, 7), C["gold5"])
    I["star_empty"] = ic([r.replace("#", "6") for r in STAR14])
    return I


def build_hud(man):
    I = hud_icons()
    assert set(I) == set(HUD_NAMES), set(HUD_NAMES) ^ set(I)
    frames = [I[n] for n in HUD_NAMES]
    sh = pix.sheet(frames, cols=16)
    save(sh, "ui/hud.png")
    man["sheets"]["hud"] = {"file": "ui/hud.png", "fw": 16, "fh": 16,
                            "names": {n: i for i, n in enumerate(HUD_NAMES)}}
    hud_previews(I, sh)


def hud_previews(I, sh):
    # the sheet, big, one row per image so every pixel can be inspected
    for r in range(3):
        row = sh.crop((0, r * 16, 256, r * 16 + 16))
        wide = new(256 + 17 * 2, 20, T)
        for i in range(16):
            wide.alpha_composite(row.crop((i * 16, 0, i * 16 + 16, 16)), (2 + i * 18, 2))
        preview(wide, f"ui_hud_row{r}.png", scale=7, bg="#1e2a5a")
    # mock HUD over the game at 1x, then x2 like the real canvas
    bg = backdrop().crop((0, 0, 480, 150))
    f8 = BMFont("pix8")
    panel = make_panel()
    x = 8
    for n in ("heart_full", "heart_full", "heart_empty"):
        bg.alpha_composite(I[n], (x, 8)); x += 17
    x += 8
    bg.alpha_composite(I["pie3"], (x, 8)); x += 19
    f8.draw(bg, x, 13, "3/4", color=C["ink0"]); f8.draw(bg, x, 12, "3/4", color=C["gold4"])
    x += 34
    for n in ("starcell", "starcell", "starcell_empty"):
        bg.alpha_composite(I[n], (x, 8)); x += 15
    x += 10
    for n in ("pie0", "pie1", "pie2", "pie3", "pie4", "whole"):
        bg.alpha_composite(I[n], (x, 8)); x += 18
    x = 480 - 8 - 16
    for n in ("pause", "hint", "reset"):
        bg.alpha_composite(I[n], (x, 8)); x -= 20
    # key prompts
    bg.alpha_composite(nine(panel, 178, 26, 8), (8, 34))
    x = 16
    for n in ("key_left", "key_right", "key_up", "key_space", "key_e", "key_esc", "tap"):
        bg.alpha_composite(I[n], (x, 39)); x += 18
    f8.draw(bg, x + 2, 44, "MOVE", color=C["cyan5"])
    # options row on a panel
    bg.alpha_composite(nine(panel, 290, 28, 8), (8, 68))
    x = 16
    for n in ("music", "sfx", "voice", "subs", "relax", "home", "replay", "lock", "go", "exit",
              "arrow_l", "arrow_r", "arrow_u", "arrow_d", "star_full", "star_empty"):
        bg.alpha_composite(I[n], (x, 74)); x += 17
    # the same icons straight over the game (no panel) and on the light panel
    x = 8
    for n in HUD_NAMES[:27]:
        bg.alpha_composite(I[n], (x, 104)); x += 17
    lightp = make_panel_light()
    bg.alpha_composite(nine(lightp, 170, 26, 8), (8, 122))
    x = 14
    for n in HUD_NAMES[27:]:
        bg.alpha_composite(I[n], (x, 127)); x += 17
    bg.resize((960, 300), Image.NEAREST).convert("RGB").save(os.path.join(pix.PREVIEW, "ui_mock_hud.png"))


# =============================================================================
# TOUCH BUTTONS (40x40, round, translucent)
# =============================================================================
def _arrow_left():
    rows = []
    for y in range(18):
        hy = min(y, 17 - y)                    # 0 at the top/bottom rows
        row = ""
        for x in range(19):
            head = x <= 9 and x >= 8 - hy      # triangle, tip on the left
            shaft = 9 <= x and 5 <= y <= 12
            row += "#" if head or shaft else "."
        rows.append(row)
    return rows


TOUCH_GLYPHS = {
    "left": _arrow_left(),
    "right": mirror(_arrow_left()),
    "jump": art([                               # double chevron = "boost up"
        ".........##.........",
        "........####........",
        ".......######.......",
        "......########......",
        ".....##########.....",
        "....#####..#####....",
        "...#####....#####...",
        "..#####......#####..",
        ".#####...##...#####.",
        "#####...####...#####",
        "####...######...####",
        ".##...########...##.",
        ".....##########.....",
        "....#####..#####....",
        "...#####....#####...",
        "..#####......#####..",
        ".#####........#####.",
        "#####..........#####",
        "####............####",
        ".##..............##.",
    ]),
    "interact": art([                           # pointing hand ("use / talk")
        "......##..........",
        ".....####.........",
        ".....####.........",
        ".....####.........",
        ".....####.........",
        ".....####.........",
        ".....####.##......",
        ".....####.###.##..",
        ".....####.###.###.",
        "##...####.###.###.",
        "###..############.",
        "####.#############",
        ".#################",
        "..################",
        "..################",
        "...###############",
        "...##############.",
        "....#############.",
        "....############..",
        ".....##########...",
    ]),
    "pause": art([
        "#####....#####",
    ] * 16),
}


def touch_button(name, on):
    img = new(40, 40)
    c = 19.5
    fill = with_alpha(C["cyan3"], 178) if on else with_alpha(C["navy0"], 122)
    gloss = with_alpha(C["cyan5"], 190) if on else with_alpha(C["navy2"], 140)
    shade = with_alpha(C["cyan2"], 190) if on else with_alpha(C["ink0"], 140)
    rim = C["white"] if on else with_alpha(C["cyan6"], 215)
    rim2 = C["cyan6"] if on else with_alpha(C["cyan4"], 205)
    key = with_alpha(C["cyan4"], 200) if on else with_alpha(C["ink0"], 150)
    for y in range(40):
        for x in range(40):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            if d > 19.2:
                continue
            if d > 18.15:
                col = key
            elif d > 16.5:
                col = rim if dx + dy < 6 else rim2          # rim lit from the top-left
            elif d < 15.3 and math.hypot(dx, dy - 5.5) > 15.6 and abs(dx) < 11:
                col = gloss                                 # glass highlight: crescent under the top rim
            elif d > 14.6 and dx + dy > 9:
                col = shade                                 # inner shadow crescent, lower right
            else:
                col = fill
            img.putpixel((x, y), col)
    g = TOUCH_GLYPHS[name]
    gw, gh = len(g[0]), len(g)
    ox = (40 - gw) // 2
    oy = (40 - gh) // 2 + (1 if on else 0)
    if name == "left":
        ox -= 1
    if name == "right":
        ox += 1
    if name == "jump":
        oy -= 1
    mask = new(40, 40)
    for y, r in enumerate(g):
        for x, ch in enumerate(r):
            if ch == "#":
                mask.putpixel((ox + x, oy + y), C["white"])
    # soft ink keyline + drop shadow so the white glyph holds on any background
    sh = pix.outline(mask, with_alpha(C["ink0"], 150 if not on else 120))
    for y in range(40):
        for x in range(40):
            if mask.getpixel((x, y))[3]:
                sh.putpixel((x, y), T)
    lay = new(40, 40)
    lay.alpha_composite(sh)
    # lower-right shadow, 1px
    drop = new(40, 40)
    for y in range(39):
        for x in range(39):
            if mask.getpixel((x, y))[3] and not mask.getpixel((x, y + 1))[3]:
                drop.putpixel((x, y + 2 if y + 2 < 40 else y + 1), with_alpha(C["ink0"], 90))
    img.alpha_composite(drop)
    img.alpha_composite(lay)
    # glyph: white with a pale-blue lower edge (1px bevel)
    for y in range(40):
        for x in range(40):
            if mask.getpixel((x, y))[3]:
                below = mask.getpixel((x, y + 1))[3] if y + 1 < 40 else 0
                img.putpixel((x, y), C["white"] if below else C["navy5"])
    return img


TOUCH_NAMES = ["left", "right", "jump", "interact", "pause"]


def build_touch(man):
    frames = [touch_button(n, False) for n in TOUCH_NAMES] + [touch_button(n, True) for n in TOUCH_NAMES]
    sh = pix.sheet(frames, cols=5)
    save(sh, "ui/touch.png")
    names = {n: i for i, n in enumerate(TOUCH_NAMES)}
    names.update({n + "_on": i + 5 for i, n in enumerate(TOUCH_NAMES)})
    man["sheets"]["touch"] = {"file": "ui/touch.png", "fw": 40, "fh": 40, "names": names}
    # previews: the sheet, and the buttons over a game screen (1x -> x2 like the canvas)
    preview(sh, "ui_touch_sheet.png", scale=5, bg="#3f5fae")
    bg = backdrop().crop((0, 2, 480, 272))
    F = dict(zip(list(names), frames))
    bg.alpha_composite(F["left"], (10, 222)); bg.alpha_composite(F["right_on"], (58, 222))
    bg.alpha_composite(F["interact"], (382, 222)); bg.alpha_composite(F["jump"], (430, 206))
    bg.alpha_composite(F["pause"], (434, 6))
    # second row to see every state against the bright platform tiles
    for i, n in enumerate(("left_on", "right", "jump_on", "interact_on", "pause_on")):
        bg.alpha_composite(F[n], (120 + i * 44, 118))
    bg.resize((960, 540), Image.NEAREST).convert("RGB").save(os.path.join(pix.PREVIEW, "ui_mock_touch.png"))


# =============================================================================
# LOGO  "MATH BLAST / ARCADE"
# =============================================================================
def glyph_mask(ch, size, weight=700, wdth=100, shear=0.0, ss=8):
    """Fredoka glyph shape snapped to the pixel grid: rendered 8x, optionally sheared
    (italic), box-filtered down and thresholded to 1-bit.  Returns (set of (x,y) pixels
    relative to pen-x / baseline-y, advance)."""
    f = ImageFont.truetype(font_path("Fredoka.ttf"), size * ss, layout_engine=ImageFont.Layout.BASIC)
    f.set_variation_by_axes([weight, wdth])
    W = H = size * 3
    bx, by = size, size * 2                               # pen origin / baseline in 1x pixels
    im = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(im).text((bx * ss, by * ss), ch, font=f, fill=255, anchor="ls")
    if shear:
        im = im.transform(im.size, Image.AFFINE, (1, shear, -shear * by * ss, 0, 1, 0), Image.BICUBIC)
    small = im.resize((W, H), Image.BOX)
    pts = set()
    p = small.load()
    for y in range(H):
        for x in range(W):
            if p[x, y] >= 128:
                pts.add((x - bx, y - by))
    return pts, f.getlength(ch) / ss


def tidy(pts):
    """Pixel clean-up: drop orphan nubs, fill one-pixel notches."""
    pts = set(pts)
    for _ in range(2):
        for (x, y) in list(pts):
            n = sum(((x + dx, y + dy) in pts) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if n <= 1:
                pts.discard((x, y))
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        for y in range(min(ys), max(ys) + 1):
            for x in range(min(xs), max(xs) + 1):
                if (x, y) not in pts:
                    n = sum(((x + dx, y + dy) in pts) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if n >= 3:
                        pts.add((x, y))
    return pts


def dilate(pts, n=1, diag=False):
    pts = set(pts)
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)] + ([(1, 1), (-1, 1), (1, -1), (-1, -1)] if diag else [])
    for _ in range(n):
        pts |= {(x + dx, y + dy) for (x, y) in pts for dx, dy in nb}
    return pts


def shift(pts, dx, dy):
    return {(x + dx, y + dy) for (x, y) in pts}


def close_waist(pts):
    """Fredoka's B has an open waist (one counter).  With the shine band running across
    it the letter read as a D, so join the waist bar to the stem: two clear counters."""
    pts = set(pts)
    ys = sorted({q[1] for q in pts})
    top, bot = ys[0], ys[-1]
    gaps = {}
    for y in ys:
        if not (top + (bot - top) * 0.3 < y < top + (bot - top) * 0.65):
            continue
        xs = sorted(q[0] for q in pts if q[1] == y)
        for a, b in zip(xs, xs[1:]):
            if b - a > 1:                                   # first gap after the stem
                gaps[y] = (a + 1, b - 1)
                break
    if not gaps:
        return pts
    narrow = min(b - a for a, b in gaps.values())
    for y, (a, b) in gaps.items():
        if b - a <= narrow + 1:
            for x in range(a, b + 1):
                pts.add((x, y))
    return pts


PAIR_KERN = {"LA": -5, "AS": -1, "AT": 0}


def set_line(text, size, gap, shear, step, weight=700, wdth=100):
    """Lay out one word.  Letters are packed so the closest pixels of neighbours are
    `gap` apart (logo kerning) and each letter steps `step` px up (rising baseline).
    Returns a list of (pts, top, bottom) with pts in line coordinates (baseline y=0 for
    the first letter)."""
    letters = []
    pen = 0
    prev = None
    for i, ch in enumerate(text):
        pts, adv = glyph_mask(ch, size, weight, wdth, shear)
        if ch == "B":
            pts = close_waist(pts)
        pts = tidy(pts)
        dy = -int(round(step * i))
        pts = shift(pts, 0, dy)
        if prev is None:
            x0 = -min(q[0] for q in pts)
        else:
            # slide left until the minimum row-wise gap to the previous letter == gap
            rows_prev = {}
            for (x, y) in prev:
                rows_prev[y] = max(rows_prev.get(y, -999), x)
            rows_cur = {}
            for (x, y) in pts:
                rows_cur[y] = min(rows_cur.get(y, 999), x)
            need = None
            for y, xmin in rows_cur.items():
                for yy in (y - 1, y, y + 1):               # also keep diagonal neighbours apart
                    if yy in rows_prev:
                        d = rows_prev[yy] + gap + 1 - xmin
                        need = d if need is None else max(need, d)
            x0 = (need if need is not None else pen) + PAIR_KERN.get(text[i - 1] + ch, 0)
        pts = shift(pts, x0, 0)
        cap_top = dy - int(round(size * 0.70))
        letters.append((pts, cap_top, dy))
        prev = pts
        pen = max(q[0] for q in pts) + gap
    return letters


FACE_BANDS = [   # (t_end, colour) from the cap top (t=0) to the baseline (t=1)
    (0.07, "gold5"), (0.29, "gold4"), (0.47, "gold3"),
    (0.56, "white"),                                       # the hard shine band
    (0.74, "orange4"), (0.90, "orange3"), (9.99, "orange2"),
]


def face_colour(t, x, y):
    """Vertical gold->orange ramp with a hard white shine band and dithered joins."""
    prev_end = 0.0
    for i, (end, name) in enumerate(FACE_BANDS):
        if t < end:
            # dither the last ~35% of soft bands into the next colour (not around the shine)
            nxt = FACE_BANDS[i + 1][1] if i + 1 < len(FACE_BANDS) else name
            hard = name == "white" or nxt == "white"
            if not hard:
                span = end - prev_end
                f = (t - (end - span * 0.45)) / (span * 0.45)
                if f > 0:
                    return pix.dither_pick([C[name], C[nxt]], f * 0.9, x, y)
            return C[name]
        prev_end = end
    return C["orange2"]


def word_body(letters, ox, oy, depth=3):
    """Pixel sets for one word in canvas coordinates: faces, the down-right extrusion
    that gives the letters their chunky depth, and both together."""
    faces = set()
    for pts, top, bot in letters:
        faces |= shift(pts, ox, oy)
    ext = set()
    for i in range(1, depth + 1):
        ext |= shift(faces, i, i)
    ext -= faces
    body = faces | ext
    return faces, ext, body


def sparkle(img, x, y, r, c0=None, c1=None):
    """Four-point star sparkle."""
    c0 = c0 or C["white"]; c1 = c1 or C["gold5"]
    for i in range(-r, r + 1):
        col = c0 if abs(i) < r else c1
        px(img, x + i, y, col); px(img, x, y + i, col)
    if r >= 3:
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            px(img, x + dx, y + dy, c1)


def pixel_text_mask(text, scale=1, track=0):
    """Press Start 2P text as a set of pixels (top-left origin)."""
    f = ImageFont.truetype(font_path("PressStart2P.ttf"), 8, layout_engine=ImageFont.Layout.BASIC)
    pts = set()
    x = 0
    for ch in text:
        im = Image.new("L", (10, 10), 0)
        d = ImageDraw.Draw(im); d.fontmode = "1"
        d.text((0, 0), ch, font=f, fill=255)
        p = im.load()
        for yy in range(8):
            for xx in range(8):
                if p[xx, yy]:
                    for sy in range(scale):
                        for sx in range(scale):
                            pts.add((x + xx * scale + sx, yy * scale + sy))
        x += 8 * scale + track
    return pts, x - track - scale                           # glyphs are 7 wide in an 8 cell


def rocket(img, ox, oy):
    """Small inspector rocket flying up-right (about 40x40), flame trailing down-left."""
    S = 44
    lay = new(S, S)
    ax, ay = 0.7071, -0.7071                               # axis unit vector (up-right)
    cx0, cy0 = 17.0, 27.0                                  # tail centre
    L = 22.0                                               # body length
    R = 6.2
    NOSE = 12.5                                            # where the ogive starts
    for y in range(S):
        for x in range(S):
            dx, dy = x - cx0, y - cy0
            u = dx * ax + dy * ay                          # along the axis (0 = tail, L = nose tip)
            v = dx * (-ay) + dy * ax                       # across (negative = upper-left = lit side)
            c = None
            # flame (behind the tail): white-hot core, gold, orange tip
            if -15.0 < u < 0.5:
                fw = 4.6 * (1 + u / 15.0) ** 0.75
                wob = 0.7 * math.sin(u * 1.3)
                if abs(v - wob * (-u / 15.0)) < fw:
                    k = abs(v) / max(fw, 0.01) * 0.75 + (-u) / 15.0
                    c = C["white"] if k < 0.33 else C["gold5"] if k < 0.5 else C["gold3"] if k < 0.72 else C["orange3"] if k < 0.92 else C["orange2"]
            # fins (swept back)
            if -2.0 <= u <= 7.5:
                reach = 11.0 - (u + 2.0) * 0.95
                if R - 2.2 < abs(v) < reach:
                    c = C["orange3"] if v < 0 else C["orange2"]
                    if v < 0 and abs(v) > reach - 1.4:
                        c = C["orange5"]
                    if v > 0 and abs(v) > reach - 1.3:
                        c = C["orange1"]
            # body
            if 0 <= u <= L:
                r = R if u < NOSE else R * math.sqrt(max(0.0, 1 - ((u - NOSE) / (L - NOSE)) ** 2))
                if u < 2.0:
                    r = R - 1.4
                if abs(v) <= r:
                    if u > 15.6:                           # nose cone
                        c = C["orange5"] if v < -1.5 else C["orange3"] if v < 1.4 else C["orange2"]
                    elif 14.2 < u <= 15.6:                 # collar band
                        c = C["navy4"] if v < -2.0 else C["navy3"] if v < 1.6 else C["navy2"]
                    elif u < 2.0:                          # engine bell
                        c = C["steel5"] if v < -1.5 else C["steel4"] if v < 1.5 else C["steel3"]
                    else:
                        c = C["white"] if v < -3.3 else C["steel7"] if v < 1.2 else C["steel6"] if v < 3.6 else C["steel5"]
                        if 2.0 <= u < 3.2:
                            c = C["steel5"] if v < 2 else C["steel4"]          # tail ring
                    # porthole
                    dw = math.hypot(u - 9.0, v)
                    if dw < 4.0:
                        c = C["ink0"]
                    if dw < 3.1:
                        c = C["cyan4"] if (u - 9.0) * 0.6 - v < 1.2 else C["cyan2"]
                    if dw < 3.1 and v < -1.0 and u < 10.2:
                        c = C["cyan6"]
            if c is not None:
                lay.putpixel((x, y), c)
    lay = pix.outline(lay)
    img.alpha_composite(lay, (ox, oy))


def make_logo():
    W, H = 300, 120
    img = new(W, H)
    shear = 0.16
    math_l = set_line("MATH", 47, gap=3, shear=shear, step=1.5)
    blast_l = set_line("BLAST", 70, gap=3, shear=shear, step=2.0)

    def extent(letters):
        xs = [q[0] for l in letters for q in l[0]]; ys = [q[1] for l in letters for q in l[0]]
        return min(xs), min(ys), max(xs), max(ys)
    mb = extent(math_l); bb = extent(blast_l)
    # BLAST: centred low; MATH: upper left, overlapping BLAST's top a little
    bw = bb[2] - bb[0] + 1
    b_ox = (W - bw) // 2 - bb[0] - 2
    b_oy = 96
    m_ox = b_ox + bb[0] - mb[0] + 4
    m_oy = b_oy + bb[1] + 4
    words = []
    for letters, ox, oy in ((math_l, m_ox, m_oy), (blast_l, b_ox, b_oy)):
        faces, ext, body = word_body(letters, ox, oy, depth=3)
        words.append((letters, ox, oy, faces, ext, body))
    all_body = set()
    for wd in words:
        all_body |= wd[5]
    ink = dilate(dilate(all_body, 1, diag=True), 1)        # 2px rounded keyline
    shadow = shift(ink, 3, 4)
    shadow_ink = dilate(shadow, 1)

    def put(pts, col):
        for (x, y) in pts:
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), col(x, y) if callable(col) else col)
    put(shadow_ink, C["ink0"])
    put(shadow, lambda x, y: C["cyan3"])
    # light the shadow slab: 1px bright edge where it meets the ink on its upper-left side
    put({q for q in shadow if (q[0] - 1, q[1] - 1) in ink and q not in ink}, C["cyan5"])
    put({q for q in shadow if (q[0] + 1, q[1]) not in shadow or (q[0], q[1] + 1) not in shadow}, C["cyan2"])
    put(ink, C["ink0"])
    # draw MATH first, then BLAST over it (each with its own keyline so the overlap reads)
    for letters, ox, oy, faces, ext, body in words:
        put(dilate(dilate(body, 1, diag=True), 1), C["ink0"])
        put(ext, lambda x, y: C["orange1"])
        put({q for q in ext if (q[0] - 1, q[1] - 1) in ext and (q[0] - 2, q[1] - 2) in ext}, C["orange0"])
        for pts, top, bot in letters:
            pts = shift(pts, ox, oy)
            t0, t1 = top + oy, bot + oy
            for (x, y) in pts:
                t = (y - t0) / max(1, (t1 - t0))
                c = face_colour(t, x, y)
                up = (x, y - 1) in pts; lf = (x - 1, y) in pts
                dn = (x, y + 1) in pts; rt = (x + 1, y) in pts
                if not up or (not lf and t < 0.56):
                    c = C["white"] if t < 0.56 else C["orange5"]            # top-left bevel
                elif not dn or not rt:
                    c = C["orange2"] if t > 0.47 else C["gold2"]            # bottom-right bevel
                if 0 <= x < W and 0 <= y < H:
                    img.putpixel((x, y), c)

    # ---- ARCADE plate
    apts, aw = pixel_text_mask("ARCADE", scale=2, track=4)
    pw, ph = aw + 26, 22
    plate = frame(pw, ph, (5, 2, 5, 2), lambda r, side, x, y:
                  C["ink0"] if r == 0 else
                  ((C["gold4"] if side == "tl" else C["gold3"]) if side in ("tl", "br") and r == 1 else
                   (C["cyan5"] if side in LIGHT else C["cyan3"]) if r == 1 else
                   mix(C["navy0"], C["cyan1"], 0.6) if r == 2 else C["navy0"]))
    px0 = b_ox + bb[2] - pw + 6
    py0 = H - ph - 1
    img.alpha_composite(plate, (px0, py0))
    tx, ty = px0 + 13, py0 + 4
    for (x, y) in apts:
        row = y // 2
        c = C["white"] if row == 0 else C["cyan6"] if row <= 1 else C["cyan5"] if row <= 3 else C["cyan4"] if row <= 5 else C["cyan3"]
        px(img, tx + x, ty + y, c)
    # ---- rocket + sparkles
    rocket(img, m_ox + mb[2] + 12, 0)
    # exhaust puffs trailing off behind the rocket
    rx, ry = m_ox + mb[2] + 12, 0
    for (qx, qy, r_) in ((7, 38, 2.0), (1, 42, 1.2)):
        puff = new(8, 8)
        pix.disc(puff, 3.5, 3.5, r_, C["steel6"])
        pix.disc(puff, 3.0, 3.0, r_ - 1.0, C["white"])
        puff = pix.outline(puff)
        img.alpha_composite(puff, (rx + qx - 4, ry + qy - 4))
    sparkle(img, m_ox + mb[0] + 3, m_oy + mb[1] + 2, 4)
    sparkle(img, b_ox + bb[2] - 6, b_oy + bb[1] + 5, 5)
    sparkle(img, b_ox + bb[0] + 118, b_oy + bb[1] + 13, 2)
    sparkle(img, m_ox + mb[2] + 8, m_oy + mb[1] + 26, 2, C["white"], C["cyan6"])
    return img


def starfield(w, h, seed=7):
    rnd = random.Random(seed)
    bg = Image.new("RGBA", (w, h), C["ink0"])
    for _ in range(w * h // 260):
        x, y = rnd.randrange(w), rnd.randrange(h)
        bg.putpixel((x, y), rnd.choice([C["navy2"], C["navy3"], C["navy4"], C["navy5"], C["navy1"], C["purple3"]]))
    for _ in range(w * h // 5000):
        x, y = rnd.randrange(1, w - 1), rnd.randrange(1, h - 1)
        bg.putpixel((x, y), C["white"])
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            bg.putpixel((x + dx, y + dy), C["navy3"])
    return bg


def build_logo(man):
    logo = make_logo()
    save(logo, "ui/logo.png")
    man["images"]["logo"] = {"file": "ui/logo.png"}
    bg = starfield(340, 150)
    bg.alpha_composite(logo, (20, 15))
    bg.resize((680, 300), Image.NEAREST).convert("RGB").save(os.path.join(pix.PREVIEW, "ui_logo_2x.png"))
    preview(logo, "ui_logo_big.png", scale=5, bg="#0d1126")
    # also over the game backdrop and a light colour, to check the outline holds anywhere
    b2 = backdrop().crop((0, 0, 480, 150)); b2.alpha_composite(logo, (90, 15))
    b2.resize((960, 300), Image.NEAREST).convert("RGB").save(os.path.join(pix.PREVIEW, "ui_logo_ingame.png"))


# =============================================================================
# main
# =============================================================================
def main(argv):
    want = set(argv) or {"all"}

    def on(name):
        return "all" in want or name in want
    man = {"sheets": {}, "images": {}, "fonts": {}}
    if on("fonts"):
        man["fonts"].update(build_fonts())
    if on("hud"):                            # before panels: the dialogue mock borrows a HUD icon
        build_hud(man)
    if on("panels"):
        build_panels(man)
    if on("touch"):
        build_touch(man)
    if on("logo"):
        build_logo(man)
    if "all" in want:
        pix.manifest("ui", man)
        print("manifest ui.json written")


if __name__ == "__main__":
    main(sys.argv[1:])
