"""
fx.py - collectibles, effects and lighting for Math Blast Arcade (manifest part "fx").

Sheets : quarter, starcell, qkey, missingq, heart, fx_poof, fx_boom, fx_ring, fx_spark,
         fx_dust, fx_star, fx_collect, fx_debris
Images : glow, glow_soft, lightcone, vignette, pixel

Re-run with:  cd art && python3 fx.py
Previews go to art/_preview/fx_*.png
"""
import math, random
from pix import *
import tiles

GOLD = ramp("gold")
CY = ramp("cyan")
ST = ramp("steel")
OR = ramp("orange")
RD = ramp("red")
NV = ramp("navy")
PK = ramp("pink")
WHITE = C["white"]


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def A(c, a):
    return (c[0], c[1], c[2], int(a))


def mask_new(w, h, fn):
    """Boolean mask sampled at pixel centres."""
    return [[bool(fn(x + 0.5, y + 0.5)) for x in range(w)] for y in range(h)]


def m_get(m, x, y):
    return 0 <= y < len(m) and 0 <= x < len(m[0]) and m[y][x]


def m_erode(m, n=1):
    for _ in range(n):
        m = [[m[y][x] and m_get(m, x - 1, y) and m_get(m, x + 1, y) and m_get(m, x, y - 1) and m_get(m, x, y + 1)
              for x in range(len(m[0]))] for y in range(len(m))]
    return m


def m_shift(m, dx, dy):
    h, w = len(m), len(m[0])
    return [[m_get(m, x - dx, y - dy) for x in range(w)] for y in range(h)]


def m_paint(img, m, c):
    for y in range(len(m)):
        for x in range(len(m[0])):
            if m[y][x]:
                img.putpixel((x, y), c)


def lighten(c, rmp, n=1, top=WHITE):
    """Move a colour n steps up its ramp (white past the end)."""
    if c in rmp:
        i = rmp.index(c) + n
        return rmp[i] if i < len(rmp) else top
    return c


def sparkle(img, x, y, size, core=WHITE, arm=None, tip=None):
    """4-point pixel glint. size 0 = dot, 1 = plus, 2 = long plus, 3 = long plus + diagonals."""
    arm = arm or core
    tip = tip or arm
    if size >= 3:
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            px(img, x + dx, y + dy, tip)
    if size >= 2:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            px(img, x + dx * size, y + dy * size, tip)
            for k in range(1, size):
                px(img, x + dx * k, y + dy * k, arm)
    elif size == 1:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            px(img, x + dx, y + dy, arm)
    px(img, x, y, core)


def wedge_fn(ax, ay, R, s=1.0, piv=None, p=2.0):
    """Quarter-disc: apex (circle centre) at (ax, ay), extending right and UP. s squashes X about piv.
    p > 2 fattens the arc slightly (superellipse) so it still reads as ROUND at tiny sizes."""
    piv = ax + R / 2.0 if piv is None else piv

    def fn(x, y):
        mx = (x - piv) / s + (piv - ax)
        my = ay - y
        return mx >= 0 and my >= 0 and mx ** p + my ** p <= R ** p
    return fn


def wedge_r(mx, my, p=2.0):
    """Radius in the same (superellipse) metric as wedge_fn."""
    return (max(mx, 0.0) ** p + max(my, 0.0) ** p) ** (1.0 / p)


# ----------------------------------------------------------------------------
# QUARTER  16x16, spin: 8 frames
# ----------------------------------------------------------------------------
QUARTER_TILT = [0, 20, 34, 20, 0, -20, -34, -20]
QP = 2.35


def quarter_frame(i, R=13, ax=1, ay=14):
    """A quarter cut from a gold coin: raised rim along the arc only, flat cut edges."""
    W = H = 16
    img = new(W, H)
    th = math.radians(QUARTER_TILT[i])
    s = math.cos(th)
    piv = ax + R / 2.0
    face = mask_new(W, H, wedge_fn(ax, ay, R, s, piv, QP))
    sx = int(round(math.sin(th) * 1.6))          # which way the chip's edge shows: -1, 0, +1
    if sx:
        m_paint(img, m_shift(face, sx, 0), GOLD[1] if sx > 0 else GOLD[4])
    for y in range(H):
        for x in range(W):
            if not face[y][x]:
                continue
            up = not m_get(face, x, y - 1)
            lf = not m_get(face, x - 1, y)
            rt = not m_get(face, x + 1, y)
            dn = not m_get(face, x, y + 1)
            mx = (x + 0.5 - piv) / s + (piv - ax)
            my = ay - (y + 0.5)
            r = wedge_r(mx, my, QP)
            ang = math.degrees(math.atan2(my, mx))
            if dn:
                c = GOLD[1]
            elif lf:
                c = WHITE if up else GOLD[5]
            elif up or rt:                        # crest of the raised rim
                c = WHITE if ang > 74 else GOLD[5] if ang > 40 else GOLD[4] if ang > 16 else GOLD[3]
            elif r > R - 2.5:                     # rim band
                c = GOLD[4] if ang > 12 else GOLD[3]
            elif r > R - 3.7 and mx > 1.2:        # groove inside the rim
                c = GOLD[2] if my > 2 else GOLD[1]
            else:
                c = GOLD[3]
                if my < 2:
                    c = GOLD[2]                   # shadow above the bottom cut edge
                elif 2.2 < mx < 3.4 and 3.6 < my < 7.4 and s > 0.9:
                    c = GOLD[4]                   # small standing highlight on the face
            img.putpixel((x, y), c)
    # travelling shine band (a "/" streak moving top-left -> bottom-right)
    band = {2: 5, 3: 11, 4: 17, 5: 23}.get(i)
    if band is not None:
        for y in range(H):
            for x in range(W):
                if face[y][x] and m_get(face, x, y + 1):
                    d = (x - ax) + (y - (ay - R)) - band
                    if d in (0, 1):
                        img.putpixel((x, y), lighten(img.getpixel((x, y)), GOLD, 3))
                    elif d in (-1, 2):
                        img.putpixel((x, y), lighten(img.getpixel((x, y)), GOLD, 1))
    img = outline(img, OUT)
    g = {5: 1, 6: 2, 7: 1}.get(i)
    if g:
        gx = int(round(piv + (ax + R * 0.70 - piv) * s))
        sparkle(img, gx, ay - int(R * 0.70) - 1, g, WHITE, WHITE, GOLD[5])
    return img, face


def build_quarter():
    return [quarter_frame(i)[0] for i in range(8)]


# ----------------------------------------------------------------------------
# STARCELL  16x16, spin: 8 frames  (gold star tumbling inside a cyan glass capsule)
# ----------------------------------------------------------------------------
STAR7 = ["...a...",
         "...a...",
         "aaabbbb",
         ".abbbc.",
         "..bbc..",
         ".bb.cc.",
         ".b...c."]


def star_sprite(w, back=False):
    """7x7 star squashed to width w (1,3,5,7) about its centre column."""
    cm = {"a": GOLD[4], "b": GOLD[3], "c": GOLD[2]}
    if back:
        cm = {"a": GOLD[3], "b": GOLD[2], "c": GOLD[1]}
    img = new(7, 7)
    half = w // 2
    for y, row in enumerate(STAR7):
        for dx in range(-half, half + 1):
            sxc = 3 + (int(round(dx * 3.0 / half)) if half else 0)
            ch = row[sxc]
            if w == 1:
                ch = "a" if y < 5 else "."
            if ch != ".":
                img.putpixel((3 + dx, y), cm[ch])
    return img


def starcell_frame(i):
    img = new(16, 16)
    # rounded pill: steel end-domes (rows 1-2, 13-14), glass tube between. x 3..11
    rows = {1: (5, 9), 2: (4, 10), 13: (4, 10), 14: (5, 9)}
    for y in range(3, 13):
        rows[y] = (3, 11)
    for y, (x0, x1) in rows.items():
        for x in range(x0, x1 + 1):
            if y <= 2:                                         # top dome
                c = ST[7] if (y == 1 or x == x0) else ST[5]
                if x == x1:
                    c = ST[4]
            elif y >= 13:                                      # bottom dome
                c = ST[4] if y == 13 else ST[2]
                if x == x0:
                    c = ST[5]
                if x == x1:
                    c = ST[2]
            else:                                              # glass
                c = CY[1]
                if x == x0:
                    c = CY[4]
                elif x == x0 + 1:
                    c = CY[2]
                elif x == x1:
                    c = CY[2]                                  # thin rim light on the far wall
                if y == 3:
                    c = CY[0] if x > x0 else CY[2]             # shadow under the cap
                if y == 12 and x0 < x < x1:
                    c = CY[2]                                  # light pooling at the bottom
            img.putpixel((x, y), c)
    px(img, 7, 2, CY[4]); px(img, 7, 13, CY[3])                # status lights on the caps
    hline(img, 5, 9, 12, CY[3]); px(img, 10, 12, CY[2])
    # star: half-turn over 8 frames (the star is symmetric, so the loop is seamless)
    w = {0: 7, 1: 7, 2: 5, 3: 3, 4: 1, 5: 3, 6: 5, 7: 7}[i]
    st = star_sprite(w)
    if i in (5, 6, 7):
        st = flip_h(st)
    sy = 4
    # glow behind the star (a soft diamond, visible when the star turns edge-on)
    for gy in range(4, 11):
        for gx in range(4, 11):
            if abs(gx - 7) + abs(gy - 7) <= 3 and get(img, gx, gy) == CY[1]:
                px(img, gx, gy, CY[2])
    paste(img, st, 4, sy)
    if i in (0, 1, 7):
        px(img, 7, sy, WHITE)
    if i == 4:                                                 # edge-on: a bright "ting"
        sparkle(img, 7, sy + 2, 2, WHITE, GOLD[5], GOLD[4])
    elif i in (3, 5):
        sparkle(img, 7, sy + 2, 1, WHITE, GOLD[5], GOLD[4])
    # glass reflection streak slides down the tube
    hy = 4 + [0, 0, 1, 2, 3, 4, 5, 6][i]
    for k in range(3):
        if hy + k <= 11:
            px(img, 4, hy + k, CY[6] if k == 0 else CY[5])
    return outline(img, OUT)


def build_starcell():
    return [starcell_frame(i) for i in range(8)]


# ----------------------------------------------------------------------------
# QKEY  24x24, glow: 6 frames  (cyan quarter-wedge power cell)
# ----------------------------------------------------------------------------
BOLT = ["...www",
        "..www.",
        ".www..",
        "wwwwww",
        "..www.",
        ".www..",
        "www..."]


def halo(img, mask_img, colour, a1, a2=0):
    """1-2px soft glow outside an (already outlined) sprite. FX-only translucency."""
    w, h = img.size
    src = mask_img.load()
    out = img.copy()

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and src[x, y][3] > 200
    for y in range(h):
        for x in range(w):
            if solid(x, y):
                continue
            d1 = any(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            d2 = any(solid(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (1, 1), (-1, 1), (1, -1), (-1, -1)))
            if d1 and a1:
                out.putpixel((x, y), A(colour, a1))
            elif d2 and a2:
                out.putpixel((x, y), A(colour, a2))
    return out


def qkey_frame(i):
    W = H = 24
    R, ax, ay = 18, 3, 21
    P = 2.25
    img = new(W, H)
    face = mask_new(W, H, wedge_fn(ax, ay, R, 1.0, None, P))
    in1 = m_erode(face, 1)
    in2 = m_erode(face, 2)
    in3 = m_erode(face, 3)
    pulse = [0.0, 0.35, 0.8, 1.0, 0.6, 0.2][i]
    for y in range(H):
        for x in range(W):
            if not face[y][x]:
                continue
            mx = x + 0.5 - ax
            my = ay - (y + 0.5)
            ang = math.degrees(math.atan2(my, mx))
            if not in1[y][x]:                                   # casing, outer edge
                lit = not m_get(face, x - 1, y) or not m_get(face, x, y - 1)
                c = ST[7] if lit and ang > 38 else ST[6] if lit else ST[3]
                if not m_get(face, x, y + 1):
                    c = ST[2]
                if not m_get(face, x - 1, y):
                    c = ST[7]
            elif not in2[y][x]:                                 # casing, inner edge
                lit = not m_get(in1, x - 1, y) or not m_get(in1, x, y - 1)
                c = ST[5] if lit else ST[4]
                if not m_get(in1, x, y + 1):
                    c = ST[3]
            else:                                               # glass + energy (breathes with the pulse)
                lvl = 1 if pulse > 0.7 else 0
                c = CY[3 + lvl]
                if not in3[y][x]:
                    sh = not m_get(in2, x - 1, y) or not m_get(in2, x, y - 1)
                    c = CY[1] if sh else CY[4 + lvl]            # shadow under the frame / lit far edge
                elif not m_get(in3, x - 1, y) or not m_get(in3, x, y - 1):
                    c = CY[2 + lvl]
            img.putpixel((x, y), c)
    # clamp bands across the casing (battery-segment feel)
    for a in (22, 68):
        for rr in (R - 0.6, R - 1.6):
            cxp = ax + rr * math.cos(math.radians(a))
            cyp = ay - rr * math.sin(math.radians(a))
            xi, yi = int(cxp), int(cyp)
            if m_get(face, xi, yi) and not in2[yi][xi]:
                img.putpixel((xi, yi), ST[2] if rr < R - 1 else ST[4])
    # hub at the apex where four cells meet: steel collar + gold contact
    hub = mask_new(W, H, wedge_fn(ax + 1, ay - 1, 5.3, 1.0, None, 2.0))
    hub2 = mask_new(W, H, wedge_fn(ax + 1, ay - 1, 3.3, 1.0, None, 2.0))
    for y in range(H):
        for x in range(W):
            if hub[y][x] and in1[y][x]:
                edge = not m_get(hub, x + 1, y) or not m_get(hub, x, y - 1)
                img.putpixel((x, y), ST[2] if edge else ST[5])
            if hub2[y][x] and in1[y][x]:
                e2 = not m_get(hub2, x + 1, y) or not m_get(hub2, x, y - 1)
                img.putpixel((x, y), GOLD[2] if e2 else GOLD[3])
    px(img, ax + 1, ay - 3, GOLD[5]); px(img, ax + 1, ay - 2, GOLD[4])
    # bolt glyph: chunky white bolt with a dark teal keyline so it reads at 1x
    bx, by = ax + 5, ay - 13
    bolt = ascii_sprite(BOLT, {"w": WHITE if pulse > 0.3 else CY[6]})
    paste(img, outline(_pad(bolt, 1), CY[1]), bx - 1, by - 1)
    if pulse > 0.7:
        px(img, bx + 7, by - 1, WHITE); px(img, bx - 1, by + 8, CY[6])
    # glass highlight
    for (hx, hy) in ((ax + 4, ay - 14), (ax + 3, ay - 13), (ax + 3, ay - 12)):
        if in3[hy][hx]:
            px(img, hx, hy, CY[6])
    out = outline(img, OUT)
    out = halo(out, out, CY[4], int(85 * pulse), 0)
    return out


def _pad(img, n):
    out = new(img.width + 2 * n, img.height + 2 * n)
    out.alpha_composite(img, (n, n))
    return out


def build_qkey():
    return [qkey_frame(i) for i in range(6)]


# ----------------------------------------------------------------------------
# MISSINGQ  32x32, glow: 8 frames  (THE Missing Quarter)
# ----------------------------------------------------------------------------
def ray_burst(img, cx, cy, rot, n, r0, r1, w0, near, far, split=0.55):
    """n tapered rays (triangles) around (cx,cy), rotated by rot radians. Chunky, no AA."""
    per = 2 * math.pi / n
    for y in range(img.height):
        for x in range(img.width):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            r = math.hypot(dx, dy)
            if r < r0 or r > r1:
                continue
            a = (math.atan2(dy, dx) - rot) % per
            a = min(a, per - a)                     # angular distance to the nearest ray axis
            f = (r - r0) / (r1 - r0)
            halfw = w0 * (1.0 - f) + 0.35
            if a * r <= halfw:
                px(img, x, y, near if f < split else far)


def missingq_frame(i, emblem=False):
    W = H = 32
    R, ax, ay = 16, 8, 24
    P = 2.25
    ph = i / 8.0 * 2 * math.pi
    body = new(W, H)
    face = mask_new(W, H, wedge_fn(ax, ay, R, 1.0, None, P))
    for y in range(H):
        for x in range(W):
            if not face[y][x]:
                continue
            up = not m_get(face, x, y - 1)
            lf = not m_get(face, x - 1, y)
            rt = not m_get(face, x + 1, y)
            dn = not m_get(face, x, y + 1)
            mx = x + 0.5 - ax
            my = ay - (y + 0.5)
            r = wedge_r(mx, my, P)
            ang = math.degrees(math.atan2(my, mx))
            if dn:
                c = GOLD[1]
            elif lf:
                c = WHITE if up or my > R - 5 else GOLD[5]
            elif up or rt:
                c = WHITE if ang > 62 else GOLD[5] if ang > 34 else GOLD[4] if ang > 12 else GOLD[3]
            elif r > R - 3.3:                                   # raised rim band
                c = GOLD[4] if ang > 9 else GOLD[3]
            elif r > R - 4.5 and mx > 1.5:                      # groove
                c = GOLD[2] if my > 2.2 else GOLD[1]
            elif mx < 2:
                c = GOLD[4]                                     # inner bevel of the lit cut edge
            elif my < 2.2:
                c = GOLD[2]
            else:
                c = GOLD[3]
                if 2.2 < mx < 4.2 and 5.0 < my < 9.6:
                    c = GOLD[4]                                 # standing highlight
                if 2.2 < mx < 3.2 and 7.0 < my < 9.6:
                    c = GOLD[5]
            body.putpixel((x, y), c)
    if emblem:
        # embossed 4-point star on the face
        ex, ey = ax + 6, ay - 7
        star = [(0, -3), (0, -2), (0, -1), (0, 0), (0, 1), (0, 2), (0, 3), (-3, 0), (-2, 0), (-1, 0), (1, 0), (2, 0), (3, 0)]
        for (sx_, sy_) in ((1, -2), (1, -1), (2, 1), (3, 1), (1, 1), (1, 2), (1, 3), (0, 4), (-2, 1), (-3, 1), (-1, 1)):
            px(body, ex + sx_, ey + sy_, GOLD[2])
        for (sx_, sy_) in star:
            px(body, ex + sx_, ey + sy_, GOLD[5] if (abs(sx_) + abs(sy_)) > 1 else WHITE)
    # shine sweep
    band = {1: 3, 2: 9, 3: 15, 4: 21, 5: 27}.get(i)
    if band is not None:
        for y in range(H):
            for x in range(W):
                if face[y][x] and m_get(face, x, y + 1):
                    d = (x - ax) + (y - (ay - R)) - band
                    if d in (0, 1, 2):
                        body.putpixel((x, y), lighten(body.getpixel((x, y)), GOLD, 3 if d == 1 else 2))
                    elif d in (-1, 3):
                        body.putpixel((x, y), lighten(body.getpixel((x, y)), GOLD, 1))
    body = outline(body, OUT)

    img = new(W, H)
    cx, cy = 16.0, 16.0
    rot = i / 8.0 * (2 * math.pi / 8)
    L = 19.0 + 1.5 * math.sin(ph)
    ray_burst(img, cx, cy, rot, 8, 4.0, L, 2.7, A(GOLD[2], 240), A(GOLD[1], 200), split=0.62)
    ray_burst(img, cx, cy, rot, 8, 4.0, L - 5.0, 1.2, A(GOLD[3], 255), A(GOLD[3], 255))
    ray_burst(img, cx, cy, rot + math.pi / 8, 8, 4.0, L - 7.0, 1.0, A(GOLD[4], 230), A(GOLD[2], 200))
    img.alpha_composite(body)
    # twinkles
    for k, (tx, ty) in enumerate(((24, 6), (4, 11), (27, 24), (11, 3))):
        st = [0, 1, 2, 3, 2, 1, -1, -1][(i + k * 3) % 8]
        if st >= 0:
            sparkle(img, tx, ty, min(st, 2) if k else st, WHITE, WHITE, GOLD[4])
    return img


def build_missingq():
    return [missingq_frame(i) for i in range(8)]


# ----------------------------------------------------------------------------
# HEART  16x16, beat: 4 frames
# ----------------------------------------------------------------------------
HEART_CM = {"k": OUT, "W": WHITE, "h": RD[4], "r": RD[3], "d": RD[2], "D": RD[1], "p": RD[5]}
HEART_N = ["..kkk...kkk..",
           ".khhrk.khrrk.",
           "khWWrrkrrrrdk",
           "khWrrrrrrrrdk",
           "khrrrrrrrrddk",
           "krrrrrrrrrddk",
           ".krrrrrrrddk.",
           "..krrrrrddk..",
           "...krrrddk...",
           "....krddk....",
           ".....kDk.....",
           "......k......"]
HEART_B = ["..kkkk...kkkk..",
           ".khhhrk.khhrrk.",
           "khpWWrrkrrrrrdk",
           "khWWrrrrrrrrrdk",
           "khWrrrrrrrrrrdk",
           "khrrrrrrrrrrddk",
           "krrrrrrrrrrrddk",
           ".krrrrrrrrrddk.",
           "..krrrrrrrddk..",
           "...krrrrrddk...",
           "....krrrddk....",
           ".....krddk.....",
           "......kDk......",
           ".......k......."]
HEART_S = [".kkk...kkk.",
           "khhrk.khrrk",
           "khWrrkrrrdk",
           "khrrrrrrddk",
           "krrrrrrrddk",
           ".krrrrrddk.",
           "..krrrddk..",
           "...krddk...",
           "....kDk....",
           ".....k....."]


def build_heart():
    frames = []
    for rows, oy in ((HEART_N, 2), (HEART_B, 1), (HEART_N, 2), (HEART_S, 3)):
        sp = ascii_sprite(rows, HEART_CM)
        f = new(16, 16)
        f.alpha_composite(sp, ((16 - sp.width) // 2, oy))
        frames.append(f)
    return frames



# ----------------------------------------------------------------------------
# FX building blocks
# ----------------------------------------------------------------------------
def cloud(img, blobs, layers):
    """Cel-shaded puff: every layer is drawn for ALL blobs before the next, so lobes merge into
    one shape with banded shading.  layers: (colour, shrink[, ox, oy]) back -> front."""
    for L in layers:
        c, shrink = L[0], L[1]
        ox, oy = (L[2], L[3]) if len(L) > 2 else (0, 0)
        for (x, y, r) in blobs:
            rr = r - shrink
            if rr >= 0.45:
                disc(img, x + ox, y + oy, rr, c)


def erase_disc(img, cx, cy, r):
    disc(img, cx, cy, r, T)


def ring_band(img, cx, cy, bands, gap=None):
    """bands: list of (r_outer, r_inner, colour). gap(angle) -> True to skip (broken ring)."""
    for y in range(img.height):
        for x in range(img.width):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            for (ro, ri, c) in bands:
                if ri < d <= ro:
                    if gap and gap(math.atan2(dy, dx), d):
                        break
                    px(img, x, y, c)
                    break


def spike(img, cx, cy, ang, r0, r1, c_in, c_out, w=0):
    """Tapered radial streak."""
    ux, uy = math.cos(ang), math.sin(ang)
    n = int((r1 - r0) * 2) + 1
    for k in range(n + 1):
        t = r0 + (r1 - r0) * k / n
        f = k / n
        c = c_in if f < 0.6 else c_out
        x, y = cx + ux * t, cy + uy * t
        px(img, int(math.floor(x)), int(math.floor(y)), c)
        if w and f < 0.5:
            px(img, int(math.floor(x - uy * 0.8)), int(math.floor(y + ux * 0.8)), c)
            px(img, int(math.floor(x + uy * 0.8)), int(math.floor(y - ux * 0.8)), c)


# ----------------------------------------------------------------------------
# FX_BOOM  48x48, play: 8 frames   white -> gold -> orange -> smoke
# ----------------------------------------------------------------------------
def build_boom():
    rnd = random.Random(5)
    N = 9
    lobes = [(i * 2 * math.pi / N + rnd.uniform(-0.25, 0.25), rnd.uniform(0.86, 1.12), rnd.uniform(0.72, 1.28)) for i in range(N)]
    sparks = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0.75, 1.1)) for _ in range(11)]
    cx = cy = 23.5
    FIRE1 = [(OR[3], 0), (GOLD[3], 1.3), (GOLD[5], 2.6, -0.4, -0.4), (WHITE, 4.0, -0.6, -0.6)]
    FIRE2 = [(OR[1], 0), (OR[2], 1.0), (OR[3], 2.1), (OR[4], 3.6, -0.6, -0.6), (GOLD[3], 5.4, -1.0, -1.0),
             (GOLD[5], 7.6, -1.4, -1.4), (WHITE, 9.6, -1.6, -1.6)]
    FIRE3 = [(RD[0], 0), (OR[1], 1.0), (OR[2], 2.1, -0.3, -0.3), (OR[3], 3.6, -0.8, -0.8), (OR[4], 5.2, -1.1, -1.1),
             (GOLD[3], 6.8, -1.4, -1.4), (GOLD[5], 8.8, -1.6, -1.6)]
    FIRE4 = [(OR[1], 0), (OR[2], 0.9, -0.2, -0.2), (OR[3], 2.0, -0.5, -0.5), (OR[4], 3.2, -0.8, -0.8), (GOLD[4], 4.6, -1.0, -1.0)]
    SMOKE = [(ST[1], 0), (ST[3], 1.0), (ST[4], 2.2, -0.5, -0.5), (ST[5], 3.8, -1.0, -1.0)]
    SMOKE_S = [(ST[1], 0), (ST[3], 0.9), (ST[4], 2.0, -0.5, -0.5)]

    def blobs(d, r, rise=0.0, only=None, wob=0.0, twin=0.0):
        out = []
        for k, (a, df, rf) in enumerate(lobes):
            if only is not None and k % 2 != only:
                continue
            dd, rr = d * df, r * rf
            dd = min(dd, 22.6 - rr)                              # keep inside the 48px frame
            x, y = cx + math.cos(a + wob) * dd, cy + math.sin(a + wob) * dd - rise
            out.append((x, y, rr))
            if twin:                                             # a smaller sibling puff -> less ball-like
                out.append((x + math.cos(a + 1.9) * rr * 0.8, y + math.sin(a + 1.9) * rr * 0.8, rr * twin))
        return out

    def draw_sparks(img, d, cols, big):
        for k, (a, v) in enumerate(sparks):
            x = cx + math.cos(a) * d * v
            y = cy + math.sin(a) * d * v + (d * d) * 0.004     # a touch of gravity
            c = cols[k % len(cols)]
            px(img, x, y, c)
            if big and k % 2 == 0:
                px(img, x + 1, y, c); px(img, x, y + 1, c); px(img, x + 1, y + 1, cols[-1])

    frames = []
    # 0  anticipation: tight white-hot point with a cross flare
    f = new(48, 48)
    for k in range(4):
        spike(f, cx, cy, k * math.pi / 2, 3, 13, WHITE, GOLD[4])
    for k in range(4):
        spike(f, cx, cy, math.pi / 4 + k * math.pi / 2, 3, 7, GOLD[5], GOLD[3])
    disc(f, cx, cy, 6.0, OR[3]); disc(f, cx, cy, 5.0, GOLD[3]); disc(f, cx, cy, 4.0, GOLD[5]); disc(f, cx, cy, 3.0, WHITE)
    frames.append(f)
    # 1  burst: big white flash with a gold skin and streaks shooting out
    f = new(48, 48)
    ray_burst(f, 24, 24, 0.25, 8, 6.0, 23.0, 2.4, GOLD[4], OR[3], split=0.5)
    ray_burst(f, 24, 24, 0.25 + math.pi / 8, 8, 6.0, 17.0, 1.6, GOLD[3], OR[2], split=0.6)
    cloud(f, blobs(8.0, 5.2) + [(cx, cy, 11.0)], FIRE1)
    frames.append(f)
    # 2  full fireball
    f = new(48, 48)
    cloud(f, blobs(12.0, 6.6) + [(cx, cy, 13.5)], FIRE2)
    draw_sparks(f, 20.5, [WHITE, GOLD[4], GOLD[3]], True)
    frames.append(f)
    # 3  fire cools and tears open, smoke shows behind
    f = new(48, 48)
    cloud(f, blobs(12.5, 6.0, only=1, wob=0.35), SMOKE)
    cloud(f, blobs(13.0, 6.2) + [(cx, cy, 11.5)], FIRE3)
    erase_disc(f, cx + 4.0, cy + 4.5, 3.0); erase_disc(f, cx + 7.5, cy + 1.5, 1.7); erase_disc(f, cx + 0.5, cy + 8.0, 1.7)
    draw_sparks(f, 22.5, [GOLD[4], GOLD[3], OR[3]], True)
    frames.append(f)
    # 4  broken ring: last tongues of fire inside rolling smoke
    f = new(48, 48)
    cloud(f, blobs(14.5, 6.2, rise=0.6, twin=0.6), SMOKE)
    erase_disc(f, cx + 1.5, cy + 1.5, 6.5)
    for (a, df, rf) in lobes[1::3]:
        erase_disc(f, cx + math.cos(a + 0.4) * 8.5, cy + math.sin(a + 0.4) * 8.5, 2.4)
    cloud(f, blobs(13.4, 4.6, rise=0.6, only=0, wob=0.12, twin=0.45), FIRE4)
    draw_sparks(f, 23.0, [OR[3], OR[2], GOLD[3]], False)
    frames.append(f)
    # 5  smoke ring, a few embers
    f = new(48, 48)
    cloud(f, blobs(16.0, 5.2, rise=1.4, twin=0.55), SMOKE)
    erase_disc(f, cx, cy, 9.5)
    cloud(f, blobs(15.0, 2.0, rise=1.4, only=0, wob=0.3), [(OR[1], 0), (OR[2], 0.7), (OR[4], 1.5)])
    frames.append(f)
    # 6  puffs separate, thin out and drift up
    f = new(48, 48)
    cloud(f, blobs(17.5, 3.7, rise=2.4, twin=0.5), [(A(ST[1], 215), 0), (A(ST[3], 215), 0.9), (A(ST[4], 215), 2.0, -0.5, -0.5)])
    frames.append(f)
    # 7  last wisps
    f = new(48, 48)
    cloud(f, blobs(18.8, 2.3, rise=3.4), [(A(ST[2], 150), 0), (A(ST[3], 150), 0.9)])
    frames.append(f)
    return frames


# ----------------------------------------------------------------------------
# FX_RING  48x48, play: 6 frames   expanding white/cyan shockwave
# ----------------------------------------------------------------------------
def build_ring():
    cx = cy = 24.0
    frames = []
    f = new(48, 48)
    for k in range(4):
        spike(f, 24, 24, k * math.pi / 2, 4, 11, CY[6], CY[4])
    ring_band(f, cx, cy, [(6.2, 5.0, CY[4]), (5.0, 3.6, CY[6]), (3.6, -1, WHITE)])
    frames.append(f)
    f = new(48, 48)
    ring_band(f, cx, cy, [(11.0, 10.0, CY[4]), (10.0, 7.4, WHITE), (7.4, 6.2, CY[5]), (6.2, 4.6, A(CY[4], 150))])
    frames.append(f)
    f = new(48, 48)
    ring_band(f, cx, cy, [(16.0, 15.0, CY[4]), (15.0, 13.0, WHITE), (13.0, 12.0, CY[5]), (12.0, 10.6, A(CY[3], 150))])
    frames.append(f)
    f = new(48, 48)
    ring_band(f, cx, cy, [(19.8, 18.9, CY[4]), (18.9, 17.6, CY[6]), (17.6, 16.6, A(CY[4], 190))])
    frames.append(f)
    f = new(48, 48)
    ring_band(f, cx, cy, [(22.2, 21.3, CY[4]), (21.3, 20.3, A(CY[5], 230))],
              gap=lambda a, d: math.sin(a * 6 + 0.6) > 0.72)
    frames.append(f)
    f = new(48, 48)
    ring_band(f, cx, cy, [(23.8, 22.8, A(CY[3], 200))], gap=lambda a, d: math.sin(a * 6 + 0.6) > 0.1)
    frames.append(f)
    return frames


# ----------------------------------------------------------------------------
# FX_POOF  16x16, play: 6 frames   enemy pop
# ----------------------------------------------------------------------------
def build_poof():
    cx = cy = 7.5
    PUFF = [(NV[4], 0), (NV[6], 0.75, -0.2, -0.2), (WHITE, 1.7, -0.5, -0.5)]
    lobes = [(-2.2 + k * 2 * math.pi / 5 + j, sz) for k, (j, sz) in enumerate(((0.0, 1.15), (0.2, 0.85), (-0.15, 1.0), (0.1, 0.8), (-0.2, 1.05)))]

    def blobs(d, r):
        return [(cx + math.cos(a) * d, cy + math.sin(a) * d, min(r * sz, 7.4 - d)) for (a, sz) in lobes]

    def pinks(img, d, c):
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2 + 0.25
            px(img, cx + math.cos(a) * d, cy + math.sin(a) * d, c)
    frames = []
    f = new(16, 16)                                   # 0 flash
    for k in range(4):
        spike(f, 8, 8, k * math.pi / 2, 0, 5.2, WHITE, PK[3])
    for k in range(4):
        spike(f, 8, 8, math.pi / 4 + k * math.pi / 2, 0, 3.0, PK[3], PK[3])
    disc(f, cx, cy, 2.6, PK[3]); disc(f, cx, cy, 1.8, WHITE)
    frames.append(f)
    f = new(16, 16)                                   # 1 puff
    cloud(f, blobs(2.2, 3.3) + [(cx, cy, 3.6)], PUFF)
    pinks(f, 7.0, PK[3])
    frames.append(f)
    f = new(16, 16)                                   # 2 widest, starts to open
    cloud(f, blobs(4.0, 3.2), PUFF)
    erase_disc(f, cx + 0.6, cy + 0.8, 1.2)
    pinks(f, 8.4, PK[2])
    frames.append(f)
    f = new(16, 16)                                   # 3 ring of puffs
    cloud(f, blobs(5.0, 2.5), PUFF)
    erase_disc(f, cx, cy, 3.3)
    frames.append(f)
    f = new(16, 16)                                   # 4
    cloud(f, blobs(5.8, 1.6), [(NV[4], 0), (NV[6], 0.7, -0.2, -0.2)])
    frames.append(f)
    f = new(16, 16)                                   # 5
    cloud(f, blobs(6.3, 0.9)[::2] + blobs(5.2, 0.6)[1::2], [(A(NV[5], 200), 0)])
    frames.append(f)
    return frames


# ----------------------------------------------------------------------------
# FX_COLLECT  16x16, play: 5 frames   gold sparkle burst
# ----------------------------------------------------------------------------
def build_collect():
    cx = cy = 7.5
    frames = []

    def astroid(img, R, c, Rin=None):
        for y in range(16):
            for x in range(16):
                dx, dy = abs(x + 0.5 - 8), abs(y + 0.5 - 8)
                v = (math.sqrt(dx) + math.sqrt(dy)) ** 2
                if v <= R and (Rin is None or v > Rin):
                    px(img, x, y, c)
    f = new(16, 16)                                   # 0 pop
    for y in range(16):
        for x in range(16):
            m = abs(x + 0.5 - 8) + abs(y + 0.5 - 8)
            if m <= 4:
                px(f, x, y, GOLD[3] if m > 3 else GOLD[5] if m > 2 else WHITE)
    frames.append(f)
    f = new(16, 16)                                   # 1 big four-point star
    astroid(f, 15.5, GOLD[3]); astroid(f, 11.5, GOLD[5]); astroid(f, 6.5, WHITE)
    frames.append(f)
    f = new(16, 16)                                   # 2 star hollows, four glints fly out on the diagonals
    astroid(f, 15.5, GOLD[3], 8.0); astroid(f, 13.5, GOLD[4], 10.0)
    for sx_, sy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        sparkle(f, int(7.5 + sx_ * 4.5), int(7.5 + sy_ * 4.5), 1, WHITE, GOLD[5])
    frames.append(f)
    f = new(16, 16)                                   # 3 scattered glints
    for sx_, sy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = int(7.5 + sx_ * 6.0), int(7.5 + sy_ * 6.0)
        px(f, x, y, WHITE); px(f, x - sx_, y, GOLD[4]); px(f, x, y - sy_, GOLD[4])
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        x, y = int(7.5 + dx * 7.0), int(7.5 + dy * 7.0)
        px(f, x, y, GOLD[4]); px(f, x - dx, y - dy, GOLD[3])
    frames.append(f)
    f = new(16, 16)                                   # 4 last specks
    for sx_, sy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px(f, int(7.5 + sx_ * 7.0), int(7.5 + sy_ * 7.0), A(GOLD[4], 210))
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        px(f, int(7.5 + dx * 4.0), int(7.5 + dy * 4.0), A(GOLD[3], 170))
    frames.append(f)
    return frames


# ----------------------------------------------------------------------------
# small 8x8 effects
# ----------------------------------------------------------------------------
def rows8(rows, cm):
    return ascii_sprite([(r + "........")[:8] for r in rows] + ["........"] * (8 - len(rows)), cm)


def build_spark():
    cm = {"W": WHITE, "y": GOLD[4], "g": GOLD[3], "o": OR[3], "r": A(OR[2], 220)}
    return [rows8(["........", "........", "...y....", "..yWy...", "...y....", "........", "........", "........"], cm),
            rows8(["...y....", ".g.W.g..", "..yWy...", "yWWWWWy.", "..yWy...", ".g.W.g..", "...y....", "........"], cm),
            rows8(["...g....", ".y...y..", "........", "g.....g.", "........", ".y...y..", "...g....", "........"], cm),
            rows8(["o.....o.", "........", "........", "........", "........", "........", "o.....o.", "........"], cm)]


def build_dust():
    cm = {"W": NV[6], "l": ST[6], "m": ST[5], "d": ST[4], "a": A(ST[6], 200), "b": A(ST[5], 160)}
    return [rows8(["........", "........", "........", "........", "...ll...", "..lWll..", "..llmm..", "...mm..."], cm),
            rows8(["........", "........", "..lll...", ".lWWll..", ".lWllllm", ".llllmmm", "..lmmmd.", "........"], cm),
            rows8(["..ll....", ".lWll.l.", ".lllm.lm", "..mm....", ".....ll.", ".ll..lm.", ".lm.....", "........"], cm),
            rows8(["..a.....", ".....a..", "........", "........", ".a....b.", "........", "...b....", "........"], cm)]


def build_star():
    cm = {"W": WHITE, "y": GOLD[5], "g": GOLD[4], "o": A(GOLD[3], 220)}
    return [rows8(["........", "........", "........", "...W....", "........", "........", "........", "........"], cm),
            rows8(["........", "........", "...y....", "..yWy...", "...y....", "........", "........", "........"], cm),
            rows8(["...g....", "...y....", "..yWy...", "gyWWWyg.", "..yWy...", "...y....", "...g....", "........"], cm),
            rows8(["........", "...g....", "...W....", ".gWWWg..", "...W....", "...g....", "........", "........"], cm)]


def build_debris():
    k = OUT
    steel = {"k": k, "L": ST[7], "l": ST[6], "m": ST[5], "d": ST[3]}
    cyan = {"k": k, "L": CY[6], "l": CY[5], "m": CY[4], "d": CY[2]}
    pink = {"k": k, "L": PK[4], "l": PK[3], "m": PK[2], "d": PK[1]}
    a = ["........", "..kkk...", ".kLLlk..", ".kLmmlk.", "..kmmdk.", "...kddk.", "....kk..", "........"]
    b = ["........", "....kk..", "...kLlk.", "..kLmk..", ".kLmdk..", ".kmdk...", "..kk....", "........"]
    c = ["........", ".kk.....", ".kLlk...", ".kLmmkk.", "..kmmdk.", "...kkdk.", ".....kk.", "........"]
    d = ["........", "...kk...", "..kLlk..", "..kLmk..", ".kLmmdk.", ".kkmdk..", "...kk...", "........"]
    return [rows8(a, steel), rows8(b, steel), rows8(c, cyan), rows8(d, pink)]


# ----------------------------------------------------------------------------
# Lighting (smooth alpha is correct here: these are drawn additively)
# ----------------------------------------------------------------------------
def build_glow(size, hot):
    """White radial light with alpha falling smoothly to exactly 0 at the rim.
    hot=True: point light with a bright core;  hot=False: broad soft wash."""
    img = new(size, size)
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            d = min(1.0, math.hypot(x - c, y - c) / (c + 0.5))
            if hot:
                a = 0.62 * (1.0 - d * d) ** 3 + 0.38 * math.exp(-(d / 0.22) ** 2)
            else:
                a = (1.0 - d * d) ** 3
            img.putpixel((x, y), (255, 255, 255, int(round(255 * max(0.0, min(1.0, a))))))
    return img


def build_lightcone():
    W, H = 64, 96
    img = new(W, H)
    cxm = (W - 1) / 2.0
    for y in range(H):
        v = y / (H - 1.0)
        hw = 5.0 + (W / 2.0 - 5.0) * v                  # half-width of the cone at this row
        fall = (1.0 - v) ** 0.9 * (1.0 - v ** 4)        # bright under the lamp, fading out by the bottom row
        top = min(1.0, (y + 1) / 3.0)                   # soften the very first rows
        for x in range(W):
            u = abs(x - cxm) / hw
            if u >= 1.0:
                a = 0.0
            else:
                e = max(0.0, min(1.0, (1.0 - u) / 0.55))  # flat core, soft edge over the outer 55%
                side = e * e * (3 - 2 * e)
                a = side * (0.72 + 0.28 * (1.0 - u)) * fall * top
            img.putpixel((x, y), (255, 255, 255, int(round(230 * a))))
    return img


def build_vignette():
    W, H = 480, 270
    img = new(W, H)
    k = C["ink0"]
    hw, hh = (W - 1) / 2.0, (H - 1) / 2.0
    p = img.load()
    for y in range(H):
        for x in range(W):
            nx, ny = (x - hw) / hw, (y - hh) / hh
            d = math.sqrt(nx * nx + ny * ny)            # 1.0 at edge midpoints, 1.414 in the corners
            t = (d - 0.62) / (1.4142 - 0.62)
            t = max(0.0, min(1.0, t))
            a = 150.0 * (t * t * (3 - 2 * t)) ** 1.5    # corners ~150, edge mid-points only ~45
            ai = int(a + (BAYER4[y % 4][x % 4] + 0.5) / 16.0)   # dithered rounding: no visible banding
            p[x, y] = (k[0], k[1], k[2], max(0, min(255, ai)))
    return img

def strip(frames, name, scale=10, bg="#0d1126", gap=1):
    fw, fh = frames[0].size
    img = new(len(frames) * (fw + gap) + gap, fh + 2 * gap)
    for i, f in enumerate(frames):
        img.alpha_composite(f, (gap + i * (fw + gap), gap))
    preview(img, name, scale=scale, bg=bg)


_ROOMS = {}


def room_image(name="dock"):
    """The real tiles.mock_room scene as an RGBA image (its own preview write is intercepted)."""
    if name not in _ROOMS:
        cap = {}
        orig = tiles.preview
        tiles.preview = lambda img, n, **k: cap.setdefault("img", img.copy())
        try:
            tiles.mock_room(name)
        finally:
            tiles.preview = orig
        _ROOMS[name] = cap["img"]
    return _ROOMS[name].copy()


def context(items, name, room="dock", crop=(88, 96, 264, 232), scale=5):
    """items: list of (image, x, y) pasted into the mock room (world px), then cropped + upscaled."""
    img = room_image(room)
    for it in items:
        im, x, y = it[0], it[1], it[2]
        add = len(it) > 3 and it[3]
        if add:
            # additive preview for lighting sprites
            base = img.crop((x, y, x + im.width, y + im.height))
            bp, ip = base.load(), im.load()
            for yy in range(base.height):
                for xx in range(base.width):
                    b, c = bp[xx, yy], ip[xx, yy]
                    a = c[3] / 255.0 * (it[4] if len(it) > 4 else 1.0)
                    bp[xx, yy] = (min(255, int(b[0] + c[0] * a)), min(255, int(b[1] + c[1] * a)),
                                  min(255, int(b[2] + c[2] * a)), 255)
            img.paste(base, (x, y))
        else:
            _safe_paste(img, im, x, y)
    if crop:
        img = img.crop(crop)
    preview(img, name, scale=scale, bg="#05060c")


def _safe_paste(dst, src, x, y):
    for yy in range(src.height):
        for xx in range(src.width):
            c = src.getpixel((xx, yy))
            if c[3]:
                px(dst, x + xx, y + yy, c)




# ----------------------------------------------------------------------------
# build everything
# ----------------------------------------------------------------------------
def anim(n, fps, loop, start=0):
    return {"frames": list(range(start, start + n)), "fps": fps, "loop": loop}


def build():
    sheets = {}
    S = {}

    def add(key, frames, anims=None, names=None):
        S[key] = frames
        save(sheet(frames), f"sprites/{key}.png")
        e = {"file": f"sprites/{key}.png", "fw": frames[0].width, "fh": frames[0].height}
        if anims:
            e["anims"] = anims
        if names:
            e["names"] = names
        sheets[key] = e

    add("quarter", build_quarter(), {"spin": anim(8, 12, True)})
    add("starcell", build_starcell(), {"spin": anim(8, 10, True)})
    add("qkey", build_qkey(), {"glow": anim(6, 10, True)})
    add("missingq", build_missingq(), {"glow": anim(8, 10, True)})
    add("heart", build_heart(), {"beat": anim(4, 8, True)})
    add("fx_poof", build_poof(), {"play": anim(6, 18, False)})
    add("fx_boom", build_boom(), {"play": anim(8, 18, False)})
    add("fx_ring", build_ring(), {"play": anim(6, 20, False)})
    add("fx_spark", build_spark(), {"play": anim(4, 16, False)})
    add("fx_dust", build_dust(), {"play": anim(4, 14, False)})
    add("fx_star", build_star(), {"play": anim(4, 10, True)})
    add("fx_collect", build_collect(), {"play": anim(5, 20, False)})
    add("fx_debris", build_debris(), None, {"steel_a": 0, "steel_b": 1, "cyan": 2, "pink": 3})

    L = {"glow": ("fx/glow.png", build_glow(64, True)),
         "glow_soft": ("fx/glow_soft.png", build_glow(128, False)),
         "lightcone": ("fx/lightcone.png", build_lightcone()),
         "vignette": ("bg/vignette.png", build_vignette()),
         "pixel": ("fx/pixel.png", new(2, 2, WHITE))}
    images = {}
    for key, (path, im) in L.items():
        save(im, path)
        images[key] = {"file": path}
    manifest("fx", {"sheets": sheets, "images": images})
    return S, {k: v[1] for k, v in L.items()}


def previews(S, L):
    DARK = "#0d1126"
    strip(S["quarter"], "fx_quarter.png", scale=12, bg=DARK)
    strip([S["quarter"][i] for i in (0, 2, 3, 6)], "fx_quarter_big.png", scale=20, bg=DARK)
    strip(S["starcell"], "fx_starcell.png", scale=12, bg=DARK)
    strip([S["starcell"][i] for i in (0, 2, 4, 6)], "fx_starcell_big.png", scale=20, bg="#243258")
    strip(S["qkey"], "fx_qkey.png", scale=10, bg=DARK)
    strip([S["qkey"][0], S["qkey"][3]], "fx_qkey_big.png", scale=20, bg=DARK)
    strip(S["missingq"], "fx_missingq.png", scale=6, bg=DARK)
    strip([S["missingq"][i] for i in (0, 3, 6)], "fx_missingq_big.png", scale=12, bg=DARK)
    strip(S["heart"], "fx_heart.png", scale=12, bg=DARK)
    strip(S["fx_boom"], "fx_boom.png", scale=4, bg=DARK)
    strip(S["fx_boom"][:4], "fx_boom_a.png", scale=8, bg=DARK)
    strip(S["fx_boom"][4:], "fx_boom_b.png", scale=8, bg=DARK)
    strip(S["fx_ring"], "fx_ring.png", scale=5, bg=DARK)
    strip(S["fx_poof"], "fx_poof.png", scale=12, bg=DARK)
    strip(S["fx_collect"], "fx_collect.png", scale=12, bg=DARK)
    small = S["fx_spark"] + S["fx_dust"] + S["fx_star"] + S["fx_debris"]
    strip(small, "fx_small.png", scale=12, bg=DARK)
    strip(small, "fx_small_light.png", scale=12, bg="#47566f")
    # everything at true in-game size (1 art px = 2 screen px)
    allrow = new(420, 190, hexc("#141a3a"))
    y = 2
    for keys in (("quarter", "starcell"), ("heart", "fx_poof", "fx_collect"), ("qkey", "fx_spark", "fx_dust", "fx_star", "fx_debris"),
                 ("missingq",), ("fx_boom",), ("fx_ring",)):
        x = 2
        for key in keys:
            for fr in S[key]:
                allrow.alpha_composite(fr, (x, y)); x += fr.width + 1
            x += 6
        y += max(S[k][0].height for k in keys) + 2
    preview(allrow, "fx_all_2x.png", scale=2, bg="#141a3a")
    # in context: collectibles next to Jake on the real tiles
    q, sc, qk, mq, ht = S["quarter"], S["starcell"], S["qkey"], S["missingq"], S["heart"]
    for room in ("dock", "reactor", "zerog"):
        context([(q[0], 150, 185), (q[2], 170, 185), (sc[0], 190, 185), (ht[0], 210, 172), (qk[2], 186, 116), (mq[0], 212, 110),
                 (S["fx_star"][2], 147, 176), (S["fx_dust"][1], 120, 200), (S["fx_dust"][2], 139, 200)],
                f"fx_ctx_collect_{room}.png", room=room)
    bm, rg = S["fx_boom"], S["fx_ring"]
    context([(bm[1], 150, 160), (bm[2], 200, 160), (bm[3], 250, 160), (bm[4], 300, 160), (bm[5], 350, 160),
             (rg[1], 150, 100), (rg[2], 200, 100), (rg[3], 250, 100), (rg[4], 300, 100),
             (S["fx_poof"][1], 180, 120), (S["fx_poof"][2], 230, 120), (S["fx_poof"][3], 280, 120),
             (S["fx_collect"][1], 330, 124), (S["fx_collect"][2], 350, 124), (S["fx_collect"][3], 370, 124),
             (S["fx_debris"][0], 400, 150), (S["fx_debris"][1], 410, 140), (S["fx_debris"][2], 420, 152), (S["fx_debris"][3], 430, 142),
             (S["fx_spark"][1], 396, 120), (S["fx_spark"][2], 408, 120)],
            "fx_ctx_fx.png", crop=(100, 80, 420, 232), scale=4)
    # lighting: on black, and additively over the room
    lw = new(64 + 128 + 64 + 16, 132, hexc("#000000"))
    lw.alpha_composite(L["glow"], (4, 34)); lw.alpha_composite(L["glow_soft"], (72, 2)); lw.alpha_composite(L["lightcone"], (204, 18))
    preview(lw, "fx_lights.png", scale=3, bg="#000000")
    img = room_image("dock")
    img.alpha_composite(L["vignette"].crop((0, 0, 480, 270)))
    preview(img, "fx_vignette_room.png", scale=2, bg="#05060c")
    vg = new(480, 270, hexc("#6b8fd6")); vg.alpha_composite(L["vignette"])
    preview(vg, "fx_vignette.png", scale=2, bg="#6b8fd6")
    context([(L["lightcone"], 96, 16, True, 0.45), (L["glow"], 180, 150, True, 0.5), (L["glow_soft"], 300, 60, True, 0.35),
             (q[0], 204, 174), (mq[0], 348, 108)],
            "fx_ctx_lights.png", crop=None, scale=2)


if __name__ == "__main__":
    S, L = build()
    previews(S, L)
    print("fx: wrote", len(S), "sheets and", len(L), "images")
