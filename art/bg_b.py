"""
bg_b.py - parallax background layers for the Reactor, Zero-G and Boss areas.

  reactor_far  bg/reactor_far.png  480x270   opaque, tileable in X
  reactor_mid  bg/reactor_mid.png  640x270   transparent, tileable in X
  zerog_far    bg/zerog_far.png    480x270   opaque + transparent portholes
  zerog_mid    bg/zerog_mid.png    640x270   transparent
  boss_far     bg/boss_far.png     480x270   transparent panoramic window
  boss_mid     bg/boss_mid.png     640x270   transparent

How the pictures are painted
----------------------------
Every layer is painted on a `Plate`: a pair of float fields (tone, hue) that
index a small hand-picked colour table (rows = hue, columns = dark -> light).
Shapes are laid down back to front with flat integer tones (crisp pixel-art
bands); light, haze and atmospheric perspective are added as fractional tone,
which the final pass turns into 4x4 Bayer ordered dithering.  Every drawing
helper wraps in X, so anything may straddle the seam and the layers tile.

Run:  cd art && python3 bg_b.py            (all six images + previews)
      python3 bg_b.py reactor|zerog|boss   (one area only)
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

import pix
from pix import hexc, C

W_FAR, W_MID, H = 480, 640, 270
BAY = (np.array(pix.BAYER4, np.float32) + 0.5) / 16.0


# ----------------------------------------------------------------------------
# Plate: tone/hue painting surface with X-wrapping helpers
# ----------------------------------------------------------------------------
class Plate:
    def __init__(self, w, h, lut):
        self.w, self.h = w, h
        n = max(len(r) for r in lut)
        self.lut = np.array([[hexc(c)[:3] for c in (r + [r[-1]] * (n - len(r)))] for r in lut], np.uint8)
        self.nt = n
        self.nh = len(lut)
        self.tone = np.zeros((h, w), np.float32)
        self.hue = np.zeros((h, w), np.float32)
        self.k = np.full((h, w), 1.5, np.float32)       # dither sharpness (1 = full dither)
        self.a = np.zeros((h, w), bool)                 # coverage
        self.haze = np.zeros((h, w), np.float32)        # smooth air-light field
        self.hazehue = np.zeros((h, w), np.float32)
        self.over = np.zeros((h, w, 4), np.float32)     # direct colour overlay (RGBA 0..255)
        self.Y, self.X = np.mgrid[0:h, 0:w].astype(np.float32)
        self.thr = np.tile(BAY, (h // 4 + 1, w // 4 + 1))[:h, :w]
        # second, decorrelated threshold for the hue axis
        self.thr2 = np.tile(BAY[::-1, ::-1].T, (h // 4 + 1, w // 4 + 1))[:h, :w]

    # ---- coordinates -------------------------------------------------------
    def dx(self, cx):
        """signed wrapped horizontal distance to cx"""
        return (self.X - cx + self.w / 2.0) % self.w - self.w / 2.0

    def u(self, x0, x1):
        """0..1 across the span x0..x1 (wrapped)"""
        return ((self.X - x0) % self.w) / float(x1 - x0)

    # ---- masks -------------------------------------------------------------
    def rect(self, x0, y0, x1, y1):
        return (((self.X - x0) % self.w) < (x1 - x0)) & (self.Y >= y0) & (self.Y < y1)

    def ell(self, cx, cy, rx, ry):
        return (self.dx(cx) / rx) ** 2 + ((self.Y - cy) / ry) ** 2 <= 1.0

    def ring(self, cx, cy, r0, r1, sx=1.0):
        d = np.hypot(self.dx(cx) / sx, self.Y - cy)
        return (d >= r0) & (d <= r1)

    def _pil(self, fn):
        im = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(im)
        for off in (-self.w, 0, self.w):
            fn(d, off)
        return np.asarray(im) > 0

    def poly(self, pts):
        return self._pil(lambda d, o: d.polygon([(x + o, y) for x, y in pts], fill=255))

    def lines(self, pts, width=1):
        return self._pil(lambda d, o: d.line([(x + o, y) for x, y in pts], fill=255, width=width))

    def trap(self, xa0, xa1, ya, xb0, xb1, yb):
        """trapezoid: top edge xa0..xa1 at ya, bottom edge xb0..xb1 at yb (analytic, wrapped)"""
        t = np.clip((self.Y - ya) / float(yb - ya), 0, 1)
        l = xa0 + (xb0 - xa0) * t
        r = xa1 + (xb1 - xa1) * t
        c = (l + r) / 2.0
        d = (self.X - c + self.w / 2.0) % self.w - self.w / 2.0
        return (np.abs(d) <= (r - l) / 2.0) & (self.Y >= ya) & (self.Y < yb)

    # ---- painting ----------------------------------------------------------
    def put(self, m, tone, hue=0.0, fog=0.0, k=14.0):
        """lay down a surface. fog mixes it toward the stored haze (aerial perspective)."""
        t = tone if np.isscalar(tone) else tone[m]
        hz = self.haze[m]
        self.tone[m] = t * (1.0 - fog) + hz * fog
        hh = hue if np.isscalar(hue) else hue[m]
        self.hue[m] = hh * (1.0 - fog) + self.hazehue[m] * fog
        self.k[m] = k
        self.a[m] = True

    def add(self, m, d):
        if m is None:
            self.tone += d
        else:
            self.tone[m] += d if np.isscalar(d) else d[m]

    def tint(self, m, amount, hue):
        """pull hue toward `hue` by amount (0..1 field or scalar)"""
        if m is None:
            self.hue += (hue - self.hue) * amount
        else:
            a = amount if np.isscalar(amount) else amount[m]
            self.hue[m] += (hue - self.hue[m]) * a

    def cut(self, m):
        self.a[m] = False

    def dot(self, x, y, col, a=255):
        x = int(round(x)) % self.w
        y = int(round(y))
        if 0 <= y < self.h:
            self.over[y, x] = (col[0], col[1], col[2], a)

    def paint(self, m, col, a=255):
        self.over[m] = (col[0], col[1], col[2], a)

    # ---- output ------------------------------------------------------------
    def render(self):
        def q(v, n, thr, k):
            v = np.clip(v, 0, n - 1)
            i = np.floor(v)
            f = v - i
            f = np.clip((f - 0.5) * k + 0.5, 0, 1)
            i = i + (f > thr)
            return np.clip(i, 0, n - 1).astype(np.int32)
        ti = q(self.tone, self.nt, self.thr, self.k)
        hi = q(self.hue, self.nh, self.thr2, np.full_like(self.k, 1.6))
        rgb = self.lut[hi, ti].astype(np.float32)
        al = self.a.astype(np.float32) * 255.0
        oa = self.over[..., 3:4] / 255.0
        # overlay composites over the base (and adds coverage where the base is empty)
        base_a = al[..., None] / 255.0
        out_a = oa + base_a * (1 - oa)
        out_rgb = np.where(out_a > 0, (self.over[..., :3] * oa + rgb * base_a * (1 - oa)) / np.maximum(out_a, 1e-6), 0)
        arr = np.dstack([out_rgb, out_a * 255.0]).round().astype(np.uint8)
        return Image.fromarray(arr, "RGBA")


def glow(P, cx, cy, rx, ry, amp, p=2.0):
    d2 = (P.dx(cx) / rx) ** 2 + ((P.Y - cy) / ry) ** 2
    return amp * np.exp(-d2 ** (p / 2.0))


def noise_x(w, h, cell, seed, cell_y=None):
    """smooth value noise that tiles in X, 0..1"""
    cell_y = cell_y or cell
    rs = np.random.RandomState(seed)
    gx = max(1, int(round(w / cell)))
    gy = int(h / cell_y) + 2
    g = rs.rand(gy, gx).astype(np.float32)
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    fx = X / w * gx
    fy = Y / cell_y
    x0 = np.floor(fx).astype(int)
    y0 = np.floor(fy).astype(int)
    tx = fx - x0
    ty = fy - y0
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    x1 = (x0 + 1) % gx
    x0 = x0 % gx
    y1 = np.minimum(y0 + 1, gy - 1)
    return (g[y0, x0] * (1 - tx) + g[y0, x1] * tx) * (1 - ty) + (g[y1, x0] * (1 - tx) + g[y1, x1] * tx) * ty


def vcyl(P, x0, x1, y0, y1, base, fog=0.0, hue=0.0, lit=0, amp=1.0, k=14.0, hi=1.0, sh=1.0):
    """vertical cylinder: key light from the left, optional warm rim on side `lit` (+1 right, -1 left)"""
    m = P.rect(x0, y0, x1, y1)
    u = P.u(x0, x1)
    wpx = x1 - x0
    e = max(1.0, round(wpx * 0.12)) / wpx
    t = np.full_like(u, float(base))
    t = np.where(u < e, base + hi, t)
    t = np.where(u >= 0.55, base - 0.5 * sh, t)
    t = np.where(u >= 1 - 1.6 * e, base - sh, t)
    if lit > 0:
        t = np.where(u >= 1 - e * 0.9, base + amp, t)
    elif lit < 0:
        t = np.where(u < e * 0.9, base + amp + 0.4, t)
    P.put(m, t, hue, fog, k)
    return m


def hcyl(P, x0, x1, y0, y1, base, fog=0.0, hue=0.0, k=14.0, under=0.0):
    """horizontal pipe: highlight on top, shade below, optional glow-lit underside"""
    m = P.rect(x0, y0, x1, y1)
    v = (P.Y - y0) / float(y1 - y0)
    hpx = y1 - y0
    e = max(1.0, round(hpx * 0.16)) / hpx
    t = np.full_like(v, float(base))
    t = np.where(v < e, base + 1.0, t)
    t = np.where(v >= 0.55, base - 0.5, t)
    t = np.where(v >= 1 - e, base - 1.0 + under, t)
    P.put(m, t, hue, fog, k)
    return m


# ----------------------------------------------------------------------------
# REACTOR
# ----------------------------------------------------------------------------
R_WARM = ["#0d070d", "#120a12", "#1c0f18", "#2a1620", "#3a1e26", "#4f2526", "#6a2c1e",
          "#8a3a1a", "#b04e1e", "#d06a26", "#eb8f3c", "#ffc46b", "#fff0b8"]
R_TEAL = ["#0d070d", "#110c12", "#151319", "#182024", "#1c3034", "#204346", "#265a58",
          "#2f736c", "#3f8f82", "#5aaa98", "#86c7b3", "#b8e2cf", "#e2f6e8"]


def reactor_far():
    W = W_FAR
    P = Plate(W, H, [R_WARM, R_TEAL])
    X, Y = P.X, P.Y
    rnd = random.Random(11)
    CA, CB = 150, 386            # core columns (A = hero, B = farther)

    # ---- air light --------------------------------------------------------
    base = np.interp(Y, [0, 30, 105, 165, 198, 270], [1.2, 2.0, 3.2, 2.6, 1.7, 0.9]).astype(np.float32)
    gA = glow(P, CA, 106, 96, 112, 3.0)
    ang = np.arctan2(Y - 106, P.dx(CA))
    rays = 0.55 * np.sin(5 * ang + 0.5) + 0.4 * np.sin(11 * ang + 2.1) + 0.3 * np.sin(19 * ang + 4.0)
    gA = gA * (1.0 + 0.2 * rays)
    gB = glow(P, CB, 110, 60, 80, 1.9)
    gT = glow(P, 270, 128, 74, 56, 0.6)
    cloud = noise_x(W, H, 120, 5, 70) - 0.5
    hz = base + gA + gB + gT + cloud * 0.6
    hz *= np.interp(Y, [186, 232], [1.0, 0.42])
    P.haze[:] = hz
    P.put(np.ones((H, W), bool), hz, 0, 0, k=2.2)

    # ---- back wall (barely there: big shapes only) -------------------------
    for bx, bw in ((58, 30), (212, 24), (306, 22), (436, 30)):
        m = P.rect(bx, 0, bx + bw, 200)
        P.add(m, -0.55)
        P.add(P.rect(bx, 0, bx + 2, 200), 0.5)
    for sy in (150,):
        P.add(P.rect(0, sy, W, sy + 1), -0.45)
        P.add(P.rect(0, sy + 1, W, sy + 2), 0.25)
    # containment rings (giant coils) behind the cores
    P.add(P.ring(CA, 106, 84, 97), 0.8)
    P.add(P.ring(CA, 106, 97, 100), -0.6)
    P.add(P.ring(CA, 106, 81, 84), -0.5)
    for a in range(0, 360, 30):                      # coil clamps
        cx_ = CA + 90.5 * math.cos(math.radians(a + 15))
        cy_ = 106 + 90.5 * math.sin(math.radians(a + 15))
        P.add(P.ell(cx_, cy_, 5, 5), -0.7)
    P.add(P.ring(CB, 110, 52, 60), 0.6)
    P.add(P.ring(CB, 110, 60, 62), -0.5)

    # ---- far plane: stacks + a distant gantry, deep in the haze -------------
    for fx, fw, top in ((196, 12, 58), (334, 14, 50), (86, 10, 64)):
        vcyl(P, fx, fx + fw, top, 200, 1.2, fog=0.6, k=3.0, hi=0.8)
        P.put(P.rect(fx - 3, top - 4, fx + fw + 3, top), 1.2, fog=0.6, k=3)
        P.add(P.rect(fx + fw // 2 - 1, 88, fx + fw // 2 + 1, 128), 2.0)
        for by in (80, 132, 170):
            P.put(P.rect(fx - 2, by, fx + fw + 2, by + 4), 1.0, fog=0.58, k=3)

    # ---- overhead ducts ----------------------------------------------------
    hcyl(P, 0, W, 30, 44, 2.6, fog=0.25, under=1.6)
    for fx in (22, 96, 204, 262, 338, 430):
        P.put(P.rect(fx, 28, fx + 4, 46), 2.2, fog=0.2)
        P.put(P.rect(fx, 28, fx + 1, 46), 3.6, fog=0.2)

    # ---- tube bank: five tall gauge tubes at different levels ---------------
    levels = [0.5, 0.75, 0.25, 1.0, 0.5]
    ty0, ty1 = 76, 176
    for i, lv in enumerate(levels):
        cx = 226 + i * 22
        vcyl(P, cx - 2, cx + 2, 44, 68, 2.4, fog=0.25)       # riser up to the duct
        g = P.rect(cx - 7, ty0, cx + 7, ty1)                # glass body
        P.put(g, np.round(P.haze * 0.8 + 0.4), k=14)
        P.put(P.rect(cx - 7, ty0, cx - 6, ty1), np.round(P.haze * 0.8 + 1.6))
        P.put(P.rect(cx - 5, ty0 + 3, cx - 4, ty1), np.round(P.haze * 0.8 + 1.6))
        P.put(P.rect(cx + 6, ty0, cx + 7, ty1), np.round(P.haze * 0.8 - 0.8))
        P.put(P.rect(cx + 4, ty0, cx + 5, ty1), np.round(P.haze * 0.8 + 1.0))
        ly = ty1 - int(round((ty1 - ty0) * lv))             # liquid
        liq = P.rect(cx - 6, ly, cx + 6, ty1)
        uu = P.u(cx - 6, cx + 6)
        lt = np.where(uu < 0.17, 6.0, np.where(uu < 0.34, 7.0, np.where(uu < 0.7, 6.0, 5.0)))
        lt = lt - np.clip((Y - ly) / 100.0, 0, 1) * 1.2
        P.put(liq, lt, k=3)
        P.put(P.rect(cx - 6, ly, cx + 6, ly + 1), 9.0)
        P.put(P.rect(cx - 5, ly + 1, cx + 2, ly + 2), 7.6)
        for qd in (1, 2, 3):                                # quarter graduations
            qy = ty1 - (ty1 - ty0) * qd // 4
            P.put(P.rect(cx + 3, qy, cx + 7, qy + 1), 2.0)
            P.put(P.rect(cx - 7, qy, cx - 5, qy + 1), 2.0)
        P.put(P.rect(cx - 8, ty0 - 6, cx + 8, ty0), 2.6, fog=0.15)   # caps
        P.put(P.rect(cx - 8, ty0 - 6, cx + 8, ty0 - 5), 4.0, fog=0.15)
        P.put(P.rect(cx - 8, ty0 - 6, cx - 7, ty0), 4.0, fog=0.15)
        P.put(P.rect(cx - 5, ty0 - 9, cx + 5, ty0 - 6), 2.2, fog=0.15)
        P.put(P.rect(cx - 8, ty1, cx + 8, ty1 + 4), 2.2, fog=0.1)
        P.put(P.rect(cx - 8, ty1, cx + 8, ty1 + 1), 5.0)
    P.put(P.rect(212, 180, 328, 196), 2.0, fog=0.1)             # plinth
    P.put(P.rect(212, 180, 328, 181), 3.6, fog=0.1)
    P.put(P.rect(212, 180, 213, 196), 3.0, fog=0.1)
    P.put(P.rect(316, 181, 328, 196), 1.4, fog=0.1)
    P.put(P.rect(208, 196, 332, 204), 1.4, fog=0.05)
    P.put(P.rect(208, 196, 332, 197), 2.6, fog=0.05)
    for i in range(5):
        P.put(P.rect(222 + i * 22, 186, 230 + i * 22, 190), 0.8)

    # ---- core columns --------------------------------------------------------
    def core(cx, s, fog, gy0, gy1, top):
        S = lambda v: int(round(v * s))
        hw = S(24)
        # crown: wide head tapering into the shaft
        cw = S(38)
        vcyl(P, cx - cw, cx + cw, top, top + S(14), 3.0, fog=fog, hi=1.4)
        P.put(P.rect(cx - cw, top, cx + cw, top + 1), 4.4, fog=fog)
        P.put(P.rect(cx - cw, top + S(14) - 1, cx + cw, top + S(14)), 1.6, fog=fog)
        m = P.trap(cx - cw + 3, cx + cw - 3, top + S(14), cx - hw, cx + hw, top + S(26))
        uu = P.u(cx - cw, cx + cw)
        P.put(m, np.where(uu < 0.3, 3.2, np.where(uu < 0.62, 2.4, 1.6)), fog=fog)
        ul = m & ~_sh(m, 0, -1)                               # underside catches the core light
        P.put(ul | (_sh(ul, 0, -1) & m), 5.4)
        P.put(ul, 6.6)
        for i in range(3):                                  # crown vents
            P.put(P.rect(cx - S(12) + i * S(9), top + S(5), cx - S(12) + i * S(9) + S(5), top + S(9)), 1.2, fog=fog * 0.5)
        # shaft
        vcyl(P, cx - hw, cx + hw, top + S(26), 180, 3.0, fog=fog, hi=1.4, sh=1.2)
        # glass throat in four stacked sections: dim red chamber, thin white-hot filament
        gw = S(17)
        gm = P.rect(cx - gw, gy0, cx + gw, gy1)
        d = np.abs(P.dx(cx)) / gw
        cham = 7.4 - d * 2.6
        cham = np.where(d > 0.78, cham - 0.8, cham)
        P.put(gm, cham, k=2.4)
        wig = np.round(1.0 * np.sin(Y * 0.31 + cx))
        dd = np.abs(P.dx(cx) - wig)
        fil = np.where(dd < 1.2 * s + 0.4, 12.0, np.where(dd < 2.6 * s + 0.6, 10.6, np.where(dd < 5.0 * s, 9.0, 0.0)))
        P.put(gm & (fil > 0), fil, k=2.4)
        sec = (gy1 - gy0) / 4.0
        for i in range(4):                                  # a soft node in each section
            ny = gy0 + sec * (i + 0.5)
            nd = P.ell(cx, ny, 5.5 * s, 6.5 * s)
            P.add(gm & nd, 1.0)
        P.add(P.rect(cx - gw + 2, gy0, cx - gw + 3, gy1), 1.6)      # glass reflection
        # side rails
        P.put(P.rect(cx - hw, gy0, cx - gw, gy1), 3.0, fog=fog * 0.6)
        P.put(P.rect(cx - hw, gy0, cx - hw + max(1, S(2)), gy1), 4.4, fog=fog * 0.6)
        P.put(P.rect(cx - gw - 1, gy0, cx - gw, gy1), 6.0)
        P.put(P.rect(cx + gw, gy0, cx + hw, gy1), 2.0, fog=fog * 0.6)
        P.put(P.rect(cx + gw, gy0, cx + gw + 1, gy1), 6.0)
        # clamp bands (quarters)
        ch = max(3, S(6))
        for i in range(5):
            cy = int(gy0 + sec * i) - ch // 2
            b = P.rect(cx - hw - 3, cy, cx + hw + 3, cy + ch)
            uu = P.u(cx - hw - 3, cx + hw + 3)
            bt = np.where(uu < 0.08, 4.6, np.where(uu < 0.5, 3.2, np.where(uu < 0.85, 2.4, 1.8)))
            P.put(b, bt, fog=fog * 0.5)
            P.put(P.rect(cx - hw - 3, cy, cx + hw + 3, cy + 1), 4.2, fog=fog * 0.5)
            P.put(P.rect(cx - hw - 3, cy + ch - 1, cx + hw + 3, cy + ch), 1.6, fog=fog * 0.5)
            if i < 4:
                P.put(P.rect(cx - gw, cy + ch - 1, cx + gw, cy + ch), 6.4)   # lit underside
            if i > 0:
                P.put(P.rect(cx - gw, cy, cx + gw, cy + 1), 7.0)
            for bx_ in (cx - hw, cx - S(8), cx + S(6), cx + hw - 2):          # bolts
                P.put(P.rect(bx_, cy + ch // 2, bx_ + 1, cy + ch // 2 + 1), 1.6)
        # lower housing with glowing vent slits
        for i in range(3):
            vy = gy1 + S(8) + i * max(3, S(5))
            P.put(P.rect(cx - gw + 2, vy, cx + gw - 4, vy + max(1, S(2))), 7.0 - i * 0.9)
            P.put(P.rect(cx - gw + 2, vy - 1, cx + gw - 4, vy), 1.6)
        # base flare + plinth
        bw = S(42)
        m = P.trap(cx - hw, cx + hw, 178, cx - bw, cx + bw, 196)
        uu = P.u(cx - bw, cx + bw)
        P.put(m, np.where(uu < 0.3, 4.0, np.where(uu < 0.62, 3.0, 2.0)), fog=fog * 0.7)
        P.put(P.lines([(cx - hw, 178), (cx - bw, 196)], 1), 5.0, fog=fog * 0.7)
        P.put(P.rect(cx - hw, 178, cx + hw, 179), 5.6)
        P.put(P.rect(cx - hw + 2, 179, cx + hw - 2, 180), 4.6)
        P.put(P.rect(cx - bw - 4, 196, cx + bw + 4, 204), 1.6, fog=fog * 0.5)
        P.put(P.rect(cx - bw - 4, 196, cx + bw + 4, 197), 3.6, fog=fog * 0.5)
        P.put(P.rect(cx - bw - 4, 196, cx - bw - 3, 204), 3.0, fog=fog * 0.5)

    core(CB, 0.66, 0.4, 82, 142, 30)
    vcyl(P, CB - 8, CB + 8, 22, 30, 2.4, fog=0.4)
    core(CA, 1.0, 0.1, 64, 152, 24)
    vcyl(P, CA - 14, CA + 14, 10, 24, 2.4, fog=0.1)
    # bloom: the light spills over the machinery right next to the glass
    P.add(None, glow(P, CA, 108, 44, 62, 1.1) * (Y < 200))
    P.add(None, glow(P, CB, 112, 28, 42, 0.8) * (Y < 200))
    # feed pipes from core A's shaft out to the duct line
    for sgn in (-1, 1):
        x0 = CA + sgn * 24
        x1 = CA + sgn * 50
        a_, b_ = min(x0, x1), max(x0, x1)
        hcyl(P, a_, b_, 52, 59, 2.6, fog=0.15, under=1.8)
        vcyl(P, x1 - 4, x1 + 3, 44, 59, 2.6, fog=0.15, lit=-sgn, amp=1.8)

    # ---- coolant tanks (row that wraps across the seam) ----------------------
    tanks = [(440, 0.25), (476, 0.75), (512, 0.5), (548, 1.0)]
    for j, (tx, lv) in enumerate(tanks):
        tw, t0, t1 = 30, 132, 198
        cx = tx + tw / 2.0
        lit = 1 if (tx % W) < CA else -1
        amp = 3.0 if j >= 2 else 2.0
        dm = P.ell(cx - 0.5, t0 + 10, tw / 2.0, 11) & (Y < t0 + 10)        # dome
        uu = P.u(tx, tx + tw)
        dt = np.where(uu < 0.2, 4.2, np.where(uu < 0.56, 3.0, 2.0))
        if lit > 0:
            dt = np.where(uu > 0.9, 3.0 + amp, dt)
        P.put(dm, dt, fog=0.08)
        vcyl(P, tx, tx + tw, t0 + 10, t1, 3.0, fog=0.08, lit=lit, amp=amp, hi=1.2)
        for hy in (t0 + 10, t0 + 36, t1 - 6):                             # hoops
            P.put(P.rect(tx - 1, hy, tx + tw + 1, hy + 3), 2.0, fog=0.06)
            P.put(P.rect(tx - 1, hy, tx + tw + 1, hy + 1), 3.6, fog=0.06)
            P.put(P.rect(tx - 1, hy, tx + 2, hy + 1), 4.6, fog=0.06)
        gx, g0, g1 = tx + 12, t0 + 16, t0 + 32                            # teal sight glass
        P.put(P.rect(gx - 1, g0 - 1, gx + 5, g1 + 1), 1.2)
        P.put(P.rect(gx, g0, gx + 4, g1), 2.6, hue=1)
        fy = g1 - int(round((g1 - g0) * lv))
        P.put(P.rect(gx, fy, gx + 4, g1), 6.0, hue=1)
        P.put(P.rect(gx, fy, gx + 4, fy + 1), 7.6, hue=1)
        P.put(P.rect(int(cx) - 4, t0 - 3, int(cx) + 4, t0 + 1), 2.4, fog=0.1)
        vcyl(P, int(cx) - 2, int(cx) + 2, 44, t0 - 3, 2.4, fog=0.25)
        P.put(P.rect(tx - 2, t1, tx + tw + 2, t1 + 6), 1.5)
        P.put(P.rect(tx - 2, t1, tx + tw + 2, t1 + 1), 3.0)

    # ---- floor: dark, calm, a little reflected glow --------------------------
    fl = Y >= 204
    ft = np.interp(Y, [204, 224, 270], [1.6, 1.0, 0.6]).astype(np.float32)
    refl = glow(P, CA, 204, 26, 44, 2.6) + glow(P, CB, 204, 18, 30, 1.4) + glow(P, 270, 204, 56, 20, 1.0)
    streak = (np.sin(Y * 1.9) > -0.2).astype(np.float32) * 0.45 + 0.55
    P.put(fl, ft + refl * streak, k=2.0)
    P.put(P.rect(0, 203, W, 204), 2.2 + refl * 0.8, k=3)
    for fy in (214, 230, 252):
        P.add(P.rect(0, fy, W, fy + 1), -0.5)

    # ---- ceiling gantry: the darkest, nearest shapes -------------------------
    P.put(P.rect(0, 0, W, 9), 0.6)
    P.put(P.rect(0, 9, W, 10), 2.0)
    P.put(P.rect(0, 20, W, 22), 0.8)
    P.put(P.rect(0, 22, W, 23), 2.0)
    for i in range(0, W, 40):
        P.put(P.lines([(i, 10), (i + 20, 20)], 2), 0.8)
        P.put(P.lines([(i + 20, 20), (i + 40, 10)], 2), 0.8)
        P.put(P.rect(i - 1, 9, i + 2, 22), 0.6)
    # hanging lamps with soft cones of light
    for lx, ln in ((66, 30), (270, 22), (424, 26)):
        P.put(P.rect(lx, 22, lx + 1, 22 + ln), 0.8)
        P.put(P.trap(lx - 2, lx + 3, 22 + ln, lx - 5, lx + 6, 22 + ln + 4), 0.8)
        P.put(P.rect(lx - 4, 22 + ln + 4, lx + 5, 22 + ln + 5), 11.0)
        y0 = 22 + ln + 5
        cone = P.trap(lx - 4, lx + 5, y0, lx - 40, lx + 41, y0 + 130)
        fall = np.clip(1 - (Y - y0) / 130.0, 0, 1) ** 1.2
        P.add(cone, fall * 1.5)

    # ---- small life: embers and indicator lights -----------------------------
    for i in range(26):
        a = rnd.uniform(0, 6.283)
        r = rnd.uniform(34, 96)
        ex, ey = CA + math.cos(a) * r * 0.9, 100 + math.sin(a) * r
        if 26 < ey < 196:
            P.dot(ex, ey, hexc(R_WARM[rnd.choice((9, 10, 11))]))
    for i in range(8):
        P.dot(CB + rnd.uniform(-50, 50), rnd.uniform(60, 160), hexc(R_WARM[rnd.choice((8, 9))]))
    for gx in (14, 118, 190, 300, 356, 452):
        P.dot(gx, 15, hexc(pix.RAMPS["red"][2]))
        P.dot(gx + 1, 15, hexc(pix.RAMPS["red"][1]))
    for i in range(5):
        P.dot(225 + i * 22, 188, hexc(R_TEAL[8]))
    return P.render()


# mid-layer colour table: neutral hull darks + a warm rim row
RM_HULL = ["#0d070d", "#120a12", "#1a1218", "#2a1c24", "#3e2a32", "#573c40", "#775650"]
RM_WARM = ["#0d070d", "#160b10", "#26100f", "#4a160e", "#6a2110", "#8a2c10", "#c9471a"]


def reactor_mid():
    W = W_MID
    P = Plate(W, H, [RM_HULL, RM_WARM])
    X, Y = P.X, P.Y
    HU, WM = 0, 1

    def S(m, base=2.0, rim=2.0, **kw):
        return sil(P, m, base, rim=rim, rim_hue=WM, hue=HU, **kw)

    def pipe_h(x0, x1, y0, h, flanges=()):
        m = P.rect(x0, y0, x1, y0 + h)
        r = Y - y0
        t = np.where(r < 1, 2.0, np.where(r < 1 + max(1, h // 5), 3.0, np.where(r < h * 0.58, 2.0, 1.0)))
        P.put(m, t, HU)
        P.put(P.rect(x0, y0 + h - 1, x1, y0 + h), 4.0, WM)
        if h >= 10:
            P.put(P.rect(x0, y0 + h - 2, x1, y0 + h - 1), 2.0, WM)
        for fx in flanges:
            S(P.rect(fx, y0 - 2, fx + 5, y0 + h + 2))
            P.put(P.rect(fx + 1, y0 + 1, fx + 2, y0 + h - 2), 3.0, HU)

    def pipe_v(x0, w_, y0, y1, flanges=()):
        m = P.rect(x0, y0, x0 + w_, y1)
        r = (X - x0) % W
        t = np.where(r < 1, 2.0, np.where(r < 1 + max(1, w_ // 5), 3.0, np.where(r < w_ * 0.58, 2.0, 1.0)))
        P.put(m, t, HU)
        P.put(P.rect(x0 + w_ - 1, y0, x0 + w_, y1), 4.0, WM)
        if w_ >= 10:
            P.put(P.rect(x0 + w_ - 2, y0, x0 + w_ - 1, y1), 2.0, WM)
        for fy in flanges:
            S(P.rect(x0 - 2, fy, x0 + w_ + 2, fy + 5))
            P.put(P.rect(x0 + 1, fy + 1, x0 + w_ - 3, fy + 2), 3.0, HU)

    def chain(x, y0, y1):
        y = y0
        while y < y1:
            P.put(P.rect(x, y, x + 4, y + 6), 2.0, HU)
            P.cut(P.rect(x + 1, y + 1, x + 3, y + 5))
            P.put(P.rect(x, y + 1, x + 1, y + 4), 3.0, HU)
            P.put(P.rect(x + 3, y + 4, x + 4, y + 6), 3.0, WM)
            P.put(P.rect(x + 1, y + 5, x + 3, y + 9), 2.0, HU)
            P.put(P.rect(x + 1, y + 5, x + 2, y + 9), 3.0, HU)
            y += 8

    def wheel(cx, cy, r):
        """hand-wheel seen face on"""
        rg = P.ring(cx, cy, r - 2.4, r)
        S(rg, 2.0)
        sp = (P.ell(cx, cy, r - 1, r - 1)) & ((np.abs(P.dx(cx)) < 1.0) | (np.abs(Y - cy) < 1.0))
        P.put(sp & ~rg, 2.0, HU)
        S(P.ell(cx, cy, 2.4, 2.4), 3.0, rim=0)

    def gauge(cx, cy, r=5):
        S(P.ell(cx, cy, r, r), 2.0)
        P.put(P.ell(cx, cy, r - 2, r - 2), 1.0, HU)
        P.put(P.lines([(cx, cy), (cx + r - 3, cy - r + 3)], 1), 4.0, WM)

    # ---- hangers to the (unseen) ceiling -------------------------------------------
    for hx in (22, 196, 300, 420, 590):
        P.put(P.rect(hx, 0, hx + 3, 12), 1.0, HU)
        P.put(P.rect(hx, 0, hx + 1, 12), 2.0, HU)
        S(P.rect(hx - 3, 9, hx + 6, 12), 2.0, rim=0)
        S(P.rect(hx - 3, 26, hx + 6, 29), 2.0)
        P.put(P.rect(hx - 3, 12, hx - 2, 26), 1.0, HU)
        P.put(P.rect(hx + 5, 12, hx + 6, 26), 1.0, HU)

    # ---- main pipe run + a thinner companion ------------------------------------------
    pipe_h(0, W, 12, 14, flanges=(48, 150, 244, 392, 536))
    pipe_h(0, W, 2, 5)
    pipe_h(176, 468, 36, 8, flanges=(232, 330, 428))
    # tee up into the main pipe
    for tx in (204, 452):
        pipe_v(tx, 8, 26, 36)
    # valve on the thin pipe: stem + wheel edge-on, and a gauge
    S(P.rect(279, 30, 283, 36), 2.0, rim=0)
    S(P.rect(271, 28, 291, 31), 2.0)
    P.put(P.rect(280, 26, 282, 28), 3.0, HU)
    S(P.rect(276, 34, 286, 46), 2.0)
    P.put(P.rect(354, 44, 356, 50), 2.0, HU)
    gauge(355, 55, 6)

    # ---- elbow down into the big riser ---------------------------------------------------
    rx0, rw = 468, 16
    el = P.ring(rx0, 36 + 20, 4, 20) & (X >= rx0) & (Y < 56) if False else None
    cxe, cye = 468, 56            # centre of curvature
    d = np.hypot(P.dx(cxe), Y - cye)
    elbow = (d >= 4) & (d < 20) & (P.dx(cxe) >= 0) & (Y <= cye)
    te = np.where(d > 18.5, 2.0, np.where(d > 15, 3.0, np.where(d > 10, 2.0, 1.0)))
    P.put(elbow, te, HU)
    P.put(elbow & (d < 5.2), 4.0, WM)
    # riser: runs off the bottom
    m = P.rect(rx0 + 4, 56, rx0 + 20, H)
    r = (X - (rx0 + 4)) % W
    t = np.where(r < 1, 2.0, np.where(r < 4, 3.0, np.where(r < 9, 2.0, np.where(r < 14, 1.0, 2.0))))
    P.put(m, t, HU)
    P.put(P.rect(rx0 + 19, 56, rx0 + 20, H), 4.0, WM)
    for fy in (56, 132, 206):
        S(P.rect(rx0 + 2, fy, rx0 + 22, fy + 5))
    # bypass loop + gauge on the riser
    pipe_v(rx0 + 28, 4, 84, 124)
    pipe_h(rx0 + 20, rx0 + 32, 80, 4)
    pipe_h(rx0 + 20, rx0 + 32, 124, 4)
    S(P.rect(rx0 + 26, 98, rx0 + 34, 108), 2.0)
    P.put(P.rect(rx0 - 4, 166, rx0 + 4, 168), 2.0, HU)
    gauge(rx0 - 7, 167, 5)

    # ---- drop pipe with a nozzle and a wisp of steam --------------------------------------
    pipe_v(204, 8, 44, 84, flanges=(62,))
    S(P.trap(203, 213, 84, 198, 218, 94), 2.0)
    S(P.rect(197, 94, 219, 97), 2.0)
    for (sx_, sy_, rr, al) in ((208, 102, 4.5, 60), (205, 109, 5.5, 50), (211, 116, 6.5, 40), (205, 125, 7.5, 30),
                              (212, 134, 8.5, 20), (207, 145, 8.5, 12)):
        st = P.ell(sx_, sy_, rr, rr * 0.8) & ~P.a
        P.over[st] = (119, 86, 80, al)
        hl = st & ~_sh(P.ell(sx_, sy_, rr, rr * 0.8), 1, 1)
        P.over[hl] = (156, 122, 104, al + 10)

    # ---- suspended catwalk (wraps over the seam) ---------------------------------------------
    cx0, cx1, cy = 524, 524 + 250, 98
    for hx in (cx0 + 3, cx0 + 124, cx1 - 5):                    # hanger rods
        P.put(P.rect(hx, 26, hx + 2, cy - 16), 1.0, HU)
        P.put(P.rect(hx, 26, hx + 1, cy - 16), 2.0, HU)
    for i in range(cx0, cx1 - 8, 25):                           # posts
        P.put(P.rect(i, cy - 15, i + 2, cy), 2.0, HU)
        P.put(P.rect(i, cy - 15, i + 1, cy), 3.0, HU)
    P.put(P.rect(cx1 - 2, cy - 15, cx1, cy), 2.0, HU)
    S(P.rect(cx0 - 1, cy - 17, cx1 + 1, cy - 15), 2.0, rim=0)      # hand rail
    P.put(P.rect(cx0, cy - 8, cx1, cy - 7), 1.0, HU)
    S(P.rect(cx0 - 3, cy, cx1 + 3, cy + 5), 2.0, hi=0)           # deck (kept dull: it must not read as a platform)
    P.put(P.rect(cx0 - 3, cy + 2, cx1 + 3, cy + 3) & ((X // 3) % 2 == 0), 1.0, HU)
    P.put(P.rect(cx0, cy + 13, cx1, cy + 14), 1.0, HU)
    P.put(P.rect(cx0, cy + 14, cx1, cy + 15), 3.0, WM)
    for i in range(cx0, cx1, 25):                               # truss
        P.put(P.lines([(i, cy + 5), (i + 12, cy + 13)], 1), 2.0, HU)
        P.put(P.lines([(i + 12, cy + 13), (i + 25, cy + 5)], 1), 1.0, HU)
    # ladder up from the catwalk
    lx = cx0 + 60
    P.put(P.rect(lx, 26, lx + 2, cy - 17), 2.0, HU)
    P.put(P.rect(lx + 9, 26, lx + 11, cy - 17), 1.0, HU)
    for ry in range(30, cy - 18, 5):
        P.put(P.rect(lx + 2, ry, lx + 9, ry + 1), 2.0, HU)
    # work lamp under the deck
    lpx = cx0 + 190
    P.put(P.rect(lpx, cy + 15, lpx + 1, cy + 22), 1.0, HU)
    S(P.trap(lpx - 2, lpx + 3, cy + 22, lpx - 5, lpx + 6, cy + 26), 2.0, rim=0)
    P.put(P.rect(lpx - 4, cy + 26, lpx + 5, cy + 27), 6.0, WM)
    cone = P.trap(lpx - 4, lpx + 5, cy + 27, lpx - 26, lpx + 27, cy + 27 + 70) & ~P.a
    ca = (np.clip(1 - (Y - (cy + 27)) / 70.0, 0, 1) ** 1.5 * 46)
    P.over[cone] = np.dstack([np.full_like(Y, 201), np.full_like(Y, 71), np.full_like(Y, 26), ca])[cone]

    # ---- chains ---------------------------------------------------------------------------
    chain(252, 44, 150)
    S(P.rect(248, 150, 260, 161), 2.0)                          # hook block
    P.put(P.rect(251, 153, 257, 155), 1.0, HU)
    hk = P.ring(254, 168, 3.6, 6.4) & ~P.rect(246, 161, 253, 168)
    S(hk | P.rect(253, 161, 256, 164), 2.0)
    chain(384, 44, 118)
    S(P.trap(381, 391, 118, 377, 395, 136), 2.0)                # counterweight
    S(P.rect(377, 136, 395, 140), 2.0)
    P.put(P.rect(380, 126, 392, 127), 1.0, HU)
    chain(100, 26, 62)
    # slack swag
    pts = [(302 + t * 0.01 * 116, 44 + 30 * (1 - (2 * t * 0.01 - 1) ** 2)) for t in range(0, 101)]
    sw = P.lines(pts, 2) & ~P.a
    P.put(sw, 2.0, HU)
    P.put(sw & ((X + Y) % 4 < 1), 3.0, HU)

    # ---- machinery rising from the bottom edge ------------------------------------------------
    # boiler: dome, hatch wheel, stack with a cap
    S(P.rect(133, 200, 141, H), 2.0)
    S(P.rect(130, 196, 144, 200), 2.0)
    S(P.rect(127, 192, 147, 195), 2.0)
    dome = (P.ell(92, 250, 48, 38) & (Y < 250)) | P.rect(44, 250, 140, H)
    S(dome, 2.0)
    P.put(P.ell(92, 250, 48, 38) & ~P.ell(96, 255, 48, 38) & (Y < 250) & (X < 92), 3.0, HU)
    for by in (236, 258):
        bm = dome & (Y >= by) & (Y < by + 2)
        P.put(bm, 1.0, HU)
        P.put(_sh(bm, 0, -2) & dome & (Y < by), 3.0, HU)
    S(P.rect(84, 204, 100, 212), 2.0, rim=0)
    wheel(78, 232, 8)
    gauge(112, 228, 5)
    # valve manifold: three risers of different heights on a header
    for (mx, top) in ((300, 222), (322, 204), (344, 230)):
        pipe_v(mx, 8, top, H)
        S(P.rect(mx - 2, top - 3, mx + 10, top + 1), 2.0)
        P.put(P.rect(mx + 3, top - 9, mx + 5, top - 3), 2.0, HU)
        S(P.rect(mx - 5, top - 11, mx + 13, top - 8), 2.0)
    pipe_h(292, 360, 246, 8, flanges=(314, 338))
    # pipe arch with flanged feet
    d = np.hypot(P.dx(572), Y - 262)
    arch = (d >= 26) & (d < 40) & (Y < 262)
    ta = np.where(d > 38.5, 2.0, np.where(d > 35, 3.0, np.where(d > 31, 2.0, 1.0)))
    P.put(arch, ta, HU)
    P.put(arch & (d < 27.2), 4.0, WM)
    P.put(arch & (d > 38.5) & (X > 590), 1.0, HU)
    for fx in (530, 596):
        S(P.rect(fx, 256, fx + 18, 262), 2.0)
        pipe_v(fx + 2, 14, 262, H)
    # drums
    for (dx_, top) in ((408, 236), (426, 242)):
        S(P.rect(dx_, top, dx_ + 16, H), 2.0)
        P.put(P.rect(dx_ + 2, top + 1, dx_ + 4, H), 3.0, HU)
        for by in (top + 6, top + 16):
            P.put(P.rect(dx_, by, dx_ + 16, by + 1), 1.0, HU)
    return P.render()


# ----------------------------------------------------------------------------
# silhouette helpers for the mid layers
# ----------------------------------------------------------------------------
def _sh(m, dx, dy):
    """shift a mask (wraps in x, clips in y)"""
    o = np.roll(m, dx, axis=1)
    if dy > 0:
        o = np.vstack([np.zeros((dy, m.shape[1]), bool), o[:-dy]])
    elif dy < 0:
        o = np.vstack([o[-dy:], np.zeros((-dy, m.shape[1]), bool)])
    return o


def sil(P, m, base=2.0, hi=1.0, sh=1.0, rim=0.0, rim_hue=0.0, hue=0.0):
    """flat silhouette with a 1px bevel: key light top-left, optional coloured bounce on the
    bottom/right edges (the glow of the far layer catching the underside)."""
    P.put(m, base, hue)
    top = m & ~_sh(m, 0, 1)
    left = m & ~_sh(m, 1, 0)
    bot = m & ~_sh(m, 0, -1)
    right = m & ~_sh(m, -1, 0)
    if sh:
        P.put(right, base - sh, hue)
    if rim:
        P.put(bot, base + rim, rim_hue)
    elif sh:
        P.put(bot, base - sh, hue)
    if hi:
        P.put(left, base + hi * 0.5, hue)
        P.put(top, base + hi, hue)
    return m


def rot_uv(P, cx, cy, deg):
    """local coordinates of every pixel in a frame rotated by deg around (cx, cy), wrapped in x"""
    a = math.radians(deg)
    dx = P.dx(cx)
    dy = P.Y - cy
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


def face_uv(P, pts):
    """0..1 coordinates across a parallelogram face (p0->p1 = a axis, p0->p3 = b axis)"""
    p0, p1, _, p3 = pts
    ax, ay = p1[0] - p0[0], p1[1] - p0[1]
    bx, by = p3[0] - p0[0], p3[1] - p0[1]
    det = ax * by - ay * bx
    if abs(det) < 1e-6:
        det = 1e-6
    dx = P.dx(p0[0])
    dy = P.Y - p0[1]
    return (dx * by - dy * bx) / det, (ax * dy - ay * dx) / det


def box3d(P, cx, cy, size, yaw, pitch, roll, base=3.0, hue=0.0, style="cargo", acc_hue=None):
    """tumbling crate: orthographic box, up to three visible faces, each textured in its own
    face space (frame, recessed panel, brace / strap, bolts) with flat tones."""
    sx, sy, sz = size

    def rm(ax, d):
        c, s_ = math.cos(math.radians(d)), math.sin(math.radians(d))
        if ax == 0:
            return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])
        if ax == 1:
            return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
        return np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
    M = rm(2, roll) @ rm(0, pitch) @ rm(1, yaw)
    L = np.array([-0.55, -0.7, 0.45])
    L = L / np.linalg.norm(L)
    hs = np.array([sx, sy, sz]) / 2.0
    faces = []
    for ax in range(3):
        for sg in (-1, 1):
            n = np.zeros(3)
            n[ax] = sg
            nr = M @ n
            if nr[2] <= 0.02:
                continue
            o = [0, 1, 2]
            o.remove(ax)
            pts = []
            for a_, b_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                p = np.zeros(3)
                p[ax] = sg * hs[ax]
                p[o[0]] = a_ * hs[o[0]]
                p[o[1]] = b_ * hs[o[1]]
                q = M @ p
                pts.append((cx + q[0], cy + q[1]))
            faces.append((float(nr @ L), pts, hs[o[0]] * 2, hs[o[1]] * 2))
    faces.sort(key=lambda f: f[0])
    nf = len(faces)
    for fi, (lit, pts, la, lb) in enumerate(faces):
        rank = fi - (nf - 1)                       # 0 = brightest, -1, -2 darker
        t = base + 1.0 + rank
        m = P.poly(pts)
        fa, fb = face_uv(P, pts)
        ea = np.minimum(fa, 1 - fa) * la           # distance to the edges, in face pixels
        eb = np.minimum(fb, 1 - fb) * lb
        e = np.minimum(ea, eb)
        fr = max(2.0, min(la, lb) * 0.13)
        P.put(m, t, hue)
        panel = m & (e > fr)
        if style == "cargo":
            P.put(panel, t - 1, hue)
            P.put(panel & (e < fr + 1.1), t - 2 if t >= 2 else t - 1, hue)       # recess shadow
            br = panel & (np.abs((fa - 0.5) * la - (fb - 0.5) * lb * (la / lb)) < max(1.2, la * 0.07))
            P.put(br, t, hue)
        elif style == "tech":
            P.put(panel, t - 1, hue)
            band = m & (np.abs(fb - 0.5) * lb < max(1.5, lb * 0.11))
            P.put(band, t, hue)
            P.put(band & (np.abs(fa - 0.5) * la < 2.2), t - 1, hue)
            if acc_hue is not None and rank == 0:
                ind = m & (np.abs(fa - 0.76) * la < max(1.6, la * 0.07)) & (np.abs(fb - 0.24) * lb < max(1.1, lb * 0.05))
                P.put(ind, 6.0, acc_hue)
        elif style == "strap":
            for q in (0.28, 0.72):
                P.put(m & (np.abs(fa - q) * la < max(1.2, la * 0.06)), t - 1, hue)
            P.put(panel & (np.abs(fb - 0.5) * lb < 1.0), t - 1, hue)
        # corner bolts
        for qa in (0.5 * fr / la, 1 - 0.5 * fr / la):
            for qb in (0.5 * fr / lb, 1 - 0.5 * fr / lb):
                P.put(m & (np.abs(fa - qa) * la < 0.8) & (np.abs(fb - qb) * lb < 0.8), t - 1, hue)
        # lit edges: the two edges of each face that lean toward the light
        outl = P.lines(pts + [pts[0]], 1) & m
        P.put(outl, t + (1.0 if rank == 0 else 0.5 if rank == -1 else 0.0), hue, k=8)
    return faces


# ----------------------------------------------------------------------------
# ZERO-G
# ----------------------------------------------------------------------------
Z_VIO = ["#0a0719", "#0c0820", "#140e30", "#1d1544", "#281d5a", "#362470", "#472585",
         "#5c33a4", "#6f3fc0", "#8a56da", "#a26bf0", "#cfa8ff", "#f0e0ff"]
Z_CYA = ["#0a0719", "#0b0b24", "#0f1634", "#12254a", "#143a5e", "#135470", "#0f7480",
         "#12a3a6", "#20c4bc", "#2de0d0", "#8ff7ea", "#dcfffa", "#ffffff"]


def zerog_far():
    W = W_FAR
    P = Plate(W, H, [Z_VIO, Z_CYA])
    X, Y = P.X, P.Y
    rnd = random.Random(23)
    cy, R, A = 118.0, 160.0, 96.0
    v = (Y - cy) / R
    c = np.sqrt(np.clip(1 - v * v, 0, 1))
    th = np.degrees(np.arcsin(np.clip(v, -1, 1)))
    s = (X - A * c) % W                     # axial coordinate of the far wall under each pixel
    TH_MAIN, TH_CYAN = -31.0, 14.0
    y_main = cy + R * math.sin(math.radians(TH_MAIN))
    y_cyan = cy + R * math.sin(math.radians(TH_CYAN))

    # ---- wall: light falls off away from the strips, floor side sinks into dark
    Lm = np.exp(-((th - TH_MAIN) / 26.0) ** 2)
    Lc = np.exp(-((th - TH_CYAN) / 9.0) ** 2)
    cloud = noise_x(W, H, 120, 9, 80) - 0.5
    tone = 2.1 + 2.0 * Lm + 0.8 * Lc + cloud * 0.5
    tone *= np.interp(th, [-60, -47, 24, 46, 75], [0.7, 1.0, 1.0, 0.66, 0.5])
    P.haze[:] = tone
    P.put(np.ones((H, W), bool), tone, 0, 0, k=2.2)
    P.tint(None, Lc * 0.6, 1)

    # panels: rows are equal steps of angle, so they crowd together toward floor and ceiling
    row = np.floor((th + 61) / 15.0)
    shift = (row * 24) % 48
    col = np.floor(((s + shift) % W) / 48.0)
    hsh = ((row * 7 + col * 13 + (col * row) % 3) % 6).astype(int)
    off = np.array([-0.45, 0.0, 0.3, 0.0, -0.2, 0.15], np.float32)[hsh]
    P.add(None, off)
    vs = ((s + shift) % 48.0) < 1.0
    P.add(vs, -0.7)
    P.add(_sh(vs, 1, 0) & ~vs, 0.3)
    for tb in range(-46, 75, 15):
        yb = int(round(cy + R * math.sin(math.radians(tb))))
        P.add(P.rect(0, yb, W, yb + 1), -0.8)
        P.add(P.rect(0, yb + 1, W, yb + 2), 0.35)

    # ---- light strips along the axis ------------------------------------------
    seg = ((s + 30) % 120.0) < 96
    ym = int(round(y_main))
    P.put(P.rect(0, ym - 2, W, ym + 3), 3.0)
    P.put(P.rect(0, ym - 1, W, ym + 2) & seg, 10.0, k=3)
    P.put(P.rect(0, ym, W, ym + 1) & seg, 12.0)
    bloom = np.exp(-((Y - ym) / 7.0) ** 2) * 2.0 + np.exp(-((Y - ym) / 22.0) ** 2) * 0.8
    P.add(np.abs(Y - ym) > 1, bloom)
    # soft curtains of light hanging under each lit segment
    c_m = math.sqrt(1 - ((ym - cy) / R) ** 2)
    seg_x = (((X - A * c_m) % W + 30) % 120.0)
    curt = np.clip(np.minimum(seg_x - 4, 92 - seg_x) / 14.0, 0, 1)
    P.add(Y > ym + 2, curt * np.exp(-np.clip(Y - ym, 0, 400) / 70.0) * 0.55)

    # ---- wall furniture: a ladder that follows the curve, hatches, a conduit ---------
    for s_l in (286.0, 296.0):                                   # ladder rails
        P.put((np.abs(((s - s_l + W / 2) % W) - W / 2) < 0.6) & (th > -44) & (th < 40), np.round(P.haze + 1.4))
    rung = (((s - 286.0) % W) < 10) & (th > -44) & (th < 40) & ((np.floor((th + 60) / 3.0) % 2) == 0) & (((th + 60) % 3.0) < 3.0 * 1.2 / np.maximum(R * c * math.radians(3.0), 1.2))
    P.put(rung, np.round(P.haze + 1.0))
    for (hs, ht0, ht1, w_) in ((92.0, -13.0, -3.0, 26.0), (232.0, 18.0, 27.0, 22.0), (428.0, -27.0, -18.0, 30.0)):   # hatches
        hm = (((s - hs) % W) < w_) & (th > ht0) & (th < ht1)
        P.put(hm, np.round(P.haze - 1.0))
        P.put(hm & ~_sh(hm, 0, 1), np.round(P.haze + 1.2))
        P.put(hm & ~_sh(hm, 1, 0), np.round(P.haze + 0.6))
        lm = (((s - hs - 3) % W) < 2) & (np.abs(th - (ht0 + ht1) / 2) < 0.6)
        P.put(lm, 9.0, 1)
    for (tc, tone_) in ((38.5, 1.0), (41.0, 2.0)):
        yc_ = int(round(cy + R * math.sin(math.radians(tc))))
        P.put(P.rect(0, yc_, W, yc_ + 3), tone_)
        P.put(P.rect(0, yc_, W, yc_ + 1), tone_ + 1.6)
        P.put(P.rect(0, yc_, W, yc_ + 3) & ((s % 60) < 3), tone_ + 1.0)
    yc = int(round(y_cyan))
    segc = ((s + 60) % 80.0) < 58
    P.put(P.rect(0, yc - 1, W, yc + 2), 2.0, 1)
    P.put(P.rect(0, yc, W, yc + 1) & segc, 9.0, 1)

    # ---- ring ribs (flanges standing in from the wall) --------------------------
    rho, tk = 0.86, 8.0
    xo = A * c
    xi = A * rho * np.sqrt(np.clip(1 - (v / rho) ** 2, 0, 1))
    inside = np.abs(v) < rho
    ribs = (22.0, 172.0, 344.0)
    for s0 in ribs:
        d0 = (X - s0) % W
        d1 = d0 - tk
        # contact shadow thrown on the wall
        shd = (d1 > xo) & (d1 <= xo + 7)
        P.add(shd, -1.1)
        face = (d1 <= xo) & np.where(inside, d1 > xi, d1 > 0) & (d0 < 240)
        ft = 3.0 + 1.6 * Lm + 0.5 * Lc
        ft = ft * np.interp(th, [-60, -47, 24, 46, 75], [0.75, 1.0, 1.0, 0.7, 0.55])
        P.put(face, ft, 0, k=4)
        P.tint(face, Lc * 0.6, 1)
        # outer lip of the face (where it meets the wall) one step darker, inner lip lighter
        P.add(face & (d1 > xo - 1.5), -0.8)
        rim = inside & (d0 >= xi) & (d0 < xi + tk)
        rt = 4.2 + 2.2 * Lm + 0.9 * Lc
        rt = rt * np.interp(th, [-60, -47, 24, 46, 75], [0.75, 1.0, 1.0, 0.7, 0.55])
        P.put(rim, rt, 0, k=4)
        P.tint(rim, Lc * 0.8, 1)
        P.add(rim & (d0 < xi + 1.2), 1.0)
        P.add(rim & (d0 >= xi + tk - 1.5), -1.0)
        # specular kick where the rim passes the main strip
        P.add(rim & (np.abs(Y - ym) < 5), 2.0)
        P.add(rim & (np.abs(Y - yc) < 2), 1.5)
        for tb in range(-45, 70, 15):                        # plate joints across the face
            jy = cy + R * math.sin(math.radians(tb + 7.5))
            P.add(face & (np.abs(Y - jy) < 0.6), -1.0)
            P.add(face & (np.abs(Y - jy - 1) < 0.6), 0.6)
        # bolts along the face
        for tb in range(-50, 70, 10):
            by = cy + R * 0.93 * math.sin(math.radians(tb))
            bx = s0 + tk + A * 0.93 * math.cos(math.radians(tb))
            bm = P.rect(int(bx), int(by), int(bx) + 2, int(by) + 2)
            P.add(bm & face, -1.0)

    # ---- portholes (transparent) -------------------------------------------------
    def porthole(px_, py_, r):
        fr = r + max(5, r // 4 + 1)
        ang = np.arctan2(Y - py_, P.dx(px_))
        lit = np.cos(ang - math.radians(225))               # light from the top-left
        # cool light leaking around the opening (on the wall, under the frame)
        g = glow(P, px_, py_, fr + 18, fr + 18, 1.0)
        P.tint(None, np.clip(g * 0.5, 0, 0.5), 1)
        P.add(None, g * 0.5)
        P.add(P.ring(px_ + 2, py_ + 3, 0, fr + 2.5), -1.0)   # contact shadow, lower right
        ring_ = P.ring(px_, py_, r, fr)
        P.put(ring_, np.where(lit > 0.35, 6.0, np.where(lit > -0.4, 5.0, 4.0)), k=14)
        P.put(P.ring(px_, py_, fr - 1.3, fr), np.where(lit > 0, 8.0, 3.0))
        P.put(P.ring(px_, py_, r, r + 1.3), np.where(lit > 0, 3.0, 7.0))
        P.tint(ring_ & (lit < -0.2), 0.5, 1)
        nb = 8 if r > 16 else 6
        for i in range(nb):
            a_ = math.radians(i * 360.0 / nb + 22)
            bx, by = px_ + math.cos(a_) * (r + fr) / 2.0, py_ + math.sin(a_) * (r + fr) / 2.0
            bx, by = int(round(bx)), int(round(by))
            P.put(P.rect(bx, by, bx + 2, by + 2), 3.0)
            P.put(P.rect(bx, by, bx + 1, by + 1), 7.0)
        hole = P.ell(px_, py_, r, r)
        P.cut(hole)
        # wall thickness seen obliquely: a crescent of tunnel on the left side of the hole
        cres = hole & ~P.ell(px_ + max(3, r // 5), py_ + 1, r, r)
        P.put(cres, 2.0)
        P.put(cres & ~P.ell(px_ + 1.3, py_ + 0.4, r, r), 4.0)
        P.tint(cres, 0.6, 1)

    porthole(196, 104, 30)
    porthole(318, 80, 12)
    porthole(374, 124, 16)
    porthole(42, 150, 20)

    # ---- drifting motes: tiny points of light -----------------------------------
    for i in range(46):
        mx, my = rnd.uniform(0, W), rnd.uniform(6, 215) ** 1.0
        if not P.a[int(my), int(mx) % W]:
            continue
        t = rnd.choice((8, 9, 10, 10, 11))
        col = hexc((Z_CYA if rnd.random() < 0.3 else Z_VIO)[t])
        P.dot(mx, my, col, 255 if t > 9 else 190)
        if t == 11 and rnd.random() < 0.6:
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                P.dot(mx + ox, my + oy, col, 90)
    return P.render()


ZM_HULL = ["#0a0719", "#110c26", "#1a1436", "#231a46", "#2d2258", "#3a2c6c", "#4b3c86", "#6654a3"]
ZM_PINK = ["#0a0719", "#160a22", "#2c0e34", "#481244", "#5a1240", "#701a58", "#a8256a", "#e84a9a"]
ZM_CYAN = ["#0a0719", "#0b1428", "#0d283e", "#0e4052", "#0e4a5c", "#0f6070", "#12909a", "#2de0d0"]


def zerog_mid():
    W = W_MID
    P = Plate(W, H, [ZM_PINK, ZM_HULL, ZM_CYAN])
    X, Y = P.X, P.Y
    HU, PK, CY_ = 1, 0, 2
    rnd = random.Random(77)

    def S(m, base=3.0, **kw):
        kw.setdefault("hue", HU)
        kw.setdefault("rim_hue", CY_)
        kw.setdefault("rim", 1.0)
        return sil(P, m, base, **kw)

    # ---- loose tether cables first (they pass behind the cargo) ---------------------
    def cable(pts4, width=2, n=70):
        p0, p1, p2, p3 = pts4
        pts = []
        for i in range(n + 1):
            t = i / n
            a_ = (1 - t) ** 3
            b_ = 3 * (1 - t) ** 2 * t
            c_ = 3 * (1 - t) * t * t
            d = t ** 3
            pts.append((a_ * p0[0] + b_ * p1[0] + c_ * p2[0] + d * p3[0], a_ * p0[1] + b_ * p1[1] + c_ * p2[1] + d * p3[1]))
        m = P.lines(pts, width)
        P.put(m, 2.0, HU)
        P.put(m & ~_sh(m, 0, 1) & ~_sh(m, 1, 0), 4.0, HU)
        return pts[-1]

    ex, ey = cable([(618, -4), (668, 52), (566, 84), (604, 140)])
    S(P.ring(ex + 1, ey + 6, 3.0, 6.0), 3.0)
    P.cut(P.rect(int(ex) + 4, int(ey) + 2, int(ex) + 8, int(ey) + 5))
    ex, ey = cable([(22, -4), (-14, 44), (56, 92), (18, 150)])
    S(P.rect(int(ex) - 3, int(ey) - 1, int(ex) + 4, int(ey) + 9), 3.0)
    P.put(P.rect(int(ex) - 1, int(ey) + 3, int(ex) + 2, int(ey) + 5), 6.0, CY_)
    cable([(300, 196), (322, 170), (352, 214), (372, 188)], 1)

    # ---- crates, tumbling ---------------------------------------------------------------
    box3d(P, 88, 74, (46, 46, 46), 34, 26, 16, base=3.0, hue=HU, style="cargo")
    box3d(P, 146, 124, (21, 21, 21), -30, 28, -24, base=3.0, hue=HU, style="tech", acc_hue=PK)
    box3d(P, 440, 180, (36, 30, 30), 38, -24, -14, base=3.0, hue=HU, style="tech", acc_hue=CY_)
    box3d(P, 598, 226, (24, 24, 42), 22, 34, 40, base=3.0, hue=HU, style="strap")
    box3d(P, 372, 2, (38, 38, 38), -24, 30, 12, base=3.0, hue=HU, style="cargo")

    # ---- hoops: short rings seen at an angle, inner wall visible on one side -----------------
    def hoop(cx, cy, a, b, deg, tk, off, stripe_hue):
        u, w = rot_uv(P, cx, cy, deg)
        outer = (u / (a + tk)) ** 2 + (w / (b + tk)) ** 2 <= 1
        inner = (u / (a - tk)) ** 2 + (w / (b - tk)) ** 2 <= 1
        hole = ((u - off) / (a - tk)) ** 2 + (w / (b - tk)) ** 2 <= 1
        wall = inner & ~hole
        front = outer & ~inner
        P.put(wall, 2.0, HU)
        P.put(wall & ~_sh(wall, 0, 1) & ~inner, 2.0, HU)
        S(front, 3.0, rim=1.0)
        ang = np.degrees(np.arctan2(w / b, u / a)) % 360
        st = front & (((ang + 12) % 60) < 20)
        P.put(st, 4.0, stripe_hue)
        P.put(st & ~_sh(front, 1, 1), 5.0, stripe_hue)
        P.put(wall & (((ang + 12) % 60) < 20), 3.0, stripe_hue)

    hoop(244, 130, 21, 39, 16, 3.4, 5, PK)
    hoop(548, 60, 13, 25, -24, 2.8, -4, CY_)

    # ---- tools ----------------------------------------------------------------------------
    def wrench(cx, cy, deg, sc=1.0):
        u, w = rot_uv(P, cx, cy, deg)
        u, w = u / sc, w / sc
        m = (np.abs(w) < 2.3) & (np.abs(u) < 15)
        head = (np.hypot(u - 18, w) < 6.8) & ~((u > 17.5) & (np.abs(w) < 2.8))
        tail = (np.hypot(u + 18, w) < 5.6) & ~(np.hypot(u + 18, w) < 2.4)
        S(m | head | tail, 3.0)
        P.put(m & (np.abs(w) < 0.6) & (np.abs(u) < 9), 2.0, HU)

    def screwdriver(cx, cy, deg):
        u, w = rot_uv(P, cx, cy, deg)
        handle = (u > -17) & (u < -3) & (np.abs(w) < 3.6 - 1.0 * (np.abs(u + 10) > 5.5))
        S(handle, 3.0)
        P.put(handle & (np.abs(w) < 0.7) & (u > -15) & (u < -5), 2.0, HU)
        P.put(handle & (u > -5), 4.0, PK)
        shaft = (u >= -3) & (u < 15) & (np.abs(w) < 1.2)
        tip = (u >= 15) & (u < 18) & (np.abs(w) < 2.0)
        S(shaft | tip, 4.0, rim=0)

    def nut(cx, cy, r, deg):
        u, w = rot_uv(P, cx, cy, deg)
        hexm = (np.abs(w) < r * 0.87) & (np.abs(w * 0.5 + u * 0.87) < r * 0.87) & (np.abs(w * 0.5 - u * 0.87) < r * 0.87)
        S(hexm & ~(np.hypot(u, w) < r * 0.4), 3.0)

    def canister(cx, cy, deg):
        u, w = rot_uv(P, cx, cy, deg)
        body = (np.abs(u) < 12) & (np.abs(w) < 6.5)
        caps = (np.hypot(np.abs(u) - 12, w) < 6.5)
        m = body | caps
        S(m, 3.0)
        P.put(m & (w < -2.4) & (w > -4.6) & (np.abs(u) < 13), 4.0, HU)       # sheen
        P.put(m & (w > 2.5) & (np.abs(u) < 15), 2.0, HU)
        P.put(m & (np.abs(u - 5) < 1.8), 4.0, CY_)
        P.put(m & (np.abs(u + 9) < 0.8), 2.0, HU)
        neck = (u >= 17) & (u < 22) & (np.abs(w) < 2.2)
        S(neck | ((u >= 21) & (u < 23.5) & (np.abs(w) < 4.4)), 3.0, rim=0)

    def datapad(cx, cy, deg):
        u, w = rot_uv(P, cx, cy, deg)
        body = (np.abs(u) < 12) & (np.abs(w) < 8) & ~((np.abs(u) > 11) & (np.abs(w) > 7))
        S(body, 3.0)
        scr = (np.abs(u + 1.5) < 8) & (np.abs(w) < 5.5)
        P.put(scr, 3.0, CY_)
        P.put(scr & (np.abs(w + 2.5) < 0.7) & (u < 3), 5.0, CY_)
        P.put(scr & (np.abs(w - 0.5) < 0.7) & (u < 0), 5.0, CY_)
        P.put(scr & (np.abs(w - 3.2) < 0.7) & (u < 4), 4.0, CY_)
        P.put((np.abs(u - 9.5) < 1.0) & (np.abs(w) < 1.0), 5.0, PK)

    def plate(pts, rivets=2):
        m = P.poly(pts)
        S(m, 3.0)
        cxm = sum(p[0] for p in pts) / len(pts)
        cym = sum(p[1] for p in pts) / len(pts)
        for i in range(rivets):
            p = pts[i]
            qx, qy = cxm + (p[0] - cxm) * 0.6, cym + (p[1] - cym) * 0.6
            P.put(P.rect(int(qx), int(qy), int(qx) + 1, int(qy) + 1), 2.0, HU)

    wrench(326, 62, -34, 1.25)
    screwdriver(398, 102, 58)
    canister(494, 116, -22)
    datapad(196, 44, 24)
    for nx, ny, nr, nd in ((122, 158, 4.6, 10), (166, 92, 3.6, 40), (290, 98, 4.0, 25), (474, 220, 3.6, 5),
                           (22, 208, 4.4, 50), (522, 26, 3.2, 20)):
        nut(nx, ny, nr, nd)
    plate([(176, 204), (200, 196), (206, 211), (196, 215), (192, 222), (183, 219)])
    plate([(516, 150), (533, 155), (527, 169), (514, 163)])
    plate([(28, 22), (47, 29), (40, 38), (33, 41)], 1)
    plate([(346, 236), (382, 226), (386, 233), (372, 238), (366, 244), (352, 246)], 3)
    plate([(286, 30), (298, 26), (300, 36)], 0)
    # specks of drifting grit, a few pixels each
    for i in range(22):
        gx, gy = rnd.uniform(0, W), rnd.uniform(8, 250)
        t = rnd.choice((3.0, 4.0, 4.0, 5.0))
        P.put(P.rect(int(gx), int(gy), int(gx) + rnd.choice((1, 1, 2)), int(gy) + 1), t, HU)
    return P.render()


# ----------------------------------------------------------------------------
# BOSS - control core
# ----------------------------------------------------------------------------
B_CYAN = ["#05080f", "#06101c", "#081a26", "#0a2b3a", "#0c3a4a", "#0e4a5c", "#0f7480",
          "#12a3a6", "#2de0d0", "#8ff7ea", "#dcfffa"]
B_STEEL = ["#05080f", "#060b16", "#0a1322", "#0f1c30", "#152840", "#1b304a", "#284564",
           "#3c6283", "#5f8aa8", "#93b7cc", "#d0e6f0"]
B_PINK = ["#05080f", "#0b0818", "#170c33", "#231248", "#2a1657", "#472585", "#6f3fc0",
          "#a8256a", "#e84a9a", "#ff8cc0", "#ffd0e6"]
WX0, WX1, WY0, WY1 = 108, 372, 16, 160       # panoramic window (55% of width, upper 60%)


def boss_far():
    W = W_FAR
    P = Plate(W, H, [B_CYAN, B_STEEL, B_PINK])
    X, Y = P.X, P.Y
    CYN, STL, PNK = 0, 1, 2
    rnd = random.Random(5)
    PX = WX1                                   # pier origin (pier spans PX .. PX+216, across the seam)
    P.hazehue[:] = STL

    def SS(m, base, **kw):
        kw.setdefault("hue", STL)
        return sil(P, m, base, **kw)

    # ---- wall: dark, lit only by the screens and the window ---------------------------
    base = np.interp(Y, [0, 14, 90, 166, 200, 270], [1.8, 2.4, 2.8, 2.6, 1.8, 1.0]).astype(np.float32)
    gl_r = glow(P, PX + 52, 70, 70, 70, 1.3)          # right-hand screens
    gl_l = glow(P, PX + 164, 70, 70, 70, 1.3)
    scr_glow = gl_r + gl_l
    wall = base + scr_glow
    P.haze[:] = wall
    P.put(np.ones((H, W), bool), wall, STL, k=2.4)
    P.tint(None, np.clip(scr_glow * 0.45, 0, 0.7), CYN)

    # lower wall: wide plates, a kick strip, vents
    for sx_ in (0, 62, 150, 240, 330, 418):
        P.add(P.rect(sx_, 204, sx_ + 1, H), -0.7)
        P.add(P.rect(sx_ + 1, 204, sx_ + 2, H), 0.35)
    for sy_ in (204, 240):
        P.add(P.rect(0, sy_, W, sy_ + 1), -0.8)
        P.add(P.rect(0, sy_ + 1, W, sy_ + 2), 0.4)
    for vx in (78, 376):
        for i in range(4):
            P.add(P.rect(vx, 214 + i * 4, vx + 26, 216 + i * 4), -0.7)

    # ---- pier: central pilaster with a light slit -----------------------------------------
    pil = P.rect(PX + 96, 6, PX + 120, H)
    u = P.u(PX + 96, PX + 120)
    P.put(pil, np.where(u < 0.1, 5.0, np.where(u < 0.36, 4.0, np.where(u < 0.7, 3.0, 2.0))), STL)
    P.put(P.rect(PX + 107, 26, PX + 109, 150), 2.0, STL)
    P.put(P.rect(PX + 107, 26, PX + 109, 150) & ((Y // 6) % 3 != 2), 7.0, CYN)
    for by in (16, 156, 200):
        SS(P.rect(PX + 93, by, PX + 123, by + 6), 4.0)

    # ---- window opening + frame ----------------------------------------------------
    ch = 16

    def oct_(x0, y0, x1, y1, c_):
        return P.poly([(x0 + c_, y0), (x1 - c_, y0), (x1, y0 + c_), (x1, y1 - c_), (x1 - c_, y1), (x0 + c_, y1), (x0, y1 - c_), (x0, y0 + c_)])
    hole = oct_(WX0, WY0, WX1 - 1, WY1 - 1, ch)
    outer = oct_(WX0 - 11, WY0 - 11, WX1 + 10, WY1 + 10, ch + 5)
    mid_ = oct_(WX0 - 6, WY0 - 6, WX1 + 5, WY1 + 5, ch + 2)
    # shadow of the frame on the wall
    P.add(_sh(outer, 2, 3) & ~outer, -1.0)
    SS(outer & ~hole, 5.0, hi=2.0, sh=2.0)                  # outer flange
    SS(mid_ & ~hole, 4.0, hi=1.0, sh=1.0)                   # inner step
    inner_lip = oct_(WX0 - 2, WY0 - 2, WX1 + 1, WY1 + 1, ch + 1) & ~hole
    P.put(inner_lip, 2.0, STL)
    # segment joints and bolts on the flange
    for jx in (WX0 + 60, WX0 + 132, WX1 - 132, WX1 - 60):
        P.put(P.rect(jx, WY0 - 11, jx + 1, WY0 - 6), 3.0, STL)
        P.put(P.rect(jx, WY1 + 5, jx + 1, WY1 + 10), 3.0, STL)
    for bx in range(WX0 + 24, WX1 - 16, 36):
        for by in (WY0 - 10, WY1 + 6):
            P.put(P.rect(bx, by, bx + 2, by + 2), 7.0, STL)
            P.put(P.rect(bx + 1, by + 1, bx + 2, by + 2), 3.0, STL)
    for by in range(WY0 + 28, WY1 - 16, 36):
        for bx in (WX0 - 10, WX1 + 6):
            P.put(P.rect(bx, by, bx + 2, by + 2), 7.0, STL)
            P.put(P.rect(bx + 1, by + 1, bx + 2, by + 2), 3.0, STL)
    P.cut(hole)
    # mullions and a high transom
    for mx in (WX0 + 86, WX1 - 90):
        P.put(P.rect(mx, WY0, mx + 4, WY1) & hole, 3.0, STL)
        P.put(P.rect(mx, WY0, mx + 1, WY1) & hole, 5.0, STL)
        P.put(P.rect(mx + 3, WY0, mx + 4, WY1) & hole, 2.0, STL)
    P.put(P.rect(WX0, WY0 + 30, WX1, WY0 + 33) & hole, 3.0, STL)
    P.put(P.rect(WX0, WY0 + 30, WX1, WY0 + 31) & hole, 5.0, STL)
    P.put(P.rect(WX0, WY0 + 32, WX1, WY0 + 33) & hole, 2.0, STL)
    for mx in (WX0 + 86, WX1 - 90):                             # junction plates
        SS(P.rect(mx - 2, WY0 + 28, mx + 6, WY0 + 35) & hole, 4.0)
    glass = hole & ~P.a
    # glass: faint shade under the top of the frame and two glints (low alpha - space stays visible)
    shade = np.clip(1 - (Y - WY0) / 20.0, 0, 1) * 70
    P.over[glass] = np.dstack([np.full_like(Y, 5), np.full_like(Y, 8), np.full_like(Y, 15), shade])[glass]
    dg = (X + Y * 0.9)
    for g0, gw_, ga in ((300, 9, 22), (316, 3, 16), (458, 14, 16)):
        gl = glass & (dg > g0) & (dg < g0 + gw_) & (Y > WY0 + 34)
        P.over[gl] = (169, 197, 240, ga)

    # ---- sill + long console under the window --------------------------------------
    SS(P.rect(WX0 - 16, WY1 + 10, WX1 + 16, WY1 + 14), 5.0, hi=0)
    P.put(P.rect(WX0 - 16, WY1 + 10, WX1 + 16, WY1 + 11), 8.0, CYN)       # planet-light on the sill
    desk = P.trap(WX0 - 8, WX1 + 8, WY1 + 14, WX0 + 6, WX1 - 6, WY1 + 34)
    P.put(desk, 3.0, STL)
    P.put(P.rect(WX0 - 8, WY1 + 14, WX1 + 8, WY1 + 15) & desk, 2.0, STL)
    P.put(P.rect(WX0 - 8, WY1 + 15, WX1 + 8, WY1 + 16) & desk, 5.0, STL)
    SS(P.rect(WX0 + 6, WY1 + 34, WX1 - 6, WY1 + 40), 2.0, hi=0)
    xk = WX0 + 14
    blocks = [(22, "bar"), (12, "keys"), (30, "scr"), (16, "keys"), (26, "bar"), (12, "keys"), (34, "scr"), (18, "keys"), (24, "bar"), (14, "keys")]
    for wdt, kind in blocks:
        if kind == "scr":
            P.put(P.rect(xk, WY1 + 19, xk + wdt, WY1 + 30), 2.0, CYN)
            P.put(P.rect(xk + 2, WY1 + 22, xk + wdt - 4, WY1 + 23), 5.0, CYN)
            P.put(P.rect(xk + 2, WY1 + 25, xk + wdt // 2, WY1 + 26), 4.0, CYN)
            P.put(P.rect(xk + wdt - 6, WY1 + 25, xk + wdt - 3, WY1 + 28), 6.0, CYN)
        elif kind == "bar":
            n = 4
            lit = rnd.choice((1, 2, 3, 3))
            for i in range(n):
                P.put(P.rect(xk + i * (wdt // n), WY1 + 20, xk + i * (wdt // n) + wdt // n - 1, WY1 + 24), 6.0 if i < lit else 3.0, CYN)
            P.put(P.rect(xk, WY1 + 27, xk + wdt - 2, WY1 + 28), 2.0, STL)
        else:
            for i in range(0, wdt - 2, 4):
                for j in range(3):
                    P.put(P.rect(xk + i, WY1 + 20 + j * 4, xk + i + 3, WY1 + 22 + j * 4), 2.0 if (i + j) % 3 else 5.0, STL)
        xk += wdt + 5
    # console legs
    for lx in (WX0 + 20, WX1 - 32):
        SS(P.trap(lx, lx + 12, WY1 + 40, lx + 2, lx + 10, WY1 + 60), 2.0, hi=0)

    # ---- header beam with a light strip ----------------------------------------------
    P.put(P.rect(0, 0, W, 4), 1.0, STL)
    P.put(P.rect(0, 4, W, 5), 3.0, STL)
    for i in range(0, W, 60):
        P.put(P.rect(i + 8, 1, i + 44, 2), 6.0, CYN)

    # ---- monitors ------------------------------------------------------------------------
    def bezel(x0, y0, x1, y1, hue=CYN, bg=2.0):
        x0 += PX
        x1 += PX
        P.add(_sh(P.rect(x0 - 3, y0 - 3, x1 + 3, y1 + 3), 2, 2), -0.8)        # drop shadow
        SS(P.rect(x0 - 3, y0 - 3, x1 + 3, y1 + 3), 5.0, hi=2.0, sh=2.0)
        P.put(P.rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1), 1.0, STL)
        scr = P.rect(x0, y0, x1, y1)
        P.put(scr, bg, hue)
        P.put(scr & (Y % 3 == 0), bg + 1.0, hue)                  # scanlines
        P.put(P.rect(x1 - 3, y1 + 1, x1 - 1, y1 + 2), 8.0, CYN)    # power LED
        return x0, y0

    def fbar(x, y, w_, h_, n, lit, hue=CYN, on=6.0, off=4.0):
        """fraction bar: n equal cells, `lit` of them filled"""
        cw = w_ // n
        for i in range(n):
            cell = P.rect(x + i * cw, y, x + i * cw + cw - 1, y + h_)
            if i < lit:
                P.put(cell, on, hue)
                P.put(P.rect(x + i * cw, y, x + i * cw + cw - 1, y + 1), on + 1, hue)
            else:
                P.put(cell, off, hue)
                P.put(P.rect(x + i * cw + 1, y + 1, x + i * cw + cw - 2, y + h_ - 1), off - 2.0, hue)

    def pie(cx, cy_, r, quarters, hue=CYN, on=6.0):
        """disc cut into quarters, clockwise from the top (odd diameter, centre on a pixel);
        the first `quarters` are lit, the rest are only an outline.
        3 -> the missing quarter is the upper left."""
        ddx = P.dx(cx)
        ddy = Y - cy_
        d = np.hypot(ddx, ddy)
        q = np.where((ddx > 0) & (ddy < 0), 0, np.where((ddx > 0) & (ddy > 0), 1, np.where((ddx < 0) & (ddy > 0), 2, 3)))
        disc_ = d <= r + 0.35
        cross = (np.abs(ddx) < 0.5) | (np.abs(ddy) < 0.5)
        litm = disc_ & (q < quarters) & ~cross
        P.put(litm, on, hue)
        P.put(litm & (d > r - 1.0) & (ddy < 0) & (ddx > -r * 0.2), on + 1, hue)
        rest = disc_ & ~litm & ~cross
        P.put(rest, 2.0, hue)
        P.put(rest & (d > r - 0.9), on - 2.0, hue)
        P.put(disc_ & cross, 2.0, hue)

    def nline(x, y, w_, n, mark, hue=CYN):
        """number line with n intervals, filled up to tick `mark`"""
        P.put(P.rect(x, y, x + w_ + 1, y + 1), 5.0, hue)
        for i in range(n + 1):
            tx = x + (w_ * i) // n
            tall = 4 if i in (0, n) else 2
            P.put(P.rect(tx, y - tall, tx + 1, y + tall + 1), 5.0, hue)
        mx_ = x + (w_ * mark) // n
        P.put(P.rect(x, y - 1, mx_ + 1, y + 2), 7.0, hue)
        P.put(P.poly([(mx_ - 3, y - 9), (mx_ + 3, y - 9), (mx_, y - 5)]), 8.0, hue)

    # right of the window --------------------------------------------------------------
    # main screen: the fuel cell with its quarter missing, and the bars that prove it
    x, y = bezel(16, 22, 88, 84)
    pie(x + 26, y + 34, 20, 3, on=6.0)
    # ... the missing quarter, drifting away up-left, drawn in the Phantom's pink
    ddx = P.dx(x + 21)
    ddy = Y - (y + 29)
    d = np.hypot(ddx, ddy)
    qm = (d <= 20.35) & (ddx < 0) & (ddy < 0)
    P.put(qm, 3.0, PNK)
    P.put(qm & ((d > 19.0) | (ddx > -1.5) | (ddy > -1.5)), 8.0, PNK)
    P.put(qm & ((X + Y) % 3 == 0) & (d < 19.0) & (ddx < -1.5) & (ddy < -1.5), 6.0, PNK)
    fbar(x + 50, y + 6, 20, 6, 2, 1)
    fbar(x + 50, y + 17, 20, 6, 4, 3)
    fbar(x + 50, y + 28, 20, 6, 5, 2)
    nline(x + 50, y + 50, 18, 3, 2)
    # strip: six eighths over three quarters
    x, y = bezel(16, 94, 88, 118)
    fbar(x + 4, y + 4, 64, 6, 8, 6)
    fbar(x + 4, y + 14, 64, 6, 4, 3)
    # left of the window ---------------------------------------------------------------
    # glitched pink screen with the Phantom's emblem
    x, y = bezel(128, 22, 162, 56, hue=PNK, bg=3.0)
    pie(x + 17, y + 17, 11, 3, hue=PNK, on=8.0)
    for gy, g0 in ((5, 0), (14, 5), (25, 2), (29, 7)):
        strip = P.rect(x, y + gy, x + 34, y + gy + 2)
        P.put(strip & (((X + g0 * 3) % 11) < 5), 7.0, PNK)
    # fuel columns at quarter heights
    x, y = bezel(170, 22, 200, 56)
    for i, q_ in enumerate((1, 3, 2, 4)):
        hx = x + 3 + i * 7
        P.put(P.rect(hx, y + 5, hx + 5, y + 29), 4.0, CYN)
        P.put(P.rect(hx + 1, y + 6, hx + 4, y + 29), 2.0, CYN)
        P.put(P.rect(hx, y + 29 - q_ * 6, hx + 5, y + 29), 6.0, CYN)
        P.put(P.rect(hx, y + 29 - q_ * 6, hx + 5, y + 30 - q_ * 6), 7.0, CYN)
    # number line, marker at three quarters
    x, y = bezel(128, 66, 200, 88)
    nline(x + 6, y + 14, 60, 4, 3)
    # four pies, one to four quarters
    x, y = bezel(128, 98, 200, 118)
    for i in range(4):
        pie(x + 10 + i * 17, y + 10, 7, i + 1, on=6.0)

    # console desks under both monitor groups
    for (d0, d1) in ((10, 94), (122, 206)):
        dk = P.trap(PX + d0, PX + d1, 128, PX + d0 + 6, PX + d1 - 6, 146)
        P.put(dk, 3.0, STL)
        P.put(P.rect(PX + d0, 128, PX + d1, 129), 5.0, STL)
        SS(P.rect(PX + d0 + 6, 146, PX + d1 - 6, 154), 2.0, hi=0)
        for i in range(0, d1 - d0 - 24, 5):
            for j in range(3):
                if (i // 5 + j * 3 + d0) % 7 in (2, 3):
                    continue
                hot = (i // 5 * 5 + j * 3 + d0) % 11 == 0
                P.put(P.rect(PX + d0 + 10 + i + j, 132 + j * 4, PX + d0 + 13 + i + j, 134 + j * 4), 6.0 if hot else 2.0, CYN if hot else STL)
        for lx in (PX + d0 + 12, PX + d1 - 22):
            SS(P.rect(lx, 154, lx + 10, H), 2.0, hi=1.0, sh=1.0)

    # ---- light spilling in through the window onto the lower wall ---------------------------
    y0, y1 = WY1 + 40, 262
    sh_ = P.trap(WX0 + 10, WX1 - 10, y0, WX0 - 30, WX1 + 30, y1)
    fall = np.clip(1 - (Y - y0) / float(y1 - y0), 0, 1) ** 1.3
    # the mullions throw two soft shadows through the wash
    mul = np.ones_like(fall)
    for mx in (WX0 + 88, WX1 - 88):
        mul *= np.clip(np.abs(P.dx(mx + (mx - 240) * (Y - y0) / 300.0)) / 7.0, 0.25, 1.0)
    P.add(sh_, fall * mul * 1.0)
    P.tint(sh_, fall * mul * 0.6, CYN)
    # planet light catching the inner lip of the frame
    lipc = oct_(WX0 - 1, WY0 - 1, WX1, WY1, ch) & ~hole
    P.put(lipc & ((X > 240) | (Y > 88)), 5.0, CYN)

    # small points of light
    for lx, ly, hue_, t in ((PX + 6, 30, PNK, 8), (PX + 6, 36, CYN, 8), (PX + 210, 100, CYN, 8), (PX + 210, 106, CYN, 6),
                           (PX + 100, 176, PNK, 7), (WX0 - 20, 190, CYN, 7), (WX1 + 30, 250, CYN, 6), (WX0 + 40, 226, CYN, 6)):
        P.dot(lx, ly, hexc([B_CYAN, B_STEEL, B_PINK][hue_][t]))
    return P.render()


BM_STEEL = ["#05080f", "#080e1a", "#0b1422", "#122034", "#1b304a", "#284564", "#3c6283"]
BM_CYAN = ["#05080f", "#07141e", "#0a2230", "#0c3646", "#0e4a5c", "#0f7480", "#12a3a6"]


def boss_mid():
    W = W_MID
    P = Plate(W, H, [BM_CYAN, BM_STEEL])
    X, Y = P.X, P.Y
    CYN, STL = 0, 1

    def S(m, base=2.0, **kw):
        kw.setdefault("hue", STL)
        kw.setdefault("rim_hue", CYN)
        return sil(P, m, base, **kw)

    cols = (10, 470)        # a pair of columns close together across the seam; the wide bay is the arena
    hw = 14

    # ---- cable bundles slung across the wide bay (kept high) ------------------------------
    def swag(x0, x1, y0, sag, width=2, tone=2.0, n=90):
        pts = [(x0 + (x1 - x0) * i / n, y0 + sag * (1 - (2.0 * i / n - 1) ** 2)) for i in range(n + 1)]
        m = P.lines(pts, width)
        P.put(m, tone, STL)
        P.put(m & ~_sh(m, 0, 1), tone + 1, STL)
        if width > 2:
            P.put(m & ~_sh(m, 0, -1), tone + 1, CYN)
        return pts

    xa, xb = cols[0] + hw, cols[1] - hw
    swag(xa, xb, 12, 30, 2)
    pts = swag(xa, xb, 18, 36, 4)
    swag(xa, xb, 30, 20, 1, 1.0)
    for f in (0.1, 0.27, 0.5, 0.73, 0.9):                       # clamps
        px_, py_ = pts[int(f * 90)]
        S(P.rect(int(px_) - 2, int(py_) - 3, int(px_) + 3, int(py_) + 5), 2.0, rim=1.0)
    # drop cables near the columns, with connectors
    for (dx_, y1, f) in ((cols[0] + 44, 132, 0.1), (cols[1] - 40, 96, 0.9)):
        px_, py_ = pts[int(f * 90)]
        pp = [(px_, py_ + 4), (px_ + 3, py_ + 30), (dx_ - 4, y1 - 30), (dx_, y1)]
        cur = []
        for i in range(41):
            t = i / 40.0
            cur.append(tuple(((1 - t) ** 3) * pp[0][k] + 3 * ((1 - t) ** 2) * t * pp[1][k] + 3 * (1 - t) * t * t * pp[2][k] + (t ** 3) * pp[3][k] for k in (0, 1)))
        m = P.lines(cur, 2)
        P.put(m, 2.0, STL)
        P.put(m & ~_sh(m, 1, 0), 3.0, STL)
        S(P.rect(int(dx_) - 3, y1, int(dx_) + 4, y1 + 9), 2.0, rim=1.0)
        P.put(P.rect(int(dx_) - 1, y1 + 9, int(dx_) + 2, y1 + 12), 1.0, STL)
        P.put(P.rect(int(dx_) - 1, y1 + 3, int(dx_) + 1, y1 + 5), 6.0, CYN)
    # short swags in the narrow bay
    xa2, xb2 = cols[1] + hw, cols[0] + W - hw
    swag(xa2, xb2, 12, 14, 2)
    swag(xa2, xb2, 20, 20, 3)

    # ---- columns -----------------------------------------------------------------------------
    def shaft(x0, x1, y0, y1, side):
        m = P.rect(x0, y0, x1, y1)
        u = P.u(x0, x1)
        t = np.where(u < 0.08, 4.0, np.where(u < 0.3, 3.0, np.where(u < 0.66, 2.0, 1.0)))
        P.put(m, t, STL)
        # rim light from the window on the side that faces the arena
        if side > 0:
            P.put(P.rect(x1 - 1, y0, x1, y1), 4.0, CYN)
            P.put(P.rect(x1 - 2, y0, x1 - 1, y1), 2.0, CYN)
        else:
            P.put(P.rect(x0, y0, x0 + 1, y1), 5.0, CYN)
            P.put(P.rect(x0 + 1, y0, x0 + 2, y1), 3.0, CYN)

    for cx, side in ((cols[0], 1), (cols[1], -1)):
        shaft(cx - hw, cx + hw, 0, H, side)
        # recessed channel with a dim light slit
        P.put(P.rect(cx - 3, 40, cx + 3, 204), 1.0, STL)
        P.put(P.rect(cx - 3, 40, cx - 2, 204), 2.0, STL)
        P.put(P.rect(cx - 1, 46, cx + 1, 198) & ((Y // 8) % 4 != 3), 4.0, CYN)
        # collars
        for (y0, y1, ex) in ((0, 10, 8), (10, 18, 5), (18, 24, 2), (H - 10, H, 8), (H - 20, H - 10, 5), (H - 26, H - 20, 2),
                             (112, 122, 3)):
            shaft(cx - hw - ex, cx + hw + ex, y0, y1, side)
            P.put(P.rect(cx - hw - ex, y0, cx + hw + ex, y0 + 1), 4.0, STL)
            P.put(P.rect(cx - hw - ex, y1 - 1, cx + hw + ex, y1), 1.0, STL)
        # diagonal brace up into the ceiling on the arena side
        bx0 = cx + side * (hw + 2)
        br = P.poly([(bx0, 24), (bx0 + side * 34, 0), (bx0 + side * 46, 0), (bx0, 44)])
        S(br, 2.0, rim=1.0)
        P.put(P.poly([(bx0 + side * 6, 22), (bx0 + side * 26, 6), (bx0 + side * 6, 32)]) & br, 1.0, STL)
    # cross-bracing between the close pair
    x0, x1 = cols[1] + hw + 8, cols[0] + W - hw - 8
    for (ya, yb) in ((40, 104), (130, 200)):
        for (p, q) in (((x0, ya), (x1, yb)), ((x1, ya), (x0, yb))):
            m = P.lines([p, q], 3) & ~P.a
            P.put(m, 2.0, STL)
            P.put(m & ~_sh(m, 0, 1), 3.0, STL)
        S(P.rect(x0 - 8, ya - 3, x1 + 8, ya + 1) & ~P.a, 2.0, rim=1.0)
        S(P.rect(x0 - 8, yb, x1 + 8, yb + 4) & ~P.a, 2.0, rim=1.0)

    # ---- railings: either side of the arena, the middle left open ----------------------------------
    def rail(x0, x1, y0=206):
        n = max(1, round((x1 - x0) / 26.0))
        for i in range(n + 1):
            x = int(round(x0 + (x1 - x0) * i / n))
            S(P.rect(x, y0, x + 3, H), 2.0, rim=0)
        S(P.rect(x0 - 3, y0 - 3, x1 + 6, y0), 3.0, rim=1.0)
        P.put(P.rect(x0, y0 + 13, x1 + 3, y0 + 15), 2.0, STL)
        P.put(P.rect(x0, y0 + 13, x1 + 3, y0 + 14), 3.0, STL)
        P.put(P.rect(x0, y0 + 30, x1 + 3, y0 + 31), 2.0, STL)

    rail(cols[0] + hw + 10, cols[0] + hw + 10 + 104)
    rail(cols[1] - hw - 13 - 104, cols[1] - hw - 13)
    return P.render()


# ----------------------------------------------------------------------------
# previews
# ----------------------------------------------------------------------------
def tile_x(img, w, off=0):
    out = Image.new("RGBA", (w, img.height))
    x = -(off % img.width)
    while x < w:
        out.alpha_composite(img, (x, 0)) if x >= 0 else out.alpha_composite(img.crop((-x, 0, img.width, img.height)), (0, 0))
        x += img.width
    return out


def backdrop(w=480, h=270):
    """space layers if the other artist's files exist, else a flat stand-in (preview only)"""
    bg = Image.new("RGBA", (w, h), hexc("#080a14"))
    p = os.path.join(pix.ASSETS, "bg", "stars.png")
    if os.path.exists(p):
        bg.alpha_composite(tile_x(Image.open(p).convert("RGBA"), w).crop((0, 0, w, h)))
    else:
        r = random.Random(4)
        for i in range(160):
            c = r.choice(["#3f5fae", "#6b8fd6", "#a9c5f0", "#e6f1ff", "#47566f", "#47566f"])
            bg.putpixel((r.randrange(w), r.randrange(h)), hexc(c))
    p = os.path.join(pix.ASSETS, "bg", "nebula.png")
    if os.path.exists(p):
        bg.alpha_composite(tile_x(Image.open(p).convert("RGBA"), w).crop((0, 0, w, h)))
    p = os.path.join(pix.ASSETS, "bg", "planet.png")
    if os.path.exists(p):
        bg.alpha_composite(Image.open(p).convert("RGBA"), (150, 10))
    else:
        pl = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(pl)
        d.ellipse((160, 20, 360, 220), fill=hexc("#0e4a5c"))
        d.ellipse((160, 20, 340, 200), fill=hexc("#0f7480"))
        d.ellipse((170, 26, 300, 150), fill=hexc("#12a3a6"))
        bg.alpha_composite(pl)
    return bg


def stack(area, far, mid, far_off=0, mid_off=0, room=0):
    img = backdrop()
    img.alpha_composite(tile_x(far, 480, far_off))
    img.alpha_composite(tile_x(mid, 480, mid_off))
    til = Image.open(os.path.join(pix.ASSETS, "tiles", f"tiles_{area}.png")).convert("RGBA")

    def tile(i):
        return til.crop(((i % 16) * 16, (i // 16) * 16, (i % 16) * 16 + 16, (i // 16) * 16 + 16))
    cols, rows = 30, 17
    g = [[0] * cols for _ in range(rows)]
    fy = 14
    for x in range(cols):
        for y in range(fy, rows):
            g[y][x] = 1
    if room == 0:
        for x in range(21, 27):
            for y in range(10, 12):
                g[y][x] = 1
        for x in range(11, 13):
            g[fy][x] = 0
    else:
        for x in range(0, 4):
            for y in range(9, fy):
                g[y][x] = 1

    def sol(x, y):
        if x < 0 or x >= cols or y < 0 or y >= rows:
            return 1
        return g[y][x]
    for y in range(rows):
        for x in range(cols):
            if not g[y][x]:
                continue
            m = sol(x, y - 1) + sol(x + 1, y) * 2 + sol(x, y + 1) * 4 + sol(x - 1, y) * 8
            t = m
            if m == 15:
                deep = all(sol(x + a, y + b) for a in (-1, 0, 1) for b in (-1, 0, 1))
                t = 16 if deep else 15
            if m == 14 and x % 7 == 3:
                t = 20
            img.alpha_composite(tile(t), (x * 16, y * 16 - 2))
    plats = [(6, 9, 4), (14, 6, 3)] if room == 0 else [(8, 10, 4), (16, 7, 5), (24, 10, 3)]
    for (px_, py_, n) in plats:
        for i in range(n):
            img.alpha_composite(tile(32 if i == 0 else 34 if i == n - 1 else 33), ((px_ + i) * 16, py_ * 16 - 2))
    p = os.path.join(pix.ASSETS, "sprites", "jake.png")
    if os.path.exists(p):
        sh = Image.open(p).convert("RGBA")
        jk = sh.crop((0, 0, 32, 32))
        jr = sh.crop((64, 32, 96, 64))
        img.alpha_composite(jk, (4 * 16, fy * 16 - 2 - 31))
        img.alpha_composite(jr, (15 * 16, 6 * 16 - 2 - 31))
        img.alpha_composite(jk, (23 * 16, (10 if room == 0 else 10) * 16 - 2 - 31))
        img.alpha_composite(jk, (7 * 16, (9 if room == 0 else 10) * 16 - 2 - 31) if room == 0 else (9 * 16, 10 * 16 - 2 - 31))
    return img


def seam(img):
    out = Image.new("RGBA", (img.width * 2, img.height))
    out.alpha_composite(img, (0, 0))
    out.alpha_composite(img, (img.width, 0))
    return out


def previews(area, far, mid):
    pix.preview(far, f"bgb_{area}_far.png", scale=3, bg="#080a14")
    pix.preview(mid, f"bgb_{area}_mid.png", scale=2, bg="#2b3f7e")
    pix.preview(seam(far), f"bgb_{area}_far_seam.png", scale=2, bg="#080a14")
    pix.preview(seam(mid), f"bgb_{area}_mid_seam.png", scale=1, bg="#2b3f7e")
    pix.preview(stack(area, far, mid), f"bgb_{area}_stack.png", scale=3, bg="#080a14")
    pix.preview(stack(area, far, mid, 173, 391, room=1), f"bgb_{area}_stack2.png", scale=3, bg="#080a14")


AREAS = {
    "reactor": (reactor_far, reactor_mid),
    "zerog": (zerog_far, zerog_mid),
    "boss": (boss_far, boss_mid),
}


def main(argv):
    want = [a for a in argv if a in AREAS] or list(AREAS)
    for area in want:
        ffar, fmid = AREAS[area]
        far, mid = ffar(), fmid()
        assert far.size == (W_FAR, H) and mid.size == (W_MID, H)
        pix.save(far, f"bg/{area}_far.png")
        pix.save(mid, f"bg/{area}_mid.png")
        previews(area, far, mid)
    images = {}
    for area in AREAS:
        images[f"{area}_far"] = {"file": f"bg/{area}_far.png"}
        images[f"{area}_mid"] = {"file": f"bg/{area}_mid.png"}
    pix.manifest("bg_b", {"images": images})


if __name__ == "__main__":
    main(sys.argv[1:])
