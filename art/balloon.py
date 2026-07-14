"""Balloon — a big hot-air balloon drifting up through a dawn sky.

Original piece for the Lumen wall: a seamless loop. The balloon holds center,
bobbing gently while the burner flickers; the clouds behind it scroll DOWNWARD,
so the whole world reads as the balloon rising. Mood: serene, uplifting.

Design law obeyed: one big subject, minimal scene — the envelope fills most of
the frame; the only other elements are a few drifting clouds and a warm sky.

Run:  .venv\\Scripts\\python.exe art\\balloon.py   -> balloon.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 22
CX = 15.5
SKY_BANDS = 7      # snap the gradient to a few levels — smaller palette, longer LZW runs

# dawn sky, deep periwinkle up top warming to peach at the horizon
SKY_TOP = (34, 40, 78)
SKY_BOT = (250, 196, 140)

# five gores wrapping the envelope, warm jewel tones
GORES = [
    (226, 74, 60),    # red
    (245, 201, 120),  # cream-gold
    (44, 162, 152),   # teal
    (245, 201, 120),  # cream-gold
    (232, 138, 60),   # orange
]

# per-row half-widths of the envelope, y = 1 (top) .. 19 (mouth)
HALFW = {
    1: 3, 2: 5, 3: 6, 4: 7, 5: 8, 6: 8, 7: 9, 8: 9, 9: 9,
    10: 9, 11: 8, 12: 8, 13: 7, 14: 6, 15: 5, 16: 4, 17: 3, 18: 3, 19: 2,
}

BASKET = (120, 74, 40)
BASKET_DK = (86, 52, 28)
ROPE = (150, 120, 92)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def clampc(c):
    return tuple(max(0, min(255, round(v))) for v in c)


def scale(c, f):
    return clampc((c[0] * f, c[1] * f, c[2] * f))


def sky(y):
    t = y / (SIZE - 1)
    t = round(t * (SKY_BANDS - 1)) / (SKY_BANDS - 1)   # quantize to bands
    return lerp(SKY_TOP, SKY_BOT, t)


# a handful of soft cloud puffs (base positions); each scrolls downward and
# wraps at 32, so the loop is seamless. (x, y, radius, brightness)
CLOUDS = [
    (6, 4, 3, 0.55),
    (24, 12, 4, 0.62),
    (11, 22, 3, 0.5),
    (27, 27, 2, 0.45),
    (2, 16, 2, 0.4),
]


def draw_clouds(img, i):
    shift = i * SIZE / FRAMES
    for cx0, cy0, r, bright in CLOUDS:
        cy = (cy0 + shift) % SIZE
        for dy in range(-r, r + 1):
            for dx in range(-r - 1, r + 2):
                # squashed puff — wider than tall, soft falloff
                d = (dx / (r + 1)) ** 2 + (dy / r) ** 2
                if d > 1.0:
                    continue
                x = cx0 + dx
                yy = int(round(cy + dy))
                if not (0 <= x < SIZE and 0 <= yy < SIZE):
                    continue
                soft = bright * (1 - d) ** 0.6
                soft = round(min(0.85, soft) * 4) / 4      # snap to 4 opacity steps
                if soft <= 0:
                    continue
                base = sky(yy)
                img.putpixel((x, yy), lerp(base, (255, 246, 232), soft))


def envelope_color(x, y):
    """Gore color + roundness shading for a pixel inside the envelope, or None."""
    hw = HALFW.get(y)
    if hw is None:
        return None
    u = (x - CX) / hw
    if abs(u) > 1.0:
        return None
    gore = GORES[min(len(GORES) - 1, int((u + 1) / 2 * len(GORES)))]
    shade = 1.0 - 0.34 * abs(u)          # edges roll into shadow
    if u < -0.05 and 2 <= y <= 9:        # upper-left highlight
        shade += 0.20
    shade = max(0.55, min(1.18, shade))
    return scale(gore, shade)


def draw_balloon(img, i):
    bob = round(1.3 * math.sin(2 * math.pi * i / FRAMES))   # gentle rise/fall

    def put(x, y, c):
        yy = y + bob
        if 0 <= x < SIZE and 0 <= yy < SIZE:
            img.putpixel((x, yy), c)

    # envelope
    for y in range(1, 20):
        for x in range(SIZE):
            c = envelope_color(x, y)
            if c is not None:
                put(x, y, c)

    # mouth / throat opening under the envelope, glowing from the burner
    for x in range(15, 17):
        put(x, 20, (70, 40, 26))

    # burner flame — flickers deterministically, glows up into the mouth
    fh = 2 + (1 if i % 3 == 0 else 0) + (1 if i % 5 == 0 else 0)
    flame = [(255, 244, 190), (255, 196, 96), (255, 128, 48)]
    for k in range(fh):
        col = flame[min(2, k)]
        put(16, 21 + k, col)
        if k < fh - 1:
            put(15, 21 + k, scale(col, 0.8))
    # burner uplight tint on the mouth pixels
    put(15, 20, lerp((70, 40, 26), (255, 180, 90), 0.6))
    put(16, 20, lerp((70, 40, 26), (255, 180, 90), 0.6))

    # ropes from lower shoulders to the basket rim
    for (x, y) in ((13, 19), (13, 21), (13, 22),
                   (18, 19), (18, 21), (18, 22)):
        put(x, y, ROPE)

    # basket
    for y in range(23, 26):
        for x in range(14, 18):
            put(x, y, BASKET if y == 23 else BASKET_DK)
    for x in range(14, 18):                 # rim highlight
        put(x, 23, lerp(BASKET, (170, 120, 78), 0.6))


def frame(i):
    img = Image.new("RGB", (SIZE, SIZE))
    for y in range(SIZE):
        row = sky(y)
        for x in range(SIZE):
            img.putpixel((x, y), row)
    draw_clouds(img, i)
    draw_balloon(img, i)
    return img


if __name__ == "__main__":
    import gifsafe

    frames = [frame(i) for i in range(FRAMES)]
    size = gifsafe.save(frames, HERE / "balloon.gif", duration_ms=120, colors=18)
    ok = size <= 8192 and len(frames) <= 60
    print(f"balloon.gif: {len(frames)} frames, {size} bytes "
          f"({'OK' if ok else 'OVER BUDGET'})")

    # save a still hero frame
    frames[0].save(HERE / "balloon.png")

    # review strip: a few phases of the loop
    keys = (0, 6, 11, 17)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6),
                      (18, 18, 24))
    for j, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST),
                    (j * (SIZE * 6 + 4), 0))
    strip.save(HERE / "balloon.strip.png")
    print("wrote balloon.gif, balloon.png, balloon.strip.png")
