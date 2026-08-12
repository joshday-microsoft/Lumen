"""Jackpot — one big slot machine, three reels, and the three seconds that pay.

An original loop for the Lumen wall. The panel IS the machine's face, cropped
the way you'd actually see it standing at one: arched marquee with five bulbs,
a chrome-framed glass window filling the middle with three cream drums behind
it, payline pointers on both edges, and the payout tray along the bottom.

The organising rule is that SPEED is the only thing drawn. Every reel pixel is
an exposure: the shutter is open for 0.75 of a frame and the strip is averaged
over the distance it travels in that time. Nothing else changes. At full spin
that average collapses a column of symbols into flat horizontal bands (which is
exactly what a spinning drum looks like), and as a reel decelerates the same
integral narrows until the symbols snap into focus on their own. Legibility is
the speedometer — there is no separate "blurred" and "sharp" drawing code, and
no fake smear. (The hummingbird taught the other half of that lesson: a soft
translucent smear over a subject is unreadable at 32px. Here the blur is 1D and
axis-aligned, so it lands as crisp bands instead of mush.)

The reels stop left to right onto three sevens, each with a real settle bounce,
the marquee detonates, coins jump out of the tray, and the drums are already
rolling again by the time the loop wraps.

Seamlessness is structural: the strip is periodic with a 60px repeat, so the
loop closes iff each reel's total travel over 18 frames is an exact multiple of
60. Each reel's spin speed is solved by bisection to make that true, and the
last frame is rendered and asserted pixel-identical to the first.

Run:  .venv\\Scripts\\python.exe art\\jackpot.py   -> jackpot.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
SS = 3                                  # spatial supersample
FRAMES = 14
DURATION_MS = 120
SHUTTER = 0.75                          # fraction of a frame the shutter is open

# ------------------------------------------------------------------ palette ---
# Deliberately a BRIGHT piece: the last six entries in the ledger have been dark
# rooms, deep space, slate and dusk. A slot machine is chrome and cherry red
# under its own bulbs, and the cream drums keep the middle of the panel light.
ROOM = (14, 12, 20)
FLOOR = (26, 22, 32)
CAB = (152, 30, 40)
CAB_DK = (96, 18, 26)
CAB_HI = (198, 58, 60)
MARQUEE = (72, 14, 22)
CHROME = (188, 196, 210)
CHROME_DK = (104, 112, 130)
CHROME_HI = (240, 244, 252)
BULB_ON = (255, 224, 130)
BULB_HOT = (255, 252, 226)
BULB_OFF = (116, 74, 44)
TRAY = (26, 20, 26)
TRAY_LIP = (150, 156, 170)

DRUM = (228, 222, 202)                  # cream drum face
GLASS_DK = (150, 148, 140)              # inner shadow under the bezel

SEVEN = (226, 44, 52)
SEVEN_HI = (255, 108, 96)
SEVEN_EDGE = (112, 14, 22)
CHERRY = (208, 36, 48)
CHERRY_HI = (255, 140, 130)
CHERRY_EDGE = (104, 14, 22)
STEM = (72, 150, 60)
LEAF = (108, 186, 70)
GOLD = (244, 186, 58)
GOLD_HI = (255, 226, 130)
GOLD_EDGE = (140, 88, 20)
LEMON = (242, 214, 66)
LEMON_HI = (255, 240, 150)
GEM = (66, 146, 238)
GEM_HI = (168, 216, 255)
GEM_EDGE = (24, 62, 128)
GLOW = (255, 206, 96)                   # the win light, additive

# ----------------------------------------------------------------- geometry ---
CAB_X0, CAB_X1, CAB_Y0 = 1.0, 31.0, 0.5
ARCH_R = 5.0
BULBS = [(5.4, 3.4), (10.7, 2.6), (16.0, 2.3), (21.3, 2.6), (26.6, 3.4)]
BULB_R = 1.15

WIN = (2.0, 30.0, 6.0, 27.0)            # outer chrome bezel
BEZEL = 1.5
IN_X0, IN_X1 = WIN[0] + BEZEL, WIN[1] - BEZEL
IN_Y0, IN_Y1 = WIN[2] + BEZEL, WIN[3] - BEZEL
PAY_Y = 0.5 * (IN_Y0 + IN_Y1)           # 16.5

GAP = 0.6
REEL_W = ((IN_X1 - IN_X0) - 2 * GAP) / 3.0
REELS = [(IN_X0 + i * (REEL_W + GAP), IN_X0 + i * (REEL_W + GAP) + REEL_W) for i in range(3)]

PITCH = 10.0                            # strip repeat per symbol
NSYM = 6
STRIP = PITCH * NSYM                    # 60 px — the loop's period
SYM_SS_X, SYM_SS_Y = 3, 6               # strip is prerendered at this resolution

# strip order per reel. Seven sits at index 0 on all three, so "stopped on a
# seven" is simply p == 0 (mod 60) for every reel — one condition, no per-reel
# bookkeeping. The rest of each order differs so the drums read as three
# separate objects while they blur.
ORDERS = [
    ["seven", "cherry", "bar", "lemon", "bell", "gem"],
    ["seven", "bar", "bell", "cherry", "gem", "lemon"],
    ["seven", "gem", "lemon", "bar", "cherry", "bell"],
]

# --------------------------------------------------------------- choreography ---
# t 0-2      all three drums at full blur     t 9-12   the win: marquee flash,
# t 2-4      reel 0 eases down and settles             bloom, coins out of the
# t 4-6      reel 1                                    tray
# t 6.2-8.6  reel 2 (the long hold — the last t 12.5-14 the drums are already
#            reel is always the slow one)              rolling again
DECEL = [(2.0, 4.0), (4.0, 6.0), (6.2, 8.6)]
RELAUNCH = (12.5, 14.0)
BOUNCE_A = 0.85                         # px of settle overshoot
BOUNCE_W = 1.2                          # windowed to exactly zero after this
FLASH = {9: 0.45, 10: 1.00, 11: 0.50, 12: 0.85}
COIN_FRAMES = (10, 11, 12, 13)


def vel(i, t, v0):
    """Speed of reel i at time t, in px/frame. Position is its integral."""
    a, b = DECEL[i]
    r0, r1 = RELAUNCH
    if t < a:
        return v0
    if t < b:
        u = (t - a) / (b - a)
        return v0 * (1.0 - u) ** 2       # ease-out: area = v0*(b-a)/3
    if t < r0:
        return 0.0
    if t < r1:
        return v0 * (t - r0) / (r1 - r0)  # spun back up for the next play
    return v0


def bounce(i, t):
    """The settle. A drum does not stop dead — it overshoots and rocks back.

    Windowed to EXACTLY zero after BOUNCE_W frames, not merely small: anything
    that leaks past the end of the loop breaks the closure assertion.
    """
    b = DECEL[i][1]
    d = t - b
    if d < 0.0 or d >= BOUNCE_W:
        return 0.0
    w = (1.0 - d / BOUNCE_W) ** 2
    return BOUNCE_A * w * math.sin(2.0 * math.pi * d / 0.95)


_INT_STEPS = 4000
_INT = {}


def _integral(i, v0):
    """Cumulative travel of reel i, sampled on a fine grid over one loop."""
    key = (i, round(v0, 9))
    if key in _INT:
        return _INT[key]
    dt = FRAMES / _INT_STEPS
    acc = [0.0]
    s = 0.0
    for k in range(_INT_STEPS):
        t0 = k * dt
        s += 0.5 * (vel(i, t0, v0) + vel(i, t0 + dt, v0)) * dt
        acc.append(s)
    _INT[key] = acc
    return acc


def travel(i, t, v0):
    acc = _integral(i, v0)
    u = max(0.0, min(float(FRAMES), t)) / FRAMES * _INT_STEPS
    k = int(u)
    if k >= _INT_STEPS:
        return acc[_INT_STEPS] + vel(i, FRAMES, v0) * (t - FRAMES)
    f = u - k
    return acc[k] * (1.0 - f) + acc[k + 1] * f


def solve_speed(i, target):
    """Pick reel i's spin speed so its travel over the loop is EXACTLY `target`.

    target is a multiple of the 60px strip repeat, which is what makes frame 18
    identical to frame 0. Travel is monotonic in v0, so bisection is exact.
    """
    lo, hi = 1.0, 60.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if travel(i, FRAMES, mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# reel 0 stops first and so travels least; each gets the multiple of 60 nearest
# its natural distance, which keeps all three spin speeds within a third of
# each other (they read as three drums, not three different machines)
TARGETS = [60.0, 120.0, 120.0]
V0 = [solve_speed(i, TARGETS[i]) for i in range(3)]
# phase: the stop lands on p == 0 (mod 60) => seven centred on the payline
P0 = [(-travel(i, DECEL[i][1], V0[i])) % STRIP for i in range(3)]


def pos(i, t):
    return P0[i] + travel(i, t, V0[i]) + bounce(i, t)


# ------------------------------------------------------------------ symbols ---
def sdf_rect(u, v, cx, cy, hw, hh):
    return max(abs(u - cx) - hw, abs(v - cy) - hh)


def sdf_circle(u, v, cx, cy, r):
    return math.hypot(u - cx, v - cy) - r


def sdf_seg(u, v, ax, ay, bx, by, r):
    vx, vy = bx - ax, by - ay
    tt = ((u - ax) * vx + (v - ay) * vy) / (vx * vx + vy * vy)
    tt = max(0.0, min(1.0, tt))
    return math.hypot(u - (ax + vx * tt), v - (ay + vy * tt)) - r


def sdf_ellipse(u, v, cx, cy, rx, ry):
    return (math.hypot((u - cx) / rx, (v - cy) / ry) - 1.0) * min(rx, ry)


def sym_seven(u, v):
    d = min(sdf_rect(u, v, 4.0, 1.75, 2.85, 0.85),
            sdf_seg(u, v, 5.9, 2.0, 3.2, 7.0, 1.05))
    if d < -0.55:
        return SEVEN_HI if v < 1.9 else SEVEN
    if d < 0.15:
        return SEVEN_EDGE
    return None


def sym_cherry(u, v):
    for a, b in (((4.3, 1.0), (2.5, 3.9)), ((4.3, 1.0), (5.8, 4.3))):
        if sdf_seg(u, v, a[0], a[1], b[0], b[1], 0.42) < 0.0:
            return STEM
    if sdf_ellipse(u, v, 6.0, 1.5, 1.6, 0.72) < 0.0:
        return LEAF
    for cx, cy, r in ((2.5, 5.5, 1.85), (5.8, 5.9, 1.65)):
        d = sdf_circle(u, v, cx, cy, r)
        if d < -0.5:
            if math.hypot(u - (cx - 0.55), v - (cy - 0.6)) < 0.5:
                return CHERRY_HI
            return CHERRY
        if d < 0.15:
            return CHERRY_EDGE
    return None


def sym_bar(u, v):
    d = sdf_rect(u, v, 4.0, 4.0, 3.15, 1.55)
    corner = math.hypot(max(0.0, abs(u - 4.0) - 2.55), max(0.0, abs(v - 4.0) - 0.95)) - 0.6
    d = max(d, corner) if abs(u - 4.0) > 2.55 and abs(v - 4.0) > 0.95 else d
    if d < -0.5:
        if abs(v - 4.0) < 0.28:
            return GOLD_EDGE                    # the seam across the ingot
        return GOLD_HI if v < 4.0 else GOLD
    if d < 0.15:
        return GOLD_EDGE
    return None


def _bell_w(v):
    if v < 1.5 or v > 5.7:
        return -1.0
    return 1.05 + 2.15 * ((v - 1.5) / 4.2) ** 1.7


def sym_bell(u, v):
    if sdf_circle(u, v, 4.0, 6.85, 0.85) < 0.0:
        return GOLD if abs(u - 4.0) > 0.35 else GOLD_HI      # clapper
    if 5.6 <= v <= 6.25 and abs(u - 4.0) < 3.25:
        return GOLD_EDGE if (v > 6.0 or abs(u - 4.0) > 2.95) else GOLD
    w = _bell_w(v)
    if w > 0.0:
        du = abs(u - 4.0)
        top = sdf_circle(u, v, 4.0, 3.55, 2.15)
        inside = du < w or top < 0.0
        edge = (w - du < 0.55) or (-0.5 < top < 0.15 and v < 3.55)
        if inside:
            if edge:
                return GOLD_EDGE
            return GOLD_HI if u < 3.5 else GOLD
    return None


def sym_lemon(u, v):
    if sdf_ellipse(u, v, 5.6, 1.9, 1.5, 0.7) < 0.0:
        return LEAF
    for nx in (1.0, 6.9):
        if sdf_circle(u, v, nx, 4.7, 0.6) < 0.0:
            return GOLD_EDGE
    d = sdf_ellipse(u, v, 3.95, 4.7, 3.0, 2.15)
    if d < -0.45:
        return LEMON_HI if (u - 3.95) + (v - 4.7) < -1.6 else LEMON
    if d < 0.12:
        return GOLD_EDGE
    return None


def sym_gem(u, v):
    d = abs(u - 4.0) / 2.9 + abs(v - 4.3) / 3.3 - 1.0
    if d < -0.10:
        if math.hypot(u - 2.95, v - 3.0) < 0.55:
            return GEM_HI
        if abs(v - 3.1) < 0.28:
            return GEM_EDGE                     # table facet line
        return GEM_HI if v < 3.1 else GEM
    if d < 0.06:
        return GEM_EDGE
    return None


SYMS = {"seven": sym_seven, "cherry": sym_cherry, "bar": sym_bar,
        "bell": sym_bell, "lemon": sym_lemon, "gem": sym_gem}


def build_strip(order):
    """Prerender one drum's 60px repeat at (3x, 6x) so sampling is a lookup."""
    w = int(round(8 * SYM_SS_X))
    h = int(round(STRIP * SYM_SS_Y))
    rows = []
    for iy in range(h):
        v_strip = (iy + 0.5) / SYM_SS_Y
        k = int(v_strip // PITCH) % NSYM
        v_local = v_strip - k * PITCH - (PITCH - 8.0) / 2.0
        fn = SYMS[order[k]]
        row = []
        for ix in range(w):
            u_local = (ix + 0.5) / SYM_SS_X
            col = None
            if 0.0 <= v_local < 8.0:
                col = fn(u_local, v_local)
            row.append(col if col is not None else DRUM)
        rows.append(row)
    return rows


STRIPS = [build_strip(o) for o in ORDERS]
_SW = int(round(8 * SYM_SS_X))
_SH = int(round(STRIP * SYM_SS_Y))


# -------------------------------------------------------------------- scene ---
def cab_dist(x, y):
    """Signed distance into the cabinet (>0 inside). Arched top corners."""
    d = min(x - CAB_X0, CAB_X1 - x, y - CAB_Y0)
    if y < CAB_Y0 + ARCH_R:
        if x < CAB_X0 + ARCH_R:
            d = min(x - CAB_X0, y - CAB_Y0,
                    ARCH_R - math.hypot(x - (CAB_X0 + ARCH_R), y - (CAB_Y0 + ARCH_R)))
        elif x > CAB_X1 - ARCH_R:
            d = min(CAB_X1 - x, y - CAB_Y0,
                    ARCH_R - math.hypot(x - (CAB_X1 - ARCH_R), y - (CAB_Y0 + ARCH_R)))
    return d


def bulb_state(t, k):
    """0 = dark, 1 = lit, 2 = blown out. Periodic in FRAMES by construction."""
    tt = int(t) % FRAMES
    if tt in FLASH:
        if FLASH[tt] >= 0.85:
            return 2
        return 1 if (k + tt) % 2 == 0 else 0
    return 1 if (k - tt) % 3 == 0 else 0            # a chase while it spins


def coin_pos(t):
    """Gold jumping out of the tray on the win. Empty (and so periodic) by 17."""
    tt = int(t) % FRAMES
    if tt not in COIN_FRAMES:
        return []
    age = tt - COIN_FRAMES[0]
    out = []
    for k, (x0, vx, vy, lag) in enumerate(((11.0, -1.35, -4.3, 0),
                                           (15.0, 0.35, -5.1, 0),
                                           (19.5, 1.45, -4.0, 1),
                                           (13.0, -0.55, -4.7, 2),
                                           (21.5, 1.9, -3.4, 2))):
        a = age - lag
        if a < 0 or a > 3:
            continue
        out.append((x0 + vx * a, 29.2 + vy * a + 1.15 * a * a))
    return out


def reel_sample(x, y, rows_cache):
    """One exposure sample of whichever drum owns column x (already integrated)."""
    for i, (rx0, rx1) in enumerate(REELS):
        if rx0 <= x < rx1:
            ix = int((x - rx0) / REEL_W * _SW)
            ix = max(0, min(_SW - 1, ix))
            rows = rows_cache[i]
            if not rows:
                return None
            r = g = b = 0
            for row in rows:
                c = STRIPS[i][row][ix]
                r += c[0]
                g += c[1]
                b += c[2]
            n = len(rows)
            return (r / n, g / n, b / n)
    return CHROME_DK                                    # divider between drums


def drum_shade(y):
    """The drums are cylinders: the face curves away top and bottom.

    Banded into four steps on purpose — a smooth ramp over an 18px window is
    hundreds of near-unique values re-encoded in every one of 18 full frames,
    and it costs more than the animation does (chameleon/gulp lesson).
    """
    u = min(1.0, abs(y - PAY_Y) / 9.0)
    return 1.0 - 0.36 * (int(u * u * 3.0 + 0.5) / 3.0)


def scene(x, y, t, rows_cache):
    """Base colour at (x,y) before the win bloom. Returns (rgb, part).

    part: 0 = the room around the machine, 1 = cabinet, 2 = behind the glass.
    The win light treats those three differently, which is what keeps the
    machine a SHAPE while it is blazing.
    """
    d = cab_dist(x, y)
    if d <= 0.0:
        return (FLOOR if y > 29.5 else ROOM), 0

    col = CAB
    if d < 0.7:
        col = CAB_HI if y < 6.0 else CAB_DK             # lit top edge, dark sides

    # marquee
    if 1.1 < y < 5.6:
        if d > 0.7:
            col = MARQUEE
        for k, (bx, by) in enumerate(BULBS):
            rr = math.hypot(x - bx, y - by)
            st = bulb_state(t, k)
            if rr < BULB_R:
                col = (BULB_HOT if st == 2 else BULB_ON) if st else BULB_OFF
            elif rr < BULB_R + 0.5 and st:
                col = BULB_ON if st == 2 else BULB_OFF

    # window: chrome bezel, then glass
    if WIN[0] <= x <= WIN[1] and WIN[2] <= y <= WIN[3]:
        bd = min(x - WIN[0], WIN[1] - x, y - WIN[2], WIN[3] - y)
        col = CHROME if bd > 0.55 else CHROME_DK
        if bd > 1.05:
            col = CHROME_HI if y < WIN[2] + 1.2 else CHROME
    if IN_X0 <= x < IN_X1 and IN_Y0 <= y < IN_Y1:
        s = reel_sample(x, y, rows_cache)
        if s is None:
            s = DRUM
        k = drum_shade(y)
        edge = min(y - IN_Y0, IN_Y1 - y, x - IN_X0, IN_X1 - x)
        if edge < 0.6:
            k *= 0.72                                   # glass shadow at the frame
        col = (s[0] * k, s[1] * k, s[2] * k)
        return col, 2

    # payline pointers — the machine tells you which row it is paying
    for px in (WIN[0] + 0.9, WIN[1] - 0.9):
        if abs(x - px) < 0.9 and abs(y - PAY_Y) < 1.5 - abs(x - px) * 1.1:
            col = GOLD

    # lower cabinet: chrome lip, then the payout tray
    if 27.0 < y < 28.0:
        col = CHROME if y < 27.6 else CHROME_DK
    if 8.0 < x < 24.0 and 28.6 < y < 30.9:
        col = TRAY
        if y < 29.0 or abs(x - 8.0) < 0.5 or abs(x - 24.0) < 0.5:
            col = TRAY_LIP

    return col, 1


# ------------------------------------------------------------------- render ---
GLOW_STEP = 0.4


def render(t):
    # exposure: sample each drum's position across the open shutter once per
    # frame, then every pixel in that column averages the same rows
    caches = []
    for i in range(3):
        p0 = pos(i, t)
        p1 = pos(i, t + SHUTTER)
        n = max(1, min(28, int(abs(p1 - p0) * 2.2)))
        caches.append([p0 + (p1 - p0) * (k + 0.5) / n for k in range(n)])

    n = SIZE * SS
    acc = [[0.0, 0.0, 0.0] for _ in range(SIZE * SIZE)]
    glass = [0.0] * (SIZE * SIZE)
    room = [0.0] * (SIZE * SIZE)
    for py in range(n):
        y = (py + 0.5) / SS
        # precompute the strip rows each drum contributes at this scanline
        rows_cache = []
        for i in range(3):
            rows_cache.append([int(((p + y - PAY_Y) % STRIP) * SYM_SS_Y) % _SH
                               for p in caches[i]])
        for px in range(n):
            x = (px + 0.5) / SS
            col, part = scene(x, y, t, rows_cache)
            i = (py // SS) * SIZE + (px // SS)
            acc[i][0] += col[0]
            acc[i][1] += col[1]
            acc[i][2] += col[2]
            glass[i] += 1.0 if part == 2 else 0.0
            room[i] += 1.0 if part == 0 else 0.0

    q = float(SS * SS)
    amp = FLASH.get(int(t) % FRAMES, 0.0)
    img = Image.new("RGB", (SIZE, SIZE))
    for py in range(SIZE):
        for px in range(SIZE):
            i = py * SIZE + px
            r, g, b = (c / q for c in acc[i])
            if amp > 0.0:
                # the win light: banded, and brightest at the marquee it comes
                # from, so it reads as the machine lighting up rather than the
                # image being turned up. The ROOM gets only a quarter of it —
                # bloom the surround at full strength and the cabinet's edge
                # meets the wall at the same value, which costs the piece its
                # silhouette exactly when it is meant to be most alive.
                k = amp * (1.0 - 0.45 * min(1.0, py / 26.0))
                k += amp * 0.35 * (glass[i] / q)
                k *= 1.0 - 0.75 * (room[i] / q)
                k = int(min(1.6, k) / GLOW_STEP) * GLOW_STEP
                r += GLOW[0] * k * 0.34
                g += GLOW[1] * k * 0.34
                b += GLOW[2] * k * 0.34
            img.putpixel((px, py), (min(255, int(r + 0.5)),
                                    min(255, int(g + 0.5)),
                                    min(255, int(b + 0.5))))

    for cx, cy in coin_pos(t):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = int(cx) + dx, int(cy) + dy
                if 0 <= x < SIZE and 0 <= y < SIZE:
                    rr = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                    if rr < 0.85:
                        img.putpixel((x, y), GOLD_HI if rr < 0.45 else GOLD)
                    elif rr < 1.25:
                        img.putpixel((x, y), GOLD_EDGE)
    return img


# --------------------------------------------------------------------- main ---
def detail(img, i):
    """Vertical high-frequency energy in reel i's window — the focus meter."""
    x0, x1 = int(REELS[i][0] + 0.9), int(REELS[i][1] - 0.5)
    s = 0
    for x in range(x0, x1):
        for y in range(int(IN_Y0) + 1, int(IN_Y1) - 1):
            a = img.getpixel((x, y))
            b = img.getpixel((x, y + 1))
            s += sum(abs(a[c] - b[c]) for c in range(3))
    return s


def off_strip(p):
    """Distance from p to the nearest whole strip repeat — never 59.999."""
    r = p % STRIP
    return min(r, STRIP - r)


def main():
    for i in range(3):
        got = travel(i, FRAMES, V0[i])
        assert abs(got - TARGETS[i]) < 1e-4, f"reel {i} travel {got}"
        assert off_strip(pos(i, DECEL[i][1] + BOUNCE_W)) < 1e-3, \
            f"reel {i} did not settle on a seven ({pos(i, DECEL[i][1]) % STRIP:.3f})"
        assert off_strip(pos(i, FRAMES) - pos(i, 0)) < 1e-3, "loop does not close"
        print(f"  reel {i}: v0 {V0[i]:5.2f} px/frame, travel {got:6.1f}, stop @ t{DECEL[i][1]}")

    frames = [render(t) for t in range(FRAMES)]

    # the loop must close pixel-for-pixel, not approximately
    wrap = render(FRAMES)
    assert list(wrap.getdata()) == list(frames[0].getdata()), "frame 18 != frame 0"

    # focus is the story: each drum must be blurred while it spins and sharp
    # after it lands, and they must land left to right
    for i in range(3):
        spin = detail(frames[0], i)
        land = detail(frames[int(DECEL[i][1]) + 1], i)
        print(f"  reel {i}: detail spinning {spin:6d} -> landed {land:6d}")
        assert land > spin * 2.0, f"reel {i} never comes into focus"
    mid = 6
    assert detail(frames[mid], 0) > detail(frames[mid], 2) * 1.8, \
        "reel 2 is not still spinning when reel 0 has landed"

    keys = range(0, FRAMES, 2)
    strip = Image.new("RGB", (SIZE * 4 * len(keys) + (len(keys) - 1) * 4, SIZE * 4), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 4, SIZE * 4), Image.NEAREST), (i * (SIZE * 4 + 4), 0))
    strip.save(HERE / "jackpot.strip.png")
    hero = frames[10]
    hero.resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "jackpot-big.png")
    hero.save(HERE / "jackpot.png")

    import gifsafe

    def quant_error(colors):
        montage = Image.new("RGB", (SIZE * len(frames), SIZE))
        for i, f_ in enumerate(frames):
            montage.paste(f_, (i * SIZE, 0))
        pal = montage.quantize(colors=colors, dither=Image.Dither.NONE)
        got = list(montage.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB").getdata())
        want = list(montage.getdata())
        return sum((got[i][c] - want[i][c]) ** 2 for i in range(len(want)) for c in range(3)) / len(want)

    keep = [SEVEN, SEVEN_HI, SEVEN_EDGE, GOLD, GOLD_HI, BULB_HOT, GEM, CHERRY, LEMON]
    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "jackpot.gif", duration_ms=DURATION_MS,
                            colors=colors, keep=keep)
        err = quant_error(colors)
        print(f"  colors={colors:3d} -> {size} bytes, err {err:7.1f}")
        if size <= 8192 and (best is None or err < best[2]):
            best = (colors, size, err)
    assert best, "no palette fits the 8 KB budget"
    size = gifsafe.save(frames, HERE / "jackpot.gif", duration_ms=DURATION_MS,
                        colors=best[0], keep=keep)

    # the three sevens are the entire point and they are a few dozen red pixels
    # on five frames — exactly the profile median cut throws away
    enc = Image.open(HERE / "jackpot.gif")
    enc.seek(11)
    got = enc.convert("RGB")
    for i, (rx0, rx1) in enumerate(REELS):
        px = [got.getpixel((x, y)) for x in range(int(rx0) + 1, int(rx1))
              for y in range(int(PAY_Y) - 4, int(PAY_Y) + 4)]
        red = max(px, key=lambda c: c[0] - c[1])
        assert red[0] > 150 and red[0] - red[1] > 60, f"the encoder ate reel {i}'s seven: {red}"
    print(f"jackpot.gif: {len(frames)} frames, {best[0]} colors, {size} bytes (OK)")


if __name__ == "__main__":
    main()
