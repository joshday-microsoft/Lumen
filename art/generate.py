"""Generate Lumen art pieces (32x32 pixel art): sunset.png + starfield.gif.

Run with the repo venv:  .venv\\Scripts\\python.exe art\\generate.py
Outputs land next to this file, with x8 .preview.png copies for humans.
"""

import math
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def save_with_preview(img: Image.Image, name: str):
    img.save(HERE / name)
    img.resize((SIZE * 8, SIZE * 8), Image.NEAREST).save(HERE / f"{name}.preview.png")


# ---------------------------------------------------------------- sunset

def make_sunset() -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE))
    horizon = 20
    top, mid, low = (18, 10, 58), (188, 74, 52), (255, 172, 66)

    for y in range(horizon):
        t = y / (horizon - 1)
        c = lerp(top, mid, t / 0.55) if t < 0.55 else lerp(mid, low, (t - 0.55) / 0.45)
        for x in range(SIZE):
            img.putpixel((x, y), c)

    # a few pale stars high in the sky
    rng = random.Random(7)
    for _ in range(6):
        x, y = rng.randrange(SIZE), rng.randrange(6)
        img.putpixel((x, y), (150, 130, 190))

    # sun: layered glow half-disc sitting on the horizon
    cx, cy = 16, horizon - 1
    for r, color in ((6, (255, 120, 40)), (4, (255, 178, 84)), (2, (255, 236, 190))):
        for y in range(cy - r, cy + 1):
            for x in range(cx - r, cx + r + 1):
                if 0 <= x < SIZE and 0 <= y < horizon:
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                        img.putpixel((x, y), color)

    # island silhouette left of the sun
    for x, h in ((2, 1), (3, 2), (4, 2), (5, 3), (6, 2), (7, 1)):
        for dy in range(h):
            img.putpixel((x, horizon - 1 - dy), (30, 14, 40))

    # two distant birds
    for bx, by in ((24, 5), (27, 7)):
        img.putpixel((bx, by), (20, 10, 30))
        img.putpixel((bx + 1, by - 1), (20, 10, 30))
        img.putpixel((bx + 2, by), (20, 10, 30))

    # water: darkening blue with a shimmering sun reflection column
    wtop, wbot = (24, 34, 78), (6, 10, 30)
    rng = random.Random(3)
    for y in range(horizon, SIZE):
        t = (y - horizon) / (SIZE - 1 - horizon)
        c = lerp(wtop, wbot, t)
        for x in range(SIZE):
            img.putpixel((x, y), c)
        # reflection: jittered widths, brighter near horizon, fading out
        if rng.random() < 0.85 - 0.5 * t:
            half = max(0, round((3 - 2.5 * t) + rng.uniform(-1, 1)))
            glow = lerp((255, 170, 70), c, 0.25 + 0.55 * t)
            for x in range(16 - half, 17 + half):
                if 0 <= x < SIZE:
                    img.putpixel((x, y), glow)
    return img


# ---------------------------------------------------------------- starfield gif

def make_starfield(frames=24) -> list[Image.Image]:
    rng = random.Random(42)
    stars = []
    while len(stars) < 26:
        x, y = rng.randrange(SIZE), rng.randrange(SIZE)
        if x > 17 and y < 12:  # keep the moon's corner clear
            continue
        stars.append((x, y, rng.uniform(0.4, 1.0), rng.uniform(0, 2 * math.pi)))

    # shooting star path, frames 6..13
    sx0, sy0, sx1, sy1 = 1.0, 3.0, 27.0, 17.0
    shoot_span = (6, 13)

    out = []
    for f in range(frames):
        img = Image.new("RGB", (SIZE, SIZE))
        for y in range(SIZE):  # night gradient
            c = lerp((8, 10, 30), (2, 3, 10), y / (SIZE - 1))
            for x in range(SIZE):
                img.putpixel((x, y), c)

        for x, y, base, phase in stars:  # twinkle
            b = base * (0.55 + 0.45 * math.sin(2 * math.pi * f / frames * 3 + phase))
            c = (round(190 * b + 20), round(195 * b + 20), round(225 * b + 25))
            img.putpixel((x, y), c)

        # crescent moon top-right
        mx, my, r = 25, 6, 4
        for y in range(my - r, my + r + 1):
            for x in range(mx - r, mx + r + 1):
                if (x - mx) ** 2 + (y - my) ** 2 <= r * r:
                    if (x - (mx + 2)) ** 2 + (y - (my - 1)) ** 2 > r * r:
                        if 0 <= x < SIZE and 0 <= y < SIZE:
                            img.putpixel((x, y), (226, 224, 200))

        f0, f1 = shoot_span
        if f0 <= f <= f1:  # shooting star with fading tail
            t = (f - f0) / (f1 - f0)
            hx, hy = sx0 + (sx1 - sx0) * t, sy0 + (sy1 - sy0) * t
            for k in range(5):
                tt = t - k * 0.055
                if tt < 0:
                    break
                px = round(sx0 + (sx1 - sx0) * tt)
                py = round(sy0 + (sy1 - sy0) * tt)
                if 0 <= px < SIZE and 0 <= py < SIZE:
                    fade = 1.0 - k / 5
                    img.putpixel((px, py), (round(255 * fade), round(250 * fade), round(210 * fade)))
        out.append(img)
    return out


if __name__ == "__main__":
    sunset = make_sunset()
    save_with_preview(sunset, "sunset.png")

    frames = make_starfield()
    frames[0].save(
        HERE / "starfield.gif",
        save_all=True,
        append_images=frames[1:],
        duration=110,
        loop=0,
    )
    frames[0].resize((SIZE * 8, SIZE * 8), Image.NEAREST).save(HERE / "starfield.gif.preview.png")
    print("wrote", HERE / "sunset.png", "and", HERE / "starfield.gif")
