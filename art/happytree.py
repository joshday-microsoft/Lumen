"""A happy little landscape, painted LIVE on the wall stroke by stroke.

Builds an ordered pixel sequence — sky wash, sun, cloud, mountain, meadow,
then a tree painted trunk-first with dabbed foliage — and hands it to the
daemon's /paint endpoint. The stroke order IS the performance.

Run:  .venv\\Scripts\\python.exe art\\happytree.py [delay_seconds]
"""

import json
import random
import sys
import urllib.request

SIZE = 32
HORIZON = 19          # sky above, meadow below


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def build_strokes():
    steps = []

    # 1. sky wash — serpentine sweep, light at top to pale horizon
    for y in range(HORIZON):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        c = lerp((104, 168, 235), (198, 224, 248), y / (HORIZON - 1))
        for x in row:
            steps.append((x, y, c))

    # 2. sun, radial: glow ring then core
    sun_cx, sun_cy = 26, 4
    for r, c in ((2, (255, 216, 110)), (1, (255, 240, 190))):
        for y in range(sun_cy - 2, sun_cy + 3):
            for x in range(sun_cx - 2, sun_cx + 3):
                if 0 <= x < SIZE and 0 <= y < HORIZON and (x - sun_cx) ** 2 + (y - sun_cy) ** 2 <= r * r + 1:
                    steps.append((x, y, c))

    # 3. a happy cloud
    for x, y in ((4, 5), (5, 5), (6, 5), (7, 5), (5, 4), (6, 4), (3, 6), (8, 6)):
        steps.append((x, y, (242, 246, 252)))

    # 4. mountain, painted top-down from the peak; snow first two rows
    peak_x, peak_y = 12, 7
    for y in range(peak_y, HORIZON):
        half = round((y - peak_y) * 0.9) + 1
        snow = y < peak_y + 3
        c = (236, 240, 248) if snow else (94, 112, 142)
        for x in range(peak_x - half, peak_x + half + 1):
            if 0 <= x < SIZE:
                steps.append((x, y, c if not (snow and abs(x - peak_x) == half) else (94, 112, 142)))

    # 5. meadow — serpentine, deepening green downward
    for y in range(HORIZON, SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        c = lerp((88, 158, 72), (44, 96, 50), (y - HORIZON) / (SIZE - 1 - HORIZON))
        for x in row:
            steps.append((x, y, c))

    # 6. the happy tree: trunk grows upward, then foliage dabs
    trunk_x = 22
    for y in range(28, 15, -1):
        steps.append((trunk_x, y, (94, 62, 34)))
        steps.append((trunk_x + 1, y, (70, 45, 25)))

    rng = random.Random(29)
    cx, cy, rx, ry = 22.5, 12.5, 6.0, 4.6
    dabs = []
    for y in range(7, 19):
        for x in range(16, 30):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 and 0 <= x < SIZE:
                dabs.append((x, y))
    rng.shuffle(dabs)
    for i, (x, y) in enumerate(dabs):            # dark base coat
        steps.append((x, y, (30, 102, 42)))
    for x, y in rng.sample(dabs, len(dabs) * 2 // 5):   # mid-tone dabs
        steps.append((x, y, (58, 148, 62)))
    lit = [(x, y) for (x, y) in dabs if x <= cx + 1 and y <= cy + 1]  # sun side
    for x, y in rng.sample(lit, max(4, len(lit) // 3)):
        steps.append((x, y, (116, 200, 96)))

    # 7. finishing strokes: grass tufts and two birds
    for x, y in ((4, 22), (9, 26), (14, 24), (7, 29), (17, 28), (27, 30)):
        steps.append((x, y, (120, 190, 90)))
    for bx, by in ((6, 3), (10, 6)):
        for dx, dy in ((0, 0), (1, -1), (2, 0)):
            steps.append((bx + dx, by + dy, (40, 48, 60)))

    return steps


if __name__ == "__main__":
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02
    steps = build_strokes()
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
