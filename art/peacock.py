"""A peacock displaying — painted LIVE on the wall, the fan blooming open.

The stroke ORDER is the show: a dark twilight wash, then the tail fan spreads
outward from the base (painted by increasing radius, so it literally opens),
then each shimmering feather shaft is drawn base-to-tip with its eye-spot lit
at the end, sweeping left to right. Finally the bird itself — breast, long
neck, head, and the little crown of crest feathers — is painted in front.

Design law: one BIG subject filling the panel. Mood: regal, dazzling.

Run:  .venv\\Scripts\\python.exe art\\peacock.py [--preview] [delay_seconds]
"""

import json
import math
import sys
import urllib.request

SIZE = 32
BASE = (16, 27)      # fan pivot / where the bird stands, low center
RMAX = 23.0          # tallest (central) feather reach


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(v))) for v in c))


def tip_radius(ang_deg):
    # central feathers (90deg = straight up) reach highest; edges shorter -> round fan
    return RMAX - 0.145 * abs(ang_deg - 90)


def build_strokes():
    steps = []

    # 1. twilight wash — serpentine, deep indigo top to warmer plum at floor
    for y in range(SIZE):
        row = range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)
        c = lerp((9, 10, 28), (26, 14, 38), y / (SIZE - 1))
        for x in row:
            steps.append((x, y, c))

    # 2. the fan base coat — a dark emerald half-disc that BLOOMS outward
    #    (sorted by radius so it grows from the pivot). This is the plush
    #    body of feathers the eye-spots sit on.
    disc = []
    for y in range(SIZE):
        for x in range(SIZE):
            dx = x - BASE[0]
            dy = y - BASE[1]
            if dy > 1:
                continue
            r = math.hypot(dx, dy)
            ang = math.degrees(math.atan2(-dy, dx))  # up = +90
            if 14 <= ang <= 166 and r <= tip_radius(ang):
                disc.append((r, x, y))
    disc.sort()
    for r, x, y in disc:
        c = lerp((12, 66, 58), (20, 104, 74), min(1.0, r / RMAX))
        steps.append((x, y, c))

    # 3. feather shafts + eye-spots, sweeping left -> right (the fan "reads")
    N = 13
    for i in range(N):
        ang = 148 - (148 - 32) * i / (N - 1)
        R = tip_radius(ang)
        tx = BASE[0] + R * math.cos(math.radians(ang))
        ty = BASE[1] - R * math.sin(math.radians(ang))
        # shaft: sample base -> tip, greens warming to gold near the eye
        seen = set()
        L = max(2, int(R * 1.6))
        for s in range(L + 1):
            t = s / L
            x = round(BASE[0] + (tx - BASE[0]) * t)
            y = round(BASE[1] + (ty - BASE[1]) * t)
            if (x, y) in seen:
                continue
            seen.add((x, y))
            col = lerp((16, 116, 76), (150, 196, 66), t)
            steps.append((x, y, col))
        # eye-spot at the tip: teal halo, copper ring, sapphire core, glint
        ex, ey = round(tx), round(ty)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                steps.append((ex + dx, ey + dy, (18, 150, 158)))
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            steps.append((ex + dx, ey + dy, (206, 148, 44)))
        steps.append((ex, ey, (34, 44, 188)))
        steps.append((ex, ey - 1, (150, 200, 255)))  # tiny glint

    # 4. the bird, painted in front — breast, neck, head, crown
    # breast: rounded iridescent-blue body at the base
    for y in range(24, 31):
        for x in range(SIZE):
            if ((x - 16) / 3.2) ** 2 + ((y - 27) / 3.6) ** 2 <= 1.0:
                t = (y - 24) / 6
                steps.append((x, y, lerp((36, 96, 210), (14, 40, 150), t)))
    # a couple of breast highlights
    for x, y in ((15, 25), (16, 25), (17, 26)):
        steps.append((x, y, (120, 200, 255)))

    # neck: tapering royal-blue column rising to the head
    for y in range(24, 13, -1):
        w = 1 if y < 18 else 1
        for dx in range(-w, w + 1):
            steps.append((16 + dx, y, (28, 70, 196)))
        steps.append((16, y, (46, 110, 230)))     # brighter core sheen

    # head
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if abs(dx) + abs(dy) < 2 or (dx == 0):
                steps.append((16 + dx, 12 + dy, (30, 62, 178)))
    steps.append((16, 12, (60, 120, 235)))
    # beak (points right) + eye glints
    steps.append((18, 12, (240, 196, 70)))
    steps.append((19, 12, (210, 150, 40)))
    steps.append((15, 11, (250, 250, 255)))
    steps.append((17, 11, (250, 250, 255)))

    # crest: three little stalks with dotted tips — the crown
    for cx in (14, 16, 18):
        steps.append((cx, 10, (30, 90, 200)))
        steps.append((cx, 9, (30, 90, 200)))
        steps.append((cx, 8, (24, 170, 170)))   # teal pom tip
    steps.append((16, 7, (150, 220, 220)))

    return steps


def render_preview(steps, path, scale=16):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for x, y, c in steps:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = tuple(int(v) for v in c)
    big = img.resize((SIZE * scale, SIZE * scale), Image.NEAREST)
    big.save(path)
    img.save(path.replace(".png", "-1x.png"))
    return path


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--preview" in args
    args = [a for a in args if a != "--preview"]
    delay = float(args[0]) if args else 0.02
    steps = build_strokes()

    if preview:
        out = render_preview(steps, "art/peacock.png")
        print(f"preview -> {out}  ({len(steps)} strokes)")
    else:
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
