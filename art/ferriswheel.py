"""Ferris wheel — a big carnival wheel turning against a night sky.

An original loop for the Lumen wall. One full revolution, so the loop is
perfectly seamless: eight rainbow gondolas ride a steel wheel around a bright
axle, the A-frame legs stand still in front at the bottom. Festive / joyful.

Run:  .venv\\Scripts\\python.exe art\\ferriswheel.py   -> ferriswheel.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 20            # one full revolution -> seamless loop

CX, CY = 16.0, 14.5
RIM_R = 14.0
CAB_R = 11.3
N_CAB = 8

SKY_TOP = (5, 6, 22)
SKY_BOT = (12, 12, 34)
STAR = (150, 160, 205)
RIM = (120, 132, 168)          # steel ring
RIM_HI = (205, 214, 245)       # bright bulbs on the ring
SPOKE = (78, 92, 128)
HUB = (255, 246, 210)
HUB_IN = (255, 210, 120)
LEG = (108, 114, 132)
LEG_DK = (66, 70, 86)
BASE = (150, 156, 176)

# eight festive gondola colors (ride around with the wheel)
CABS = [
    (255, 66, 66),    # red
    (255, 150, 40),   # orange
    (255, 226, 70),   # yellow
    (86, 224, 96),    # green
    (70, 220, 220),   # cyan
    (90, 140, 255),   # blue
    (176, 108, 255),  # violet
    (255, 96, 200),   # pink
]

# a few static stars, kept sparse (inter-frame noise bloats the GIF)
STARS = [(3, 3, 0.9), (27, 4, 0.7), (6, 8, 0.5), (29, 10, 0.8),
         (2, 12, 0.6), (24, 2, 0.55), (10, 2, 0.7)]


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def put(img, x, y, c):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((x, y), c)


def line(img, x0, y0, x1, y1, c):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        put(img, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def frame(f):
    img = Image.new("RGB", (SIZE, SIZE))
    for y in range(SIZE):
        base = lerp(SKY_TOP, SKY_BOT, y / (SIZE - 1))
        for x in range(SIZE):
            img.putpixel((x, y), base)
    for sx, sy, b in STARS:
        put(img, sx, sy, lerp(SKY_TOP, STAR, b))

    theta = 2 * math.pi * f / FRAMES         # wheel rotation (clockwise)

    # rim: steel ring, with a bright bulb every ~22 degrees riding along
    for k in range(72):
        a = 2 * math.pi * k / 72 + theta
        x = round(CX + RIM_R * math.cos(a))
        y = round(CY + RIM_R * math.sin(a))
        put(img, x, y, RIM_HI if k % 4 == 0 else RIM)

    # spokes from the hub out to each gondola
    for i in range(N_CAB):
        a = theta + 2 * math.pi * i / N_CAB
        rx = round(CX + RIM_R * math.cos(a))
        ry = round(CY + RIM_R * math.sin(a))
        line(img, round(CX), round(CY), rx, ry, SPOKE)

    # gondolas: a 2x2 colored car just inside the rim, riding the wheel
    for i in range(N_CAB):
        a = theta + 2 * math.pi * i / N_CAB
        cx = CX + CAB_R * math.cos(a)
        cy = CY + CAB_R * math.sin(a)
        col = CABS[i]
        bx, by = int(round(cx)) - 0, int(round(cy)) - 0
        for ox in (-1, 0):
            for oy in (-1, 0):
                put(img, bx + ox, by + oy, col)
        # a lit window pip
        put(img, bx, by, lerp(col, (255, 255, 255), 0.55))

    # bright axle over the spokes
    for ox in (-1, 0):
        for oy in (-1, 0):
            put(img, round(CX) + ox, round(CY) + oy, HUB)
    put(img, round(CX), round(CY), HUB_IN)

    # static A-frame legs + base, drawn in front at the bottom
    hx, hy = round(CX), round(CY)
    line(img, hx, hy, 8, 31, LEG_DK)
    line(img, hx, hy, 24, 31, LEG_DK)
    line(img, hx - 1, hy, 7, 31, LEG)
    line(img, hx + 1, hy, 25, 31, LEG)
    for x in range(6, 27):
        put(img, x, 31, BASE)
    return img


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    import gifsafe
    size = gifsafe.save(frames, HERE / "ferriswheel.gif", duration_ms=160, colors=12)
    ok = "OK" if size <= 8192 else "TOO BIG!"
    print(f"ferriswheel.gif: {len(frames)} frames, {size} bytes ({ok})")

    keys = (0, 3, 6, 9, 12, 16)
    strip = Image.new("RGB", (SIZE * 5 * len(keys) + (len(keys) - 1) * 4, SIZE * 5), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 5, SIZE * 5), Image.NEAREST),
                    (i * (SIZE * 5 + 4), 0))
    strip.save(HERE / "ferriswheel.strip.png")
    print("wrote ferriswheel.gif + ferriswheel.strip.png")
