"""
phantom.py - the Fraction Phantom (boss, 96x96) and its small holo-bust projection (48x48).

The Phantom is a hooded hologram whose cloak is literally a stack of fraction bars.
  * bars are parametric: width, segment count and lit cells animate (they re-divide
    into EQUIVALENT fractions: 1/2 -> 2/4 -> 4/8 ...), and each bar can slide sideways
  * a number line with scrolling tick marks runs down the cloak edge
  * hood, eyes, hands and the "missing quarter" emblem are hand-pixelled
  * a hologram pass adds alpha, scanlines, empty lines and pink/purple glitch slices

Body centre is (48,48) in every frame of float/attack/hurt/stunned; the game adds the hover.
Re-run:  cd art && python3 phantom.py
"""
import math, os, random
from pix import *

FW = FH = 96
NV, CN, PU, PK, GD, IK = ramp("navy"), ramp("cyan"), ramp("purple"), ramp("pink"), ramp("gold"), ramp("ink")
WHITE = C["white"]
BG = "#0a1322"


def A(c, a):
    return (c[0], c[1], c[2], max(0, min(255, int(a))))


def sp(img, x, y, c):
    """Set a pixel (overwrite, no blending)."""
    x = int(x); y = int(y)
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), c)


def gp(img, x, y):
    if 0 <= x < img.width and 0 <= y < img.height:
        return img.getpixel((x, y))
    return T


# =============================================================================
# 1. FRACTION BARS
# =============================================================================
LIT_SETS = [  # (top row, fill, bottom row) from shadow side to lit side
    (CN[3], CN[2], CN[2]),
    (CN[4], CN[3], CN[2]),
    (CN[5], CN[4], CN[3]),
    (CN[6], CN[5], CN[4]),
    (WHITE, CN[6], CN[5]),
    (WHITE, WHITE, CN[6]),
]
PINK_SET = (PK[4], PK[3], PK[2])
PURP_SET = (PU[6], PU[5], PU[4])
DIM_SET = (NV[4], NV[3], NV[2])
FRAME = (NV[5], NV[4], NV[3])
FRAME_PU = (PU[5], PU[4], PU[3])
FRAME_DIM = (NV[3], NV[2], NV[1])


def frac_bar(img, cx, y, W, h, n, lit, a=230, body_cx=48, bright=0, tint=None, frame=None,
             hollow=None, clip=None, cell_tint=None):
    """One fraction bar: W px wide (W-1 divisible by n keeps the cells equal), h tall,
    n cells, `lit` = set of lit cell indices.  Shaded as part of a round body centred on body_cx."""
    x0 = int(round(cx)) - W // 2
    y = int(round(y))
    bnd = [int(round(k * (W - 1) / n)) for k in range(n + 1)]
    cell_of = {}
    for k in range(n):
        for i in range(bnd[k] + 1, bnd[k + 1]):
            cell_of[i] = k
    fr_hi, fr_mid, fr_lo = frame or FRAME
    hol = hollow or PU[1]
    cell_tint = cell_tint or {}
    for j in range(h):
        for i in range(W):
            if i in (0, W - 1) and j in (0, h - 1) and h >= 3 and W >= 4:
                continue                                    # rounded corners
            x = x0 + i
            if clip:
                lo, hi = clip(y + j) if callable(clip) else clip
                if not (lo <= x <= hi):
                    continue
            u = (x - body_cx) / 15.0                        # -1 (lit side) .. +1 (shadow side)
            if i in cell_of and 0 < j < h - 1:
                k = cell_of[i]
                if k in lit or k in cell_tint:
                    tn = cell_tint.get(k, tint)
                    if tn:
                        top, fill, bot = tn
                    else:
                        idx = 2 + bright + (1 if u < -0.3 else 0) - (1 if u > 0.4 else 0)
                        top, fill, bot = LIT_SETS[max(0, min(5, idx))]
                    if j == 1 and h >= 4:
                        c = top
                    elif j == h - 2 and h >= 5:
                        c = bot
                    else:
                        c = fill
                    sp(img, x, y + j, A(c, a))
                else:
                    c = IK[1] if (j == 1 and h >= 5) else hol
                    sp(img, x, y + j, A(c, a * 0.84))
            else:
                # frame / divider
                if j == 0:
                    c = fr_hi if u < 0.1 else fr_mid
                elif j == h - 1:
                    c = fr_lo
                elif i == 0:
                    c = fr_hi
                elif i == W - 1:
                    c = fr_lo
                else:
                    kl = cell_of.get(i - 1); kr = cell_of.get(i + 1)
                    c = fr_mid
                    if kl in lit and kr in lit:
                        c = (tint[2] if tint else CN[2])
                sp(img, x, y + j, A(c, a))


def fit_n(W, prefer=(4, 2, 1)):
    for n in prefer:
        if (W - 1) % n == 0:
            return n
    return 1


# cloak layout: (y, W, h).  W-1 is divisible by every denominator the bar uses.
BARS = [
    dict(y=44, W=29, h=5),
    dict(y=50, W=29, h=5),
    dict(y=56, W=25, h=5),
    dict(y=62, W=19, h=5),
    dict(y=68, W=13, h=4),
    dict(y=73, W=9, h=4),
]
# each bar: a fraction value shown with a cycle of denominators (equivalent fractions),
# and which end the lit cells are packed against.
BAR_FRAC = [
    dict(num=1, den=2, dens=[2, 4], side=0),
    dict(num=3, den=4, dens=[4, 4], side=1),
    dict(num=1, den=4, dens=[4, 8], side=0),
    dict(num=2, den=3, dens=[3, 3], side=1),
    dict(num=1, den=2, dens=[2, 4], side=0),
    dict(num=1, den=2, dens=[2, 2], side=1),
]


def lit_cells(num, den, n, side):
    k = num * n // den
    return set(range(k)) if side == 0 else set(range(n - k, n))


# cloak silhouette: the bar width the cloak is cut for at each row - broad chest, then a
# smooth S-curve taper into a narrow stem.  Bars are clipped to it row by row.
CLOAK_Y0, CLOAK_Y1 = 41, 78
MARGIN_L, MARGIN_R = 4, 2      # left: edge line + 3px number-line strip; right: gap + edge line
CHEST_W, STEM_W = 29.6, 8.0


def cloak_w(y):
    if y <= 50:
        return CHEST_W - max(0, 46 - y) * 0.12
    t = min(1.0, (y - 50) / 28.0)
    return STEM_W + (CHEST_W - STEM_W) * (0.5 + 0.5 * math.cos(math.pi * t))


# =============================================================================
# 2. HOOD (hand-tuned row spans, shaded by rule)
# =============================================================================
# local box; row 0 is the tip of the hood (hooked back to the left).
HOOD_OUT = [
    (4, 5), (3, 8), (3, 10), (4, 12), (5, 14), (6, 16), (6, 18), (5, 19), (4, 21), (3, 22),
    (2, 23), (1, 24), (1, 25), (0, 25), (0, 26), (0, 26), (0, 26), (0, 26), (0, 26), (0, 26),
    (1, 26), (1, 25), (2, 25), (3, 24), (4, 23),
    # cowl / shoulders
    (2, 25), (-1, 28), (-3, 30), (-4, 31), (-4, 31), (-4, 31), (-3, 30), (-1, 28), (4, 23), (9, 18),
]
HOOD_IN = {
    9: (14, 15), 10: (13, 17), 11: (12, 18), 12: (11, 20), 13: (10, 21), 14: (9, 22), 15: (8, 22),
    16: (7, 23), 17: (6, 23), 18: (6, 24), 19: (5, 24), 20: (5, 24), 21: (6, 24), 22: (6, 23),
    23: (8, 22),
}
HOOD_W = 28
COWL_ROW = 25         # first row of the cowl
HOOD_CX = 13          # local x that sits on the body centre line
HOOD_Y = 10           # frame y of hood row 0

EYES = {
    # art for the LEFT eye (mirrored for the right).  w white, c pale cyan, d cyan, p pink
    "calm":   ["cc...",
               "wwwww",
               "wwwww",
               ".ddd."],
    "narrow": [".....",
               "cc...",
               "wwwww",
               ".ddd."],
    "fierce": ["ww...",
               "wwww.",
               "wwwww",
               ".ddd."],
    "blink":  [".....",
               ".....",
               "ddddd",
               "....."],
    "wide":   [".www.",
               "wwwww",
               "wwwww",
               ".ddd."],
    "x":      ["p...p",
               ".p.p.",
               "..w..",
               ".p.p.",
               "p...p"],
    "plus":   ["..p..",
               "..p..",
               "ppwpp",
               "..p..",
               "..p.."],
}
EYE_CMAP = {"w": WHITE, "c": CN[6], "d": CN[4], "p": PK[3]}
EYE_L = (8, 17)      # local top-left of each eye
EYE_R = (17, 17)
HOOD_PAD = 14


def hood_layer(eyes="calm", shear=0.0, dim=0, eye_dx=0, eye_dy=0, a=235, part="all", tip=0, wire=False):
    """The hood on a padded canvas; local (0,0) is at (HOOD_PAD, 0).
    part: all | hood | cowl.   shear tilts the hood about its base (pixel-clean row offsets).
    tip: extra x offset for the very tip rows (secondary motion)."""
    pad = HOOD_PAD
    img = new(HOOD_W + pad * 2, len(HOOD_OUT) + 2)
    out = set(); face = set()
    for r, (L, R) in enumerate(HOOD_OUT):
        for x in range(L, R + 1):
            out.add((x, r))
    for r, (L, R) in HOOD_IN.items():
        for x in range(L, R + 1):
            face.add((x, r))

    def sh(r):
        s = int(round(shear * (COWL_ROW - r))) if r < COWL_ROW else 0
        if tip:
            s += tip if r <= 1 else (int(tip / 2) if r <= 3 and abs(tip) > 1 else 0)
        return s

    tones = [PU[1], PU[2], NV[3], NV[4], NV[5]]
    lipc = (CN[5], CN[3])
    hem = (NV[5], NV[3])
    lining = NV[0]
    if dim:
        tones = [IK[2], NV[1], NV[2], NV[3], NV[4]]
        lipc = (NV[4], NV[3]); hem = (NV[4], NV[2])
    eye_px = {}
    if eyes and eyes != "off" and not wire:
        rows = EYES[eyes]
        for (ex, ey), mirror in ((EYE_L, False), (EYE_R, True)):
            oy = ey + eye_dy - (len(rows) - 4)
            for j, row in enumerate(rows):
                row = row[::-1] if mirror else row
                for i, ch in enumerate(row):
                    if ch != ".":
                        eye_px[(ex + i + eye_dx, oy + j)] = EYE_CMAP[ch]
    for (x, r) in sorted(out):
        if part == "hood" and r >= COWL_ROW:
            continue
        if part == "cowl" and r < COWL_ROW:
            continue
        X = pad + x + sh(r)
        e_t = (x, r - 1) not in out
        e_l = (x - 1, r) not in out
        e_r = (x + 1, r) not in out
        e_b = (x, r + 1) not in out
        lip = (x, r) not in face and any(((x + dx, r + dy) in face) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if wire:
            if e_t or e_l or e_r or e_b or lip:
                sp(img, X, r, A(CN[4] if (x + r) % 2 else CN[5], a))
            continue
        if (x, r) in face:
            c = IK[0]
            # inner lining: the far wall of the hood catches a little light
            if (x + 1, r) not in face or (x + 2, r) not in face or (x + 1, r + 1) not in face:
                c = lining
            sp(img, X, r, A(c, 240))
            continue
        if r < COWL_ROW:
            nx = (x - 13) / 13.0; ny = (r - 13) / 13.0
            l = -(nx * 0.62 + ny * 0.78)
            ti = 3 if l > 0.50 else 2 if l > 0.0 else 1 if l > -0.55 else 0
            if (e_t or e_l) and l > -0.15:
                ti = min(4, ti + 1)
            if (e_r or e_b) and l < 0.2:
                ti = max(0, ti - 1)
            c = tones[ti]
            if lip:
                lx = (x - 14.5); ly = (r - 17.0)
                c = lipc[0] if (lx * 0.55 + ly * 0.8) > -3.0 else lipc[1]
        else:
            # cowl / shoulder cape
            rr = r - COWL_ROW
            nx = (x - 13.5) / 18.0
            l = -(nx * 0.80 + (rr - 3.5) / 7.0 * 0.60)
            ti = 3 if l > 0.42 else 2 if l > -0.05 else 1 if l > -0.55 else 0
            if rr <= 1 and abs(nx) < 0.75:
                ti = max(0, ti - 1)        # shadow under the hood
            if e_l or (e_t and nx < 0.1):
                ti = 4
            if e_r:
                ti = 0
            c = tones[ti]
            if (x, r + 1) not in out:
                c = hem[0] if nx < 0.3 else hem[1]     # trim along the hem
        sp(img, X, r, A(c, a))
    for (x, r), c in eye_px.items():
        sp(img, pad + x + sh(r), r, c)
    return img


# =============================================================================
# 3. EMBLEM: a circle with one quarter wedge missing
# =============================================================================
def missing_arc(r):
    """Rim pixels of the missing (top-right) quarter, ordered along the arc."""
    R2 = (r + 0.35) ** 2
    ins = lambda dx, dy: dx * dx + dy * dy <= R2
    pts = [(dx, dy) for dx in range(1, r + 1) for dy in range(-r, 0)
           if ins(dx, dy) and (not ins(dx + 1, dy) or not ins(dx, dy - 1))]
    pts.sort(key=lambda p: math.atan2(p[0], -p[1]))
    return pts


def emblem(img, cx, cy, r=6, state="normal", pulse=0, ants=0, socket=True, glint=None):
    """Pie with the top-right quarter missing; its ghost outline 'marches' in pink."""
    R2 = (r + 0.35) ** 2
    if socket:
        for y in range(cy - r - 2, cy + r + 3):          # dark socket behind
            for x in range(cx - r - 2, cx + r + 3):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if d2 <= (r + 1.6) ** 2:
                    sp(img, x, y, A(IK[0], 240))
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            d2 = dx * dx + dy * dy
            if d2 > R2 or (dx > 0 and dy < 0):
                continue
            edge = d2 > (r - 0.9) ** 2
            if dx == 0 or dy == 0:
                c = CN[3] if state != "dim" else NV[2]
            else:
                l = -(dx * 0.6 + dy * 0.8) / r
                if state == "dim":
                    c = NV[4] if l > 0.2 else NV[3]
                else:
                    c = WHITE if l > 0.45 else CN[6] if l > -0.2 else CN[5]
                    if edge and l < -0.1:
                        c = CN[4]
                    if pulse and not edge:
                        c = WHITE
                    if glint is not None and (dx + dy) in (glint, glint + 1):
                        c = WHITE
            sp(img, x, y, A(c, 245))
    if socket:
        for i, (dx, dy) in enumerate(missing_arc(r)):
            on = (i - ants) % 4 == 0
            c = (PK[3] if on else PK[1]) if state != "dim" else (PU[3] if on else PU[2])
            sp(img, cx + dx, cy + dy, A(c, 235))


def core(img, cx, cy, r=9, f=0):
    """The exposed, SOLID projector core of the stunned Phantom: the same three-quarter pie,
    opaque gold, ink-outlined, cracked and pulsing - the 'jump on me' target."""
    hot = f in (1, 2)
    # pulse ring (drawn first, under the core)
    rr = [r + 2.2, r + 3.4, r + 4.8, r + 6.0][f]
    ra = [0, 230, 150, 70][f]
    if ra:
        for y in range(int(cy - rr - 2), int(cy + rr + 3)):
            for x in range(int(cx - rr - 2), int(cx + rr + 3)):
                d = math.hypot(x - cx, y - cy)
                if rr - 1.0 < d <= rr:
                    px(img, x, y, A(GD[5] if f == 1 else GD[3], ra))
    for y in range(cy - r - 2, cy + r + 3):
        for x in range(cx - r - 2, cx + r + 3):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d <= r + 1.45:
                sp(img, x, y, IK[0])                               # ink outline + socket
            if d > r + 0.35:
                continue
            missing = dx > 0 and dy < 0
            edge = d > r - 1.0
            if missing:
                sp(img, x, y, IK[1])
                continue
            if dx == 0 or dy == 0:
                sp(img, x, y, GD[1]); continue
            l = -(dx * 0.6 + dy * 0.8) / r
            if l > 0.55:
                c = GD[5]
            elif l > 0.15:
                c = GD[4]
            elif l > -0.35:
                c = GD[3]
            else:
                c = GD[2]
            if edge and l < 0.0:
                c = GD[1] if l < -0.5 else GD[2]
            if hot:
                c = {GD[2]: GD[3], GD[3]: GD[4], GD[4]: GD[5], GD[5]: WHITE, GD[1]: GD[2]}[c]
            sp(img, x, y, c)
    for i, (dx, dy) in enumerate(missing_arc(r)):
        sp(img, cx + dx, cy + dy, PK[3] if (i - f) % 4 == 0 else PK[1])
    # crack: zig-zag from the centre down-left to the rim, with a branch
    crack = [(-1, 1), (-2, 2), (-2, 3), (-3, 4), (-4, 4), (-5, 5), (-5, 6), (-6, 7),
             (-3, 5), (-3, 6), (-2, 7),
             (1, 2), (2, 2), (3, 3), (4, 3), (5, 4)]
    for (dx, dy) in crack:
        if math.hypot(dx, dy) <= r:
            sp(img, cx + dx, cy + dy, IK[0])
    # specular glint
    sp(img, cx - 5, cy - 5, WHITE); sp(img, cx - 4, cy - 6, WHITE); sp(img, cx - 6, cy - 4, GD[5])


# =============================================================================
# 4. HANDS (detached, hand-pixelled)
# =============================================================================
HAND_CMAP = {"W": NV[6], "H": NV[5], "h": NV[4], "d": NV[3], "c": CN[3], "C": CN[5], "k": NV[2]}
HANDS = {
    # open palm, fingers up, thumb on the left
    "open": [
        "...WH.WH....",
        "...Hh.Hh.WH.",
        "...Hh.Hh.Hh.",
        "WH.Hh.Hh.Hh.",
        "Hh.HHHHHHHh.",
        "HHhHHHHHHhh.",
        ".HHHHHHHhhd.",
        "..hHHHHhhd..",
        "...CCCCCc...",
        "....cc.c....",
    ],
    # cupped, palm up, fingers curled - idly toying with a spark of glitch energy
    "cup": [
        "....WH.WH...",
        "...WHh.Hh.WH",
        "WH.Hh..Hh.Hh",
        "HHhHHHHHHHHh",
        ".HHHHHHHHhh.",
        "..hHHHHhhd..",
        "...hhhhdd...",
        "...CCCCCc...",
        "....cc.c....",
    ],
    # relaxed, hanging: cuff on top, fingers curled down, thumb on the right
    "rest": [
        "...c.cc....",
        "..CCCCCc...",
        "..WHHHHh...",
        ".WHHHHHHh..",
        ".HHHHHHHhH.",
        ".HHHHHHhhHh",
        ".Hh.Hh.Hhd.",
        ".Hh.Hh.hd..",
        ".hd.hd.....",
    ],
}


def hand_sprite(kind, flip=False, rot=0, a=235, dim=False):
    img = ascii_sprite(HANDS[kind], HAND_CMAP)
    if dim:
        img = replace(img, {NV[6]: NV[4], NV[5]: NV[3], NV[4]: NV[2], NV[3]: NV[1], CN[5]: NV[3], CN[3]: NV[2]})
    if rot:
        img = img.rotate(-90 * rot, expand=True)
    if flip:
        img = flip_h(img)
    big = new(img.width + 2, img.height + 2)
    big.alpha_composite(img, (1, 1))
    big = outline(big, A(IK[0], 235))
    return tint_alpha(big, a / 255.0) if a < 255 else big


# =============================================================================
# 5. THE FIGURE
# =============================================================================
def default_pose():
    return dict(
        t=0.0,                    # loop phase 0..1
        sway=3.0,                 # tail sway amplitude
        curve=9.0,                # how far the tail trails to the left
        bars=[dict() for _ in BARS],   # per-bar overrides: n, lit, dx, dy, a, bright, tint, hide, W, h
        den_step=0,               # which denominator of each bar's cycle
        hood=dict(dx=0, dy=0, shear=0.0, eyes="calm", dim=0, tip=0, cowl_dy=0, wire=False, a=235),
        emblem=dict(state="normal", pulse=0, dx=0, dy=0, r=6, show=True, ants=0),
        hands=[dict(kind="rest", x=21, y=58), dict(kind="cup", x=76, y=50)],
        tick=0,                   # tick scroll
        tail=True, cloak=True, dim=False, clip=True,
        tail_dy=0,
    )


def body_cx(y, pose):
    t = pose["t"]
    s = max(0.0, min(1.4, (y - 52) / 30.0)) ** 1.3
    curve = -pose["curve"] * max(0.0, (y - 58) / 30.0) ** 2          # the tail trails off to the left
    return 48 + curve + pose["sway"] * s * math.sin(2 * math.pi * t - (y - 52) * 0.085)


def cloak_span(y, pose):
    cx = body_cx(y, pose)
    half = (cloak_w(y) - 1) / 2.0
    return int(round(cx - half - MARGIN_L)), int(round(cx + half + MARGIN_R))


TAIL = [  # loose bars under the cloak: (y, dx, W, h, n, lit, phase)
    (80, 0, 9, 4, 2, {0}, 0.0),
    (85, 0, 7, 3, 1, {0}, 0.3),
    (89, 0, 2, 2, 1, {0}, 0.6),
]
TAIL_TINT = [PURP_SET, PINK_SET, PINK_SET, PINK_SET]


def render_body(pose):
    """Cloak (membrane, bars, number line, tail), hood and emblem on one layer; outlined."""
    img = new(FW, FH)
    t = pose["t"]
    dim = pose["dim"]
    ticks = []
    if pose["cloak"]:
        # --- membrane + edge lines ------------------------------------------------
        prev = None
        for y in range(CLOAK_Y0, CLOAK_Y1 + 1):
            L, R = cloak_span(y, pose)
            for x in range(L + 1, R):
                sp(img, x, y, A(IK[1], 168))
            a = 235 if y < 70 else 235 - (y - 70) * 8
            for side, x in ((0, L), (1, R)):
                xs = [x]
                if prev is not None:
                    px_ = prev[side]
                    if x - px_ > 1:
                        xs = list(range(px_ + 1, x + 1))
                    elif px_ - x > 1:
                        xs = list(range(x, px_))
                ec = (CN[5] if side == 0 else NV[4]) if not dim else (NV[3] if side == 0 else NV[2])
                for xx in xs:
                    sp(img, xx, y, A(ec, a))
            prev = (L, R)
            # number-line ticks on the left strip: short every 4 px, long every 8
            ph = (y - pose["tick"]) % 8
            if ph % 4 == 0 and y < CLOAK_Y1 - 2:
                ticks.append((L + 1, y, 2 if ph == 0 else 1, a))
        for (x, y, ln, a) in ticks:
            for k in range(ln):
                tc = (CN[5] if ln == 1 else CN[6]) if not dim else NV[3]
                sp(img, x + k, y, A(tc, a))
    # --- bars -----------------------------------------------------------------
    for i, (b, fr) in enumerate(zip(BARS, BAR_FRAC)):
        o = pose["bars"][i]
        if o.get("hide"):
            continue
        W = o.get("W", b["W"])
        n = o.get("n", fr["dens"][o.get("den_i", pose["den_step"]) % len(fr["dens"])])
        if (W - 1) % n:
            n = fit_n(W)
        lit = o.get("lit", lit_cells(fr["num"], fr["den"], n, fr["side"]))
        h = o.get("h", b["h"])
        by = b["y"] + o.get("dy", 0) + (b["h"] - h) // 2
        yc = b["y"] + b["h"] / 2
        cx = body_cx(yc, pose) + o.get("dx", 0)
        a = o.get("a", 235 - i * 8)
        clip = None
        if pose["clip"] and pose["cloak"] and not o.get("noclip"):
            clip = lambda yy, _p=pose: (cloak_span(yy, _p)[0] + 1, cloak_span(yy, _p)[1] - 1)
        frac_bar(img, cx, by, W, h, n, lit, a=a, bright=o.get("bright", 0),
                 tint=o.get("tint", DIM_SET if dim else None), clip=clip,
                 frame=o.get("frame", FRAME_DIM if dim else None), hollow=IK[2] if dim else None,
                 cell_tint=o.get("cell_tint"))
    # --- tail -------------------------------------------------------------------
    if pose["tail"]:
        for k, (y, dx, W, h, n, lit, ph) in enumerate(TAIL):
            bob = math.sin(2 * math.pi * (t + ph))
            yy = y + int(round(bob * 0.8)) + pose["tail_dy"]
            cx = body_cx(y + 1, pose) + dx
            tint = TAIL_TINT[min(k, 3)]
            if dim:
                tint = (PU[4], PU[3], PU[2])
            if W <= 3:
                rect(img, int(round(cx)) - 1, yy, W, h, A(PK[3] if not dim else PU[3], 190))
            else:
                frac_bar(img, cx, yy, W, h, n, lit, a=220 - k * 25, tint=tint,
                         frame=FRAME_PU if not dim else (PU[3], PU[2], PU[1]))
    # --- hood ---------------------------------------------------------------------
    h = pose["hood"]
    ox = 48 - HOOD_CX - HOOD_PAD
    if h.get("cowl_dy", 0) != h["dy"] or h["dx"]:
        cw = hood_layer(None, 0, h["dim"], part="cowl", a=h["a"], wire=h["wire"])
        img.alpha_composite(cw, (ox, HOOD_Y + h.get("cowl_dy", 0)))
        hd = hood_layer(h["eyes"], h["shear"], h["dim"], part="hood", tip=h["tip"], a=h["a"], wire=h["wire"])
        paste(img, hd, ox + h["dx"], HOOD_Y + h["dy"])
    else:
        hd = hood_layer(h["eyes"], h["shear"], h["dim"], tip=h["tip"], a=h["a"], wire=h["wire"])
        img.alpha_composite(hd, (ox, HOOD_Y + h["dy"]))
    # --- emblem ---------------------------------------------------------------------
    e = pose["emblem"]
    if e["show"]:
        emblem(img, 48 + e["dx"], 46 + e["dy"], e["r"], e["state"], e["pulse"], e["ants"], glint=e.get("glint"))
    img = outline(img, A(IK[0], 235))
    return img


# ------------------------------------------------------------------ hologram FX
def holo_fx(img, scan=0, empty=(), dim_rows=3, strength=0.86):
    """Hologram pass: every `dim_rows`-th row is dimmer, `empty` rows are blank."""
    out = img.copy(); p = out.load()
    for y in range(img.height):
        if y in empty:
            for x in range(img.width):
                p[x, y] = T
            continue
        if dim_rows and (y + scan) % dim_rows == 0:
            for x in range(img.width):
                c = p[x, y]
                if c[3]:
                    p[x, y] = (c[0], c[1], c[2], int(c[3] * strength))
    return out


def glitch(img, slices):
    """slices: (y0, y1, dx) - shift those rows sideways."""
    if not slices:
        return img
    shift = {}
    for (y0, y1, dx) in slices:
        for y in range(y0, y1 + 1):
            shift[y] = dx
    out = new(*img.size); src = img.load()
    for y in range(img.height):
        dx = shift.get(y, 0)
        for x in range(img.width):
            c = src[x, y]
            if c[3]:
                sp(out, x + dx, y, c)
    return out


def chroma(img, dx, col, alpha=150, rows=None):
    """Coloured echo of the silhouette, offset by dx, only on empty pixels (glitch fringe)."""
    out = img.copy(); src = img.load()
    for y in range(img.height):
        if rows is not None and y not in rows:
            continue
        for x in range(img.width):
            if src[x, y][3] > 120 and gp(img, x + dx, y)[3] < 40:
                sp(out, x + dx, y, A(col, alpha))
    return out


def aura(img, col=None, alpha=80):
    """1px soft glow hugging the ink outline, so the hologram separates from dark walls."""
    col = col or CN[3]
    out = img.copy(); src = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and src[xx, yy][3] > 150:
                    out.putpixel((x, y), (col[0], col[1], col[2], alpha))
                    break
    return out


def tint_img(img, col, amt):
    out = img.copy(); p = out.load()
    for y in range(img.height):
        for x in range(img.width):
            c = p[x, y]
            if c[3]:
                p[x, y] = (int(c[0] + (col[0] - c[0]) * amt), int(c[1] + (col[1] - c[1]) * amt),
                           int(c[2] + (col[2] - c[2]) * amt), c[3])
    return out


def fade(img, m):
    return tint_alpha(img, m)


def render(pose):
    img = render_body(pose)
    for hd in pose["hands"]:
        if hd is None:
            continue
        s = hand_sprite(hd["kind"], hd.get("flip", False), hd.get("rot", 0), dim=hd.get("dim", False),
                        a=hd.get("a", 235))
        paste(img, s, int(round(hd["x"] - s.width / 2)), int(round(hd["y"] - s.height / 2)))
    if pose.get("tint"):
        img = tint_img(img, pose["tint"][0], pose["tint"][1])
    if pose.get("aura", True):
        img = aura(img, NV[2] if pose["dim"] else CN[3], 80)
    img = holo_fx(img, scan=pose.get("scan", 0), empty=pose.get("empty", ()))
    img = glitch(img, pose.get("glitch"))
    for (dx, col, al, rows) in pose.get("chroma", []):
        img = chroma(img, dx, col, al, rows)
    if pose.get("fade", 1.0) < 1.0:
        img = fade(img, pose["fade"])
    if pose.get("core") is not None:
        core(img, 48, pose.get("core_y", 54), 9, pose["core"])
    for (x, y, c) in pose.get("pixels", []):
        px(img, x, y, c)
    return img


def sparkle(x, y, c, big=False):
    pts = [(x, y, c)]
    if big:
        pts += [(x - 1, y, A(c, 170)), (x + 1, y, A(c, 170)), (x, y - 1, A(c, 170)), (x, y + 1, A(c, 170))]
    return pts


# =============================================================================
# 6. ANIMATIONS
# =============================================================================
RH = (76, 50)      # right (cupped) hand rest position
LH = (21, 58)      # left (hanging) hand rest position


def spark_px(x, y, f):
    """The little flame of glitch energy dancing over the cupped palm."""
    pat = [
        [(0, 0, PK[4]), (1, 0, PK[3]), (0, -1, PK[3]), (1, -1, PK[2]), (0, -3, PK[2])],
        [(0, 0, PK[4]), (1, 0, PK[3]), (0, -1, WHITE), (-1, -1, PK[2]), (1, -2, PK[3]), (1, -4, PU[4])],
        [(0, 0, PK[3]), (1, 0, PK[4]), (1, -1, PK[3]), (0, -1, PK[2]), (1, -3, PK[2])],
        [(0, 0, PK[3]), (1, 0, PK[4]), (1, -1, WHITE), (2, -1, PK[2]), (0, -2, PK[3]), (0, -4, PU[4])],
    ][f % 4]
    return [(x + dx, y + dy, A(c, 235)) for dx, dy, c in pat]


def float_pose(f, n=8):
    p = default_pose()
    t = f / n
    p["t"] = t
    p["tick"] = f                       # 1 px/frame, period 8 -> seamless
    for i in range(len(BARS)):
        o = p["bars"][i]
        o["den_i"] = ((f + 2 * i) // 4) % 2
        amp = [0, 0, 1, 1.6, 2, 2][i]
        o["dx"] = int(round(amp * math.sin(2 * math.pi * (t - 0.14 * i))))
        if (f - i) % n == 1:
            o["bright"] = 1             # a pulse of energy runs down the cloak, one bar per frame
    p["emblem"]["ants"] = f % 4
    p["emblem"]["glint"] = {5: -6, 6: -1, 7: 4}.get(f)
    lh = p["hands"][0]; rh = p["hands"][1]
    lh["y"] = LH[1] + round(1.3 * math.sin(2 * math.pi * (t + 0.15)))
    rh["y"] = RH[1] + round(1.3 * math.sin(2 * math.pi * (t + 0.55)))
    p["hood"]["tip"] = -1 if f in (3, 4, 5, 6) else 0
    y1 = 18 + f * 9
    p["empty"] = {y1, (y1 - 18 + 36) % 72 + 18}
    p["pixels"] = spark_px(rh["x"], rh["y"] - 7, f)
    return p


def anim_float():
    frames = []
    for f in range(8):
        p = float_pose(f)
        if f == 3:      # a small glitch: one bar jumps, one cell goes pink
            p["bars"][2]["cell_tint"] = {3: PINK_SET}
            p["glitch"] = [(56, 60, 2)]
            p["chroma"] = [(-1, PK[2], 170, set(range(56, 61)))]
        if f == 6:
            p["bars"][4]["cell_tint"] = {1: PURP_SET}
            p["pixels"] += [(62, 71, A(PK[3], 220)), (64, 74, A(PU[4], 200))]
        if f == 1:
            p["pixels"] += [(29, 68, A(PK[3], 200))]
        frames.append(render(p))
    return frames


def anim_attack():
    frames = []
    shear = [-0.04, -0.08, 0.08, 0.04, 0.0, 0.0]
    eyes = ["narrow", "narrow", "fierce", "fierce", "calm", "calm"]
    rhand = [("cup", 75, 41, 0), ("cup", 72, 31, 0), ("open", 82, 45, 1), ("open", 81, 46, 1), ("open", 79, 48, 0), ("cup", 77, 50, 0)]
    lhand = [(21, 56), (20, 53), (15, 58), (17, 59), (20, 59), (21, 58)]
    for f in range(6):
        p = float_pose(f + 2)           # phases 2..7, so the tail flows straight back into float frame 0
        p["emblem"]["glint"] = None
        p["hood"]["shear"] = shear[f]; p["hood"]["eyes"] = eyes[f]; p["hood"]["tip"] = 0
        kind, x, y, rot = rhand[f]
        p["hands"][1] = dict(kind=kind, x=x, y=y, rot=rot)
        p["hands"][0]["x"], p["hands"][0]["y"] = lhand[f]
        p["empty"] = set()
        p["pixels"] = []
        for i, b in enumerate(BARS):
            o = p["bars"][i]
            n = BAR_FRAC[i]["dens"][0]
            if f == 0:      # charging: cells fill up
                o["n"] = n; o["lit"] = set(range(n)) if i < 3 else lit_cells(BAR_FRAC[i]["num"], BAR_FRAC[i]["den"], n, BAR_FRAC[i]["side"])
                o["dx"] = 0
            elif f == 1:    # squash in: every bar full, contracted
                o["W"] = b["W"] - (4 if b["W"] >= 19 else 2); o["n"] = fit_n(o["W"]); o["lit"] = set(range(o["n"])); o["bright"] = 1; o["dx"] = -1
            elif f == 2:    # release: bars flare out past the cloak
                o["W"] = b["W"] + 6; o["n"] = fit_n(o["W"]); o["lit"] = set(range(o["n"])); o["bright"] = 2
                o["dx"] = 2; o["noclip"] = True; o["a"] = 245
            elif f == 3:
                o["W"] = b["W"] + 2; o["n"] = fit_n(o["W"]); o["lit"] = set(range(o["n"])); o["bright"] = 1
                o["dx"] = 1; o["noclip"] = True
            elif f == 4:
                o["bright"] = 1; o["dx"] = 0
        if f == 0:
            p["pixels"] = spark_px(75, 33, 1) + [(79, 31, A(PK[3], 220)), (71, 30, A(PK[2], 200))]
        if f == 1:      # the spark swells into a charge above the raised palm
            p["emblem"]["pulse"] = 1
            cx_, cy_ = 72, 21
            for yy in range(-3, 4):
                for xx in range(-3, 4):
                    d = math.hypot(xx, yy)
                    if d <= 3.2:
                        p["pixels"].append((cx_ + xx, cy_ + yy, WHITE if d < 1.2 else PK[4] if d < 2.3 else PK[2]))
            p["pixels"] += [(66, 19, A(PK[3], 220)), (78, 23, A(PK[3], 220)), (73, 15, A(PK[2], 220)), (68, 26, A(PU[4], 220))]
        if f == 2:
            p["emblem"]["pulse"] = 1
            p["chroma"] = [(1, PK[2], 170, None)]
            p["pixels"] = (sparkle(91, 45, WHITE, True) + [(92, 41, PK[3]), (93, 49, PK[3]), (90, 38, A(PK[2], 220)),
                           (90, 52, A(PK[2], 220)), (93, 45, PK[4]), (94, 45, PK[3])])
        if f == 3:
            p["pixels"] = [(91, 42, A(PK[3], 200)), (92, 49, A(PK[2], 200)), (94, 46, A(PK[3], 180))]
        if f == 5:
            p["pixels"] = spark_px(77, 43, 0)[:2]
        frames.append(render(p))
    return frames


def anim_hurt():
    frames = []
    dxs = [[5, -4, 5, -4, 3, -3], [-3, 3, -3, 2, -2, 2], [1, -1, 1, -1, 0, 0], [0, 0, 0, 0, 0, 0]]
    shear = [-0.10, -0.06, -0.03, 0.0]
    eyes = ["wide", "wide", "narrow", "narrow"]
    lhand = [(14, 51), (16, 53), (19, 56), (21, 58)]
    rhand = [(83, 40), (81, 43), (78, 47), (76, 50)]
    for f in range(4):
        p = float_pose(f + 4)           # phases 4..7 -> hands back to float frame 0
        p["emblem"]["glint"] = None
        p["hood"]["shear"] = shear[f]; p["hood"]["eyes"] = eyes[f]; p["hood"]["tip"] = 0
        p["hands"][0] = dict(kind="open" if f < 3 else "rest", x=lhand[f][0], y=lhand[f][1], flip=f < 3)
        p["hands"][1] = dict(kind="open" if f < 3 else "cup", x=rhand[f][0], y=rhand[f][1])
        p["empty"] = set()
        p["pixels"] = []
        for i in range(len(BARS)):
            o = p["bars"][i]
            o["dx"] = dxs[f][i]; o["noclip"] = f < 2
            if f == 0:
                o["bright"] = 2
        if f == 0:
            p["tint"] = (WHITE, 0.55)
            p["chroma"] = [(2, PK[2], 200, None), (-2, PU[4], 170, None)]
            p["glitch"] = [(20, 23, -3), (30, 32, 3)]
            p["pixels"] = sparkle(34, 22, WHITE, True) + sparkle(68, 60, PK[4], True) + [(28, 40, PK[3]), (70, 30, PK[3])]
        elif f == 1:
            p["tint"] = (PK[3], 0.28)
            p["chroma"] = [(-1, PK[2], 180, None)]
            p["glitch"] = [(26, 29, 2), (14, 16, -2)]
            p["empty"] = {24, 47, 66}
            p["pixels"] = [(31, 20, A(PK[3], 200)), (71, 63, A(PK[2], 200)), (26, 44, A(WHITE, 200))]
        elif f == 2:
            p["empty"] = {33, 58}
            p["chroma"] = [(1, PK[2], 120, set(range(40, 62)))]
        frames.append(render(p))
    return frames


CORE_Y, CORE_R = 54, 9


def anim_stunned():
    frames = []
    for f in range(4):
        p = default_pose()
        p["t"] = f / 4.0
        p["sway"] = 1.0; p["curve"] = 4.0
        p["dim"] = True
        p["tick"] = 0
        p["tail_dy"] = 1
        p["hood"].update(dx=2, dy=5, cowl_dy=2, shear=0.2, eyes="x" if f % 2 == 0 else "plus", dim=1, a=215)
        p["emblem"]["show"] = False
        off = [0, -2, 1, -1, 2, 0]
        for i in range(len(BARS)):
            o = p["bars"][i]
            n = BAR_FRAC[i]["dens"][0]
            o["n"] = n; o["lit"] = set(); o["dx"] = off[i]; o["a"] = 222 - i * 6
            o["dy"] = 1 if i >= 3 else 0
        # one faint cell flickers somewhere, as if trying to reboot
        fl = [(3, 0), (5, 1), (4, 1), (3, 2)][f]
        p["bars"][fl[0]]["lit"] = {fl[1]}
        p["hands"][0] = dict(kind="rest", x=20, y=66 + (f % 2), dim=True, a=215)
        p["hands"][1] = dict(kind="rest", x=77, y=64 + ((f + 1) % 2), dim=True, flip=True, a=215)
        p["empty"] = {[31, 70, 39, 66][f]}
        p["core"] = f
        p["core_y"] = CORE_Y
        # dizzy sparks circling the drooped hood
        pix = []
        for k in range(3):
            ang = 2 * math.pi * (f / 4.0 + k / 3.0)
            sx = 53 + 13 * math.cos(ang); sy = 16 + 3.2 * math.sin(ang)
            front = math.sin(ang) > -0.2
            col = [GD[4], PK[3], WHITE][k]
            pix += sparkle(int(round(sx)), int(round(sy)), col, big=front)
        p["pixels"] = pix
        frames.append(render(p))
    return frames


def anim_appear():
    frames = []
    # 0: a bright seed line
    img = new(FW, FH)
    for x in range(40, 57):
        sp(img, x, 48, A(WHITE if 44 <= x <= 52 else CN[5], 235))
    for x in range(36, 61):
        if gp(img, x, 48)[3] == 0:
            sp(img, x, 48, A(CN[4], 150))
    for (x, y, c) in sparkle(48, 48, WHITE, True) + [(48, 46, A(CN[5], 200)), (48, 50, A(CN[5], 200)), (33, 48, A(PK[3], 200)), (63, 48, A(PK[3], 200))]:
        px(img, x, y, c)
    frames.append(img)
    # 1: a vertical number line unrolls, first bars are thin lines
    img = new(FW, FH)
    for y in range(24, 75):
        sp(img, 48, y, A(CN[5], 220))
        if (y - 24) % 4 == 0:
            ln = 2 if (y - 24) % 8 == 0 else 1
            for k in range(1, ln + 1):
                sp(img, 48 - k, y, A(CN[5], 200)); sp(img, 48 + k, y, A(CN[5], 200))
    for i, b in enumerate(BARS[:5]):
        w = [9, 13, 11, 7, 5][i]
        for x in range(48 - w, 48 + w + 1):
            sp(img, x, b["y"] + 2, A(CN[4] if (x + i) % 5 else WHITE, 210))
    for (x, y, c) in sparkle(48, 24, WHITE, True) + sparkle(48, 74, PK[4], False) + [(38, 40, A(PK[3], 200)), (59, 61, A(PK[2], 200))]:
        px(img, x, y, c)
    frames.append(img)
    # 2: hollow bars slide in from both sides; the hood is only a wireframe
    p = float_pose(0)
    p["cloak"] = False; p["tail"] = False; p["clip"] = False
    p["hood"].update(wire=True, a=200)
    p["emblem"]["show"] = False
    for i in range(len(BARS)):
        o = p["bars"][i]
        o["dx"] = (7 if i % 2 == 0 else -7); o["lit"] = set(); o["h"] = 3; o["a"] = 170
    p["hands"] = [None, None]
    p["empty"] = set(range(11, 90, 4))
    p["pixels"] = []
    im = render(p)
    for y in range(40, 78):
        if y % 2 == 0:
            px(im, 48, y, A(CN[5], 160))
    frames.append(im)
    # 3: bars snap towards their places, half lit; hood filled but full of empty lines
    p = float_pose(0)
    p["tail"] = False; p["clip"] = False
    p["hood"].update(eyes="blink", a=210)
    for i in range(len(BARS)):
        o = p["bars"][i]
        o["dx"] = (-2 if i % 2 == 0 else 2); o["a"] = 200
    p["hands"][0]["a"] = 130; p["hands"][1]["a"] = 130
    p["empty"] = set(range(12, 90, 3))
    p["chroma"] = [(2, PK[2], 150, None)]
    p["pixels"] = []
    frames.append(render(p))
    # 4: overbright snap-on
    p = float_pose(0)
    p["hood"].update(eyes="wide")
    for i in range(len(BARS)):
        p["bars"][i]["bright"] = 2
        p["bars"][i]["lit"] = set(range(8))
    p["emblem"]["pulse"] = 1
    p["tint"] = (WHITE, 0.35)
    p["empty"] = {30, 61}
    p["chroma"] = [(-1, PK[2], 170, None), (1, CN[5], 120, None)]
    p["pixels"] = sparkle(26, 30, WHITE, True) + sparkle(70, 62, WHITE, True) + [(22, 46, PK[3]), (73, 34, PK[3]), (64, 76, CN[5])]
    frames.append(render(p))
    # 5: settled (leads straight into float)
    p = float_pose(0)
    p["emblem"]["pulse"] = 1
    p["bars"][1]["bright"] = 1; p["bars"][0]["bright"] = 1
    p["empty"] = {70}
    p["pixels"] = spark_px(RH[0], p["hands"][1]["y"] - 7, 0)[:2] + [(27, 36, A(CN[5], 200)), (69, 62, A(PK[3], 180))]
    frames.append(render(p))
    return frames


# ---- defeat: the whole figure resolves into separate fraction bars that drift apart ------
HOOD_BAR_SET = (NV[6], NV[5], NV[4])


def _pieces():
    """Every part of the figure as a free bar: (kind, x, y (top-left of bar), W, h, n, lit, style, drift)."""
    rnd = random.Random(11)
    pcs = []
    p = float_pose(0)
    hx = 48 - HOOD_CX
    # hood + cowl re-expressed as bars (the eye cells stay lit the longest)
    hood_rows = [(0, 11, 2, {0, 1}, 5), (5, 17, 4, {0, 1}, 9), (10, 25, 4, {0, 1, 2}, 13), (15, 25, 8, {2, 5}, 13),
                 (20, 25, 4, {0}, 13), (25, 33, 4, {0, 1}, 13), (30, 33, 8, {0, 1, 2, 3, 4}, 13)]
    for k, (r, W, n, lit, cxl) in enumerate(hood_rows):
        side = -1 if k % 2 == 0 else 1
        pcs.append(dict(x=hx + cxl - W // 2, y=HOOD_Y + r, W=W, h=4, n=n, lit=lit, style="hood" if k != 3 else "eyes",
                        vx=side * rnd.uniform(7, 13), vy=(HOOD_Y + r - 48) * 0.18 + rnd.uniform(-1, 1), delay=rnd.uniform(0, 0.18),
                        lead=side))
    for i, (b, fr) in enumerate(zip(BARS, BAR_FRAC)):
        n = fr["dens"][0]
        side = 1 if i % 2 == 0 else -1
        cx = body_cx(b["y"] + 2, p)
        pcs.append(dict(x=int(round(cx)) - b["W"] // 2, y=b["y"], W=b["W"], h=b["h"], n=n,
                        lit=lit_cells(fr["num"], fr["den"], n, fr["side"]), style="bar",
                        vx=side * rnd.uniform(7, 13), vy=(b["y"] - 48) * 0.22 + rnd.uniform(-1, 1), delay=rnd.uniform(0, 0.18),
                        lead=side))
    for k, (y, dx, W, h, n, lit, ph) in enumerate(TAIL):
        cx = body_cx(y + 1, p) + dx
        pcs.append(dict(x=int(round(cx)) - W // 2, y=y, W=W, h=h, n=n, lit=lit, style="tail%d" % k,
                        vx=rnd.uniform(-8, 2), vy=rnd.uniform(0, 2), delay=0.0, lead=-1))
    return pcs


def _draw_piece(img, pc, s, e, flash=0):
    shed = max(0.0, min(1.0, (s - 0.12 - pc["delay"]) / 0.72))
    n = pc["n"]; W = pc["W"]; h = pc["h"]
    cw = (W - 1) // n
    m = int(math.ceil(n * (1.0 - shed) - 1e-6))
    if m <= 0:
        return
    keep = list(range(m)) if pc["lead"] < 0 else list(range(n - m, n))     # trailing cells are shed first
    Wm = m * cw + 1
    x0 = pc["x"] + (0 if pc["lead"] < 0 else (n - m) * cw)
    lit = set(c - keep[0] for c in pc["lit"] if c in keep)
    a = 235 * (1.0 - 0.80 * s ** 1.5)
    x = x0 + pc["vx"] * e; y = pc["y"] + pc["vy"] * e
    tmp = new(Wm + 2, h + 2)
    st = pc["style"]
    kw = {}
    if st == "hood":
        kw = dict(tint=HOOD_BAR_SET, hollow=NV[1])
    elif st == "eyes":
        kw = dict(tint=(WHITE, WHITE, CN[5]), hollow=IK[1])
    elif st.startswith("tail"):
        kw = dict(tint=TAIL_TINT[int(st[4:])], frame=FRAME_PU)
    if Wm <= 3:
        rect(tmp, 1, 1, Wm, h, A(PK[3], 235))
    else:
        frac_bar(tmp, 1 + Wm // 2, 1, Wm, h, m, lit, a=235, body_cx=1 + Wm // 2 + (48 - (pc["x"] + W // 2)),
                 bright=flash, **kw)
    tmp = outline(tmp, A(IK[0], 235))
    if flash:
        tmp = tint_img(tmp, WHITE, 0.3)
    tmp = tint_alpha(tmp, a / 235.0)
    paste(img, tmp, int(round(x)) - 1, int(round(y)) - 1)


def anim_defeat():
    frames = []
    # 0: struck - white flash, bars thrown sideways
    p = float_pose(0)
    p["hood"].update(eyes="wide", shear=-0.08)
    for i in range(len(BARS)):
        p["bars"][i].update(dx=[6, -5, 6, -5, 4, -4][i], noclip=True, bright=2)
    p["tint"] = (WHITE, 0.6)
    p["hands"][0] = dict(kind="open", x=14, y=50, flip=True)
    p["hands"][1] = dict(kind="open", x=83, y=40)
    p["empty"] = set()
    p["glitch"] = [(18, 22, -4), (29, 32, 4), (64, 67, -3)]
    p["chroma"] = [(2, PK[2], 210, None), (-2, PU[4], 180, None)]
    p["pixels"] = sparkle(30, 24, WHITE, True) + sparkle(70, 58, WHITE, True) + [(24, 40, PK[3]), (74, 28, PK[3]), (66, 74, PK[4])]
    frames.append(render(p))
    # 1: destabilised - slices torn in both directions, pink/purple split
    p = float_pose(2)
    p["hood"].update(eyes="x", shear=0.06)
    for i in range(len(BARS)):
        p["bars"][i].update(dx=[-7, 6, -6, 7, -5, 5][i], noclip=True, cell_tint={0: PINK_SET} if i % 2 else {})
    p["cloak"] = False
    p["tint"] = (PK[3], 0.22)
    p["hands"][0] = dict(kind="open", x=13, y=54, flip=True)
    p["hands"][1] = dict(kind="open", x=84, y=37)
    p["empty"] = {21, 22, 37, 55, 72}
    p["glitch"] = [(10, 14, 4), (15, 19, -3), (24, 28, 5), (33, 36, -4)]
    p["chroma"] = [(-2, PK[2], 200, None), (2, PU[4], 160, None)]
    p["emblem"]["pulse"] = 1
    p["pixels"] = sparkle(48, 46, WHITE, True) + [(20, 30, PK[3]), (78, 60, PK[3]), (40, 84, PU[4]), (62, 16, WHITE)]
    frames.append(render(p))
    # 2..8: everything is now a bar; bars drift apart, shed their cells and fade
    pcs = _pieces()
    wedges = [(-1, -1, -9, -7), (-1, 1, -7, 9), (1, 1, 10, 7)]       # three quarters of the emblem
    hands0 = [("open", 13, 54, True, -4, 7), ("open", 84, 37, False, 4, -7)]
    for k in range(7):
        s = (k + 1) / 8.0                 # 0.125 .. 0.875
        e = 1 - (1 - s) ** 2.0            # ease-out drift
        img = new(FW, FH)
        for pc in pcs:
            _draw_piece(img, pc, s, e, flash=2 if k == 0 else 0)
        # emblem wedges
        wa = 1.0 if s < 0.5 else max(0.0, 1 - (s - 0.5) / 0.42)
        if wa > 0:
            em = new(19, 19)
            emblem(em, 9, 9, 6, "normal", 1 if k == 0 else 0, 0, socket=False)
            for (qx, qy, vx, vy) in wedges:
                box = (2 if qx < 0 else 10, 2 if qy < 0 else 10, 9 if qx < 0 else 17, 9 if qy < 0 else 17)
                w0 = em.crop(box)
                w1 = new(w0.width + 2, w0.height + 2); w1.alpha_composite(w0, (1, 1))
                w1 = tint_alpha(outline(w1, A(IK[0], 235)), wa)
                paste(img, w1, int(round(48 - 9 + box[0] - 1 + vx * e)), int(round(46 - 9 + box[1] - 1 + vy * e)))
        # hands let go and fade
        ha = max(0.0, 1 - s / 0.7)
        if ha > 0:
            for kind, x, y, flip, vx, vy in hands0:
                hs = hand_sprite(kind, flip, a=int(235 * ha))
                paste(img, hs, int(round(x + vx * e - hs.width / 2)), int(round(y + vy * e - hs.height / 2)))
        img = aura(img, CN[3], 70)
        img = holo_fx(img, scan=k, empty={(23 + k * 13) % 90})
        if k < 2:
            img = chroma(img, 1 if k % 2 else -1, PK[2], 150 - k * 50)
        rnd = random.Random(40 + k)
        for _ in range(max(2, 10 - k)):
            ang = rnd.uniform(0, 6.283); d = 10 + e * rnd.uniform(14, 34)
            c = rnd.choice([PK[3], PK[2], CN[5], WHITE, PU[4]])
            px(img, int(48 + math.cos(ang) * d), int(46 + math.sin(ang) * d * 0.9), A(c, int(230 * (1 - s * 0.75))))
        frames.append(img)
    # 9: gone
    frames.append(new(FW, FH))
    return frames


# =============================================================================
# 7. HOLO BUST (48x48): a small cyan projection of the Phantom's head and shoulders
# =============================================================================
MONO = [CN[0], CN[1], CN[2], CN[3], CN[4], CN[5], CN[6]]


def to_mono(img, lift=0):
    """Re-colour to the single-hue cyan of a cheap projection."""
    out = img.copy(); p = out.load()
    for y in range(img.height):
        for x in range(img.width):
            c = p[x, y]
            if not c[3]:
                continue
            if c[:3] == WHITE[:3]:
                continue
            lum = (0.3 * c[0] + 0.5 * c[1] + 0.2 * c[2]) / 255.0
            i = int(round(lum * 6.4 + 0.6)) + lift
            m = MONO[max(0, min(6, i))]
            p[x, y] = (m[0], m[1], m[2], c[3])
    return out


def holo_frame(f):
    img = new(48, 48)
    eyes = ["calm", "calm", "calm", "narrow", "narrow", "calm"][f]
    # two bars under the cowl, fading into the projector beam
    for i, (y, W) in enumerate(((37, 29), (43, 25))):
        n = [2, 4][(f // 3 + i) % 2] if i == 0 else 4
        frac_bar(img, 24, y, W, 5, n, lit_cells(1, 2, n, i) if i == 0 else {0}, a=220 - i * 50, body_cx=24)
    hd = hood_layer(eyes)
    img.alpha_composite(hd, (24 - HOOD_CX - HOOD_PAD, 3))
    emblem(img, 24, 39, 5, "normal", 1 if f == 4 else 0, f // 2)
    img = outline(img, A(IK[0], 220))
    img = to_mono(img, lift=1 if f == 4 else 0)
    img = aura(img, CN[3], 90)
    # projection look: strong scanlines (eyes stay solid), beam fade at the bottom
    p = img.load()
    for y in range(48):
        for x in range(48):
            c = p[x, y]
            if not c[3]:
                continue
            a = c[3] * (0.66 if (y + f) % 2 == 0 and c[:3] != WHITE[:3] else 0.95)
            if y >= 41:
                a *= max(0.0, (48 - y) / 8.0)
                if (x + y) % 2 == 0 and y >= 44:
                    a = 0
            p[x, y] = (c[0], c[1], c[2], int(a))
    base = [1.0, 0.9, 1.0, 0.72, 1.0, 0.85][f]
    if base < 1:
        img = tint_alpha(img, base)
    if f == 2:
        img = glitch(img, [(15, 19, 3), (20, 21, -2)])
        img = chroma(img, -1, PK[2], 150, set(range(13, 23)))
    if f == 3:
        img = holo_fx(img, empty={10, 11, 28, 34}, dim_rows=0)
    if f == 5:
        img = glitch(img, [(29, 32, -2), (7, 9, 2)])
        img = chroma(img, 1, PK[2], 130, set(range(27, 34)))
    return img


def anim_holo():
    return [holo_frame(f) for f in range(6)]


# =============================================================================
# 8. BUILD
# =============================================================================
def strip_preview(frames, name, scale=4, cols=None):
    preview(sheet(frames, cols=cols or len(frames)), name, scale=scale, bg=BG, grid=(frames[0].width, frames[0].height))


def boss_room(Wt=22, Ht=11):
    """A little slice of the boss arena built from the real tiles (None if tiles are not built yet)."""
    path = os.path.join(ASSETS, "tiles/tiles_boss.png")
    if not os.path.exists(path):
        return None
    til = Image.open(path).convert("RGBA")

    def tile(i):
        return til.crop(((i % 16) * 16, (i // 16) * 16, (i % 16) * 16 + 16, (i // 16) * 16 + 16))
    img = new(Wt * 16, Ht * 16, hexc("#05060c"))
    for y in range(Ht):
        for x in range(Wt):
            t = 48 + (1 if (x + y) % 5 == 0 else 2 if y % 6 == 2 else 0)
            if x in (3, 18) and y < 9:
                t = 56
            if y == 4 and 8 <= x <= 13:
                t = 51
            if (x, y) in ((6, 2), (15, 2)):
                t = 67
            if x in (10, 11) and y in (1, 2):
                t = 54
            img.alpha_composite(tile(t), (x * 16, y * 16))
    for x in range(Wt):
        img.alpha_composite(tile(20 if x % 7 == 3 else 14), (x * 16, (Ht - 2) * 16))
        img.alpha_composite(tile(15), (x * 16, (Ht - 1) * 16))
    for i, x in enumerate(range(8, 12)):
        img.alpha_composite(tile(32 if i == 0 else 34 if i == 3 else 33), (x * 16 + 96, 6 * 16))
    jp = os.path.join(ASSETS, "sprites/jake.png")
    if os.path.exists(jp):
        jk = Image.open(jp).convert("RGBA").crop((0, 0, 32, 32))
        img.alpha_composite(jk, (16, (Ht - 2) * 16 - 31))
    return img


def context_preview(frames):
    """Phantom (and Jake for scale) over the real boss-arena tiles, at game zoom."""
    img = boss_room()
    if img is None:
        return
    img.alpha_composite(frames["float"][0], (40, 24))
    img.alpha_composite(frames["attack"][2], (140, 16))
    img.alpha_composite(frames["stunned"][1], (250, 50))
    preview(img, "phantom_ctx.png", scale=3, bg="#05060c")
    img = boss_room()
    img.alpha_composite(frames["hurt"][0], (30, 30))
    img.alpha_composite(frames["defeat"][3], (130, 24))
    img.alpha_composite(frames["appear"][3], (240, 30))
    preview(img, "phantom_ctx2.png", scale=3, bg="#05060c")


def build():
    groups = [
        ("appear", anim_appear(), 10, False),
        ("float", anim_float(), 8, True),
        ("attack", anim_attack(), 10, False),
        ("hurt", anim_hurt(), 12, False),
        ("stunned", anim_stunned(), 6, True),
        ("defeat", anim_defeat(), 8, False),
    ]
    frames = []; anims = {}; byname = {}
    for name, fr, fps, loop in groups:
        start = len(frames)
        frames += fr
        byname[name] = fr
        anims[name] = {"frames": list(range(start, len(frames))), "fps": fps, "loop": loop}
    sh = sheet(frames, cols=8)
    save(sh, "sprites/phantom.png")
    holo = anim_holo()
    save(sheet(holo, cols=6), "sprites/phantom_holo.png")
    manifest("phantom", {
        "sheets": {
            "phantom": {"file": "sprites/phantom.png", "fw": FW, "fh": FH, "anims": anims},
            "phantom_holo": {"file": "sprites/phantom_holo.png", "fw": 48, "fh": 48,
                             "anims": {"flicker": {"frames": list(range(6)), "fps": 10, "loop": True}}},
        },
        # extra hints for the game code (frame-local pixels, sprite facing right)
        "phantomMeta": {
            "facing": "right",
            "bodyCentre": [48, 48],
            "stunnedCore": {"x": 48, "y": CORE_Y, "r": CORE_R},
            "castHand": {"x": 90, "y": 45, "releaseFrame": anims["attack"]["frames"][2]},
            "emblem": {"x": 48, "y": 46, "r": 6},
        },
    })
    # ---- previews --------------------------------------------------------------
    preview(byname["float"][0], "phantom_big.png", scale=8, bg=BG)
    preview(sh, "phantom_sheet.png", scale=2, bg=BG, grid=(FW, FH))
    for name, fr, fps, loop in groups:
        if len(fr) <= 4:
            strip_preview(fr, f"phantom_{name}.png")
        else:
            half = (len(fr) + 1) // 2
            strip_preview(fr[:half], f"phantom_{name}_a.png")
            strip_preview(fr[half:], f"phantom_{name}_b.png")
    strip_preview(holo, "phantom_holo.png", scale=5)
    preview(sheet([byname["float"][0], byname["attack"][1], byname["attack"][2], byname["stunned"][1]]),
            "phantom_keys.png", scale=5, bg=BG)
    context_preview(byname)
    return frames, anims


if __name__ == "__main__":
    fr, an = build()
    print(len(fr), "frames", {k: v["frames"] for k, v in an.items()})
