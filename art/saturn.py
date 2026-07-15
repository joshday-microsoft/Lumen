"""Saturn — a big ringed planet hung in deep space. A STILL.

Design law for 32x32: one big subject, minimal scene. The planet fills the
frame off-center; its rings sweep across at a tilt, passing BEHIND the globe at
top and IN FRONT at bottom, with a Cassini gap and the planet's own shadow cast
onto the rings. A sparse starfield and a soft space gradient are the whole set.

Rendered at 8x supersample with real sphere shading + ring-plane math, then
box-downsampled to 32x32 for clean edges. Deterministic (fixed star seed).

Run:  .venv\\Scripts\\python.exe art\\saturn.py
Then: POST /image {"path":"saturn.png"}  (or lumen_image)
"""

import math
import random
from pathlib import Path

from PIL import Image

ART = Path(__file__).resolve().parent
SIZE = 32
SS = 8                      # supersample factor
N = SIZE * SS              # 256

# --- scene geometry (in final-32px units, scaled up by SS) ---
CX, CY = 14.2, 15.0        # planet center, slightly left & above middle
PR = 8.6                   # planet radius
RING_TILT = 0.34           # vertical squash of the ring plane (viewed near-edge-on)
RING_IN = 11.2             # inner ring radius (ring-plane units)
RING_OUT = 15.6            # outer ring radius
CASSINI = 13.4             # Cassini division center
CASSINI_W = 0.7            # gap half-width

# light comes from the upper-left, slightly toward the viewer
LX, LY, LZ = -0.60, -0.52, -0.61
_ln = math.sqrt(LX * LX + LY * LY + LZ * LZ)
LX, LY, LZ = LX / _ln, LY / _ln, LZ / _ln


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


# horizontal band palette for the gas giant (top -> bottom of globe)
BANDS = [
    (0.00, (232, 214, 168)),   # bright cream cap
    (0.14, (208, 176, 120)),
    (0.26, (190, 150, 96)),    # amber belt
    (0.40, (224, 204, 158)),   # pale zone
    (0.52, (176, 138, 92)),    # darker belt
    (0.63, (214, 190, 140)),
    (0.76, (198, 162, 108)),
    (0.88, (168, 132, 90)),    # dusky south
    (1.00, (150, 116, 80)),
]


def band_color(t):
    for i in range(len(BANDS) - 1):
        t0, c0 = BANDS[i]
        t1, c1 = BANDS[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return lerp(c0, c1, clamp(f))
    return BANDS[-1][1]


def ring_base(rr):
    """Color + opacity for a ring point at ring-plane radius rr (float, in
    final px). Returns (rgb, alpha) with alpha 0 = no ring here."""
    if rr < RING_IN or rr > RING_OUT:
        return (0, 0, 0), 0.0
    # Cassini division -> a dark near-gap
    gap = clamp(1.0 - max(0.0, CASSINI_W - abs(rr - CASSINI)) / CASSINI_W)
    # brightness varies across the ring width (bright inner B-ring, faint edges)
    u = (rr - RING_IN) / (RING_OUT - RING_IN)
    bright = 0.55 + 0.45 * math.sin(math.pi * clamp(u))      # dome across width
    inner_boost = 0.85 + 0.30 * (1.0 - u)                    # inner ring richer
    base = lerp((150, 138, 120), (226, 214, 186), bright)
    a = (0.28 + 0.72 * bright) * inner_boost * (0.18 + 0.82 * gap)
    return base, clamp(a, 0.0, 1.0)


def in_planet_shadow(x, y, rr):
    """True-ish shadow factor for a ring point: does the ray from this point
    toward the light pass through the planet globe? Cast in the ring plane."""
    dx, dy = x - CX, y - CY
    # only the anti-solar side can be shadowed (points away from the light)
    if dx * (-LX) + dy * (-LY) <= 0:
        return 0.0
    # 2D distance from planet center to the light-ray line through (dx,dy)
    # ray direction is (LX,LY); perpendicular distance = |cross|
    cross = abs(dx * LY - dy * LX)
    if cross < PR * 0.98:
        soft = clamp((PR * 0.98 - cross) / (PR * 0.55))
        return soft
    return 0.0


def render():
    img = Image.new("RGB", (N, N))
    px = img.load()
    rng = random.Random(70)

    # --- background: soft space gradient, deep indigo -> near black ---
    bg = []
    for j in range(N):
        t = j / (N - 1)
        top = (14, 12, 34)
        bot = (3, 2, 10)
        # faint cool nebula glow drifting from upper-left
        bg.append(lerp(top, bot, t))
    for j in range(N):
        for i in range(N):
            c = bg[j]
            # subtle radial vignette brightening near planet for depth
            px[i, j] = (round(c[0]), round(c[1]), round(c[2]))

    # --- stars (behind everything; a few bright, many faint) ---
    stars = []
    for _ in range(90):
        sx = rng.randint(0, N - 1)
        sy = rng.randint(0, N - 1)
        mag = rng.random()
        stars.append((sx, sy, mag))
    for sx, sy, mag in stars:
        # don't scatter stars over the planet disk
        if (sx - CX * SS) ** 2 + (sy - CY * SS) ** 2 < (PR * SS + 2) ** 2:
            continue
        if mag > 0.93:
            col = (255, 250, 240); rad = 2      # rare bright star
        elif mag > 0.75:
            col = (210, 220, 255); rad = 1
        else:
            col = (past := (120 + int(90 * mag)),) * 1 and (150, 160, 200)
            rad = 0
        b = clamp(0.35 + 0.65 * mag)
        col = tuple(round(v * b) for v in col)
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                if dx * dx + dy * dy <= rad * rad + 1:
                    x, y = sx + dx, sy + dy
                    if 0 <= x < N and 0 <= y < N:
                        o = px[x, y]
                        px[x, y] = tuple(min(255, o[k] + col[k]) for k in range(3))

    def blend(x, y, rgb, a):
        if a <= 0:
            return
        o = px[x, y]
        px[x, y] = tuple(round(o[k] * (1 - a) + rgb[k] * a) for k in range(3))

    cxs, cys = CX * SS, CY * SS
    prs = PR * SS

    # --- pass 1: BACK half of the rings (top, behind the globe) ---
    for j in range(N):
        for i in range(N):
            dx = (i - cxs) / SS
            dy = (j - cys) / SS
            rr = math.sqrt(dx * dx + (dy / RING_TILT) ** 2)
            rgb, a = ring_base(rr)
            if a <= 0:
                continue
            if dy >= 0:                # bottom = front, drawn later
                continue
            # occluded by the globe? skip (globe drawn next, on top)
            if dx * dx + dy * dy <= PR * PR:
                continue
            sh = in_planet_shadow(dx + CX, dy + CY, rr)
            rgb = tuple(v * (1 - 0.72 * sh) for v in rgb)
            blend(i, j, rgb, a)

    # --- pass 2: the globe ---
    for j in range(N):
        for i in range(N):
            dx = (i - cxs) / SS
            dy = (j - cys) / SS
            d2 = dx * dx + dy * dy
            if d2 > PR * PR:
                continue
            nx = dx / PR
            ny = dy / PR
            nz2 = 1 - nx * nx - ny * ny
            nz = -math.sqrt(max(0.0, nz2))       # toward viewer (-z)
            # latitude parameter for banding follows the sphere's curve
            lat = clamp((ny + 1.0) / 2.0)
            col = band_color(lat)
            # diffuse shading
            diff = clamp(nx * LX + ny * LY + nz * LZ)
            shade = 0.30 + 0.82 * diff
            # limb darkening
            limb = clamp(1.0 - (d2 / (PR * PR)) ** 3 * 0.5)
            col = tuple(clamp(v * shade * limb, 0, 255) for v in col)
            # tiny specular hint on the sunlit shoulder
            spec = max(0.0, diff) ** 6 * 40
            col = tuple(min(255, v + spec) for v in col)
            px[i, j] = (round(col[0]), round(col[1]), round(col[2]))

    # --- pass 3: FRONT half of the rings (bottom, over the globe) ---
    for j in range(N):
        for i in range(N):
            dx = (i - cxs) / SS
            dy = (j - cys) / SS
            if dy < 0:
                continue
            rr = math.sqrt(dx * dx + (dy / RING_TILT) ** 2)
            rgb, a = ring_base(rr)
            if a <= 0:
                continue
            sh = in_planet_shadow(dx + CX, dy + CY, rr)
            rgb = tuple(v * (1 - 0.72 * sh) for v in rgb)
            blend(i, j, rgb, a)

    return img


def main():
    big = render()
    small = big.resize((SIZE, SIZE), Image.BOX)
    out = ART / "saturn.png"
    small.save(out)
    # a chunky preview for eyeballing quality
    small.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(ART / "saturn.preview.png")
    print(f"wrote {out}  ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
