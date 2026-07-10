"""Surfer riding a rolling ocean swell — 16-frame seamless loop (32x32).

Run:  .venv\\Scripts\\python.exe art\\surfer.py   → surfer.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 16
WAVELEN = 16  # divides 32 and FRAMES → loop wraps perfectly

SKY_TOP = (74, 168, 232)
SKY_LOW = (168, 221, 246)
SUN = (255, 230, 128)
SUN_CORE = (255, 244, 192)
GULL = (40, 48, 60)
SEA_TOP = (42, 114, 192)
SEA_BOT = (16, 56, 102)
SEA_GLINT = (94, 158, 218)
FOAM = (234, 246, 255)
BOARD = (255, 106, 61)
SUIT = (43, 43, 52)
SKIN = (217, 160, 107)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def wave_y(x, f):
    """Ocean surface row at column x for frame f (wave travels right)."""
    return 19 + round(2.4 * math.sin(2 * math.pi * ((x - f) % WAVELEN) / WAVELEN))


def put(img, x, y, c):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((x, y), c)


def frame(f):
    img = Image.new("RGB", (SIZE, SIZE))
    # sky
    for y in range(SIZE):
        c = lerp(SKY_TOP, SKY_LOW, min(1.0, y / 16))
        for x in range(SIZE):
            img.putpixel((x, y), c)
    # sun
    for y in range(1, 8):
        for x in range(23, 30):
            if (x - 26) ** 2 + (y - 4) ** 2 <= 9:
                put(img, x, y, SUN)
            if (x - 26) ** 2 + (y - 4) ** 2 <= 2:
                put(img, x, y, SUN_CORE)
    # gull, flapping every 4 frames
    gx, gy = 7, 5
    if (f // 4) % 2 == 0:
        put(img, gx - 1, gy - 1, GULL); put(img, gx, gy, GULL); put(img, gx + 1, gy - 1, GULL)
    else:
        put(img, gx - 1, gy, GULL); put(img, gx, gy, GULL); put(img, gx + 1, gy, GULL)

    # ocean under the traveling wave surface
    for x in range(SIZE):
        top = wave_y(x, f)
        for y in range(top, SIZE):
            t = (y - 16) / (SIZE - 16)
            img.putpixel((x, y), lerp(SEA_TOP, SEA_BOT, max(0.0, t)))
        # crest foam where the surface peaks
        if top <= 17:
            put(img, x, top, FOAM)
        # sun glints sliding with the wave
        if (x + f) % 5 == 0:
            put(img, x, top + 3, SEA_GLINT)

    # surfer: straight tilted board riding the surface, x=11..16
    y0, y1 = wave_y(11, f) - 1, wave_y(16, f) - 1
    board_y = {}
    for i, x in enumerate(range(11, 17)):
        by = round(y0 + (y1 - y0) * i / 5)
        board_y[x] = by
        put(img, x, by, BOARD)
        if by + 1 >= wave_y(x, f):                 # contact spray
            put(img, x, by + 1, FOAM)
    put(img, 10, board_y[11] + 1, FOAM)            # spray off the tail
    if f % 2 == 0:
        put(img, 9, board_y[11] + 1, FOAM)

    hb = board_y[14]
    slope = wave_y(16, f) - wave_y(12, f)          # >0 = dropping in
    if slope > 0:  # crouch
        put(img, 13, hb - 1, SUIT); put(img, 14, hb - 1, SUIT)
        put(img, 12, hb - 2, SUIT); put(img, 13, hb - 2, SUIT); put(img, 15, hb - 2, SUIT)
        put(img, 13, hb - 3, SKIN)
    else:  # standing, arms out
        put(img, 13, hb - 1, SUIT); put(img, 14, hb - 1, SUIT)
        put(img, 13, hb - 2, SUIT); put(img, 14, hb - 2, SUIT)
        put(img, 12, hb - 3, SUIT); put(img, 13, hb - 3, SUIT); put(img, 15, hb - 3, SUIT)
        put(img, 13, hb - 4, SKIN)
    return img


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    frames[0].save(HERE / "surfer.gif", save_all=True, append_images=frames[1:], duration=120, loop=0)
    keys = (0, 4, 8, 12)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "surfer.strip.png")
    print("wrote surfer.gif")
