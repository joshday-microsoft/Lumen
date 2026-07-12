"""Phoenix Rising — painted LIVE on the wall, stroke by stroke.

One big firebird on a dark night sky. The stroke ORDER is the performance:
dark sky wash first, then the tail plumes trail in from behind, the two great
wings unfurl tip-to-shoulder, the body fills bottom-up, the head + crest flare
white-hot, and finally embers drift up around it.

Colour is a "heat" field — pixels near the spine burn white/gold, wing tips and
tail ends cool to deep ember red — so the whole bird reads as living fire.

Run (perform):  .venv\\Scripts\\python.exe art\\phoenix.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\phoenix.py --preview
"""

import json
import math
import random
import sys
import urllib.request

SIZE = 32
RNG = random.Random(717)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(v))) for v in c))


# --- heat palette: distance from the fire's core -> colour ---------------
WHITE = (255, 250, 214)
GOLD = (255, 214, 96)
ORANGE = (250, 138, 40)
EMBER = (196, 54, 22)

# spine points the fire radiates from (head down through the body)
SPINE = [(16.0, y) for y in range(6, 19)] + [(15.5, 15.0), (16.5, 15.0)]


def heat_color(x, y, jitter=0.0):
    d = min(math.hypot(x - sx, y - sy) for sx, sy in SPINE)
    d += jitter
    if d <= 1.4:
        c = lerp(WHITE, GOLD, (d) / 1.4)
    elif d <= 3.2:
        c = lerp(GOLD, ORANGE, (d - 1.4) / 1.8)
    elif d <= 5.4:
        c = lerp(ORANGE, EMBER, (d - 3.2) / 2.2)
    else:
        c = EMBER
    return c


# --- silhouette shapes ---------------------------------------------------
def rot_ellipse(x, y, cx, cy, rx, ry, ang):
    dx, dy = x - cx, y - cy
    ca, sa = math.cos(ang), math.sin(ang)
    xr = dx * ca + dy * sa
    yr = -dx * sa + dy * ca
    return (xr / rx) ** 2 + (yr / ry) ** 2 <= 1.0


def in_body(x, y):
    return rot_ellipse(x, y, 16, 14.2, 3.1, 5.0, 0.0)


def in_head(x, y):
    return math.hypot(x - 16, y - 7) <= 2.3


def in_wing_left(x, y):
    # shoulder ~(14,13) -> tip ~(2,6)
    return rot_ellipse(x, y, 8.0, 9.6, 7.1, 2.7, math.atan2(-7, -12))


def in_wing_right(x, y):
    return rot_ellipse(x, y, 24.0, 9.6, 7.1, 2.7, math.atan2(-7, 12))


def tail_pixels():
    """Three trailing plumes, base->tip order (drawn behind everything)."""
    plumes = [((16, 17), (16, 30)), ((16, 18), (11, 29)), ((16, 18), (21, 29))]
    pts = []
    for (x0, y0), (x1, y1) in plumes:
        steps = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(steps + 1):
            t = i / steps
            x = round(x0 + (x1 - x0) * t)
            y = round(y0 + (y1 - y0) * t)
            width = 2 if t < 0.45 else 1  # fat at the base, wispy at the tip
            for w in range(width):
                px = x + w
                if 0 <= px < SIZE and 0 <= y < SIZE and y >= 17:
                    pts.append((px, y))
    # de-dup preserving order
    seen, out = set(), []
    for p in pts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def build_strokes():
    steps = []          # ordered (x, y, color)
    painted = set()

    def put(x, y, c):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            steps.append((x, y, c))
            painted.add((x, y))

    # 1. night-sky wash — serpentine, deep indigo up top to near-black below
    for y in range(SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        base = lerp((26, 20, 54), (7, 6, 18), y / (SIZE - 1))
        for x in row:
            f = RNG.uniform(-4, 4)
            put(x, y, (base[0] + f, base[1] + f, base[2] + f * 1.5))

    # collect the firebird mask by region
    body_head = set()
    wings = set()
    for y in range(SIZE):
        for x in range(SIZE):
            if in_body(x, y) or in_head(x, y):
                body_head.add((x, y))
            elif in_wing_left(x, y) or in_wing_right(x, y):
                wings.add((x, y))

    # 2. tail plumes trail in from behind (base -> tip)
    for (x, y) in tail_pixels():
        if (x, y) in body_head:
            continue
        put(x, y, heat_color(x, y, RNG.uniform(-0.3, 0.6)))

    # 3. wings unfurl — tip first, sweeping toward the shoulders
    def wing_key(p):
        x, y = p
        shoulder = 14 if x < 16 else 18
        return -math.hypot(x - shoulder, y - 13)  # farthest (tip) first
    for (x, y) in sorted(wings, key=wing_key):
        put(x, y, heat_color(x, y, RNG.uniform(-0.3, 0.5)))

    # 4. body fills bottom-up
    body_only = sorted((p for p in body_head if not in_head(*p)),
                       key=lambda p: (-p[1], abs(p[0] - 16)))
    for (x, y) in body_only:
        put(x, y, heat_color(x, y, RNG.uniform(-0.4, 0.3)))

    # bright heart glow at the chest
    for (x, y) in ((16, 12), (15, 13), (16, 13), (17, 13), (16, 14)):
        put(x, y, WHITE)

    # 5. head + crest flare white-hot
    head_only = sorted((p for p in body_head if in_head(*p)), key=lambda p: p[1])
    for (x, y) in head_only:
        put(x, y, heat_color(x, y, RNG.uniform(-0.5, 0.2)))
    for (x, y, c) in ((16, 5, WHITE), (16, 4, GOLD),        # crest swept up-back
                      (17, 3, GOLD), (18, 3, ORANGE)):
        put(x, y, c)
    put(18, 7, (255, 170, 40))                              # beak spark

    # 6. embers drift up around the bird — the last, brightest strokes
    embers = []
    for _ in range(10):
        ex = RNG.randint(1, 30)
        ey = RNG.randint(1, 24)
        if (ex, ey) in painted and RNG.random() < 0.6:
            continue
        embers.append((ex, ey, RNG.choice([WHITE, GOLD, (255, 120, 40)])))
    embers.sort(key=lambda e: e[1])          # top-most sparks first
    for (x, y, c) in embers:
        put(x, y, c)

    return steps


def render_preview(steps, path, scale=14):
    from PIL import Image
    grid = [[(0, 0, 0)] * SIZE for _ in range(SIZE)]
    for x, y, c in steps:
        grid[y][x] = tuple(max(0, min(255, int(v))) for v in c)
    img = Image.new("RGB", (SIZE, SIZE))
    for y in range(SIZE):
        for x in range(SIZE):
            img.putpixel((x, y), grid[y][x])
    img.save(path[:-4] + "_32.png")  # true-size asset
    big = img.resize((SIZE * scale, SIZE * scale), Image.NEAREST)
    big.save(path)
    print(f"preview -> {path}  ({len(steps)} strokes)")


if __name__ == "__main__":
    if "--preview" in sys.argv:
        steps = build_strokes()
        render_preview(steps, "art/phoenix_preview.png")
    else:
        delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02
        steps = build_strokes()
        payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps],
                   "delay": delay, "clear": True}
        req = urllib.request.Request(
            "http://127.0.0.1:7788/paint",
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.read().decode())
        print(f"{len(steps)} strokes queued")
