"""Hourglass — one big glass turning itself over, forever.

An original loop for the Lumen wall. The top bulb drains grain by grain into a
growing mound below; when the last of it falls the whole hourglass flips
end-over-end and the run starts again. The flip is what closes the loop: the
drained state mirrored top-to-bottom IS the full state, so frame 0 follows the
last frame exactly with no cut. Patient / meditative.

Everything the loop draws is mirror-symmetric about y=15.5 (wood, glass, sheen,
sand speckle), which is what makes that identity hold pixel-for-pixel.

Run:  .venv\\Scripts\\python.exe art\\hourglass.py   -> hourglass.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
DRAIN = 16                      # frames of falling sand, p = 1 .. 0
FLIP = (30, 60, 90, 120, 150)   # the turn-over; 180 == frame 0

CX = 15.5
TOP_ROWS = range(4, 16)         # top bulb
BOT_ROWS = range(16, 28)        # bottom bulb

BG_EDGE = (7, 8, 16)            # dark room
BG_HAZE = (46, 30, 18)          # warm haze pooled around the neck
WOOD_DK = (58, 32, 18)
WOOD = (112, 64, 32)
WOOD_HI = (158, 100, 54)
GLASS = (96, 122, 146)          # cool wall of the bulb
GLASS_IN = (20, 27, 38)         # tinted interior
SHEEN = (196, 228, 248)
SAND_DK = (176, 112, 36)
SAND = (232, 168, 58)
SAND_HI = (255, 216, 128)
STREAM = (255, 240, 190)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def half_width(y):
    """Half-width of the glass interior at row y, or None outside the bulbs."""
    if 4 <= y <= 15:
        t = (15 - y) / 11.0
    elif 16 <= y <= 27:
        t = (y - 16) / 11.0
    else:
        return None
    w = 1.35 + 9.15 * (t ** 0.65)
    if y in (4, 27):
        w *= 0.86               # rounded shoulder at the very top/bottom
    return w


INNER = {}
for _y in range(SIZE):
    _w = half_width(_y)
    if _w is not None:
        INNER[_y] = [x for x in range(SIZE) if abs(x - CX) < _w]

INTERIOR = {(x, y) for y, xs in INNER.items() for x in xs}
TOP_AREA = sum(len(INNER[y]) for y in TOP_ROWS)
BOT_AREA = sum(len(INNER[y]) for y in BOT_ROWS)


def speckle(x, y):
    """Deterministic grain, symmetric under a top-to-bottom flip."""
    k = min(y, 31 - y) * 32 + x
    h = (k * 2654435761) & 0xFFFFFFFF
    return ((h >> 13) ^ h) & 0xFF


def top_sand(p):
    """Pixels of sand left in the upper bulb; p=1 full, p=0 empty.

    The surface dips in the middle as it drains (the funnel), and the dip
    vanishes at both extremes so a full bulb is exactly, entirely full.
    """
    if p <= 0.0005:
        return set()
    if p >= 0.9995:
        return {(x, y) for y in TOP_ROWS for x in INNER[y]}
    target = p * TOP_AREA
    dip = 2.4 * math.sin(math.pi * p)

    def count(level):
        w = half_width(min(15, max(4, int(round(level)))))
        got = set()
        for y in TOP_ROWS:
            for x in INNER[y]:
                edge = level + dip * (1.0 - min(1.0, abs(x - CX) / w))
                if y >= edge:
                    got.add((x, y))
        return got

    lo, hi = 3.0, 16.5
    for _ in range(24):
        mid = (lo + hi) / 2
        if len(count(mid)) >= target:
            lo = mid
        else:
            hi = mid
    return count(lo)


def bottom_sand(q):
    """Mound in the lower bulb; q=1-p. Peaks under the stream, flat when full."""
    if q <= 0.0005:
        return set()
    if q >= 0.9995:
        return {(x, y) for y in BOT_ROWS for x in INNER[y]}
    target = q * BOT_AREA
    peak = 2.4 * math.sin(math.pi * q)

    def count(level):
        # falloff measured at the mound's outer rim (the wider row), so the
        # cone spans the whole surface instead of collapsing to a spike
        w = half_width(min(27, max(16, int(round(level + peak)))))
        got = set()
        for y in BOT_ROWS:
            for x in INNER[y]:
                edge = level - peak * (1.0 - min(1.0, abs(x - CX) / w))
                if y >= edge:
                    got.add((x, y))
        return got

    # sand count DECREASES as the level moves down the panel, exactly like the
    # top bulb: keep lo on the too-much side, hi on the too-little side
    lo, hi = 15.5, 28.5
    for _ in range(24):
        mid = (lo + hi) / 2
        if len(count(mid)) >= target:
            lo = mid
        else:
            hi = mid
    return count(lo)


def background():
    """Dark room with a warm haze pooled at the neck.

    Banded on purpose: a smooth gradient gives every row a different byte
    pattern and roughly doubles the encoded size, and this panel only has an
    8 KB budget. Three flat steps read the same at 32x32 and compress.
    """
    img = Image.new("RGB", (SIZE, SIZE))
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - CX, y - CX)
            g = math.exp(-(d / 11.0) ** 2) * 0.9
            band = round(g * 3) / 3.0
            img.putpixel((x, y), lerp(BG_EDGE, BG_HAZE, band))
    return img


def glass_layer(p, f):
    """The hourglass itself on transparent film, so the flip can move it."""
    lay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = lay.load()

    def put(x, y, c):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = (c[0], c[1], c[2], 255)

    # wood caps: outer edge dark, then a lit face, then shadow into the glass
    for y in range(1, 4):
        shade = (WOOD_DK, WOOD_HI, WOOD)[y - 1]
        for x in range(3, 29):
            put(x, y, shade)
            put(x, 31 - y, shade)

    # corner posts holding the two caps apart
    for y in range(4, 28):
        put(3, y, WOOD)
        put(28, y, WOOD)
    for y in (4, 27):
        put(3, y, WOOD_HI)
        put(28, y, WOOD_HI)

    # glass: tinted interior, then a wall hugging each row
    for y, xs in INNER.items():
        for x in xs:
            put(x, y, GLASS_IN)
        put(xs[0] - 1, y, GLASS)
        put(xs[-1] + 1, y, GLASS)

    # a sheen down the left of both bulbs (mirror-symmetric, so the flip closes)
    for y in range(6, 11):
        put(INNER[y][0] - 1, y, SHEEN)
        put(INNER[31 - y][0] - 1, 31 - y, SHEEN)

    top = top_sand(p)
    bot = bottom_sand(1.0 - p)
    for pack in (top, bot):
        for (x, y) in pack:
            # lit only where sand meets air INSIDE its own bulb — a bulb filled
            # to the glass has no free surface, which is what keeps the two
            # extreme states exact mirrors of each other
            up = (x, y - 1)
            same_bulb = up in INTERIOR and ((y - 1) < 16) == (y < 16)
            if same_bulb and up not in pack:
                c = SAND_HI
            else:
                s = speckle(x, y)
                c = SAND_HI if s > 214 else (SAND_DK if s < 66 else SAND)
            put(x, y, c)

    # the falling stream: a shimmering two-pixel trickle from neck to mound
    if 0.0005 < p < 0.9995:
        floor = min((y for (x, y) in bot), default=28)
        for y in range(16, floor):
            h = ((y * 73 + f * 151) * 2654435761) & 0xFF
            put(15, y, STREAM if h & 1 else SAND_HI)
            put(16, y, SAND_HI if h & 2 else STREAM)
        for x in (15, 16):          # lit throat
            put(x, 15, STREAM)
    return lay


def edge_on():
    """The hourglass seen exactly edge-on, mid-flip — a lit bar."""
    lay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = lay.load()
    for x in range(3, 29):
        core = SAND if 6 <= x <= 25 else WOOD
        px[x, 15] = (*lerp(core, SAND_HI, 0.35), 255)
        px[x, 16] = (*lerp(core, WOOD_DK, 0.35), 255)
    return lay


def compose(layer):
    img = background().convert("RGBA")
    img.alpha_composite(layer)
    return img.convert("RGB")


def build():
    frames = []
    for f in range(DRAIN):
        p = 1.0 - f / (DRAIN - 1)
        frames.append(compose(glass_layer(p, f)))

    drained = glass_layer(0.0, DRAIN)
    for a in FLIP:
        c = abs(math.cos(math.radians(a)))
        h = round(SIZE * c)
        if h < 3:
            lay = edge_on()
        else:
            squashed = drained.resize((SIZE, h), Image.NEAREST)
            lay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
            lay.paste(squashed, (0, (SIZE - h) // 2))
        if a > 90:                              # past edge-on: it's over
            lay = lay.transpose(Image.FLIP_TOP_BOTTOM)
        frames.append(compose(lay))
    return frames


if __name__ == "__main__":
    frames = build()

    # sanity: the sand must actually MOVE. Eyeballing the contact strip missed
    # a flipped bisection invariant that pinned the lower bulb full in every
    # frame, so the piece played as an hourglass that refills itself. Check the
    # fill fractions, not the vibe.
    print("  frame     p   top%   bot%")
    prev_top, prev_bot = None, None
    for f in range(DRAIN):
        p = 1.0 - f / (DRAIN - 1)
        t = len(top_sand(p)) / TOP_AREA
        b = len(bottom_sand(1.0 - p)) / BOT_AREA
        print(f"  {f:5d} {p:5.2f} {t:6.2f} {b:6.2f}")
        assert abs(t - p) < 0.07, f"top bulb off target at frame {f}"
        assert abs(b - (1.0 - p)) < 0.07, f"bottom bulb off target at frame {f}"
        if prev_top is not None:
            assert t <= prev_top + 1e-9, f"top bulb refilled at frame {f}"
            assert b >= prev_bot - 1e-9, f"bottom bulb drained at frame {f}"
        prev_top, prev_bot = t, b

    # the drained glass flipped must BE the full glass (seamless loop)
    a = glass_layer(0.0, 0).transpose(Image.FLIP_TOP_BOTTOM)
    b = glass_layer(1.0, 0)
    assert list(a.getdata()) == list(b.getdata()), "flip does not close the loop"

    import gifsafe
    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "hourglass.gif", duration_ms=170, colors=colors)
        print(f"  colors={colors:3d} -> {size} bytes")
        if best is None or size < best[1]:
            best = (colors, size)
    size = gifsafe.save(frames, HERE / "hourglass.gif", duration_ms=170, colors=best[0])
    ok = "OK" if size <= 8192 else "TOO BIG!"
    print(f"hourglass.gif: {len(frames)} frames, {best[0]} colors, {size} bytes ({ok})")

    keys = (0, 3, 6, 9, 12, 15, DRAIN, DRAIN + 1, DRAIN + 2, DRAIN + 3, DRAIN + 4)
    strip = Image.new("RGB", (SIZE * 4 * len(keys) + (len(keys) - 1) * 4, SIZE * 4), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 4, SIZE * 4), Image.NEAREST),
                    (i * (SIZE * 4 + 4), 0))
    strip.save(HERE / "hourglass.strip.png")
    frames[6].resize((SIZE, SIZE)).save(HERE / "hourglass.png")
    print("wrote hourglass.gif + hourglass.strip.png + hourglass.png")
