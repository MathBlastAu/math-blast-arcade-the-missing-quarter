"""
props_machines.py - interactive machinery for Math Blast Arcade (PART "props", machines half).

Sheets : door, checkpoint, mplat, spring, console, fblock, lever, tank4, liquid_top,
         bridge_emitter, bridge_seg, cannon, beam, holo_proj
Images : reactor_back, reactor_front
Manifest fragment: assets/manifest/props_machines.json

Run:  cd art && python3 props_machines.py            (build everything + previews)
      cd art && python3 props_machines.py door lever  (re-render only those previews)

Conventions used here
  * every solid machine is drawn on a "body" layer, outlined with ink0, and only then
    are the translucent glow pixels composited (so glows never get an outline);
  * light comes from the top-left: top/left bevels use ramp+2, bottom/right use ramp-2;
  * cyan = friendly energy, green = success/plus, red-pink = locked/minus, gold = caution.
"""
import sys
from pix import *

ST = ramp("steel"); CY = ramp("cyan"); NV = ramp("navy"); GD = ramp("gold"); OR = ramp("orange")
GR = ramp("green"); RD = ramp("red"); PK = ramp("pink"); PU = ramp("purple"); INK = ramp("ink")
WHITE = C["white"]
# warm hull used by the reactor area tiles (tiles.SKINS["reactor"]["hull"])
RH = [hexc(h) for h in ["#1a1218", "#2a1c24", "#3e2a32", "#573c40", "#775650", "#9c7a68", "#c7a68a", "#efd9b8"]]
# "minus" ramp: red shadows shifting to pink highlights
MI = [RD[0], RD[1], RD[2], RD[3], PK[3], PK[4]]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def A(c, a):
    return (c[0], c[1], c[2], a)


def bevel(img, x, y, w, h, R, f=3, hi=2, lo=2, cut=0):
    """Bevelled metal slab: fill R[f], top/left lighter, bottom/right darker."""
    n = len(R) - 1
    rect(img, x, y, w, h, R[f])
    hline(img, x, x + w - 1, y + h - 1, R[max(0, f - lo)])
    vline(img, x + w - 1, y, y + h - 1, R[max(0, f - lo)])
    hline(img, x, x + w - 1, y, R[min(n, f + hi)])
    vline(img, x, y, y + h - 1, R[min(n, f + hi - 1)])
    px(img, x, y, R[min(n, f + hi)])
    px(img, x + w - 1, y, R[f]); px(img, x, y + h - 1, R[f])
    for i in range(cut):
        for j in range(cut - i):
            for (cx, cy) in ((x + i, y + j), (x + w - 1 - i, y + j), (x + i, y + h - 1 - j), (x + w - 1 - i, y + h - 1 - j)):
                img.putpixel((cx, cy), T)


def rivet(img, x, y, R, f=3):
    px(img, x, y, R[min(len(R) - 1, f + 2)]); px(img, x + 1, y + 1, R[max(0, f - 2)])


def hazard(img, x, y, w, h, a, b, ph=0):
    for yy in range(h):
        for xx in range(w):
            px(img, x + xx, y + yy, a if ((xx + yy + ph) // 3) % 2 == 0 else b)


def clip_paste(dst, src, x, y, box):
    """Paste src at x,y but only inside box (x0,y0,x1,y1 exclusive)."""
    for yy in range(src.height):
        for xx in range(src.width):
            c = src.getpixel((xx, yy))
            X, Y = x + xx, y + yy
            if c[3] and box[0] <= X < box[2] and box[1] <= Y < box[3]:
                px(dst, X, Y, c)


def over(dst, src, x=0, y=0):
    _tmp = new(dst.width, dst.height)
    for yy in range(src.height):
        for xx in range(src.width):
            c = src.getpixel((xx, yy))
            if c[3]:
                X, Y = x + xx, y + yy
                if 0 <= X < dst.width and 0 <= Y < dst.height:
                    _tmp.putpixel((X, Y), c)
    dst.alpha_composite(_tmp)


def cyl_cols(w, R, lo=1, hi=6):
    """Column colours for a vertical cylinder lit from the left."""
    prof = [0.35, 0.75, 1.0, 0.8, 0.6, 0.48, 0.38, 0.28, 0.16, 0.05, 0.22]
    out = []
    for i in range(w):
        t = i / max(1, w - 1) * (len(prof) - 1)
        a = int(t); b = min(len(prof) - 1, a + 1)
        v = prof[a] + (prof[b] - prof[a]) * (t - a)
        out.append(R[int(round(lo + v * (hi - lo)))])
    return out


def cyl_v(img, x, y, w, h, R, lo=1, hi=6):
    cols = cyl_cols(w, R, lo, hi)
    for i, c in enumerate(cols):
        vline(img, x + i, y, y + h - 1, c)


def band_pick(colors, v, x, y, soft=0.3):
    """Flat colour bands with only a thin checker-dither transition between them."""
    n = len(colors) - 1
    f = max(0.0, min(1.0, v)) * n
    i = int(math.floor(f)); fr = f - i
    lo, hi = 0.5 - soft / 2.0, 0.5 + soft / 2.0
    if fr > hi or (fr > lo and (x + y) % 2 == 0):
        i += 1
    return colors[min(n, i)]


def glow_dot(img, cx, cy, r, c, a0=150):
    """Chunky dithered-free halo: stepped alpha rings."""
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                step = int((1 - d / r) * 3 + 0.999)        # 1..3
                px(img, x, y, A(c, int(a0 * step / 3)))


def strip(frames, name, scale=6, bg="#1b2547", cols=None):
    preview(sheet(frames, cols=cols, pad=1), name, scale=scale, bg=bg)


# ----------------------------------------------------------------------------
# DOOR  32x48 : 0 locked, 1 unlocked, 2-6 opening, 7 open
# ----------------------------------------------------------------------------
def door_interior():
    """What you see through the open airlock: a short lit corridor."""
    img = new(20, 34, INK[1])
    # far wall + inner hatch
    rect(img, 5, 5, 10, 24, NV[0])
    rect(img, 7, 9, 6, 20, NV[1])
    hline(img, 7, 12, 9, NV[2]); vline(img, 7, 9, 28, NV[2])
    vline(img, 10, 10, 28, NV[0])
    rect(img, 9, 14, 2, 3, CY[1]); px(img, 9, 14, CY[3])
    hline(img, 8, 11, 7, CY[2]); hline(img, 9, 10, 7, CY[4])
    # ceiling and floor wedges
    for i in range(5):
        hline(img, i, 19 - i, i, INK[2] if i < 4 else NV[0])
        hline(img, i, 19 - i, 33 - i, NV[1] if i < 4 else NV[0])
    hline(img, 3, 16, 2, CY[2]); hline(img, 5, 14, 2, CY[4]); hline(img, 7, 12, 2, CY[5])
    hline(img, 4, 15, 3, CY[1])
    # floor guide strip
    vline(img, 9, 29, 33, NV[2]); vline(img, 10, 29, 33, NV[2])
    px(img, 9, 33, CY[2]); px(img, 10, 33, CY[2]); px(img, 9, 31, CY[1]); px(img, 10, 31, CY[1])
    # wall ribs
    for (x0, x1) in ((2, 2), (17, 17)):
        vline(img, x0, 3, 30, INK[2])
    vline(img, 4, 5, 28, INK[0]); vline(img, 15, 5, 28, INK[2])
    # contact shadow from lintel and left jamb
    hline(img, 0, 19, 0, INK[0]); vline(img, 0, 0, 33, INK[0]); hline(img, 1, 19, 1, INK[0])
    return img


def door_leaf(side, lock):
    """One sliding leaf, 10x34. lock: red | green | flash | open"""
    B = NV
    img = new(10, 34)
    rect(img, 0, 0, 10, 34, B[2])
    # painted-metal sheen: two diagonal light bands
    for y in range(34):
        for x in range(10):
            gx = x if side == "L" else x + 10
            k = (gx + y) % 26
            if k in (9, 10, 11):
                px(img, x, y, B[3])
    # bevel
    hline(img, 0, 9, 0, B[1]); hline(img, 0, 9, 1, B[4]); hline(img, 0, 9, 33, B[0]); hline(img, 0, 9, 32, B[1])
    if side == "L":
        vline(img, 0, 1, 32, B[3]); vline(img, 9, 0, 33, INK[1]); vline(img, 8, 1, 32, B[1])
    else:
        vline(img, 0, 0, 33, B[4]); vline(img, 1, 1, 32, B[3]); vline(img, 9, 1, 32, B[1])
    # embossed "slides this way" chevrons
    for k, cy in enumerate((4,)):
        for j in range(5):
            dx = abs(j - 2)
            for cx0 in (2, 5):
                x = (cx0 + dx) if side == "L" else (9 - cx0 - dx)
                px(img, x, cy + j, B[5]); px(img, x + (1 if side == "L" else -1), cy + j, B[0])
    # grooves
    for gy in (11, 24):
        hline(img, 1, 8, gy, B[0]); hline(img, 1, 8, gy + 1, B[4])
    # lower plate rivets
    rivet(img, 2 if side == "L" else 6, 13, B, 2)
    # hazard stripes
    hazard(img, 1, 28, 8, 4, GD[3], INK[1], 0 if side == "L" else 2)
    hline(img, 1, 8, 27, B[0]); hline(img, 1, 8, 26, B[1])
    # lock disc half
    cx = 9.5 if side == "L" else -0.5
    LR = {"red": RD, "green": GR, "flash": GR, "open": GR}[lock]
    disc(img, cx, 17.5, 4.6, INK[0])
    disc(img, cx, 17.5, 3.6, LR[2] if lock != "flash" else LR[4])
    disc(img, cx - 0.6, 17.0, 2.4, LR[3] if lock != "flash" else LR[5])
    if side == "L":
        px(img, 7, 15, LR[4] if lock != "flash" else WHITE); px(img, 6, 16, LR[4] if lock != "flash" else WHITE)
        px(img, 8, 15, LR[4] if lock != "flash" else WHITE)
    if lock == "red":           # bolt bar across the seam
        hline(img, 6 if side == "L" else 0, 9 if side == "L" else 3, 17, INK[0])
        hline(img, 6 if side == "L" else 0, 9 if side == "L" else 3, 18, INK[0])
    elif lock in ("green", "open"):
        if side == "L":
            vline(img, 9, 15, 20, GR[0])
        else:
            vline(img, 0, 15, 20, GR[4])
    return img


def door_frame_art(img, LC, flash=False):
    S = ST
    # pillars
    rect(img, 1, 11, 5, 34, S[4]); rect(img, 26, 11, 5, 34, S[4])
    vline(img, 1, 11, 44, S[6]); vline(img, 2, 11, 44, S[5]); vline(img, 4, 11, 44, S[3]); vline(img, 5, 11, 44, S[1])
    vline(img, 26, 11, 44, S[6]); vline(img, 27, 11, 44, S[4]); vline(img, 29, 11, 44, S[3]); vline(img, 30, 11, 44, S[1])
    for py in (21, 33):
        hline(img, 1, 5, py, S[1]); hline(img, 1, 4, py + 1, S[6])
        hline(img, 26, 30, py, S[1]); hline(img, 26, 29, py + 1, S[6])
    for ly in (14, 25, 37):
        for lx in (3, 28):
            vline(img, lx, ly - 1, ly + 3, S[1])
            vline(img, lx, ly, ly + 2, LC[3]); px(img, lx, ly, LC[5] if flash else LC[4])
    # header
    rect(img, 1, 1, 30, 10, S[4])
    hline(img, 1, 30, 1, S[7]); hline(img, 1, 30, 2, S[6]); hline(img, 1, 30, 7, S[3])
    vline(img, 1, 1, 10, S[6]); vline(img, 30, 2, 10, S[1])
    hazard(img, 2, 8, 28, 2, GD[3], INK[1])
    hline(img, 1, 30, 10, S[1])
    for (cx, cy) in ((1, 1), (2, 1), (1, 2), (30, 1), (29, 1), (30, 2)):
        img.putpixel((cx, cy), T)
    px(img, 2, 2, S[7]); px(img, 29, 2, S[5])
    rivet(img, 4, 4, S, 4); rivet(img, 26, 4, S, 4)
    # lamp
    rect(img, 9, 2, 14, 6, S[1])
    hline(img, 9, 22, 2, S[2])
    rect(img, 10, 3, 12, 4, LC[3])
    hline(img, 10, 21, 3, LC[4]); hline(img, 10, 21, 6, LC[2])
    hline(img, 11, 14, 4, LC[5]); px(img, 11, 3, WHITE if flash else LC[5])
    for (cx, cy) in ((10, 3), (21, 3), (10, 6), (21, 6)):
        px(img, cx, cy, S[1])
    if flash:
        rect(img, 11, 4, 10, 2, LC[5]); hline(img, 12, 16, 4, WHITE)
    # threshold
    hline(img, 1, 30, 45, S[6]); hline(img, 1, 30, 46, S[3])
    hline(img, 1, 8, 45, S[7])
    for x in range(7, 26, 3):
        px(img, x, 45, S[4])
    px(img, 30, 45, S[4]); px(img, 30, 46, S[1])


def door_frames():
    frames = []
    inter = door_interior()
    offs = [0, 0, 0, 1, 3, 6, 8, 9]
    locks = ["red", "green", "flash", "open", "open", "open", "open", "open"]
    for i in range(8):
        img = new(32, 48)
        d = offs[i]
        if d:
            img.alpha_composite(inter, (6, 11))
        L = door_leaf("L", locks[i]); R = door_leaf("R", locks[i])
        box = (6, 11, 26, 45)
        clip_paste(img, L, 6 - d, 11, box)
        clip_paste(img, R, 16 + d, 11, box)
        if d:
            # shadow the leaves cast into the corridor + bright slit of light on first crack
            if d == 1:
                vline(img, 15, 12, 44, CY[5]); vline(img, 16, 12, 44, CY[3])
            else:
                vline(img, 16 - d, 11, 44, INK[0])
        door_frame_art(img, RD if i == 0 else GR, flash=(i in (2, 6)))
        img = outline(img)
        # steam bursting from the floor seals as the leaves part (clean little puffs)
        if i in (3, 4, 5):
            k = i - 3
            for sgn in (-1, 1):
                bx = 15.5 + sgn * (2.5 + k * 3.0)
                by = 42.5 - k * 2.5
                r = (1.6, 1.3, 0.8)[k]
                disc(img, bx, by + 0.6, r, ST[5]); disc(img, bx, by, r, ST[7] if k < 2 else ST[6])
                if k < 2:
                    px(img, bx - sgn * 0.5, by - 0.5, WHITE)
                px(img, bx + sgn * (2 + k), by - 2 - k, A(ST[7], 170 - k * 40))
        frames.append(img)
    return frames


# ----------------------------------------------------------------------------
# FBLOCK 32x32 : plus, minus, neutral, off
# ----------------------------------------------------------------------------
ARROW_BIG = ["...XX...", "..XXXX..", ".XXXXXX."]
ARROW_SIDE = [".X.", "XXX"]


def stamp(img, rows, x, y, c, flip=False):
    rows = rows[::-1] if flip else rows
    for ry, r in enumerate(rows):
        for rx, ch in enumerate(r):
            if ch == "X":
                px(img, x + rx, y + ry, c)


def fblock(kind):
    R = {"plus": GR, "minus": MI, "neutral": CY[0:6], "off": ST[0:6]}[kind]
    lit = kind != "off"
    img = new(32, 32)
    rect(img, 1, 1, 30, 30, R[2])
    # top + left arms catch the light, right + bottom arms sit in shade (mitred joins)
    rect(img, 1, 1, 30, 4, R[3]); rect(img, 1, 1, 3, 30, R[3])
    for i in range(4):
        hline(img, 30 - i, 30, 1 + i, R[2])
    for i in range(3):
        vline(img, 1 + i, 30 - i, 30, R[2])
    rect(img, 28, 5, 3, 26, R[2]); rect(img, 4, 27, 27, 4, R[2])
    # rim light / rim shadow
    hline(img, 2, 28, 1, R[5]); vline(img, 1, 2, 28, R[4]); hline(img, 5, 26, 2, R[4])
    hline(img, 2, 30, 30, R[0]); vline(img, 30, 3, 30, R[0])
    hline(img, 3, 29, 29, R[1]); px(img, 29, 28, R[1])
    # recessed bezel: top/left in shadow, bottom/right catch light
    rect(img, 4, 5, 24, 22, INK[0])
    hline(img, 5, 27, 26, R[4]); vline(img, 27, 6, 26, R[3]); px(img, 27, 26, R[5])
    # the display: flat, 22x20 at (5,6)
    rect(img, 5, 6, 22, 20, INK[1])
    if kind in ("plus", "minus"):
        fl = kind == "minus"
        # arrow plates: a darker inset so the big arrows punch out
        rect(img, 11, 2, 10, 3, R[2]); px(img, 11, 2, R[3]); px(img, 20, 2, R[3])
        rect(img, 11, 27, 10, 3, R[1]); px(img, 11, 29, R[2]); px(img, 20, 29, R[2])
        stamp(img, ARROW_BIG, 12, 2, WHITE, fl)
        stamp(img, ARROW_BIG, 12, 27, R[5], fl)
        # groove either side of the arrow so it pops
        for (gx0, gx1) in ((6, 9), (22, 25)):
            hline(img, gx0, gx1, 3, R[5]); hline(img, gx0, gx1, 28, R[4])
        for sy in (10, 19):
            stamp(img, ARROW_SIDE, 1, sy, R[5], fl)
            stamp(img, ARROW_SIDE, 28, sy, R[4], fl)
    elif kind == "neutral":
        rect(img, 12, 2, 8, 2, WHITE); rect(img, 12, 28, 8, 2, R[5])
        for (gx0, gx1) in ((6, 9), (22, 25)):
            hline(img, gx0, gx1, 3, R[5]); hline(img, gx0, gx1, 28, R[4])
        for sy in (10, 19):
            rect(img, 2, sy, 1, 2, R[5]); rect(img, 29, sy, 1, 2, R[4])
    else:
        rect(img, 12, 3, 8, 1, R[1]); rect(img, 12, 28, 8, 1, R[0])
        for sy in (10, 19):
            rect(img, 2, sy, 1, 2, R[1]); rect(img, 29, sy, 1, 2, R[0])
        px(img, 28, 28, RD[2])          # stand-by LED
    # rounded corners + corner studs (single bright pixel with a soft shadow)
    for (cx, cy) in ((1, 1), (30, 1), (1, 30), (30, 30)):
        img.putpixel((cx, cy), T)
    px(img, 2, 2, WHITE if lit else R[5]); px(img, 3, 2, R[5]); px(img, 2, 3, R[5])
    px(img, 29, 2, R[4]); px(img, 2, 29, R[3])
    return outline(img)


# ----------------------------------------------------------------------------
# LEVER 24x24 : off, mid, on
# ----------------------------------------------------------------------------
def lever(state):
    S = ST
    img = new(24, 24)
    ang = {"off": -40, "mid": 0, "on": 40}[state]
    LC = {"off": RD, "mid": GD, "on": GR}[state]
    pv = (11.5, 14.5)
    L = 9.5
    a = math.radians(ang)
    tip = (pv[0] + math.sin(a) * L, pv[1] - math.cos(a) * L)
    # shaft (behind the hub): 2px steel rod, light on its upper-left side
    capsule(img, pv[0], pv[1], tip[0], tip[1], 1.0, S[4])
    if state == "mid":
        vline(img, 11, tip[1], pv[1], S[7]); vline(img, 12, tip[1], pv[1], S[4])
    else:
        line(img, pv[0] - 0.5, pv[1] - 1, tip[0] - 0.5, tip[1] - (0 if ang > 0 else 1), S[7])
    # knob
    kx, ky = round(tip[0] - 0.5) + 0.5, round(tip[1] - 0.5) + 0.5
    disc(img, kx, ky, 3.6, CY[2])
    disc(img, kx - 0.5, ky - 0.5, 3.0, CY[3])
    disc(img, kx - 0.5, ky - 0.5, 2.1, CY[4])
    px(img, kx - 2, ky - 2, CY[6]); px(img, kx - 1, ky - 2, CY[5]); px(img, kx - 2, ky - 1, CY[5]); px(img, kx - 1, ky - 3, CY[5])
    px(img, kx - 2.5, ky - 1.5, WHITE)
    # base housing (trapezoid: sloped shoulders)
    rect(img, 4, 15, 16, 2, S[5]); hline(img, 5, 18, 15, S[7]); px(img, 4, 15, T); px(img, 19, 15, T)
    px(img, 4, 16, S[6]); px(img, 19, 16, S[3])
    rect(img, 2, 17, 20, 6, S[4])
    hline(img, 2, 21, 17, S[6]); vline(img, 2, 17, 22, S[6]); vline(img, 21, 18, 22, S[2])
    hline(img, 2, 21, 22, S[1]); hline(img, 3, 21, 21, S[2])
    px(img, 2, 17, T); px(img, 21, 17, T); px(img, 3, 17, S[7])
    # slot + hub
    rect(img, 7, 15, 10, 1, S[1])
    disc(img, 11.5, 15.0, 2.6, S[2]); disc(img, 11.2, 14.8, 1.7, S[5]); px(img, 11, 14, S[7]); px(img, 12, 16, S[3])
    # direction pips: red on the left, green on the right
    px(img, 4, 19, RD[3] if state == "off" else RD[1]); px(img, 5, 19, RD[3] if state == "off" else RD[1])
    px(img, 18, 19, GR[3] if state == "on" else GR[1]); px(img, 19, 19, GR[3] if state == "on" else GR[1])
    # indicator window
    rect(img, 7, 18, 10, 4, INK[0])
    rect(img, 8, 19, 8, 2, LC[3]); hline(img, 8, 15, 19, LC[4]); hline(img, 8, 10, 19, LC[5])
    return outline(img)


# ----------------------------------------------------------------------------
# SPRING 16x16 : idle [0], bounce [1..4]
# ----------------------------------------------------------------------------
def spring(top, halfw=6):
    """top = y of the pad surface; the bellows fill whatever is left above the base."""
    S = ST
    img = new(16, 16)
    # base plate
    rect(img, 2, 13, 12, 2, S[3]); hline(img, 2, 13, 13, S[6]); hline(img, 3, 13, 14, S[2]); px(img, 2, 13, S[7])
    px(img, 4, 14, S[5]); px(img, 11, 14, S[5])
    # bellows: wide lit folds alternate with narrow shadowed creases
    c0, c1 = top + 3, 12
    rows = c1 - c0 + 1
    if rows <= 1:
        hline(img, 3, 12, 12, GD[3]); hline(img, 3, 5, 12, GD[4]); px(img, 12, 12, GD[2])
    else:
        folds = max(1, min(3, (rows + 1) // 3))
        for r in range(rows):
            ph = (r * folds * 2.0 / rows) % 2.0
            y = c0 + r
            if ph < 1.0:
                hline(img, 3, 12, y, GD[3]); hline(img, 3, 5, y, GD[5]); px(img, 6, y, GD[4]); hline(img, 11, 12, y, GD[2])
            else:
                hline(img, 5, 10, y, GD[1]); px(img, 5, y, GD[2]); px(img, 10, y, GD[0])
    # pad
    x0, x1 = 8 - halfw, 7 + halfw
    rect(img, x0, top, x1 - x0 + 1, 3, CY[3])
    hline(img, x0, x1, top, CY[5]); hline(img, x0 + 1, x0 + 4, top, CY[6]); hline(img, x0, x1, top + 2, CY[1])
    px(img, x0, top + 1, CY[4]); px(img, x1, top + 1, CY[2]); px(img, x0, top, CY[6])
    hline(img, 6, 9, top + 1, CY[5])
    return outline(img)


def spring_frames():
    #        idle     squash    launch   overshoot  settle
    return [spring(6, 6), spring(10, 7), spring(1, 5), spring(4, 6), spring(7, 6)]


# ----------------------------------------------------------------------------
# CONSOLE 24x32 : idle 0-3, active 4-7, done 8-9
# ----------------------------------------------------------------------------
TICK = ["......XX", ".....XX.", "XX..XX..", ".XXXX...", "..XX...."]


def console_screen(mode, f):
    """16x9 screen contents."""
    s = new(16, 9)
    if mode == "done":
        rect(s, 0, 0, 16, 9, GR[1] if f == 0 else GR[2])
        for y in range(1, 9, 2):
            hline(s, 0, 15, y, GR[0] if f == 0 else GR[1])
        stamp(s, TICK, 4, 3, GR[0])
        stamp(s, TICK, 4, 2, GR[5] if f == 0 else WHITE)
        return s
    bright = mode == "active"
    rect(s, 0, 0, 16, 9, CY[2] if not bright else CY[3])
    for y in range(1, 9, 2):
        hline(s, 0, 15, y, CY[1] if not bright else CY[2])
    if not bright:
        # quarter pie: one more wedge lights each frame (the station's missing-quarter motif)
        cx, cy = 3.5, 4.0
        for y in range(1, 8):
            for x in range(0, 8):
                dx, dy = x - cx, y - cy
                if dx * dx + dy * dy <= 3.6 ** 2 * 0.95:
                    q = 0 if (dx > 0 and dy < 0) else 1 if (dx > 0 and dy > 0) else 2 if (dx < 0 and dy > 0) else 3
                    if abs(dy) < 0.4:
                        px(s, x, y, CY[0]); continue
                    px(s, x, y, CY[6] if q <= f else CY[0])
        # text lines + cursor
        hline(s, 9, 14, 2, CY[5]); hline(s, 9, 12, 4, CY[4]); hline(s, 9, 13, 6, CY[4])
        if f % 2 == 0:
            px(s, 14, 6, WHITE); px(s, 15, 6, WHITE)
    else:
        # fraction bar: four cells filling up
        rect(s, 0, 1, 16, 7, CY[1])
        for k in range(4):
            on = k <= f
            rect(s, k * 4, 2, 3, 5, WHITE if (on and k == f) else CY[6] if on else CY[2])
        vline(s, 15, 1, 7, CY[1])
        hline(s, 0, 15, 0, CY[5]); hline(s, 0, 15, 8, CY[4])
    return s


def console(mode, f):
    S = ST
    img = new(24, 32)
    lc = CY if mode != "done" else GR
    # foot
    rect(img, 4, 28, 16, 3, S[4]); hline(img, 5, 18, 28, S[7]); hline(img, 4, 19, 30, S[1]); hline(img, 5, 19, 29, S[3])
    px(img, 4, 28, T); px(img, 19, 28, T); vline(img, 4, 29, 30, S[5]); px(img, 19, 29, S[2])
    px(img, 6, 29, S[6]); px(img, 17, 29, S[6])
    # pedestal column, flaring into the foot
    cyl_v(img, 8, 18, 8, 10, S, lo=2, hi=6)
    hline(img, 7, 16, 27, S[2]); px(img, 7, 27, S[5]); hline(img, 8, 15, 18, S[1])
    # service light in the column
    rect(img, 11, 20, 2, 6, INK[0])
    for k in range(3):
        on = (mode == "active" and (2 - k) < f) or mode == "done" or (mode == "idle" and k == 2)
        yy = 20 + k * 2
        hline(img, 11, 12, yy, lc[4] if on else lc[1]); hline(img, 11, 12, yy + 1, lc[2] if on else lc[0])
    # keyboard shelf (slanted towards the player): top face + front lip
    hline(img, 4, 19, 14, S[6]); hline(img, 3, 20, 15, S[5]); hline(img, 2, 21, 16, S[4]); hline(img, 2, 21, 17, S[1])
    px(img, 2, 16, S[6]); px(img, 3, 15, S[7]); px(img, 4, 14, S[7]); px(img, 21, 16, S[2])
    keys = [CY[5], CY[5], GD[3], CY[5], CY[5], PK[2], CY[5]]
    for k, kc in enumerate(keys):
        on = True
        if mode == "active":
            on = (k + f) % 4 != 0
        elif mode == "done":
            kc = GR[4]
        px(img, 5 + k * 2, 15, kc if on else S[2])
        px(img, 5 + k * 2, 16, S[2])
    # monitor housing with side ears
    rect(img, 2, 1, 20, 13, S[4])
    hline(img, 3, 20, 1, S[7]); vline(img, 2, 2, 12, S[6]); hline(img, 3, 21, 13, S[1]); vline(img, 21, 2, 12, S[2])
    px(img, 2, 1, T); px(img, 21, 1, T); px(img, 2, 13, T); px(img, 21, 13, T)
    px(img, 3, 2, S[7]); px(img, 20, 12, S[1])
    for ex in (1, 22):
        vline(img, ex, 5, 9, S[3] if ex == 22 else S[5]); px(img, ex, 5, S[6] if ex == 1 else S[4])
    # bezel + screen
    rect(img, 3, 2, 18, 11, INK[0])
    scr = console_screen(mode, f)
    img.alpha_composite(scr, (4, 3))
    # glass glint (diagonal, top-left)
    for (gx, gy, ga) in ((5, 3, 170), (4, 4, 170), (6, 3, 90), (4, 5, 90), (18, 10, 60), (19, 9, 60)):
        px(img, gx, gy, A(WHITE, ga))
    # power LED
    px(img, 19, 13, lc[4])
    img = outline(img)
    # soft screen bloom outside the casing
    fx = new(24, 32)
    al = {"idle": (40, 60, 50, 60), "active": (80, 110, 80, 110), "done": (70, 110)}[mode][f]
    hline(fx, 4, 19, 0, A(lc[4], al))
    if mode != "idle":
        vline(fx, 0, 4, 10, A(lc[4], al // 2)); vline(fx, 23, 4, 10, A(lc[4], al // 2))
    out = new(24, 32)
    # bloom only where the sprite itself is empty
    for y in range(32):
        for x in range(24):
            c = img.getpixel((x, y))
            out.putpixel((x, y), c if c[3] else fx.getpixel((x, y)))
    return out


def console_frames():
    return [console("idle", f) for f in range(4)] + [console("active", f) for f in range(4)] + [console("done", f) for f in range(2)]


# ----------------------------------------------------------------------------
# CHECKPOINT 24x40 : off 0, activate 1-5, on 6-9
# ----------------------------------------------------------------------------
FLAG_TICK = [".......X", "......XX", "X....XX.", "XX..XX..", ".XXXX...", "..XX...."]


def flag_off(x, phase, w):
    """Vertical offset of flag column x: the panel with the tick stays rigid, the tail ripples."""
    if x < 9:
        return 0
    amp = 0.9 + 0.5 * (x - 9) / 3.0
    return int(round(math.sin((x / 8.0 - phase) * 2 * math.pi) * amp))


def holo_flag(phase, grow=1.0, bright=0, w=13, h=10):
    """Translucent pennant, pole edge at x=0, nominal top at y=2. Image 14 x 15."""
    img = new(14, 15)
    cols = max(0, int(round(w * grow)))
    sheen = int((phase * w * 1.0) % w) if bright == 0 else -9
    for x in range(cols):
        off = flag_off(x, phase, w)
        for y in range(h):
            # swallow-tail notch
            notch = x - (w - 4)
            if notch > 0 and abs(y - (h - 1) / 2.0) < notch * 0.9:
                continue
            top = y == 0
            bot = y == h - 1
            if bright >= 2:
                c = A(WHITE, 245)
            elif bright == 1:
                c = A(CY[6], 235) if (top or x == 0) else A(CY[5], 220)
            else:
                c = A(CY[6], 240) if top else A(CY[3], 215) if bot else A(CY[4], 215 if y % 2 == 0 else 190)
                if x == 0:
                    c = A(CY[6], 240)
                if x in (sheen, sheen + 1) and not (top or bot):
                    c = A(CY[5], 225)
            px(img, x, 2 + y + off, c)
    if grow >= 1.0 and bright < 2:
        for ry, r in enumerate(FLAG_TICK):
            for rx, ch in enumerate(r):
                if ch == "X":
                    x = 1 + rx
                    img.putpixel((x, 2 + 2 + ry + flag_off(x, phase, w)), WHITE)
    return img


def checkpoint(i):
    """i: 0 off, 1-5 activate, 6-9 on"""
    S = ST
    img = new(24, 40)
    on = i >= 6
    PX = 7                                     # pole occupies x 7..10
    # foot
    rect(img, 3, 35, 12, 4, S[4]); hline(img, 4, 13, 35, S[7]); hline(img, 3, 14, 38, S[1]); hline(img, 4, 14, 37, S[3])
    px(img, 3, 35, T); px(img, 14, 35, T); vline(img, 3, 36, 37, S[6]); px(img, 14, 36, S[2])
    hazard(img, 5, 36, 8, 2, GD[3], INK[1])
    # collar
    rect(img, 5, 32, 8, 3, S[3]); hline(img, 5, 12, 32, S[6]); px(img, 5, 33, S[5]); hline(img, 6, 12, 34, S[1])
    # pole
    cyl_v(img, PX, 5, 4, 27, S, lo=2, hi=7)
    for by in (17, 23):
        hline(img, PX, PX + 3, by, S[1]); hline(img, PX, PX + 2, by + 1, S[6])
    # light slot on the pole
    lit = 0 if i == 0 else 2 if i in (1, 3, 4) else 1
    lc = [CY[1], CY[4], CY[6]][lit]
    rect(img, PX + 1, 25, 2, 6, INK[0])
    k = (i - 6) % 4 if on else -1
    for yy in range(25, 31):
        c = lc
        if on and (yy - 25) in (4 - k, 5 - k):
            c = CY[6]
        elif on:
            c = CY[3]
        px(img, PX + 1, yy, c); px(img, PX + 2, yy, c)
    # projector prongs (the flag hangs between them)
    hline(img, PX + 4, PX + 5, 4, S[5]); px(img, PX + 5, 5, S[2])
    hline(img, PX + 4, PX + 5, 15, S[4]); px(img, PX + 5, 14, S[6])
    # emitter cap
    rect(img, PX - 1, 2, 6, 3, S[3]); hline(img, PX - 1, PX + 4, 4, S[1]); hline(img, PX, PX + 3, 2, S[6]); px(img, PX - 1, 3, S[5])
    capc = [CY[1], CY[4], WHITE][lit]
    rect(img, PX, 0, 4, 2, capc); px(img, PX, 0, T); px(img, PX + 3, 0, T)
    if lit:
        px(img, PX + 1, 0, CY[6] if lit == 1 else WHITE); px(img, PX, 1, CY[5] if lit == 1 else WHITE); px(img, PX + 3, 1, CY[3] if lit == 1 else CY[6])
    else:
        px(img, PX + 1, 0, CY[2])
    img = outline(img)
    # ---- holo layers (after the outline) ----
    fx = new(24, 40)
    FX0, FY0 = PX + 4, 3
    cap = (PX + 1.5, 0.5)
    if i == 0:
        # dormant: a faint dotted ghost of the flag, so it reads as "raise me"
        fl = holo_flag(0.0, grow=1.0, bright=2)
        for yy in range(fl.height):
            for xx in range(fl.width):
                if not fl.getpixel((xx, yy))[3]:
                    continue
                edge = any(not (0 <= xx + dx < fl.width and 0 <= yy + dy < fl.height and fl.getpixel((xx + dx, yy + dy))[3])
                           for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if edge and (xx + yy) % 2 == 0:
                    px(fx, FX0 + xx, FY0 + yy, A(CY[3], 150))
    elif i == 1:      # power-up flash at the cap, sparks on the prongs
        glow_dot(fx, cap[0], cap[1], 4.5, CY[5], 150)
        px(fx, PX + 6, 4, WHITE); px(fx, PX + 6, 15, WHITE); px(fx, PX + 7, 3, A(CY[6], 200)); px(fx, PX + 7, 16, A(CY[6], 200))
    elif i == 2:      # a thin bright bar snaps on between the prongs
        vline(fx, FX0, 5, 14, WHITE); vline(fx, FX0 + 1, 5, 14, A(CY[6], 230)); vline(fx, FX0 + 2, 6, 13, A(CY[5], 150))
        glow_dot(fx, cap[0], cap[1], 3.5, CY[5], 120)
    elif i == 3:
        over(fx, holo_flag(0.0, grow=0.5, bright=2), FX0, FY0)
        vline(fx, FX0 + 7, 6, 13, A(CY[5], 150))
    elif i == 4:      # overshoot: full flag, white hot, sparkles
        over(fx, holo_flag(0.0, grow=1.0, bright=2), FX0, FY0)
        for (sx, sy) in ((21, 1), (16, 18)):
            px(fx, sx, sy, WHITE)
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px(fx, sx + dx, sy + dy, A(CY[6], 170))
    elif i == 5:
        over(fx, holo_flag(0.0, grow=1.0, bright=1), FX0, FY0)
        px(fx, 22, 1, A(CY[6], 200)); px(fx, 15, 19, A(CY[6], 160))
    else:
        ph = (i - 6) / 4.0
        fl = holo_flag(ph, grow=1.0, bright=0)
        halo = new(24, 40)
        for yy in range(fl.height):
            for xx in range(fl.width):
                if fl.getpixel((xx, yy))[3]:
                    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        X, Y = FX0 + xx + dx, FY0 + yy + dy
                        if 0 <= X < 24 and 0 <= Y < 40 and X >= FX0:
                            halo.putpixel((X, Y), A(CY[4], 70))
        fx.alpha_composite(halo)
        over(fx, fl, FX0, FY0)
        sp = [(18, 19), (19, 18), (21, 1), (20, 0)][i - 6]
        px(fx, sp[0], sp[1], A(CY[6], 220))
        glow_dot(fx, cap[0], cap[1], 2.6 + (0.9 if (i - 6) in (1, 2) else 0), CY[5], 110)
    img.alpha_composite(fx)
    return img


def checkpoint_frames():
    return [checkpoint(i) for i in range(10)]


# ----------------------------------------------------------------------------
# MPLAT 48x16 : hover 0-3
# ----------------------------------------------------------------------------
def mplat(f):
    S = ST
    img = new(48, 16)
    # walk surface (rows 0-2)
    hline(img, 1, 46, 0, S[7]); hline(img, 1, 46, 1, S[6]); hline(img, 1, 46, 2, S[5])
    for x in range(3, 46, 4):
        px(img, x, 1, CY[4]); px(img, x, 2, S[3])
    px(img, 1, 0, S[6]); px(img, 46, 0, S[5]); px(img, 46, 1, S[4]); px(img, 46, 2, S[3])
    # hull: boat-shaped slab
    hline(img, 1, 46, 3, S[1])
    spans = {4: (2, 45), 5: (2, 45), 6: (3, 44), 7: (5, 42), 8: (8, 39)}
    for y, (a, b) in spans.items():
        hline(img, a, b, y, S[3] if y < 7 else S[2])
        px(img, a, y, S[5]); px(img, b, y, S[1])
    hline(img, 3, 44, 4, S[4])
    hline(img, 6, 41, 7, S[2]); hline(img, 9, 38, 8, S[1])
    # light strip on the face
    hline(img, 6, 41, 5, INK[0])
    for k in range(9):
        x0 = 6 + k * 4
        on = (k - f) % 4 == 0
        hline(img, x0, x0 + 3, 5, CY[5] if on else CY[2])
        px(img, x0 + 3, 5, INK[0])
    # centre emblem plate
    rect(img, 21, 6, 6, 3, S[5]); hline(img, 21, 26, 6, S[6]); hline(img, 21, 26, 8, S[2])
    rect(img, 23, 7, 2, 1, CY[5])
    # thruster nozzles
    for x0 in (8, 33):
        rect(img, x0, 8, 7, 2, S[2]); hline(img, x0, x0 + 6, 8, S[4]); px(img, x0, 8, S[5])
        hline(img, x0 + 1, x0 + 5, 10, S[1])
        hline(img, x0 + 1, x0 + 5, 10, CY[6])
    img = outline(img)
    # exhaust (after outline)
    fx = new(48, 16)
    lens = [(4, 3), (5, 4), (3, 5), (4, 3)][f]
    for n, x0 in enumerate((8, 33)):
        ln = lens[n]
        for d in range(ln):
            y = 11 + d
            half = [2, 2, 1, 1, 0][d] if d < ln - 1 else 0
            for x in range(x0 + 3 - half, x0 + 3 + half + 1):
                core = abs(x - (x0 + 3)) < half or half == 0
                c = (WHITE if core else CY[6]) if d == 0 else (CY[6] if core else CY[4]) if d == 1 else CY[4] if d == 2 else CY[3]
                px(fx, x, y, A(c, [255, 240, 200, 150, 100][d]))
        px(fx, x0 + 3 + (1 if (f + n) % 2 else -1), 11 + ln, A(CY[4], 110))
    img.alpha_composite(fx)
    return img


def mplat_frames():
    return [mplat(f) for f in range(4)]


# ----------------------------------------------------------------------------
# TANK4 40x72 : frames 0-4 = number of quarters filled (from the bottom)
# ----------------------------------------------------------------------------
TANK_SECT = [(9, 20), (24, 35), (39, 50), (54, 65)]      # top .. bottom, inclusive rows
TANK_BAND = [(21, 23), (36, 38), (51, 53)]


def tank4(n):
    S = ST
    img = new(40, 72)
    GX0, GX1 = 4, 35                       # glass columns
    # ---- glass sections ----
    for si, (y0, y1) in enumerate(TANK_SECT):
        full = (3 - si) < n
        topmost_full = full and (3 - si) == n - 1
        w = GX1 - GX0 + 1
        for x in range(GX0, GX1 + 1):
            t = (x - GX0) / float(w - 1)
            for y in range(y0, y1 + 1):
                if full:
                    # cylinder of glowing fuel: bright left-centre, deeper to the right
                    v = 0.52 + 0.42 * math.cos((t - 0.30) * 3.2)
                    c = band_pick([CY[2], CY[3], CY[4], CY[5]], v, x, y, 0.08)
                else:
                    v = 0.30 + 0.42 * math.cos((t - 0.30) * 3.2)
                    c = band_pick([INK[0], INK[1], INK[2], NV[1]], v, x, y, 0.08)
                px(img, x, y, c)
        # glass edges
        vline(img, GX0, y0, y1, CY[2] if full else INK[0]); vline(img, GX1, y0, y1, CY[1] if full else INK[0])
        vline(img, GX1 - 1, y0, y1, CY[2] if full else INK[1])
        # specular streaks on the glass
        hl = CY[6] if full else NV[3]
        hl2 = CY[5] if full else NV[2]
        vline(img, GX0 + 3, y0 + 1, y1 - 3, hl); vline(img, GX0 + 4, y0 + 1, y1 - 5, hl2)
        px(img, GX0 + 3, y1 - 1, hl)
        vline(img, GX1 - 4, y0 + 4, y1 - 1, CY[4] if full else NV[1])
        if full:
            # bubbles: a few deliberate round ones rising through the fuel
            for (bx, by, big) in (((14, 7, True), (24, 4, False), (9, 9, False)),
                                  ((21, 6, True), (12, 3, False), (27, 9, False)),
                                  ((11, 5, True), (25, 8, False), (19, 3, False)),
                                  ((23, 7, True), (10, 4, False), (16, 9, False)))[si]:
                X, Y = GX0 + bx, y0 + by
                if big:
                    px(img, X, Y, WHITE); px(img, X + 1, Y, CY[6]); px(img, X, Y + 1, CY[6]); px(img, X + 1, Y + 1, CY[3])
                else:
                    px(img, X, Y, CY[6]); px(img, X, Y + 1, CY[3])
            if topmost_full:
                hline(img, GX0 + 1, GX1 - 1, y0, WHITE); hline(img, GX0 + 1, GX1 - 1, y0 + 1, CY[6])
                hline(img, GX0 + 6, GX0 + 12, y0 + 2, CY[6])
        else:
            # empty: shadow under the band above, faint rim of the jar floor
            hline(img, GX0 + 1, GX1 - 1, y0, INK[0]); hline(img, GX0 + 1, GX1 - 1, y0 + 1, INK[0])
            hline(img, GX0 + 6, GX1 - 8, y1, NV[1]); hline(img, GX0 + 9, GX0 + 14, y1, NV[2])
    # ---- bands between sections (flanges) ----
    cols = cyl_cols(36, S, lo=2, hi=7)
    for (y0, y1) in TANK_BAND:
        for i, c in enumerate(cols):
            px(img, 2 + i, y0, c); px(img, 2 + i, y0 + 1, S[max(1, S.index(c) - 1)]); px(img, 2 + i, y1, S[max(0, S.index(c) - 3)])
        for bx in (7, 15, 23, 31):
            px(img, bx, y0 + 1, S[7]); px(img, bx + 1, y0 + 1, S[1])
    # glow spill from fuel onto the bands
    for si, (y0, y1) in enumerate(TANK_SECT):
        if (3 - si) < n:
            for x in range(8, 32, 1):
                if y1 + 1 <= 65 and (x % 2 == 0):
                    px(img, x, y1 + 1, A(CY[4], 110))
                if y0 - 1 >= 21 and (x % 2 == 1):
                    px(img, x, y0 - 1, A(CY[4], 90))
    # ---- top cap ----
    dome = {4: (9, 30), 5: (6, 33), 6: (4, 35), 7: (3, 36), 8: (2, 37)}
    for y, (a, b) in dome.items():
        cc = cyl_cols(b - a + 1, S, lo=2, hi=7 if y < 8 else 6)
        for i, c in enumerate(cc):
            px(img, a + i, y, c)
    hline(img, 2, 37, 8, S[1])
    cc = cyl_cols(36, S, lo=2, hi=6)
    for i, c in enumerate(cc):
        px(img, 2 + i, 7, c)
    hline(img, 10, 22, 4, S[7])
    # valve + pipe stub
    rect(img, 15, 1, 10, 3, S[4]); hline(img, 15, 24, 1, S[7]); hline(img, 15, 24, 3, S[2]); px(img, 15, 2, S[6]); px(img, 24, 2, S[2])
    rect(img, 18, 2, 4, 1, GD[3]); px(img, 18, 2, GD[4])
    # status lamp on the dome
    px(img, 29, 5, CY[5] if n == 4 else GD[3] if n else RD[3]); px(img, 30, 5, CY[3] if n == 4 else GD[2] if n else RD[2])
    # ---- base ----
    cc = cyl_cols(36, S, lo=2, hi=6)
    for i, c in enumerate(cc):
        px(img, 2 + i, 66, c)
    rect(img, 1, 67, 38, 4, S[3]); hline(img, 1, 38, 67, S[6]); hline(img, 1, 38, 70, S[1]); vline(img, 1, 67, 70, S[5]); vline(img, 38, 68, 70, S[1])
    hazard(img, 8, 68, 24, 2, GD[3], INK[1])
    rivet(img, 4, 68, S, 3); rivet(img, 34, 68, S, 3)
    return outline(img)


def tank_frames():
    return [tank4(n) for n in range(5)]


# ----------------------------------------------------------------------------
# REACTOR 64x112 : back (vessel) + front (glass highlights, collars)
# tube = x 20..43, y 16..95 (flat ink1 in the back image)
# ----------------------------------------------------------------------------
TUBE = (20, 16, 43, 95)


def reactor_collars(img):
    """Top and bottom collars that clamp the gauge tube (shared by back and front)."""
    H = RH
    for (y0, top) in ((10, True), (96, False)):
        cc = cyl_cols(34, H, lo=3, hi=7)
        for i, c in enumerate(cc):
            x = 15 + i
            k = H.index(c)
            vline(img, x, y0, y0 + 5, c)
            px(img, x, y0, H[min(7, k + 1)]); px(img, x, y0 + 5, H[max(0, k - 3)])
            px(img, x, y0 + 4, H[max(0, k - 1)])
        # bolts
        for bx in (18, 25, 37, 44):
            px(img, bx, y0 + 2, H[7]); px(img, bx + 1, y0 + 3, H[1])
        # accent lamp
        rect(img, 29, y0 + 2, 6, 2, OR[1]); hline(img, 30, 33, y0 + 2, OR[4]); hline(img, 30, 33, y0 + 3, OR[3]); px(img, 30, y0 + 2, OR[6])


def reactor_back():
    H = RH
    img = new(64, 112)
    # ---- vessel shell (big cylinder, rows 14..99) ----
    shell = [H[1], H[2], H[3], H[4]]
    for y in range(14, 100):
        for x in range(2, 62):
            t = (x - 2) / 59.0
            v = 0.50 + 0.50 * math.cos((t - 0.24) * 3.3)
            v = max(0.0, v) * 0.95
            px(img, x, y, band_pick(shell, v, x, y, 0.3))
    vline(img, 2, 14, 99, H[2]); vline(img, 61, 14, 99, H[0]); vline(img, 60, 14, 99, H[1])
    # vertical plate seams + rivet columns
    for sx in (13, 50):
        vline(img, sx, 16, 97, H[0]); vline(img, sx + 1, 16, 97, H[3] if sx < 30 else H[2])
    for ry in range(19, 97, 7):
        px(img, 11, ry, H[5]); px(img, 52, ry, H[3]); px(img, 53, ry + 1, H[0]); px(img, 10, ry + 1, H[1])
    # glowing core slits either side (reactor heat showing through)
    for (sx, bright) in ((6, 1.0), (56, 0.8)):
        rect(img, sx - 1, 24, 4, 66, H[0])
        for y in range(25, 89):
            t = 1.0 - abs((y - 57) / 32.0)
            c = band_pick([OR[1], OR[2], OR[3], OR[4], OR[5]], t * bright, sx, y, 0.3)
            px(img, sx, y, c); px(img, sx + 1, y, band_pick([OR[0], OR[1], OR[2], OR[3]], t * bright, sx + 1, y, 0.3))
        vline(img, sx + 2, 24, 89, H[4] if sx < 30 else H[2])
    # ---- gauge frame: struts hugging the tube ----
    for (x0, flip) in ((16, False), (44, True)):
        cc = cyl_cols(4, H, lo=3, hi=7)
        for i, c in enumerate(cc):
            vline(img, x0 + i, 14, 97, c)
    vline(img, 15, 14, 97, H[0]); vline(img, 48, 14, 97, H[0])
    # the tube itself: flat, the game draws the liquid here
    rect(img, 20, 16, 24, 80, INK[1])
    # ---- top cap ----
    dome = {6: (10, 53), 7: (7, 56), 8: (5, 58), 9: (4, 59), 10: (3, 60), 11: (2, 61), 12: (2, 61), 13: (2, 61)}
    for y, (a, b) in dome.items():
        cc = cyl_cols(b - a + 1, H, lo=2, hi=6)
        for i, c in enumerate(cc):
            px(img, a + i, y, c)
    hline(img, 12, 30, 6, H[7]); hline(img, 2, 61, 13, H[0]); hline(img, 3, 60, 12, H[2])
    # pipe stub + flange on top
    cc = cyl_cols(14, H, lo=2, hi=7)
    for i, c in enumerate(cc):
        vline(img, 25 + i, 1, 5, c)
    hline(img, 23, 40, 4, H[1]); 
    cc = cyl_cols(18, H, lo=3, hi=7)
    for i, c in enumerate(cc):
        px(img, 23 + i, 3, c); px(img, 23 + i, 4, H[max(0, H.index(c) - 2)])
    # warning beacons on the dome shoulders
    for (bx, lit) in ((8, True), (52, True)):
        rect(img, bx, 4, 4, 3, OR[2]); hline(img, bx, bx + 3, 4, OR[4]); px(img, bx, 4, OR[6]); hline(img, bx, bx + 3, 6, H[1])
        px(img, bx - 0, 3, T)
    # ---- base ----
    cc = cyl_cols(56, H, lo=2, hi=6)
    for i, c in enumerate(cc):
        vline(img, 4 + i, 100, 102, c); px(img, 4 + i, 100, H[min(7, H.index(c) + 1)]); px(img, 4 + i, 102, H[max(0, H.index(c) - 2)])
    rect(img, 1, 103, 62, 8, H[3]); hline(img, 1, 62, 103, H[6]); hline(img, 1, 62, 110, H[0]); vline(img, 1, 104, 110, H[5]); vline(img, 62, 104, 110, H[1])
    hline(img, 2, 61, 104, H[4]); hline(img, 2, 61, 109, H[1])
    hazard(img, 10, 105, 44, 3, GD[3], INK[1])
    hline(img, 10, 53, 108, H[1])
    for bx in (4, 57):
        rivet(img, bx, 105, H, 4); rivet(img, bx, 108, H, 3)
    reactor_collars(img)
    rect(img, 20, 16, 24, 80, INK[1])
    return outline(img)


def reactor_front():
    img = new(64, 112)
    # collars overlap the ends of the tube so a full/overflowing wave is tucked away neatly
    reactor_collars(img)
    for x in range(64):
        for y in range(112):
            if 20 <= x <= 43 and 16 <= y <= 95:
                img.putpixel((x, y), T)
    # ink lip where the collar meets the glass (outside the tube rows)
    # ---- inside the tube: translucent glass only ----
    for y in range(16, 96):
        # curvature shading at the glass edges
        px(img, 20, y, A(INK[0], 120)); px(img, 21, y, A(INK[0], 50))
        px(img, 43, y, A(INK[0], 150)); px(img, 42, y, A(INK[0], 90)); px(img, 41, y, A(INK[0], 40))
    # specular streaks (broken, like real glass)
    for (x, y0, y1, a) in ((23, 19, 58, 150), (24, 19, 40, 80), (23, 62, 70, 110), (23, 74, 76, 80), (39, 30, 80, 45), (39, 84, 90, 45)):
        vline(img, x, y0, y1, A(WHITE, a))
    px(img, 24, 18, A(WHITE, 150)); px(img, 25, 17, A(WHITE, 110))
    # shadow under the top collar, glint above the bottom one
    hline(img, 20, 43, 16, A(INK[0], 140)); hline(img, 20, 43, 17, A(INK[0], 70))
    hline(img, 22, 41, 95, A(INK[0], 90))
    return img


# ----------------------------------------------------------------------------
# LIQUID_TOP 24x6 : wave 0-3 (white, tinted in code; rows 4-5 always solid)
# ----------------------------------------------------------------------------
def liquid_top(f):
    img = new(24, 6)
    GREY = hexc("#c8d3df")
    for x in range(24):
        h = 1.25 * math.sin(2 * math.pi * (x / 12.0 - f / 4.0)) + 0.75 * math.sin(2 * math.pi * (x / 24.0 + f / 4.0) + 1.0)
        top = int(round(2.0 - h * 0.9))
        top = max(0, min(3, top))
        for y in range(top, 6):
            px(img, x, y, WHITE)
        if top + 1 <= 3:
            px(img, x, top + 1, GREY)
    return img


def liquid_frames():
    return [liquid_top(f) for f in range(4)]


# ----------------------------------------------------------------------------
# BRIDGE EMITTER 24x40 : idle 0-3, off 4.  Emits to the RIGHT from the shoe at its foot.
# ----------------------------------------------------------------------------
def ring_h(img, x0, x1, y, R, lvl):
    """One chunky 3-row coil ring with rounded ends. lvl 0 dull, 1 lit, 2 hot."""
    w = x1 - x0 + 1
    lo, hi = [(0, 3), (2, 5), (4, 6)][lvl]
    cols = cyl_cols(w, R, lo=lo, hi=hi)
    for i, c in enumerate(cols):
        k = R.index(c)
        top = R[min(6, k + 1)]
        if lvl == 2 and 1 <= i <= w * 0.55:
            top = WHITE
        px(img, x0 + i, y, top); px(img, x0 + i, y + 1, c); px(img, x0 + i, y + 2, R[max(0, k - 2)])
    for (cx, cy) in ((x0, y), (x1, y), (x0, y + 2), (x1, y + 2)):
        img.putpixel((cx, cy), T)
    if lvl:
        px(img, x0 + 2, y, WHITE); px(img, x0 + 3, y, WHITE)


def bridge_emitter(f, off=False):
    S = ST
    img = new(24, 40)
    # foot
    rect(img, 1, 35, 21, 4, S[4]); hline(img, 2, 21, 35, S[7]); hline(img, 1, 21, 38, S[1]); hline(img, 2, 21, 37, S[3])
    px(img, 1, 35, T); vline(img, 1, 36, 37, S[6])
    hazard(img, 3, 36, 10, 2, GD[3], INK[1])
    # tower core
    cyl_v(img, 4, 7, 8, 28, S, lo=1, hi=5)
    # coil rings (energy runs down the tower towards the shoe)
    for k in range(4):
        y = 9 + k * 6
        lvl = 0 if off else (2 if k == f else 1)
        ring_h(img, 2, 13, y, CY, lvl)
        hline(img, 4, 11, y + 3, S[0])
    # cap + antenna
    rect(img, 3, 4, 10, 3, S[4]); hline(img, 4, 11, 4, S[7]); hline(img, 3, 12, 6, S[1]); px(img, 3, 5, S[6]); px(img, 3, 4, T); px(img, 12, 4, T)
    px(img, 12, 5, S[2])
    vline(img, 7, 2, 3, S[6]); vline(img, 8, 2, 3, S[3])
    if off:
        rect(img, 7, 0, 2, 2, CY[1])
    else:
        rect(img, 7, 0, 2, 2, CY[5] if f % 2 else CY[6]); px(img, 7, 0, WHITE)
    # projector shoe (bottom right): housing + lens facing right
    rect(img, 14, 26, 7, 10, S[4])
    hline(img, 14, 19, 26, S[7]); hline(img, 14, 20, 27, S[6]); vline(img, 20, 28, 34, S[2])
    px(img, 20, 26, T); px(img, 20, 27, S[5])
    # energy window on the shoe
    rect(img, 15, 29, 4, 4, INK[0])
    wc = CY[1] if off else (WHITE if f == 3 else CY[5])
    rect(img, 16, 30, 2, 2, wc)
    if not off:
        px(img, 16, 30, WHITE)
    rivet(img, 15, 34, S, 4)
    # lens
    lc = [CY[0], CY[1], CY[1]] if off else [CY[4], CY[6], WHITE]
    rect(img, 20, 28, 3, 9, INK[0])
    vline(img, 21, 28, 37, lc[1]); vline(img, 22, 29, 36, lc[2]); vline(img, 20, 28, 37, S[1])
    px(img, 21, 28, lc[0]); px(img, 21, 37, lc[0])
    rect(img, 14, 36, 8, 3, S[3]); hline(img, 14, 21, 38, S[1])
    vline(img, 21, 36, 38, lc[1])
    img = outline(img)
    if not off:
        fx = new(24, 40)
        a0 = (130, 100, 130, 190)[f]
        vline(fx, 23, 29, 38, A(CY[5], a0))
        px(fx, 23, 39, A(CY[5], a0 // 2)); px(fx, 22, 39, A(CY[5], a0 // 2)); px(fx, 21, 39, A(CY[5], a0 // 3))
        # hot ring halo
        y = 9 + f * 6
        px(fx, 0, y + 1, A(CY[5], 130)); px(fx, 15, y + 1, A(CY[5], 130))
        glow_dot(fx, 7.5, 0.5, 2.5, CY[5], 90)
        out = new(24, 40)
        for yy in range(40):
            for xx in range(24):
                c = img.getpixel((xx, yy))
                out.putpixel((xx, yy), c if c[3] else fx.getpixel((xx, yy)))
        img = out
    return img


def emitter_frames():
    return [bridge_emitter(f) for f in range(4)] + [bridge_emitter(0, off=True)]


# ----------------------------------------------------------------------------
# BRIDGE SEG 16x12 : flow 0-3.  Hard-light plank, tiles in X.
# ----------------------------------------------------------------------------
def bridge_seg(f):
    img = new(16, 12)
    for x in range(16):
        # walk surface: two solid bright rows
        img.putpixel((x, 0), CY[6]); img.putpixel((x, 1), CY[5]); img.putpixel((x, 2), A(CY[4], 240))
        for y in range(3, 9):
            # chevrons flowing right: period 8, 2px per frame
            k = (x - f * 2 + abs(y - 5.5) + 0.5) % 8
            fade = [175, 165, 155, 145, 135, 125][y - 3]
            if k < 1:
                c = A(CY[6], 230)
            elif k < 2:
                c = A(CY[5], 205)
            else:
                c = A(CY[4], fade)
            img.putpixel((x, y), c)
        img.putpixel((x, 9), A(CY[5], 215))
        img.putpixel((x, 10), A(CY[4], 120 if x % 2 == 0 else 80))
        img.putpixel((x, 11), A(CY[3], 55 if (x + 1) % 2 == 0 else 0))
    # plank joint: a thin bright seam + a notch in the top glint
    for y in range(2, 10):
        img.putpixel((0, y), A(CY[6], 235))
    img.putpixel((0, 0), WHITE); img.putpixel((0, 1), CY[6]); img.putpixel((15, 1), CY[4])
    # travelling glint on the top edge
    gx = (f * 4 + 3) % 16
    for d in range(3):
        img.putpixel(((gx + d) % 16, 0), WHITE)
    img.putpixel(((gx + 1) % 16, 1), CY[6])
    return img


def seg_frames():
    return [bridge_seg(f) for f in range(4)]


# ----------------------------------------------------------------------------
# BEAM 16x16 : flow 0-3.  Vertical, tiles in Y, energy travels UP.
# ----------------------------------------------------------------------------
def beam(f):
    img = new(16, 16)
    for y in range(16):
        ph = 2 * math.pi * ((y + f * 4) / 16.0)
        w = math.sin(ph * 2)                 # edge wobble, two bulges per tile
        for x in range(16):
            d = abs(x - 7.5)
            edge = 3.0 + 0.9 * w
            if d < edge - 0.9:
                c = WHITE
            elif d < edge + 0.1:
                c = CY[6]
            elif d < edge + 1.1:
                c = CY[5]
            elif d < edge + 2.1:
                c = A(CY[4], 215)
            elif d < edge + 3.1:
                c = A(CY[3], 130)
            elif d < edge + 4.1:
                c = A(CY[3], 55)
            else:
                c = T
            img.putpixel((x, y), c)
        # streaks racing up the core
        s = (y + f * 4) % 16
        if s in (1, 2, 3):
            img.putpixel((6, y), CY[6])
        if s in (9, 10, 11, 12):
            img.putpixel((9, y), CY[6])
        if s in (5, 6):
            img.putpixel((8, y), CY[5])
    return img


def beam_frames():
    return [beam(f) for f in range(4)]


# ----------------------------------------------------------------------------
# HOLO PROJECTOR 32x16 : on 0-3
# ----------------------------------------------------------------------------
def holo_proj(f):
    S = ST
    img = new(32, 16)
    # skirt
    hline(img, 4, 27, 14, S[1]); hline(img, 3, 28, 13, S[3]); hline(img, 3, 28, 12, S[4]); hline(img, 4, 27, 11, S[5])
    px(img, 3, 12, S[6]); px(img, 4, 11, S[7]); hline(img, 5, 12, 11, S[6]); px(img, 28, 13, S[1]); px(img, 28, 12, S[2])
    # status lights round the skirt (the Phantom has hijacked it: pink)
    for k, x in enumerate((6, 10, 21, 25)):
        on = (k + f) % 4 < 2
        px(img, x, 12, PK[3] if on else PK[1]); px(img, x + 1, 12, PK[2] if on else PK[0])
    rect(img, 14, 12, 4, 2, INK[0]); px(img, 15, 12, CY[4]); px(img, 16, 12, CY[2])
    # dish
    hline(img, 6, 25, 10, S[3]); hline(img, 7, 24, 9, S[6]); hline(img, 9, 22, 8, S[5])
    px(img, 6, 10, S[5]); px(img, 7, 9, S[7]); px(img, 8, 9, S[7]); px(img, 25, 10, S[1]); px(img, 24, 9, S[3])
    # lens
    lc = [CY[5], CY[6], CY[5], WHITE][f]
    hline(img, 10, 21, 8, CY[3]); hline(img, 11, 20, 8, CY[4]); hline(img, 12, 19, 8, lc)
    hline(img, 10, 21, 9, CY[2]); hline(img, 12, 19, 9, CY[4]); hline(img, 13, 16, 9, CY[5])
    img = outline(img)
    # light cone (after outline): bright edge rays, faint fill, fading out towards the top
    fx = new(32, 16)
    for y in range(0, 8):
        t = (7 - y) / 7.0                       # 0 at lens, 1 at top
        half = 5.0 + t * 8.5
        k = (1.0 - t)
        for x in range(32):
            d = abs(x - 15.5)
            if d <= half:
                edge = d > half - 1.3
                a = (40 + 190 * k) if edge else (25 + 120 * k ** 1.3)
                c = CY[5] if edge else CY[4]
                band = (y + f * 2) % 8
                if band == 0 and not edge:
                    c = CY[6]; a = a * 1.7 + 25 * k
                elif band == 1 and not edge:
                    c = CY[5]; a = a * 1.25
                if t > 0.9:
                    a *= 0.45                     # the top row just melts away
                if a > 8:
                    px(fx, x, y, A(c, int(min(255, a))))
    # glitch pixels (phantom signature)
    gl = [((9, 3), (22, 5)), ((20, 2),), ((12, 5), (24, 1)), ((7, 1),)][f]
    for (gx, gy) in gl:
        px(fx, gx, gy, A(PK[3], 230)); px(fx, gx + 1, gy, A(PU[4], 200))
    out = new(32, 16)
    out.alpha_composite(fx); out.alpha_composite(img)
    return out


def holo_frames():
    return [holo_proj(f) for f in range(4)]


# ----------------------------------------------------------------------------
# CANNON 64x48 : idle 0-1, charge 2-5, fire 6-9.  "Restorer beam projector", aims UP.
# ----------------------------------------------------------------------------
def cannon_barrel(rings, lens):
    """Barrel layer, 24 wide x 30 tall; (0,0) = top-left at rest. rings: 3 levels bottom..top."""
    S = ST
    b = new(24, 32)
    # tube
    cyl_v(b, 4, 4, 16, 26, S, lo=2, hi=7)
    # muzzle collar
    cc = cyl_cols(20, S, lo=3, hi=7)
    for i, c in enumerate(cc):
        k = S.index(c)
        px(b, 2 + i, 3, S[min(7, k + 1)]); px(b, 2 + i, 4, c); px(b, 2 + i, 5, c); px(b, 2 + i, 6, S[max(0, k - 2)])
    hazard(b, 5, 7, 14, 2, GD[3], INK[1])
    # lens (seen slightly from above)
    L = lens
    lp = [(CY[1], CY[2], CY[3]), (CY[3], CY[4], CY[6]), (CY[4], CY[6], WHITE), (CY[6], WHITE, WHITE)][L]
    hline(b, 4, 19, 2, lp[0]); hline(b, 5, 18, 1, lp[1]); hline(b, 7, 16, 0, lp[1]); hline(b, 6, 17, 2, lp[1])
    hline(b, 7, 12, 1, lp[2]); hline(b, 8, 10, 0, lp[2])
    px(b, 4, 2, S[2]); px(b, 19, 2, S[2])
    # coil rings
    for k in range(3):
        y = 22 - k * 5
        ring_h(b, 2, 21, y, CY, rings[k])
        hline(b, 4, 19, y + 3, S[1])
    return b


def cannon(i):
    """0-1 idle, 2-5 charge, 6-9 fire"""
    S = ST
    img = new(64, 48)
    if i < 2:
        rings = (1, 0, 0) if i == 0 else (0, 0, 0); lens = 1; dy = 0; cell = 1; mode = "idle"; f = i
    elif i < 6:
        f = i - 2
        rings = [(2, 1, 0), (1, 2, 1), (1, 1, 2), (2, 2, 2)][f]; lens = [1, 2, 2, 3][f]; dy = [0, 0, 0, 1][f]; cell = 1 + f; mode = "charge"
    else:
        f = i - 6
        rings = [(2, 2, 2), (2, 2, 2), (1, 1, 2), (1, 0, 0)][f]; lens = [3, 3, 2, 1][f]; dy = [4, 3, 1, 0][f]; cell = [4, 2, 1, 1][f]; mode = "fire"
    # ---- barrel (behind the hull) ----
    b = cannon_barrel(rings, lens)
    over(img, b, 20, 2 + dy)
    # ---- side capacitors ----
    for (x0, mir) in ((9, False), (47, True)):
        cyl_v(img, x0, 19, 8, 10, S, lo=2, hi=6)
        hline(img, x0, x0 + 7, 18, GD[3]); hline(img, x0 + 1, x0 + 6, 17, GD[4]); px(img, x0 + 1, 17, GD[5]); px(img, x0 + 7, 18, GD[2]); px(img, x0, 18, GD[4])
        rect(img, x0 + 2, 21, 4, 6, INK[0])
        for k in range(3):
            on = cell > (2 - k) + (0 if mode != "idle" else 1)
            hline(img, x0 + 2, x0 + 5, 21 + k * 2, CY[5] if on else CY[1]); hline(img, x0 + 2, x0 + 5, 22 + k * 2, CY[3] if on else CY[0])
        # cable to the barrel
        if not mir:
            line(img, x0 + 8, 20, x0 + 12, 24, S[1])
        else:
            line(img, x0 - 1, 20, x0 - 5, 24, S[1])
    # ---- hull (squat, sloped shoulders) ----
    sq = 1 if (mode == "fire" and f == 0) else 0
    top = 28 + sq
    for y in range(top, 41):
        inset = max(0, 6 - (y - top) * 2)
        a, bb = 6 + inset, 57 - inset
        cc = cyl_cols(bb - a + 1, S, lo=2, hi=6)
        for k, c in enumerate(cc):
            px(img, a + k, y, c)
    for k in range(4):
        inset = max(0, 6 - k * 2)
        px(img, 6 + inset, top + k, S[7]); px(img, 7 + inset, top + k, S[6]); px(img, 57 - inset, top + k, S[1])
    hline(img, 13, 50, top, S[7]); hline(img, 13, 50, top + 1, S[6])
    hline(img, 6, 57, 40, S[1])
    # barrel socket
    rect(img, 21, top - 1, 22, 4, S[2]); hline(img, 21, 42, top - 1, S[6]); hline(img, 22, 41, top + 2, S[0]); px(img, 21, top - 1, S[7])
    # front panel: charge gauge in four cells - four quarters make the whole shot
    rect(img, 22, 33, 21, 6, INK[0])
    segs = {"idle": 1, "charge": 1 + f, "fire": [4, 3, 1, 0][f] if mode == "fire" else 0}[mode]
    for k in range(4):
        on = k < segs
        x0 = 23 + k * 5
        hot = on and k == segs - 1 and mode == "charge"
        rect(img, x0, 34, 4, 4, WHITE if hot else CY[5] if on else CY[1])
        if on and not hot:
            hline(img, x0, x0 + 3, 37, CY[3]); px(img, x0, 34, CY[6])
        elif not on:
            hline(img, x0, x0 + 3, 37, CY[0])
    # side vents + bolts
    for vx in (10, 46):
        for k in range(3):
            hline(img, vx, vx + 7, 34 + k * 2, S[1]); hline(img, vx, vx + 7, 35 + k * 2, S[5] if vx < 30 else S[3])
    rivet(img, 19, 30 + sq, S, 4); rivet(img, 43, 30 + sq, S, 3)
    # ---- base / feet ----
    rect(img, 3, 41, 58, 6, S[3]); hline(img, 4, 59, 41, S[6]); hline(img, 3, 60, 46, S[1]); vline(img, 3, 42, 45, S[5]); vline(img, 60, 42, 46, S[1])
    px(img, 3, 41, T); px(img, 60, 41, T)
    hline(img, 4, 59, 42, S[4])
    hazard(img, 16, 43, 32, 3, GD[3], INK[1])
    for fx0 in (5, 50):
        rect(img, fx0, 43, 9, 3, S[2]); hline(img, fx0, fx0 + 8, 43, S[5]); px(img, fx0 + 2, 44, S[6]); px(img, fx0 + 6, 44, S[6])
    img = outline(img)
    # ---- FX ----
    fx = new(64, 48)
    cx = 31.5
    if mode == "idle":
        if f == 0:
            px(fx, 31, 1, A(CY[6], 160)); px(fx, 32, 1, A(CY[6], 160))
    elif mode == "charge":
        # motes converging on the lens
        R0 = [9, 7, 5, 3][f]
        for ang in (200, 250, 290, 340, 225, 315):
            a = math.radians(ang + f * 9)
            x = cx + math.cos(a) * R0 * 1.4; y = 3 + dy + math.sin(a) * R0 * 0.5 - R0 * 0.2
            px(fx, x, y, A(CY[6] if f < 3 else WHITE, 230))
        glow_dot(fx, cx, 2.5 + dy, 3.5 + f * 1.3, CY[5], 70 + f * 30)
    else:
        if f == 0:      # muzzle flash
            for y in range(0, 7):
                half = 11 - abs(y - 5) * 1.3
                for x in range(64):
                    d = abs(x - cx)
                    if d < half:
                        px(fx, x, y, WHITE if d < half - 3 else A(CY[6], 235) if d < half - 1.5 else A(CY[4], 170))
            for (sx, sy) in ((14, 4), (49, 4), (17, 9), (46, 9), (11, 7), (52, 7)):
                px(fx, sx, sy, WHITE); px(fx, sx + (1 if sx > 32 else -1), sy, A(CY[5], 180))
        elif f == 1:
            for y in range(0, 6):
                half = 9 - abs(y - 3) * 1.6
                for x in range(64):
                    d = abs(x - cx)
                    if d < half:
                        px(fx, x, y, WHITE if d < half - 2.5 else A(CY[5], 200))
            for (sx, sy) in ((12, 2), (51, 2), (15, 11), (48, 11)):
                px(fx, sx, sy, A(CY[6], 220))
        elif f == 2:
            glow_dot(fx, cx, 3, 6, CY[5], 120)
            for (sx, sy) in ((20, 1), (43, 1)):
                px(fx, sx, sy, A(CY[5], 160))
        else:           # smoke wisps
            for (sx, sy, a) in ((27, 0, 120), (28, 1, 150), (36, 0, 110), (35, 2, 130), (31, 0, 90)):
                px(fx, sx, sy, A(S[7], a))
    img.alpha_composite(fx)
    return img


def cannon_frames():
    return [cannon(i) for i in range(10)]


# ----------------------------------------------------------------------------
# Context previews: props composited into rooms built from the real tiles + Jake
# ----------------------------------------------------------------------------
def build_room(skin, rows, bgcol="#05060c"):
    """rows: list of strings, '#' solid, '=' one-way platform, ' ' empty. Returns RGBA image."""
    til = Image.open(os.path.join(ASSETS, f"tiles/tiles_{skin}.png")).convert("RGBA")
    Ht = len(rows); Wt = max(len(r) for r in rows)
    rows = [r.ljust(Wt) for r in rows]
    img = new(Wt * 16, Ht * 16, hexc(bgcol))

    def tile(i):
        return til.crop(((i % 16) * 16, (i // 16) * 16, (i % 16) * 16 + 16, (i // 16) * 16 + 16))

    def sol(x, y):
        if x < 0 or x >= Wt or y < 0 or y >= Ht:
            return 1
        return 1 if rows[y][x] == "#" else 0
    rnd = random.Random(5)
    for y in range(Ht):
        for x in range(Wt):
            t = 48 + (1 if (x + y) % 5 == 0 else 2 if y % 6 == 2 else 0)
            if y == 3 and x > 3:
                t = 51
            if x % 11 == 6 and y > 3:
                t = 56
            if y == Ht - 6 and x % 8 == 2:
                t = 67
            img.alpha_composite(tile(t), (x * 16, y * 16))
    for y in range(Ht):
        for x in range(Wt):
            ch = rows[y][x]
            if ch == "=":
                l = x > 0 and rows[y][x - 1] == "="; r = x < Wt - 1 and rows[y][x + 1] == "="
                img.alpha_composite(tile(33 if (l and r) else 32 if r else 34 if l else 35), (x * 16, y * 16))
            if ch != "#":
                continue
            m = sol(x, y - 1) * 1 + sol(x + 1, y) * 2 + sol(x, y + 1) * 4 + sol(x - 1, y) * 8
            t = m
            if m == 15:
                deep = all(sol(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                t = (16 + rnd.randint(0, 1)) if deep else 15
            if m == 14 and x % 7 == 3:
                t = 20
            img.alpha_composite(tile(t), (x * 16, y * 16))
    return img


def jake_frame(i=0, flip=False):
    jk = Image.open(os.path.join(ASSETS, "sprites/jake.png")).convert("RGBA")
    fr = jk.crop(((i % 8) * 32, (i // 8) * 32, (i % 8) * 32 + 32, (i // 8) * 32 + 32))
    return flip_h(fr) if flip else fr


DIG = {"+": ["...", ".X.", "XXX", ".X.", "..."], "-": ["...", "...", "XXX", "...", "..."],
       "1": [".X.", "XX.", ".X.", ".X.", "XXX"], "2": ["XX.", "..X", ".X.", "X..", "XXX"], "3": ["XX.", "..X", ".X.", "..X", "XX."],
       "4": ["X.X", "X.X", "XXX", "..X", "..X"], "8": ["XXX", "X.X", "XXX", "X.X", "XXX"]}


def fake_label(img, x, y, sign, num, den, col):
    """Stand-in for the code-drawn fraction on an fblock screen (22x20 at x,y)."""
    stamp(img, DIG[sign], x + 3, y + 7, col)
    stamp(img, DIG[num], x + 12, y + 2, col)
    hline(img, x + 10, x + 16, y + 9, col)
    stamp(img, DIG[den], x + 12, y + 12, col)


def mock_dock():
    rows = [
        "##############################",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                    ===      ",
        "#                             ",
        "#                             ",
        "#                             ",
        "##############################",
        "##############################",
        "##############################",
        "##############################",
    ]
    img = build_room("dock", rows)
    G = 13 * 16
    door = door_frames(); cp = checkpoint_frames(); con = console_frames(); tk = tank_frames()
    img.alpha_composite(door[0], (20, G - 48))
    img.alpha_composite(door[7], (58, G - 48))
    img.alpha_composite(jake_frame(0), (92, G - 31))
    img.alpha_composite(cp[0], (122, G - 40))
    img.alpha_composite(cp[7], (144, G - 40))
    img.alpha_composite(con[1], (178, G - 32))
    img.alpha_composite(jake_frame(40), (196, G - 31))
    img.alpha_composite(lever("off"), (232, G - 24))
    img.alpha_composite(lever("on"), (258, G - 24))
    img.alpha_composite(tk[3], (296, G - 72))
    img.alpha_composite(tk[1], (340, G - 72))
    sp = spring_frames()
    img.alpha_composite(sp[0], (392, G - 16))
    img.alpha_composite(sp[2], (412, G - 16))
    img.alpha_composite(holo_frames()[0], (438, G - 16))
    # fblocks in a row above Jake's head (he bumps them from below)
    by = 64
    kinds = [("plus", "+", "1", "8"), ("minus", "-", "1", "4"), ("neutral", "+", "1", "2"), ("off", "+", "1", "8")]
    for k, (kind, sg, n, d) in enumerate(kinds):
        b = fblock(kind)
        x = 150 + k * 44
        img.alpha_composite(b, (x, by))
        if kind != "off":
            fake_label(img, x + 5, by + 6, sg, n, d, WHITE)
    img.alpha_composite(jake_frame(16), (150, by + 32 + 1))
    # one-way platform row is at y=9: put a console + checkpoint there too
    img.alpha_composite(con[8], (21 * 16 + 12, 9 * 16 - 32))
    # hover platform
    img.alpha_composite(mplat_frames()[1], (60, 96))
    img.alpha_composite(jake_frame(0), (70, 96 - 31))
    preview(img, "pm_mock_dock.png", scale=3, bg="#05060c")
    preview(img, "pm_mock_dock_2x.png", scale=2, bg="#05060c")
    preview(img.crop((0, 140, 240, 224)), "pm_mock_dock_a.png", scale=6, bg="#05060c")
    preview(img.crop((224, 120, 480, 224)), "pm_mock_dock_b.png", scale=6, bg="#05060c")
    preview(img.crop((40, 40, 340, 140)), "pm_mock_dock_c.png", scale=5, bg="#05060c")


def mock_bridge():
    rows = [
        "##############################",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#                             ",
        "#######                 ######",
        "#######                 ######",
        "#######                 ######",
        "#######                 ######",
        "#######                 ######",
    ]
    img = build_room("bridge", rows)
    G = 9 * 16
    em = emitter_frames(); sg = seg_frames()
    img.alpha_composite(em[1], (7 * 16 - 24, G - 40))
    for k in range(11):
        img.alpha_composite(sg[1], (7 * 16 + k * 16, G))
    img.alpha_composite(jake_frame(9), (7 * 16 + 60, G - 31))
    img.alpha_composite(jake_frame(0), (40, G - 31))
    img.alpha_composite(em[4], (24 * 16 + 30, G - 40))
    preview(img, "pm_mock_bridge.png", scale=3, bg="#05060c")


def mock_reactor():
    rows = ["####################"] + ["#                   "] * 9 + ["####################"] * 3
    img = build_room("reactor", rows)
    G = 10 * 16
    rb, rf = reactor_back(), reactor_front()
    liq = liquid_frames()
    for n, (x, lvl, col) in enumerate(((40, 0.375, CY[4]), (150, 0.75, OR[4]))):
        img.alpha_composite(rb, (x, G - 112))
        hgt = int(round(80 * lvl)); ytop = G - 112 + 96 - hgt
        rect(img, x + 20, ytop, 24, hgt, col)
        for yy in range(6):
            for xx in range(24):
                c = liq[n].getpixel((xx, yy))
                if c[3]:
                    img.putpixel((x + 20 + xx, ytop - 4 + yy), (c[0] * col[0] // 255, c[1] * col[1] // 255, c[2] * col[2] // 255, 255))
        img.alpha_composite(rf, (x, G - 112))
    img.alpha_composite(jake_frame(0), (112, G - 31))
    img.alpha_composite(console_frames()[5], (220, G - 32))
    img.alpha_composite(lever("mid"), (250, G - 24))
    for k, kind in enumerate(("plus", "minus")):
        img.alpha_composite(fblock(kind), (236 + k * 40, G - 31 - 46))
    preview(img, "pm_mock_reactor.png", scale=3, bg="#05060c")


def mock_boss():
    rows = ["####################"] + ["#                   "] * 9 + ["####################"] * 3
    img = build_room("boss", rows)
    G = 10 * 16
    cf = cannon_frames(); bm = beam_frames()
    img.alpha_composite(cf[0], (24, G - 48))
    img.alpha_composite(cf[4], (100, G - 48))
    img.alpha_composite(cf[7], (176, G - 48))
    for t in range(7):
        img.alpha_composite(bm[t % 4], (176 + 24, G - 48 - 16 * (t + 1) + 3))
    img.alpha_composite(jake_frame(0), (78, G - 31))
    img.alpha_composite(holo_frames()[2], (256, G - 16))
    preview(img, "pm_mock_boss.png", scale=3, bg="#05060c")


def contact_sheet():
    """Every saved sheet exactly as the game will load it, stacked on one page."""
    names = ["door", "checkpoint", "console", "fblock", "lever", "spring", "mplat", "tank4", "bridge_emitter",
             "bridge_seg", "liquid_top", "beam", "holo_proj", "cannon"]
    ims = [Image.open(os.path.join(ASSETS, "sprites", n + ".png")).convert("RGBA") for n in names]
    ims += [Image.open(os.path.join(ASSETS, "props", n + ".png")).convert("RGBA") for n in ("reactor_back", "reactor_front")]
    W = 660
    x = y = 2; rowh = 0
    pos = []
    for im in ims:
        if x + im.width + 2 > W:
            x = 2; y += rowh + 4; rowh = 0
        pos.append((x, y)); x += im.width + 6; rowh = max(rowh, im.height)
    page = new(W, y + rowh + 2, hexc("#1b2547"))
    for im, p in zip(ims, pos):
        page.alpha_composite(im, p)
    preview(page, "pm_all.png", scale=2, bg="#1b2547")


# ----------------------------------------------------------------------------
# Build: sheets, images, manifest, previews
# ----------------------------------------------------------------------------
def rng(a, b):
    return list(range(a, b + 1))


def build():
    sheets = {}

    def put(key, frames, file, anims=None, names=None):
        fw, fh = frames[0].size
        for f in frames:
            assert f.size == (fw, fh), key
        save(sheet(frames), file)
        e = {"file": file, "fw": fw, "fh": fh}
        if anims:
            e["anims"] = {k: {"frames": v[0], "fps": v[1], "loop": v[2]} for k, v in anims.items()}
        if names:
            e["names"] = names
        sheets[key] = e

    put("door", door_frames(), "sprites/door.png",
        anims={"open": (rng(1, 7), 14, False)}, names={"locked": 0, "unlocked": 1, "open": 7})
    put("checkpoint", checkpoint_frames(), "sprites/checkpoint.png",
        anims={"off": ([0], 1, False), "activate": (rng(1, 5), 12, False), "on": (rng(6, 9), 8, True)})
    put("mplat", mplat_frames(), "sprites/mplat.png", anims={"hover": (rng(0, 3), 10, True)})
    put("spring", spring_frames(), "sprites/spring.png",
        anims={"idle": ([0], 1, False), "bounce": (rng(1, 4), 18, False)})
    put("console", console_frames(), "sprites/console.png",
        anims={"idle": (rng(0, 3), 6, True), "active": (rng(4, 7), 10, True), "done": (rng(8, 9), 4, True)})
    put("fblock", [fblock(k) for k in ("plus", "minus", "neutral", "off")], "sprites/fblock.png",
        names={"plus": 0, "minus": 1, "neutral": 2, "off": 3})
    put("lever", [lever(k) for k in ("off", "mid", "on")], "sprites/lever.png", names={"off": 0, "mid": 1, "on": 2})
    put("tank4", tank_frames(), "sprites/tank4.png", names={"q0": 0, "q1": 1, "q2": 2, "q3": 3, "q4": 4})
    put("liquid_top", liquid_frames(), "sprites/liquid_top.png", anims={"wave": (rng(0, 3), 8, True)})
    put("bridge_emitter", emitter_frames(), "sprites/bridge_emitter.png",
        anims={"idle": (rng(0, 3), 8, True), "off": ([4], 1, False)})
    put("bridge_seg", seg_frames(), "sprites/bridge_seg.png", anims={"flow": (rng(0, 3), 12, True)})
    put("cannon", cannon_frames(), "sprites/cannon.png",
        anims={"idle": (rng(0, 1), 4, True), "charge": (rng(2, 5), 10, True), "fire": (rng(6, 9), 14, False)})
    put("beam", beam_frames(), "sprites/beam.png", anims={"flow": (rng(0, 3), 16, True)})
    put("holo_proj", holo_frames(), "sprites/holo_proj.png", anims={"on": (rng(0, 3), 10, True)})

    rb, rf = reactor_back(), reactor_front()
    assert rb.size == (64, 112) and rf.size == (64, 112)
    # contract checks: the tube is flat ink1 in the back and has nothing opaque in the front
    for y in range(16, 96):
        for x in range(20, 44):
            assert rb.getpixel((x, y)) == INK[1], ("tube not flat", x, y)
            assert rf.getpixel((x, y))[3] < 255, ("opaque pixel in tube overlay", x, y)
    save(rb, "props/reactor_back.png"); save(rf, "props/reactor_front.png")
    images = {"reactor_back": {"file": "props/reactor_back.png"}, "reactor_front": {"file": "props/reactor_front.png"}}

    # contract check: fblock display is flat and at least 22x20
    fb = fblock("plus")
    for y in range(6, 26):
        for x in range(5, 27):
            assert fb.getpixel((x, y)) == INK[1]

    manifest("props_machines", {
        "sheets": sheets,
        "images": images,
        "meta": {
            "fblock_display": {"x": 5, "y": 6, "w": 22, "h": 20},
            "reactor_tube": {"x": 20, "y": 16, "w": 24, "h": 80},
            "tank4_sections": [{"y": a, "h": b - a + 1} for (a, b) in TANK_SECT],
            "bridge": "emitter stands on the ledge, its right edge at the gap; planks start there with their top row on the floor line (emitter frame bottom)",
            "cannon_muzzle": {"x": 32, "y": 2},
        },
    })
    return sheets, images


def main(argv):
    only = set(argv)

    def want(k):
        return not only or k in only

    if not only:
        sheets, images = build()
        print("wrote", len(sheets), "sheets +", len(images), "images -> assets/manifest/props_machines.json")
    if want("door"):
        fr = door_frames(); strip(fr, "pm_door.png", scale=6)
    if want("fblock"):
        fr = [fblock(k) for k in ("plus", "minus", "neutral", "off")]; strip(fr, "pm_fblock.png", scale=8)
    if want("lever"):
        fr = [lever(k) for k in ("off", "mid", "on")]; strip(fr, "pm_lever.png", scale=8)
    if want("spring"):
        strip(spring_frames(), "pm_spring.png", scale=10)
    if want("console"):
        strip(console_frames(), "pm_console.png", scale=6)
    if want("checkpoint"):
        strip(checkpoint_frames(), "pm_checkpoint.png", scale=6)
    if want("mplat"):
        strip(mplat_frames(), "pm_mplat.png", scale=8, cols=2)
    if want("tank4"):
        strip(tank_frames(), "pm_tank4.png", scale=5)
    if want("reactor"):
        rb, rf = reactor_back(), reactor_front()
        demos = [rb]
        liq = liquid_frames()
        for lvl, col in ((0.0, CY[4]), (0.375, CY[4]), (0.75, OR[4]), (1.0, GR[3])):
            d = rb.copy()
            hgt = int(round(80 * lvl))
            if hgt > 0:
                ytop = 96 - hgt
                lay = new(64, 112)
                rect(lay, 20, ytop, 24, hgt, col)
                lt = liq[1]
                for yy in range(6):
                    for xx in range(24):
                        c = lt.getpixel((xx, yy))
                        if c[3]:
                            lay.putpixel((20 + xx, ytop - 4 + yy), (c[0] * col[0] // 255, c[1] * col[1] // 255, c[2] * col[2] // 255, 255))
                d.alpha_composite(lay)
            d.alpha_composite(rf)
            demos.append(d)
        fr_only = new(64, 112, hexc("#7a1228")); fr_only.alpha_composite(rf); demos.append(fr_only)
        strip(demos, "pm_reactor.png", scale=4, bg="#1c0f18")
        strip(liquid_frames(), "pm_liquid_top.png", scale=10, bg="#2a1620", cols=2)
    if want("bridge"):
        em = emitter_frames(); strip(em, "pm_bridge_emitter.png", scale=6)
        sg = seg_frames(); strip(sg, "pm_bridge_seg.png", scale=10)
        # tiling test: emitter on a ledge, 8 planks across the gap, all four flow frames
        demo = new(24 + 16 * 8 + 16, (40 + 16) * 4, hexc("#141a3a"))
        for f in range(4):
            oy = f * 56
            demo.alpha_composite(em[f], (0, oy))
            rect(demo, 0, oy + 40, 24, 16, ST[3]); hline(demo, 0, 23, oy + 40, ST[7]); hline(demo, 0, 23, oy + 41, ST[6])
            for k in range(8):
                demo.alpha_composite(sg[f], (24 + k * 16, oy + 40))
        preview(demo, "pm_bridge_demo.png", scale=5, bg="#141a3a")
    if want("cannon"):
        strip(cannon_frames(), "pm_cannon.png", scale=4, cols=5)
        bm = beam_frames(); strip(bm, "pm_beam.png", scale=8)
        demo = new(64 * 4 + 3, 48 + 64, hexc("#0a1322"))
        cf = cannon_frames()
        for k in range(4):
            demo.alpha_composite(cf[6 + k], (k * 65, 64))
            if k < 3:
                for t in range(4):
                    demo.alpha_composite(bm[k], (k * 65 + 24, t * 16))
        preview(demo, "pm_cannon_demo.png", scale=4, bg="#0a1322")
    if want("holo_proj"):
        strip(holo_frames(), "pm_holo_proj.png", scale=8, cols=2)
    if want("mock"):
        mock_dock(); mock_bridge(); mock_reactor(); mock_boss()
    if want("all"):
        contact_sheet()


if __name__ == "__main__":
    main(sys.argv[1:])
