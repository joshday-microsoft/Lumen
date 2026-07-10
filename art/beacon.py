"""Beacon — a lighthouse sweeping a dark sea; the beam reveals what hides in it.

An original piece for the Lumen wall: 36-frame loop, one full revolution.
A sailboat and a whale sit nearly invisible in the dark until the light
passes over them.

Run:  .venv\\Scripts\\python.exe art\\beacon.py   → beacon.gif (+ strip)
"""

import math
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 24
HORIZON = 20

LAMP = (25.5, 7.5)
BEAM_W = 0.22          # half-width, radians
LIGHT = (255, 240, 185)

SKY_TOP = (6, 7, 26)
SKY_LOW = (14, 18, 48)
SEA_TOP = (10, 20, 44)
SEA_BOT = (4, 8, 20)
GLINT = (40, 70, 110)
ROCK = (28, 26, 34)
ROCK_DK = (18, 16, 22)
TOWER_W = (150, 148, 165)
TOWER_R = (110, 34, 44)
CAP = (30, 28, 38)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def beam_intensity(x, y, theta):
    """0..1 — how strongly the beam hits pixel (x, y) at beam angle theta."""
    dx, dy = x - LAMP[0], y - LAMP[1]
    dist = math.hypot(dx, dy)
    if dist < 1.5:
        return 1.0
    phi = math.atan2(dy, dx)
    d = (phi - theta + math.pi) % (2 * math.pi) - math.pi
    if abs(d) >= BEAM_W:
        return 0.0
    falloff = max(0.25, min(1.0, 1.25 - dist / 40))
    return (1 - abs(d) / BEAM_W) * falloff


# hidden things: {pixel: (dark_color, lit_color)}
def sprites():
    s = {}
    # sailboat near the horizon, far left: hull + mast + sail
    for x in range(3, 8):
        s[(x, 19)] = ((14, 22, 46), (198, 168, 118))          # hull
    s[(5, 18)] = ((13, 20, 44), (172, 148, 108))              # mast
    s[(5, 17)] = ((12, 18, 42), (172, 148, 108))
    s[(4, 18)] = ((13, 21, 45), (238, 233, 218))              # sail
    s[(4, 17)] = ((12, 19, 43), (238, 233, 218))
    s[(3, 18)] = ((13, 21, 45), (222, 216, 200))
    # whale mid-sea: back arc + tail
    for x, y in ((9, 24), (10, 23), (11, 23), (12, 23), (13, 23), (14, 24)):
        s[(x, y)] = ((11, 17, 36), (92, 122, 162))
    s[(15, 22)] = ((11, 16, 35), (110, 140, 178))             # tail tip
    s[(8, 24)] = ((11, 17, 36), (80, 108, 146))
    return s


SPRITES = sprites()
WHALE_HEAD = (10.0, 23.0)   # spout shows only while the beam is on the whale


def frame(f):
    theta = 2 * math.pi * f / FRAMES - math.pi / 2   # start pointing up
    img = Image.new("RGB", (SIZE, SIZE))
    rng = random.Random(11)

    # background with beam wash
    for y in range(SIZE):
        for x in range(SIZE):
            if y < HORIZON:
                base = lerp(SKY_TOP, SKY_LOW, y / (HORIZON - 1))
            else:
                base = lerp(SEA_TOP, SEA_BOT, (y - HORIZON) / (SIZE - HORIZON))
            i = beam_intensity(x, y, theta)
            img.putpixel((x, y), lerp(base, LIGHT, i * 0.85) if i > 0 else base)

    # stars (static — inter-frame noise bloats the GIF past the panel's buffer)
    for _ in range(18):
        x, y = rng.randrange(SIZE), rng.randrange(HORIZON - 3)
        if x > 20:
            continue
        b = rng.uniform(0.45, 1.0)
        i = beam_intensity(x, y, theta)
        c = lerp((0, 0, 0), (172, 180, 220), b)
        img.putpixel((x, y), lerp(c, LIGHT, i * 0.85) if i > 0 else c)

    # sea glints (static, same reason)
    for k in range(10):
        x = (k * 7 + 3) % SIZE
        y = HORIZON + 2 + (k * 3) % (SIZE - HORIZON - 3)
        if (x - 4) ** 2 < 1 and y in (17, 18, 19):
            continue
        i = beam_intensity(x, y, theta)
        img.putpixel((x, y), lerp(GLINT, LIGHT, i * 0.85) if i > 0 else GLINT)

    # hidden sprites — lit only by the beam
    for (x, y), (dark, lit) in SPRITES.items():
        i = beam_intensity(x, y, theta)
        img.putpixel((x, y), lerp(dark, lit, min(1.0, i * 1.7)))

    # whale spout, only while the light is on it
    wi = beam_intensity(*WHALE_HEAD, theta)
    if wi > 0.25:
        h = 2 + (f % 2)
        for k in range(h):
            img.putpixel((9, 22 - k), lerp((11, 17, 36), (235, 245, 255), min(1.0, wi * 1.5)))

    # islet + lighthouse, drawn crisp over the wash
    for x, y in ((20, 21), (21, 20), (22, 20), (23, 19), (24, 19), (25, 19),
                 (26, 19), (27, 19), (28, 20), (29, 21), (30, 21)):
        for yy in range(y, min(SIZE, y + 4)):
            img.putpixel((x, yy), ROCK if yy == y else ROCK_DK)
    for y in range(9, 19):
        band = TOWER_R if (y // 3) % 2 == 0 else TOWER_W
        for x in (24, 25, 26):
            img.putpixel((x, y), band)
    img.putpixel((25, 17), (12, 10, 16))            # door
    for x in (24, 25, 26):                          # gallery + cap
        img.putpixel((x, 8), CAP)
        img.putpixel((x, 6), CAP)
    img.putpixel((25, 5), CAP)
    # lamp room glow
    img.putpixel((25, 7), (255, 252, 220))
    img.putpixel((24, 7), lerp(CAP, LIGHT, 0.7))
    img.putpixel((26, 7), lerp(CAP, LIGHT, 0.7))
    return img


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    # shared 48-color palette, no dither, full frames (no optimize: delta/transparency
    # frames are risky on the panel's firmware decoder)
    pal = frames[0].quantize(colors=48)
    q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    q[0].save(HERE / "beacon.gif", save_all=True, append_images=q[1:], duration=150, loop=0)
    keys = (0, 6, 15, 16)   # up, seaward, whale reveal, boat reveal
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "beacon.strip.png")
    print("wrote beacon.gif")
