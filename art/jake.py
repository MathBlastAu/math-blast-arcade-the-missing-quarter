"""
jake.py - Jake Nova, Junior Fuel Inspector.  32x32 frames, facing right.

Built as a pixel "paper doll": hand-pixelled head / torso / boots, limbs posed
with a tiny two-bone IK rig so every animation shares the same proportions.
Change the palette block below to restyle him to match brand artwork.
"""
import math
from pix import *

FW = FH = 32

# ---- palette (swap these to re-skin Jake) -----------------------------------
SUIT = ramp("orange")       # 0 darkest .. 6 lightest
HAIR = ramp("hair")
SKIN = ramp("skin")
CY = ramp("cyan")
ST = ramp("steel")

HEAD_CMAP = {
    "a": HAIR[1], "b": HAIR[2], "c": HAIR[3],
    "s": SKIN[3], "S": SKIN[4], "d": SKIN[2], "D": SKIN[1],
    "e": C["ink2"], "w": C["white"],
    "g": ST[1], "y": ST[4], "G": CY[4], "L": CY[6], "l": CY[3],
    "m": hexc("#8a2c10"), "p": hexc("#f09a84"), "W": C["white"],
}

# 13 wide x 12 tall, facing right.  Goggles pushed up on the forehead.
HEAD = {
    "normal": [
        "....bbbb.....",
        "..bbccbbbb...",
        ".abccbbbbbbb.",
        ".abbbbbbbbbba",
        "aygGLlygGLlyy",
        "aaygGgyygGGy.",
        "aabbsbsssbsS.",
        "aadsswesswes.",
        ".adsseesseeS.",
        ".dDpsssssspS.",
        "..dsssmmssS..",
        "...ddssssd...",
    ],
}


def head_variant(kind):
    rows = [list(r) for r in HEAD["normal"]]
    if kind == "blink":
        rows[7] = list("aadssssssss.")
        rows[8] = list(".adsDDssDDS.")
    elif kind == "happy":      # ^ ^ eyes and open grin
        rows[7] = list("aadsssessses.")
        rows[8] = list(".adssesesese.")
        rows[10] = list("..dssmWWmsS..")
        rows[11] = list("...ddsmmsd...")
    elif kind == "hurt":       # scrunched eyes, open mouth
        rows[7] = list("aadsDsssssDS.")
        rows[8] = list(".adssDDsDDsS.")
        rows[10] = list("..dsssmmmsS..")
        rows[11] = list("...ddsmmsd...")
    elif kind == "effort":     # determined: flat brows
        rows[6] = list("aabbsDDsDDsS.")
        rows[10] = list("..dssssmmsS..")
    elif kind == "look_up":
        rows[7] = list("aadsseesseeS.")
        rows[8] = list(".adsswssswsS.")
    out = []
    for r in rows:
        r = "".join(r)
        out.append((r + "." * 13)[:13])
    return ascii_sprite(out, HEAD_CMAP)


TORSO_CMAP = {
    "W": C["white"], "y": ST[6], "o": SUIT[3], "O": SUIT[4], "r": SUIT[2], "R": SUIT[1],
    "c": CY[5], "C": CY[4], "n": C["navy1"], "N": C["navy2"], "k": ST[2], "K": ST[3], "q": ST[5],
}
# 10 wide x 8 tall. Left 2 columns = backpack. Facing right.
TORSO = [
    "...yWWWy..",
    "kK.OOoooo.",
    "KqrOooooo.",
    "KCrOooCcr.",
    "KqrOooooR.",
    "kkrooooor.",
    "..nNNNyNn.",
    "..rooooor.",
]
BOOT_CMAP = {"W": C["white"], "y": ST[6], "g": ST[5], "k": ST[3], "o": SUIT[4]}
BOOT_F = ["Wy...", "WWWy.", "ygggk"]          # front boot 5x3 (toe points right)
BOOT_B_CMAP = {"W": ST[6], "y": ST[5], "g": ST[4], "k": ST[2], "o": SUIT[3]}


def ik(p0, p1, l1, l2, bend):
    """Two-bone IK. bend=+1 bends the joint to the right of the p0->p1 direction."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy)
    d = max(0.001, min(d, l1 + l2 - 0.001))
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    ux, uy = dx / math.hypot(dx, dy or 0.0001), dy / math.hypot(dx or 0.0001, dy)
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    mx, my = p0[0] + ux * a, p0[1] + uy * a
    return (mx - uy * h * bend, my + ux * h * bend)


def limb(img, pts, r, col):
    for i in range(len(pts) - 1):
        capsule(img, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], r, col)


def draw_leg(img, hip, foot, back, bend=1):
    knee = ik(hip, (foot[0], foot[1] - 1.5), 4.0, 4.0, bend)
    base = SUIT[2] if back else SUIT[3]
    limb(img, [hip, knee], 1.3, base)
    limb(img, [knee, (foot[0], foot[1] - 2)], 1.0, base)
    if not back:
        # highlight along the front of the thigh
        limb(img, [(hip[0] + 0.6, hip[1]), (knee[0] + 0.6, knee[1])], 0.4, SUIT[4])
    boot = ascii_sprite(BOOT_F, BOOT_B_CMAP if back else BOOT_CMAP)
    paste(img, boot, round(foot[0] - 2), round(foot[1] - 2))


def draw_arm(img, sh, hand, back, bend=-1):
    el = ik(sh, hand, 3.2, 3.2, bend)
    base = SUIT[2] if back else SUIT[4]
    limb(img, [sh, el, hand], 0.9, base)
    if not back:
        px(img, sh[0], sh[1] - 1, SUIT[5])
    glove = ST[5] if back else C["white"]
    disc(img, hand[0], hand[1], 1.0, glove)
    if not back:
        px(img, round(hand[0]), round(hand[1]) + 1, ST[6])


def render(p):
    """p: pose dict -> 32x32 RGBA frame (with outline)."""
    img = new(FW, FH)
    hipx = 15.0 + p.get("hx", 0)
    hipy = 22.0 + p.get("hy", 0)
    lean = p.get("lean", 0)
    neck = (hipx + lean, hipy - 7)
    ground = 30

    # --- back arm, back leg -------------------------------------------------
    sh_b = (neck[0] + 1.5, neck[1] + 2)
    hb = p.get("armB", (2, 5))
    draw_arm(img, sh_b, (sh_b[0] + hb[0], sh_b[1] + hb[1]), True, p.get("bendAB", -1))
    lb = p.get("legB", (-1, 8))
    draw_leg(img, (hipx + 1.0, hipy), (hipx + 1.0 + lb[0], hipy + lb[1]), True, p.get("bendLB", 1))

    # --- front leg ----------------------------------------------------------
    lf = p.get("legF", (0, 8))
    draw_leg(img, (hipx - 1.0, hipy), (hipx - 1.0 + lf[0], hipy + lf[1]), False, p.get("bendLF", 1))

    # --- torso --------------------------------------------------------------
    torso = ascii_sprite(TORSO, TORSO_CMAP)
    tx = round(neck[0] - 6)
    ty = round(neck[1])
    if p.get("squash"):
        torso = torso.crop((0, 1, 10, 8))
        ty += 1
    paste(img, torso, tx, ty)

    # --- head ---------------------------------------------------------------
    head = head_variant(p.get("face", "normal"))
    hd = p.get("head", (0, 0))
    lag = p.get("hairLag", 0)
    if lag:
        h2 = new(15, 12)
        for y in range(12):
            sx = (-lag if y < 2 else (-lag // 2 if y < 3 and abs(lag) > 1 else 0))
            for x in range(13):
                c = head.getpixel((x, y))
                if c[3]:
                    px(h2, x + 1 + sx, y, c)
        head = h2
        hx0 = round(neck[0] - 6.0 + hd[0]) - 1
    else:
        hx0 = round(neck[0] - 6.0 + hd[0])
    paste(img, head, hx0, round(neck[1] - 11 + hd[1]))

    # --- front arm ----------------------------------------------------------
    sh_f = (neck[0] - 1.5, neck[1] + 2)
    hf = p.get("armF", (-1, 5))
    draw_arm(img, sh_f, (sh_f[0] + hf[0], sh_f[1] + hf[1]), False, p.get("bendAF", -1))

    img = outline(img, OUT)
    # extras drawn after the outline (sparkles etc.)
    for (x, y, c) in p.get("extra", []):
        px(img, x, y, c)
    return img


# ---------------------------------------------------------------------------
# Animations
# ---------------------------------------------------------------------------
def foot_cycle(ph, stride=4.0, lift=3.5):
    ph = ph % 1.0
    if ph < 0.5:                                  # stance: foot slides back along ground
        t = ph / 0.5
        return (stride - 2 * stride * t, 8.0)
    t = (ph - 0.5) / 0.5                          # swing: foot lifts and travels forward
    return (-stride + 2 * stride * t, 8.0 - lift * math.sin(math.pi * t) - (1.0 if 0.2 < t < 0.8 else 0))


def anim_idle():
    fr = []
    for i in range(8):
        b = 1 if i in (2, 3, 4) else 0            # breathe: body sinks 1px
        fr.append(dict(hy=b * 0.0, head=(0, b), armF=(-1, 5 + b * 0.4), armB=(2, 5 + b * 0.4),
                       legF=(-1, 8), legB=(1.5, 8), face="blink" if i == 6 else "normal",
                       hairLag=0))
    return fr


def anim_run():
    fr = []
    for i in range(8):
        ph = i / 8.0
        f = foot_cycle(ph)
        b = foot_cycle(ph + 0.5)
        bob = [1, 0, -1, 0, 1, 0, -1, 0][i]
        sw = math.cos(2 * math.pi * ph)
        fr.append(dict(hy=bob, lean=1, head=(1, 0), legF=f, legB=b,
                       armF=(-3.6 * sw + 0.5, 3.6 - abs(sw) * 0.8),
                       armB=(3.6 * sw + 0.5, 3.6 - abs(sw) * 0.8),
                       bendAF=-1, bendAB=-1, hairLag=1, face="effort" if False else "normal"))
    return fr


def anim_jump():
    return [
        dict(hy=-1, head=(0, 0), legF=(2, 5.5), legB=(-2, 7.5), armF=(-5, -2.5), armB=(5.5, -1.5),
             bendAF=-1, bendAB=1, hairLag=0, face="look_up"),
        dict(hy=-1, head=(0, 0), legF=(2.5, 5), legB=(-2.5, 7), armF=(-5, -3.5), armB=(5.5, -2.5),
             bendAF=-1, bendAB=1, hairLag=0, face="look_up"),
    ]


def anim_fall():
    return [
        dict(hy=-1, head=(0, 0), legF=(1.5, 7.5), legB=(-2.5, 6.5), armF=(-4.5, -2.5), armB=(5.5, -2.5),
             bendAF=-1, bendAB=1, hairLag=0, face="normal"),
        dict(hy=-1, head=(0, 0), legF=(2, 7), legB=(-2, 7), armF=(-4.5, -3.5), armB=(5.5, -3.5),
             bendAF=-1, bendAB=1, hairLag=0, face="normal"),
    ]


def anim_land():
    return [
        dict(hy=3, head=(0, 1), squash=True, legF=(-2.5, 5), legB=(3, 5), bendLF=1, bendLB=1,
             armF=(-3.5, 4), armB=(4.5, 4), face="effort"),
        dict(hy=1.5, head=(0, 0), legF=(-1.5, 6.5), legB=(2, 6.5), armF=(-2.5, 4.5), armB=(3.5, 4.5),
             face="normal"),
    ]


def anim_interact():
    return [
        dict(head=(0, 0), legF=(-1, 8), legB=(1.5, 8), armF=(4.5, 1.5), armB=(2, 5), bendAF=1),
        dict(head=(1, 0), legF=(-1, 8), legB=(1.5, 8), armF=(5.5, 0), armB=(2, 5), bendAF=1, face="effort"),
        dict(head=(0, 0), legF=(-1, 8), legB=(1.5, 8), armF=(5, 2.5), armB=(2, 5), bendAF=1),
    ]


def anim_celebrate():
    fr = []
    hop = [0, -1, -3, -3, -2, 0, 1, 0]
    for i in range(8):
        up = hop[i] < -1
        fr.append(dict(hy=hop[i] if hop[i] < 0 else hop[i] * 1.0,
                       head=(0, -1 if up else 0),
                       legF=(-1.5, 8 if not up else 6.5), legB=(2, 8 if not up else 6),
                       armF=((-1, 5) if i == 0 else (-4.5, -4.5) if up else (-5, -2)),
                       armB=((2, 5) if i == 0 else (5.5, -3.5) if up else (5.5, -1)),
                       bendAF=-1, bendAB=1, face="happy" if i > 0 else "normal",
                       squash=(i == 6)))
    return fr


def anim_hurt():
    return [
        dict(hx=-1, hy=-1, lean=-1, head=(-1, 0), legF=(2.5, 7), legB=(-0.5, 7.5), armF=(-4, -1), armB=(5, -2),
             bendAB=1, face="hurt"),
        dict(hx=-1, hy=0, lean=-1, head=(-1, 1), legF=(2, 7.5), legB=(0, 8), armF=(-4, 0), armB=(5, -1),
             bendAB=1, face="hurt"),
    ]


def build():
    groups = [
        ("idle", anim_idle(), 6, True),
        ("run", anim_run(), 14, True),
        ("jump", anim_jump(), 8, False),
        ("fall", anim_fall(), 8, True),
        ("land", anim_land(), 14, False),
        ("interact", anim_interact(), 8, True),
        ("celebrate", anim_celebrate(), 10, True),
        ("hurt", anim_hurt(), 8, False),
    ]
    frames = []
    anims = {}
    for name, poses, fps, loop in groups:
        start = len(frames)
        for p in poses:
            frames.append(render(p))
        anims[name] = {"frames": list(range(start, len(frames))), "fps": fps, "loop": loop}
    sh = sheet(frames, cols=8)
    save(sh, "sprites/jake.png")
    preview(sh, "jake.png", scale=6, bg="#323f57")
    preview(sheet([frames[i] for i in (0, 9, 11, 16, 18, 20, 27, 33)], cols=8), "jake_big.png", scale=10, bg="#47566f")
    manifest("jake", {"sheets": {"jake": {"file": "sprites/jake.png", "fw": FW, "fh": FH, "anims": anims}}})
    return frames, anims


if __name__ == "__main__":
    fr, an = build()
    print(len(fr), "frames", {k: v["frames"] for k, v in an.items()})
