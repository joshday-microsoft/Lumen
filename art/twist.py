"""Twist — one big colour-cube puzzle turning its top layer, a quarter at a time.

An original loop for the Lumen wall. A 3x3 twisty puzzle fills the panel in
three-quarter view: warm-white top, magenta right face, cyan left face, dark
plastic between the tiles. Nothing else is in the scene. Four times per loop the
TOP LAYER snaps a quarter turn — three eased frames of motion, then one frame
where it arrives and flashes as it clicks home.

Two things make the loop close exactly and for free:

  * the turn is cumulative geometry, not a colour permutation. Every sticker on
    the top layer is a real quad rotated about the vertical axis by the running
    angle, so after 4 x 90 degrees the cube IS the starting cube — asserted
    pixel-for-pixel, which also proves the schedule sums to a whole turn;
  * one corner tile on the top face is amber instead of white. On a solved cube
    a top-layer turn is invisible from above; that single odd tile is what makes
    the rotation legible on the face you see most, and it laps the cube once per
    loop.

The faces that come around from the back matter: rotating +Z into +X means the
right face's top band shows the colour that was on the left, so all four side
colours cycle through the two visible faces over the loop.

The camera sits at azimuth 34, not 45. At 45 the cube is symmetric about the
screen, so a layer 45 degrees into its turn ends up perfectly axis-aligned: its
top face projects to a plain rectangle and the whole layer reads as a white card
hovering over the cube. Off-axis, no sampled angle lands in that pose.

Run:  .venv\\Scripts\\python.exe art\\twist.py   -> twist.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZE = 32
SS = 2                                  # supersample factor
TURNS = 4
MOTION = 3                              # frames of movement per quarter turn
FRAMES = TURNS * (MOTION + 1)           # + 1 arrival/flash frame each
DURATION_MS = 130

AZ, EL = math.radians(34.0), math.radians(30.0)
STICKER = 0.82                          # tile size as a fraction of a cubie face
MARGIN = 0.8                            # panel px kept clear at the widest frame

# original palette, deliberately not the classic puzzle's six
FACE = {
    (0, 1, 0): (255, 246, 226),         # up    — warm white
    (0, -1, 0): (90, 96, 118),          # down  — never seen
    (1, 0, 0): (255, 46, 104),          # right — magenta
    (-1, 0, 0): (124, 255, 61),         # left  — lime  (comes round on a turn)
    (0, 0, 1): (44, 190, 255),          # front — cyan
    (0, 0, -1): (178, 102, 255),        # back  — violet (comes round on a turn)
}
ODD_CUBIE = (1, 1, 1)                   # the one amber tile, front-top corner
ODD = (255, 158, 26)
BODY = (34, 32, 42)                     # plastic between the tiles
BG_BANDS = [(9, 9, 18), (12, 11, 24), (15, 13, 28)]
LIGHT = (0.55, 0.75, 0.35)
AMBIENT, DIFFUSE = 0.38, 0.62
FLASH = 1.20                            # arrival brighten on the turned layer

DIRS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

F = (math.cos(EL) * math.sin(AZ), math.sin(EL), math.cos(EL) * math.cos(AZ))
R = (math.cos(AZ), 0.0, -math.sin(AZ))
U = (F[1] * R[2] - F[2] * R[1], F[2] * R[0] - F[0] * R[2], F[0] * R[1] - F[1] * R[0])
LN = math.sqrt(sum(c * c for c in LIGHT))
L = tuple(c / LN for c in LIGHT)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)


def ease(t):
    """Snap out, settle in — a speedcuber's flick, not a constant-rate spin."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


def quads(theta):
    """Every cubie face at layer angle `theta`, back to front, backface-culled.

    Interior faces are emitted too (as plain plastic): when the top layer is
    mid-turn the seam opens up, and without them you would see straight through
    the cube to the background.
    """
    # The angle is periodic, so SAY it is: at theta=0 the cube is symmetric and
    # its tile edges land exactly on supersample boundaries, where an
    # infinitesimal nudge (radians(360) carries a 2.4e-16 sine) flips whole
    # subpixel columns in or out of the raster and the closing frame lands ~20
    # pixels off. radians(360) % 2pi is exactly 0.0, so this costs nothing.
    theta %= 2 * math.pi
    out = []
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                if i == j == k == 0:
                    continue
                for d in DIRS:
                    ax = 0 if d[0] else (1 if d[1] else 2)
                    outer = (i, j, k)[ax] == d[ax]
                    cen = (i + d[0] * 0.5, j + d[1] * 0.5, k + d[2] * 0.5)
                    ua, va = [DIRS[2 * n] for n in range(3) if n != ax]
                    corners = [
                        tuple(cen[m] + ua[m] * sx * 0.5 + va[m] * sy * 0.5 for m in range(3))
                        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
                    ]
                    n = d
                    if j == 1:                      # the turning layer
                        corners = [rot_y(c, theta) for c in corners]
                        n = rot_y(d, theta)
                    if dot(n, F) <= 0.03:
                        continue
                    col = FACE[d]
                    if outer and d == (0, 1, 0) and (i, j, k) == ODD_CUBIE:
                        col = ODD
                    depth = sum(dot(c, F) for c in corners) / 4.0
                    shade = AMBIENT + DIFFUSE * max(0.0, dot(n, L))
                    out.append((depth, len(out), corners, col if outer else None,
                                shade, j == 1))
    # Quantised depth, then generation order. Adjacent faces of the same corner
    # cubie tie exactly, and a raw sort lets a 1e-16 angle (radians(360) is not
    # radians(0)) swap which one is painted last — enough to move the pixels on
    # their shared edge and break the closing assert. Real faces are never
    # within 1e-6 of each other in depth.
    out.sort(key=lambda q: (round(q[0], 6), q[1]))
    return out


def angles():
    """The running layer angle for every frame: rest, then the eased steps."""
    seq = []
    for t in range(TURNS):
        seq.append((math.radians(90.0 * t), True))                  # arrival
        for k in range(1, MOTION + 1):
            seq.append((math.radians(90.0 * t + 90.0 * ease(k / MOTION)), False))
    return seq


ANGLES = angles()


def fit():
    """One scale/offset for the whole loop, from the widest frame's bounds."""
    xs, ys = [], []
    for theta, _ in ANGLES:
        for _, _, corners, _, _, _ in quads(theta):
            for c in corners:
                xs.append(dot(c, R))
                ys.append(-dot(c, U))
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    scale = (SIZE - 2 * MARGIN) / span
    cx = SIZE / 2.0 - (max(xs) + min(xs)) / 2.0 * scale
    cy = SIZE / 2.0 - (max(ys) + min(ys)) / 2.0 * scale
    return scale, cx, cy


SCALE, CX, CY = fit()


def project(p):
    return (dot(p, R) * SCALE * SS + CX * SS, -dot(p, U) * SCALE * SS + CY * SS)


def tint(col, shade):
    return tuple(max(0, min(255, round(c * shade))) for c in col)


def background():
    img = Image.new("RGB", (SIZE * SS, SIZE * SS))
    d = ImageDraw.Draw(img)
    # flat bands, not a gradient: every row is one LZW run, and the background
    # is re-encoded in all 16 full frames
    step = SIZE * SS / len(BG_BANDS)
    for b, col in enumerate(BG_BANDS):
        d.rectangle([0, round(b * step), SIZE * SS, round((b + 1) * step)], fill=col)
    return img


BG = background()


def frame(theta, flash):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    for _, _, corners, col, shade, turning in quads(theta):
        poly = [project(c) for c in corners]
        # one flat tone for every plastic face, not a shaded one: the frame
        # between the tiles is a big share of the cube, and giving each face its
        # own near-black splits that whole grid into three LZW alphabets for a
        # difference you cannot see at 32 px (worth ~600 bytes of the budget)
        d.polygon(poly, fill=BODY)
        if col is None:
            continue
        cen = tuple(sum(c[m] for c in corners) / 4.0 for m in range(3))
        inset = [tuple(cen[m] + (c[m] - cen[m]) * STICKER for m in range(3)) for c in corners]
        s = shade * (FLASH if (flash and turning) else 1.0)
        d.polygon([project(c) for c in inset], fill=tint(col, s))
    # Box-filter down, blend tones and all. At this size a cubie face is ~7 px,
    # so the plastic gap between tiles is UNDER one pixel: it can only exist as
    # a tonal line. Rasterising it as geometry — SS=1, or SS=2 snapped back to
    # the flat painted palette — breaks every gap into dashes and the cube stops
    # reading as 3x3 at all. Those blends cost ~2 KB of LZW, which is why this
    # loop buys its frames back: three motion frames per turn, not six.
    return img.resize((SIZE, SIZE), Image.BOX)


def build():
    return [frame(theta, flash) for theta, flash in ANGLES]


if __name__ == "__main__":
    frames = build()

    # the loop has to close on geometry alone: a full 360 of the top layer is
    # the cube we started with, same flash state, same pixels — which also
    # checks the schedule really does add up to one whole turn
    assert abs(ANGLES[-1][0] - math.radians(360.0)) < 1e-12, "the four turns do not sum to 360"
    closing = frame(ANGLES[-1][0], True)
    assert list(closing.getdata()) == list(frames[0].getdata()), "loop does not close"
    assert list(frame(*ANGLES[3]).getdata()) == list(frames[3].getdata()), "not deterministic"

    # and it has to actually move: mid-turn frames differ from the rest frames
    def diff(a, b):
        return sum(1 for p, q in zip(a.getdata(), b.getdata()) if p != q)

    moved = diff(frames[0], frames[3])
    print(f"  moving pixels rest->mid-turn: {moved}")
    assert moved > 250, "the turn is barely visible"
    assert diff(frames[0], frames[7]) > 120, "the cube looks identical after a quarter turn"

    # the amber tile must lap the cube — its centroid should travel
    def amber(im):
        pts = [(x, y) for y in range(SIZE) for x in range(SIZE)
               if im.getpixel((x, y))[0] > 170 and 90 < im.getpixel((x, y))[1] < 205
               and im.getpixel((x, y))[2] < 90]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None

    half = FRAMES // 2                      # two turns on: the tile is 180 round
    a0, a2 = amber(frames[0]), amber(frames[half])
    print(f"  amber tile: f0={a0} f{half}={a2}")
    assert a0 and a2 and math.dist(a0, a2) > 5, "the odd tile is not travelling"

    keys = list(range(FRAMES))
    cols, rows = 14, 2
    strip = Image.new("RGB", (cols * (SIZE * 4 + 4) - 4, rows * (SIZE * 4 + 4) - 4), (20, 20, 24))
    for n, f in enumerate(keys):
        strip.paste(frames[f].resize((SIZE * 4, SIZE * 4), Image.NEAREST),
                    ((n % cols) * (SIZE * 4 + 4), (n // cols) * (SIZE * 4 + 4)))
    strip.save(HERE / "twist.strip.png")
    frames[0].resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "twist-big.png")
    frames[0].save(HERE / "twist.png")

    used = len({c for f in frames for c in f.getdata()})
    print(f"  distinct colours in the loop: {used}")

    # Pick the palette on MEASURED error, not on file size. Nearly all of those
    # tones are the sub-pixel blends drawing the gaps between the tiles, so a
    # small table does not just posterise the shading — it rounds the grid lines
    # away and the cube stops reading as 3x3. Smallest table that lands under a
    # mean error of 2/765, which is invisible on the panel.
    import gifsafe
    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "twist.gif", duration_ms=DURATION_MS, colors=colors)
        check = Image.open(HERE / "twist.gif")
        err = 0
        for i, f in enumerate(frames):
            check.seek(i)
            err += sum(sum(abs(p[m] - q[m]) for m in range(3))
                       for p, q in zip(check.convert("RGB").getdata(), f.getdata()))
        err /= len(frames) * SIZE * SIZE
        print(f"  colors={colors:3d} -> {size} bytes, mean error {err:.2f}")
        if size <= 8192 and err < 2.0 and best is None:
            best = (colors, size)
    assert best, "no palette fits the 8 KB budget cleanly"
    size = gifsafe.save(frames, HERE / "twist.gif", duration_ms=DURATION_MS, colors=best[0])
    print(f"twist.gif: {len(frames)} frames, {best[0]} colors, {size} bytes (OK)")
    print("wrote twist.gif + twist.strip.png + twist.png")
