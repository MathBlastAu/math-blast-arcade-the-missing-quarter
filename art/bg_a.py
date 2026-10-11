"""
bg_a.py - space layers, docking-bay and bridge parallax backgrounds, the intro
hero shot of Kepler Station and Jake's inspector shuttle.

  python3 bg_a.py            regenerate everything + previews (art/_preview/bga_*.png)
  python3 bg_a.py planet     regenerate one part (stars nebula planet dock_far dock_mid
                             bridge_far bridge_mid station shuttle), then the previews

Method: big layers are painted as *value maps* (numpy float images, 0..1) plus a
material id, lit with large soft light fields, then quantised onto a short colour
ramp with the same 4x4 ordered dither as pix.dither_pick.  That keeps every layer
on a handful of related colours and gives the layered, hazy look without any soft
anti-aliasing.  Small points of light are placed by hand on top.

Background ramps are low-contrast in-betweens of the pix.py ink/navy/steel ramps
and the tile "wall" ramps of the dock/bridge skins (see tiles.SKINS), so the far
layer stays darker than the mid layer, which stays darker than any solid tile.
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw
import pix
from pix import C, hexc, mix, save, preview, manifest, ASSETS, PREVIEW

TAU = math.pi * 2
BAY4 = (np.array(pix.BAYER4, dtype=np.float32) + 0.5) / 16.0


# ----------------------------------------------------------------------------
# numpy helpers
# ----------------------------------------------------------------------------
def bayer(h, w, ox=0, oy=0):
    yy, xx = np.mgrid[0:h, 0:w]
    return BAY4[(yy + oy) % 4, (xx + ox) % 4]


def quant(t, n, width=1.0, ox=0, oy=0):
    """Float field 0..1 -> integer ramp index 0..n-1 with ordered dithering.
    width < 1 narrows the dithered zone between two neighbouring tones."""
    f = np.clip(t, 0.0, 1.0) * (n - 1)
    i = np.floor(f)
    frac = f - i
    if width < 1.0:
        frac = np.clip((frac - 0.5) / max(width, 1e-3) + 0.5, 0.0, 1.0)
    thr = bayer(t.shape[0], t.shape[1], ox, oy)
    return np.minimum(i + (frac > thr), n - 1).astype(np.int32)


def pal(cols, alpha=None):
    out = []
    for i, c in enumerate(cols):
        c = hexc(c) if isinstance(c, str) else tuple(c)
        if alpha is not None:
            c = (c[0], c[1], c[2], alpha[i] if isinstance(alpha, (list, tuple)) else alpha)
        out.append(c)
    return np.array(out, dtype=np.uint8)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def to_img(arr):
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def over(dst, src):
    """alpha-composite src array over dst array (both HxWx4 uint8)."""
    a = src[..., 3:4].astype(np.float32) / 255.0
    out = dst.astype(np.float32)
    out[..., :3] = src[..., :3] * a + out[..., :3] * (1 - a)
    out[..., 3:4] = np.maximum(dst[..., 3:4], src[..., 3:4])
    return out.astype(np.uint8)


class Noise:
    """Periodic value-noise fBm.  at(u, v): u, v in 'periods' (wraps at integers)."""

    def __init__(self, seed, cx, cy, octaves=4, gain=0.5):
        rng = np.random.default_rng(seed)
        self.grids = [rng.random((cy * 2 ** o, cx * 2 ** o)).astype(np.float32) for o in range(octaves)]
        self.amps = [gain ** o for o in range(octaves)]

    def at(self, u, v):
        tot = 0.0
        for g, a in zip(self.grids, self.amps):
            gh, gw = g.shape
            x = u * gw; y = v * gh
            x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
            fx = x - x0; fy = y - y0
            fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
            x0 %= gw; y0 %= gh
            x1 = (x0 + 1) % gw; y1 = (y0 + 1) % gh
            tot = tot + a * ((g[y0, x0] * (1 - fx) + g[y0, x1] * fx) * (1 - fy)
                             + (g[y1, x0] * (1 - fx) + g[y1, x1] * fx) * fy)
        return tot / sum(self.amps)


class VC:
    """Value canvas: paint shapes as brightness values + material ids, light it,
    then render() quantises each material onto its own colour ramp."""

    def __init__(self, w, h, wrap=True):
        self.w, self.h, self.wrap = w, h, wrap
        self.v = np.zeros((h, w), np.float32)
        self.m = np.zeros((h, w), np.uint8)          # 0 = transparent
        self.yy, self.xx = np.mgrid[0:h, 0:w]

    # --- masks ---------------------------------------------------------------
    def _mask(self, fn):
        im = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(im)
        for dx in ((-self.w, 0, self.w) if self.wrap else (0,)):
            fn(d, dx)
        return np.array(im) > 0

    def rect_m(self, x0, y0, x1, y1):
        return self._mask(lambda d, dx: d.rectangle([x0 + dx, y0, x1 + dx, y1], fill=255))

    def poly_m(self, pts):
        return self._mask(lambda d, dx: d.polygon([(x + dx, y) for x, y in pts], fill=255))

    def ell_m(self, x0, y0, x1, y1):
        return self._mask(lambda d, dx: d.ellipse([x0 + dx, y0, x1 + dx, y1], fill=255))

    def line_m(self, pts, width=1):
        return self._mask(lambda d, dx: d.line([(x + dx, y) for x, y in pts], fill=255, width=width))

    # --- painting ------------------------------------------------------------
    def put(self, mask, v, mat=1):
        self.v[mask] = v
        self.m[mask] = mat

    def add(self, mask, dv):
        self.v[mask] += dv

    def cut(self, mask):
        self.m[mask] = 0
        self.v[mask] = 0

    def rect(self, x0, y0, x1, y1, v, mat=1):
        self.put(self.rect_m(x0, y0, x1, y1), v, mat)

    def box(self, x0, y0, x1, y1, v, mat=1, hi=0.10, lo=0.10):
        """Rectangle lit from the top-left: light top/left edge, dark bottom/right edge."""
        self.rect(x0, y0, x1, y1, v, mat)
        if lo:
            self.rect(x0, y1, x1, y1, v - lo, mat)
            self.rect(x1, y0, x1, y1, v - lo, mat)
        if hi:
            self.rect(x0, y0, x1, y0, v + hi, mat)
            self.rect(x0, y0, x0, y1 - 1, v + hi * 0.7, mat)

    def line(self, pts, v, mat=1, width=1):
        self.put(self.line_m(pts, width), v, mat)

    def poly(self, pts, v, mat=1):
        self.put(self.poly_m(pts), v, mat)

    def render(self, ramps, width=0.8):
        out = np.zeros((self.h, self.w, 4), np.uint8)
        for mat, rp in ramps.items():
            P = pal(rp)
            idx = quant(self.v, len(P), width[mat] if isinstance(width, dict) else width)
            sel = self.m == mat
            out[sel] = P[idx[sel]]
        return out


def dots(arr, pts, col, wrap=True):
    """Place single pixels (x, y) of a colour on an RGBA array."""
    h, w = arr.shape[:2]
    c = hexc(col) if isinstance(col, str) else col
    for x, y in pts:
        x = int(x) % w if wrap else int(x)
        if 0 <= x < w and 0 <= int(y) < h:
            arr[int(y), x] = c


def light(arr, x, y, core, halo=None, wrap=True, big=False, only_opaque=True):
    """A tiny lamp: bright core pixel and a dim halo of the same hue (plus shape)."""
    h, w = arr.shape[:2]
    core = hexc(core) if isinstance(core, str) else core
    if halo is not None:
        halo = hexc(halo) if isinstance(halo, str) else halo
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in nb:
            xx = (x + dx) % w if wrap else x + dx
            yy = y + dy
            if 0 <= xx < w and 0 <= yy < h and (arr[yy, xx, 3] > 0 or not only_opaque):
                arr[yy, xx] = halo
    xx = x % w if wrap else x
    if 0 <= xx < w and 0 <= y < h:
        arr[y, xx] = core
        if big and xx + 1 < w:
            arr[y, xx + 1] = core


# ----------------------------------------------------------------------------
# colour ramps for the background layers (dark -> light)
# ----------------------------------------------------------------------------
SPACE = ["#080a14", "#0a0c1b", "#0c1024"]

DOCK_FAR = ["#090b18", "#0b0e1f", "#0d1126", "#10152e", "#131936", "#161d3d", "#192245", "#1d284d", "#222f57"]
DOCK_SHIP = ["#090b17", "#0b0e20", "#0d122a", "#101733", "#131b3c", "#182446", "#1f2f58", "#2a416f", "#385688"]
DOCK_MID = ["#0e1229", "#121834", "#161e3f", "#1b2549", "#202c53", "#26355e", "#2d3f6b", "#374c7a", "#445c8b"]

DOCK_MID_TEAL = [mix(hexc(a), hexc("#0f7480"), 0.17) for a in DOCK_MID]
DOCK_MID_PLUM = [mix(hexc(a), hexc("#6f3fc0"), 0.10) for a in DOCK_MID]

BRIDGE_FAR = ["#090b19", "#0b0f22", "#0d132b", "#101835", "#131d3f", "#172349", "#1b2a54", "#20325f"]
BRIDGE_MID = ["#0d1228", "#111836", "#151f43", "#1a274f", "#1f2f5c", "#253868", "#2d4478", "#39548c", "#4867a2"]


# ============================================================================
# bg_stars  512x288  opaque, tiles in X and Y
# ============================================================================
def make_stars():
    W, H = 512, 288
    rng = np.random.default_rng(20)
    yy, xx = np.mgrid[0:H, 0:W]
    u = xx / W; v = yy / H
    # faint large-scale mottling of the void (3 near-black tones, tileable)
    n = Noise(5, 3, 2, octaves=4).at(u, v)
    n2 = Noise(6, 2, 1, octaves=3).at(u + 0.3, v + 0.1)
    t = smooth(0.50, 0.74, n * 0.65 + n2 * 0.35)
    arr = pal(SPACE)[quant(t, 3, width=0.55)]

    # star density: clustered, with real voids, tileable
    dens = Noise(9, 4, 3, octaves=3).at(u, v) * 0.6 + Noise(10, 2, 2, octaves=2).at(u, v) * 0.4
    dens = smooth(0.34, 0.72, dens) ** 1.5 + 0.06
    dens = dens / dens.max()

    def scatter(count, minsep, taken, power=1.0):
        pts = []
        tries = 0
        while len(pts) < count and tries < count * 400:
            tries += 1
            x = int(rng.integers(0, W)); y = int(rng.integers(0, H))
            if rng.random() > dens[y, x] ** power:
                continue
            ok = True
            for (px_, py_) in taken[-400:] if minsep <= 2 else taken:
                dx = min(abs(px_ - x), W - abs(px_ - x)); dy = min(abs(py_ - y), H - abs(py_ - y))
                if dx < minsep and dy < minsep:
                    ok = False; break
            if ok:
                pts.append((x, y)); taken.append((x, y))
        return pts

    def P(x, y, c):
        arr[y % H, x % W] = hexc(c)

    taken = []
    # class 4 - a handful of big glinting stars (placed first so they get room)
    big = scatter(6, 60, taken, 0.5)
    # class 3 - bright
    bright = scatter(34, 14, taken, 0.8)
    # class 2 - medium
    medium = scatter(110, 4, taken, 1.0)
    # class 1 - dim dust
    dim = scatter(300, 2, taken, 1.3)

    dim_cols = ["#1e2a5a", "#243258", "#2b3f7e", "#323f57", "#2a2f5e", "#1f3550"]
    for (x, y) in dim:
        P(x, y, dim_cols[int(rng.integers(0, len(dim_cols)))])
    med_cols = ["#3f5fae", "#47566f", "#64758f", "#4d63a0", "#5a709e", "#3f5fae"]
    tint_med = ["#6f3fc0", "#12a3a6", "#c9471a", "#a8256a"]
    for i, (x, y) in enumerate(medium):
        P(x, y, tint_med[i % 4] if i % 9 == 0 else med_cols[int(rng.integers(0, len(med_cols)))])
    for i, (x, y) in enumerate(bright):
        k = i % 8
        if k == 0:
            core, arm = "#ffc46b", "#8a2c10"      # warm
        elif k == 1:
            core, arm = "#8ff7ea", "#0e4a5c"      # cyan
        elif k == 2:
            core, arm = "#cfa8ff", "#2a1657"      # violet
        else:
            core, arm = ("#e6f1ff", "#2b3f7e") if i % 2 else ("#a9c5f0", "#1e2a5a")
        P(x, y, core)
        if i % 3 != 2:                             # two in three get a soft plus halo
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                P(x + dx, y + dy, arm)
    for i, (x, y) in enumerate(big):
        warm = i == 1
        violet = i == 4
        c0 = "#fff0b8" if warm else "#f0e0ff" if violet else "#e6f1ff"
        c1 = "#ff9340" if warm else "#a26bf0" if violet else "#6b8fd6"
        c2 = "#8a2c10" if warm else "#472585" if violet else "#2b3f7e"
        c3 = "#4a160e" if warm else "#2a1657" if violet else "#1e2a5a"
        P(x, y, c0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            P(x + dx, y + dy, c1)
            P(x + dx * 2, y + dy * 2, c2)
            if i % 2 == 0:
                P(x + dx * 3, y + dy * 3, c3)
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            P(x + dx, y + dy, c3)
    return to_img(arr)


# ============================================================================
# bg_nebula  512x288  transparent, tiles in X
# ============================================================================
def make_nebula():
    W, H = 512, 288
    yy, xx = np.mgrid[0:H, 0:W]
    u = xx / W; v = yy / W                      # isotropic; X period = 1
    wx = Noise(31, 3, 3, 4).at(u, v) - 0.5
    wy = Noise(32, 3, 3, 4).at(u + 0.5, v) - 0.5
    uw = u + wx * 0.42; vw = v + wy * 0.42
    d = Noise(33, 3, 3, 5, gain=0.58).at(uw, vw)
    n2 = Noise(34, 6, 6, 4, gain=0.6).at(uw + 0.3, vw * 1.3)
    ridge = 1 - np.abs(2 * n2 - 1)                           # filaments
    big = Noise(35, 2, 2, 2).at(u, v)

    # a sweeping band that climbs and falls across the period
    yc = 88 + 44 * np.sin(TAU * u + 0.9) + 14 * np.sin(2 * TAU * u + 2.4)
    dy = (yy - yc)
    env = np.exp(-(dy / np.where(dy < 0, 70.0, 52.0)) ** 2)
    env *= smooth(200, 140, yy.astype(np.float32))           # nothing in the bottom third
    env *= 0.35 + 0.95 * smooth(0.36, 0.62, big)
    D = d * 0.62 + ridge * 0.38
    D = smooth(0.43, 0.80, D) * env
    D = np.clip(D * 1.25, 0, 1) ** 1.25

    hue = Noise(36, 3, 3, 3).at(u + wy * 0.5 + 0.2, v + wx * 0.5)
    teal = smooth(0.53, 0.66, hue + dy / 500.0)              # teal gathers on the lower fringe
    is_teal = teal > bayer(H, W, 2, 1)

    lvl = quant(D, 6, width=0.62)
    purple = pal(["#000000", "#130a2a", "#1a0e38", "#211045", "#291554", "#341b66"], [0, 95, 135, 170, 195, 215])
    tealp = pal(["#000000", "#071a26", "#092330", "#0a2d3c", "#0c3847", "#0f4553"], [0, 90, 130, 165, 190, 210])
    arr = np.where(is_teal[..., None], tealp[lvl], purple[lvl])

    # a few newborn stars glowing inside the densest gas
    rng = np.random.default_rng(4)
    core = np.argwhere(D > 0.62)
    placed = []
    for _ in range(600):
        if len(placed) >= 8 or len(core) == 0:
            break
        y, x = core[int(rng.integers(0, len(core)))]
        if all(abs(x - px_) + abs(y - py_) > 40 for px_, py_ in placed) and 3 < x < W - 3:
            placed.append((x, y))
    for i, (x, y) in enumerate(placed):
        c = ("#cfa8ff", "#6f3fc0") if i % 3 else ("#ffd0e6", "#a8256a")
        arr[y, x] = hexc(c[0])
        if i % 2 == 0:
            for dx, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                arr[y + dy_, (x + dx) % W] = hexc(c[1], 230)
    return to_img(arr)


# ============================================================================
# bg_planet  220x220  transparent
# ============================================================================
PLANET_HUES = [
    # night      ...                                                   highlight
    ["#0a0c1b", "#10142f", "#161f48", "#1c2b5f", "#243a76", "#30508e", "#4069a4"],   # 0 deep blue belt
    ["#0a0c1b", "#0f1732", "#14264c", "#193a66", "#225280", "#346d98", "#5189ac"],   # 1 blue
    ["#0a0c1b", "#0d1a30", "#0f2c46", "#12465e", "#186476", "#2c858e", "#55a5a2"],   # 2 teal
    ["#0a0c1b", "#101d33", "#18364c", "#265768", "#3f7c84", "#69a19a", "#9cc2b0"],   # 3 pale teal / mint
    ["#0a0c1b", "#19172f", "#31233e", "#553649", "#835555", "#b17f67", "#d6ac88"],   # 4 peach / cream
    ["#0a0c1b", "#19132e", "#321b39", "#55263f", "#7f3a40", "#a85840", "#c98253"],   # 5 rust
]
RING_RAMP = ["#0d1024", "#1a1d3c", "#2b2e55", "#444870", "#666a8e", "#8f8ea8", "#b9b0b4"]


def make_planet():
    S = 220
    R = 83.0
    cx = cy = 109.5
    yy, xx = np.mgrid[0:S, 0:S]
    x = (xx - cx) / R; y = (yy - cy) / R
    r2 = x * x + y * y
    inside = r2 <= 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    roll = math.radians(20); inc = math.radians(19)
    ca, sa = math.cos(roll), math.sin(roll)
    ci, si = math.cos(inc), math.sin(inc)
    x1 = x * ca - y * sa
    y1 = x * sa + y * ca
    y2 = y1 * ci - z * si
    z2 = y1 * si + z * ci
    s = -y2                                      # sin(latitude), north = +1
    lon = np.arctan2(x1, z2)

    L = np.array([-0.52, -0.60, 0.61]); L = L / np.linalg.norm(L)
    lam = x * L[0] + y * L[1] + z * L[2]

    # --- band structure ------------------------------------------------------
    u = lon / TAU + 0.5
    v = (s + 1) / 2
    turb = (Noise(41, 5, 9, 3).at(u, v) - 0.5) * 0.085 + (Noise(42, 11, 24, 2).at(u, v) - 0.5) * 0.045
    # storm oval
    lon0, s0 = -0.52, 0.075
    e = ((lon - lon0) / 0.24) ** 2 + ((s - s0) / 0.085) ** 2
    turb += 0.06 * np.exp(-e * 0.6) * np.sign(s - s0) * (e > 1)
    st = s + turb
    # (upper sin-lat edge, hue 0..5, brightness)
    bands = [(1.00, 0.0, 0.80), (0.86, 1.0, 0.92), (0.74, 2.0, 1.00), (0.63, 3.0, 1.08), (0.55, 2.0, 0.96),
             (0.44, 1.0, 0.90), (0.36, 2.2, 1.02), (0.27, 3.6, 1.10), (0.17, 4.0, 1.06), (-0.04, 5.0, 0.94),
             (-0.12, 4.0, 1.08), (-0.30, 3.0, 1.04), (-0.38, 2.0, 0.98), (-0.52, 1.0, 0.90), (-0.60, 2.0, 0.98),
             (-0.70, 1.0, 0.88), (-0.84, 0.0, 0.78)]
    edges = np.array([b[0] for b in bands])
    hv = np.array([b[1] for b in bands]); bv = np.array([b[2] for b in bands])
    k = np.clip(np.searchsorted(-edges, -st, side="left") - 1, 0, len(bands) - 1)
    k2 = np.clip(k + 1, 0, len(bands) - 1)
    # soft transition in the last 0.022 before the next (lower) edge
    lower = np.where(k + 1 < len(bands), edges[k2], -1.2)
    tmix = smooth(0.026, 0.0, st - lower)
    hue_f = hv[k] * (1 - tmix) + hv[k2] * tmix
    bri = bv[k] * (1 - tmix) + bv[k2] * tmix
    # streaks: long thin features stretched along longitude
    streak = Noise(43, 6, 64, 2).at(u, v + turb * 0.5) - 0.5
    fine = Noise(44, 18, 40, 2).at(u, v) - 0.5
    hue_f = hue_f + streak * 0.9
    bri = bri * (1 + streak * 0.26 + fine * 0.04)
    # strings of small pale ovals riding two of the belts
    for (ol, os_, sl, ss) in ((-0.95, -0.455, 0.060, 0.026), (-0.66, -0.45, 0.075, 0.03), (-0.34, -0.455, 0.055, 0.024),
                              (-0.30, 0.50, 0.08, 0.03), (0.12, 0.49, 0.06, 0.024), (-1.05, 0.31, 0.07, 0.026)):
        eo = ((lon - ol) / sl) ** 2 + ((s - os_) / ss) ** 2
        w = smooth(1.0, 0.5, eo)
        hue_f = hue_f * (1 - w) + 3.0 * w
        bri = bri * (1 + 0.16 * w)
    # storm: rust eye, cream collar
    eye = smooth(1.0, 0.55, e)
    collar = smooth(1.9, 1.15, e) * (1 - eye)
    hue_f = hue_f * (1 - eye) + 5.0 * eye
    hue_f = hue_f * (1 - collar * 0.8) + 4.0 * collar * 0.8
    bri = bri * (1 + 0.16 * collar + 0.10 * smooth(0.5, 0.0, e) - 0.10 * smooth(0.95, 0.7, e) * smooth(0.45, 0.7, e))

    # --- ring geometry (equatorial plane) -------------------------------------
    rho = np.sqrt(x1 ** 2 + (y1 / si) ** 2)
    zr = y1 / math.tan(inc)
    RB = [(1.100, 1.146, 0.40), (1.160, 1.240, 1.0), (1.262, 1.300, 0.70)]     # (inner, outer, brightness)

    def ring_val(r):
        out = np.zeros_like(r)
        for a, b, w in RB:
            out = np.where((r >= a) & (r <= b), w, out)
        return out

    # ring shadow cast on the planet
    lx1 = L[0] * ca - L[1] * sa; ly1 = L[0] * sa + L[1] * ca
    ly2 = ly1 * ci - L[2] * si; lz2 = ly1 * si + L[2] * ci
    tt = -y2 / ly2
    hx = x1 + tt * lx1; hz = z2 + tt * lz2
    rsh = np.where(tt > 0, ring_val(np.sqrt(hx ** 2 + hz ** 2)), 0.0)

    # --- light -> tone ---------------------------------------------------------
    t = np.clip(lam, 0, 1) ** 0.85
    t = t * (0.80 + 0.20 * z ** 0.6)             # limb darkening
    t = t * bri * (1 - 0.42 * rsh)
    tone_f = np.clip(0.09 + t * 1.04, 0, 1)
    tone_f = np.where(lam <= 0, np.clip(0.09 + lam * 0.8, 0, 1), tone_f)
    # atmosphere: lit limb glows mint
    limb = smooth(0.34, 0.05, z) * smooth(0.10, 0.45, lam)
    hue_f = hue_f * (1 - limb * 0.7) + 2.6 * limb * 0.7
    tone_f = np.clip(tone_f + limb * 0.10, 0, 1)

    hue_i = quant(np.clip(hue_f, 0, 5) / 5.0, 6, width=0.45, ox=2, oy=1)
    tone_i = quant(tone_f, 7, width=0.7)
    PH = np.array([pal(h) for h in PLANET_HUES])
    arr = np.zeros((S, S, 4), np.uint8)
    arr[inside] = PH[hue_i, tone_i][inside]

    # thin atmospheric halo just outside the lit limb
    rr = np.sqrt(r2)
    lam_edge = (x * L[0] + y * L[1]) / np.maximum(rr, 1e-6)
    halo = (~inside) & (rr <= 1 + 1.6 / R) & (lam_edge > 0.25)
    arr[halo] = hexc("#2c858e", 150)
    halo2 = (~inside) & (rr > 1 + 1.6 / R) & (rr <= 1 + 3.0 / R) & (lam_edge > 0.55) & (bayer(S, S) > 0.5)
    arr[halo2] = hexc("#186476", 90)

    # --- ring ------------------------------------------------------------------
    rv = ring_val(rho)
    # fine radial structure
    rv = rv * np.where((rho > 1.19) & (rho < 1.215), 0.86, 1.0)
    vis = (rv > 0) & ((~inside) | (zr > z))
    # planet's shadow across the ring
    Pl = x * L[0] + y * L[1] + zr * L[2]
    d2 = (x * x + y * y + zr * zr) - Pl * Pl
    shadow = smooth(1.04, 0.92, d2) * (Pl < 0)
    side = 0.80 + 0.20 * smooth(-1.2, 1.2, -x1)            # sun side a little brighter
    back = np.where(zr < 0, 0.86, 1.0)
    rt = rv * side * back * (1 - 0.93 * shadow)
    ring_i = quant(np.clip(0.04 + rt * 0.84, 0, 1), len(RING_RAMP), width=0.25, ox=1, oy=2)
    RP = pal(RING_RAMP)
    arr[vis] = RP[ring_i][vis]
    # the faint inner ring is see-through (checker) so the planet shows behind it
    faint = vis & (rho < 1.153) & (((xx + yy) % 2) == 0)
    back_px = np.zeros((S, S, 4), np.uint8)
    back_px[inside] = PH[hue_i, tone_i][inside]
    arr[faint] = back_px[faint]
    return to_img(arr)


def cham(x0, y0, x1, y1, c):
    """Rectangle with chamfered corners as a polygon."""
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def edges(mask):
    """(top/left edge pixels, bottom/right edge pixels) of a mask - for bevels."""
    up = np.roll(mask, 1, axis=0); up[0, :] = False
    lf = np.roll(mask, 1, axis=1)
    dn = np.roll(mask, -1, axis=0); dn[-1, :] = False
    rt = np.roll(mask, -1, axis=1)
    return mask & ~(up & lf), mask & ~(dn & rt)


def bevel(c, mask, v, mat=1, hi=0.10, lo=0.10):
    c.put(mask, v, mat)
    e_hi, e_lo = edges(mask)
    c.v[e_lo] = v - lo
    c.v[e_hi & ~e_lo] = v + hi


# ============================================================================
# dock_far  480x270  tiles in X, hangar openings transparent
# ============================================================================
def make_dock_far():
    W, H = 480, 270
    c = VC(W, H)
    WALL, SHIP = 1, 2
    yy, xx = c.yy, c.xx

    # --- wall plates --------------------------------------------------------
    c.rect(0, 0, W - 1, H - 1, 0.50)
    for i, x in enumerate(range(0, W, 60)):
        c.rect(x, 0, x + 59, H - 1, 0.50 + [0.02, -0.025, 0.0, 0.03, -0.03, 0.012, -0.012, 0.025][i])
        c.rect(x, 0, x, H - 1, 0.42)
        c.rect(x + 1, 0, x + 1, H - 1, 0.555)
    # horizontal plate joints in the lower wall, staggered
    for i, x in enumerate(range(0, W, 60)):
        y = 226 + (i % 3) * 9
        c.rect(x + 2, y, x + 59, y, 0.40); c.rect(x + 2, y + 1, x + 59, y + 1, 0.545)

    # --- ceiling: heavy beam + truss ----------------------------------------
    c.rect(0, 0, W - 1, 12, 0.30)
    c.rect(0, 13, W - 1, 14, 0.64); c.rect(0, 15, W - 1, 15, 0.26)
    c.rect(0, 16, W - 1, 28, 0.36)
    for k in range(0, W, 40):
        c.line([(k, 16), (k + 20, 28), (k + 40, 16)], 0.52, width=2)
        c.rect(k - 1, 16, k + 1, 28, 0.56)
    c.rect(0, 28, W - 1, 29, 0.62); c.rect(0, 30, W - 1, 31, 0.30)

    # --- lower wall: ledge, plinth, pipes -----------------------------------
    c.rect(0, 188, W - 1, 189, 0.70); c.rect(0, 190, W - 1, 192, 0.34)
    c.rect(0, 193, W - 1, 193, 0.44)
    for y, v in ((206, 0.66), (207, 0.56), (208, 0.46), (209, 0.36), (210, 0.28)):
        c.rect(0, y, W - 1, y, v)
    for y, v in ((214, 0.56), (215, 0.44), (216, 0.30)):
        c.rect(0, y, W - 1, y, v)
    for x in (22, 118, 214, 300, 396):
        c.box(x, 204, x + 3, 212, 0.60, hi=0.10, lo=0.2)
    # a riser pipe with a valve
    c.box(140, 193, 144, 205, 0.56, hi=0.1, lo=0.18)
    c.box(137, 197, 147, 200, 0.62, hi=0.1, lo=0.18)

    # --- support ribs (pillars) ---------------------------------------------
    for (x0, x1) in ((24, 46), (334, 356)):
        c.rect(x0, 0, x1, H - 1, 0.58)
        c.rect(x0, 0, x0 + 1, H - 1, 0.70)
        c.rect(x1 - 1, 0, x1, H - 1, 0.38)
        c.rect(x0 + 6, 32, x1 - 6, H - 1, 0.46)             # recessed web
        c.rect(x0 + 6, 32, x0 + 6, H - 1, 0.36)
        c.rect(x1 - 6, 32, x1 - 6, H - 1, 0.60)
        for y in (60, 108, 156, 220):                        # stiffener plates
            c.box(x0 + 2, y, x1 - 2, y + 5, 0.62, hi=0.1, lo=0.2)
        c.box(x0 - 4, 28, x1 + 4, 35, 0.66, hi=0.10, lo=0.22)    # capital
        c.box(x0 - 3, 186, x1 + 3, 193, 0.66, hi=0.10, lo=0.22)  # base collar
        # diagonal gussets up to the truss
        c.poly([(x0 - 4, 36), (x0 - 16, 36), (x0 - 4, 48)], 0.52)
        c.poly([(x1 + 4, 36), (x1 + 16, 36), (x1 + 4, 48)], 0.44)

    # --- the big hangar opening ----------------------------------------------
    OX0, OY0, OX1, OY1 = 60, 46, 320, 178
    bevel(c, c.poly_m(cham(OX0 - 10, OY0 - 9, OX1 + 10, OY1 + 9, 22)), 0.66, hi=0.12, lo=0.22)
    rev = c.poly_m(cham(OX0 - 4, OY0 - 4, OX1 + 4, OY1 + 4, 18))
    c.put(rev, 0.30)
    hole = c.poly_m(cham(OX0, OY0, OX1, OY1, 16))
    # sunlight from outside catches the sill and the right-hand reveal
    c.put(rev & (yy > OY1 - 12) & (yy - OY1 > -(OX1 - xx) * 1.0 - 4) & (yy > (OY1 + OY0) / 2), 0.80)
    c.put(rev & (yy >= OY1), 0.86)
    c.put(rev & (xx >= OX1) & (yy > OY0 + 14), 0.72)

    # --- control section: slit window, booth, closed bay door ---------------
    bevel(c, c.poly_m(cham(372, 38, 468, 64, 8)), 0.64, hi=0.12, lo=0.2)
    slit_rev = c.poly_m(cham(376, 42, 464, 60, 6))
    c.put(slit_rev, 0.30)
    slit = c.poly_m(cham(379, 44, 461, 58, 5))
    c.put(slit_rev & (yy >= 58), 0.8)
    # booth
    c.box(362, 74, 478, 77, 0.74, hi=0.1, lo=0.2)             # roof slab
    c.box(368, 78, 472, 120, 0.60, hi=0.08, lo=0.18)
    c.rect(368, 78, 472, 79, 0.36)                             # shadow under the roof slab
    c.rect(372, 85, 468, 101, 0.24)                            # window recess
    c.box(368, 108, 472, 111, 0.68, hi=0.08, lo=0.2)          # sill band
    for x in (380, 420, 460):                                  # brackets under the booth
        c.poly([(x - 5, 121), (x + 5, 121), (x + 5, 124), (x, 133), (x - 1, 133)], 0.50)
        c.line([(x - 5, 121), (x - 1, 133)], 0.62)
    c.rect(368, 121, 472, 122, 0.30)
    # mast on the booth roof
    c.rect(452, 62, 453, 73, 0.62)
    # closed bay door
    bevel(c, c.poly_m(cham(380, 138, 460, 189, 6)), 0.64, hi=0.10, lo=0.2)
    c.rect(385, 143, 455, 187, 0.42)
    for y in range(143, 186, 7):
        c.rect(385, y, 455, y, 0.52); c.rect(385, y + 1, 455, y + 1, 0.34)
    c.rect(419, 143, 420, 187, 0.30); c.rect(421, 143, 421, 187, 0.50)
    stripe = (((xx + yy) // 5) % 2 == 0) & c.rect_m(385, 180, 455, 186)
    c.put(c.rect_m(385, 180, 455, 186), 0.30)
    c.put(stripe, 0.62)

    # --- light --------------------------------------------------------------
    lit = np.zeros((H, W), np.float32)
    lamps = [(35, 37), (345, 37), (190, 33), (420, 124)]
    for lx, ly in lamps:
        for dx in (-W, 0, W):
            dyy = (yy - ly).astype(np.float32)
            spread = 12 + np.maximum(dyy, 0) * 0.55
            cone = np.clip(1 - np.abs(xx - lx - dx) / spread, 0, 1) * (dyy >= 0)
            lit += cone ** 0.8 * np.exp(-np.maximum(dyy, 0) / (46.0 if ly > 100 else 80.0)) * (0.30 if ly > 100 else 0.50)
    lit += 0.09 * np.exp(-((yy - 112) / 64.0) ** 2)                 # planet-light bouncing around the bay
    grime = Noise(61, 4, 3, 3).at(xx / W, yy / W) - 0.5
    fade = 1 - 0.62 * smooth(182, 268, yy.astype(np.float32))       # calm, dark bottom third
    c.v = (c.v - 0.07 + lit + grime * 0.07) * fade * (0.86 + 0.14 * smooth(0, 44, yy.astype(np.float32)))

    # --- cut the openings, park the freighter outside ------------------------
    c.cut(hole); c.cut(slit)
    c.wrap = False
    ship = np.zeros((H, W), bool)

    def sp(mask, v):
        m = mask & hole
        c.put(m, v, SHIP)
        ship[m] = True

    # tanker waiting for fuel: nose to the left, tail hidden behind the right-hand rib
    Ls = np.array([-0.55, -0.62, 0.56]); Ls = Ls / np.linalg.norm(Ls)
    # keel / main hull
    sp(c.poly_m([(112, 158), (124, 151), (340, 151), (340, 168), (134, 168), (118, 163)]), 0.36)
    sp(c.rect_m(124, 151, 340, 151), 0.78)
    sp(c.line_m([(112, 158), (124, 151)]), 0.66)
    sp(c.rect_m(134, 168, 340, 168), 0.18)
    sp(c.rect_m(126, 159, 340, 159), 0.26); sp(c.rect_m(126, 160, 340, 160), 0.44)   # hull strake
    # spherical tanks in cradles along the deck
    for i, tx in enumerate((192, 240, 288, 336)):
        r = 22.0; ty = 133.0
        m = ((xx - tx) ** 2 + (yy - ty) ** 2 <= r * r) & (yy < 152)
        nx = (xx - tx) / r; ny = (yy - ty) / r
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
        lam = np.clip(nx * Ls[0] + ny * Ls[1] + nz * Ls[2], 0, 1)
        val = 0.20 + 0.80 * lam ** 1.7
        m &= hole
        c.v[m] = val[m]; c.m[m] = SHIP; ship[m] = True
        sp(c.rect_m(tx - 23, 132, tx + 23, 133), 0.30)                 # equator band
        sp(c.rect_m(tx - 23, 132, tx - 6, 132), 0.56)
        sp(c.poly_m([(tx - 16, 151), (tx - 11, 143), (tx + 11, 143), (tx + 16, 151)]), 0.30)   # cradle
        sp(c.line_m([(tx - 16, 151), (tx - 11, 143), (tx + 11, 143)]), 0.52)
        sp(c.rect_m(tx - 1, 107, tx, 111), 0.5)                         # vent stack
    sp(c.rect_m(170, 109, 340, 109), 0.40)                              # pipe linking the tank tops
    sp(c.rect_m(170, 108, 340, 108), 0.66)
    # bridge tower
    sp(c.poly_m([(128, 151), (133, 137), (141, 130), (162, 130), (166, 151)]), 0.42)
    sp(c.line_m([(133, 137), (141, 130), (162, 130)]), 0.86)
    sp(c.line_m([(128, 151), (133, 137)]), 0.66)
    sp(c.rect_m(163, 131, 165, 150), 0.24)
    sp(c.rect_m(146, 122, 158, 129), 0.40); sp(c.rect_m(146, 122, 158, 122), 0.78)
    sp(c.rect_m(152, 104, 152, 121), 0.5); sp(c.rect_m(148, 110, 156, 110), 0.5)   # antenna
    sp(c.rect_m(166, 140, 172, 142), 0.5)                               # gangway to the first tank
    # fuel umbilical from the sill up to the ship's belly
    sp(c.line_m([(214, 178), (214, 172), (218, 168)]), 0.55)
    sp(c.line_m([(262, 178), (262, 172), (266, 168)]), 0.55)

    arr = c.render({WALL: DOCK_FAR, SHIP: DOCK_SHIP}, width={WALL: 0.8, SHIP: 0.45})

    # --- points of light -----------------------------------------------------
    for lx, ly in lamps[:3]:
        light(arr, lx, ly - 2, "#8ff7ea", "#0f7480", big=True)
        arr[ly - 3, lx % W] = hexc("#12a3a6"); arr[ly - 3, (lx + 1) % W] = hexc("#12a3a6")
    # booth windows: one long glass band, warm light inside, a couple of dark panes
    panes = [1, 1, 0, 1, 2, 1, 0, 1]
    for i, st in enumerate(panes):
        x0 = 374 + i * 12
        cols = ["#15263c", "#122035", "#0f1a2e"] if st == 0 else ["#82663f", "#674d36", "#4e392e"]
        for y in range(87, 100):
            k = 0 if y < 90 else 1 if y < 95 else 2
            arr[y, x0:x0 + 10] = hexc(cols[k])
        if st:
            arr[87, x0:x0 + 10] = hexc("#a5824c")
            arr[97:100, x0 + 1:x0 + 5 + (i % 3)] = hexc("#33262a")      # consoles
            arr[96, x0 + 2:x0 + 4] = hexc("#33262a")
        if st == 2:
            arr[92:97, x0 + 6:x0 + 8] = hexc("#33262a")                 # an officer at the glass
            arr[90:92, x0 + 6:x0 + 8] = hexc("#33262a")
            arr[88, x0 + 2] = hexc("#f0cf88")
    for x0 in (374 + 12, 374 + 5 * 12):
        arr[88, x0 + 7] = hexc("#f0cf88")                                # ceiling lamps
    # running lights along the sill, force-field emitters in the corners
    for x in range(OX0 + 22, OX1 - 16, 31):
        arr[OY1 + 2, x] = hexc("#2de0d0"); arr[OY1 + 2, x + 1] = hexc("#12a3a6")
        arr[OY1 + 3, x] = hexc("#0e4a5c")
    for x in (OX0 + 22, OX1 - 23):
        arr[OY0 - 3, x] = hexc("#12a3a6"); arr[OY0 - 3, x + 1] = hexc("#0f7480")
    # door status lamp (red = closed), mast beacon
    light(arr, 420, 133, "#e8384f", "#7a1228")
    light(arr, 452, 61, "#ff7a7a", None)
    # tanker lights
    for (x, y, col) in ((136, 140, "#b89050"), (139, 140, "#94703f"), (142, 140, "#b89050"), (145, 140, "#94703f"),
                        (150, 125, "#94703f"), (154, 125, "#b89050"),
                        (112, 158, "#e8384f"), (152, 103, "#8ff7ea"),
                        (192, 147, "#12a3a6"), (240, 147, "#12a3a6"), (288, 147, "#e8384f"),
                        (216, 170, "#2de0d0"), (264, 170, "#2de0d0")):
        if hole[y, x]:
            arr[y, x] = hexc(col)
    return to_img(arr)


def auto_rim(c, top=0.80, left=0.08, thick=3):
    """Rim light: every silhouette edge that faces up gets a bright line, left edges a faint one.
    Thin things (cables) are skipped so they stay dark."""
    op = c.m > 0
    up = np.roll(op, 1, 0); up[0] = True
    solid = op.copy()
    for k in range(1, thick):
        dn = np.roll(op, -k, 0); dn[-k:] = True
        solid &= dn
    top_edge = op & ~up & solid
    c.v[top_edge] = np.maximum(c.v[top_edge], top)
    lf = np.roll(op, 1, 1)
    solidx = op & np.roll(op, -1, 1) & np.roll(op, -2, 1)
    left_edge = op & ~lf & solidx & ~top_edge
    c.v[left_edge] += left
    return top_edge


def tint_cone(arr, lx, ly, col, reach=70, spread=0.55, strength=0.4, wrap=True):
    """Coloured lamp light falling on whatever is below it (dithered, keeps the palette small)."""
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    col = np.array(hexc(col)[:3], np.float32)
    for dx in ((-w, 0, w) if wrap else (0,)):
        dy = (yy - ly).astype(np.float32)
        s_ = np.clip(1 - np.abs(xx - lx - dx) / (6 + np.maximum(dy, 0) * spread), 0, 1) * (dy > 0) * np.clip(1 - dy / reach, 0, 1)
        m = ((s_ > 0.42) | ((s_ > 0.2) & (bayer(h, w) > 0.5))) & (arr[..., 3] > 0)
        rgb = arr[..., :3].astype(np.float32)
        rgb[m] = rgb[m] * (1 - strength) + col * strength
        arr[..., :3] = rgb.astype(np.uint8)


def vcyl(c, x0, x1, y0, y1, base, amp=0.3, mat=1, mask=None):
    """Vertical cylinder lit from the left: soft highlight, core shadow, faint bounce on the far edge."""
    m = c.rect_m(x0, y0, x1, y1) if mask is None else mask
    t = (c.xx - (x0 + x1) / 2.0) / max((x1 - x0) / 2.0, 1)
    th = np.arcsin(np.clip(t, -1, 1))
    lam = np.clip(np.cos(th + 0.75), 0, 1)
    val = base - amp * 0.45 + amp * lam + 0.10 * amp * smooth(0.75, 1.0, t)
    c.v[m] = val[m]; c.m[m] = mat


def hcyl(c, x0, x1, y0, y1, base, amp=0.3, mat=1, mask=None):
    """Horizontal cylinder (pipe) lit from above."""
    m = c.rect_m(x0, y0, x1, y1) if mask is None else mask
    t = (c.yy - (y0 + y1) / 2.0) / max((y1 - y0) / 2.0, 1)
    th = np.arcsin(np.clip(t, -1, 1))
    lam = np.clip(np.cos(th + 0.75), 0, 1)
    val = base - amp * 0.45 + amp * lam + 0.10 * amp * smooth(0.75, 1.0, t)
    c.v[m] = val[m]; c.m[m] = mat


def catenary(x0, y0, x1, y1, sag, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)))
    return pts


def container(c, x0, y0, x1, y1, v, rib=6, mat=1):
    """Shipping container: ribbed side, lit top rail, corner posts."""
    c.rect(x0, y0, x1, y1, v, mat)
    for xr in range(x0 + 4, x1 - 2, rib):
        c.rect(xr, y0 + 4, xr, y1 - 3, v - 0.10, mat)
        c.rect(xr + 1, y0 + 4, xr + 1, y1 - 3, v + 0.05, mat)
    c.rect(x0, y0, x1, y0, v + 0.36, mat)           # top rail catches the light
    c.rect(x0, y0 + 1, x1, y0 + 1, v + 0.14, mat)
    c.rect(x0, y0 + 2, x1, y0 + 2, v - 0.10, mat)
    c.rect(x0, y0 + 1, x0, y1, v + 0.20, mat)
    c.rect(x0 + 1, y0 + 2, x0 + 1, y1, v + 0.06, mat)
    c.rect(x1 - 1, y0 + 1, x1, y1, v - 0.14, mat)
    c.rect(x0, y1, x1, y1, v - 0.20, mat)
    c.rect(x0, y1 - 1, x1, y1 - 1, v - 0.08, mat)


# ============================================================================
# dock_mid  640x270  transparent, tiles in X
# ============================================================================
def make_dock_mid():
    W, H = 640, 270
    c = VC(W, H)
    yy, xx = c.yy, c.xx
    B = 0.44                                         # body value of the silhouettes

    # --- overhead crane rail (runs the full width) ---------------------------
    for x in (52, 212, 372, 532):                    # hangers up to the ceiling
        c.rect(x, 0, x + 4, 18, B - 0.06); c.rect(x, 0, x, 18, B + 0.12)
        c.box(x - 3, 15, x + 7, 18, B + 0.06, hi=0.14, lo=0.14)
    c.rect(0, 18, W - 1, 28, B - 0.04)
    c.rect(0, 18, W - 1, 18, B + 0.34); c.rect(0, 19, W - 1, 19, B + 0.10)
    c.rect(0, 20, W - 1, 20, B - 0.16)
    c.rect(0, 27, W - 1, 27, B + 0.16); c.rect(0, 28, W - 1, 28, B - 0.20)
    for x in range(20, W, 80):                       # web stiffeners
        c.rect(x, 21, x, 26, B + 0.10); c.rect(x + 1, 21, x + 1, 26, B - 0.14)

    # --- crane trolley, cab, hook and a container on the hook -----------------
    tx = 178
    c.box(tx - 26, 10, tx + 26, 17, B + 0.04, hi=0.2, lo=0.14)
    c.box(tx - 30, 29, tx + 30, 37, B + 0.02, hi=0.2, lo=0.16)
    c.rect(tx - 22, 18, tx - 18, 28, B + 0.06); c.rect(tx + 18, 18, tx + 22, 28, B - 0.08)
    for wx in (tx - 20, tx + 20):                    # wheels
        c.put(c.ell_m(wx - 4, 13, wx + 4, 21), B - 0.14)
    c.box(tx + 6, 38, tx + 28, 56, B, hi=0.16, lo=0.16)          # operator cab
    c.poly([(tx + 6, 57), (tx + 28, 57), (tx + 24, 60), (tx + 10, 60)], B - 0.1)
    for cxp in (tx - 16, tx - 8):                    # hoist cables
        c.rect(cxp, 38, cxp, 70, B + 0.02)
    c.box(tx - 20, 70, tx - 4, 76, B + 0.06, hi=0.2, lo=0.16)    # hook block
    c.rect(tx - 13, 77, tx - 11, 80, B)
    c.line([(tx - 12, 80), (tx - 34, 91)], B + 0.04)
    c.line([(tx - 12, 80), (tx + 10, 91)], B - 0.04)
    container(c, tx - 36, 91, tx + 12, 111, B - 0.02)

    # --- fuel main: fat pipe hanging under the rail, dropping to a hose reel --
    for x in (262, 330, 398):
        c.rect(x, 29, x + 1, 42, B - 0.02)
    hcyl(c, 248, 440, 43, 51, B + 0.02, 0.40)
    hcyl(c, 268, 440, 55, 58, B - 0.02, 0.30)
    for x in (270, 334, 402):
        c.box(x - 2, 41, x + 2, 53, B + 0.10, hi=0.16, lo=0.2)   # flanges
    vcyl(c, 244, 253, 47, 84, B + 0.02, 0.40)
    c.put(c.ell_m(243, 42, 254, 53), B + 0.08)                     # elbow
    c.put(c.ell_m(244, 43, 250, 48), B + 0.24)
    c.box(241, 66, 256, 69, B + 0.10, hi=0.16, lo=0.2)
    c.box(240, 84, 257, 91, B + 0.06, hi=0.18, lo=0.2)             # nozzle head
    c.put(c.poly_m([(244, 92), (253, 92), (251, 97), (246, 97)]), B - 0.06)
    c.line(catenary(249, 97, 300, 84, 40), B - 0.04)               # fuel hose swinging away
    c.line([(300, 84), (300, 59)], B - 0.04)
    # pipes turn up into the ceiling at the gantry
    vcyl(c, 440, 448, 0, 51, B + 0.02, 0.40)
    vcyl(c, 452, 455, 0, 58, B - 0.02, 0.30)
    c.rect(440, 55, 455, 58, B - 0.04)

    # --- hanging cables ---------------------------------------------------------
    c.line(catenary(540, 29, 660, 29, 30), B - 0.04)
    c.line(catenary(556, 29, 700, 29, 52), B - 0.08)
    c.rect(600, 29, 600, 84, B - 0.02)                                   # chain with a hook
    c.put(c.ell_m(597, 84, 603, 91), B + 0.04); c.cut(c.ell_m(599, 86, 601, 89))
    c.line(catenary(60, 29, 130, 29, 18), B - 0.06)
    c.rect(352, 59, 352, 92, B - 0.04)                                   # lamp on a drop cable
    c.poly([(348, 93), (356, 93), (359, 98), (345, 98)], B + 0.06)

    # everything above hangs from the rail: drop the whole group so it clears the far truss
    SH = 14
    c.v = np.roll(c.v, SH, axis=0); c.m = np.roll(c.m, SH, axis=0)
    c.v[:SH] = 0; c.m[:SH] = 0
    for x in (52, 212, 372, 532):
        c.rect(x, 0, x + 4, SH, B - 0.06); c.rect(x, 0, x, SH, B + 0.12)
    vcyl(c, 440, 448, 0, SH, B + 0.02, 0.40)
    vcyl(c, 452, 455, 0, SH, B - 0.02, 0.30)

    # --- gantry tower (lattice) -------------------------------------------------
    gx0, gx1 = 470, 510
    for y0 in range(29 + SH, H, 34):
        y1 = y0 + 34
        c.line([(gx0 + 2, y0), (gx1 - 2, y1)], B - 0.06, width=2)
        c.line([(gx1 - 2, y0), (gx0 + 2, y1)], B + 0.04, width=2)
        c.rect(gx0, y0, gx1, y0 + 1, B + 0.08)
    c.rect(gx0, 29 + SH, gx0 + 4, H - 1, B + 0.04); c.rect(gx0, 29 + SH, gx0, H - 1, B + 0.30)
    c.rect(gx1 - 4, 29 + SH, gx1, H - 1, B - 0.02); c.rect(gx1 - 4, 29 + SH, gx1 - 4, H - 1, B + 0.16)
    c.rect(gx1, 29 + SH, gx1, H - 1, B - 0.18)
    c.box(gx0 - 8, 116, gx1 + 8, 120, B + 0.08, hi=0.26, lo=0.18)      # service platform
    for x in range(gx0 - 8, gx1 + 9, 8):
        c.rect(x, 108, x, 115, B + 0.02)
    c.rect(gx0 - 8, 107, gx1 + 8, 107, B + 0.16)
    c.box(gx1 + 8, 124, gx1 + 16, 142, B, hi=0.14, lo=0.16)             # junction box
    c.line(catenary(gx1 + 12, 143, 600, 30 + SH, 60), B - 0.06)        # slack cable back up to the rail

    # --- fuel storage tank --------------------------------------------------------
    T0, T1 = 318, 372
    dome = c.ell_m(T0, 150, T1, 186)
    vcyl(c, T0, T1, 150, 186, B, 0.34, mask=dome & (yy <= 168))
    vcyl(c, T0, T1, 168, H - 1, B, 0.34)
    for y in (172, 214, 256):
        m = c.rect_m(T0 - 1, y, T1 + 1, y + 3)
        vcyl(c, T0 - 1, T1 + 1, y, y + 3, B + 0.10, 0.38)
        c.rect(T0 - 1, y + 3, T1 + 1, y + 3, B - 0.16)
    c.rect(343, 142, 347, 151, B + 0.04); c.box(339, 139, 351, 142, B + 0.1, hi=0.2, lo=0.16)   # top valve
    c.rect(T1 + 3, 160, T1 + 4, H - 1, B - 0.02)                          # ladder
    c.rect(T1 + 9, 160, T1 + 10, H - 1, B - 0.08)
    for y in range(162, H, 6):
        c.rect(T1 + 3, y, T1 + 10, y, B + 0.04)
    c.rect(326, 190, 330, 208, B - 0.26)                                   # gauge slot (lit below)

    # --- container stacks -----------------------------------------------------------
    TEAL, PLUM = 2, 3
    container(c, 12, 242, 70, 269, B - 0.02)
    container(c, 72, 242, 132, 269, B + 0.02, mat=PLUM)
    container(c, 20, 214, 80, 241, B + 0.03, mat=TEAL)
    container(c, 82, 214, 126, 241, B - 0.03, rib=5)
    container(c, 26, 186, 86, 213, B, mat=PLUM)
    container(c, 34, 160, 80, 185, B + 0.04, rib=5)
    c.box(88, 204, 100, 213, B + 0.02, hi=0.2, lo=0.16)                  # loose crate + drum on the stack
    vcyl(c, 104, 113, 200, 213, B + 0.02, 0.36)
    # right-hand stack + drums
    container(c, 548, 240, 610, 269, B, mat=TEAL)
    container(c, 612, 240, 668, 269, B - 0.03)
    container(c, 556, 212, 616, 239, B + 0.03)
    container(c, 572, 186, 622, 211, B - 0.02, rib=5, mat=PLUM)
    for bx in (414, 430):
        vcyl(c, bx, bx + 13, 236, H - 1, B + 0.02, 0.36)
        c.rect(bx, 236, bx + 13, 236, B + 0.26); c.rect(bx, 246, bx + 13, 246, B - 0.12); c.rect(bx, 258, bx + 13, 258, B - 0.12)
    vcyl(c, 422, 435, 218, 235, B + 0.04, 0.36)
    c.rect(422, 218, 435, 218, B + 0.28); c.rect(422, 227, 435, 227, B - 0.12)

    # --- light: brighter up top, sinking into the dark towards the floor ---------
    auto_rim(c, top=B + 0.40)
    op = c.m > 0
    fade = 1 - 0.50 * smooth(150, 268, yy.astype(np.float32))
    c.v = np.where(op, c.v * fade, 0)
    arr = c.render({1: DOCK_MID, TEAL: DOCK_MID_TEAL, PLUM: DOCK_MID_PLUM}, width=0.55)
    tint_cone(arr, 352, 100 + SH, "#12a3a6", reach=120, spread=0.5, strength=0.2)

    # --- points of light -----------------------------------------------------------
    arr[42 + SH:50 + SH, tx + 9:tx + 26] = hexc("#172a42")               # cab glass
    arr[42 + SH, tx + 9:tx + 26] = hexc("#24405c")
    arr[44 + SH, tx + 20] = hexc("#e8b860"); arr[44 + SH, tx + 21] = hexc("#94703f"); arr[45 + SH, tx + 20] = hexc("#94703f")
    light(arr, tx - 30, 31 + SH, "#ffcf33", "#96620a")                   # trolley warning lamp
    light(arr, gx0 + 20, 105, "#e8384f", "#7a1228")                      # tower beacon
    arr[106, gx0 + 20] = hexc("#445c8b")
    for y in range(196, 208, 2):                                         # tank gauge
        arr[y, 327:330] = hexc("#0f7480")
    arr[204:208, 327:330] = hexc("#12a3a6"); arr[206, 328] = hexc("#2de0d0")
    light(arr, 248, 87 + SH, "#2de0d0", None); arr[87 + SH, 249] = hexc("#12a3a6")   # nozzle ready light
    arr[99 + SH, 347:358] = hexc("#8ff7ea"); arr[100 + SH, 349:356] = hexc("#12a3a6")  # drop lamp
    light(arr, gx1 + 12, 128, "#3fc468", None)
    return to_img(arr)


def lattice(c, xc, y_top, y_bot, w_top, w_bot, bay, v, mat=1):
    """Tapering lattice pylon: two legs, horizontals and zig-zag bracing."""
    def half(y):
        t = (y - y_top) / max(1, (y_bot - y_top))
        return (w_top + (w_bot - w_top) * t) / 2.0
    y = y_top
    flip = False
    while y < y_bot:
        y2 = min(y_bot, y + bay)
        a0, a1 = half(y), half(y2)
        if flip:
            c.line([(xc - a0, y), (xc + a1, y2)], v - 0.08, mat)
        else:
            c.line([(xc + a0, y), (xc - a1, y2)], v - 0.08, mat)
        c.line([(xc - a0, y), (xc + a0, y)], v, mat)
        flip = not flip
        y = y2
        bay = int(bay * 1.12) + 1
    c.line([(xc - half(y_top), y_top), (xc - half(y_bot), y_bot)], v + 0.12, mat, width=2)
    c.line([(xc + half(y_top), y_top), (xc + half(y_bot), y_bot)], v - 0.04, mat, width=2)


# ============================================================================
# bridge_far  480x270  transparent sky, tiles in X
# ============================================================================
def make_bridge_far():
    W, H = 480, 270
    c = VC(W, H)
    yy, xx = c.yy, c.xx
    yf = yy.astype(np.float32); xf = xx.astype(np.float32)
    RING, PANEL = 3, 2
    S = 0.52

    # --- the great ring: a section sweeping out from behind the tower and down
    #     below the skyline (it is the farthest thing, so it uses the dimmest ramp)
    rcx, rcy, RR = 60.0, 818.0, 701.0
    dist = np.sqrt((xf - rcx) ** 2 + (yf - rcy) ** 2)
    d = RR - dist                                           # 0 at the outer edge, grows inwards
    arc = RR * np.arctan2(xf - rcx, rcy - yf)               # px along the ring
    vis = (xf > 20) & (xf < 430)
    band = (d >= 0) & (d < 23) & vis
    c.put(band, 0.40, RING)
    c.put(band & (d < 8), 0.70, RING)                       # sunlit upper deck
    c.put(band & (d < 1.6), 1.0, RING)                      # bright outer edge
    c.put(band & (d >= 8) & (d < 9.2), 0.26, RING)          # shadow under the deck lip
    c.put(band & (d >= 19), 0.22, RING)                     # underside
    seg = np.mod(arc + 14, 46.0)
    c.put(band & (seg < 1.2) & (d >= 1.6), 0.24, RING)      # segment joints
    c.put(band & (seg >= 1.2) & (seg < 2.4) & (d >= 1.6) & (d < 19), 0.52, RING)
    # little pods and masts riding on the outer deck
    for a0, wdt, hgt in ((70, 16, 5), (150, 9, 8), (226, 22, 4), (300, 10, 6)):
        pod = (arc > a0) & (arc < a0 + wdt) & (d < 0) & (d > -hgt) & vis
        c.put(pod, 0.50, RING)
        c.put(pod & (d < -hgt + 1.3), 0.8, RING)
    for a0, hgt in ((110, 14), (262, 10)):
        c.put((np.abs(arc - a0) < 0.7) & (d < 0) & (d > -hgt) & vis, 0.5, RING)
    # spokes dropping to the hub far below
    for a0 in (96, 196, 290):
        sp_ = (np.abs(arc - a0) < 3.2) & (d >= 23) & (yf < 210) & vis
        c.put(sp_, 0.30, RING)
        c.put(sp_ & (arc - a0 < -1.6), 0.46, RING)
        c.put((np.abs(arc - a0) < 7) & (d >= 23) & (d < 27) & vis, 0.34, RING)

    # --- skyline of hull and modules ---------------------------------------------
    c.rect(0, 206, W - 1, H - 1, S - 0.08)                  # base hull
    for (x0, x1, y0, v) in ((64, 108, 196, S - 0.02), (292, 330, 192, S - 0.04), (330, 378, 186, S + 0.02),
                            (378, 410, 194, S - 0.05), (410, 432, 184, S)):
        c.box(x0, y0, x1, 210, v, hi=0.22, lo=0.12)
    # observation dome
    dcx, dcy, dr = 132.0, 198.0, 23.0
    dome = ((xf - dcx) ** 2 + (yf - dcy) ** 2 <= dr * dr) & (yy <= 198)
    nx = (xf - dcx) / dr; ny = (yf - dcy) / dr
    lam = np.clip(-0.55 * nx - 0.62 * ny + 0.56 * np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1)), 0, 1)
    c.v[dome] = (S - 0.18 + 0.52 * lam ** 1.3)[dome]; c.m[dome] = 1
    c.box(106, 198, 158, 206, S + 0.04, hi=0.2, lo=0.14)
    c.rect(131, 164, 132, 175, S)                           # dome mast
    # long habitat cylinder with domed ends
    cap = c.ell_m(166, 180, 188, 204) | c.ell_m(266, 180, 288, 204) | c.rect_m(177, 180, 277, 204)
    hcyl(c, 166, 288, 180, 204, S + 0.02, 0.38, mask=cap)
    for x in (196, 226, 256):
        c.rect(x, 180, x + 1, 204, S - 0.12)
        c.rect(x + 2, 181, x + 2, 203, S + 0.10)
    c.rect(172, 204, 282, 207, S - 0.14)
    c.box(214, 174, 240, 180, S, hi=0.22, lo=0.12)          # docking collar on top
    # relay mast
    c.rect(420, 152, 421, 184, S - 0.02); c.rect(415, 160, 426, 160, S - 0.02); c.rect(417, 166, 424, 166, S - 0.06)

    # --- solar array -----------------------------------------------------------------
    mx = 353
    c.rect(mx - 1, 112, mx + 1, 186, S + 0.02)
    c.rect(mx - 1, 112, mx - 1, 186, S + 0.2)
    c.box(mx - 6, 126, mx + 6, 132, S + 0.06, hi=0.2, lo=0.14)
    for pts in ([(mx - 62, 122), (mx - 8, 114), (mx - 8, 140), (mx - 62, 148)], [(mx + 8, 112), (mx + 62, 104), (mx + 62, 130), (mx + 8, 138)]):
        m = c.poly_m(pts)
        x0 = pts[0][0]; x1 = pts[1][0]; yt0 = pts[0][1]; yt1 = pts[1][1]
        slope = (yt1 - yt0) / (x1 - x0)
        local_y = yf - (yt0 + (xf - x0) * slope)            # 0 at the top edge
        sheen = smooth(0.0, 1.0, 1 - np.abs(((xf - x0) / (x1 - x0)) - 0.42 + (local_y / 26.0 - 0.5) * 0.5) / 0.3)
        val = 0.34 + 0.22 * sheen - 0.004 * local_y
        c.v[m] = val[m]; c.m[m] = PANEL
        cell = m & ((((xx - x0) % 9) == 0) | ((np.floor(local_y) % 9) == 8))
        c.v[cell] = 0.16
        c.v[m & (local_y < 1)] = 0.78
        c.v[m & (local_y >= 25)] = 0.14
    c.line([(mx - 8, 127), (mx + 8, 125)], S + 0.1)

    # --- habitat tower on the seam -----------------------------------------------------
    c.box(452, 96, 506, 210, S + 0.04, hi=0.2, lo=0.14)     # main shaft (wraps round the seam)
    c.rect(452, 96, 468, 210, S + 0.12)                     # sunlit left face
    c.rect(452, 96, 452, 210, S + 0.24)
    c.rect(492, 96, 506, 210, S - 0.10)                     # shadow face
    c.box(446, 110, 512, 116, S + 0.10, hi=0.22, lo=0.16)   # collars
    c.box(446, 160, 512, 166, S + 0.10, hi=0.22, lo=0.16)
    c.poly([(456, 96), (464, 84), (494, 84), (502, 96)], S + 0.02)   # tapered crown
    c.line([(456, 96), (464, 84), (494, 84)], S + 0.3)
    c.box(470, 74, 488, 84, S, hi=0.24, lo=0.14)
    c.rect(478, 50, 479, 74, S + 0.04)                      # mast
    c.rect(474, 60, 483, 60, S + 0.04)
    c.box(430, 150, 452, 210, S - 0.02, hi=0.22, lo=0.12)   # annex left
    c.box(506, 132, 524, 210, S - 0.08, hi=0.2, lo=0.12)    # annex right (x 26..44 after the wrap)
    c.box(524, 176, 544, 210, S - 0.04, hi=0.2, lo=0.12)

    rim = auto_rim(c, top=S + 0.26)
    c.v[rim & (c.m == RING)] = 1.0
    # --- everything sinks into the dark towards the bottom ------------------------------
    op = c.m > 0
    fade = 1 - 0.58 * smooth(196, 268, yf)
    haze = Noise(71, 4, 3, 2).at(xf / W, yf / W) - 0.5
    c.v = np.where(op, (c.v + haze * 0.05) * fade, 0)
    c.v[c.m == RING] *= (0.80 + 0.20 * smooth(330, 60, xf))[c.m == RING]    # ring dims as it recedes
    PANEL_RAMP = ["#0a0d1f", "#0c1230", "#0f1840", "#132152", "#182c66", "#1e3878", "#28488c", "#36609e"]
    RING_FAR = ["#090b18", "#0b0e20", "#0d1228", "#0f1631", "#121b3b", "#162247", "#1b2b54", "#213562", "#294272"]
    arr = c.render({1: BRIDGE_FAR, PANEL: PANEL_RAMP, RING: RING_FAR}, width=0.6)

    # --- points of light -------------------------------------------------------------------
    rng = np.random.default_rng(8)
    warm = ["#b89050", "#94703f", "#775535"]
    # two rows of windows along the ring wall
    for row, dd in enumerate((12.0, 16.0)):
        a_ = 30.0
        while a_ < 380:
            a_ += 5.0
            if np.mod(a_ + 14, 46.0) < 6 or rng.random() < (0.50 if row == 0 else 0.68):
                continue
            th = a_ / RR
            x = int(round(rcx + (RR - dd) * math.sin(th))); y = int(round(rcy - (RR - dd) * math.cos(th)))
            if 22 < x < 428 and arr[y, x, 3] and c.m[y, x] == RING:
                arr[y, x] = hexc(warm[int(rng.integers(0, 3))])
                if rng.random() < 0.45 and c.m[y, x + 1] == RING:
                    arr[y, x + 1] = hexc(warm[2])
    for a_ in (64, 156, 248, 332):                           # cyan running lights on the outer deck
        th = a_ / RR
        x = int(round(rcx + (RR - 4) * math.sin(th))); y = int(round(rcy - (RR - 4) * math.cos(th)))
        if c.m[y, x] == RING:
            arr[y, x] = hexc("#2de0d0"); arr[y, x + 1] = hexc("#12a3a6"); arr[y + 1, x] = hexc("#0f7480")
    # tower windows: neat rows, most dark
    for row, y in enumerate(range(100, 204, 7)):
        if y in (107, 114, 156, 163):
            continue
        for col, x in enumerate(range(456, 504, 5)):
            r = rng.random()
            xx_ = x % W
            if r < 0.34:
                arr[y, xx_] = hexc(warm[0] if r < 0.12 else warm[1]); arr[y, (xx_ + 1) % W] = hexc(warm[2] if r > 0.2 else warm[1])
            elif r < 0.5:
                arr[y, xx_] = hexc("#1c3a5c"); arr[y, (xx_ + 1) % W] = hexc("#1c3a5c")
    for (x, y) in ((434, 158), (438, 158), (434, 170), (442, 182), (510 - W, 142), (514 - W, 142), (510 - W, 156), (516 - W, 170),
                   (530 - W, 184), (70, 201), (82, 201), (300, 198), (308, 198), (338, 194), (346, 194), (384, 200), (392, 200), (416, 190), (424, 190)):
        arr[y, x] = hexc(warm[int(rng.integers(0, 3))])
    for x in range(172, 284, 6):                              # habitat cylinder portholes
        if rng.random() < 0.6:
            arr[191, x] = hexc(warm[int(rng.integers(0, 3))])
    for (x, y) in ((122, 190), (128, 185), (136, 183), (142, 188), (120, 195), (132, 193), (144, 195)):   # dome interior
        arr[y, x] = hexc("#12a3a6" if (x + y) % 3 else "#8ff7ea")
    light(arr, 478, 49, "#ff7a7a", None); arr[50, 478] = hexc("#b81f38")
    light(arr, 420, 151, "#2de0d0", None)
    light(arr, 131, 163, "#e8384f", None)
    arr[111, mx] = hexc("#8ff7ea")
    return to_img(arr)


def dish(c, cx_, cy_, R, ax, v, mat=1):
    """Antenna dish seen from behind-the-side. ax = unit axis the dish points along."""
    yy, xx = c.yy.astype(np.float32), c.xx.astype(np.float32)
    dxn, dyn = ax
    pxn, pyn = -dyn, dxn                                     # rim direction
    out = None
    for off in ((-c.w, 0, c.w) if c.wrap else (0,)):
        a = (xx - cx_ - off) * pxn + (yy - cy_) * pyn
        b = (xx - cx_ - off) * dxn + (yy - cy_) * dyn
        back = ((a / R) ** 2 + (b / (0.62 * R)) ** 2 <= 1) & (b <= 0)
        face = ((a / R) ** 2 + (b / (0.26 * R)) ** 2 <= 1)
        shade = v - 0.10 + 0.24 * smooth(0.9, -0.9, (a / R) * (1 if pyn > 0 else -1)) - 0.18 * smooth(0.0, -0.6, b / R)
        c.v[back] = shade[back]; c.m[back] = mat
        inner = v + 0.16 - 0.26 * smooth(-0.26, 0.26, b / R)
        c.v[face] = inner[face]; c.m[face] = mat
        rim = face & ~(((a / (R - 1.6)) ** 2 + (b / (0.26 * R - 1.2)) ** 2) <= 1)
        c.v[rim & (b <= 0.02)] = v + 0.40
        c.v[rim & (b > 0.02)] = v + 0.14
        for t in (-0.55, 0.0, 0.55):                         # ribs on the back of the bowl
            ribm = back & ~face & (np.abs(a / R - t * (1 - (b / (0.62 * R)) ** 2)) < 0.035)
            c.v[ribm] -= 0.10
    fx, fy = cx_ + dxn * R * 0.78, cy_ + dyn * R * 0.78       # feed horn on three struts
    for t in (-0.85, 0.85, 0.1):
        c.line([(cx_ + pxn * R * t, cy_ + pyn * R * t), (fx, fy)], v + 0.04, mat)
    c.box(int(fx) - 2, int(fy) - 2, int(fx) + 2, int(fy) + 2, v + 0.1, mat, hi=0.2, lo=0.14)
    return fx, fy


# ============================================================================
# bridge_mid  640x270  transparent, tiles in X
# ============================================================================
def make_bridge_mid():
    W, H = 640, 270
    c = VC(W, H)
    yy, xx = c.yy, c.xx
    B = 0.44

    # --- long truss boom along the bottom ---------------------------------------
    TY0, TY1 = 222, 242
    for k in range(0, W, 40):
        c.line([(k, TY1), (k + 20, TY0 + 2), (k + 40, TY1)], B - 0.08, width=2)
        c.rect(k - 1, TY0, k + 1, TY1, B + 0.02)
        c.rect(k + 19, TY0, k + 20, TY1, B - 0.06)
    c.rect(0, TY0, W - 1, TY0 + 3, B + 0.04); c.rect(0, TY0, W - 1, TY0, B + 0.30); c.rect(0, TY0 + 3, W - 1, TY0 + 3, B - 0.16)
    c.rect(0, TY1, W - 1, TY1 + 3, B - 0.02); c.rect(0, TY1, W - 1, TY1, B + 0.22); c.rect(0, TY1 + 3, W - 1, TY1 + 3, B - 0.2)
    # second, lower boom half out of frame
    c.rect(0, 258, W - 1, H - 1, B - 0.10); c.rect(0, 258, W - 1, 258, B + 0.14)
    for k in range(20, W, 80):
        c.rect(k, 246, k + 2, 258, B - 0.10)

    # --- pylon A: tall lattice mast with cross-arms and a beacon ------------------
    ax_ = 96
    lattice(c, ax_, 88, TY0, 8, 30, 14, B + 0.02)
    c.box(ax_ - 9, 82, ax_ + 9, 88, B + 0.08, hi=0.3, lo=0.16)
    c.rect(ax_, 60, ax_ + 1, 82, B + 0.04)
    c.box(ax_ - 22, 104, ax_ + 22, 106, B + 0.06, hi=0.26, lo=0.14)     # cross-arms
    c.box(ax_ - 16, 126, ax_ + 16, 128, B + 0.04, hi=0.26, lo=0.14)
    for x in (ax_ - 22, ax_ + 21):
        c.rect(x, 96, x, 104, B); c.rect(x, 107, x + 1, 112, B - 0.04)
    for x in (ax_ - 16, ax_ + 15):
        c.rect(x, 129, x + 1, 135, B - 0.04)
    c.box(ax_ - 18, TY0 - 8, ax_ + 18, TY0, B + 0.04, hi=0.3, lo=0.16)       # footing

    # --- big dish ------------------------------------------------------------------
    dxc, dyc = 338, 152
    c.poly([(dxc - 5, 178), (dxc + 7, 178), (dxc + 12, TY0), (dxc - 12, TY0)], B - 0.02)   # pedestal
    c.line([(dxc - 5, 178), (dxc - 12, TY0)], B + 0.18)
    c.box(dxc - 16, TY0 - 8, dxc + 16, TY0, B + 0.04, hi=0.3, lo=0.16)
    c.box(dxc - 9, 170, dxc + 11, 178, B + 0.06, hi=0.3, lo=0.16)                           # yoke
    c.put(c.ell_m(dxc - 5, 160, dxc + 7, 172), B)
    n = math.hypot(-0.62, -0.78)
    dish(c, dxc - 6, dyc - 6, 40, (-0.62 / n, -0.78 / n), B)
    c.line([(dxc + 1, 166), (dxc + 16, 150), (dxc + 12, 132)], B - 0.06, width=2)            # elevation jack

    # --- pylon C: slim mast with a small dish and whip antennas -----------------------
    cx_ = 536
    c.rect(cx_ - 2, 112, cx_ + 2, TY0, B); c.rect(cx_ - 2, 112, cx_ - 2, TY0, B + 0.2); c.rect(cx_ + 2, 112, cx_ + 2, TY0, B - 0.14)
    c.box(cx_ - 6, 150, cx_ + 6, 154, B + 0.06, hi=0.26, lo=0.16)
    c.box(cx_ - 6, 186, cx_ + 6, 190, B + 0.06, hi=0.26, lo=0.16)
    c.box(cx_ - 14, TY0 - 8, cx_ + 14, TY0, B + 0.04, hi=0.3, lo=0.16)
    c.rect(cx_, 84, cx_, 112, B + 0.02)                                                     # whip
    c.rect(cx_ - 10, 118, cx_ + 10, 118, B + 0.02); c.rect(cx_ - 7, 124, cx_ + 7, 124, B - 0.02)
    c.rect(cx_ - 10, 112, cx_ - 10, 118, B - 0.02); c.rect(cx_ + 10, 110, cx_ + 10, 118, B - 0.02)
    n2 = math.hypot(0.75, -0.66)
    c.line([(cx_ + 2, 168), (cx_ + 12, 164)], B, width=2)
    dish(c, cx_ + 18, 158, 15, (0.75 / n2, -0.66 / n2), B - 0.02)
    # equipment on the boom
    c.box(190, TY0 - 14, 222, TY0 - 1, B - 0.02, hi=0.3, lo=0.14)
    vcyl(c, 228, 240, TY0 - 20, TY0 - 1, B + 0.02, 0.36); c.rect(228, TY0 - 20, 240, TY0 - 20, B + 0.3)
    c.box(430, TY0 - 12, 470, TY0 - 1, B - 0.04, hi=0.3, lo=0.14)
    c.box(438, TY0 - 20, 452, TY0 - 13, B, hi=0.3, lo=0.14)
    for x in range(586, 660, 9):                                                            # handrail
        c.rect(x, TY0 - 9, x, TY0 - 1, B - 0.06)
    c.rect(586, TY0 - 10, 658, TY0 - 10, B + 0.1)

    # --- guy wires and feeder cables ---------------------------------------------------
    c.line([(ax_, 84), (ax_ - 70, TY0)], B - 0.10)
    c.line([(ax_, 84), (ax_ + 70, TY0)], B - 0.10)
    c.line(catenary(ax_ + 2, 104, dxc - 4, 176, 34), B - 0.08)
    c.line(catenary(cx_, 118, ax_ + W, 106, 46), B - 0.10)

    auto_rim(c, top=B + 0.42)
    op = c.m > 0
    fade = 1 - 0.56 * smooth(184, 262, yy.astype(np.float32))
    c.v = np.where(op, c.v * fade, 0)
    arr = c.render({1: BRIDGE_MID}, width=0.55)

    light(arr, ax_, 59, "#ff7a7a", None); arr[60, ax_] = hexc("#b81f38"); arr[59, ax_ + 1] = hexc("#e8384f")
    light(arr, cx_, 83, "#2de0d0", None); arr[84, cx_] = hexc("#0f7480")
    for x in (ax_ - 22, ax_ + 21):
        arr[95, x] = hexc("#12a3a6")
    arr[TY0 - 8, 196] = hexc("#2de0d0"); arr[TY0 - 8, 200] = hexc("#12a3a6"); arr[TY0 - 8, 204] = hexc("#0f7480")
    arr[TY0 - 8, 446] = hexc("#3fc468"); arr[TY0 - 16, 444] = hexc("#ffcf33")
    return to_img(arr)


# ============================================================================
# intro_station  256x160  transparent - hero shot of Kepler Station
# ============================================================================
STATION = ["#0d1126", "#141a3a", "#1d2748", "#2a3758", "#3c4b6c", "#536488", "#7082a2", "#93a4bd", "#b9c7d6", "#e2eaf2"]
STATION_PANEL = ["#0c1230", "#0f1840", "#132152", "#182c66", "#1f3a7c", "#2b4f96", "#3f6cb0", "#6b8fd6"]


def make_station():
    W, H = 256, 160
    c = VC(W, H, wrap=False)
    yy, xx = c.yy, c.xx
    yf = yy.astype(np.float32); xf = xx.astype(np.float32)
    HULL, PAN = 1, 2
    L = np.array([-0.52, -0.64, 0.56]); L = L / np.linalg.norm(L)
    HX = 120                                              # hub axis

    # ---- ring geometry -----------------------------------------------------
    rcx, rcy, rx, ry, rt = 120.0, 50.0, 94.0, 24.0, 5.4
    th = np.linspace(0, TAU, 900, endpoint=False)
    cxs = rcx + rx * np.cos(th); cys = rcy + ry * np.sin(th)
    P = np.stack([xf.ravel(), yf.ravel()], 1)
    best = np.full(P.shape[0], 1e9, np.float32); bi = np.zeros(P.shape[0], np.int32)
    for i0 in range(0, 900, 100):
        dd = (P[:, None, 0] - cxs[None, i0:i0 + 100]) ** 2 + (P[:, None, 1] - cys[None, i0:i0 + 100]) ** 2
        j = dd.argmin(1); v = dd[np.arange(len(j)), j]
        upd = v < best
        best[upd] = v[upd]; bi[upd] = j[upd] + i0
    dist = np.sqrt(best).reshape(H, W)
    tsel = th[bi].reshape(H, W)
    ox = xf - (rcx + rx * np.cos(tsel)); oy = yf - (rcy + ry * np.sin(tsel))
    tube = dist <= rt
    nz = np.sqrt(np.clip(1 - (dist / rt) ** 2, 0, 1))
    lam = np.clip((ox / rt) * L[0] + (oy / rt) * L[1] + nz * L[2], 0, 1)
    ring_v = 0.24 + 0.72 * lam ** 0.9
    ring_v += 0.07 * np.cos(tsel - 3.6)                   # the left (sun) side of the wheel is brighter
    front = np.sin(tsel) > 0
    seam = np.abs(np.mod(tsel + 0.13, TAU / 16) - TAU / 32) > (TAU / 32 - 0.012)

    def draw_ring(sel, dim):
        m = tube & sel
        c.v[m] = (ring_v * dim)[m]; c.m[m] = HULL
        c.v[m & seam] -= 0.16

    def spoke(a, v):
        ex = rcx + (rx - 3) * math.cos(a); ey = rcy + (ry - 1) * math.sin(a)
        sx = HX + 13 * math.cos(a); sy = rcy + 3 * math.sin(a)
        c.line([(sx, sy - 1), (ex, ey - 1)], v + 0.22, HULL)
        c.line([(sx, sy), (ex, ey)], v, HULL)
        c.line([(sx, sy + 1), (ex, ey + 1)], v - 0.22, HULL)

    # ---- far side: back spokes, back half of the ring -------------------------
    for a in (math.radians(232), math.radians(308)):
        spoke(a, 0.36)
    draw_ring(~front, 0.80)

    # ---- hub -------------------------------------------------------------------
    # antenna
    c.rect(HX, 5, HX, 17, 0.62); c.rect(HX - 3, 9, HX + 3, 9, 0.55); c.rect(HX - 2, 13, HX + 2, 13, 0.5)
    # command dome
    dcy, dr = 29.0, 13.0
    dome = ((xf - HX) ** 2 + (yf - dcy) ** 2 <= dr * dr) & (yy <= 29)
    nx = (xf - HX) / dr; ny = (yf - dcy) / dr
    dl = np.clip(nx * L[0] + ny * L[1] + np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1)) * L[2], 0, 1)
    c.v[dome] = (0.30 + 0.72 * dl)[dome]; c.m[dome] = HULL
    vcyl(c, HX - 14, HX + 14, 30, 32, 0.62, 0.55)          # dome skirt
    vcyl(c, HX - 12, HX + 12, 33, 44, 0.52, 0.62)          # upper hub
    vcyl(c, HX - 17, HX + 17, 45, 55, 0.56, 0.62)          # ring collar
    c.v[c.rect_m(HX - 17, 45, HX + 17, 45)] += 0.12
    c.v[c.rect_m(HX - 17, 55, HX + 17, 55)] -= 0.18
    vcyl(c, HX - 12, HX + 12, 56, 62, 0.42, 0.55)
    vcyl(c, HX - 10, HX + 10, 63, 96, 0.52, 0.62)          # lower hub (spine)
    for y in (72, 84):
        c.v[c.rect_m(HX - 10, y, HX + 10, y)] -= 0.14
    vcyl(c, HX - 13, HX + 13, 97, 110, 0.54, 0.62)         # arm junction block
    c.v[c.rect_m(HX - 13, 97, HX + 13, 97)] += 0.12
    c.v[c.rect_m(HX - 13, 110, HX + 13, 110)] -= 0.18
    vcyl(c, HX - 6, HX + 6, 111, 150, 0.40, 0.5)           # tank spine
    # comm dish on the upper hub
    c.line([(HX + 12, 38), (HX + 19, 34)], 0.5, HULL)
    dm = ((xf - (HX + 23)) ** 2 + (yf - 31) ** 2 <= 30) & ((xf - (HX + 23)) * 0.7 - (yf - 31) * 0.7 <= 1.5)
    c.put(dm, 0.62, HULL)
    c.put(dm & ((xf - (HX + 23)) * 0.7 - (yf - 31) * 0.7 > 0.2), 0.9, HULL)
    c.put(dm & ((xf - (HX + 23)) ** 2 + (yf - 31) ** 2 > 20) & (yf > 31), 0.34, HULL)
    c.line([(HX + 24, 30), (HX + 28, 26)], 0.6, HULL)

    # ---- fuel tanks clustered round the spine ----------------------------------
    def tank(x0, x1, y0, y1, base, amp):
        w = x1 - x0
        capt = c.ell_m(x0, y0, x1, y0 + w); capb = c.ell_m(x0, y1 - w, x1, y1)
        body = c.rect_m(x0, y0 + w // 2, x1, y1 - w // 2)
        m = capt | capb | body
        vcyl(c, x0, x1, y0, y1, base, amp, mask=m)
        # shade the end caps as domes
        c.v[capt & (yy < y0 + 3)] += 0.06
        c.v[capb & (yy > y1 - 4)] -= 0.14
        for yb in (y0 + w // 2 + 1, (y0 + y1) // 2, y1 - w // 2 - 1):
            c.v[m & (yy == yb)] -= 0.16
            c.v[m & (yy == yb + 1)] += 0.05
        return m

    tk_bl = tank(87, 103, 114, 151, 0.40, 0.52)            # back pair (dimmer)
    tk_br = tank(137, 153, 114, 151, 0.36, 0.48)
    c.rect(96, 122, 144, 123, 0.34); c.rect(96, 142, 144, 143, 0.30)     # cradle rings
    tk_fl = tank(99, 118, 112, 155, 0.56, 0.66)            # front pair
    tk_fr = tank(122, 141, 112, 155, 0.52, 0.64)
    c.rect(117, 126, 123, 127, 0.4); c.rect(117, 140, 123, 141, 0.36)

    # ---- docking arm (right) -----------------------------------------------------
    AY0, AY1 = 100, 107
    ax0, ax1 = HX + 14, 226
    for k in range(ax0, ax1, 8):
        c.line([(k, AY1), (k + 4, AY0), (k + 8, AY1)], 0.44, HULL)
    c.rect(ax0, AY0, ax1, AY0, 0.86); c.rect(ax0, AY0 + 1, ax1, AY0 + 1, 0.58)
    c.rect(ax0, AY1, ax1, AY1, 0.5); c.rect(ax0, AY1 + 1, ax1, AY1 + 1, 0.28)
    c.rect(ax0, AY1 + 4, ax1 - 6, AY1 + 5, 0.46); c.rect(ax0, AY1 + 4, ax1 - 6, AY1 + 4, 0.66)   # fuel line under the truss
    for k in range(ax0 + 14, ax1 - 6, 24):
        c.rect(k, AY1 + 2, k, AY1 + 4, 0.4)
    # docking head
    hcyl(c, 224, 240, 96, 112, 0.56, 0.64)
    c.rect(224, 96, 225, 112, 0.36)
    hcyl(c, 241, 244, 94, 114, 0.62, 0.66)                 # docking collar
    c.rect(245, 98, 246, 110, 0.30)
    c.rect(220, 113, 226, 116, 0.4); c.rect(222, 117, 224, 121, 0.5)    # fuel nozzle hanging under the head

    # ---- solar wings (left) ----------------------------------------------------------
    c.rect(34, 103, HX - 14, 104, 0.6); c.rect(34, 105, HX - 14, 105, 0.3)
    c.rect(34, 103, HX - 14, 103, 0.84)
    for (bx0, bx1) in ((34, 58), (62, 86)):
        for (by0, by1) in ((85, 100), (108, 123)):
            m = c.rect_m(bx0, by0, bx1, by1)
            sheen = smooth(0, 1, 1 - np.abs((xf - bx0) / 24.0 - 0.35 + (yf - by0) / 40.0) / 0.35)
            val = 0.34 + 0.42 * sheen - (0.10 if by0 > 105 else 0.0)
            c.v[m] = val[m]; c.m[m] = PAN
            grid = m & ((((xx - bx0) % 6) == 0) | (((yy - by0) % 5) == 0))
            c.v[grid] = 0.14
            c.v[m & (yy == by0)] = 0.92
            c.v[m & (xx == bx0)] = 0.7
            c.v[m & (yy == by1)] = 0.05
            c.v[m & (xx == bx1)] = 0.05
        c.rect((bx0 + bx1) // 2, 100, (bx0 + bx1) // 2, 108, 0.5)
    c.rect(30, 101, 33, 107, 0.6); c.rect(30, 101, 33, 101, 0.86)

    # ---- near side: side + front spokes, front half of the ring -----------------------
    for a in (0.0, math.pi):
        spoke(a, 0.56)
    for a in (math.radians(52), math.radians(128)):
        spoke(a, 0.62)
    # the ring throws a soft shadow down the spine just below it
    shadow_zone = c.rect_m(HX - 12, 56, HX + 12, 86) & ~(tube & front)
    c.v[shadow_zone] -= (0.20 * smooth(88, 78, yf))[shadow_zone] * (c.m[shadow_zone] == HULL)
    draw_ring(front, 1.0)
    # thruster pods riding on the ring
    for a in (math.radians(22), math.radians(158), math.radians(100)):
        ex = int(round(rcx + rx * math.cos(a))); ey = int(round(rcy + ry * math.sin(a)))
        c.box(ex - 3, ey - 8, ex + 3, ey - 5, 0.66, HULL, hi=0.24, lo=0.26)
        c.rect(ex - 1, ey - 10, ex, ey - 9, 0.5)

    c.v = np.clip(c.v, 0, 1)
    arr = c.render({HULL: STATION, PAN: STATION_PANEL}, width=0.12)

    # ---- planet-light bounce on the shadow-side edges ----------------------------------
    op = arr[..., 3] > 0
    rt_ = np.roll(op, -1, 1); rt_[:, -1] = False
    dn = np.roll(op, -1, 0); dn[-1, :] = False
    edge = op & (~rt_ | ~dn) & (c.m == HULL) & (c.v < 0.5)
    arr[edge] = hexc("#22516e")
    edge2 = edge & (c.v < 0.34) & (yy > 60)
    arr[edge2] = hexc("#1b3f5c")

    # ---- windows and lights ---------------------------------------------------------------
    A1, A2, A3 = hexc("#ffe97a"), hexc("#ffcf33"), hexc("#d49a12")
    CY1, CY2, CY3 = hexc("#dcfffa"), hexc("#2de0d0"), hexc("#12a3a6")

    def P_(x, y, col):
        if 0 <= x < W and 0 <= y < H:
            arr[y, x] = col

    # dome glass band
    for x in range(HX - 9, HX + 10):
        yb = 24 if abs(x - HX) < 8 else 25
        P_(x, yb, CY2 if x < HX + 2 else CY3); P_(x, yb + 1, CY3 if x < HX + 2 else hexc("#0f7480"))
    P_(HX - 6, 24, CY1); P_(HX - 5, 24, CY1)
    # hub windows
    for x in range(HX - 9, HX + 10, 3):
        P_(x, 36, A2 if x < HX + 3 else A3); P_(x, 40, A1 if x < HX else A3)
    for x in range(HX - 14, HX + 15, 4):
        P_(x, 49, A2 if x < HX + 4 else A3); P_(x + 1, 49, A3)
    for y in (66, 69, 76, 79, 88, 91):
        for x in (HX - 6, HX - 2, HX + 3):
            if (x + y) % 4 != 1:
                P_(x, y, A2 if x < HX else A3)
    for x in range(HX - 10, HX + 11, 5):
        P_(x, 103, CY2); P_(x + 1, 103, CY3)
    # ring windows on the near side, running lights at the tips
    for k in range(900):
        a = th[k]
        if math.sin(a) > 0.12 and k % 7 == 0:
            x = int(round(rcx + rx * math.cos(a))); y = int(round(rcy + ry * math.sin(a) + 1))
            if abs(x - HX) > 0 and (k // 7) % 5 != 3:
                P_(x, y, A1 if math.cos(a) < -0.2 else A2 if math.cos(a) < 0.5 else A3)
    for (x, y) in ((27, 50), (213, 50)):
        P_(x, y, CY1); P_(x - 1, y, CY2); P_(x + 1, y, CY2); P_(x, y - 1, CY2); P_(x, y + 1, CY2)
    for a in (math.radians(40), math.radians(90), math.radians(140)):
        x = int(round(rcx + rx * math.cos(a))); y = int(round(rcy + ry * math.sin(a) - 4))
        P_(x, y, CY2)
    # tank gauges: each tank filled to a different level
    for (gx, y0, y1, lvl, dim) in ((104, 124, 146, 1.0, 0), (127, 124, 146, 0.5, 0), (91, 124, 144, 0.75, 1), (146, 124, 144, 0.25, 1)):
        for y in range(y0, y1 + 1):
            full = (y1 - y) / (y1 - y0) <= lvl
            col = (CY3 if dim else CY2) if full else hexc("#0a2b3a")
            P_(gx, y, col); P_(gx + 1, y, (hexc("#0f7480") if dim else CY3) if full else hexc("#0a2b3a"))
        if lvl > 0:
            yt = int(round(y1 - lvl * (y1 - y0)))
            P_(gx, yt, CY1 if not dim else CY2)
    # arm approach lights + docking head
    for i, x in enumerate(range(ax0 + 8, ax1 - 4, 16)):
        P_(x, AY0 - 1, CY2); P_(x, AY0, CY1)
    for y in range(98, 111):                                # hazard band on the head
        if (y // 2) % 2 == 0:
            P_(230, y, A2 if y < 104 else A3); P_(231, y, A3 if y < 104 else hexc("#96620a"))
        else:
            P_(230, y, hexc("#141a3a")); P_(231, y, hexc("#141a3a"))
    P_(246, 97, CY2); P_(246, 111, CY2); P_(247, 104, CY1); P_(246, 104, CY2)
    P_(223, 121, CY2); P_(223, 122, CY3)
    # beacons
    P_(HX, 4, hexc("#ff7a7a")); P_(HX, 5, hexc("#e8384f")); P_(HX - 1, 4, hexc("#b81f38")); P_(HX + 1, 4, hexc("#b81f38")); P_(HX, 3, hexc("#b81f38"))
    P_(30, 104, hexc("#e8384f")); P_(HX + 29, 25, CY2)
    P_(HX, 151, CY2); P_(HX, 152, CY3)
    return to_img(arr)


# ============================================================================
# shuttle  64x32 frames: fly 0-3, parked 4
# ============================================================================
def make_shuttle():
    from pix import px, new, outline, rect as prect, hline, vline, sheet
    ink = C["ink0"]
    S7, S6, S5, S4, S3, S2, S1 = C["white"], C["steel7"], C["steel6"], C["steel5"], C["steel4"], C["steel3"], C["steel2"]
    O5, O4, O3, O2, O1 = C["orange5"], C["orange4"], C["orange3"], C["orange2"], C["orange1"]
    Y6, Y5, Y4, Y3, Y2, Y1 = C["cyan6"], C["cyan5"], C["cyan4"], C["cyan3"], C["cyan2"], C["cyan1"]

    top = {17: 13, 18: 12, 19: 11, 20: 10, 21: 10, 22: 9, 23: 9}
    for x in range(24, 36):
        top[x] = 9
    top.update({36: 8, 37: 7, 38: 6, 39: 5, 40: 5, 41: 4, 42: 4, 43: 4, 44: 4, 45: 4, 46: 5, 47: 5, 48: 6, 49: 7, 50: 8,
                51: 9, 52: 10, 53: 10, 54: 11, 55: 11, 56: 12, 57: 13, 58: 14, 59: 15})
    bot = {17: 20, 18: 22, 19: 23, 20: 24, 21: 24, 22: 25}
    for x in range(23, 47):
        bot[x] = 25
    bot.update({47: 25, 48: 25, 49: 24, 50: 24, 51: 24, 52: 23, 53: 23, 54: 22, 55: 22, 56: 21, 57: 21, 58: 20, 59: 19})

    def hull(parked):
        im = new(64, 32)
        # --- tail fin (behind the hull) ---
        fin = [(19, 11), (20, 4), (21, 3), (26, 3), (27, 4), (30, 9)]
        m = Image.new("L", (64, 32), 0); ImageDraw.Draw(m).polygon(fin, fill=255)
        fm = np.array(m) > 0
        for y in range(32):
            for x in range(64):
                if fm[y, x]:
                    px(im, x, y, O3)
        for y in range(3, 10):                               # light leading edge, dark trailing edge
            xs = [x for x in range(64) if fm[y, x]]
            if xs:
                px(im, xs[0], y, O4); px(im, xs[-1], y, O2)
                if len(xs) > 3:
                    px(im, xs[0] + 1, y, O4 if y < 6 else O3)
        hline(im, 21, 26, 3, O5)
        hline(im, 22, 25, 6, S7); hline(im, 22, 26, 7, S6)   # white flash on the fin
        # --- body ---
        for x in range(17, 60):
            t, b = top[x], bot[x]
            for y in range(t, b + 1):
                rel = (y - t) / max(1, (b - t))
                if y - t == 0:
                    col = S6
                elif rel < 0.2:
                    col = S7
                elif rel < 0.60:
                    col = S6
                elif rel < 0.84:
                    col = S5
                else:
                    col = S4
                px(im, x, y, col)
        # belly bounce light and nose shadow
        for x in range(24, 46):
            px(im, x, bot[x], S3)
        for x in range(52, 60):
            for y in range(top[x], bot[x] + 1):
                if y - top[x] >= 2 and im.getpixel((x, y)) == S6:
                    px(im, x, y, S5)
        # --- orange stripe sweeping along the side, up over the nose ---
        for x in range(17, 60):
            yc = 17 if x < 50 else 17 - (x - 50) * 0.12
            y0 = int(round(yc))
            if top[x] + 1 <= y0 and y0 + 2 <= bot[x]:
                px(im, x, y0, O4); px(im, x, y0 + 1, O3); px(im, x, y0 + 2, O2)
            elif top[x] <= y0 + 1 <= bot[x]:
                px(im, x, y0 + 1, O3)
        hline(im, 27, 33, 17, O5)                            # specular kick on the stripe
        # nose cap
        for x in range(56, 60):
            for y in range(top[x], bot[x] + 1):
                px(im, x, y, O3 if y < 17 else O2)
        px(im, 56, 12, O4); px(im, 57, 13, O4); px(im, 58, 14, O4); px(im, 56, 13, O4)
        px(im, 59, 15, O2); px(im, 59, 19, O1); px(im, 58, 20, O1); px(im, 57, 21, O1); px(im, 56, 21, O1)
        # panel lines
        vline(im, 34, 10, 15, S5); vline(im, 34, 20, 24, S4)
        vline(im, 50, 15, 16, S5); vline(im, 50, 20, 23, S4)
        # --- canopy ---
        cb = {37: 9, 38: 11, 39: 12, 40: 13, 41: 13, 42: 13, 43: 13, 44: 13, 45: 13, 46: 13, 47: 13, 48: 13, 49: 13, 50: 12, 51: 11}
        for x, yb in cb.items():
            for y in range(top[x] + 1, yb + 1):
                rel = (y - top[x]) / max(1, yb - top[x])
                col = Y3
                if x <= 44 and rel < 0.55:
                    col = Y4
                if x >= 48 or rel > 0.8:
                    col = Y2
                px(im, x, y, col)
            px(im, x, top[x], S5 if x < 46 else S4)          # frame over the top
        # canopy frame along the bottom + pillars
        for x in range(36, 53):
            yb = cb.get(x, top[x]) + 1 if x in cb else top[x] + 1
            px(im, x, yb, S4)
        vline(im, 45, 5, 13, S5)                             # centre pillar
        # glints
        px(im, 39, 6, Y6); px(im, 40, 6, Y6); px(im, 39, 7, Y6); px(im, 41, 5, Y5); px(im, 42, 5, Y5); px(im, 38, 8, Y5)
        px(im, 47, 7, Y4); px(im, 48, 8, Y3)
        if not parked:                                       # Jake at the controls
            H2, H3 = C["hair2"], C["hair3"]
            hline(im, 40, 43, 8, H2); px(im, 40, 8, H3); hline(im, 40, 43, 9, H2)
            px(im, 43, 9, Y5); px(im, 44, 9, Y4)             # goggles
            hline(im, 41, 43, 10, C["skin3"]); px(im, 44, 10, C["skin4"])
            hline(im, 41, 43, 11, C["skin3"]); px(im, 40, 10, H2)
            hline(im, 40, 43, 12, O3); hline(im, 40, 43, 13, O2)
        else:
            hline(im, 40, 43, 12, S2); hline(im, 40, 43, 13, S2); hline(im, 41, 42, 11, S2)   # empty seat
        # --- porthole + badge ---
        for (x, y, col) in ((28, 12, S3), (29, 12, S3), (30, 12, S3), (27, 13, S3), (31, 13, S4), (27, 14, S3), (31, 14, S4),
                            (28, 15, S4), (29, 15, S4), (30, 15, S4), (28, 13, Y4), (29, 13, Y3), (30, 13, Y2), (28, 14, Y3), (29, 14, Y2), (30, 14, Y1)):
            px(im, x, y, col)
        px(im, 22, 13, C["gold3"]); px(im, 23, 13, C["gold2"]); px(im, 22, 14, C["gold2"])
        # --- engine bell ---
        for x, (y0, y1) in {16: (14, 20), 15: (13, 21), 14: (12, 22), 13: (12, 22)}.items():
            for y in range(y0, y1 + 1):
                rel = (y - y0) / (y1 - y0)
                px(im, x, y, S3 if rel < 0.25 else S2 if rel < 0.7 else S1)
            px(im, x, y0, S4)
        vline(im, 16, 14, 20, S1)
        if not parked:
            vline(im, 13, 14, 20, C["gold3"]); vline(im, 13, 16, 18, C["gold5"])
        else:
            vline(im, 13, 13, 21, C["steel1"]); vline(im, 13, 15, 19, C["steel0"])
        # --- stubby swept wing on the near side ---
        wing = [(27, 20), (39, 20), (33, 27), (22, 27)]
        m = Image.new("L", (64, 32), 0); ImageDraw.Draw(m).polygon(wing, fill=255)
        wm = np.array(m) > 0
        for y in range(32):
            xs = [x for x in range(64) if wm[y, x]]
            for x in xs:
                px(im, x, y, S6 if y < 23 else S5)
            if xs:
                px(im, xs[0], y, S7 if y < 24 else S6); px(im, xs[-1], y, S4)
        for x in range(27, 40):
            px(im, x, 20, S2 if x > 27 else S3)              # shadow line where the wing meets the hull
        for x in range(64):
            if wm[26, x]:
                px(im, x, 26, O3)
            if wm[27, x]:
                px(im, x, 27, O2)
        # --- landing skids (parked only) ---
        if parked:
            for sx in (25, 46):
                vline(im, sx, 26, 29, S3); vline(im, sx + 1, 26, 29, S2)
                hline(im, sx - 2, sx + 3, 30, S3); hline(im, sx - 2, sx + 3, 29, S4)
        im = outline(im, ink)
        return im

    def flame(k):
        im = new(64, 32)
        # (length, wobble) per frame; drawn as stacked tapering rows around y=17
        spec = [(11, 0), (8, 1), (12, -1), (9, 0)][k]
        Ln, wob = spec
        O = C["orange3"]; G = C["gold3"]; Yl = C["gold4"]; Wt = C["gold5"]; R = C["orange2"]
        for i in range(Ln + 1):
            x = 12 - i
            t = i / Ln
            hw = (4.2 * (1 - t) ** 0.8) + (0.6 if (i + k) % 3 == 0 and i > 1 else 0)
            yc = 17 + (wob * t * 1.5) + (0.5 if (i + k) % 4 == 2 else 0)
            for y in range(int(round(yc - hw)), int(round(yc + hw)) + 1):
                dy = abs(y - yc) / max(hw, 0.5)
                if t < 0.30 and dy < 0.45:
                    col = Wt
                elif t < 0.55 and dy < 0.65:
                    col = Yl
                elif t < 0.8 and dy < 0.9:
                    col = G
                else:
                    col = O
                px(im, x, y, col)
        # dark-orange rim so the flame holds its shape on bright and dark backgrounds
        im = outline(im, R)
        # loose sparks
        for (sx, sy) in [((1, 15), (3, 20)), ((4, 13),), ((0, 18), (2, 14)), ((3, 21),)][k]:
            px(im, sx, sy, with_a(O, 200))
        return im

    def with_a(col, a):
        return (col[0], col[1], col[2], a)

    frames = []
    for k in range(4):
        f = new(64, 32)
        f.alpha_composite(flame(k))
        f.alpha_composite(hull(False))
        frames.append(f)
    frames.append(hull(True))
    return frames


# ----------------------------------------------------------------------------
# previews
# ----------------------------------------------------------------------------
def load(name):
    return Image.open(os.path.join(ASSETS, name)).convert("RGBA")


def side_by_side(img, n=2):
    out = Image.new("RGBA", (img.width * n, img.height), (0, 0, 0, 0))
    for i in range(n):
        out.alpha_composite(img, (i * img.width, 0))
    return out


def space_view(px_=250, py_=18, ox=0, oy=0):
    st = load("bg/stars.png"); nb = load("bg/nebula.png"); pl = load("bg/planet.png")
    v = Image.new("RGBA", (480, 270), hexc("#080a14"))
    v.alpha_composite(st.crop((ox, oy, ox + 480, oy + 270)))
    v.alpha_composite(nb.crop((ox, 0, ox + 480, 270)))
    v.alpha_composite(pl, (px_, py_))
    return v


PARTS = {}


def part(fn):
    PARTS[fn.__name__.replace("build_", "")] = fn
    return fn


@part
def build_stars():
    img = make_stars(); save(img, "bg/stars.png")
    preview(side_by_side(img), "bga_stars_x2.png", scale=2, bg="#080a14")
    tall = Image.new("RGBA", (512, 576)); tall.alpha_composite(img); tall.alpha_composite(img, (0, 288))
    preview(tall, "bga_stars_y2.png", scale=2, bg="#080a14")


@part
def build_nebula():
    img = make_nebula(); save(img, "bg/nebula.png")
    preview(side_by_side(img), "bga_nebula_x2.png", scale=2, bg="#080a14")


@part
def build_planet():
    img = make_planet(); save(img, "bg/planet.png")
    preview(img, "bga_planet.png", scale=4, bg="#080a14")


@part
def build_dock_far():
    img = make_dock_far(); save(img, "bg/dock_far.png")
    preview(side_by_side(img), "bga_dock_far_x2.png", scale=2, bg="#3a1030")


def tile_room(skin, layout):
    """Small test room made of real tiles (transparent where empty) + Jake, 480x270."""
    til = load(f"tiles/tiles_{skin}.png")
    Wt, Ht = 30, 17
    grid = [[0] * Wt for _ in range(Ht)]
    for (x0, y0, x1, y1) in layout["solid"]:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < Wt and 0 <= y < Ht:
                    grid[y][x] = 1
    img = Image.new("RGBA", (Wt * 16, Ht * 16), (0, 0, 0, 0))

    def tile(i):
        return til.crop(((i % 16) * 16, (i // 16) * 16, (i % 16) * 16 + 16, (i // 16) * 16 + 16))

    def sol(x, y):
        if x < 0 or x >= Wt or y < 0 or y >= Ht:
            return 1
        return grid[y][x]
    import random
    rnd = random.Random(3)
    for y in range(Ht):
        for x in range(Wt):
            if not grid[y][x]:
                continue
            m = sol(x, y - 1) * 1 + sol(x + 1, y) * 2 + sol(x, y + 1) * 4 + sol(x - 1, y) * 8
            t = m
            if m == 15:
                deep = all(sol(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                t = (16 + rnd.randint(0, 1)) if deep else 15
            if m == 14 and x % 7 == 3:
                t = 20
            if m == 14 and (not sol(x + 2, y) or not sol(x - 2, y)):
                t = 21
            img.alpha_composite(tile(t), (x * 16, y * 16))
    for (x0, x1, y) in layout.get("oneway", []):
        for x in range(x0, x1 + 1):
            img.alpha_composite(tile(32 if x == x0 else 34 if x == x1 else 33), (x * 16, y * 16))
    jk = load("sprites/jake.png")
    for (jx, jy, fr, flip) in layout["jake"]:
        f = jk.crop(((fr % 8) * 32, (fr // 8) * 32, (fr % 8) * 32 + 32, (fr // 8) * 32 + 32))
        if flip:
            f = f.transpose(Image.FLIP_LEFT_RIGHT)
        img.alpha_composite(f, (jx, jy * 16 - 32))
    # the 480x270 view shows the bottom of the 272px tile grid
    return img.crop((0, 2, 480, 272))


LAYOUT = {
    "solid": [(0, 14, 13, 16), (14, 15, 17, 16), (18, 13, 29, 16), (6, 9, 10, 9), (23, 8, 29, 9)],
    "oneway": [(13, 16, 6), (1, 3, 5)],
    "jake": [(60, 14, 0, False), (110, 9, 9, False), (330, 13, 12, True), (228, 6, 16, False), (400, 8, 2, True)],
}


def stack(area, planet_xy, mid_off=0, far_off=0, room=True, layers=("far", "mid")):
    v = space_view(planet_xy[0], planet_xy[1])
    for kind, off in (("far", far_off), ("mid", mid_off)):
        p = os.path.join(ASSETS, f"bg/{area}_{kind}.png")
        if kind in layers and os.path.exists(p):
            im = side_by_side(load(f"bg/{area}_{kind}.png"))
            v.alpha_composite(im.crop((off, 0, off + 480, 270)))
    if room:
        v.alpha_composite(tile_room(area, LAYOUT))
    return v


@part
def build_dock_mid():
    img = make_dock_mid(); save(img, "bg/dock_mid.png")
    preview(side_by_side(img), "bga_dock_mid_x2.png", scale=2, bg="#0d1126")


@part
def build_bridge_far():
    img = make_bridge_far(); save(img, "bg/bridge_far.png")
    preview(side_by_side(img), "bga_bridge_far_x2.png", scale=2, bg="#080a14")


@part
def build_bridge_mid():
    img = make_bridge_mid(); save(img, "bg/bridge_mid.png")
    preview(side_by_side(img), "bga_bridge_mid_x2.png", scale=2, bg="#080a14")


@part
def build_station():
    img = make_station(); save(img, "intro/station.png")
    preview(img, "bga_station.png", scale=5, bg="#080a14")
    v = space_view(250, 40).crop((0, 0, 400, 225))
    v.alpha_composite(img, (60, 30))
    sh = load("intro/shuttle.png") if os.path.exists(os.path.join(ASSETS, "intro/shuttle.png")) else None
    if sh:
        v.alpha_composite(sh.crop((0, 0, 64, 32)), (318, 130))
    preview(v, "bga_station_scene.png", scale=3, bg="#080a14")


@part
def build_shuttle():
    frames = make_shuttle()
    sh = pix.sheet(frames)
    save(sh, "intro/shuttle.png")
    preview(sh, "bga_shuttle.png", scale=6, bg="#2b3f7e", grid=(64, 32))
    preview(sh, "bga_shuttle_dark.png", scale=6, bg="#080a14")


def build_previews():
    have = lambda f: os.path.exists(os.path.join(ASSETS, f))
    if all(have(f) for f in ("bg/stars.png", "bg/nebula.png", "bg/planet.png")):
        preview(space_view(), "bga_space.png", scale=3, bg="#080a14")
        for area, pxy in (("dock", (92, -8)), ("bridge", (236, 6))):
            if have(f"bg/{area}_far.png"):
                preview(stack(area, pxy, room=False, layers=("far",)), f"bga_{area}_far_view.png", scale=3)
                f_ = load(f"bg/{area}_far.png")
                preview(f_.crop((0, 40, 260, 230)), f"bga_{area}_far_L.png", scale=5, bg="#080a14")
                preview(f_.crop((220, 40, 480, 230)), f"bga_{area}_far_R.png", scale=5, bg="#080a14")
                preview(stack(area, pxy, room=False), f"bga_{area}_layers.png", scale=3)
                preview(stack(area, pxy), f"bga_stack_{area}.png", scale=3)
                preview(stack(area, pxy, mid_off=300, far_off=210), f"bga_stack_{area}_b.png", scale=3)
            if have(f"bg/{area}_mid.png"):
                m = load(f"bg/{area}_mid.png")
                preview(m.crop((0, 0, 320, 270)), f"bga_{area}_mid_L.png", scale=4, bg="#0d1126")
                preview(m.crop((320, 0, 640, 270)), f"bga_{area}_mid_R.png", scale=4, bg="#0d1126")


if __name__ == "__main__":
    want = sys.argv[1:] or list(PARTS)
    for name in want:
        PARTS[name]()
    build_previews()
