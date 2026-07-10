"""Microsoft-themed loop: four brand panes assemble, gleam, and scatter,
with a boot-style dot spinner orbiting below. 16 frames, single 4k block.

Run:  .venv\\Scripts\\python.exe art\\microsoft.py   → microsoft.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 16

BG = (10, 10, 14)
RED = (242, 80, 34)
GREEN = (127, 186, 0)
BLUE = (0, 164, 239)
YELLOW = (255, 185, 0)
DOT = (222, 222, 226)

SQ = 9      # pane size
GAP = 1
# assembled top-left corners of the four panes, and their fly-in corners
PANES = [
    ((6, 4), (-10, -10), RED),      # TL
    ((16, 4), (33, -10), GREEN),    # TR
    ((6, 14), (-10, 33), BLUE),     # BL
    ((16, 14), (33, 33), YELLOW),   # BR
]
SPIN_C = (15.5, 28.0)
SPIN_R = 2.6


def lerp(a, b, t):
    return a + (b - a) * t


def blend(c1, c2, t):
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def frame(f):
    img = Image.new("RGB", (SIZE, SIZE), BG)

    # pane positions: fly in f0-4, hold f5-11, fly out f12-14, absent f15
    if f <= 4:
        t = (f / 4) ** 0.7          # ease-out arrival
        vis = True
    elif f <= 11:
        t = 1.0
        vis = True
    elif f <= 14:
        t = 1.0 - (f - 11) / 3      # accelerate away
        vis = True
    else:
        vis = False

    if vis:
        gleam_c = 8 + (f - 5) * 6 if 5 <= f <= 11 else None   # diagonal sweep
        for (hx, hy), (cx, cy), color in PANES:
            px = round(lerp(cx, hx, t))
            py = round(lerp(cy, hy, t))
            for dy in range(SQ):
                for dx in range(SQ):
                    x, y = px + dx, py + dy
                    if 0 <= x < SIZE and 0 <= y < SIZE:
                        c = color
                        if gleam_c is not None and gleam_c <= x + y <= gleam_c + 2:
                            c = blend(color, (255, 255, 255), 0.65)
                        img.putpixel((x, y), c)

    # boot spinner: five dots chasing around a small circle, one lap per loop
    theta = 2 * math.pi * f / FRAMES
    for k in range(5):
        a = theta + k * 0.5
        x = round(SPIN_C[0] + SPIN_R * math.cos(a))
        y = round(SPIN_C[1] + SPIN_R * math.sin(a))
        fade = 1.0 - k * 0.18
        if 0 <= x < SIZE and 0 <= y < SIZE:
            img.putpixel((x, y), blend(BG, DOT, fade))
    return img


if __name__ == "__main__":
    import gifsafe

    frames = [frame(f) for f in range(FRAMES)]
    size = gifsafe.save(frames, HERE / "microsoft.gif", duration_ms=140, colors=32)
    print(f"microsoft.gif: {len(frames)} frames, {size} bytes, panel-safe encode, round-trip OK"
          f" ({'single block' if size <= 4080 else 'TOO BIG!'})")
    keys = (2, 5, 8, 13)   # flying in, assembled, gleam, scattering
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "microsoft.strip.png")
