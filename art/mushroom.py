"""A big storybook toadstool, painted LIVE on the wall stroke by stroke.

One large red-capped mushroom on a bright meadow — big subject, minimal scene.
The stroke ORDER is the show: sky wash, grass, the cream stem, then the red cap
BLOOMS open from its apex outward by distance, gills tucked under the rim, and
finally the white spots are dabbed on and a couple of grass tufts + a tiny flower.

Run (perform):  .venv\\Scripts\\python.exe art\\mushroom.py [delay_seconds]
Run (preview) :  .venv\\Scripts\\python.exe art\\mushroom.py preview   -> art\\mushroom.png
"""

import json
import math
import random
import sys
import urllib.request

SIZE = 32
GRASS_TOP = 25          # sky above, meadow below

# cap apex + per-row half-widths (a fat dome that curls in at the rim)
CAP_APEX = (16, 6)
CAP_ROWS = {
    6: 3, 7: 5, 8: 7, 9: 9, 10: 10,
    11: 11, 12: 12, 13: 12, 14: 12, 15: 11, 16: 11,
}
CAP_BOTTOM = 16
STEM_CX = 16


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def cap_color(x, y):
    """Red cap: bright highlight toward the upper-left light, shadow at the rim."""
    row_half = CAP_ROWS[y]
    edge = abs(x - CAP_APEX[0]) / max(row_half, 1)          # 0 center .. 1 rim
    # light from upper-left
    light = 1.0 - (0.55 * edge) - (0.28 * ((y - 6) / (CAP_BOTTOM - 6)))
    light += 0.18 * (1.0 if x < CAP_APEX[0] else -0.2)
    light = max(0.0, min(1.0, light))
    shadow = (150, 24, 34)
    base = (206, 42, 46)
    hi = (244, 96, 84)
    return lerp(shadow, hi, light) if light > 0.5 else lerp(shadow, base, light * 2)


def build_strokes():
    steps = []

    # 1. sky wash — serpentine, warm daytime blue paling toward the meadow
    for y in range(GRASS_TOP):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        c = lerp((116, 178, 240), (188, 218, 246), y / (GRASS_TOP - 1))
        for x in row:
            steps.append((x, y, c))

    # 2. meadow — serpentine, deepening green downward
    for y in range(GRASS_TOP, SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        c = lerp((98, 172, 80), (50, 118, 56), (y - GRASS_TOP) / (SIZE - 1 - GRASS_TOP))
        for x in row:
            steps.append((x, y, c))

    # 3. the stem — cream column with a rounded foot, painted bottom-up
    for y in range(27, CAP_BOTTOM - 1, -1):
        half = 3 if y < 24 else 4                    # slight bulge at the foot
        for x in range(STEM_CX - half, STEM_CX + half + 1):
            shade = (x - STEM_CX) / (half + 0.5)     # -1 left .. 1 right
            c = lerp((244, 232, 200), (198, 182, 150), max(0.0, shade) + 0.12)
            steps.append((x, y, c))

    # 4. gills — warm shadow band tucked just under the cap rim
    for x in range(STEM_CX - 9, STEM_CX + 10):
        d = abs(x - STEM_CX)
        if d <= 9:
            steps.append((x, CAP_BOTTOM, lerp((228, 158, 128), (196, 120, 96), d / 9)))

    # 5. the red cap — BLOOMS open from the apex outward by distance
    cap_px = []
    for y, half in CAP_ROWS.items():
        for x in range(CAP_APEX[0] - half, CAP_APEX[0] + half + 1):
            if 0 <= x < SIZE:
                cap_px.append((x, y))
    cap_px.sort(key=lambda p: math.hypot(p[0] - CAP_APEX[0], (p[1] - CAP_APEX[1]) * 1.2))
    for x, y in cap_px:
        steps.append((x, y, cap_color(x, y)))

    # 6. the white spots — dabbed on last, the classic toadstool freckles
    spots = [(11, 9, 1), (20, 8, 1), (16, 7, 1), (8, 12, 1),
             (24, 12, 1), (14, 13, 1), (22, 14, 1), (18, 12, 0)]
    for sx, sy, r in spots:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = sx + dx, sy + dy
                if dx * dx + dy * dy <= r * r + 1 and y in CAP_ROWS:
                    if abs(x - CAP_APEX[0]) <= CAP_ROWS[y]:
                        steps.append((x, y, (250, 248, 242)))

    # 7. finishing strokes — grass tufts and one little flower
    for x, y in ((4, 28), (9, 30), (26, 29), (29, 27), (6, 26)):
        steps.append((x, y, (132, 200, 96)))
    steps.append((28, 26, (66, 138, 62)))            # flower stalk
    for dx, dy, c in ((0, -1, (250, 214, 92)), (-1, -1, (240, 132, 150)),
                      (1, -1, (240, 132, 150)), (0, -2, (240, 132, 150))):
        steps.append((28 + dx, 26 + dy, c))

    return steps


def render_preview(steps, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for x, y, c in steps:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = tuple(c)
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    steps = build_strokes()
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(steps, "art/mushroom.png")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02
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
