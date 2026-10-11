"""
props_world.py - world props for Math Blast Arcade (manifest part "props_world").

Sheets (see ASSET_SPEC.md, PART "props"):
  gpad, pod, barrier, sign_display, mine, zap_emitter, zap_arc, steam, spikes,
  bolt, orb, decor
Run:  cd art && python3 props_world.py     (regenerates sheets, manifest, pw_* previews)
"""
import math, os, random
from pix import *

ST = ramp("steel"); CY = ramp("cyan"); NV = ramp("navy"); OR = ramp("orange")
PU = ramp("purple"); GR = ramp("green"); RD = ramp("red"); GD = ramp("gold")
PK = ramp("pink"); INK = ramp("ink"); SK = ramp("skin"); HR = ramp("hair")
WH = C["white"]
SCREEN = C["navy0"]            # flat dark "display" colour the game draws labels on

# 6-tone material ramps (dark -> light) for the decor, all built from the master palette
STL = [ST[1], ST[2], ST[3], ST[4], ST[5], ST[6]]
RUST = [OR[0], OR[1], mix(OR[1], OR[2], .55), OR[2], mix(OR[2], OR[3], .6), OR[4]]
TEAL = [CY[0], CY[1], mix(CY[1], CY[2], .5), CY[2], mix(CY[2], CY[3], .55), CY[3]]
BLUE = [NV[0], NV[1], NV[2], NV[3], NV[4], NV[5]]
OCHRE = [GD[0], mix(GD[0], GD[1], .5), GD[1], mix(GD[1], GD[2], .5), GD[2], GD[3]]


def A_(c, a):
    return (c[0], c[1], c[2], a)


def acc(name):
    """Accent colour set: d(arkest) lo m(id) b(right) h(ot) w(hite-hot)."""
    r = {"cyan": [CY[1], CY[2], CY[3], CY[4], CY[5], CY[6]],
         "pink": [PK[0], PK[1], PK[1], PK[2], PK[3], PK[4]],
         "green": [GR[0], GR[1], GR[2], GR[3], GR[4], GR[5]],
         "red": [RD[0], RD[1], RD[2], RD[3], RD[4], RD[5]],
         "gold": [GD[0], GD[1], GD[2], GD[3], GD[4], GD[5]]}[name]
    return dict(d=r[0], lo=r[1], m=r[2], b=r[3], h=r[4], w=r[5])


def clear(img, x, y):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), T)


def setp(img, x, y, c):
    """Overwrite (no blending)."""
    x = int(round(x)); y = int(round(y))
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), c)


def glowpx(img, x, y, c):
    """Draw only where the canvas is still empty (glows never cover the sprite)."""
    x = int(round(x)); y = int(round(y))
    if 0 <= x < img.width and 0 <= y < img.height and img.getpixel((x, y))[3] == 0:
        img.putpixel((x, y), c)


def stamp(img, rows, x, y, cmap):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in ". ":
                continue
            setp(img, x + i, y + j, cmap[ch])


def contact(frames, name, scale=8, bg="#1b2547", cols=None, gap=2):
    """Preview: frames side by side with a gap so edges can be judged."""
    fw, fh = frames[0].size
    cols = cols or len(frames)
    rows = (len(frames) + cols - 1) // cols
    img = new(cols * (fw + gap) + gap, rows * (fh + gap) + gap)
    for i, f in enumerate(frames):
        img.alpha_composite(f, (gap + (i % cols) * (fw + gap), gap + (i // cols) * (fh + gap)))
    preview(img, name, scale=scale, bg=bg)


# =============================================================================
# gpad  32x12   up: 0-3 (floor pad, cyan arrows rise)   down: 4-7 (ceiling pad, pink arrows fall)
# =============================================================================
def gpad_frame(i, kind):
    img = new(32, 12)
    A = acc("cyan" if kind == "up" else "pink")
    up = kind == "up"
    # ---- pad body (4 rows) --------------------------------------------------
    if up:
        hline(img, 3, 28, 8, ST[6]); hline(img, 2, 29, 9, ST[4])
        hline(img, 1, 30, 10, ST[3]); hline(img, 1, 30, 11, ST[1])
        px(img, 3, 8, ST[7]); px(img, 28, 8, ST[4]); px(img, 29, 9, ST[2]); px(img, 30, 10, ST[2])
        px(img, 2, 9, ST[6]); px(img, 1, 10, ST[5])
        e0, e1 = 8, 9                      # emitter rows (hot row first)
        lamp_y = 10
    else:
        hline(img, 1, 30, 0, ST[2]); hline(img, 1, 30, 1, ST[5])
        hline(img, 2, 29, 2, ST[3]); hline(img, 3, 28, 3, ST[2])
        px(img, 1, 1, ST[6]); px(img, 2, 1, ST[6]); px(img, 30, 1, ST[3]); px(img, 29, 2, ST[2])
        e0, e1 = 3, 2
        lamp_y = 1
    # recessed emitter strip
    hline(img, 4, 27, e0, INK[1]); hline(img, 4, 27, e1, INK[1])
    for x in range(5, 27):
        ph = (x - i * 2) % 8
        setp(img, x, e0, A["w"] if ph < 3 else A["h"])
        setp(img, x, e1, A["b"] if ph < 4 else A["m"])
    # end-cap lamps
    for x in (2, 29):
        setp(img, x, lamp_y, A["h"] if i % 2 == 0 else A["b"])
    img = outline(img)
    # selective outline: the glow eats the ink line over the emitter
    oy = 7 if up else 4
    for x in range(5, 27):
        setp(img, x, oy, A["m"])

    def fy(y):          # field row (0 = far end, 6 = next to the pad) -> image row
        return y if up else 11 - y
    # ---- soft light lifting off the emitter -----------------------------------
    for x in range(5, 27):
        setp(img, x, fy(6), A_(A["b"], 110))
        setp(img, x, fy(5), A_(A["b"], 60))
        if (x + i) % 2 == 0:
            setp(img, x, fy(4), A_(A["b"], 36))
    # ---- flowing chevrons (period 4 rows, 1px per frame) ---------------------
    chev = ["..##..", ".#..#.", "#....#"]
    alpha = [130, 175, 215, 245, 255, 255, 255]
    for ci, cx in enumerate((5, 13, 21)):
        for k in range(0, 4):
            yt = ((-i) % 4) + 4 * k - 4
            for r, row in enumerate(chev):
                y = yt + r
                if not (0 <= y <= 6):
                    continue
                for c, ch in enumerate(row):
                    if ch != "#":
                        continue
                    col = A["w"] if y >= 3 else A["h"] if y >= 1 else A["b"]
                    setp(img, cx + c, fy(y), A_(col, alpha[y]))
    return img


# =============================================================================
# pod  48x24   idle, correct, wrong, done      display: x=12..35, y=4..19 (24x16)
# =============================================================================
POD_ICON = {
    "idle":    [".....", ".###.", ".#.#.", ".###.", "....."],
    "correct": ["....#", "...##", "#.##.", "###..", ".#..."],
    "wrong":   ["#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "done":    ["..#..", ".###.", "#####", ".###.", "..#.."],
}
POD_DISPLAY = (12, 4, 24, 16)


def pod_frame(state):
    A = acc({"idle": "cyan", "correct": "green", "wrong": "red", "done": "gold"}[state])
    img = new(48, 24)
    lit = state in ("correct", "done")
    # ---- engine nacelles ----------------------------------------------------
    for side, x0 in ((0, 1), (1, 38)):
        rect(img, x0, 3, 9, 15, ST[3])
        vline(img, x0, 3, 17, ST[5]); vline(img, x0 + 8, 3, 17, ST[2])
        hline(img, x0, x0 + 8, 3, ST[1])
        hline(img, x0 + 1, x0 + 7, 4, ST[4]); px(img, x0 + 1, 4, ST[6])
        hline(img, x0 + 1, x0 + 7, 5, ST[3])
        # chamfered outer-bottom corner
        for k in range(3):
            for j in range(k + 1):
                clear(img, (x0 + j) if side == 0 else (x0 + 8 - j), 15 + k)
            px(img, (x0 + k + 1) if side == 0 else (x0 + 7 - k), 15 + k, ST[4] if side == 0 else ST[1])
        hline(img, x0 + (4 if side == 0 else 1), x0 + (7 if side == 0 else 4), 17, ST[2])
        # status recess with icon
        rect(img, x0 + 1, 6, 7, 7, INK[1])
        hline(img, x0 + 1, x0 + 7, 13, ST[5])
        vline(img, x0 + 8 if side == 0 else x0, 6, 12, ST[4] if side else ST[2])
        stamp(img, POD_ICON[state], x0 + 2, 7, {"#": A["h"] if lit else A["b"]})
        # vent slit
        hline(img, x0 + 3, x0 + 5, 15, ST[1])
        # nozzle
        nx = x0 + (3 if side == 0 else 1)
        rect(img, nx, 18, 5, 2, ST[2]); hline(img, nx, nx + 4, 18, ST[1]); px(img, nx, 19, ST[4]); px(img, nx + 4, 19, ST[1])
    # ---- screen housing -----------------------------------------------------
    rect(img, 10, 3, 28, 19, ST[3])
    hline(img, 10, 37, 3, A["b"]); hline(img, 10, 37, 20, A["m"])
    vline(img, 10, 3, 20, A["h"]); vline(img, 11, 3, 20, A["b"])
    vline(img, 36, 3, 20, A["b"]); vline(img, 37, 3, 20, A["m"])
    hline(img, 10, 14, 3, A["h"]); px(img, 10, 3, A["w"]); px(img, 11, 3, A["w"]); px(img, 10, 4, A["w"])
    px(img, 37, 20, A["lo"]); px(img, 36, 20, A["lo"])
    hline(img, 10, 37, 21, ST[2]); px(img, 13, 21, ST[4]); px(img, 34, 21, ST[4])
    clear(img, 10, 21); clear(img, 37, 21)
    x, y, w, h = POD_DISPLAY
    rect(img, x, y, w, h, SCREEN)
    # ---- deck (walk surface) ------------------------------------------------
    hline(img, 2, 45, 0, ST[7]); hline(img, 1, 46, 1, ST[6]); hline(img, 1, 46, 2, ST[4])
    px(img, 1, 1, ST[7]); px(img, 46, 1, ST[4]); px(img, 46, 2, ST[2]); px(img, 24, 2, ST[5]); px(img, 23, 2, ST[2])
    for (a, b) in (((4, 9), (38, 43)) if not lit else ((4, 43),)):
        hline(img, a, b, 0, A["w"]); hline(img, a, b, 1, A["h"] if lit else A["b"])
        px(img, a - 1, 1, A["m"]); px(img, b + 1, 1, A["m"])
    img = outline(img)
    # ---- thruster flames (state coloured) -----------------------------------
    for side, x0 in ((0, 1), (1, 38)):
        c = x0 + (5 if side == 0 else 3)
        if state == "wrong":            # engines sputtering
            setp(img, c, 20, A["h"]); setp(img, c, 21, A_(A["b"], 170))
            setp(img, c + (1 if side else -1), 22, A_(A["m"], 150))
            continue
        hline(img, c - 1, c + 1, 20, A["w"])
        hline(img, c - 2, c + 2, 21, A["h"]); setp(img, c, 21, A["w"])
        for xx in range(c - 1, c + 2):
            setp(img, xx, 22, A_(A["b"], 230))
        setp(img, c, 22, A["h"])
        setp(img, c, 23, A_(A["b"], 150))
    return img


# =============================================================================
# barrier 16x16   on: 0-3   (near-white so code can tint; tiles in Y)
# layers: slow ripple (period 8, 2px/frame) + fast streaks (period 16, 4px/frame)
# =============================================================================
BARRIER_STREAKS = [(5, 0, 6, 1), (10, 7, 5, 1), (7, 11, 3, 1), (8, 3, 4, -1), (6, 6, 2, 1), (9, 14, 2, 1)]


def barrier_frame(i):
    img = new(16, 16)
    for y in range(16):
        ya = (y + 2 * i) % 8
        for x in range(16):
            a = 0
            if x in (2, 13):
                a = 255 if ya not in (5, 6) else 200
            elif x in (3, 12):
                a = 140
            elif x in (1, 14):
                a = 70
            elif 4 <= x <= 11:
                a = 34
                if ya == 4 and x % 2 == 0:
                    a = 80
                for (sx, s0, ln, d) in BARRIER_STREAKS:
                    if x != sx:
                        continue
                    k = ((y + 4 * i * d) - s0) % 16
                    if k < ln:
                        a = max(a, 235 - (k if d > 0 else ln - 1 - k) * (150 // ln))
            # bright nodes travelling up the rails
            if ya in (0, 1):
                if x in (1, 14):
                    a = 200
                if x in (3, 12):
                    a = 255
                if x in (4, 11):
                    a = 110
            if ya == 0 and x in (0, 15):
                a = 80
            if a:
                img.putpixel((x, y), (255, 255, 255, a) if a >= 200 else (226, 234, 242, a))
    return img


# =============================================================================
# sign_display 32x32   normal, good, bad     display: x=4..27, y=5..26 (24x22)
# =============================================================================
SIGN_DISPLAY = (4, 5, 24, 22)


def sign_frame(state):
    A = acc({"normal": "cyan", "good": "green", "bad": "red"}[state])
    img = new(32, 32)
    # light-tube bars between the clamps (carry the state colour)
    hline(img, 3, 28, 2, A["m"]); hline(img, 3, 28, 3, A["b"]); hline(img, 3, 28, 4, A["h"])
    hline(img, 3, 28, 27, A["b"]); hline(img, 3, 28, 28, A["m"]); hline(img, 3, 28, 29, A["lo"])
    vline(img, 2, 4, 27, A["b"]); vline(img, 3, 4, 27, A["h"])
    vline(img, 28, 4, 27, A["b"]); vline(img, 29, 4, 27, A["m"])
    hline(img, 8, 12, 4, A["w"]); vline(img, 3, 8, 11, A["w"])
    # steel corner clamps (L shaped, 1px proud of the tubes)
    for (cx, cy, sx, sy) in ((1, 1, 1, 1), (30, 1, -1, 1), (1, 30, 1, -1), (30, 30, -1, -1)):
        lit = (sx == 1) + (sy == 1)                  # 2 = top-left clamp, 0 = bottom-right
        face = [ST[3], ST[4], ST[5]][lit]
        for k in range(7):
            for t in range(3 if True else 2):
                # horizontal arm (3 rows thick on top/bottom, since the tube is 3 rows)
                px(img, cx + sx * k, cy + sy * t, face)
            for t in range(2):
                px(img, cx + sx * t, cy + sy * k, face)
        # bevels
        for k in range(7):
            px(img, cx + sx * k, cy, ST[7] if sy == 1 else ST[1])
            px(img, cx, cy + sy * k, (ST[6] if sx == 1 else ST[1]))
        px(img, cx + sx * 6, cy + sy * 1, ST[2] if sx == 1 else ST[6]) if False else None
        clear(img, cx, cy)
        px(img, cx + sx, cy + sy, ST[7] if lit == 2 else ST[5] if lit == 1 else ST[4])
        # bolt
        px(img, cx + sx * 4, cy + sy * 1, ST[1])
    # top tab with status light, bottom projector lens
    rect(img, 12, 1, 8, 3, ST[4]); hline(img, 12, 19, 1, ST[6]); px(img, 12, 2, ST[5]); px(img, 19, 2, ST[2]); px(img, 19, 3, ST[2])
    hline(img, 14, 17, 2, A["w"]); hline(img, 14, 17, 3, A["b"])
    rect(img, 12, 28, 8, 3, ST[3]); hline(img, 12, 19, 28, ST[5]); hline(img, 12, 19, 30, ST[1])
    hline(img, 14, 17, 29, A["h"]); hline(img, 14, 17, 30, A["b"]); px(img, 14, 29, A["w"])
    x, y, w, h = SIGN_DISPLAY
    rect(img, x, y, w, h, SCREEN)
    return outline(img)


# =============================================================================
# mine 16x16   pulse: 0-3
# =============================================================================
def mine_frame(i):
    img = new(16, 16)
    lvl = [0, 1, 2, 1][i]
    c = 7.5
    # spikes: collar + shaft (tips are coloured after the outline)
    for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        for s in (-1.5, -0.5, 0.5, 1.5):
            px(img, c + dx * 4.5 + (s if dx == 0 else 0), c + dy * 4.5 + (s if dy == 0 else 0), ST[3])
        for t in (5.5, 6.5):
            for s in (-0.5, 0.5):
                px(img, c + dx * t + (s if dx == 0 else 0), c + dy * t + (s if dy == 0 else 0), ST[5] if (dx + dy) < 0 else ST[4])
    for (dx, dy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px(img, c + dx * 3.5, c + dy * 3.5, ST[3])
        px(img, c + dx * 4.5, c + dy * 4.5, ST[5] if dx + dy < 0 else ST[4])
    # shell
    for y in range(16):
        for x in range(16):
            if (x - c) ** 2 + (y - c) ** 2 <= 4.5 * 4.5 + 0.3:
                d = (x - 5.6) ** 2 + (y - 5.4) ** 2
                setp(img, x, y, ST[6] if d < 1.2 else ST[5] if d < 5 else ST[4] if d < 13 else ST[3] if d < 26 else ST[2])
    setp(img, 5, 5, ST[7])
    # core lens
    core = [[RD[1], RD[2], RD[3]], [RD[2], RD[3], RD[4]], [RD[3], RD[4], WH]][lvl]
    rect(img, 5, 5, 6, 6, ST[1])
    for (x, y) in ((5, 5), (10, 5), (5, 10), (10, 10)):
        setp(img, x, y, ST[4] if x + y < 12 else ST[3] if x + y < 16 else ST[2])
    setp(img, 5, 5, ST[6])
    rect(img, 6, 6, 4, 4, core[0])
    rect(img, 7, 7, 2, 2, core[1]); setp(img, 7, 7, core[2])
    if lvl == 2:
        rect(img, 6, 6, 4, 4, core[1]); rect(img, 7, 7, 2, 2, WH)
        for (x, y) in ((6, 6), (9, 6), (6, 9), (9, 9)):
            setp(img, x, y, RD[3])
        for k in range(6, 10):                       # the socket ring catches the flash
            for (x, y) in ((k, 5), (k, 10), (5, k), (10, k)):
                setp(img, x, y, RD[1])
    else:
        for (x, y) in ((6, 6), (9, 6), (6, 9), (9, 9)):
            setp(img, x, y, RD[1] if lvl == 0 else RD[2])
    img = outline(img)
    # hot spike tips
    tip = [RD[2], RD[3], RD[4]][lvl]
    for (x, y) in ((7, 1), (8, 1), (7, 14), (8, 14), (1, 7), (1, 8), (14, 7), (14, 8)):
        setp(img, x, y, tip)
    for (x, y) in ((3, 3), (12, 3), (3, 12), (12, 12)):
        setp(img, x, y, [RD[1], RD[2], RD[3]][lvl])
    return img


# =============================================================================
# zap_emitter 16x16  idle(0) firing(1)  - hangs from the ceiling, fires down
# =============================================================================
ZAP_EMITTER = [
    ".4444444444444. ",
    ".7666666666665. ",
    ".2222222222221. ",
    "...5433333321...",
    "...54rrrrrr21...",
    "...54RRRRRr21...",
    "...5433333321...",
    "....22222211....",
    "....65555432....",
    ".....222221.....",
    ".....655432.....",
    "......2221......",
    "......6542......",
    ".......21.......",
    ".......eE.......",
    ".......fF.......",
]


def zap_emitter_frame(firing):
    cm = {str(k): ST[k] for k in range(8)}
    cm.update({"r": RD[3] if firing else RD[1], "R": PK[4] if firing else RD[2],
               "e": WH if firing else ST[6], "E": WH if firing else ST[4],
               "f": PK[4] if firing else RD[3], "F": PK[3] if firing else RD[2]})
    rows = [r.replace(" ", ".") for r in ZAP_EMITTER]
    rows[0] = ".44444444444444."; rows[1] = ".76666666666665."; rows[2] = ".22222222222221."
    img = outline(ascii_sprite(rows, cm))
    if firing:
        setp(img, 7, 4, WH); setp(img, 8, 4, WH)
        for (x, y, a) in ((6, 15, 255), (9, 15, 255), (5, 15, 170), (10, 15, 170), (6, 14, 200), (9, 14, 200), (5, 13, 120), (10, 13, 120)):
            setp(img, x, y, A_(PK[3] if a > 180 else PK[2], a))
    return img


# =============================================================================
# zap_arc 16x16  arc: 0-3 (tiles in Y: the core enters and leaves at x=7..8)
# =============================================================================
ARC_PATHS = [[7, 7, 8, 10, 10, 10, 7, 5, 5, 5, 6, 9, 9, 9, 8, 7],
             [7, 6, 5, 5, 5, 8, 10, 10, 10, 8, 6, 6, 6, 5, 7, 7],
             [7, 8, 9, 9, 6, 6, 6, 4, 4, 6, 9, 10, 10, 8, 8, 7],
             [7, 7, 5, 5, 5, 7, 10, 10, 10, 9, 7, 7, 5, 5, 6, 7]]     # core x per row


def zap_arc_frame(i):
    xs = ARC_PATHS[i] + [7]
    core = set()
    for y in range(16):
        x, xn = xs[y], xs[y + 1]
        for xx in range(min(x, xn), max(x, xn) + 2):
            core.add((xx, y))
    img = new(16, 16)

    def wrap(p):
        return (p[0], p[1] % 16)
    halo1 = set()
    for (x, y) in core:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = wrap((x + dx, y + dy))
            if p not in core:
                halo1.add(p)
    halo2 = set()
    for (x, y) in halo1:
        for dx, dy in ((1, 0), (-1, 0)):
            p = wrap((x + dx, y + dy))
            if p not in core and p not in halo1:
                halo2.add(p)
    for (x, y) in halo2:
        if (x + y + i) % 2 == 0:
            setp(img, x, y, A_(PK[1], 150))
    for (x, y) in halo1:
        setp(img, x, y, PK[3] if (x * 3 + y + i) % 5 else PK[2])
    for (x, y) in core:
        setp(img, x, y, WH)
    # a thin side fork + loose sparks
    rnd = random.Random(70 + i)
    y = rnd.randint(3, 6)
    side = 1 if xs[y] < 8 else -1
    x = xs[y] + (3 if side > 0 else -2)
    for k in range(rnd.randint(3, 5)):
        if 0 <= x < 16 and img.getpixel((x, y))[3] == 0:
            setp(img, x, y, PK[4] if k < 2 else A_(PK[3], 220))
        y += 1
        x += side * rnd.choice((0, 1, 1))
    for _ in range(2):
        y = rnd.randint(1, 14)
        sx = xs[y] + rnd.choice((-6, -5, 5, 6))
        glowpx(img, sx, y, A_(PK[4], 255))
    return img


# =============================================================================
# steam 16x32  puff: 0-5   (metaball field -> 4 hard tone bands)
# =============================================================================
STEAM_PUFFS = [(0.0, 0.3, 1.0), (1 / 3., 2.1, 0.9), (2 / 3., 4.4, 1.05),
               (1 / 6., 1.2, 0.6), (0.5, 3.3, 0.55), (5 / 6., 5.1, 0.65)]


def steam_frame(i):
    img = new(16, 32)
    blobs = []
    for (ph, seed, size) in STEAM_PUFFS:
        t = (i / 6.0 + ph) % 1.0
        y = 25 - 21.0 * (t ** 0.85)
        x = 7.5 + math.sin(seed + t * 4.5) * 3.4 * (t ** 0.8)
        r = (1.8 + 4.4 * (t ** 0.8)) * size
        wgt = (1.0 - t) ** 0.55 * (0.8 + 0.4 * size)
        blobs.append((x, y, r, wgt))

    def field(x, y):
        d = 0.0
        for (bx, by, r, wgt) in blobs:
            dist = math.hypot(x - bx, y - by)
            if dist < r:
                d += wgt * (1 - (dist / r) ** 2)
        if y >= 21:                         # the jet itself: tight column out of the nozzle
            half = 0.8 + (31 - y) * 0.10
            ax = abs(x - 7.5)
            if ax < half + 0.6:
                d += 1.2 * max(0.0, 1 - ax / (half + 0.6)) * min(1.0, (y - 20) / 3.0)
        return d
    for y in range(32):
        for x in range(16):
            d = field(x, y)
            if d < 0.2:
                continue
            hot = y >= 27
            lit = field(x + 1.3, y + 1.3) - field(x - 1.3, y - 1.3)     # >0: we are on the top-left rim
            if d < 0.38:
                col = A_(RD[3], 170) if hot else A_(ST[5], 120) if lit < 0 else A_(ST[6], 150)
            elif hot:
                col = WH if d > 1.0 else RD[5] if d > 0.6 else RD[4]
            elif lit > 0.16:
                col = WH
            elif lit < -0.22:
                col = A_(ST[5], 235) if d < 0.75 else A_(ST[6], 245)
            else:
                col = A_(ST[7], 245)
            img.putpixel((x, y), col)
    return img


# =============================================================================
# spikes 16x16  shimmer: 0-3 (tiles in X; emitter strip on the bottom rows)
# =============================================================================
def spikes_frame(i):
    img = new(16, 16)
    BIGW = [2, 2, 2, 2, 4, 4, 4, 4, 6, 6, 6]
    SPIKES = [(3.5, BIGW, 0), (11.5, BIGW[2:], 6), (7.5, [2, 2, 4, 4, 4], 3), (15.5, [2, 2, 4, 4], 9)]
    prof = {2: [PK[3], PK[2]], 4: [RD[3], PK[4], PK[3], RD[3]], 6: [RD[3], PK[2], PK[4], PK[3], PK[2], RD[3]]}
    hotp = {2: [WH, PK[4]], 4: [PK[2], WH, WH, PK[2]], 6: [RD[3], PK[3], WH, WH, PK[3], RD[3]]}
    for (cx, widths, phase) in SPIKES:
        top = 14 - len(widths)
        c0 = int(cx + 0.5)
        # dark red rim keeps overlapping blades apart
        for k, w in enumerate(widths):
            for x in range(c0 - w // 2 - 1, c0 + w // 2 + 1):
                setp(img, x % 16, top + k, RD[1])
        for x in (c0 - 1, c0):
            setp(img, x % 16, top - 1, RD[1])
        by = 13 - ((3 * i + phase) % 12)
        for k, w in enumerate(widths):
            y = top + k
            p = hotp[w] if y in (by, by - 1) else prof[w]
            for j in range(w):
                setp(img, (c0 - w // 2 + j) % 16, y, p[j])
        # tip flare when the shimmer reaches the top
        if by <= top + 1:
            setp(img, (c0 - 1) % 16, top - 1, PK[4]); setp(img, (c0 - 1) % 16, top - 2, A_(PK[3], 200))
    # emitter strip
    hline(img, 0, 15, 14, ST[3]); hline(img, 0, 15, 15, ST[1])
    for x in range(16):
        if x % 4 in (1, 2):
            setp(img, x, 14, RD[4] if (x // 4 + i) % 2 == 0 else RD[3])
    setp(img, 0, 14, ST[5]); setp(img, 8, 14, ST[5])
    return img


# =============================================================================
# bolt 24x8  fly: 0-3   (the Phantom's fraction bar: 4 cells, 3 lit; travels right)
# =============================================================================
def bolt_frame(i):
    img = new(24, 8)
    # bar: frame x=6..22, interior x=7..21 (4 cells of 3 + 3 dividers), rows 2..5
    rect(img, 6, 1, 17, 6, PU[1])
    hline(img, 7, 21, 1, PU[3]); hline(img, 7, 21, 6, PU[0]); vline(img, 6, 2, 5, PU[2]); vline(img, 22, 2, 5, PK[3])
    for c in range(4):
        x0 = 7 + c * 4
        if c == 0:                      # the empty share
            rect(img, x0, 2, 3, 4, PU[0]); px(img, x0, 2, PU[1])
            px(img, x0 + 1, 3 + (i % 2), PU[2])
        else:
            hot = ((i + 3 - c) % 4) == 0
            rect(img, x0, 2, 3, 4, PK[3] if hot else PK[2])
            hline(img, x0, x0 + 2, 2, WH if hot else PK[4]); hline(img, x0, x0 + 2, 5, PK[2] if hot else PK[1])
            px(img, x0, 3, PK[4] if hot else PK[3])
    for (x, y) in ((6, 1), (6, 6), (22, 1), (22, 6)):
        clear(img, x, y)
    # leading edge heat
    vline(img, 22, 2, 5, PK[4]); vline(img, 22, 3, 4, WH)
    img = outline(img, A_(PK[2], 135))
    setp(img, 23, 3, A_(PK[4], 230)); setp(img, 23, 4, A_(PK[4], 230))
    # after-image of a share left behind + speed streaks
    for y in range(2, 6):
        for x in range(1, 4):
            setp(img, x, y, A_(PK[2] if y > 2 else PK[3], 105 if i % 2 == 0 else 80))
    setp(img, 4, 2 + i, A_(PK[3], 200)) if i < 4 else None
    lens = [(5, 2), (3, 4), (4, 3), (2, 5)][i]
    for k in range(lens[0]):
        setp(img, 4 - k, 1, A_(PU[4], 200 - k * 36))
    for k in range(lens[1]):
        setp(img, 4 - k, 6, A_(PU[3], 200 - k * 36))
    return img


# =============================================================================
# orb 12x12  pulse: 0-3
# =============================================================================
def orb_frame(i):
    img = new(12, 12)
    r = [3.6, 4.1, 4.6, 4.1][i]
    c = 5.5
    for y in range(12):
        for x in range(12):
            d = math.hypot(x - c, y - c)
            hl = math.hypot(x - (c - 1.2), y - (c - 1.2))
            if r < d <= r + 1.25:
                img.putpixel((x, y), A_(PK[2], 150 if d <= r + 0.7 else 90))
            elif d <= r:
                if d > r - 1.05:
                    col = PU[3] if (x + y) > 12 else PK[2] if (x + y) > 8 else PK[3]
                elif hl < 1.3:
                    col = WH
                elif hl < 2.5:
                    col = PK[4]
                elif (x + y) > 13:
                    col = PK[1]
                else:
                    col = PK[3] if d < r - 1.9 else PK[2]
                img.putpixel((x, y), col)
    # orbiting sparks
    ang = i * math.pi / 2 + 0.6
    setp(img, c + math.cos(ang) * 5.3, c + math.sin(ang) * 5.3, WH)
    setp(img, c - math.cos(ang) * 5.3, c - math.sin(ang) * 5.3, A_(PK[4], 200))
    return img


# =============================================================================
# decor 32x32 (bottom-centre anchored: object stands on row 30, outline on row 31)
# =============================================================================
DECOR_NAMES = ["crate", "crate_stack", "barrel", "barrel_cyan", "cone", "toolbox", "sign_right", "sign_up",
               "sign_warning", "sign_fuel", "terminal_small", "plant_pot", "lamp_post", "pipe_valve",
               "monitor_wall", "fan_vent", "cable_coil", "robot_parts", "bench", "fuel_hose"]

PIE = ["##..",
       "##..",
       "####",
       "####"]          # a disc with one quarter missing: the Kepler fuel logo


def tone_cols(n):
    """Tone index (into a 6-tone ramp) for each column of an upright cylinder lit from the left."""
    out = []
    for k in range(n):
        t = (k + 0.5) / n
        out.append(3 if t < 0.09 else 4 if t < 0.16 else 5 if t < 0.3 else 4 if t < 0.42 else 3 if t < 0.68 else 2 if t < 0.88 else 1)
    return out


def crate_box(img, x0, y0, x1, y1, R):
    """Framed cargo crate front. R = 6 tones dark->light."""
    w = x1 - x0 + 1; h = y1 - y0 + 1
    rect(img, x0, y0, w, h, R[3])
    hline(img, x0, x1, y0, R[5]); hline(img, x0 + 1, x1 - 1, y0 + 1, R[4])
    vline(img, x0, y0, y1, R[5]); vline(img, x0 + 1, y0 + 1, y1 - 1, R[4])
    hline(img, x0, x1, y1, R[1]); hline(img, x0 + 1, x1 - 1, y1 - 1, R[2])
    vline(img, x1, y0, y1, R[1]); vline(img, x1 - 1, y0 + 1, y1 - 1, R[2])
    px(img, x1, y0, R[3]); px(img, x0, y1, R[2])
    # recessed panel: shadow under the top/left frame, light catching the bottom lip
    hline(img, x0 + 2, x1 - 2, y0 + 2, R[1]); vline(img, x0 + 2, y0 + 2, y1 - 2, R[1])
    hline(img, x0 + 3, x1 - 2, y1 - 2, R[4])
    # corner rivets
    for (cx, cy) in ((x0 + 1, y0 + 1), (x1 - 1, y0 + 1), (x0 + 1, y1 - 1), (x1 - 1, y1 - 1)):
        px(img, cx, cy, R[0])


def d_crate():
    img = new(32, 32)
    crate_box(img, 6, 14, 25, 30, STL)
    # lid with a 1px overhang
    hline(img, 5, 26, 12, ST[7]); hline(img, 5, 26, 13, ST[4]); px(img, 5, 12, ST[6]); px(img, 26, 12, ST[5]); px(img, 26, 13, ST[2])
    # latches
    for lx in (10, 20):
        rect(img, lx, 13, 2, 2, GD[3]); px(img, lx, 13, GD[4]); hline(img, lx, lx + 1, 15, ST[1])
    # painted band with a stencilled fraction bar (3 of 4 full)
    rect(img, 9, 19, 14, 6, GD[2]); hline(img, 9, 22, 19, GD[3]); hline(img, 9, 22, 24, GD[1])
    crate_fracbar(img, 10, 20, INK[2])
    # chipped paint
    px(img, 22, 19, ST[3]); px(img, 22, 20, ST[3]); px(img, 9, 24, ST[3]); px(img, 15, 24, ST[3]); px(img, 16, 24, ST[3])
    # dent + scratch, status light
    px(img, 19, 27, ST[2]); px(img, 20, 27, ST[2]); px(img, 20, 26, ST[5])
    px(img, 11, 17, ST[5]); px(img, 12, 17, ST[5]); px(img, 13, 17, ST[2])
    px(img, 23, 17, GR[3])
    return outline(img)


def d_crate_stack():
    img = new(32, 32)
    # bottom: wide teal container
    crate_box(img, 4, 17, 27, 30, TEAL)
    # stencil: two "this way up" arrows + shipping label
    for ax in (7, 13):
        stamp(img, ["..#..", ".###.", "#####", "..#..", "..#.."], ax, 21, {"#": TEAL[5]})
    rect(img, 20, 21, 6, 5, ST[7]); hline(img, 20, 25, 25, ST[5])
    hline(img, 21, 24, 22, ST[3]); hline(img, 21, 22, 24, ST[3]); px(img, 24, 24, RD[3])
    # top: smaller rust crate with a cargo strap
    crate_box(img, 6, 5, 19, 16, RUST)
    vline(img, 10, 5, 16, ST[4]); vline(img, 11, 5, 16, ST[2]); px(img, 10, 5, ST[6])
    rect(img, 10, 9, 2, 2, ST[7]); px(img, 11, 10, ST[5])
    rect(img, 14, 9, 3, 4, GD[5]); px(img, 15, 10, RUST[2]); px(img, 15, 11, RUST[2])
    px(img, 8, 13, RUST[1]); px(img, 8, 12, RUST[5])
    # a power cell someone left on the big crate
    rect(img, 22, 11, 4, 6, ST[4]); vline(img, 22, 11, 16, ST[6]); vline(img, 25, 11, 16, ST[2])
    hline(img, 22, 25, 10, GD[3]); px(img, 22, 10, GD[4]); hline(img, 23, 24, 9, ST[5])
    vline(img, 23, 13, 15, CY[4]); px(img, 23, 13, CY[6]); vline(img, 24, 13, 15, CY[3])
    return outline(img)


def d_barrel(cyan=False):
    img = new(32, 32)
    R = STL if cyan else RUST
    x0, x1 = 9, 22
    tc = tone_cols(14)
    for k in range(14):
        vline(img, x0 + k, 13, 30, R[tc[k]])
    clear(img, x0, 30); clear(img, x1, 30)
    for k in range(1, 13):
        px(img, x0 + k, 30, R[max(0, tc[k] - 2)])
    # lid seen slightly from above
    hline(img, x0 + 2, x1 - 2, 10, R[4]); hline(img, x0 + 1, x1 - 1, 11, R[3]); px(img, x0, 11, R[4]); px(img, x1, 11, R[2])
    hline(img, x0, x1, 12, R[5]); hline(img, x0 + 9, x1, 12, R[3]); px(img, x0, 12, R[4])
    hline(img, x0, x1, 13, R[1]); px(img, x0, 13, R[2])
    hline(img, 12, 13, 11, R[0])                                # bung
    if not cyan:
        for ry in (17, 25):                                     # rolled ribs
            for k in range(14):
                px(img, x0 + k, ry, R[min(5, tc[k] + 1)]); px(img, x0 + k, ry + 1, R[max(0, tc[k] - 2)])
        stamp(img, ["..#..", "..#..", ".###.", "#####", "#####", ".###."], 13, 19, {"#": GD[5]})   # stencilled fuel drop
        px(img, 16, 23, GD[4]); px(img, 17, 22, GD[4]); px(img, 15, 24, GD[4])
        px(img, 19, 15, R[1]); px(img, 20, 15, R[1]); px(img, 20, 14, R[4])                          # dent
        px(img, 11, 27, R[1]); px(img, 11, 28, R[1]); px(img, 11, 29, R[2])                          # drip stain
    else:
        for ry in (14, 28):
            for k in range(14):
                px(img, x0 + k, ry, R[min(5, tc[k] + 1)])
            for k in range(14):
                px(img, x0 + k, ry + 1, R[max(0, tc[k] - 1)])
        # sight glass with glowing fuel: 2 of 4 marks full
        rect(img, 12, 15, 8, 13, ST[1])
        rect(img, 13, 16, 6, 11, SCREEN)
        rect(img, 13, 21, 6, 6, CY[4]); vline(img, 13, 21, 26, CY[5]); vline(img, 18, 21, 26, CY[3])
        hline(img, 13, 18, 21, CY[6]); px(img, 16, 23, CY[6]); px(img, 15, 25, CY[5]); px(img, 14, 24, CY[6])
        px(img, 14, 17, NV[2]); px(img, 14, 18, NV[2]); px(img, 15, 17, NV[1])
        for ty in (17, 20, 23, 26):
            px(img, 20, ty, ST[6]); px(img, 21, ty, ST[2])
        hline(img, 15, 16, 10, CY[5]); hline(img, 14, 17, 11, CY[3]); px(img, 15, 11, CY[6])
        px(img, 10, 18, GD[3]); px(img, 10, 19, GD[2]); px(img, 10, 21, GD[3]); px(img, 10, 22, GD[2])
    return outline(img)


def d_cone():
    img = new(32, 32)
    widths = {15: 2, 16: 2, 17: 2, 18: 4, 19: 4, 20: 4, 21: 6, 22: 6, 23: 6, 24: 6, 25: 8, 26: 8, 27: 8, 28: 8}
    for y, w in widths.items():
        x0 = 16 - w // 2
        stripe = y in (20, 21, 25, 26)
        for k in range(w):
            t = (k + 0.5) / w
            if stripe:
                col = WH if t < 0.3 else ST[7] if t < 0.65 else ST[5]
            else:
                col = OR[4] if t < 0.3 else OR[3] if t < 0.65 else OR[2]
            px(img, x0 + k, y, col)
    px(img, 15, 15, OR[5]); px(img, 14, 19, OR[5]); px(img, 13, 22, OR[5]); px(img, 12, 27, OR[5])
    # base flange
    hline(img, 10, 21, 29, OR[3]); hline(img, 10, 13, 29, OR[4]); hline(img, 19, 21, 29, OR[2])
    hline(img, 9, 22, 30, OR[2]); hline(img, 18, 22, 30, OR[1]); px(img, 9, 30, OR[3])
    # scuffs
    px(img, 17, 23, OR[1]); px(img, 18, 27, OR[1]); px(img, 14, 26, ST[6])
    return outline(img)


def d_toolbox():
    img = new(32, 32)
    # box
    rect(img, 5, 22, 18, 9, BLUE[3])
    hline(img, 5, 22, 22, BLUE[5]); hline(img, 5, 22, 23, BLUE[4]); vline(img, 5, 22, 30, BLUE[4])
    hline(img, 5, 22, 24, BLUE[1])                                    # lid seam
    hline(img, 6, 22, 30, BLUE[1]); vline(img, 22, 23, 30, BLUE[2]); hline(img, 6, 21, 29, BLUE[2])
    # latches + nameplate
    for lx in (8, 18):
        rect(img, lx, 23, 2, 3, GD[3]); px(img, lx, 23, GD[5]); hline(img, lx, lx + 1, 25, GD[1])
    rect(img, 12, 26, 4, 2, ST[6]); hline(img, 12, 15, 27, ST[4])
    # handle
    hline(img, 10, 17, 18, ST[6]); hline(img, 10, 17, 19, ST[3]); vline(img, 10, 19, 21, ST[5]); vline(img, 17, 19, 21, ST[3])
    px(img, 10, 18, ST[7])
    # wrench leaning on the side
    for k in range(10):
        px(img, 24 + (k + 2) // 4, 30 - k, ST[5]); px(img, 25 + (k + 2) // 4, 30 - k, ST[3])
    stamp(img, ["#..#", "#..#", "####", ".##."], 25, 17, {"#": ST[6]})
    px(img, 28, 19, ST[4]); px(img, 27, 20, ST[4]); px(img, 25, 17, ST[7])
    return outline(img)


def sign_post(img, top=17, foot=True):
    vline(img, 15, top, 29, ST[5]); vline(img, 16, top, 29, ST[3])
    px(img, 15, top, ST[2]); px(img, 16, top, ST[1])                       # shadow under the plate
    px(img, 15, 23, ST[6]); px(img, 16, 23, ST[4]); px(img, 15, 24, ST[3]); px(img, 16, 24, ST[2])   # joint
    hline(img, 13, 18, 29, ST[5]); hline(img, 12, 19, 30, ST[3]); px(img, 12, 30, ST[4]); px(img, 19, 30, ST[2]); px(img, 18, 29, ST[3])


def sign_plate(img, x0, y0, x1, y1):
    rect(img, x0, y0, x1 - x0 + 1, y1 - y0 + 1, ST[4])
    hline(img, x0, x1, y0, ST[6]); vline(img, x0, y0, y1, ST[6]); hline(img, x0, x1, y1, ST[2]); vline(img, x1, y0, y1, ST[2])
    px(img, x0, y0, ST[7]); px(img, x1, y0, ST[4]); px(img, x0, y1, ST[4])
    rect(img, x0 + 1, y0 + 1, x1 - x0 - 1, y1 - y0 - 1, NV[0])
    hline(img, x0 + 1, x1 - 1, y0 + 1, INK[1])
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        pass


def d_sign_right():
    img = new(32, 32)
    sign_post(img)
    sign_plate(img, 6, 3, 25, 16)
    # chunky arrow
    rect(img, 9, 8, 8, 4, CY[4]); hline(img, 9, 16, 8, CY[5]); hline(img, 9, 16, 11, CY[3])
    for k in range(5):
        vline(img, 17 + k, 5 + k, 14 - k, CY[4])
        px(img, 17 + k, 5 + k, CY[6] if k < 4 else CY[5]); px(img, 17 + k, 14 - k, CY[3])
    px(img, 9, 8, CY[6])
    # tally
    px(img, 8, 14, CY[2]); px(img, 10, 14, CY[2]); px(img, 11, 14, CY[2])
    return outline(img)


def d_sign_up():
    img = new(32, 32)
    sign_post(img)
    sign_plate(img, 8, 2, 23, 16)
    rect(img, 14, 9, 4, 6, CY[4]); vline(img, 14, 9, 14, CY[5]); vline(img, 17, 9, 14, CY[3])
    for k in range(5):
        hline(img, 11 + k, 20 - k, 8 - k, CY[4])
        px(img, 11 + k, 8 - k, CY[6]); px(img, 20 - k, 8 - k, CY[3])
    hline(img, 11, 13, 8, CY[3]); hline(img, 18, 20, 8, CY[3])
    hline(img, 14, 17, 14, CY[3])
    return outline(img)


def d_sign_warning():
    img = new(32, 32)
    sign_post(img)
    hws = [1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 8, 8, 9, 10, 10]
    for k, hw in enumerate(hws):
        y = 2 + k
        x0 = 16 - hw; x1 = 15 + hw
        hline(img, x0, x1, y, GD[3])
        px(img, x0, y, GD[4]); px(img, x1, y, GD[2])
        if hw > 2:
            px(img, x0 + 1, y, GD[4])
    hline(img, 6, 25, 16, GD[1]); hline(img, 7, 24, 15, GD[2]); px(img, 6, 15, GD[3])
    clear(img, 6, 16); clear(img, 25, 16)
    px(img, 15, 2, GD[5]); px(img, 15, 3, GD[5]); px(img, 14, 3, GD[5])
    # !
    rect(img, 15, 6, 2, 5, INK[1]); rect(img, 15, 12, 2, 2, INK[1])
    return outline(img)


def d_sign_fuel():
    img = new(32, 32)
    sign_post(img, top=18)
    x0, y0, x1, y1 = 8, 1, 23, 17
    rect(img, x0, y0, 16, 17, GD[3])
    hline(img, x0, x1, y0, GD[4]); vline(img, x0, y0, y1, GD[4]); hline(img, x0, x1, y1, GD[1]); vline(img, x1, y0, y1, GD[2])
    rect(img, x0 + 2, y0 + 2, 12, 13, NV[0]); hline(img, x0 + 2, x1 - 2, y0 + 2, INK[1])
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        clear(img, cx, cy)
    drop = ["...##...",
            "...##...",
            "..####..",
            "..####..",
            ".######.",
            "########",
            "########",
            "########",
            ".######.",
            "..####.."]
    stamp(img, drop, 12, 4, {"#": CY[4]})
    # drop shading
    for (x, y) in ((14, 7), (13, 8), (13, 9), (13, 10), (14, 6)):
        px(img, x, y, CY[6])
    for (x, y) in ((19, 9), (19, 10), (19, 11), (18, 12), (17, 13), (16, 13), (15, 13), (18, 11)):
        px(img, x, y, CY[3])
    px(img, 14, 9, CY[5]); px(img, 14, 10, CY[5])
    return outline(img)


def d_terminal_small():
    img = new(32, 32)
    # pedestal
    rect(img, 12, 21, 8, 10, ST[3]); vline(img, 12, 21, 30, ST[5]); vline(img, 19, 21, 30, ST[2])
    hline(img, 12, 19, 21, ST[1])
    hline(img, 14, 17, 24, ST[1]); hline(img, 14, 17, 26, ST[1]); hline(img, 14, 17, 25, ST[4])
    px(img, 14, 28, CY[4]); px(img, 15, 28, CY[3])
    hline(img, 10, 21, 30, ST[3]); hline(img, 11, 20, 29, ST[4]); px(img, 10, 30, ST[5]); px(img, 21, 30, ST[1]); px(img, 11, 29, ST[6])
    # head
    rect(img, 8, 7, 16, 14, ST[4])
    hline(img, 9, 22, 7, ST[7]); hline(img, 8, 23, 8, ST[6]); vline(img, 8, 8, 20, ST[6]); vline(img, 23, 8, 20, ST[2])
    hline(img, 8, 23, 20, ST[2]); hline(img, 9, 22, 19, ST[3])
    clear(img, 8, 7); clear(img, 23, 7)
    # screen
    rect(img, 10, 10, 12, 7, CY[0]); hline(img, 10, 21, 9, ST[1]); vline(img, 9, 9, 17, ST[1]); hline(img, 10, 21, 17, ST[5])
    # bars on screen + a tiny fraction bar
    for k, hgt in enumerate((2, 4, 3)):
        rect(img, 11 + k * 2, 16 - hgt, 1, hgt, CY[4])
    px(img, 11, 14, CY[5]); px(img, 13, 12, CY[6]); px(img, 15, 13, CY[5])
    hline(img, 17, 20, 11, CY[3]); hline(img, 17, 18, 13, GD[3]); hline(img, 19, 20, 13, CY[2]); hline(img, 17, 20, 15, CY[2])
    # keys
    px(img, 10, 18, GD[3]); px(img, 12, 18, ST[7]); px(img, 14, 18, ST[7]); px(img, 16, 18, ST[7]); px(img, 21, 18, GR[3])
    # antenna
    vline(img, 21, 3, 6, ST[4]); px(img, 21, 2, RD[3])
    return outline(img)


def leaf(img, p0, p1, bend, w, cols):
    """Tapered curved leaf on its own layer, lit from above, composited onto img."""
    lay = new(img.width, img.height)
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    cx_, cy_ = (x0 + x1) / 2 + nx * bend, (y0 + y1) / 2 + ny * bend
    n = int(L * 3)
    for k in range(n + 1):
        t = k / float(n)
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx_ + t * t * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy_ + t * t * y1
        r = w * (math.sin(math.pi * min(1.0, 0.12 + t * 0.9)) ** 0.7)
        disc(lay, x, y, max(0.35, r), cols[1])
    src = lay.copy()
    for y in range(lay.height):
        for x in range(lay.width):
            if src.getpixel((x, y))[3] == 0:
                continue
            up = get(src, x, y - 1)[3] == 0
            dn = get(src, x, y + 1)[3] == 0
            if up and not dn:
                lay.putpixel((x, y), cols[2])
            elif dn and not up:
                lay.putpixel((x, y), cols[0])
    # dark separation only where this leaf overlaps what is already drawn
    for y in range(lay.height):
        for x in range(lay.width):
            if src.getpixel((x, y))[3] == 0 and img.getpixel((x, y))[3] > 0:
                if any(get(src, x + ddx, y + ddy)[3] > 0 for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    img.putpixel((x, y), GR[0])
    img.alpha_composite(lay)


def d_plant_pot():
    img = new(32, 32)
    back = (GR[0], GR[1], GR[2])
    front = (GR[1], GR[2], GR[3])
    lite = (GR[2], GR[3], GR[4])
    leaf(img, (15, 22), (6, 9), -3.0, 1.9, back)
    leaf(img, (16, 22), (26, 8), 3.0, 1.9, back)
    leaf(img, (15.5, 22), (14, 3), 1.5, 2.0, front)
    leaf(img, (16, 22), (21, 5), 2.0, 1.6, front)
    leaf(img, (15, 22), (5, 18), -3.5, 1.7, front)
    leaf(img, (16, 22), (27, 17), 3.5, 1.7, lite)
    leaf(img, (15, 22), (9, 6), -2.0, 1.5, lite)
    # pot
    for y in range(22, 31):
        ins = 0 if y < 27 else 1 if y < 30 else 2
        x0 = 11 + ins; x1 = 20 - ins
        for x in range(x0, x1 + 1):
            t = (x - x0 + 0.5) / (x1 - x0 + 1)
            px(img, x, y, SK[3] if t < 0.25 else SK[2] if t < 0.6 else SK[1])
    hline(img, 10, 21, 21, SK[4]); hline(img, 10, 21, 22, SK[2]); px(img, 10, 21, SK[5]); px(img, 11, 21, SK[5])
    hline(img, 17, 21, 21, SK[3]); hline(img, 18, 21, 22, SK[1]); px(img, 21, 22, SK[0])
    hline(img, 11, 20, 23, SK[0])
    hline(img, 12, 19, 26, SK[1]); px(img, 12, 26, SK[2])
    px(img, 13, 25, SK[4]); px(img, 13, 24, SK[4])
    return outline(img)


def d_lamp_post():
    img = new(32, 32)
    # foot
    hline(img, 13, 18, 28, ST[5]); hline(img, 12, 19, 29, ST[4]); hline(img, 12, 19, 30, ST[2]); px(img, 12, 29, ST[6]); px(img, 19, 29, ST[2])
    px(img, 13, 28, ST[6]); px(img, 18, 28, ST[3])
    # pole
    vline(img, 15, 10, 27, ST[5]); vline(img, 16, 10, 27, ST[3])
    for jy in (13, 23):
        hline(img, 14, 17, jy, ST[5]); px(img, 14, jy, ST[6]); px(img, 17, jy, ST[2]); hline(img, 15, 16, jy + 1, ST[2])
    # control box with a tiny green light
    rect(img, 13, 17, 5, 4, ST[4]); hline(img, 13, 17, 17, ST[6]); vline(img, 17, 18, 20, ST[2]); px(img, 14, 19, GR[3]); px(img, 16, 19, ST[1])
    # lantern: finial, hood, glowing glass
    hline(img, 15, 16, 0, ST[5])
    hline(img, 12, 19, 1, ST[6]); px(img, 12, 1, ST[7]); px(img, 19, 1, ST[4])
    hline(img, 10, 21, 2, ST[5]); px(img, 10, 2, ST[7]); px(img, 11, 2, ST[6]); hline(img, 18, 21, 2, ST[3])
    hline(img, 10, 21, 3, ST[2])
    rect(img, 12, 4, 8, 4, CY[5]); hline(img, 13, 18, 8, CY[4])
    rect(img, 13, 4, 4, 3, CY[6]); px(img, 13, 5, WH); px(img, 14, 5, WH); px(img, 13, 4, WH); px(img, 14, 4, WH)
    vline(img, 19, 4, 7, CY[4]); px(img, 18, 7, CY[4])
    hline(img, 14, 17, 9, ST[4]); px(img, 14, 9, ST[6]); px(img, 17, 9, ST[2])
    img = outline(img)
    # soft halo (FX: alpha allowed)
    for y in range(0, 15):
        for x in range(4, 28):
            d = math.hypot(x - 15.5, (y - 6) * 1.15)
            if d < 7.6:
                glowpx(img, x, y, A_(CY[4], 84 if d < 5.2 else 40))
    return img


def d_pipe_valve():
    img = new(32, 32)
    vt = [ST[4], ST[6], ST[5], ST[3], ST[2], ST[1]]
    # vertical riser x=7..12, horizontal run y=12..17
    for k in range(6):
        vline(img, 7 + k, 14, 30, vt[k])
        hline(img, 9, 24, 12 + k, vt[k])
    # elbow corner
    for (x, y, c) in ((7, 12, None), (8, 12, None), (7, 13, None), (8, 13, ST[4]), (9, 12, ST[4]), (7, 14, ST[4]),
                      (8, 14, ST[6]), (9, 13, ST[6]), (9, 14, ST[5]), (10, 14, ST[5]), (10, 13, ST[6])):
        if c is None:
            clear(img, x, y)
        else:
            setp(img, x, y, c)
    for d in range(3):
        setp(img, 12 - d, 18 + d - 3 + 3, vt[5 - d]) if False else None
    # floor flange
    rect(img, 5, 28, 10, 3, ST[3]); hline(img, 5, 14, 28, ST[5]); hline(img, 5, 14, 30, ST[1]); px(img, 5, 28, ST[6])
    px(img, 6, 29, ST[6]); px(img, 13, 29, ST[6]); px(img, 9, 29, ST[1])
    # joint collar on the riser
    hline(img, 6, 13, 21, ST[5]); hline(img, 6, 13, 22, ST[2]); px(img, 6, 21, ST[6]); px(img, 13, 21, ST[3])
    # end cap
    rect(img, 23, 10, 3, 10, ST[4]); vline(img, 23, 10, 19, ST[6]); vline(img, 25, 10, 19, ST[2]); hline(img, 23, 25, 10, ST[6]); hline(img, 23, 25, 19, ST[1])
    px(img, 24, 12, ST[1]); px(img, 24, 17, ST[1])
    # hand wheel (faces the viewer)
    cxw, cyw = 16.5, 14.5
    for y in range(8, 22):
        for x in range(10, 24):
            d = math.hypot(x - cxw, y - cyw)
            if 3.3 < d <= 4.9:
                col = RD[4] if (x - cxw) + (y - cyw) < -2.5 else RD[2] if (x - cxw) + (y - cyw) > 3 else RD[3]
                setp(img, x, y, col)
    for k in range(-3, 4):
        setp(img, 16 + (k > 0), 14 + k + (k > 0), RD[2]) if False else None
    vline(img, 16, 11, 18, RD[2]); vline(img, 17, 11, 18, RD[3]); hline(img, 13, 20, 14, RD[3]); hline(img, 13, 20, 15, RD[2])
    rect(img, 16, 14, 2, 2, ST[6]); px(img, 17, 15, ST[3])
    # pressure gauge
    vline(img, 21, 9, 11, ST[4])
    disc(img, 21, 6, 2.5, ST[5]); disc(img, 21, 6, 1.5, WH); px(img, 21, 6, RD[3]); px(img, 22, 5, RD[3]); px(img, 20, 7, ST[6]); px(img, 19, 5, ST[7])
    return outline(img)


def d_monitor_wall():
    img = new(32, 32)
    # wall bracket + cable
    rect(img, 14, 2, 4, 3, ST[3]); hline(img, 14, 17, 2, ST[5]); px(img, 15, 3, ST[1])
    for (x, y) in ((22, 22), (22, 23), (22, 24), (23, 25), (23, 26), (24, 27), (25, 27)):
        px(img, x, y, ST[2])
    px(img, 26, 26, ST[2])
    # casing
    rect(img, 4, 5, 24, 17, ST[2]); hline(img, 4, 27, 5, ST[5]); vline(img, 4, 5, 21, ST[4]); hline(img, 4, 27, 21, ST[1]); vline(img, 27, 6, 21, ST[1])
    px(img, 4, 5, ST[6]); clear(img, 4, 21); clear(img, 27, 21); clear(img, 27, 5); clear(img, 4, 5)
    px(img, 5, 5, ST[6]); px(img, 4, 6, ST[5])
    # screen
    rect(img, 6, 7, 20, 12, CY[0]); hline(img, 6, 25, 7, INK[1])
    # pie chart with the missing quarter
    for y in range(8, 18):
        for x in range(7, 17):
            d = math.hypot(x - 11.5, y - 13)
            if d <= 4.3:
                if x >= 12 and y < 13:
                    if d > 3.2 and (x + y) % 2 == 0:
                        px(img, x, y, GD[3])
                    continue
                px(img, x, y, CY[4] if d < 3.3 else CY[3])
    px(img, 9, 10, CY[6]); px(img, 10, 10, CY[5]); px(img, 9, 11, CY[5])
    # bars
    hline(img, 18, 24, 9, CY[4]); hline(img, 18, 22, 11, CY[3]); hline(img, 18, 23, 13, CY[4]); hline(img, 18, 20, 15, PK[2]); hline(img, 21, 24, 15, CY[1])
    px(img, 18, 17, CY[2]); px(img, 20, 17, CY[2]); px(img, 21, 17, CY[2])
    # glare
    px(img, 24, 8, CY[2]); px(img, 25, 9, CY[2])
    # chin
    px(img, 24, 20, GR[3]); hline(img, 7, 10, 20, ST[4])
    return outline(img)


def d_fan_vent():
    img = new(32, 32)
    x0, y0 = 6, 3
    rect(img, x0, y0, 20, 20, ST[3])
    hline(img, x0, x0 + 19, y0, ST[6]); vline(img, x0, y0, y0 + 19, ST[5]); hline(img, x0, x0 + 19, y0 + 19, ST[1]); vline(img, x0 + 19, y0, y0 + 19, ST[1])
    hline(img, x0 + 1, x0 + 18, y0 + 1, ST[4]); vline(img, x0 + 1, y0 + 1, y0 + 18, ST[4])
    px(img, x0, y0, ST[7])
    cx, cy = 15.5, 12.5
    for y in range(y0 + 1, y0 + 19):
        for x in range(x0 + 1, x0 + 19):
            d = math.hypot(x - cx, y - cy)
            if d <= 7.7:
                col = INK[1]
                ang = math.atan2(y - cy, x - cx)
                sw = (ang + d * 0.16 + 0.3) % (2 * math.pi / 3)
                if 1.6 < d < 6.4 and sw < 1.15:
                    col = ST[4] if sw < 0.3 else ST[3] if sw < 0.75 else ST[2]
                if d >= 6.9:
                    col = ST[1] if (x - cx) + (y - cy) < 0 else ST[5]
                setp(img, x, y, col)
    # guard: one ring + cross bars, hub cap
    for y in range(y0 + 1, y0 + 19):
        for x in range(x0 + 1, x0 + 19):
            d = math.hypot(x - cx, y - cy)
            if 3.6 < d <= 4.5:
                setp(img, x, y, ST[6] if (x - cx) + (y - cy) < 0 else ST[4])
    for k in range(-6, 7):
        if abs(k) > 1:
            setp(img, 15 if k < 0 else 16, int(cy + k + (0.5 if k < 0 else 0.5)), ST[5] if k < 0 else ST[4])
            setp(img, int(cx + k + 0.5), 12 if k < 0 else 13, ST[5] if k < 0 else ST[4])
    disc(img, cx, cy, 1.5, ST[6]); px(img, 15, 12, ST[7]); px(img, 16, 13, ST[3])
    # corner bolts
    for (bx, by) in ((x0 + 2, y0 + 2), (x0 + 17, y0 + 2), (x0 + 2, y0 + 17), (x0 + 17, y0 + 17)):
        px(img, bx, by, ST[6])
    # ribbon tied to the guard, fluttering in the draught
    for k, (x, y) in enumerate(((21, 13), (22, 12), (23, 12), (24, 13), (25, 14), (26, 14), (27, 13), (28, 12), (29, 12))):
        setp(img, x, y, GD[4] if k % 4 < 2 else GD[3])
        setp(img, x, y + 1, GD[2] if k % 4 < 2 else GD[1])
    img = outline(img)
    # grime streaks on the wall below
    for (x, ln) in ((10, 4), (11, 2), (19, 5), (20, 3)):
        for k in range(ln):
            glowpx(img, x, 24 + k, A_(INK[0], 120 - k * 20))
    return img


def d_cable_coil():
    img = new(32, 32)
    cx = 13.5
    R = OCHRE
    # three stacked loops, bottom first
    for k, cy in enumerate((27.0, 25.0, 23.0)):
        for y in range(18, 31):
            for x in range(2, 26):
                e = ((x - cx) / 9.0) ** 2 + ((y - cy) / 3.4) ** 2
                if e <= 1.0:
                    if e > 0.72 and y > cy:
                        col = R[0] if x > cx + 5 else R[1]      # underside of the loop
                    elif y < cy - 1 and e > 0.45:
                        col = R[4] if x < cx + 1 else R[3]
                    else:
                        col = R[3] if x < cx - 3 else R[2]
                    setp(img, x, y, col)
    # hole in the top loop
    for y in range(20, 26):
        for x in range(6, 22):
            e = ((x - cx) / 5.0) ** 2 + ((y - 22.8) / 1.6) ** 2
            if e <= 1.0:
                setp(img, x, y, INK[1] if y > 22 else R[0])
    # winding line on the top surface + a catch light
    for x in range(6, 22):
        e = ((x - cx) / 7.2) ** 2
        if e < 1:
            px(img, x, 23.0 + 2.6 * math.sqrt(1 - e), R[1])
    hline(img, 8, 12, 20, R[5])
    # cable ties
    for tx in (7, 20):
        vline(img, tx, 24, 29, CY[3]); px(img, tx, 24, CY[5]); px(img, tx, 29, CY[2])
    # loose end and plug
    hline(img, 21, 25, 30, R[2]); px(img, 22, 29, R[3]); px(img, 23, 30, R[4])
    rect(img, 26, 28, 3, 3, ST[5]); hline(img, 26, 28, 28, ST[7]); hline(img, 26, 28, 30, ST[3])
    px(img, 29, 28, ST[7]); px(img, 29, 30, ST[6])
    return outline(img)


def d_robot_parts():
    img = new(32, 32)
    # arm reaching up from behind, claw open
    capsule(img, 16, 27, 21, 19, 1.0, ST[3])
    for k in range(7):
        px(img, 16 + k * 5 / 8.0 - 0.6, 26 - k, ST[5])
    disc(img, 21.5, 18.5, 1.6, ST[5]); px(img, 21, 18, ST[7]); px(img, 22, 19, ST[2])
    for (x, y, c) in ((20, 16, ST[5]), (19, 15, ST[5]), (19, 14, ST[6]), (20, 13, ST[6]),
                      (23, 17, ST[4]), (24, 16, ST[4]), (25, 15, ST[5]), (25, 14, ST[5])):
        px(img, x, y, c)
    # rusty gear on the floor
    gx, gy = 22.5, 26.5
    for y in range(21, 31):
        for x in range(17, 29):
            d = math.hypot(x - gx, y - gy)
            ang = math.atan2(y - gy, x - gx)
            tooth = math.cos(ang * 6 + 0.5) > 0.15
            if d <= 3.3 or (d <= 4.6 and tooth):
                s = (x - gx) + (y - gy)
                setp(img, x, y, RUST[5] if s < -3 else RUST[2] if s > 2.5 else RUST[4])
    disc(img, gx, gy, 1.3, INK[1]); px(img, 22, 25, RUST[1])
    # dome head
    hx, hy = 10.5, 27.0
    for y in range(20, 28):
        for x in range(4, 18):
            d = math.hypot(x - hx, y - hy)
            if d <= 6.3:
                dl = math.hypot(x - 8, y - 22.5)
                setp(img, x, y, ST[6] if dl < 2 else ST[5] if dl < 4.5 else ST[4] if dl < 7.5 else ST[3])
    hline(img, 5, 16, 27, ST[2]); hline(img, 5, 16, 28, ST[3]); px(img, 5, 28, ST[5]); px(img, 16, 28, ST[1])
    px(img, 7, 28, GD[3]); px(img, 9, 28, ST[1]); px(img, 11, 28, ST[1])
    hline(img, 7, 14, 29, ST[2]); hline(img, 7, 14, 30, ST[1]); px(img, 7, 29, ST[4])
    # visor with a switched-off X eye
    rect(img, 9, 23, 6, 3, INK[1]); px(img, 8, 24, INK[1]); px(img, 15, 24, INK[1])
    stamp(img, ["#.#", ".#.", "#.#"], 11, 23, {"#": CY[3]})
    px(img, 6, 24, ST[2]); px(img, 7, 25, ST[2])                    # crack
    # bent antenna
    px(img, 8, 20, ST[4]); px(img, 8, 19, ST[4]); px(img, 7, 18, ST[5]); px(img, 7, 17, ST[5]); px(img, 8, 16, ST[5]); px(img, 9, 15, ST[5])
    px(img, 10, 15, PK[2])
    # bolt
    px(img, 2, 30, ST[6]); px(img, 3, 30, ST[4]); px(img, 2, 29, ST[7])
    return outline(img)


def d_bench():
    img = new(32, 32)
    # legs
    for lx in (5, 24):
        rect(img, lx, 23, 3, 8, ST[3]); vline(img, lx, 23, 30, ST[5]); vline(img, lx + 2, 23, 30, ST[2])
        hline(img, lx - 1, lx + 3, 30, ST[3]); px(img, lx - 1, 30, ST[5]); px(img, lx + 3, 30, ST[1])
    hline(img, 8, 23, 26, ST[2]); hline(img, 8, 23, 25, ST[4])              # stretcher
    # back posts + back cushion
    for lx in (5, 25):
        vline(img, lx, 12, 18, ST[5]); vline(img, lx + 1, 12, 18, ST[3])
    rect(img, 3, 8, 26, 7, TEAL[3]); hline(img, 4, 27, 8, TEAL[5]); hline(img, 3, 28, 9, TEAL[4]); hline(img, 3, 28, 14, TEAL[1])
    vline(img, 28, 9, 14, TEAL[2]); vline(img, 3, 9, 13, TEAL[4]); clear(img, 3, 8); clear(img, 28, 8)
    vline(img, 15, 9, 13, TEAL[1]); vline(img, 16, 9, 13, TEAL[4]); px(img, 9, 11, TEAL[1]); px(img, 22, 11, TEAL[1])
    px(img, 9, 12, TEAL[4]); px(img, 22, 12, TEAL[4])
    # seat
    rect(img, 2, 19, 28, 2, TEAL[4]); hline(img, 3, 28, 19, TEAL[5]); hline(img, 2, 29, 21, TEAL[2])
    px(img, 29, 20, TEAL[2]); px(img, 29, 19, TEAL[3])
    hline(img, 2, 29, 22, ST[3]); px(img, 2, 22, ST[5]); px(img, 29, 22, ST[1])
    img = outline(img)
    # forgotten mug on the seat (drawn over the outline so it sits in front)
    rect(img, 18, 14, 6, 6, OUT)
    rect(img, 19, 15, 4, 4, WH); vline(img, 22, 15, 18, ST[6]); hline(img, 19, 22, 18, ST[6])
    hline(img, 19, 22, 15, OR[3]); px(img, 19, 15, OR[4])
    setp(img, 24, 16, OUT); setp(img, 24, 17, OUT); setp(img, 25, 16, OUT); setp(img, 25, 17, OUT) if False else None
    setp(img, 23, 16, ST[7]); setp(img, 24, 16, ST[7]) if False else None
    return img


def d_fuel_hose():
    img = new(32, 32)
    # hose (behind the pump): from the nozzle down in a loop back to the base
    pts = [(20, 15), (22, 18), (24, 21), (24, 25), (22, 28), (18, 28)]
    for k in range(len(pts) - 1):
        capsule(img, pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1], 0.8, ST[1])
    for (x, y) in ((23, 19), (24, 21), (25, 23), (24, 26), (21, 28)):
        px(img, x, y, ST[3])
    # pump body
    rect(img, 7, 6, 10, 25, ST[4]); vline(img, 7, 6, 30, ST[6]); vline(img, 8, 6, 30, ST[5]); vline(img, 16, 6, 30, ST[2]); vline(img, 15, 7, 30, ST[3])
    hline(img, 8, 15, 4, GD[3]); hline(img, 7, 16, 5, GD[2]); px(img, 8, 4, GD[4]); px(img, 9, 4, GD[4]); px(img, 16, 5, GD[1])
    hline(img, 7, 16, 6, ST[1])
    # display window: drop icon + 4-part gauge (3 lit)
    rect(img, 9, 8, 6, 8, SCREEN); hline(img, 9, 14, 8, INK[1])
    stamp(img, [".#.", ".#.", "###", "###", ".#."], 10, 9, {"#": CY[4]}); px(img, 10, 11, CY[6])
    px(img, 14, 9, GR[3])
    for k in range(4):
        px(img, 10 + k, 15, CY[4] if k < 3 else CY[1])
    # lower panel: vents, hazard strip
    hline(img, 10, 13, 19, ST[2]); hline(img, 10, 13, 21, ST[2]); hline(img, 10, 13, 20, ST[5])
    for x in range(9, 15):
        for y in (25, 26):
            px(img, x, y, GD[3] if ((x + y) // 2) % 2 == 0 else INK[1])
    # base
    hline(img, 6, 17, 29, ST[4]); hline(img, 6, 17, 30, ST[2]); px(img, 6, 29, ST[6]); px(img, 17, 29, ST[2])
    # holstered nozzle on the right side
    rect(img, 17, 10, 2, 3, ST[2])
    stamp(img, ["..sS..",
                "..sS..",
                ".OOoo.",
                "OOOoor",
                "OOooor",
                ".Ooor.",
                "..or..",
                "..kk.."], 17, 7, {"o": OR[2], "O": OR[4], "r": OR[1], "s": ST[6], "S": ST[4], "k": ST[1]})
    return outline(img)


def decor_frames():
    fn = {"crate": d_crate, "crate_stack": d_crate_stack, "barrel": d_barrel, "barrel_cyan": lambda: d_barrel(True),
          "cone": d_cone, "toolbox": d_toolbox, "sign_right": d_sign_right, "sign_up": d_sign_up,
          "sign_warning": d_sign_warning, "sign_fuel": d_sign_fuel, "terminal_small": d_terminal_small,
          "plant_pot": d_plant_pot, "lamp_post": d_lamp_post, "pipe_valve": d_pipe_valve,
          "monitor_wall": d_monitor_wall, "fan_vent": d_fan_vent, "cable_coil": d_cable_coil,
          "robot_parts": d_robot_parts, "bench": d_bench, "fuel_hose": d_fuel_hose}
    out = []
    for n in DECOR_NAMES:
        f = fn[n]()
        assert f.size == (32, 32), n
        out.append(f)
    return out


def crate_fracbar(img, x, y, col, hollow=3):
    """Stencilled 4-part fraction bar (cells 2x4), one cell left hollow."""
    for c in range(4):
        x0 = x + c * 3
        if c == hollow:
            px(img, x0, y, col); px(img, x0 + 1, y, col); px(img, x0, y + 3, col); px(img, x0 + 1, y + 3, col)
            px(img, x0, y + 1, col); px(img, x0, y + 2, col); px(img, x0 + 1, y + 1, col) if False else None
            px(img, x0 + 1, y + 2, col) if False else None
        else:
            rect(img, x0, y, 2, 4, col)


# =============================================================================
# build
# =============================================================================
def anim(frames, fps, loop=True):
    return {"frames": list(frames), "fps": fps, "loop": loop}


def bbox(img):
    b = img.getbbox()
    return [b[0], b[1], b[2] - b[0], b[3] - b[1]] if b else [0, 0, 0, 0]


def build():
    S = {}
    F = {}
    F["gpad"] = [gpad_frame(i, "up") for i in range(4)] + [gpad_frame(i, "down") for i in range(4)]
    S["gpad"] = dict(file="sprites/gpad.png", fw=32, fh=12,
                     anims={"up": anim(range(0, 4), 10), "down": anim(range(4, 8), 10)})
    F["pod"] = [pod_frame(s) for s in ("idle", "correct", "wrong", "done")]
    S["pod"] = dict(file="sprites/pod.png", fw=48, fh=24,
                    names={"idle": 0, "correct": 1, "wrong": 2, "done": 3})
    F["barrier"] = [barrier_frame(i) for i in range(4)]
    S["barrier"] = dict(file="sprites/barrier.png", fw=16, fh=16, anims={"on": anim(range(4), 12)})
    F["sign_display"] = [sign_frame(s) for s in ("normal", "good", "bad")]
    S["sign_display"] = dict(file="sprites/sign_display.png", fw=32, fh=32, names={"normal": 0, "good": 1, "bad": 2})
    F["mine"] = [mine_frame(i) for i in range(4)]
    S["mine"] = dict(file="sprites/mine.png", fw=16, fh=16, anims={"pulse": anim(range(4), 8)})
    F["zap_emitter"] = [zap_emitter_frame(False), zap_emitter_frame(True)]
    S["zap_emitter"] = dict(file="sprites/zap_emitter.png", fw=16, fh=16, names={"idle": 0, "firing": 1})
    F["zap_arc"] = [zap_arc_frame(i) for i in range(4)]
    S["zap_arc"] = dict(file="sprites/zap_arc.png", fw=16, fh=16, anims={"arc": anim(range(4), 16)})
    F["steam"] = [steam_frame(i) for i in range(6)]
    S["steam"] = dict(file="sprites/steam.png", fw=16, fh=32, anims={"puff": anim(range(6), 12)})
    F["spikes"] = [spikes_frame(i) for i in range(4)]
    S["spikes"] = dict(file="sprites/spikes.png", fw=16, fh=16, anims={"shimmer": anim(range(4), 8)})
    F["bolt"] = [bolt_frame(i) for i in range(4)]
    S["bolt"] = dict(file="sprites/bolt.png", fw=24, fh=8, anims={"fly": anim(range(4), 14)})
    F["orb"] = [orb_frame(i) for i in range(4)]
    S["orb"] = dict(file="sprites/orb.png", fw=12, fh=12, anims={"pulse": anim(range(4), 12)})
    F["decor"] = decor_frames()
    S["decor"] = dict(file="sprites/decor.png", fw=32, fh=32, names={n: i for i, n in enumerate(DECOR_NAMES)})
    for key, frames in F.items():
        cols = 5 if key == "decor" else len(frames)
        save(sheet(frames, cols=cols), S[key]["file"])
    manifest("props_world", {"sheets": S})
    return F, S


def previews(F):
    contact(F["gpad"], "pw_gpad.png", scale=8, cols=4)
    contact(F["pod"], "pw_pod.png", scale=8, cols=2)
    contact(F["barrier"] + F["zap_arc"], "pw_barrier_arc.png", scale=10, cols=4)
    contact(F["sign_display"], "pw_sign_display.png", scale=10)
    contact(F["mine"] + F["zap_emitter"] + F["spikes"], "pw_hazards.png", scale=10, cols=5)
    contact(F["steam"], "pw_steam.png", scale=8)
    contact(F["bolt"], "pw_bolt.png", scale=12, cols=2)
    contact(F["orb"], "pw_orb.png", scale=14)
    contact(F["decor"][:10], "pw_decor_a.png", scale=8, cols=5)
    contact(F["decor"][10:], "pw_decor_b.png", scale=8, cols=5)


if __name__ == "__main__":
    F, S = build()
    previews(F)
    print("props_world:", {k: len(v) for k, v in F.items()})
