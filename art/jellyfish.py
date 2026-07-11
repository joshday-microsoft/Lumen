"""Jellyfish — a lone bioluminescent bell drifting up through dark water.

Big subject, minimal scene: one glowing jellyfish centered on the panel.
The bell pulses (contract → rise, relax → sink), the oral arms and tentacles
sway with the same phase, and faint motes drift upward. Everything is drawn
additively into a float buffer so the glow blooms softly — deep-sea serene.

Seamless 44-frame loop (all motion is sinusoidal over one period).

Run:  .venv\\Scripts\\python.exe art\\jellyfish.py   → jellyfish.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

import os

HERE = Path(__file__).resolve().parent
SIZE = 32
# 18 frames / 24 colors lands at ~7.9 KB — inside the panel's 8192-byte ceiling.
# The soft additive glow gives every frame high spatial entropy (~410 B/frame),
# so frame count, not palette, is the binding constraint here.
FRAMES = int(os.environ.get("JF_FRAMES", "18"))
COLORS = int(os.environ.get("JF_COLORS", "24"))
CX = 16.0

# palette (additive intensities keep these from clipping unless glows overlap)
BG_TOP = (2, 3, 10)
BG_BOT = (4, 11, 22)
BELL = (210, 60, 145)        # translucent magenta body
BELL_CORE = (255, 150, 205)  # brighter inner glow
RIM = (255, 185, 225)        # bright bell margin
CYAN = (120, 225, 255)       # inner gonad streaks / cool highlight
TENT = (200, 55, 135)        # tentacle filaments
TIP = (255, 120, 200)        # glowing tentacle tips
MOTE = (80, 170, 215)        # drifting plankton motes


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def new_buf():
    """Buffer pre-filled with the deep-water gradient."""
    buf = []
    for y in range(SIZE):
        base = lerp(BG_TOP, BG_BOT, y / (SIZE - 1))
        buf.append([[base[0], base[1], base[2]] for _ in range(SIZE)])
    return buf


def add(buf, x, y, color, k):
    if k <= 0 or x < 0 or x >= SIZE or y < 0 or y >= SIZE:
        return
    p = buf[y][x]
    p[0] += color[0] * k
    p[1] += color[1] * k
    p[2] += color[2] * k


def glow(buf, cx, cy, r, color, inten):
    """Soft radial bloom centred at (cx, cy)."""
    sig2 = 2 * (r * 0.55) ** 2
    for y in range(max(0, int(cy - r - 1)), min(SIZE, int(cy + r + 2))):
        for x in range(max(0, int(cx - r - 1)), min(SIZE, int(cx + r + 2))):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= (r + 1) ** 2:
                add(buf, x, y, color, inten * math.exp(-d2 / sig2))


def to_image(buf):
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            p = buf[y][x]
            px[x, y] = (min(255, int(p[0])), min(255, int(p[1])), min(255, int(p[2])))
    return img


def frame(f):
    p = f / FRAMES
    ph = 2 * math.pi * p
    # contraction 0..1..0: contracted bell is narrower, taller, and risen
    c = 0.5 - 0.5 * math.cos(ph)

    a = 8.5 * (1 - 0.20 * c)          # bell half-width
    b = 5.4 * (1 + 0.20 * c)          # bell half-height
    cy = 12.5 - 2.6 * c              # bell centre rises as it contracts
    margin = cy + 0.34 * b           # lower edge of the bell (where arms hang)

    buf = new_buf()

    # ambient body halo so the bell reads as translucent, not a hard shape
    glow(buf, CX, cy - 0.4 * b, a * 1.15, BELL, 0.32)

    # bell body: fill the dome, brighter toward the crown and the rim
    x0, x1 = int(CX - a - 1), int(CX + a + 2)
    for x in range(max(0, x0), min(SIZE, x1)):
        dx = (x - CX) / a
        if abs(dx) > 1:
            continue
        dome = b * math.sqrt(max(0.0, 1 - dx * dx))
        y_top = cy - dome
        y_bot = margin
        span = max(1.0, y_bot - y_top)
        for yy in range(int(round(y_top)), int(round(y_bot)) + 1):
            t = min(1.0, max(0.0, (yy - y_top) / span))   # 0 crown .. 1 margin
            # brighter at the crown, dimmer mid-body, glow again near margin
            body = 0.55 * (1 - t) ** 1.5 + 0.18
            add(buf, x, yy, BELL, body)
            add(buf, x, yy, BELL_CORE, 0.22 * (1 - abs(dx)) * (1 - t))

    # crown highlight — a cool sheen on top of the dome
    glow(buf, CX, cy - 0.72 * b, a * 0.42, CYAN, 0.5)
    glow(buf, CX, cy - 0.5 * b, a * 0.6, BELL_CORE, 0.45)

    # inner gonad streaks (four cool arcs inside the bell)
    for k in (-1.5, -0.5, 0.5, 1.5):
        gx = CX + k * a * 0.30
        glow(buf, gx, cy - 0.05 * b, 1.3, CYAN, 0.34)

    # scalloped bell margin — bright bumps along the lower rim
    scallops = 7
    for i in range(scallops):
        dx = (i / (scallops - 1) - 0.5) * 2       # -1..1
        mx = CX + dx * a * 0.94
        my = margin + math.sqrt(max(0.0, 1 - dx * dx)) * 0.6
        # margin flutters gently with the pulse
        my += 0.5 * math.sin(ph + i)
        glow(buf, mx, my, 1.15, RIM, 0.7)

    # oral arms: 4 short frilly ribbons near the centre
    for j, base_dx in enumerate((-0.42, -0.14, 0.14, 0.42)):
        bx = CX + base_dx * a
        length = 9 + 2 * math.sin(ph + j)
        n = int(length)
        for s in range(n):
            t = s / max(1, n - 1)
            sway = (0.9 * a) * 0.16 * math.sin(3.0 * t + ph * 1.0 + j * 1.6) * t
            xx = bx + sway + base_dx * 1.5 * t
            yy = margin + 0.5 + s * 0.9
            glow(buf, xx, yy, 0.9, TENT, 0.42 * (1 - 0.5 * t))

    # long trailing tentacles: thin filaments with glowing tips
    for j, base_dx in enumerate((-0.92, -0.6, 0.6, 0.92)):
        bx = CX + base_dx * a
        length = 15 + 3 * math.sin(ph * 1.0 + j * 2.0)
        n = int(length)
        for s in range(n):
            t = s / max(1, n - 1)
            sway = 2.6 * math.sin(2.4 * t + ph + j * 1.3) * t
            xx = bx + sway
            yy = margin + 1.0 + s * 1.05
            add(buf, int(round(xx)), int(round(yy)), TENT, 0.5 * (1 - 0.6 * t))
            if s % 4 == 0:
                glow(buf, xx, yy, 0.8, TIP, 0.30 * (1 - 0.5 * t))
        # bright tip bead
        tt = 1.0
        sway = 2.6 * math.sin(2.4 * tt + ph + j * 1.3) * tt
        glow(buf, bx + sway, margin + 1.0 + n * 1.05, 1.0, TIP, 0.6)

    # drifting motes (seamless upward loop)
    motes = ((6, 24), (26, 12), (23, 27), (4, 9), (28, 20), (10, 6))
    for i, (mx, y0) in enumerate(motes):
        span = 30
        yy = (y0 - p * span - i * 3) % span + 1
        drift = 1.2 * math.sin(ph + i)
        glow(buf, mx + drift, yy, 1.0, MOTE, 0.30)

    return to_image(buf)


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    import gifsafe

    size = gifsafe.save(frames, HERE / "jellyfish.gif", duration_ms=130, colors=COLORS)
    ok = "OK" if size <= 8192 else "TOO BIG!"
    print(f"jellyfish.gif: {len(frames)} frames, {size} bytes ({ok}), budget<=8192")

    # save a representative still (mid-relax) + a review strip
    frames[0].save(HERE / "jellyfish.png")
    q = max(1, FRAMES // 4)
    keys = (0, q, 2 * q, 3 * q)   # relaxed, contracting, contracted, relaxing
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (18, 18, 22))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "jellyfish.strip.png")
    print("wrote jellyfish.gif + jellyfish.strip.png")
