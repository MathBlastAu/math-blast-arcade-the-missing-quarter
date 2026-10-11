"""
tiles.py - modular Kepler Station tileset (16x16 tiles, 16 columns).

Index map (same for every skin):
  0..15   solid hull, auto-tile by neighbour mask (N=1, E=2, S=4, W=8; bit set = solid neighbour)
  16,17   deep interior (far from any edge)        18,19  interior variants (vent, bolted plate)
  20      top surface with floor lamp              21     top surface with hazard stripes
  22,23   top surface variants (grate, seam)
  32..35  one-way platform: left, mid, right, single     36 strut under platform
  48..50  back wall plain A/B/C      51 pipe horizontal   52 pipe vertical   53 pipe elbow
  54      back wall vent             55 girder cross-brace 56 column          57 column cap
  58..65  window frame: TL, T, TR, L, R, BL, B, BR  (centre left empty so space shows through)
  66      back wall hazard strip     67 back wall light   68 back wall grate  69 hanging cables
  70      back wall dark (shadowed)  71 back wall seam vertical
Skins: dock, bridge, reactor, zerog, boss  -> assets/tiles/tiles_<skin>.png
"""
import random
from pix import *

TS = 16
COLS = 16
ROWS = 5

SKINS = {
    # hull ramp (8 steps dark->light), back-wall ramp (4), accent ramp, lamp colour
    "dock":    dict(hull=RAMPS["steel"], wall=["#0d1126", "#141a3a", "#1b2547", "#243258"], acc="cyan", lamp="cyan", stripe="gold"),
    "bridge":  dict(hull=["#141a2e", "#1e2a48", "#2c3c62", "#3f527f", "#5a709e", "#8298c0", "#b3c4e0", "#e2ecfa"],
                    wall=["#0b0f24", "#111836", "#18224a", "#20305e"], acc="cyan", lamp="cyan", stripe="gold"),
    "reactor": dict(hull=["#1a1218", "#2a1c24", "#3e2a32", "#573c40", "#775650", "#9c7a68", "#c7a68a", "#efd9b8"],
                    wall=["#120a12", "#1c0f18", "#2a1620", "#3a1e26"], acc="orange", lamp="orange", stripe="gold"),
    "zerog":   dict(hull=["#150f2b", "#211a42", "#32285e", "#483a80", "#6654a3", "#8f7fc6", "#bdb0e4", "#e8e2fa"],
                    wall=["#0c0820", "#140e30", "#1d1544", "#281d5a"], acc="cyan", lamp="purple", stripe="pink"),
    "boss":    dict(hull=["#0b1422", "#122034", "#1b304a", "#284564", "#3c6283", "#5f8aa8", "#93b7cc", "#d0e6f0"],
                    wall=["#060b16", "#0a1322", "#0f1c30", "#152840"], acc="cyan", lamp="cyan", stripe="red"),
}


def hull_interior(img, ox, oy, H, variant=0, rnd=None):
    """Interior plating: 16x16 with seams that line up into 32x32 panels."""
    rect(img, ox, oy, TS, TS, H[2])
    # seams on left + top, highlight just inside them
    vline(img, ox, oy, oy + 15, H[1]); hline(img, ox, ox + 15, oy, H[1])
    vline(img, ox + 1, oy + 1, oy + 15, H[3]); hline(img, ox + 1, ox + 15, oy + 1, H[3])
    px(img, ox + 1, oy + 1, H[3])
    # rivets
    for (rx, ry) in ((3, 3), (13, 3), (3, 13), (13, 13)):
        px(img, ox + rx, oy + ry, H[4]); px(img, ox + rx + 1, oy + ry + 1, H[1])
    if variant == 1:      # vent slats
        for i in range(4):
            hline(img, ox + 5, ox + 11, oy + 5 + i * 2, H[0])
            hline(img, ox + 5, ox + 11, oy + 6 + i * 2, H[3])
    elif variant == 2:    # bolted access plate
        rect(img, ox + 5, oy + 5, 7, 7, H[3])
        hline(img, ox + 5, ox + 11, oy + 5, H[4]); vline(img, ox + 5, oy + 5, oy + 11, H[4])
        hline(img, ox + 5, ox + 11, oy + 11, H[1]); vline(img, ox + 11, oy + 5, oy + 11, H[1])
        px(img, ox + 8, oy + 8, H[1])


def hull_deep(img, ox, oy, H, variant=0):
    rect(img, ox, oy, TS, TS, H[0])
    if variant == 0:
        hline(img, ox, ox + 15, oy, mix(hexc_(H[0]), hexc_(H[1]), 0.6))
        vline(img, ox, oy, oy + 15, mix(hexc_(H[0]), hexc_(H[1]), 0.6))
    else:
        for i in range(0, 16, 4):
            px(img, ox + (i + 2) % 16, oy + i + 1, H[1])


def hexc_(c):
    return c if isinstance(c, tuple) else hexc(c)


def edge_top(img, ox, oy, H, A, kind="plain"):
    """Walkable surface: bright lip, plating, shadow line."""
    hline(img, ox, ox + 15, oy, H[7])
    hline(img, ox, ox + 15, oy + 1, H[6])
    hline(img, ox, ox + 15, oy + 2, H[5])
    hline(img, ox, ox + 15, oy + 3, H[3])
    hline(img, ox, ox + 15, oy + 4, H[0])
    hline(img, ox, ox + 15, oy + 5, H[1])
    # plate joints
    px(img, ox, oy + 1, H[4]); px(img, ox, oy + 2, H[3]); px(img, ox + 8, oy + 2, H[4])
    if kind == "lamp":
        rect(img, ox + 5, oy + 1, 6, 2, A[5]); hline(img, ox + 5, ox + 10, oy, A[6])
        px(img, ox + 4, oy + 1, A[3]); px(img, ox + 11, oy + 1, A[3]); hline(img, ox + 5, ox + 10, oy + 3, A[2])
    elif kind == "grate":
        for i in range(1, 16, 3):
            px(img, ox + i, oy + 1, H[3]); px(img, ox + i, oy + 2, H[2])
    elif kind == "seam":
        vline(img, ox + 7, oy, oy + 3, H[2]); vline(img, ox + 8, oy, oy + 2, H[7])


def edge_top_hazard(img, ox, oy, H, S):
    edge_top(img, ox, oy, H, S)
    for x in range(16):
        for y in range(6, 10):
            on = ((x + y) // 3) % 2 == 0
            px(img, ox + x, oy + y, S[3] if on else H[0])
    hline(img, ox, ox + 15, oy + 10, H[1])


def edge_bottom(img, ox, oy, H):
    hline(img, ox, ox + 15, oy + 15, H[0])
    hline(img, ox, ox + 15, oy + 14, H[1])
    hline(img, ox, ox + 15, oy + 13, H[3])
    hline(img, ox, ox + 15, oy + 12, H[1])
    px(img, ox + 4, oy + 13, H[4]); px(img, ox + 12, oy + 13, H[4])


def edge_left(img, ox, oy, H):
    vline(img, ox, oy, oy + 15, H[5])
    vline(img, ox + 1, oy, oy + 15, H[4])
    vline(img, ox + 2, oy, oy + 15, H[1])
    px(img, ox + 1, oy + 4, H[2]); px(img, ox + 1, oy + 12, H[2])


def edge_right(img, ox, oy, H):
    vline(img, ox + 15, oy, oy + 15, H[0])
    vline(img, ox + 14, oy, oy + 15, H[1])
    vline(img, ox + 13, oy, oy + 15, H[3])
    px(img, ox + 14, oy + 4, H[2]); px(img, ox + 14, oy + 12, H[2])


def solid_tile(img, ox, oy, mask, H, A, kind="plain", S=None):
    hull_interior(img, ox, oy, H)
    n, e, s, w = mask & 1, mask & 2, mask & 4, mask & 8
    if not s:
        edge_bottom(img, ox, oy, H)
    if not w:
        edge_left(img, ox, oy, H)
    if not e:
        edge_right(img, ox, oy, H)
    if not n:
        if kind == "hazard":
            edge_top_hazard(img, ox, oy, H, S)
        else:
            edge_top(img, ox, oy, H, A, kind)
        # rounded outer corners on the walk surface
        if not w:
            px(img, ox, oy, T); px(img, ox + 1, oy, H[6]); px(img, ox, oy + 1, H[6])
        if not e:
            px(img, ox + 15, oy, T); px(img, ox + 14, oy, H[5]); px(img, ox + 15, oy + 1, H[3])
    if not s:
        if not w:
            px(img, ox, oy + 15, T)
        if not e:
            px(img, ox + 15, oy + 15, T)


def oneway(img, ox, oy, H, A, part):
    """Thin catwalk: 6px deck + cross-bracing below. part: l, m, r, single"""
    x0 = ox + (1 if part in ("l", "single") else 0)
    x1 = ox + (14 if part in ("r", "single") else 15)
    hline(img, x0, x1, oy, H[7]); hline(img, x0, x1, oy + 1, H[6]); hline(img, x0, x1, oy + 2, H[4])
    hline(img, x0, x1, oy + 3, H[1]); hline(img, x0, x1, oy + 4, H[2]); hline(img, x0, x1, oy + 5, H[0])
    for i in range(x0 + 1, x1, 4):
        px(img, i, oy + 1, A[4]); px(img, i, oy + 2, H[3])
    if part in ("l", "single"):
        vline(img, ox, oy + 1, oy + 4, H[5]);
    if part in ("r", "single"):
        vline(img, ox + 15, oy + 1, oy + 4, H[1])
    # truss underneath
    for i in range(0, 8):
        if part in ("m",) or (part == "l" and i + 0 >= 2) or (part == "r" and i <= 5) or part == "single" and 2 <= i <= 5:
            px(img, ox + i, oy + 6 + (i % 4), H[1]) if i < 4 else px(img, ox + i, oy + 9 - (i % 4), H[1])
            px(img, ox + 8 + i, oy + 6 + (i % 4), H[1]) if i < 4 else px(img, ox + 8 + i, oy + 9 - (i % 4), H[1])


def wall_plain(img, ox, oy, W, variant=0):
    rect(img, ox, oy, TS, TS, W[1])
    if variant == 0:
        hline(img, ox, ox + 15, oy, W[0]); vline(img, ox, oy, oy + 15, W[0])
        hline(img, ox + 1, ox + 15, oy + 1, W[2])
    elif variant == 1:
        hline(img, ox, ox + 15, oy, W[0]); vline(img, ox, oy, oy + 15, W[0])
        hline(img, ox + 1, ox + 15, oy + 1, W[2])
        px(img, ox + 3, oy + 4, W[2]); px(img, ox + 12, oy + 4, W[2]); px(img, ox + 3, oy + 12, W[2]); px(img, ox + 12, oy + 12, W[2])
    elif variant == 2:
        hline(img, ox, ox + 15, oy, W[0])
        hline(img, ox, ox + 15, oy + 1, W[2])
        hline(img, ox, ox + 15, oy + 8, W[0]); hline(img, ox, ox + 15, oy + 9, W[2])
    elif variant == 3:   # shadowed
        rect(img, ox, oy, TS, TS, W[0])
        for i in range(0, 16, 4):
            px(img, ox + i, oy + (i * 3) % 16, W[1])
    elif variant == 4:   # vertical seam
        vline(img, ox + 7, oy, oy + 15, W[0]); vline(img, ox + 8, oy, oy + 15, W[2])


def build_skin(name, sk):
    H = [hexc(h) for h in sk["hull"]]
    W = [hexc(h) for h in sk["wall"]]
    A = ramp(sk["acc"]); L = ramp(sk["lamp"]); S = ramp(sk["stripe"])
    img = new(COLS * TS, ROWS * TS)

    def at(i):
        return (i % COLS) * TS, (i // COLS) * TS

    for m in range(16):
        ox, oy = at(m)
        solid_tile(img, ox, oy, m, H, A)
    ox, oy = at(16); hull_deep(img, ox, oy, H, 0)
    ox, oy = at(17); hull_deep(img, ox, oy, H, 1)
    ox, oy = at(18); hull_interior(img, ox, oy, H, 1)
    ox, oy = at(19); hull_interior(img, ox, oy, H, 2)
    # top-surface variants (mask: E, S, W solid, N open = 2+4+8 = 14)
    ox, oy = at(20); solid_tile(img, ox, oy, 14, H, L, "lamp")
    ox, oy = at(21); solid_tile(img, ox, oy, 14, H, A, "hazard", S)
    ox, oy = at(22); solid_tile(img, ox, oy, 14, H, A, "grate")
    ox, oy = at(23); solid_tile(img, ox, oy, 14, H, A, "seam")
    for i, part in enumerate(["l", "m", "r", "single"]):
        ox, oy = at(32 + i); oneway(img, ox, oy, H, A, part)
    ox, oy = at(36)
    vline(img, ox + 7, oy, oy + 15, H[1]); vline(img, ox + 8, oy, oy + 15, H[3])
    for y in range(2, 16, 6):
        px(img, ox + 6, oy + y, H[2]); px(img, ox + 9, oy + y, H[2])

    # ---- back wall ---------------------------------------------------------
    for v in range(3):
        ox, oy = at(48 + v); wall_plain(img, ox, oy, W, v)
    # pipes
    P = [W[0], H[1], H[3], H[4]]
    ox, oy = at(51); wall_plain(img, ox, oy, W, 0)
    hline(img, ox, ox + 15, oy + 5, P[0]); hline(img, ox, ox + 15, oy + 6, P[3]); hline(img, ox, ox + 15, oy + 7, P[2])
    hline(img, ox, ox + 15, oy + 8, P[1]); hline(img, ox, ox + 15, oy + 9, P[1]); hline(img, ox, ox + 15, oy + 10, P[0])
    vline(img, ox + 3, oy + 5, oy + 10, P[0]); vline(img, ox + 4, oy + 5, oy + 10, P[2]); px(img, ox + 4, oy + 6, H[5])
    ox, oy = at(52); wall_plain(img, ox, oy, W, 0)
    vline(img, ox + 5, oy, oy + 15, P[0]); vline(img, ox + 6, oy, oy + 15, P[3]); vline(img, ox + 7, oy, oy + 15, P[2])
    vline(img, ox + 8, oy, oy + 15, P[1]); vline(img, ox + 9, oy, oy + 15, P[1]); vline(img, ox + 10, oy, oy + 15, P[0])
    hline(img, ox + 5, ox + 10, oy + 3, P[0]); hline(img, ox + 5, ox + 10, oy + 4, P[2]); px(img, ox + 6, oy + 4, H[5])
    ox, oy = at(53); wall_plain(img, ox, oy, W, 0)   # elbow: from left to down
    for i in range(0, 8):
        hline(img, ox, ox + 7, oy + 5, P[0])
    hline(img, ox, ox + 8, oy + 5, P[0]); hline(img, ox, ox + 9, oy + 6, P[3]); hline(img, ox, ox + 8, oy + 7, P[2])
    hline(img, ox, ox + 7, oy + 8, P[1]); hline(img, ox, ox + 6, oy + 9, P[1]); hline(img, ox, ox + 5, oy + 10, P[0])
    vline(img, ox + 5, oy + 10, oy + 15, P[0]); vline(img, ox + 6, oy + 10, oy + 15, P[3]); vline(img, ox + 7, oy + 9, oy + 15, P[2])
    vline(img, ox + 8, oy + 8, oy + 15, P[1]); vline(img, ox + 9, oy + 7, oy + 15, P[1]); vline(img, ox + 10, oy + 6, oy + 15, P[0])
    # vent
    ox, oy = at(54); wall_plain(img, ox, oy, W, 0)
    rect(img, ox + 2, oy + 3, 12, 10, W[0])
    for y in range(4, 12, 2):
        hline(img, ox + 3, ox + 12, oy + y, W[3])
    hline(img, ox + 2, ox + 13, oy + 3, H[1]); hline(img, ox + 2, ox + 13, oy + 12, H[1])
    # girder cross-brace
    ox, oy = at(55); wall_plain(img, ox, oy, W, 3)
    for i in range(16):
        px(img, ox + i, oy + i, W[3]); px(img, ox + 15 - i, oy + i, W[3])
        px(img, ox + i, oy + min(15, i + 1), W[2]); px(img, ox + 15 - i, oy + min(15, i + 1), W[2])
    hline(img, ox, ox + 15, oy, W[3]); hline(img, ox, ox + 15, oy + 15, W[2])
    # column + cap
    ox, oy = at(56); wall_plain(img, ox, oy, W, 0)
    rect(img, ox + 4, oy, 8, 16, W[2]); vline(img, ox + 4, oy, oy + 15, W[3]); vline(img, ox + 5, oy, oy + 15, H[2])
    vline(img, ox + 11, oy, oy + 15, W[0]); vline(img, ox + 8, oy, oy + 15, W[1])
    ox, oy = at(57); wall_plain(img, ox, oy, W, 0)
    rect(img, ox + 4, oy + 6, 8, 10, W[2]); vline(img, ox + 4, oy + 6, oy + 15, W[3]); vline(img, ox + 11, oy + 6, oy + 15, W[0])
    rect(img, ox + 2, oy + 2, 12, 4, W[3]); hline(img, ox + 2, ox + 13, oy + 2, H[3]); hline(img, ox + 2, ox + 13, oy + 5, W[0])
    # window frame pieces (thick frame, inner bevel); centre is transparent
    F = [W[0], H[1], H[2], H[4]]

    def frame(ox, oy, top, bottom, left, right):
        rect(img, ox, oy, TS, TS, T)  # start transparent
        img.paste((0, 0, 0, 0), (ox, oy, ox + TS, oy + TS))
        if top:
            rect(img, ox, oy, TS, 6, F[1]); hline(img, ox, ox + 15, oy, W[1]); hline(img, ox, ox + 15, oy + 1, F[3])
            hline(img, ox, ox + 15, oy + 4, F[2]); hline(img, ox, ox + 15, oy + 5, F[0])
        if bottom:
            rect(img, ox, oy + 10, TS, 6, F[1]); hline(img, ox, ox + 15, oy + 10, F[0]); hline(img, ox, ox + 15, oy + 11, F[3])
            hline(img, ox, ox + 15, oy + 14, F[2]); hline(img, ox, ox + 15, oy + 15, W[0])
        if left:
            rect(img, ox, oy, 6, TS, F[1]); vline(img, ox, oy, oy + 15, W[1]); vline(img, ox + 1, oy, oy + 15, F[3])
            vline(img, ox + 4, oy, oy + 15, F[2]); vline(img, ox + 5, oy, oy + 15, F[0])
        if right:
            rect(img, ox + 10, oy, 6, TS, F[1]); vline(img, ox + 10, oy, oy + 15, F[0]); vline(img, ox + 11, oy, oy + 15, F[3])
            vline(img, ox + 14, oy, oy + 15, F[2]); vline(img, ox + 15, oy, oy + 15, W[0])
        # corner bolts
        if top and left:
            rect(img, ox, oy, 6, 6, F[1]); px(img, ox + 2, oy + 2, F[3]); px(img, ox + 3, oy + 3, F[0])
            hline(img, ox, ox + 5, oy, W[1]); vline(img, ox, oy, oy + 5, W[1])
        if top and right:
            rect(img, ox + 10, oy, 6, 6, F[1]); px(img, ox + 12, oy + 2, F[3]); px(img, ox + 13, oy + 3, F[0])
        if bottom and left:
            rect(img, ox, oy + 10, 6, 6, F[1]); px(img, ox + 2, oy + 12, F[3]); px(img, ox + 3, oy + 13, F[0])
        if bottom and right:
            rect(img, ox + 10, oy + 10, 6, 6, F[1]); px(img, ox + 12, oy + 12, F[3]); px(img, ox + 13, oy + 13, F[0])

    specs = [(1, 0, 1, 0), (1, 0, 0, 0), (1, 0, 0, 1), (0, 0, 1, 0), (0, 0, 0, 1), (0, 1, 1, 0), (0, 1, 0, 0), (0, 1, 0, 1)]
    for i, (t, b, l, r) in enumerate(specs):
        ox, oy = at(58 + i); frame(ox, oy, t, b, l, r)
    # hazard strip on wall
    ox, oy = at(66); wall_plain(img, ox, oy, W, 0)
    for x in range(16):
        for y in range(6, 10):
            px(img, ox + x, oy + y, S[2] if ((x + y) // 3) % 2 == 0 else W[0])
    # wall light
    ox, oy = at(67); wall_plain(img, ox, oy, W, 0)
    rect(img, ox + 5, oy + 5, 6, 6, H[1]); rect(img, ox + 6, oy + 6, 4, 4, L[4]); px(img, ox + 6, oy + 6, L[6]); px(img, ox + 7, oy + 6, L[5])
    px(img, ox + 9, oy + 9, L[3])
    # wall grate
    ox, oy = at(68); wall_plain(img, ox, oy, W, 3)
    for y in range(0, 16, 4):
        hline(img, ox, ox + 15, oy + y, W[2])
    for x in range(0, 16, 4):
        vline(img, ox + x, oy, oy + 15, W[2])
    # hanging cables (transparent bg)
    ox, oy = at(69)
    for (cx, ln, col) in ((3, 12, W[3]), (7, 15, H[1]), (11, 9, W[3]), (13, 13, W[2])):
        vline(img, ox + cx, oy, oy + ln, col)
    px(img, ox + 7, oy + 15, L[4])
    ox, oy = at(70); wall_plain(img, ox, oy, W, 3)
    ox, oy = at(71); wall_plain(img, ox, oy, W, 4)
    save(img, f"tiles/tiles_{name}.png")
    return img


def build():
    out = {}
    for name, sk in SKINS.items():
        img = build_skin(name, sk)
        out[f"tiles_{name}"] = {"file": f"tiles/tiles_{name}.png"}
        if name in ("dock", "reactor"):
            preview(img, f"tiles_{name}.png", scale=4, bg="#05060c", grid=(16, 16))
    manifest("tiles", {"images": out, "tileSize": TS, "tileCols": COLS})


def mock_room(name="dock"):
    """Assemble a little test room to judge the tiles in context."""
    til = Image.open(os.path.join(ASSETS, f"tiles/tiles_{name}.png"))
    Wt, Ht = 30, 17
    grid = [[0] * Wt for _ in range(Ht)]
    for x in range(Wt):
        for y in range(13, Ht):
            grid[y][x] = 1
    for x in range(8, 14):
        for y in range(9, 11):
            grid[y][x] = 1
    for x in range(20, 30):
        for y in range(10, 13):
            grid[y][x] = 1
    for x in range(0, 30):
        grid[0][x] = 1
    for y in range(0, 6):
        grid[y][0] = 1; grid[y][1] = 1
    for x in range(15, 18):
        grid[13][x] = 0; grid[14][x] = 0
    img = new(Wt * 16, Ht * 16, hexc("#05060c"))

    def tile(i):
        return til.crop(((i % 16) * 16, (i // 16) * 16, (i % 16) * 16 + 16, (i // 16) * 16 + 16))

    def sol(x, y):
        if x < 0 or x >= Wt or y < 0 or y >= Ht:
            return 1
        return grid[y][x]
    rnd = random.Random(3)
    # back wall with a window
    for y in range(Ht):
        for x in range(Wt):
            if 3 <= x <= 7 and 3 <= y <= 7:
                wi = {(0, 0): 58, (1, 0): 59, (2, 0): 60, (0, 1): 61, (2, 1): 62, (0, 2): 63, (1, 2): 64, (2, 2): 65}
                kx = 0 if x == 3 else 2 if x == 7 else 1
                ky = 0 if y == 3 else 2 if y == 7 else 1
                if (kx, ky) in wi:
                    img.alpha_composite(tile(wi[(kx, ky)]), (x * 16, y * 16))
                continue
            t = 48 + (1 if (x + y) % 5 == 0 else 2 if y % 6 == 2 else 0)
            if y == 8 and x > 9:
                t = 51
            if x == 22 and y < 8:
                t = 56
            if x == 26 and 2 < y < 6:
                t = 54
            if y == 11 and x in (4, 12):
                t = 67
            img.alpha_composite(tile(t), (x * 16, y * 16))
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
    for i, x in enumerate(range(3, 7)):
        img.alpha_composite(tile(32 if i == 0 else 34 if i == 3 else 33), (x * 16 + 320 - 48 - 200, 6 * 16 + 16))
    jk = Image.open(os.path.join(ASSETS, "sprites/jake.png")).crop((0, 0, 32, 32))
    img.alpha_composite(jk, (10 * 16, 9 * 16 - 31))
    img.alpha_composite(jk, (2 * 16 + 96, 13 * 16 - 31))
    preview(img, f"mock_{name}.png", scale=3, bg="#05060c")


if __name__ == "__main__":
    build()
    mock_room("dock")
    mock_room("reactor")
    mock_room("zerog")
