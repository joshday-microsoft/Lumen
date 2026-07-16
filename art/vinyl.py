"""Vinyl — a record spinning under the needle.

An original piece for the Lumen wall: a 32x32 turntable seen from above.
The platter fills the panel edge to edge (big subject, minimal scene): black
grooves with a fixed specular sheen from the upper left, a red label whose
off-center mark and stray dust specks carry the rotation, and a tonearm
riding the outer groove. One loop = one revolution. Mood: warm, nostalgic,
unhurried.

Run:  .venv\\Scripts\\python.exe art\\vinyl.py   -> vinyl.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 16                 # one revolution
CX, CY = 15.5, 16.5
R_DISC = 15.6               # platter reaches every edge
R_LABEL = 4.6
R_HOLE = 0.9
R_GROOVE_IN = 6.0           # grooves live between the label and the lead-in
R_GROOVE_OUT = 14.2

BG = (26, 16, 12)           # dark wood deck, barely there
VINYL = (17, 15, 19)
GROOVE = (33, 30, 37)
RIM = (58, 55, 64)
SHEEN = (150, 138, 128)
LABEL = (176, 44, 32)
LABEL_DK = (118, 26, 20)
LABEL_LT = (232, 196, 120)
HOLE = (14, 12, 14)
ARM = (168, 170, 182)
ARM_DK = (96, 98, 110)
HEAD = (44, 42, 52)
STYLUS = (255, 238, 190)

LIGHT = -2.3                # sheen direction, radians
DUST = ((11.5, 0.9), (8.8, 2.7), (13.1, 4.4))   # (radius, phase)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sheen_at(r, phi):
    """Broad specular band across the platter — fixed to the room, not the disc."""
    d = (phi - LIGHT + math.pi) % (2 * math.pi) - math.pi
    lobe = max(math.cos(d), math.cos(d + math.pi)) ** 4      # both sides of the disc
    v = max(0.0, lobe) * min(1.0, 0.25 + r / R_DISC) * 0.5
    return math.floor(v * 5) / 5     # banded: flat regions keep the GIF in budget


def frame(f):
    theta = 2 * math.pi * f / FRAMES
    img = Image.new("RGB", (SIZE, SIZE), BG)
    px = img.load()

    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x + 0.5 - CX, y + 0.5 - CY
            r = math.hypot(dx, dy)
            if r > R_DISC:
                continue
            phi = math.atan2(dy, dx)

            if r <= R_HOLE:
                px[x, y] = HOLE
                continue

            if r <= R_LABEL:
                c = LABEL
                if r > R_LABEL - 0.9:
                    c = LABEL_DK                                  # label edge
                elif abs(r - 2.6) < 0.45:
                    c = LABEL_DK                                  # printed ring
                # off-center mark: the eye locks onto this and reads the spin
                mx, my = math.cos(theta) * 3.4, math.sin(theta) * 3.4
                if math.hypot(dx - mx, dy - my) < 0.85:
                    c = LABEL_LT
                px[x, y] = lerp(c, SHEEN, sheen_at(r, phi) * 0.35)
                continue

            base = VINYL
            if R_GROOVE_IN <= r <= R_GROOVE_OUT:
                g = (math.sin(r * 2.4) * 0.5 + 0.5) ** 2          # concentric grooves
                base = lerp(VINYL, GROOVE, math.floor(g * 3) / 3)
            elif r > R_DISC - 0.8:
                base = RIM                                        # lit outer edge
            c = lerp(base, SHEEN, sheen_at(r, phi))

            for dr, ph in DUST:                                   # specks ride the disc
                sx, sy = math.cos(theta + ph) * dr, math.sin(theta + ph) * dr
                if math.hypot(dx - sx, dy - sy) < 0.7:
                    c = lerp(c, (208, 198, 186), 0.55)
            px[x, y] = c

    # tonearm: pivot off the bottom-right corner, needle down on the outer groove
    px0, py0 = 30.5, 26.0
    px1, py1 = 22.0, 7.5
    steps = 44
    for i in range(steps + 1):
        t = i / steps
        x = round(px0 + (px1 - px0) * t)
        y = round(py0 + (py1 - py0) * t)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = ARM if i % 7 else ARM_DK                   # segment shading
            if x + 1 < SIZE and t > 0.08:
                px[x + 1, y] = lerp(px[x + 1, y], ARM_DK, 0.55)   # thin drop shadow
    for x, y in ((21, 7), (22, 7), (21, 8), (22, 8)):             # headshell
        px[x, y] = HEAD
    px[21, 9] = STYLUS                                            # needle in the groove
    for x, y in ((30, 26), (31, 26), (30, 27), (31, 27)):         # counterweight
        px[x, y] = HEAD
    px[30, 25] = ARM
    return img


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    import gifsafe
    size = gifsafe.save(frames, HERE / "vinyl.gif", duration_ms=110, colors=12)
    ok = "OK" if size <= 8192 else "TOO BIG!"
    print(f"vinyl.gif: {len(frames)} frames, {size} bytes ({ok})")
    frames[0].save(HERE / "vinyl.png")
    keys = (0, 4, 8, 12)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "vinyl.strip.png")
    print("wrote vinyl.gif")
