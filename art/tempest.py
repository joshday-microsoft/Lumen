"""Tempest — night storm loop. Rain falls; lightning forks down and the flash
reveals a hidden landscape. First piece built for the expanded envelope
(≤60 frames / ≤8KB, gifsafe encoding).

Run:  .venv\\Scripts\\python.exe art\\tempest.py
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 40

SKY = (4, 5, 10)
CLOUD_A = (16, 18, 28)
CLOUD_B = (24, 26, 38)
RAIN = (52, 72, 110)
RAIN_HEAD = (86, 116, 164)
HILL = (9, 11, 19)
TREE = (11, 13, 22)
BOLT_CORE = (242, 246, 255)
BOLT_DIM = (120, 130, 185)
BOLT_FADE = (178, 188, 232)
EMBER = (212, 96, 32)
EMBER_DK = (150, 60, 22)

HILL_Y = {x: 28 - (1 if 4 <= x <= 10 else 0) - (2 if 18 <= x <= 27 else 0) for x in range(SIZE)}

BOLT_MAIN = [(10, 6), (15, 11), (11, 16), (19, 22), (23, 26)]
BOLT_FORK = [(11, 16), (6, 21), (8, 25)]
BOLT_FAR = [(4, 7), (6, 12), (3, 16)]

rng = random.Random(17)
DROPS = [(rng.randrange(SIZE), rng.randrange(40)) for _ in range(15)]


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def base_scene(flash):
    """flash 0..1 — lightning illumination lifts the whole world."""
    img = Image.new("RGB", (SIZE, SIZE), lerp(SKY, (120, 130, 175), flash * 0.55))
    d = ImageDraw.Draw(img)
    # static cloud bank, brightened by flash from behind
    for (x0, y0, x1, y1, c) in (
        (0, 0, 31, 2, CLOUD_A), (2, 3, 13, 4, CLOUD_B), (17, 3, 29, 5, CLOUD_B),
        (6, 5, 24, 5, CLOUD_A), (0, 3, 4, 4, CLOUD_A),
    ):
        d.rectangle([x0, y0, x1, y1], fill=lerp(c, (190, 200, 240), flash * 0.7))
    # hills + lone tree — invisible until the flash backlights them
    hill_c = lerp(HILL, (58, 64, 96), flash)
    tree_c = lerp(TREE, (30, 34, 56), flash)
    for x in range(SIZE):
        d.rectangle([x, HILL_Y[x], x, SIZE - 1], fill=hill_c)
    d.rectangle([23, 21, 23, 25], fill=tree_c)                     # trunk
    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 0), (0, -2), (-1, -1), (1, -1)):
        d.point((23 + dx, 20 + dy), fill=tree_c)                   # canopy
    return img, d


def draw_bolt(d, pts, color, wide=False):
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=color, width=1)
        if wide:
            for (x0, y0), (x1, y1) in ((pts[i], pts[i + 1]),):
                d.line([(x0 + 1, y0), (x1 + 1, y1)], fill=lerp(color, SKY, 0.45), width=1)


def frame(f):
    # strike A: f16 dim, f17 FULL, f18 fade, f19 afterglow. strike B (far): f32.
    flash = {16: 0.18, 17: 1.0, 18: 0.38, 19: 0.12, 32: 0.22, 33: 0.08}.get(f, 0.0)
    img, d = base_scene(flash)

    # rain — continuous fall, glinting white during the big flash
    for k, (dx, phase) in enumerate(DROPS):
        y = (phase + f * 2) % 40 - 6
        x = (dx + (k % 3)) % SIZE
        head = lerp(RAIN_HEAD, (235, 240, 255), flash * 0.8)
        tail = lerp(RAIN, (170, 180, 220), flash * 0.6)
        for i, c in ((0, head), (1, tail), (2, tail)):
            yy = y - i
            if 6 <= yy < HILL_Y.get(x, 28):
                d.point((x, yy), fill=c)

    if f == 16:
        draw_bolt(d, BOLT_MAIN, BOLT_DIM)
    elif f == 17:
        draw_bolt(d, BOLT_MAIN, BOLT_CORE, wide=True)
        draw_bolt(d, BOLT_FORK, BOLT_CORE)
    elif f == 18:
        draw_bolt(d, BOLT_MAIN, BOLT_FADE)
        draw_bolt(d, BOLT_FORK, lerp(BOLT_FADE, SKY, 0.4))
    elif f == 32:
        draw_bolt(d, BOLT_FAR, BOLT_DIM)

    # embers where the bolt met the tree, flickering out
    if 18 <= f <= 30:
        strength = 1.0 - (f - 18) / 13
        c = EMBER if f % 2 == 0 else EMBER_DK
        d.point((23, 19), fill=lerp(TREE, c, strength))
        if f % 2 == 0 and strength > 0.4:
            d.point((24, 18), fill=lerp(SKY, EMBER, strength * 0.7))
    return img


if __name__ == "__main__":
    import gifsafe

    frames = [frame(f) for f in range(FRAMES)]
    size = gifsafe.save(frames, HERE / "tempest.gif", duration_ms=130, colors=32)
    print(f"tempest.gif: {FRAMES} frames, {size} bytes ({'OK' if size <= 8192 else 'TOO BIG'})")
    keys = (8, 17, 21, 32)   # rain, THE STRIKE, embers, far strike
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "tempest.strip.png")
