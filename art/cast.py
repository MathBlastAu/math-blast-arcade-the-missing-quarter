"""
cast.py - supporting cast for Math Blast Arcade.

  crawler   24x24  scrambled maintenance bot (ground enemy, stomped from above)
  drone     24x24  glitch drone (flying enemy)
  priya     32x32  Fuel Officer Priya (NPC) - saved sheet faces LEFT
  portraits 48x48  dialogue busts: Jake x3, Priya x2, Fraction Phantom x2

Run:  cd art && python3 cast.py
Writes assets/sprites/{crawler,drone,priya,portraits}.png, assets/manifest/cast.json
and previews art/_preview/cast_*.png
"""
import math, os
from pix import *
import jake as J

ST = ramp("steel"); PK = ramp("pink"); PU = ramp("purple"); CY = ramp("cyan")
NV = ramp("navy"); SK = ramp("skin"); HR = ramp("hair"); OR = ramp("orange")
GD = ramp("gold"); INK = ramp("ink"); RD = ramp("red")
WHITE = C["white"]

# shared colour keys for the robots ------------------------------------------
BOT = {
    "0": ST[0], "1": ST[1], "2": ST[2], "3": ST[3], "4": ST[4], "5": ST[5], "6": ST[6], "7": ST[7],
    "q": PU[1], "p": PU[2], "P": PU[3], "v": PU[4], "V": PU[5],
    "j": PK[0], "k": PK[1], "K": PK[2], "l": PK[3], "L": PK[4], "W": WHITE,
    "i": INK[0], "n": INK[1], "N": INK[2], "g": GD[3], "G": GD[4],
}


def stamp(img, rows, x, y, cmap=BOT):
    paste(img, ascii_sprite(rows, cmap), x, y)


def pts(img, coords, c):
    for (x, y) in coords:
        px(img, x, y, c)


def seg(img, coords, c):
    """Polyline through the listed points."""
    for i in range(len(coords) - 1):
        line(img, coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1], c)


def shift_row(img, y, dx):
    """Glitch tear: slide one pixel row sideways."""
    w = img.width
    row = [img.getpixel((x, y)) for x in range(w)]
    for x in range(w):
        sx = x - dx
        img.putpixel((x, y), row[sx] if 0 <= sx < w else T)


def spark(img, x, y, size=1, core=WHITE, arm=None):
    """Little plus-shaped spark. size 0 = single pixel."""
    arm = arm or PK[3]
    px(img, x, y, core)
    if size >= 1:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            px(img, x + dx, y + dy, arm)
    if size >= 2:
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            px(img, x + dx, y + dy, PK[2])
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            px(img, x + dx, y + dy, core)


# =============================================================================
# CRAWLER
# =============================================================================
# 20 x 13 body, facing right.  Broad flat top (stomp target), flared purple rim
# band with a toothy grille under the eye.
CRAWL_BODY = [
    "....677777766665....",
    "..6677766666555544..",
    ".667665555555555444.",
    ".676655555555555444.",
    ".666555555555555443.",
    ".665555555555554443.",
    ".655555555555544433.",
    ".655555555555444433.",
    ".554444444444443332.",
    ".1qqqqqqqqqqqqqqqq1.",
    "PvVvPPPPPPPPPPPPpppq",
    ".pPPpppppppppppppqq.",
    "...22222222222211...",
]
for _r in CRAWL_BODY:
    assert len(_r) == 20, _r
# 7 x 7 eye: dark socket, glowing pink lens with a hot core
EYE_VARIANTS = {
    "normal": [
        "..iii..",
        ".iKKKi.",
        "iKlLLKi",
        "iKLWLKi",
        "iklLlKi",
        ".ikKki.",
        "..iii..",
    ],
    "glitch": [
        "..iii..",
        ".iKKKi.",
        "iVLLlKi",
        "LWLKivi",
        "iklLlKi",
        ".ikvki.",
        "..iii..",
    ],
    "half": [
        "..iii..",
        ".i333i.",
        "i32222i",
        "iKLWLKi",
        "iklLlKi",
        ".ikKki.",
        "..iii..",
    ],
    "wide": [
        "..iii..",
        ".iLLLi.",
        "iLWWWLi",
        "iLWWWLi",
        "ilLWLli",
        ".iKlKi.",
        "..iii..",
    ],
}
FOOT = [".665.", "56654", "12221"]


def nslice(rows, keep, dup=()):
    """Squash helper: keep only the listed rows, and duplicate the listed columns."""
    out = []
    for r in keep:
        s = rows[r]
        t = ""
        for x, ch in enumerate(s):
            t += ch * (1 + dup.count(x))
        out.append(t)
    return out


def crawler_detail(img, x0, y0, i=0):
    """Panel seam, rivets, a cracked panel leaking glitch light, and the rim grille."""
    for r in range(1, 9):
        px(img, x0 + 8, y0 + r, ST[4])
    px(img, x0 + 10, y0 + 7, ST[3]); px(img, x0 + 2, y0 + 6, ST[4])
    # cracked back panel leaking glitch light (flickers)
    pts(img, [(x0 + 4, y0 + 1), (x0 + 5, y0 + 2), (x0 + 4, y0 + 3), (x0 + 4, y0 + 4), (x0 + 5, y0 + 5),
              (x0 + 4, y0 + 6), (x0 + 3, y0 + 7)], ST[3])
    glow = [(4, 3, PK[2]), (5, 5, PU[4]), (4, 4, PK[3])][i % 3]
    px(img, x0 + glow[0], y0 + glow[1], glow[2])
    px(img, x0 + 5, y0 + 3, ST[6]); px(img, x0 + 6, y0 + 5, ST[6])
    # toothy grille on the rim under the eye
    for cx in (12, 14, 16):
        px(img, x0 + cx, y0 + 10, ST[7]); px(img, x0 + cx, y0 + 11, ST[5])
        px(img, x0 + cx + 1, y0 + 10, INK[1]); px(img, x0 + cx + 1, y0 + 11, INK[1])
    # rim running light
    lit = i % 3
    for k, cx in enumerate((3, 6, 9)):
        px(img, x0 + cx, y0 + 10, PK[4] if k == lit else PK[1])


def crawler_frame(i):
    img = new(24, 24)
    ph = i / 6.0
    bob = [0, 1, 0, 0, 1, 0][i]
    by = 6 + bob
    # --- stubby legs (behind body) -------------------------------------------
    for hipx, off in ((16, 0.5), (6, 0.0)):
        fx, fy = J.foot_cycle(ph + off, stride=2.0, lift=2.0)
        fx = round(fx); lift = round(8.0 - fy)
        foot_x = hipx - 2 + fx
        foot_y = 20 - lift
        rect(img, hipx, 18, 2, max(0, foot_y - 18 + 1), ST[1])
        stamp(img, FOOT, foot_x, foot_y)
    # --- antenna (bent, bulb lags behind the bob) ------------------------------
    sway = [0, 0, 1, 0, 0, -1][i]
    ax, ay = 7, by
    px(img, ax, ay - 1, ST[4]); px(img, ax - 1, ay - 2, ST[5])
    bx = ax - 3 + sway
    rect(img, bx, ay - 4, 2, 2, PK[2]); px(img, bx, ay - 4, PK[4])
    # --- body ---------------------------------------------------------------
    stamp(img, CRAWL_BODY, 2, by)
    crawler_detail(img, 2, by, i)
    eye = ["normal", "normal", "glitch", "normal", "normal", "half"][i]
    stamp(img, EYE_VARIANTS[eye], 13, by + 2)
    # angry lid plate over the eye (slopes down toward the front)
    line(img, 12, by + 1, 19, by + 3, ST[2])
    if i == 2:
        # scrambled: one scanline tears sideways for a frame
        shift_row(img, by + 5, 1); shift_row(img, by + 6, -1)
        px(img, 3, by + 5, PU[4]); px(img, 20, by + 6, PK[3])
    img = outline(img)
    return img


def crawler_squash(k):
    img = new(24, 24)
    lens = ["KlK", "lWl", "KlK"]
    if k == 0:
        # stomped: shell slams down and spreads, eye squeezed to a slit
        body = nslice(CRAWL_BODY, [0, 1, 3, 5, 7, 9, 10, 11, 12], dup=(9, 10))
        top = 22 - len(body) + 1
        stamp(img, body, 1, top)
        hline(img, 6, 17, top, WHITE)
        for cx in (13, 15, 17):
            px(img, cx + 1, top + 6, ST[7]); px(img, cx + 1, top + 7, ST[5])
            px(img, cx + 2, top + 6, INK[1]); px(img, cx + 2, top + 7, INK[1])
        stamp(img, [".iiiiii.", "iLWWWWLi", "iKlLLlKi", ".iiiiii."], 12, top + 1)
        px(img, 6, top - 1, ST[4]); px(img, 5, top - 2, ST[5]); rect(img, 3, top - 3, 2, 2, PK[2]); px(img, 3, top - 3, PK[4])
        img = outline(img)
        spark(img, 3, 7, 1); spark(img, 20, 8, 1); px(img, 10, 9, WHITE); px(img, 14, 8, PK[4])
    elif k == 1:
        # pancake: eye lens pops out, sparks and bolts fly
        body = nslice(CRAWL_BODY, [0, 2, 9, 10, 11], dup=(9, 10))
        top = 22 - len(body) + 1
        stamp(img, body, 1, top)
        hline(img, 14, 19, top + 1, INK[0]); px(img, 16, top + 1, PK[1])
        stamp(img, lens, 15, 10)
        rect(img, 6, 12, 2, 2, ST[5]); px(img, 6, 12, ST[7])
        img = outline(img)
        spark(img, 4, 9, 2); spark(img, 20, 7, 2); spark(img, 11, 4, 1)
        spark(img, 1, 15, 0); spark(img, 22, 14, 0, core=PK[4])
    else:
        # scrap: shell in pieces, lens and sparks still flying
        body = nslice(CRAWL_BODY, [1, 10, 11], dup=(9, 10))
        stamp(img, body, 1, 20)
        for x in (7, 8, 15, 16):
            vline(img, x, 20, 22, T)
        vline(img, 9, 20, 20, T); vline(img, 14, 20, 20, T)
        stamp(img, lens, 18, 4)
        rect(img, 4, 8, 2, 2, ST[4]); px(img, 4, 8, ST[6])
        img = outline(img)
        spark(img, 2, 5, 1, arm=PU[4]); spark(img, 11, 2, 0); spark(img, 22, 11, 0, core=PK[4])
        px(img, 7, 14, PK[2]); px(img, 15, 12, PK[2]); px(img, 0, 13, PU[3]); px(img, 12, 9, PU[4])
    return img


def build_crawler():
    frames = [crawler_frame(i) for i in range(6)] + [crawler_squash(k) for k in range(3)]
    return frames


# =============================================================================
# DRONE
# =============================================================================
DRONE_BODY = [
    "....677766....",
    "..6677776655..",
    ".667766555554.",
    ".676655555544.",
    "66665555555444",
    "66655555555443",
    "66555555555443",
    "65555555554433",
    "65555555544433",
    ".555554444333.",
    ".544444433332.",
    "..4433333322..",
    "....332222....",
]


def drone_ring(img, back, i=0, flash=False):
    """Saturn-style thruster ring: elliptical band, back arc goes behind the body."""
    cx, cy, rx, ry = 11.5, 11.5, 10.5, 2.0
    for x in range(1, 23):
        t = (x - cx) / rx
        s = math.sqrt(max(0.0, 1 - t * t))
        if back:
            y = int(round(cy - ry * s - 0.5))
            px(img, x, y, PU[1]); px(img, x, y + 1, PU[1])
        else:
            y = int(round(cy + ry * s + 0.49))
            shade = PU[4] if x < 8 else PU[3] if x < 17 else PU[2]
            px(img, x, y - 1, shade)
            px(img, x, y, PU[2] if x < 17 else PU[1])
            if 3 <= x <= 20:
                px(img, x, y + 1, PU[1])
    if not back:
        px(img, 2, 11, PU[5]); px(img, 3, 11, PU[5])
        lit = i % 6
        for k, lx in enumerate((3, 7, 11, 15, 19)):
            t = (lx - cx) / rx
            y = int(round(cy + ry * math.sqrt(1 - t * t) + 0.49))
            on = flash or k == lit
            px(img, lx, y, PK[4] if on else PK[1])
            if on:
                px(img, lx, y - 1, PK[3])


def drone_art(i, mode="hover", do_outline=True, flame=True):
    img = new(24, 24)
    alert = mode == "alert"
    flash = alert and i % 2 == 0
    drone_ring(img, True)
    # fins ("ears"); they flare outward when alerted
    fin = [(5, 1, ST[6]), (5, 2, ST[5]), (6, 2, ST[4]), (5, 3, ST[5]), (6, 3, ST[4]), (7, 3, ST[3]),
           (6, 4, ST[4]), (7, 4, ST[3])]
    if flash:
        fin = [(3, 1, ST[6]), (4, 1, ST[6]), (4, 2, ST[5]), (5, 2, ST[5]), (5, 3, ST[5]), (6, 3, ST[4]),
               (7, 3, ST[3]), (6, 4, ST[4]), (7, 4, ST[3])]
    for (x, y, c) in fin:
        px(img, x, y, c)
        px(img, 23 - x, y, ST[3] if c not in (ST[5], ST[6]) else ST[4])
    # thruster flame: hot core, pink body
    n = [3, 5, 4, 3, 5, 4][i % 6] if not alert else (5 if flash else 4)
    if flame:
        for k in range(n):
            y = 17 + k
            w = 4 if k < n - 2 else 2
            x0 = 12 - w // 2
            for x in range(x0, x0 + w):
                edge = x in (x0, x0 + w - 1) and w > 2
                px(img, x, y, PK[2] if edge else (WHITE if k < 2 else PK[4] if k < n - 1 else PK[3]))
    stamp(img, DRONE_BODY, 5, 3)
    rect(img, 9, 16, 6, 1, ST[1])           # nozzle
    drone_ring(img, False, i, flash=flash)
    if flash:
        # the whole ring flares pink
        m = {PU[k]: PK[min(4, max(1, k - 1))] for k in range(1, 6)}
        m[PK[1]] = WHITE
        ringzone = img.crop((0, 9, 24, 16))
        img.paste(replace(ringzone, m), (0, 9))
        stamp(img, DRONE_BODY[:7], 5, 3)
    eye = ["normal", "normal", "normal", "glitch", "normal", "half"][i % 6]
    if alert:
        eye = "wide" if flash else "normal"
    stamp(img, EYE_VARIANTS[eye], 10, 4)
    if alert and not flash:
        # angry lid plate slanting over the eye
        line(img, 9, 4, 13, 5, ST[2]); line(img, 17, 4, 14, 5, ST[2])
    if not do_outline:
        return img
    return outline(img)


def drone_alert(k):
    img = drone_art(k, mode="alert")
    if k == 0:
        # alarm ticks radiating from the body
        for (x, y) in ((1, 6), (22, 6), (9, 1), (14, 1)):
            px(img, x, y, PK[3])
        for (x, y) in ((0, 5), (23, 5), (9, 0), (14, 0)):
            px(img, x, y, PK[4])
    return img


def flash_map(img, amount=2):
    m = {}
    for k in range(8):
        m[ST[k]] = ST[k + amount] if k + amount < 8 else WHITE
    for k in range(7):
        m[PU[k]] = PK[min(4, max(2, k))]
    for k in range(5):
        m[PK[k]] = PK[min(4, k + 2)] if k < 3 else WHITE
    return replace(img, m)


def dilate(img, c):
    out = img.copy()
    for y in range(img.height):
        for x in range(img.width):
            if img.getpixel((x, y))[3] == 0 and any(get(img, x + dx, y + dy)[3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), c)
    return out


def drone_pop(k):
    base = drone_art(0, do_outline=False, flame=False)
    img = new(24, 24)
    if k == 0:
        # swell: the whole drone bloats and flashes white-hot
        fl = flash_map(base, 3)
        core = fl.crop((2, 1, 22, 18))
        paste(img, core, 2, 2)
        img = dilate(img, WHITE)
        stamp(img, EYE_VARIANTS["wide"], 10, 5)
        img = outline(img)
        spark(img, 2, 3, 0); spark(img, 21, 4, 0); px(img, 12, 21, PK[3]); px(img, 11, 22, PK[2])
    elif k == 1:
        # burst: chunks fly outward from a starburst
        chunks = [((5, 1, 11, 8), (-3, 0)), ((13, 2, 19, 8), (3, -1)),
                  ((1, 10, 9, 15), (0, 5)), ((14, 10, 22, 15), (0, 6))]
        for (box, (dx, dy)) in chunks:
            paste(img, base.crop(box), box[0] + dx, box[1] + dy)
        img = outline(img)
        disc(img, 11.5, 10.5, 4.6, PK[2]); disc(img, 11.5, 10.5, 3.6, PK[3]); disc(img, 11.5, 10.5, 2.6, PK[4])
        disc(img, 11.5, 10.5, 1.6, WHITE)
        for a in range(8):
            ang = a * math.pi / 4 + 0.2
            for r in (5, 6, 7, 8):
                if r == 8 and a % 2:
                    continue
                px(img, 11.5 + math.cos(ang) * r, 10.5 + math.sin(ang) * r, WHITE if r < 7 else PK[3])
    else:
        # fizzle: a ring of fading sparks and two bits of scrap
        for a in range(8):
            ang = a * math.pi / 4 + 0.5
            r = 9 if a % 2 else 7
            x = 11.5 + math.cos(ang) * r; y = 11 + math.sin(ang) * r
            if a % 2:
                spark(img, int(round(x)), int(round(y)), 1, arm=PU[4] if a % 4 == 1 else PK[3])
            else:
                px(img, x, y, PK[4]); px(img, x + 1, y, PK[2])
        for a in range(0, 360, 30):          # thin fading shock ring
            px(img, 11.5 + math.cos(math.radians(a + 15)) * 4.5, 10.5 + math.sin(math.radians(a + 15)) * 4.5,
               with_alpha(PU[4] if a % 60 else PK[3], 200))
        rect(img, 4, 15, 2, 2, ST[4]); px(img, 4, 15, ST[6]); rect(img, 18, 17, 2, 2, ST[3]); px(img, 18, 17, ST[5])
    return img


def build_drone():
    return ([drone_art(i) for i in range(6)] + [drone_alert(k) for k in range(2)]
            + [drone_pop(k) for k in range(3)])


# =============================================================================
# PRIYA  (drawn facing right on Jake's rig, sheet is flipped to face left)
# =============================================================================
UNI = [CY[0], CY[1], CY[2], CY[3], CY[4]]        # deep shadow .. highlight (base = UNI[3])
PR_HEAD_CMAP = {
    "a": HR[0], "b": HR[1], "c": HR[2],
    "s": SK[2], "S": SK[3], "d": SK[1], "D": SK[0],
    "e": INK[2], "w": WHITE, "m": RD[1], "M": hexc("#b85a4a"), "W": WHITE, "g": GD[3],
}
# 15 x 12, facing right; bun at the back (left), hair swept back off the forehead
PR_HEAD = [
    "......aaaaaa...",
    "....aabbbbaaa..",
    ".aa.abbcbaaaaa.",
    "abaaabaaasssaa.",
    "aaaaaaassssssa.",
    ".a.aaasssssssS.",
    "..aaasaaassaaS.",
    "..aaadswesswes.",
    "...adsseesseeS.",
    "...agDsssssssS.",
    "....ddsssmmsS..",
    ".....ddssssd...",
]



def priya_head(kind="normal"):
    rows = [list(r) for r in PR_HEAD]
    if kind == "blink":
        rows[7] = list("..aaadsssssss..")
        rows[8] = list("...adsDDssDDS..")
    elif kind == "talk":       # open mouth
        rows[10] = list("....ddssmWmsS..")
        rows[11] = list(".....ddsmmsd...")
    elif kind == "smile":      # brows lift, mouth corners up
        rows[5] = list(".a.aaasaassaaS.")
        rows[6] = list("..aaasssssssS..")
        rows[9] = list("...agDssMssMsS.")
        rows[10] = list("....ddsssmmsS..")
    out = [("".join(r) + "." * 15)[:15] for r in rows]
    return ascii_sprite(out, PR_HEAD_CMAP)


PR_TORSO_CMAP = {"W": WHITE, "h": CY[5], "H": CY[4], "c": CY[3], "d": CY[2], "D": CY[1], "x": CY[0],
                 "g": GD[3], "G": GD[4], "b": ST[1], "B": GD[3], "n": NV[1], "N": NV[2], "y": ST[6],
                 "s": SK[2], "S": SK[3], "k": SK[1],
                 "T": ST[2], "t": ST[5], "q": CY[1], "Q": CY[3]}
# 10 x 9, facing right (columns 0 and 9 are only used by the folded arms)
PR_TORSO = [
    "...hWWh...",
    "..gcccccd.",
    ".Hccccgcdd",
    ".Hcccccccd",
    ".dccccccdd",
    ".dccccccdD",
    "..dcccccd.",
    "..bbbbBbb.",
    "..nNNNNNn.",
]
# folded arms, pasted over torso rows 3..6
PR_ARMS = [
    "HHHHHHcSd.",
    "cccccccsD.",
    "DskdddddD.",
    ".DDDDDDD..",
]
PR_ARMS_TAP = [
    "HHHHHHcSd.",
    "ccccccccD.",
    "DskdddddD.",
    ".DDDDDDD..",
]
# near arm hugging a tablet to her chest (talk), pasted over torso rows 2..7
PR_HOLD = [
    ".HH.ttttt.",
    ".Hc.tQhQt.",
    ".dc.thQQt.",
    ".dcccsQqt.",
    "..DDDSttt.",
    "..........",
]
PR_BOOT = ["54...", "5443.", "32221"]
PR_BOOT_CMAP = {"5": ST[5], "4": ST[4], "3": ST[3], "2": ST[2], "1": ST[1]}
PR_BOOT_B_CMAP = {"5": ST[4], "4": ST[3], "3": ST[2], "2": ST[1], "1": ST[0]}


def pr_leg(img, hip, foot, back):
    base = NV[1] if back else NV[2]
    capsule(img, hip[0], hip[1], foot[0], foot[1] - 2, 1.2, base)
    if not back:
        capsule(img, hip[0] - 0.4, hip[1] + 1, foot[0] - 0.4, foot[1] - 3, 0.4, NV[3])
    boot = ascii_sprite(PR_BOOT, PR_BOOT_B_CMAP if back else PR_BOOT_CMAP)
    paste(img, boot, round(foot[0] - 2), round(foot[1] - 2))


def pr_arm(img, sh, hand, back, bend=-1):
    el = J.ik(sh, hand, 3.4, 3.4, bend)
    if not back:
        # dark under-contour so the sleeve separates from the jacket behind it
        J.limb(img, [(sh[0], sh[1] + 1), (el[0], el[1] + 1), (hand[0] - 0.5, hand[1] + 1)], 0.9, UNI[1])
    base = UNI[2] if back else UNI[3]
    J.limb(img, [sh, el, hand], 0.9, base)
    if not back:
        J.limb(img, [(sh[0], sh[1] - 0.6), (el[0], el[1] - 0.6)], 0.3, UNI[4])
    else:
        J.limb(img, [(el[0], el[1] + 0.8), (hand[0] - 1, hand[1] + 0.8)], 0.3, UNI[1])
    disc(img, hand[0], hand[1], 1.0, SK[2])
    px(img, round(hand[0]), round(hand[1]) - 1, SK[3])
    if back:
        px(img, round(hand[0]), round(hand[1]) + 1, SK[1])


def priya_render(p):
    img = new(32, 32)
    hipx, hipy = 15.0, 21.0
    neck = (hipx, hipy - 8)
    # back arm
    sh_b = (neck[0] + 2.0, neck[1] + 2)
    if p.get("armB"):
        hb = p["armB"]
        pr_arm(img, sh_b, (sh_b[0] + hb[0], sh_b[1] + hb[1]), True, p.get("bendAB", -1))
    # legs: straight, feet planted apart
    pr_leg(img, (hipx + 1.2, hipy + 1), (hipx + 2.5, hipy + 9), True)
    pr_leg(img, (hipx - 1.2, hipy + 1), (hipx - 2.0, hipy + 9), False)
    # torso
    tx, ty = round(neck[0] - 5), round(neck[1])
    paste(img, ascii_sprite(PR_TORSO, PR_TORSO_CMAP), tx, ty)
    # head
    hd = p.get("head", (0, 0))
    paste(img, priya_head(p.get("face", "normal")), round(neck[0] - 8 + hd[0]), round(neck[1] - 11 + hd[1]))
    # arms
    sh_f = (neck[0] - 2.5, neck[1] + 2)
    if p.get("crossed"):
        arms = PR_ARMS_TAP if p.get("tap") else PR_ARMS
        paste(img, ascii_sprite(arms, PR_TORSO_CMAP), tx, ty + 3)
        if p.get("tap"):
            px(img, tx + 7, ty + 2, SK[3])
    elif p.get("hold"):
        paste(img, ascii_sprite(PR_HOLD, PR_TORSO_CMAP), tx, ty + 2)
    elif p.get("armF"):
        hf = p["armF"]
        pr_arm(img, sh_f, (sh_f[0] + hf[0], sh_f[1] + hf[1]), False, p.get("bendAF", -1))
    img = outline(img)
    return img


def build_priya():
    idle = []
    for i in range(6):
        br = 1 if i in (2, 3) else 0
        idle.append(dict(crossed=True, head=(0, br), face="blink" if i == 4 else "normal",
                         tap=1 if i in (0,) else 0))
    talk = [
        dict(hold=True, armB=(4.5, 2.5), bendAB=1, face="talk", head=(0, 0)),
        dict(hold=True, armB=(5.0, 1.0), bendAB=1, face="normal", head=(0, 0)),
        dict(hold=True, armB=(5.0, -0.5), bendAB=1, face="talk", head=(0, 1)),
        dict(hold=True, armB=(5.0, 1.0), bendAB=1, face="smile", head=(0, 0)),
    ]
    right = [priya_render(p) for p in idle + talk]
    return right


# =============================================================================
# PORTRAITS  (48x48 busts)
# =============================================================================
from PIL import ImageDraw

PW = PH = 48


def pmask(points):
    im = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(im).polygon(points, fill=255)
    d = im.load()
    return {(x, y) for y in range(PH) for x in range(PW) if d[x, y]}


def emask(cx, cy, rx, ry, n=2.0):
    return {(x, y) for y in range(PH) for x in range(PW)
            if abs((x - cx) / rx) ** n + abs((y - cy) / ry) ** n <= 1.0}


def rmask(x0, y0, x1, y1, r=0):
    """Inclusive rounded rectangle."""
    out = set()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = max(x0 + r - x, 0, x - (x1 - r)); dy = max(y0 + r - y, 0, y - (y1 - r))
            if dx * dx + dy * dy <= r * r + 0.5:
                out.add((x, y))
    return out


def mshift(mask, dx, dy):
    return {(x + dx, y + dy) for (x, y) in mask}


def fill(img, mask, c):
    for (x, y) in mask:
        px(img, x, y, c)


def cel(img, mask, base, sh=(), hi=(), sdir=(1, 1)):
    """Cel-shade a mask.  sh / hi are [(depth, colour), ...] nearest-the-edge first:
    a pixel takes a shadow tone when the shape ends within `depth` px on the side
    away from the light, a highlight tone when it ends within `depth` px toward it."""
    def run(x, y, dx, dy, cap):
        k = 1
        while k <= cap and (x + dx * k, y + dy * k) in mask:
            k += 1
        return k
    smax = max([d for d, _ in sh], default=0); hmax = max([d for d, _ in hi], default=0)
    for (x, y) in mask:
        c = base
        ds = run(x, y, sdir[0], sdir[1], smax) if sh else 99
        dl = run(x, y, -sdir[0], -sdir[1], hmax) if hi else 99
        done = False
        for d, col in sh:
            if ds <= d:
                c = col; done = True; break
        if not done:
            for d, col in hi:
                if dl <= d:
                    c = col; break
        px(img, x, y, c)


BLUSH = hexc("#f09a84")
HAIR_HI = mix(HR[3], OR[5], 0.35)


FACE_CMAP = {
    "n": INK[0], "E": INK[2], "e": NV[1], "B": NV[3], "W": WHITE, "w": ST[7], "g": ST[6],
    "h": HR[1], "H": HR[0], "m": OR[1], "M": OR[0], "t": WHITE, "T": ST[6], "r": RD[3], "R": RD[2],
    "s": SK[3], "S": SK[4], "d": SK[2], "D": SK[1], "b": BLUSH, "c": CY[5], "C": CY[3],
}
# Jake's eyes: big shiny beads, like the sprite's 2x2 eyes scaled up
J_EYE = [
    ".HHHH.",
    ".EEEE.",
    ".WWEE.",
    ".WWEE.",
    ".EEEB.",
    ".EEBB.",
    "..EE..",
]
J_EYE_WORRY = [          # wide, whites showing, small pupils
    "..HH..",
    ".wwww.",
    "wwEEww",
    "wwEEww",
    ".wwww.",
    "..gg..",
    "......",
]
J_EYE_HAPPY = [          # closed, smiling arcs
    "......",
    "......",
    ".HHHH.",
    "HH..HH",
    "H....H",
    "......",
    "......",
]


def portrait_jake(expr="neutral"):
    img = new(PW, PH)
    # ---- backpack peeking behind the near shoulder -----------------------
    pack = rmask(3, 33, 13, 47, 2)
    cel(img, pack, ST[3], sh=[(1, ST[1]), (2, ST[2])], hi=[(1, ST[5])])
    pts(img, [(5, 37), (5, 38)], CY[4])
    # ---- flight suit shoulders ----------------------------------------------
    suit = pmask([(5, 47), (6, 43), (9, 40), (16, 38), (32, 38), (39, 40), (42, 43), (43, 47)])
    cel(img, suit, OR[3], sh=[(1, OR[1]), (3, OR[2])], hi=[(1, OR[5]), (2, OR[4])])
    # ---- neck ---------------------------------------------------------------
    neck = rmask(20, 33, 30, 41, 1)
    fill(img, neck, SK[2])
    fill(img, {(x, y) for (x, y) in neck if y <= 37}, SK[1])
    # ---- collar ---------------------------------------------------------------
    collar = pmask([(15, 39), (19, 37), (25, 42), (31, 37), (35, 39), (33, 42), (25, 46), (17, 42)])
    cel(img, collar, WHITE, sh=[(1, ST[5]), (2, ST[6])])
    seg(img, [(25, 43), (25, 47)], OR[1])
    # chest light
    fill(img, rmask(33, 43, 36, 45), CY[4]); px(img, 33, 43, CY[6]); px(img, 36, 45, CY[3])
    # shoulder strap
    seg(img, [(11, 40), (13, 47)], ST[2]); seg(img, [(12, 40), (14, 47)], ST[4])
    # ---- face -----------------------------------------------------------------
    face = emask(26.5, 25.0, 11.5, 11.5, n=2.25)
    cel(img, face, SK[3], sh=[(1, SK[2]), (2, SK[2])], hi=[])
    # ---- hair: dark under-mass, then chunky tufts on top ------------------------
    hair = pmask([(12, 31), (9, 28), (7, 23), (7, 16), (9, 11), (8, 8), (11, 8), (13, 5), (15, 6), (17, 3),
                  (20, 4), (22, 1), (25, 1), (27, 3), (30, 2), (33, 3), (34, 5), (37, 6), (39, 9), (41, 9),
                  (40, 12), (41, 17), (17, 18), (16, 22), (15, 30), (14, 32)])
    cel(img, hair, HR[2], sh=[(1, HR[0]), (3, HR[1])], hi=[(1, HR[3])])
    tufts = [
        [(7, 16), (8, 9), (13, 6), (15, 9), (13, 14), (9, 20)],
        [(12, 9), (13, 5), (17, 3), (21, 5), (20, 10), (15, 13)],
        [(19, 6), (22, 1), (26, 1), (28, 5), (26, 10), (21, 11)],
        [(26, 5), (30, 2), (34, 4), (35, 8), (32, 11), (27, 10)],
        [(33, 6), (37, 6), (41, 9), (40, 13), (35, 12)],
    ]
    for t in tufts:
        cel(img, pmask(t) & hair, HR[2], sh=[(1, HR[1])], hi=[(1, HAIR_HI), (2, HR[3])])
    # side lock behind the ear
    cel(img, pmask([(7, 17), (12, 17), (14, 24), (14, 31), (12, 31), (9, 28), (7, 23)]) & hair, HR[2],
        sh=[(1, HR[0]), (2, HR[1])], hi=[(1, HR[3])])
    # cast shadows: under the goggles, and beside the side hair
    fill(img, {(x, y) for (x, y) in face if y in (19, 20) and (x, y) not in hair}, SK[2])
    fill(img, {(x, y) for (x, y) in face if x in (16, 17) and y > 20 and (x, y) not in hair}, SK[2])
    # ---- ear ---------------------------------------------------------------------
    ear = emask(14.5, 25.5, 2.2, 3.2)
    fill(img, ear, SK[3]); pts(img, [(14, 24), (14, 25), (15, 26), (14, 27)], SK[2]); pts(img, [(13, 23), (13, 24)], SK[4])
    # sideburn tuft over the ear top
    fill(img, pmask([(13, 18), (18, 18), (17, 23), (15, 22), (14, 23)]), HR[2])
    pts(img, [(17, 22), (17, 21), (14, 22)], HR[1])
    # ---- goggles pushed up on the forehead -------------------------------------
    strap = rmask(6, 12, 41, 16, 1)
    cel(img, strap & (hair | face), ST[3], sh=[(1, ST[1])], hi=[(1, ST[5])], sdir=(0, 1))
    for (x0, x1) in ((13, 25), (28, 39)):
        frame = rmask(x0, 9, x1, 18, 3)
        cel(img, frame, ST[4], sh=[(1, ST[1]), (2, ST[2])], hi=[(1, ST[6])])
        lens = rmask(x0 + 2, 11, x1 - 2, 16, 2)
        cel(img, lens, CY[4], sh=[(1, CY[2]), (2, CY[3])], hi=[(1, CY[5])])
        seg(img, [(x0 + 3, 14), (x0 + 5, 12)], CY[6]); seg(img, [(x0 + 5, 15), (x0 + 8, 12)], CY[6])
    fill(img, rmask(26, 12, 27, 14), ST[2])
    # fringe wisps poking out under the goggles
    fill(img, pmask([(34, 19), (38, 19), (37, 21)]), HR[2])
    pts(img, [(37, 21), (38, 20)], HR[1])
    pts(img, [(18, 19), (19, 19), (18, 20)], HR[2])
    # ---- features ---------------------------------------------------------------
    ex0, ex1, ey = 18, 29, 22
    if expr == "neutral":
        stamp(img, J_EYE, ex0, ey, FACE_CMAP); stamp(img, J_EYE, ex1, ey, FACE_CMAP)
        seg(img, [(19, 20), (22, 20)], HR[1]); seg(img, [(30, 20), (33, 20)], HR[1])
        pts(img, [(23, 32), (24, 33), (25, 33), (26, 33), (27, 33), (28, 32)], OR[1])
        pts(img, [(25, 34), (26, 34)], SK[2])
    elif expr == "happy":
        stamp(img, J_EYE_HAPPY, ex0, ey, FACE_CMAP); stamp(img, J_EYE_HAPPY, ex1, ey, FACE_CMAP)
        mouth = pmask([(22, 30), (30, 30), (29, 33), (27, 35), (25, 35), (23, 33)])
        fill(img, mouth, OR[0])
        fill(img, {(x, y) for (x, y) in mouth if y == 31 and 23 <= x <= 29}, WHITE)
        fill(img, {(x, y) for (x, y) in mouth if y >= 33}, RD[3])
        pts(img, [(22, 30), (30, 30)], OR[1])
    else:
        stamp(img, J_EYE_WORRY, ex0, ey, FACE_CMAP); stamp(img, J_EYE_WORRY, ex1, ey, FACE_CMAP)
        seg(img, [(18, 21), (22, 20)], HR[1]); seg(img, [(30, 20), (34, 21)], HR[1])
        fill(img, rmask(23, 31, 29, 33), OR[1]); fill(img, rmask(24, 32, 28, 32), WHITE)
        pts(img, [(26, 32)], ST[6])
        # sweat drop
        pts(img, [(36, 21), (36, 22), (37, 22), (36, 23), (37, 23)], CY[5]); px(img, 36, 22, WHITE)
    # nose and cheeks
    pts(img, [(27, 29), (28, 30), (27, 30)], SK[2]); px(img, 26, 28, SK[4])
    for (cx, cy) in ((19, 30), (34, 30)):
        pts(img, [(cx, cy), (cx + 1, cy), (cx + 2, cy), (cx, cy + 1), (cx + 1, cy + 1), (cx + 2, cy + 1)], BLUSH)
    return outline(img)


P_BLUSH = mix(SK[2], RD[3], 0.4)
P_CMAP = dict(FACE_CMAP)
P_CMAP.update({"s": SK[2], "S": SK[3], "d": SK[1], "D": SK[0], "e": HR[2], "b": P_BLUSH, "l": RD[2], "L": RD[1]})
P_EYE = [
    "nnnnn.",
    ".EEEE.",
    ".EEWW.",
    ".eEEW.",
    "..eE..",
    "......",
]
P_EYE_SMILE = [
    ".nnnn.",
    "nEEEEn",
    ".EEWW.",
    ".eEEE.",
    "......",
    "......",
]


def portrait_priya(expr="neutral"):
    """Drawn facing right with the light from the top-RIGHT, then flipped so she
    faces left (like her sprite) with the light back on the top-left."""
    img = new(PW, PH)
    L = (-1, 1)            # shadow direction before the flip
    # ---- uniform ------------------------------------------------------------
    suit = pmask([(3, 47), (4, 43), (8, 40), (16, 38), (33, 38), (40, 40), (44, 43), (45, 47)])
    cel(img, suit, CY[3], sh=[(1, CY[1]), (3, CY[2])], hi=[(1, CY[4])], sdir=L)
    for x0 in (7, 36):
        fill(img, rmask(x0, 40, x0 + 4, 41), GD[3]); px(img, x0 + 4, 40, GD[4]); px(img, x0, 41, GD[2])
    for k in range(3):
        px(img, 33 + k * 2, 44, GD[3])
    # ---- neck ---------------------------------------------------------------
    neck = rmask(22, 33, 30, 42, 1)
    fill(img, neck, SK[1])
    fill(img, {(x, y) for (x, y) in neck if y <= 37}, SK[0])
    # ---- stand collar ----------------------------------------------------------
    collar = pmask([(18, 40), (21, 37), (26, 41), (31, 37), (35, 40), (33, 43), (26, 46), (19, 43)])
    cel(img, collar, CY[2], sh=[(1, CY[1])], hi=[(1, CY[5])], sdir=(0, 1))
    seg(img, [(26, 42), (26, 47)], CY[1])
    px(img, 26, 43, GD[3])
    # ---- back hair + bun (behind the head) ----------------------------------------
    bun = emask(9.5, 8.5, 5.0, 5.0)
    cel(img, bun, HR[0], hi=[(1, HR[2]), (2, HR[1])], sdir=L)
    seg(img, [(8, 7), (10, 10)], HR[1])
    # ---- face -----------------------------------------------------------------
    face = emask(27.0, 24.5, 10.5, 12.5, n=2.05)
    cel(img, face, SK[2], sh=[(1, SK[1])], sdir=L)
    # ---- hair: sleek, swept back to the bun ---------------------------------------
    hair = pmask([(14, 32), (11, 28), (9, 22), (9, 15), (11, 10), (15, 6), (20, 4), (22, 3), (30, 3), (32, 4), (34, 6),
                  (36, 9), (37, 13), (34, 12), (30, 12), (26, 12), (22, 14), (19, 17), (18, 21),
                  (17, 25), (16, 32)])
    cel(img, hair, HR[0], hi=[(1, HR[2]), (3, HR[1])], sdir=L)
    # strands pulled back toward the bun, and a sheen band
    for s in ([(26, 10), (20, 9), (15, 11)], [(31, 9), (24, 6), (18, 7)], [(21, 14), (15, 15), (12, 18)],
              [(17, 20), (13, 22)], [(12, 25), (14, 28)]):
        seg(img, s, HR[1])
    for s in ([(26, 7), (30, 7), (33, 9)],):
        seg(img, s, HR[2])
    pts(img, [(28, 6), (29, 6)], HR[3])
    # hair tie
    pts(img, [(13, 10), (14, 9), (13, 11)], CY[4]); px(img, 14, 10, CY[2])
    # hair shadow on the forehead
    fill(img, (mshift(hair, 0, 1) & face) - hair, SK[1])
    # ---- ear + earring ------------------------------------------------------------
    ear = emask(16.0, 25.5, 2.0, 3.0)
    fill(img, ear, SK[2]); pts(img, [(16, 24), (16, 25), (15, 26), (16, 27)], SK[1]); pts(img, [(17, 23), (17, 24)], SK[3])
    fill(img, rmask(15, 29, 16, 30), GD[3]); px(img, 16, 29, GD[5])
    # ---- features -------------------------------------------------------------------
    if expr == "neutral":
        stamp(img, P_EYE, 19, 22, P_CMAP); stamp(img, P_EYE, 29, 22, P_CMAP)
        # level near brow, far brow arched: the appraising "go on, then" look
        seg(img, [(19, 20), (24, 20)], HR[0])
        pts(img, [(29, 20), (30, 19), (31, 19), (32, 19), (33, 19), (34, 20)], HR[0])
        seg(img, [(25, 33), (30, 33)], RD[1]); seg(img, [(26, 34), (29, 34)], RD[2])
        px(img, 31, 32, RD[1])
    else:
        stamp(img, P_EYE_SMILE, 19, 22, P_CMAP); stamp(img, P_EYE_SMILE, 29, 22, P_CMAP)
        seg(img, [(19, 20), (20, 19), (24, 19)], HR[0]); seg(img, [(29, 19), (33, 19), (34, 20)], HR[0])
        pts(img, [(24, 32), (31, 32)], RD[1])
        seg(img, [(25, 33), (30, 33)], WHITE); seg(img, [(25, 34), (30, 34)], RD[1]); seg(img, [(26, 35), (29, 35)], RD[2])
        for (cx, cy) in ((20, 29), (33, 29)):
            pts(img, [(cx, cy), (cx + 1, cy), (cx + 2, cy), (cx + 1, cy + 1), (cx, cy + 1)], P_BLUSH)
    pts(img, [(28, 29), (27, 30), (28, 30)], SK[1]); px(img, 29, 28, SK[3])
    return flip_h(outline(img))


# ---- the Fraction Phantom ---------------------------------------------------------
def holo(c, a):
    return (c[0], c[1], c[2], a)


def portrait_phantom(glitch=False):
    """Bust of the Fraction Phantom, matching the 96px sprite: periwinkle hood with a
    curled tip, pointed dark opening rimmed in cyan, slab eyes, mantle, quarter emblem."""
    img = new(PW, PH)
    A = 232
    # ---- body: fraction bars inside the cloak ----------------------------------------
    body = pmask([(7, 38), (41, 38), (42, 47), (6, 47)])
    fill(img, body, holo(NV[1], 175))
    for (y0, n, lit) in ((41, 4, (1, 0, 0, 1)), (45, 8, (0, 1, 1, 0, 1, 0, 1, 1))):
        x0, x1 = 9, 39
        w = x1 - x0 + 1
        for k in range(n):
            sx0 = x0 + round(k * w / n); sx1 = x0 + round((k + 1) * w / n) - 2
            for y in range(y0, min(PH, y0 + 3)):
                for x in range(sx0, sx1 + 1):
                    if lit[k]:
                        c = holo(CY[5], 235) if y == y0 else holo(CY[3], 225) if (x == sx1 or y == y0 + 2) else holo(CY[4], 225)
                    else:
                        c = holo(NV[3], 215) if y == y0 else holo(PU[1], 215)
                    img.putpixel((x, y), c)
    # cloak edge lines with number-line ticks
    for y in range(39, 48):
        img.putpixel((6, y), holo(CY[4], 235)); img.putpixel((42, y), holo(CY[2], 235))
        if y % 3 == 1:
            img.putpixel((7, y), holo(CY[5], 235)); img.putpixel((8, y), holo(CY[4], 200))
    # ---- mantle ---------------------------------------------------------------------------
    mantle = pmask([(11, 31), (37, 31), (42, 33), (45, 36), (46, 39), (41, 40), (7, 40), (2, 39), (3, 36), (6, 33)])
    for (x, y) in mantle:
        c = NV[4] if x + y // 2 < 34 else NV[3] if x + y // 2 < 48 else NV[2] if x + y // 2 < 57 else PU[2]
        top = min(yy for (xx, yy) in mantle if xx == x)
        bot = max(yy for (xx, yy) in mantle if xx == x)
        if y == top:
            c = NV[5] if x < 31 else NV[4] if x < 40 else NV[3]
        elif y == bot:
            c = NV[1] if x < 39 else PU[1]
        elif y == bot - 1 and x % 4 == 1:
            c = CY[4]                                  # number-line ticks along the hem
        img.putpixel((x, y), holo(c, A))
    # ---- hood -------------------------------------------------------------------------------
    tip = pmask([(24, 5), (19, 2), (13, 1), (10, 2), (10, 4), (15, 5), (18, 9)])
    hood = emask(25.0, 18.5, 13.5, 14.5, n=2.2) | tip
    hood = {(x, y) for (x, y) in hood if y <= 32}
    cel(img, hood, holo(NV[3], A), sh=[(2, holo(PU[2], A)), (5, holo(NV[2], A))],
        hi=[(1, holo(NV[5], A)), (3, holo(NV[4], A))])
    for (x, y) in tip:
        if x < 19:
            top = min(yy for (xx, yy) in tip if xx == x); bot = max(yy for (xx, yy) in tip if xx == x)
            img.putpixel((x, y), holo(NV[5] if y == top else NV[2] if y == bot and bot > top else NV[4], A))
    # hologram scan banding
    up = {NV[2][:3]: NV[3], NV[3][:3]: NV[4], NV[4][:3]: NV[5], NV[5][:3]: NV[6], PU[2][:3]: PU[3]}
    for (x, y) in hood:
        if y % 4 == 1:
            c = img.getpixel((x, y))
            if c[:3] in up:
                img.putpixel((x, y), holo(up[c[:3]], A))
    # tip curl highlight
    pts(img, [(11, 2), (12, 2), (13, 2)], holo(NV[6], A))
    # ---- hood opening: pointed arch of darkness with a cyan rim --------------------------------
    hole = pmask([(25, 9), (20, 13), (17, 18), (16, 23), (17, 28), (20, 31), (30, 31), (33, 28), (34, 23),
                  (33, 18), (30, 13)])
    rim = set()
    for (x, y) in hole:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in hole:
                rim.add((x + dx, y + dy))
    for (x, y) in hole:
        img.putpixel((x, y), holo(INK[1] if y > 25 and (x + y) % 2 == 0 else INK[0], 250))
    for (x, y) in rim:
        img.putpixel((x, y), holo(CY[5] if (x < 25 and y < 22) else CY[4] if y < 28 else CY[3], 245))
    # ---- eyes: two calm bright slabs ---------------------------------------------------------------
    EY = ["WWWWWW.", "WWWWWWW", ".CCCCCC", "..cccc."]
    em = {"W": WHITE, "C": CY[4], "c": CY[2]}
    le = ascii_sprite(EY, em)
    paste(img, le, 17, 20); paste(img, flip_h(le), 27, 20)
    # ---- emblem: a circle with one quarter missing ----------------------------------------------------
    ecx, ecy = 24.5, 40.5
    for y in range(32, 48):
        for x in range(16, 34):
            dx, dy = x - ecx, y - ecy
            d2 = dx * dx + dy * dy
            if d2 <= 7.0 * 7.0:
                c = INK[0]
                if d2 <= 6.0 * 6.0:
                    if dx > 0 and dy < 0:
                        c = INK[2]
                    elif abs(dx) < 1 or abs(dy) < 1:
                        c = NV[4]                       # dividing lines
                    else:
                        c = WHITE if (dy < 0 or dx < 0) and y % 3 != 0 else ST[7] if dy < 0 or dx < 0 else NV[6]
                img.putpixel((x, y), c)
    seg(img, [(26, 36), (29, 39)], PK[2]); px(img, 25, 35, PK[1])
    # a couple of stray glitch pixels
    pts(img, [(13, 28), (14, 28)], holo(PK[2], 235)); px(img, 36, 12, holo(PU[4], 235)); px(img, 40, 43, holo(PK[2], 235))
    img = outline(img, holo(INK[0], 255))
    if glitch:
        img = glitch_tear(img)
    return img


def glitch_tear(src):
    """Horizontal tearing with pink ghosts for the 'glitch' portrait."""
    img = src.copy()
    bands = [(5, 7, 4), (13, 14, -3), (19, 22, 5), (27, 28, -2), (33, 35, -5), (41, 42, 3)]
    for (y0, y1, dx) in bands:
        for y in range(y0, y1 + 1):
            row = [src.getpixel((x, y)) for x in range(PW)]
            for x in range(PW):
                sx = x - dx
                img.putpixel((x, y), row[sx] if 0 <= sx < PW else T)
            # pink ghost of the band, offset the other way
            for x in range(PW):
                sx = x + dx
                c = row[sx] if 0 <= sx < PW else T
                if c[3] and img.getpixel((x, y))[3] == 0:
                    img.putpixel((x, y), holo(PK[3] if y == y0 else PU[3] if (y - y0) % 2 else PK[2], 210))
    # corrupted pixels: pink scan specks and one eye gone pink
    for (x, y) in ((9, 10), (10, 10), (38, 25), (39, 25), (37, 30), (12, 37), (30, 44), (31, 44)):
        if img.getpixel((x, y))[3]:
            img.putpixel((x, y), holo(PK[3], 240))
    p = img.load()
    for y in range(19, 25):
        for x in range(26, 44):
            if p[x, y][:3] == WHITE[:3]:
                p[x, y] = PK[4]
            elif p[x, y][:3] == CY[4][:3]:
                p[x, y] = PK[2]
    return img


PORTRAIT_NAMES = ["jake_neutral", "jake_happy", "jake_worried", "priya_neutral", "priya_smile",
                  "phantom_neutral", "phantom_glitch"]


def build_portraits():
    return [portrait_jake("neutral"), portrait_jake("happy"), portrait_jake("worried"),
            portrait_priya("neutral"), portrait_priya("smile"),
            portrait_phantom(False), portrait_phantom(True)]


# =============================================================================
# preview helpers
# =============================================================================
def strip_preview(frames, name, scale=8, bg="#2b3f7e", cols=None):
    sh = sheet(frames, cols=cols or len(frames))
    preview(sh, name, scale=scale, bg=bg, grid=frames[0].size)


def mock_scene(skin, name, crawler, drone, priya, portraits):
    """Drop the cast into a little room built from the real tiles to judge them in context."""
    til = Image.open(os.path.join(ASSETS, f"tiles/tiles_{skin}.png")).convert("RGBA")
    Wt, Ht = 30, 14
    solid = [[0] * Wt for _ in range(Ht)]
    for x in range(Wt):
        for y in range(11, Ht):
            solid[y][x] = 1
    for x in range(19, 26):
        solid[7][x] = 1
    img = new(Wt * 16, Ht * 16, hexc("#05060c"))

    def tile(i):
        return til.crop(((i % 16) * 16, (i // 16) * 16, (i % 16) * 16 + 16, (i // 16) * 16 + 16))

    def sol(x, y):
        if x < 0 or x >= Wt or y < 0 or y >= Ht:
            return 1
        return solid[y][x]
    for y in range(Ht):
        for x in range(Wt):
            t = 48 + (1 if (x + y) % 5 == 0 else 2 if y % 6 == 2 else 0)
            if y == 5 and x > 3:
                t = 51
            if x in (9, 17) and y < 11:
                t = 56
            if y == 9 and x in (4, 13, 27):
                t = 67
            img.alpha_composite(tile(t), (x * 16, y * 16))
    for y in range(Ht):
        for x in range(Wt):
            if not solid[y][x]:
                continue
            m = sol(x, y - 1) * 1 + sol(x + 1, y) * 2 + sol(x, y + 1) * 4 + sol(x - 1, y) * 8
            t = m
            if m == 15:
                t = 16
            if m == 14 and x % 7 == 3:
                t = 20
            img.alpha_composite(tile(t), (x * 16, y * 16))
    gy = 11 * 16
    jk = Image.open(os.path.join(ASSETS, "sprites/jake.png")).convert("RGBA")
    img.alpha_composite(jk.crop((0, 0, 32, 32)), (40, gy - 31))
    img.alpha_composite(priya[0], (76, gy - 31))
    img.alpha_composite(priya[7], (112, gy - 31))
    img.alpha_composite(jk.crop((32, 32, 64, 64)), (150, gy - 31))
    for k, fr in enumerate((0, 2, 4)):
        img.alpha_composite(crawler[fr], (196 + k * 34, gy - 23))
    img.alpha_composite(flip_h(crawler[1]), (300, gy - 23))
    img.alpha_composite(crawler[6], (330, gy - 23))
    img.alpha_composite(crawler[7], (360, gy - 23))
    img.alpha_composite(crawler[3], (330, 7 * 16 - 23))
    img.alpha_composite(drone[0], (200, 60)); img.alpha_composite(drone[3], (240, 40))
    img.alpha_composite(drone[6], (280, 70)); img.alpha_composite(drone[9], (420, 60))
    img.alpha_composite(flip_h(drone[1]), (130, 50))
    # dialogue-box mock: portraits on the dark UI panel colour
    panel = new(7 * 56 + 8, 56, hexc("#141a3a", 235))
    for i, p in enumerate(portraits):
        panel.alpha_composite(p, (8 + i * 56, 4))
    img.alpha_composite(panel, (40, 2))
    preview(img, name, scale=3, bg="#05060c")


def build():
    crawler = build_crawler()
    drone = build_drone()
    priya_r = build_priya()
    priya = [flip_h(f) for f in priya_r]          # saved sheet faces LEFT
    portraits = build_portraits()

    save(sheet(crawler, cols=9), "sprites/crawler.png")
    save(sheet(drone, cols=11), "sprites/drone.png")
    save(sheet(priya, cols=10), "sprites/priya.png")
    save(sheet(portraits, cols=7), "sprites/portraits.png")

    manifest("cast", {"sheets": {
        "crawler": {"file": "sprites/crawler.png", "fw": 24, "fh": 24, "anims": {
            "walk": {"frames": [0, 1, 2, 3, 4, 5], "fps": 10, "loop": True},
            "squash": {"frames": [6, 7, 8], "fps": 14, "loop": False}}},
        "drone": {"file": "sprites/drone.png", "fw": 24, "fh": 24, "anims": {
            "hover": {"frames": [0, 1, 2, 3, 4, 5], "fps": 10, "loop": True},
            "alert": {"frames": [6, 7], "fps": 8, "loop": True},
            "pop": {"frames": [8, 9, 10], "fps": 14, "loop": False}}},
        "priya": {"file": "sprites/priya.png", "fw": 32, "fh": 32, "anims": {
            "idle": {"frames": [0, 1, 2, 3, 4, 5], "fps": 5, "loop": True},
            "talk": {"frames": [6, 7, 8, 9], "fps": 8, "loop": True}}},
        "portraits": {"file": "sprites/portraits.png", "fw": 48, "fh": 48,
                      "names": {n: i for i, n in enumerate(PORTRAIT_NAMES)}},
    }})

    # ---- previews ---------------------------------------------------------------
    strip_preview(crawler, "cast_crawler.png", scale=10, cols=5)
    strip_preview(drone, "cast_drone.png", scale=10, cols=6)
    jk = Image.open(os.path.join(ASSETS, "sprites/jake.png")).convert("RGBA").crop((0, 0, 32, 32))
    strip_preview([flip_h(jk)] + priya[:5], "cast_priya_a.png", scale=10, bg="#47566f", cols=6)
    strip_preview(priya[5:] + [flip_h(jk)], "cast_priya_b.png", scale=10, bg="#47566f", cols=6)
    strip_preview(portraits[:3], "cast_portraits_a.png", scale=10, bg="#1e2a5a", cols=3)
    strip_preview(portraits[3:], "cast_portraits_b.png", scale=10, bg="#1e2a5a", cols=4)
    # game-size check: everything at 2x on dark and light grounds
    strip_preview([crawler[0], crawler[3], drone[0], drone[6]], "cast_zoom_bots.png", scale=16, cols=4)
    strip_preview([priya[0], priya[4], priya[6], priya[9]], "cast_zoom_priya.png", scale=14, bg="#47566f", cols=4)
    strip_preview([portraits[3], portraits[5]], "cast_portraits_zoom.png", scale=16, bg="#1e2a5a", cols=2)
    strip_preview([portraits[0], portraits[1]], "cast_portraits_zoom2.png", scale=16, bg="#1e2a5a", cols=2)
    strip_preview([portraits[4], portraits[6]], "cast_portraits_zoom3.png", scale=16, bg="#1e2a5a", cols=2)
    preview(sheet(portraits, cols=7), "cast_portraits_2x.png", scale=2, bg="#141a3a")
    preview(sheet(portraits, cols=7), "cast_portraits_2x_light.png", scale=2, bg="#b9c7d6")
    allspr = new(24 * 11, 24 * 2 + 32)
    allspr.alpha_composite(sheet(crawler, cols=9), (0, 0)); allspr.alpha_composite(sheet(drone, cols=11), (0, 24))
    allspr.alpha_composite(sheet(priya, cols=10).crop((0, 0, 24 * 11, 32)), (0, 48))
    preview(allspr, "cast_sprites_2x.png", scale=2, bg="#1b2547")
    for skin in ("dock", "reactor", "zerog"):
        mock_scene(skin, f"cast_mock_{skin}.png", crawler, drone, priya, portraits)
    return crawler, drone, priya, portraits


if __name__ == "__main__":
    build()
    print("cast: crawler 9 frames, drone 11, priya 10, portraits 7")
