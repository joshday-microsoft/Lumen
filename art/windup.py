"""One big wind-up tin robot, painted LIVE on the wall stroke by stroke.

Big subject, minimal scene: a toy-shop spotlight, a shelf, and a single stubby
tin robot standing in it, filling the panel from antenna to feet. The stroke
ORDER is the show —

  1. backdrop wash (serpentine), warm pool of light behind him, shelf + shadow,
  2. the things BEHIND the body go down first: the brass wind-up key on his
     back-right, the antenna mast, then both spring arms coiled shoulder-outward
     and their claws,
  3. the whole robot is blocked in flat as a dark silhouette, from his chest
     outward, so he arrives as one shape before he becomes metal,
  4. then he is painted: torso band by band top-to-bottom, legs, feet, neck
     ribs, head, face plate, speaker grille, ear bolts, rivets,
  5. the chest gauge is glazed in — brass ring swept around, dial face from the
     middle out, ticks, needle, glass glint,
  6. and LAST he powers on: both eyes light, the glow bleeds onto the face
     plate, and the antenna bulb flares. Nothing before that moment is lit.

Everything is deterministic — no RNG, so the piece is reproducible.

Run (perform):  .venv\\Scripts\\python.exe art\\windup.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\windup.py preview  -> art\\windup.png
"""

import json
import math
import sys
import urllib.request

SIZE = 32
CX = 15.5                      # axis of symmetry

# ---------------------------------------------------------------- palette ---
BACK_FAR = (10, 14, 26)        # corners of the room
BACK_POOL = (58, 46, 62)       # warm pool of light behind him
SHELF_TOP = (68, 48, 34)
SHELF_BOT = (30, 21, 16)
SHADOW = (14, 10, 10)

BLOCK_IN = (18, 16, 22)        # flat silhouette coat

TIN_LIT = (198, 214, 230)      # torso / limbs
TIN_MID = (124, 140, 160)
TIN_DARK = (58, 70, 90)
TIN_EDGE = (28, 34, 48)

HEAD_LIT = (212, 226, 240)
HEAD_MID = (140, 156, 176)
HEAD_DARK = (68, 80, 100)

PLATE = (78, 90, 112)          # recessed face plate — must stay well above the
                               # grille, or the whole lower head reads as a hole
GRILLE = (22, 26, 38)

BRASS_LIT = (252, 210, 116)
BRASS = (212, 152, 46)
BRASS_DARK = (124, 82, 18)

DIAL_IN = (96, 60, 22)
DIAL_OUT = (38, 23, 10)
NEEDLE = (255, 238, 196)

EYE_SOCKET = (20, 24, 34)
EYE_GLOW = (255, 206, 96)
EYE_CORE = (255, 250, 224)
BULB = (255, 78, 58)
BULB_HOT = (255, 198, 176)

# ------------------------------------------------------------------ shape ---
HEAD = (10, 4, 21, 12)         # x0, y0, x1, y1
NECK = (13, 13, 18, 14)
TORSO = (9, 15, 22, 25)
LEGS = ((11, 26, 14, 29), (17, 26, 20, 29))
FEET = ((9, 30, 15, 31), (16, 30, 22, 31))
ARMS = ((6, 8), (23, 25))      # spring columns, x range each side
ARM_TOP, ARM_BOT = 16, 23
KEY_C, KEY_R = (28.5, 18.0), 3.0

GAUGE_C, GAUGE_R = (15.5, 20.2), 3.6
EYES = ((13.0, 7.8), (18.0, 7.8))      # r 1.75: they must not touch each other
EYE_R = 1.75                           # nor reach the grille two rows below


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def rrect(x0, y0, x1, y1, r):
    """Pixels of a rounded rectangle, reading order."""
    out = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = max(x0 + r - x, x - (x1 - r), 0)
            dy = max(y0 + r - y, y - (y1 - r), 0)
            if dx * dx + dy * dy <= r * r + 0.25:
                out.append((x, y))
    return out


def metal(x, y, box, lit, mid, dark):
    """Tin shading: light from the upper left, rim on top, shadow at the foot,
    plus one narrow specular streak so the plate reads as curved sheet."""
    x0, y0, x1, y1 = box
    t = (x - x0) / max(1, x1 - x0)
    c = lerp(lit, dark, min(1.0, t * 1.12 + 0.04) ** 0.85)
    if y == y0:                                    # top rim catches the lamp
        c = lerp(c, lit, 0.55)
    elif y >= y1 - 1:                              # sits in its own shadow
        c = lerp(c, TIN_EDGE, 0.45)
    if abs(t - 0.24) < 0.07:                       # specular streak
        c = lerp(c, lit, 0.5)
    return lerp(c, mid, 0.12)


def build_strokes():
    steps = []
    fb = {}

    def put(x, y, c):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            steps.append((x, y, c))
            fb[(x, y)] = c

    def under(x, y):
        return fb.get((x, y), BACK_FAR)

    def glaze(x, y, c, a):
        put(x, y, lerp(under(x, y), c, a))

    # -- 1. the room ---------------------------------------------------------
    for y in range(SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        for x in row:
            if y >= 29:                                   # shelf he stands on
                c = lerp(SHELF_TOP, SHELF_BOT, (y - 29) / 2.6)
            else:
                d = math.hypot((x - CX) / 1.15, y - 13.5)  # pool of lamplight
                c = lerp(BACK_POOL, BACK_FAR, min(1.0, (d / 19.0) ** 1.4))
            put(x, y, c)

    for y in range(29, SIZE):                             # cast shadow
        for x in range(SIZE):
            q = ((x - CX) / 13.5) ** 2 + ((y - 31.5) / 3.2) ** 2
            if q <= 1.0:
                glaze(x, y, SHADOW, 0.75 * (1.0 - q * 0.55))

    # -- 2. behind him: wind-up key, antenna mast, spring arms ---------------
    kx, ky = KEY_C
    for x in range(23, 27):                               # key shaft
        put(x, 18, BRASS_DARK if x < 25 else BRASS)
    ring = []
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - kx, y - ky)
            if 1.5 <= d <= KEY_R:
                ring.append((math.atan2(y - ky, x - kx), x, y, d))
    ring.sort()                                            # swept around
    for _, x, y, d in ring:
        shade = (x - kx) * -0.6 + (y - ky) * -0.8          # lit from upper left
        put(x, y, lerp(BRASS, BRASS_LIT if shade > 0 else BRASS_DARK, min(0.85, abs(shade) / 3.0)))

    for y in (3, 2):                                       # antenna mast, dark
        put(16, y, TIN_MID if y == 3 else TIN_DARK)

    for side, (ax0, ax1) in enumerate(ARMS):
        for i, y in enumerate(range(ARM_TOP, ARM_BOT + 1)):
            shove = 0 if i % 2 == 0 else (-1 if side == 0 else 1)
            for x in range(ax0 + shove, ax1 + shove + 1):
                c = TIN_MID if i % 2 == 0 else TIN_DARK
                put(x, y, lerp(c, TIN_LIT, 0.35) if x == ax0 + shove else c)
        hx0 = ax0 - 2 if side == 0 else ax0
        for x, y in ((hx0, 24), (hx0 + 1, 24), (hx0 + 2, 24), (hx0 + 3, 24),
                     (hx0, 25), (hx0 + 3, 25), (hx0, 26), (hx0 + 3, 26)):
            put(x, y, lerp(TIN_MID, TIN_LIT, 0.3) if y == 24 else TIN_DARK)

    # -- 3. block him in flat, from the chest outward ------------------------
    body = rrect(*HEAD, 2) + rrect(*NECK, 0) + rrect(*TORSO, 2)
    for leg in LEGS:
        body += rrect(*leg, 0)
    for foot in FEET:
        body += rrect(*foot, 1)
    body = sorted(set(body), key=lambda p: math.hypot(p[0] - CX, p[1] - 19))
    for x, y in body:
        put(x, y, BLOCK_IN)
    solid = set(body)

    # -- 4. paint the metal --------------------------------------------------
    for y in range(TORSO[1], TORSO[3] + 1):                # torso, band by band
        for x in range(TORSO[0], TORSO[2] + 1):
            if (x, y) in solid:
                c = metal(x, y, TORSO, TIN_LIT, TIN_MID, TIN_DARK)
                if y == 16:                                # chest-plate seam
                    c = lerp(c, TIN_EDGE, 0.4)
                if y >= 24:                                # hip band
                    c = lerp(c, TIN_DARK, 0.35)
                put(x, y, c)

    for leg in LEGS:
        for y in range(leg[1], leg[3] + 1):
            for x in range(leg[0], leg[2] + 1):
                c = metal(x, y, leg, TIN_LIT, TIN_MID, TIN_DARK)
                put(x, y, lerp(c, TIN_EDGE, 0.35) if y == 28 else c)   # knee
    for foot in FEET:
        for x, y in rrect(*foot, 1):
            c = metal(x, y, foot, TIN_LIT, TIN_MID, TIN_DARK)
            put(x, y, lerp(c, TIN_LIT, 0.45) if y == foot[1] else c)   # keep the
            # feet off the dark shelf — a shadowed foot just vanishes down there

    for y in (13, 14):                                     # neck ribs
        for x in range(NECK[0], NECK[2] + 1):
            c = metal(x, y, NECK, TIN_LIT, TIN_MID, TIN_DARK)
            put(x, y, c if y == 13 else lerp(c, TIN_EDGE, 0.45))

    for x, y in rrect(*HEAD, 2):                           # head, top down
        put(x, y, metal(x, y, HEAD, HEAD_LIT, HEAD_MID, HEAD_DARK))

    for x, y in rrect(11, 6, 20, 11, 1):                   # recessed face plate
        put(x, y, lerp(PLATE, TIN_EDGE, (y - 6) / 14.0))

    for x in range(13, 19):                                # speaker grille
        for y in (10, 11):
            put(x, y, GRILLE if x % 2 == 1 else lerp(TIN_MID, TIN_LIT, 0.2))

    for bx in (8, 22):                                     # ear bolts
        for x in range(bx, bx + 2):
            for y in (7, 8):
                put(x, y, BRASS_LIT if (x == bx and y == 7) else BRASS_DARK if y == 8 else BRASS)

    for x, y in ((10, 16), (21, 16), (10, 23), (21, 23), (11, 5), (20, 5)):
        put(x, y, lerp(TIN_LIT, (255, 255, 255), 0.25))    # rivets

    # -- 5. the chest gauge --------------------------------------------------
    gx, gy = GAUGE_C
    rim = []
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - gx, y - gy)
            if GAUGE_R - 1.15 <= d <= GAUGE_R:
                rim.append((math.atan2(y - gy, x - gx), x, y))
    rim.sort()
    for _, x, y in rim:
        shade = (x - gx) * -0.6 + (y - gy) * -0.8
        put(x, y, lerp(BRASS, BRASS_LIT if shade > 0 else BRASS_DARK, min(0.8, abs(shade) / 3.2)))

    face = []
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - gx, y - gy)
            if d < GAUGE_R - 1.15:
                face.append((d, x, y))
    face.sort()
    for d, x, y in face:
        put(x, y, lerp(DIAL_IN, DIAL_OUT, d / (GAUGE_R - 1.0)))

    for a in range(0, 360, 45):                            # ticks
        r = GAUGE_R - 1.7
        put(round(gx + r * math.cos(math.radians(a))),
            round(gy + r * math.sin(math.radians(a))), BRASS_LIT)
    for t in range(1, 5):                                  # needle, up and right
        r = t * 0.52
        put(round(gx + r * math.cos(math.radians(-52))),
            round(gy + r * math.sin(math.radians(-52))), NEEDLE)
    put(round(gx), round(gy), BRASS_LIT)                   # hub
    glaze(round(gx - 1.6), round(gy - 1.8), (255, 255, 255), 0.35)   # glass glint

    # -- 6. power on ---------------------------------------------------------
    for ex, ey in EYES:
        socket = []
        for y in range(SIZE):
            for x in range(SIZE):
                d = math.hypot(x - ex, y - ey)
                if d <= EYE_R:
                    socket.append((d, x, y))
        socket.sort(reverse=True)
        for d, x, y in socket:
            put(x, y, EYE_SOCKET if d > 1.25 else lerp(EYE_CORE, EYE_GLOW, min(1.0, d / 1.3)))
    for ex, ey in EYES:                                    # glow bleeds onto the plate
        for y in range(SIZE):
            for x in range(SIZE):
                d = math.hypot(x - ex, y - ey)
                if EYE_R < d <= 2.8 and (x, y) in solid:
                    glaze(x, y, EYE_GLOW, 0.22 * (2.8 - d))

    for x, y in ((15, 1), (16, 1), (15, 0), (16, 0)):      # antenna bulb flares
        put(x, y, BULB)
    put(15, 0, BULB_HOT)
    for x, y in ((15, 2), (16, 2)):
        glaze(x, y, BULB, 0.5)
    for x, y in ((12, 5), (11, 16), (10, 30)):             # last tin glints
        glaze(x, y, (255, 255, 255), 0.4)

    return steps, fb


def render_preview(fb, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for (x, y), c in fb.items():
        px[x, y] = c
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    steps, fb = build_strokes()
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(fb, "art/windup.png")
        print(f"{len(steps)} strokes")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.015
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay, "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued")
