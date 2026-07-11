"""A single koi fish, painted LIVE on the wall stroke by stroke — a zen piece.

The stroke ORDER is the performance:
  1. water wash   — serpentine teal sweep, top-lit, deepening downward
  2. koi body     — one big orange teardrop laid down spine-first (tail -> head)
  3. patches      — kohaku white blocks + a tancho red cap dabbed on
  4. fins & tail  — pale flowing fins, painted after the body they hang off
  5. eye          — the single detail that brings it alive
  6. ripples      — expanding rings + a rising bubble, the last quiet touches

Big subject, minimal scene: one large fish fills the panel, water is just mood.

Run (preview only):   .venv\\Scripts\\python.exe art\\koi.py
Run (perform live):   .venv\\Scripts\\python.exe art\\koi.py --perform [delay]
"""

import json
import math
import random
import sys
import urllib.request

SIZE = 32


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(int(v) for v in c))


# --- koi geometry -----------------------------------------------------------
# Spine runs from tail (lower-left) to head (upper-right) with a gentle arc.
def spine(t):
    cx = 6.0 + 20.0 * t
    cy = 24.0 - 15.0 * t - 3.0 * math.sin(math.pi * t)   # arcs upward
    return cx, cy


def half_width(t):
    # plump through the shoulder (t~0.6), tapering to a thin tail wrist
    bell = math.exp(-((t - 0.60) ** 2) / 0.055)
    return 1.1 + 4.6 * bell


def body_pixels():
    """Return {(x,y): 'role'} for the fish, role in body/back."""
    px = {}
    ts = [i / 240.0 for i in range(241)]
    for t in ts:
        cx, cy = spine(t)
        r = half_width(t)
        r2 = r * r
        y0, y1 = int(cy - r - 1), int(cy + r + 1)
        x0, x1 = int(cx - r - 1), int(cx + r + 1)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < SIZE and 0 <= y < SIZE:
                    d2 = (x - cx) ** 2 + (y - cy) ** 2
                    if d2 <= r2:
                        # "back" = upper half of the tube (lit side), for shading
                        role = "back" if (y - cy) < -0.25 * r else "body"
                        # head end keeps its fuller color regardless
                        prev = px.get((x, y))
                        if prev != "body":
                            px[(x, y)] = role
    return px


def build_strokes():
    steps = []
    body = body_pixels()

    # 1. WATER WASH — serpentine, top-lit teal fading to deep water
    for y in range(SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        base = lerp((26, 96, 112), (9, 40, 56), y / (SIZE - 1))
        for x in row:
            # faint diagonal light shafts for a sunlit-pond feel
            shimmer = 6 if ((x + y) % 9 == 0 and y < 18) else 0
            c = (base[0] + shimmer, base[1] + shimmer, base[2] + shimmer // 2)
            steps.append((x, y, c))

    # 2. KOI BODY — laid down spine order, tail -> head, so it "grows" forward
    ORANGE = (240, 120, 36)
    ORANGE_LIT = (252, 158, 70)
    order = sorted(body.keys(), key=lambda p: (p[0] + (24 - p[1])))  # tail(LL)->head(UR)
    for (x, y) in order:
        c = ORANGE_LIT if body[(x, y)] == "back" else ORANGE
        steps.append((x, y, c))

    # 3. PATCHES — kohaku white blocks + a tancho red cap
    rng = random.Random(7)
    white_zones = [(0.22, 0.34), (0.44, 0.56), (0.72, 0.82)]  # bands along spine
    whites = []
    for (x, y), _ in body.items():
        # map pixel to nearest spine t (coarse) to decide banding
        best_t, best_d = 0, 1e9
        for i in range(0, 25):
            t = i / 24.0
            sx, sy = spine(t)
            d = (x - sx) ** 2 + (y - sy) ** 2
            if d < best_d:
                best_d, best_t = d, t
        for lo, hi in white_zones:
            if lo <= best_t <= hi:
                whites.append((x, y))
                break
    rng.shuffle(whites)
    for (x, y) in whites:
        steps.append((x, y, (238, 238, 230)))

    # tancho red cap near the head/back
    hx_, hy_ = spine(0.90)
    for (x, y) in sorted(body.keys()):
        if (x - hx_) ** 2 + (y - hy_) ** 2 <= 4.2 and (y - hy_) <= 1:
            steps.append((x, y, (214, 44, 40)))

    # 4. FINS & TAIL — pale, translucent-looking, painted after the body
    tail_cx, tail_cy = spine(0.0)
    tail = [
        (-1, -3), (-2, -2), (-3, -2), (-1, -2), (-2, -1), (-3, -1),
        (-1, 2), (-2, 2), (-3, 3), (-1, 3), (-2, 4), (-3, 4), (-2, 0), (-3, 0),
    ]
    for dx, dy in tail:
        x, y = int(tail_cx + dx), int(tail_cy + dy)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            steps.append((x, y, (250, 196, 150)))
    # pectoral fin, hanging below the shoulder
    fx, fy = spine(0.6)
    for dx, dy in ((0, 3), (1, 3), (1, 4), (2, 4), (0, 4), (2, 5)):
        x, y = int(fx + dx - 1), int(fy + dy)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            steps.append((x, y, (250, 200, 156)))
    # dorsal fin ridge along the back
    for t in (0.5, 0.58, 0.66, 0.74):
        sx, sy = spine(t)
        r = half_width(t)
        x, y = int(sx), int(sy - r - 1)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            steps.append((x, y, (252, 170, 96)))

    # 5. EYE — the single detail that makes it a fish
    ex, ey = spine(0.955)
    ex, ey = int(ex), int(ey + 1)
    for dx, dy in ((0, 0),):
        steps.append((ex + dx, ey + dy, (18, 20, 28)))
    steps.append((ex, ey - 1, (240, 240, 240)))   # glint above the eye

    # 6. RIPPLES + a rising bubble — quiet finishing touches over the water
    rcx, rcy = 9, 7
    for rad in (3, 5, 7):
        for a in range(0, 360, 26):
            x = int(rcx + rad * math.cos(math.radians(a)))
            y = int(rcy + rad * 0.7 * math.sin(math.radians(a)))
            if 0 <= x < SIZE and 0 <= y < SIZE and (x, y) not in body:
                steps.append((x, y, (120, 178, 196)))
    for x, y in ((4, 20), (5, 16), (4, 12), (6, 9)):   # bubble trail
        if (x, y) not in body:
            steps.append((x, y, (170, 214, 224)))

    return steps


def render_preview(steps, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for x, y, c in steps:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = tuple(int(v) for v in c)
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"preview -> {path}  ({len(steps)} strokes)")


def perform(steps, delay):
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


if __name__ == "__main__":
    steps = build_strokes()
    render_preview(steps, "art/koi.png")
    if "--perform" in sys.argv:
        rest = [a for a in sys.argv[1:] if a != "--perform"]
        delay = float(rest[0]) if rest else 0.02
        perform(steps, delay)
