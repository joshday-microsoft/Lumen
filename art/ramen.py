"""A big steaming bowl of ramen, painted LIVE on the wall stroke by stroke.

The stroke order IS the show: dark room first, then the bowl thrown top-down,
broth poured into it, noodles laid in, toppings placed one by one, and finally
the steam curling up off the surface into the dark.

Run:  .venv\\Scripts\\python.exe art\\ramen.py [delay_seconds]
      .venv\\Scripts\\python.exe art\\ramen.py --preview      (render only)
"""

import json
import math
import random
import sys
import urllib.request

SIZE = 32

# bowl geometry
CX = 16.0
RIM_Y = 17.0          # centre of the rim ellipse
RIM_RX, RIM_RY = 14.0, 5.0
BROTH_RX, BROTH_RY = 11.5, 3.6
BODY_RY = 14.0        # how far the bowl belly falls below the rim

# palette
BG_TOP = (28, 19, 17)
BG_BOT = (12, 9, 9)
CERAMIC = (176, 54, 40)
CERAMIC_DARK = (104, 30, 24)
CERAMIC_LIT = (216, 88, 66)
BAND = (238, 226, 206)
BROTH_MID = (218, 162, 88)
BROTH_EDGE = (168, 112, 54)
NOODLE = (244, 214, 140)
NOODLE_SHADE = (206, 168, 92)
NORI = (22, 50, 42)
NORI_LIT = (46, 84, 68)
EGG_WHITE = (248, 240, 226)
YOLK = (246, 150, 48)
YOLK_LIT = (252, 198, 92)
SCALLION = (86, 176, 74)
SCALLION_LIT = (146, 218, 116)
STEAM = (236, 231, 226)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def bg_at(y):
    return lerp(BG_TOP, BG_BOT, y / (SIZE - 1))


def in_broth(x, y):
    return ((x - CX) / BROTH_RX) ** 2 + ((y - RIM_Y) / BROTH_RY) ** 2 <= 1.0


def in_rim(x, y):
    return ((x - CX) / RIM_RX) ** 2 + ((y - RIM_Y) / RIM_RY) ** 2 <= 1.0


def in_body(x, y):
    if y < RIM_Y:
        return False
    t = (y - RIM_Y) / BODY_RY
    if t > 1.0:
        return False
    return abs(x - CX) <= RIM_RX * math.sqrt(1.0 - t * t)


def build_strokes():
    steps = []
    rng = random.Random(717)

    # 1. the dark room — serpentine wash, warm charcoal fading down
    for y in range(SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        c = bg_at(y)
        for x in row:
            steps.append((x, y, c))

    # 2. the bowl, thrown top-down: base coat over rim ring + belly
    bowl = [
        (x, y)
        for y in range(SIZE)
        for x in range(SIZE)
        if (in_rim(x, y) or in_body(x, y)) and not in_broth(x, y)
    ]
    for x, y in sorted(bowl, key=lambda p: (p[1], abs(p[0] - CX))):
        steps.append((x, y, CERAMIC))

    # 3. shading pass — light rakes in from the upper left, belly darkens down
    for x, y in bowl:
        t = (y - RIM_Y + RIM_RY) / (BODY_RY + RIM_RY)
        side = (x - CX) / RIM_RX
        if side < -0.35 and t < 0.75:
            c = lerp(CERAMIC_LIT, CERAMIC, min(1.0, t * 1.6 + abs(side) * 0.3))
        else:
            c = lerp(CERAMIC, CERAMIC_DARK, max(0.0, t * 0.95 + side * 0.25))
        steps.append((x, y, c))

    # 4. the cream band around the rim — the bowl's one bit of decoration
    for x, y in sorted(bowl, key=lambda p: p[0]):
        if in_rim(x, y):
            continue
        t = (y - RIM_Y) / BODY_RY
        if 0.30 <= t <= 0.44:
            steps.append((x, y, BAND if x % 5 != 4 else lerp(BAND, CERAMIC_DARK, 0.35)))

    # 5. rim lip: pale where it catches the light, dark on the far side
    lip = []
    for y in range(SIZE):
        for x in range(SIZE):
            if in_rim(x, y) and not in_broth(x, y):
                lip.append((x, y))
    for x, y in sorted(lip, key=lambda p: p[0]):
        near = y < RIM_Y
        c = lerp(BAND, CERAMIC_DARK, 0.15 if near else 0.55)
        steps.append((x, y, c))

    # 6. pour the broth — serpentine, hot in the middle, deeper at the edges
    broth = [(x, y) for y in range(SIZE) for x in range(SIZE) if in_broth(x, y)]
    for y in sorted({p[1] for p in broth}):
        row = [p for p in broth if p[1] == y]
        row.sort(key=lambda p: p[0], reverse=(y % 2 == 1))
        for x, _ in row:
            d = math.hypot((x - CX) / BROTH_RX, (y - RIM_Y) / BROTH_RY)
            steps.append((x, y, lerp(BROTH_MID, BROTH_EDGE, min(1.0, d))))

    # 7. noodles — three wavy strands laid in left to right
    for i, (base, amp, phase) in enumerate(((15.4, 1.15, 0.0), (17.0, 1.0, 2.1), (18.4, 0.8, 4.0))):
        for x in range(6, 27):
            y = base + amp * math.sin(x * 0.62 + phase)
            yi = int(round(y))
            if in_broth(x, yi):
                steps.append((x, yi, NOODLE))
                if in_broth(x, yi + 1):
                    steps.append((x, yi + 1, NOODLE_SHADE))

    # 8. nori sheet standing in the broth, left side
    for x in range(7, 10):
        for y in range(13, 19):
            if in_broth(x, y):
                steps.append((x, y, NORI))
    for x, y in ((7, 13), (8, 14), (7, 16), (9, 13)):
        if in_broth(x, y):
            steps.append((x, y, NORI_LIT))

    # 9. the soft-boiled egg, halved, right of centre
    ecx, ecy = 22.6, 16.4
    egg = [
        (x, y)
        for y in range(12, 21)
        for x in range(18, 28)
        if ((x - ecx) / 3.1) ** 2 + ((y - ecy) / 2.5) ** 2 <= 1.0
    ]
    for x, y in sorted(egg, key=lambda p: (p[1], p[0])):
        steps.append((x, y, EGG_WHITE))
    for x, y in egg:
        if ((x - ecx) / 1.7) ** 2 + ((y - ecy) / 1.35) ** 2 <= 1.0:
            steps.append((x, y, YOLK))
    for x, y in ((22, 16), (22, 15), (23, 16)):
        steps.append((x, y, YOLK_LIT))

    # 10. scallions scattered last, the way they land on top
    spots = [(x, y) for x, y in broth if not (17 <= x <= 27 and 13 <= y <= 20) and x > 10]
    rng.shuffle(spots)
    for i, (x, y) in enumerate(spots[:11]):
        steps.append((x, y, SCALLION if i % 3 else SCALLION_LIT))

    # 11. steam — three wisps curling up off the broth, breaking apart as they climb
    for sx, phase, sway in ((11.5, 0.4, 1.6), (16.5, 2.6, 2.1), (21.0, 4.4, 1.4)):
        for y in range(11, -1, -1):
            rise = (11 - y) / 11.0
            if rng.random() < rise * 0.55:       # the trail comes apart up high
                continue
            x = sx + sway * math.sin(y * 0.55 + phase) * (0.35 + rise)
            xi = int(round(x))
            if not (0 <= xi < SIZE):
                continue
            fade = 0.45 + 0.5 * rise             # never opaque; thins as it climbs
            steps.append((xi, y, lerp(STEAM, bg_at(y), fade)))
            if rise < 0.3 and xi + 1 < SIZE:     # only just off the broth is it thick
                steps.append((xi + 1, y, lerp(STEAM, bg_at(y), fade + 0.3)))

    return steps


def render(steps, path, scale=1):
    from PIL import Image

    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for x, y, c in steps:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = tuple(int(v) for v in c)
    if scale > 1:
        img = img.resize((SIZE * scale, SIZE * scale), Image.NEAREST)
    img.save(path)
    return img


if __name__ == "__main__":
    steps = build_strokes()
    args = sys.argv[1:]

    if "--preview" in args:
        render(steps, "art/ramen.png")
        render(steps, "tmp/ramen-preview.png", scale=12)
        print(f"{len(steps)} strokes -> art/ramen.png, tmp/ramen-preview.png")
        sys.exit(0)

    delay = float(args[0]) if args else 0.02
    render(steps, "art/ramen.png")
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay, "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued")
