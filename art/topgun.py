"""Carrier-deck jet launch at sunset, Top Gun intro style — 30-frame loop.

Run:  .venv\\Scripts\\python.exe art\\topgun.py   → topgun.gif (+ previews)
"""

import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from server.font3x5 import GLYPH_H, GLYPH_W, glyph  # noqa: E402

SIZE = 32
DECK_Y = 23          # deck surface row; jet gear sits on DECK_Y - 1
CAT_X = 6            # catapult hold position

# jet silhouette, facing right, '#' = pixel (13 x 5)
JET = (
    "..#..........",
    ".##....###...",
    "#############",
    "...########..",
    "......##.....",
)
JET_C = (26, 18, 22)

SKY_TOP = (59, 18, 48)
SKY_MID = (196, 69, 31)
SKY_LOW = (255, 179, 71)
SUN_C = (255, 207, 110)
SUN_CORE = (255, 233, 173)
DECK_C = (36, 26, 32)
HULL_C = (18, 12, 16)
RIM_C = (181, 82, 46)
GOLD = (255, 215, 94)
SHADOW = (122, 42, 18)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky_color(y):
    t = y / (DECK_Y - 1)
    return lerp(SKY_TOP, SKY_MID, t / 0.6) if t < 0.6 else lerp(SKY_MID, SKY_LOW, (t - 0.6) / 0.4)


def base_scene():
    img = Image.new("RGB", (SIZE, SIZE))
    for y in range(DECK_Y):
        c = sky_color(y)
        for x in range(SIZE):
            img.putpixel((x, y), c)
    # low sun, right of the catapult run
    cx, cy, r = 23, DECK_Y - 1, 6
    for y in range(cy - r, DECK_Y):
        for x in range(cx - r, cx + r + 1):
            if 0 <= x < SIZE and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                img.putpixel((x, y), SUN_C)
    for y in range(cy - 3, DECK_Y):
        for x in range(cx - 3, cx + 4):
            if 0 <= x < SIZE and (x - cx) ** 2 + (y - cy) ** 2 <= 9:
                img.putpixel((x, y), SUN_CORE)
    # deck rim light + deck + hull
    for x in range(SIZE):
        img.putpixel((x, DECK_Y), RIM_C)
        for y in range(DECK_Y + 1, SIZE):
            img.putpixel((x, y), DECK_C if y < DECK_Y + 4 else HULL_C)
    return img


def put(img, x, y, c):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((x, y), c)


def draw_jet(img, jx, jy):
    for dy, row in enumerate(JET):
        for dx, cell in enumerate(row):
            if cell == "#":
                put(img, jx + dx, jy + dy, JET_C)


def draw_flame(img, jx, jy, length, hot):
    # exhaust exits at the jet's tail (left end), fuselage row
    fy = jy + 2
    for i in range(length):
        x = jx - 1 - i
        t = i / max(1, length - 1)
        c = lerp((255, 243, 196) if hot else (255, 154, 61), (232, 84, 42), t)
        put(img, x, fy, c)
        if i < length // 2:
            put(img, x, fy - 1, lerp(c, sky_color(fy - 1), 0.5))
            put(img, x, fy + 1, lerp(c, DECK_C, 0.4))


def draw_steam(img, f0, f):
    age = f - f0
    if age < 0 or age > 6:
        return
    fade = age / 6
    for i, x in enumerate(range(CAT_X + 2, CAT_X + 16, 3)):
        y = DECK_Y - 1 - (age + i) % 3
        put(img, x, y, lerp((232, 180, 140), sky_color(y), fade))


def draw_text(img, text, y, color, shadow=None):
    w = len(text) * (GLYPH_W + 1) - 1
    x = (SIZE - w) // 2
    for ch in text:
        g = glyph(ch)
        for gy, row in enumerate(g):
            for gx, cell in enumerate(row):
                if cell == "#":
                    if shadow:
                        put(img, x + gx + 1, y + gy + 1, shadow)
                    put(img, x + gx, y + gy, color)
        x += GLYPH_W + 1


def build_frames():
    frames = []
    jy = DECK_Y - len(JET)  # gear on the deck
    taxi = [-13, -10, -7, -5, -3, -1, 1, 3, 5, CAT_X]        # f0..9
    for f, jx in enumerate(taxi):
        img = base_scene()
        draw_jet(img, jx, jy)
        frames.append(img)

    for f in range(6):                                        # f10..15 burner spool
        img = base_scene()
        draw_flame(img, CAT_X, jy, length=min(5, f + 1), hot=(f % 2 == 0))
        draw_jet(img, CAT_X, jy)
        frames.append(img)

    run_x = [8, 11, 15, 20, 26, 33, 41]                       # f16..22 launch + climb
    run_dy = [0, 0, -1, -1, -2, -3, -5]
    for i in range(len(run_x)):
        img = base_scene()
        draw_steam(img, 0, i)
        draw_flame(img, run_x[i], jy + run_dy[i], length=6, hot=(i % 2 == 0))
        draw_jet(img, run_x[i], jy + run_dy[i])
        frames.append(img)

    for i in range(8):                                        # f23..30 title card
        img = base_scene()
        draw_steam(img, 0, 5 + i)
        if i >= 1:
            draw_text(img, "TOP", 6, GOLD, SHADOW)
            draw_text(img, "GUN", 13, GOLD, SHADOW)
        frames.append(img)
    return frames


if __name__ == "__main__":
    frames = build_frames()
    frames[0].save(HERE / "topgun.gif", save_all=True, append_images=frames[1:], duration=120, loop=0)
    keys = (7, 13, 19, 26)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "topgun.strip.png")
    print("wrote topgun.gif,", len(frames), "frames")
