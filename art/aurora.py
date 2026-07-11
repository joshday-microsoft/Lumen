"""Aurora — northern lights over snowy peaks, one warm cabin window.

Seamless loop: two sine-driven curtain layers ripple and pulse through
green/teal with a violet fringe. A nod to the Alaska trip.

Run:  .venv\\Scripts\\python.exe art\\aurora.py
"""

import math
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 20

SKY = (3, 4, 12)
STAR = (150, 160, 200)
GREEN = (64, 224, 128)
TEAL = (36, 160, 150)
VIOLET = (138, 84, 216)
SNOW = (222, 230, 244)
SNOW_SHADE = (150, 165, 200)
ROCK = (26, 32, 52)
CABIN = (34, 26, 30)
WINDOW = (255, 190, 80)

rng = random.Random(8)
STARS = [(rng.randrange(SIZE), rng.randrange(20)) for _ in range(14)]

# mountain ridge heights (top row of snow per column)
RIDGE = [26, 25, 24, 23, 24, 25, 24, 23, 22, 23, 24, 25, 26, 25, 24, 23,
         22, 21, 22, 23, 24, 25, 26, 26, 25, 24, 25, 26, 27, 26, 25, 26]


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def frame(f):
    ph = 2 * math.pi * f / FRAMES
    img = Image.new("RGB", (SIZE, SIZE), SKY)

    for x, y in STARS:
        img.putpixel((x, y), STAR)

    # aurora curtains: undulating top edge, per-column brightness pulse
    for x in range(SIZE):
        u = x / SIZE
        top = 5 + 3.2 * math.sin(2 * math.pi * u * 1.5 + ph) + 2.0 * math.sin(2 * math.pi * u * 3 - 2 * ph)
        glow = round((0.5 + 0.5 * math.sin(2 * math.pi * u * 2 + 2 * ph + 1.3)) * 2) / 2
        strength = 0.35 + 0.65 * glow          # 3 discrete shimmer levels
        band = 7 + round(2 * glow)
        for i in range(band):
            y = round(top) + i
            if 0 <= y < 21:
                t = round(i / band * 4) / 4    # 5 discrete band positions
                c = lerp(VIOLET, GREEN, min(1.0, t * 1.9)) if t < 0.55 else lerp(GREEN, TEAL, (t - 0.55) / 0.45)
                c = lerp(SKY, c, strength * (1.0 - t * 0.35))
                if sum(c) > sum(SKY) + 18:
                    img.putpixel((x, y), c)

    # snowy ridge + rock shadow beneath
    for x in range(SIZE):
        r = RIDGE[x]
        img.putpixel((x, r), SNOW)
        img.putpixel((x, r + 1), SNOW if RIDGE[(x + 1) % SIZE] > r else SNOW_SHADE)
        for y in range(r + 2, SIZE):
            img.putpixel((x, y), ROCK if y > r + 3 else SNOW_SHADE)

    # cabin with one warm window (flickers gently)
    for dx in range(3):
        for dy in range(3):
            img.putpixel((23 + dx, 27 + dy), CABIN)
    win = WINDOW if f % 6 < 4 else (226, 158, 60)
    img.putpixel((24, 28), win)
    return img


if __name__ == "__main__":
    import gifsafe

    frames = [frame(f) for f in range(FRAMES)]
    size = gifsafe.save(frames, HERE / "aurora.gif", duration_ms=200, colors=32)
    print(f"aurora.gif: {FRAMES} frames, {size} bytes ({'OK' if size <= 8192 else 'TOO BIG'})")
    keys = (0, 5, 10, 15)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "aurora.strip.png")
