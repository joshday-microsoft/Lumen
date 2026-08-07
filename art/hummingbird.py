"""Hummingbird — one big hovering bird, wings smeared into a fan.

An original loop for the Lumen wall. The bird fills the panel on the diagonal:
needle bill buried in a violet trumpet flower at the lower left, bronze-green
body, fanned tail sweeping to the lower right. It never travels anywhere. The
whole show is what a hovering hummingbird actually is:

  * the wings, which are never a shape — they are a MOTION BLUR. Each frame
    integrates the blade over the exposure window just behind its current
    angle, on top of a faint full-arc ghost, because the wing is everywhere in
    its stroke faster than an eye can resolve;
  * the gorget, which is not pigment but structural colour: dead maroon from
    most angles, and once per loop, at the top of the hover bob, it catches the
    sun and detonates into ruby.

5 wingbeats per loop, 4 frames each, so the stroke closes exactly on frame 20.
The bob is one slow sine over the same period, and the flash rides its peak.

The wing is drawn as a translucent membrane that DARKENS and COOLS what is
behind it, not as a pale blade: the background is a warm out-of-focus garden
haze, and a light-coloured smear on it is invisible (the same trap the honeybee
wings fell into).

Run:  .venv\\Scripts\\python.exe art\\hummingbird.py   -> hummingbird.gif (+ strip)
"""

import colorsys
import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 16
DURATION_MS = 90
BEATS = 4                       # wingbeats per loop; FRAMES/BEATS = 4 frames each

# ---------------------------------------------------------------- palette ---
# Deep garden shade, banded flat so every row is one LZW run.
#
# This started as a warm amber haze and it was the wrong call for the reason
# the honeybee's wings taught: the beat of this piece is a RED flash, and a red
# flash on an orange field is a smudge. Cool and dark gives the gorget, the
# bird's green and the pale wing smear somewhere to be bright.
BANDS = [
    (0, (36, 64, 56)),
    (6, (28, 54, 48)),
    (13, (21, 43, 39)),
    (20, (15, 33, 30)),
    (26, (10, 24, 22)),
]
BOKEH = [(6.5, 5.0, 4.2), (25.0, 3.5, 3.4), (29.0, 12.0, 2.8)]
BOKEH_C = (74, 116, 88)

PETAL = (168, 96, 220)
PETAL_DK = (96, 44, 140)
PETAL_HI = (216, 168, 246)
THROAT = (60, 22, 88)
POLLEN = (252, 224, 128)
STEM = (78, 112, 58)
STEM_DK = (44, 66, 36)

BILL = (108, 106, 116)          # a black bill vanishes on a dark field; this
BILL_DK = (52, 50, 58)          # is the needle catching the light
EYE = (14, 14, 16)
CHEEK = (128, 176, 118)         # lifted so the eye has something to sit on
SPOT = (238, 236, 226)
FOOT = (44, 34, 32)
TAIL_TIP = (236, 232, 220)

GORGET_DARK = (68, 16, 30)
GORGET_HOT = (250, 26, 58)
GORGET_CORE = (255, 158, 150)
# handed to the encoder so median cut cannot drop the flash (see gifsafe.save)
KEEP = (GORGET_HOT, GORGET_CORE, (214, 40, 66), (176, 30, 54), GORGET_DARK)

WING_COOL = (150, 172, 194)     # what the membrane pulls the background toward
WING_EDGE = (214, 230, 244)     # the leading edge, catching the light

LIGHT = (-0.58, -0.81)          # from the upper left

# ---------------------------------------------------------------- geometry --
# spine, bill base -> tail base. y is the resting pose; the bob offsets it.
# The radii are NOT monotonic: there is a deliberate pinch behind the skull.
# Without it the head is just the fat end of a capsule and the whole animal
# reads as a leaf — the neck is what makes a bird a bird at this size.
SPINE = [
    (12.2, 16.8, 1.50),
    (13.4, 15.9, 3.00),
    (15.2, 14.8, 4.30),         # skull
    (17.8, 15.0, 3.40),         # neck — the pinch
    (20.2, 16.4, 5.20),         # shoulder / breast
    (22.8, 18.8, 5.50),
    (25.2, 21.4, 4.30),
    (26.9, 23.3, 2.50),
]

BILL_BASE = (12.0, 16.9)
BILL_TIP = (4.4, 21.6)

HEAD_C = (15.2, 14.8)
EYE_C = (13.6, 13.9)
SPOT_C = (16.4, 13.3)
GORGET_C = (15.2, 18.3)
GORGET_R = 3.8

TAIL_ROOT = (26.6, 23.0)
TAIL_N = 5
# steeper than the body's own axis (~40 deg): a tail laid along the line the
# body is already travelling just extends the blob, it never reads as a tail
TAIL_MID_DEG = 66.0             # screen-space, pointing down-right
TAIL_LEN = 6.6

WING_ROOT = (19.6, 14.2)        # near wing, at the shoulder
WING_ROOT_FAR = (21.4, 16.0)    # far wing, behind and below
WING_LEN = 12.2
WING_W = 3.15
STROKE_MID = 60.0               # degrees, measured with y up
STROKE_SPAN = 68.0

# The flower is CROPPED by the left edge rather than sitting in the corner as
# a small blob: half a big trumpet reads as a flower, a whole small one reads
# as a smudge. Same lesson the violin piece learned about composing a crop.
FLOWER_C = (0.6, 21.8)
FLOWER_R = 5.2

MOTES = [(25.5, 9.0, 0.0), (9.2, 6.0, 0.55)]


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def blend(dst, src, a):
    a = clamp(a)
    return tuple(round(dst[i] + (src[i] - dst[i]) * a) for i in range(3))


def hashp(x, y, salt=0):
    h = ((x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)) & 0xFFFFFFFF
    h = (h * 2654435761) & 0xFFFFFFFF
    return ((h >> 13) ^ h) & 0xFF


def spine_samples(dy):
    """Dense (x, y, r, s) samples down the body, s in [0, 1] nose to tail."""
    pts = []
    for i in range(len(SPINE) - 1):
        x0, y0, r0 = SPINE[i]
        x1, y1, r1 = SPINE[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(seg / 0.18))
        for k in range(n):
            t = k / n
            pts.append((x0 + (x1 - x0) * t, y0 + dy + (y1 - y0) * t, r0 + (r1 - r0) * t))
    pts.append((SPINE[-1][0], SPINE[-1][1] + dy, SPINE[-1][2]))

    out, arc = [], 0.0
    for i, (x, y, r) in enumerate(pts):
        if i:
            arc += math.hypot(x - pts[i - 1][0], y - pts[i - 1][1])
        out.append((x, y, r, arc))
    total = out[-1][3] or 1.0
    return [(x, y, r, a / total) for (x, y, r, a) in out]


def body_map(dy):
    """Per-pixel (u, s, normal) for the bird's body at this bob offset."""
    pts = spine_samples(dy)
    skin = {}
    for y in range(SIZE):
        for x in range(SIZE):
            best = None
            for (px, py, r, s) in pts:
                d2 = (x - px) ** 2 + (y - py) ** 2
                if d2 <= r * r:
                    d = math.sqrt(d2)
                    if best is None or d / r < best[0]:
                        best = (d / r, s, (x - px, y - py))
            if best is not None:
                skin[(x, y)] = best
    return skin


def body_rgb(u, s, n):
    nx, ny = n
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    lam = max(0.0, nx * LIGHT[0] + ny * LIGHT[1])
    # only what genuinely faces DOWN goes pale — at ny*0.95+0.10 the whole lower
    # half of the bird turned buff and the body read as a white blob with a
    # green cap on it
    belly = clamp(ny * 0.85 - 0.18)

    v = 0.44 + 0.54 * lam
    v *= 1.0 - 0.24 * (u ** 1.8)
    v = v * (1.0 - 0.55 * belly) + 0.62 * belly          # grey underside
    sat = 0.94 - 0.60 * belly
    # bronze-green iridescence: the hue shimmers in bands down the back rather
    # than sitting on one flat green, which is what makes it read as feather
    hue = 0.378 + 0.040 * math.sin(s * 7.0) - 0.030 * lam

    # dark face and crown — but only so dark: on a dark field the head has to
    # keep enough value to stay attached to the body
    if s < 0.26:
        k = 1.0 - s / 0.26
        v *= 1.0 - 0.40 * k
        sat *= 1.0 - 0.20 * k
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, clamp(sat), clamp(v, 0.03, 1.0))
    return (round(r * 255), round(g * 255), round(b * 255))


def wing_blade(root, ang_deg, weight, acc, mode="sum"):
    """Accumulate one blade of the wing into acc[(x, y)] -> (body, edge).

    mode="sum" builds the haze (many faint blades adding up); mode="max" lays
    down a discrete blade without letting overlaps double it.
    """
    a = math.radians(ang_deg)
    dx, dy = math.cos(a), -math.sin(a)               # screen coords, y down
    px_, py_ = -dy, dx                               # perpendicular
    n = 46
    for i in range(n + 1):
        t = i / n
        # widest around 40% out, tapering to a point — a blade, not a paddle
        w = WING_W * (0.34 + 0.66 * math.sin(math.pi * min(1.0, t ** 0.82)) ** 0.7)
        # a slight backward sweep of the tip, the way a real wing bows
        bow = 0.9 * math.sin(math.pi * t) * (1.0 if ang_deg > STROKE_MID else -1.0)
        cx = root[0] + dx * t * WING_LEN + px_ * bow
        cy = root[1] + dy * t * WING_LEN + py_ * bow
        # every blade of the smear radiates from the same root, so alpha piles
        # up there and the shoulder turns into an ink blot. Thin the inner
        # stretch — but never to zero, or the fan detaches from the bird and
        # floats over it as a separate grey cloud.
        wt = weight * (0.42 + 0.58 * clamp(t / 0.22) ** 0.8)
        rad = int(w) + 2
        for yy in range(int(cy) - rad, int(cy) + rad + 1):
            for xx in range(int(cx) - rad, int(cx) + rad + 1):
                if not (0 <= xx < SIZE and 0 <= yy < SIZE):
                    continue
                d = math.hypot(xx - cx, yy - cy)
                if d > w:
                    continue
                b, e = acc.get((xx, yy), (0.0, 0.0))
                v = b + wt if mode == "sum" else max(b, wt)
                acc[(xx, yy)] = (v, max(e, wt * (0.35 + 0.65 * (d / w) ** 2)))


def wing_pass(root, phase, gain):
    """The wing at this instant, plus one ghost of where it just was.

    This started out as a proper motion blur — an exposure smear over a ghost
    of the whole stroke, weighted by dwell time so it piled up at the
    turnarounds. It is the right physics and it was unusable: a soft
    translucent field is exactly what a 32 px panel on a 16-64 colour table
    cannot hold, and every version of it landed as a flat lilac slab sitting
    over the bird like weather. What reads at this size is a SHAPE. So the
    wing is a real blade with a lit edge, and the speed is carried by one
    fading ghost behind it and by the beat being faster than the eye.
    """
    def theta(p):
        return STROKE_MID + STROKE_SPAN * math.cos(2 * math.pi * p)

    blades = {}
    wing_blade(root, theta(phase - 0.16), 0.24, blades, mode="max")   # the ghost
    wing_blade(root, theta(phase), 0.64, blades, mode="max")          # the wing

    out = {}
    for p, (b, e) in blades.items():
        a = clamp(b * gain, 0.0, 0.92)
        a = round(a * 8) / 8.0                        # band it: flat runs, small file
        if a > 0.0:
            out[p] = (a, clamp(e * gain))
    return out


def background():
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        col = BANDS[0][1]
        for (y0, c) in BANDS:
            if y >= y0:
                col = c
        for x in range(SIZE):
            px[x, y] = col

    # a few soft blown-out gaps in the foliage behind the bird — enough depth
    # that the dark field reads as shade on a bright day, not as night
    for (bx, by, br) in BOKEH:
        for y in range(SIZE):
            for x in range(SIZE):
                d = math.hypot(x - bx, y - by)
                if d <= br:
                    a = 0.40 * (1.0 - (d / br) ** 1.6)
                    px[x, y] = blend(px[x, y], BOKEH_C, round(a * 4) / 4.0)

    # (a big foreground leaf lived in the near corner for one revision. It was
    # the same green as the bird and at 32 px the tail simply merged into it —
    # the corner is better left as depth than filled with a rival shape.)

    # stem, running down off the bottom-left corner
    for i in range(40):
        t = i / 39
        sx = FLOWER_C[0] + 1.2 + 2.4 * t
        sy = FLOWER_C[1] + 3.4 + 7.0 * t
        for w in (0, 1):
            x, y = int(round(sx + w)), int(round(sy))
            if 0 <= x < SIZE and 0 <= y < SIZE:
                px[x, y] = STEM if w == 0 else STEM_DK

    # trumpet flower: a cone opening up-right toward the bird, five lobes
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x - FLOWER_C[0], y - FLOWER_C[1]
            d = math.hypot(dx, dy)
            if d > FLOWER_R + 1.2:
                continue
            ang = math.atan2(-dy, dx)
            lobe = FLOWER_R * (0.86 + 0.20 * math.cos(5 * (ang - 0.35)))
            if d <= lobe:
                t = d / max(lobe, 0.01)
                c = lerp(THROAT, PETAL, clamp(t * 1.5))
                c = lerp(c, PETAL_HI, clamp((t - 0.62) * 2.0) * 0.7)
                if hashp(x, y, 5) > 226:
                    c = lerp(c, PETAL_DK, 0.35)
                px[x, y] = c
    for (sx, sy) in ((4.6, 20.0), (3.4, 18.9), (5.2, 21.6)):
        x, y = int(round(sx)), int(round(sy))
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = POLLEN
    return img


BG = background()


def draw_tail(px, dy, spread):
    for i in range(TAIL_N):
        f = (i / (TAIL_N - 1)) - 0.5
        ang = math.radians(TAIL_MID_DEG + spread * f * 2.0)
        ln = TAIL_LEN * (1.0 - 0.22 * abs(f) * 2.0)
        n = 22
        for k in range(n + 1):
            t = k / n
            x = TAIL_ROOT[0] + math.cos(ang) * t * ln
            y = TAIL_ROOT[1] + dy + math.sin(ang) * t * ln
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < SIZE and 0 <= yi < SIZE):
                continue
            # alternate feathers a value step apart, or the fan fuses with the
            # body into one green wedge and the bird loses its back end
            shade = 0.56 + 0.30 * (1.0 - abs(f) * 2.0) - 0.16 * t
            shade *= 1.0 if i % 2 == 0 else 0.68
            r, g, b = colorsys.hsv_to_rgb(0.375, 0.84, clamp(shade, 0.06, 1.0))
            px[xi, yi] = (round(r * 255), round(g * 255), round(b * 255))
            # white tips on the OUTER feathers only, one pixel each: five
            # feather tips converging near the corner merged into a single
            # white block that read as a hole punched in the panel
            if t > 0.985 and i in (0, TAIL_N - 1):
                px[xi, yi] = blend(px[xi, yi], TAIL_TIP, 0.75)


def frame(f):
    img = BG.copy()
    px = img.load()

    u = (f % FRAMES) / FRAMES
    dy = 0.85 * math.sin(2 * math.pi * u)
    beat = (f * BEATS / FRAMES) % 1.0

    # far wing first — behind everything, dimmer, a quarter beat ahead so the
    # pair never collapses into one symmetric blob
    for (x, y), (a, e) in wing_pass(WING_ROOT_FAR, beat + 0.06, 0.55).items():
        px[x, y] = blend(blend(px[x, y], WING_COOL, a * 0.8), WING_EDGE, e * 0.30)

    draw_tail(px, dy, 15.0 + 6.0 * math.cos(2 * math.pi * beat))

    skin = body_map(dy)
    for (x, y), (uu, s, n) in skin.items():
        c = body_rgb(uu, s, n)
        h = hashp(x, y, 3)                  # a sparse feather grain, deterministic
        if h > 214:
            c = tuple(round(v_ * 0.88) for v_ in c)
        elif h < 26:
            c = tuple(min(255, round(v_ * 1.10)) for v_ in c)
        px[x, y] = c

    # Rim light along the lit contour. On a dark field a shaded body meets the
    # background at nearly the same value and the silhouette dissolves; one
    # bright pixel on the upper-left edge is what keeps the bird a solid.
    for (x, y), (uu, s, n) in skin.items():
        if uu < 0.62:
            continue
        if (x - 1, y) in skin and (x, y - 1) in skin and (x - 1, y - 1) in skin:
            continue
        ln = math.hypot(n[0], n[1]) or 1.0
        if (n[0] / ln) * LIGHT[0] + (n[1] / ln) * LIGHT[1] < 0.25:
            continue                        # only the edge the light reaches
        px[x, y] = blend(px[x, y], (206, 240, 194), 0.22 + 0.16 * uu)

    # needle bill, straight into the flower
    n = 26
    for k in range(n + 1):
        t = k / n
        x = BILL_BASE[0] + (BILL_TIP[0] - BILL_BASE[0]) * t
        y = BILL_BASE[1] + dy * (1.0 - t) + (BILL_TIP[1] - BILL_BASE[1]) * t
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < SIZE and 0 <= yi < SIZE:
            px[xi, yi] = BILL if t < 0.88 else lerp(BILL_DK, THROAT, 0.5)
            if yi + 1 < SIZE and t < 0.9:            # its own shadow underneath
                px[xi, yi + 1] = blend(px[xi, yi + 1], BILL_DK, 0.55)

    # gorget: structural colour. Dead maroon for most of the loop, then one
    # three-frame detonation at the top of the bob.
    flash = clamp(1.0 - abs(((u - 0.25) % 1.0 + 0.5) % 1.0 - 0.5) / 0.085)
    flash = flash * flash * (3 - 2 * flash)
    for (x, y), (uu, s, nn) in skin.items():
        d = math.hypot(x - GORGET_C[0], y - (GORGET_C[1] + dy))
        if d > GORGET_R or nn[1] < -0.35 or s > 0.46:
            continue
        k = clamp(1.0 - (d / GORGET_R) ** 2.4)
        c = lerp(GORGET_DARK, GORGET_HOT, clamp(flash * (0.35 + 0.65 * k)))
        # the white-hot core is ONE or two pixels. At k > 0.72 with a 0.6 blend
        # it covered most of the patch and the whole gorget went pale pink —
        # a flash that loses its colour isn't a flash, it's a hole
        if flash > 0.88 and k > 0.94:
            c = lerp(c, GORGET_CORE, (flash - 0.88) * 2.6)
        px[x, y] = blend(px[x, y], c, 0.30 + 0.70 * k)

    # bloom: the flash spills a little light onto the chin, breast and the air
    # just off the throat. Kept tight (r 3.8, low alpha) — the tin robot's eyes
    # taught this piece's ancestors that a wide glow just washes the whole face
    if flash > 0.02:
        for (x, y) in skin:                     # onto the bird only — spilling
            d = math.hypot(x - GORGET_C[0],     # it into the sky just smudged
                           y - (GORGET_C[1] + dy))   # the background orange
            if GORGET_R < d <= 4.0:
                px[x, y] = blend(px[x, y], GORGET_HOT,
                                 0.30 * flash * (1.0 - (d - GORGET_R) / (4.0 - GORGET_R)))

    # A black eye on a near-black face is nothing at all. Lift a cheek around
    # it first so the eye has something to be dark against, then stamp it.
    for (x, y), (uu, s, nn) in skin.items():
        d = math.hypot(x - EYE_C[0], y - (EYE_C[1] + dy))
        if d <= 2.4:
            k = clamp(1.0 - d / 2.4) ** 0.8
            px[x, y] = blend(px[x, y], CHEEK, 0.62 * k)
    ex, ey = int(round(EYE_C[0])), int(round(EYE_C[1] + dy))
    if 0 <= ex < SIZE and 0 <= ey < SIZE:
        px[ex, ey] = EYE
        if ey - 1 >= 0:
            px[ex, ey - 1] = blend(px[ex, ey - 1], EYE, 0.62)
        if ex + 1 < SIZE:
            px[ex + 1, ey] = blend(px[ex + 1, ey], EYE, 0.50)
    # the post-ocular streak is a hint, not a headlight: at full white it was
    # brighter than the eye and the bird read as having one big pale eye
    sx, sy = int(round(SPOT_C[0])), int(round(SPOT_C[1] + dy))
    if 0 <= sx < SIZE and 0 <= sy < SIZE:
        px[sx, sy] = blend(px[sx, sy], SPOT, 0.60)
    for (fx, fy) in ((20.9, 22.8), (22.1, 23.4)):       # tucked feet
        xi, yi = int(round(fx)), int(round(fy + dy))
        if 0 <= xi < SIZE and 0 <= yi < SIZE:
            px[xi, yi] = FOOT

    # near wing last: it passes IN FRONT of the body
    for (x, y), (a, e) in wing_pass(WING_ROOT, beat, 1.0).items():
        px[x, y] = blend(blend(px[x, y], WING_COOL, a), WING_EDGE, e * 0.42)

    for (mx, my, ph) in MOTES:
        t = (u + ph) % 1.0
        x = int(round(mx + 1.6 * math.sin(2 * math.pi * t)))
        y = int(round(my - 2.5 * t + 2.5 * (t > 0.999)))
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = blend(px[x, y], POLLEN, 0.55)
    return img


def build():
    return [frame(f) for f in range(FRAMES)]


if __name__ == "__main__":
    frames = build()

    skin0 = body_map(0.0)
    print(f"  body pixels: {len(skin0)}")
    # a hummingbird's body is small next to its wings by definition — what has
    # to fill the panel is the bird PLUS the fan, so the body bound is modest
    assert 110 < len(skin0) < 460, "the bird is the wrong size for the panel"

    # the loop must close: frame FRAMES is frame 0 again (bob, beat and flash
    # all share the same period, so this is the real test of all three)
    assert list(frame(FRAMES).getdata()) == list(frames[0].getdata()), "loop does not close"
    assert list(frame(3).getdata()) == list(frames[3].getdata()), "frames not deterministic"

    # the wings must actually move: consecutive frames differ, and the two
    # mid-stroke frames of a beat (same angle, opposite travel) are not twins
    def diff(a, b):
        da, db = list(a.getdata()), list(b.getdata())
        return sum(1 for i in range(len(da)) if da[i] != db[i])
    d01 = diff(frames[0], frames[1])
    d13 = diff(frames[1], frames[3])
    print(f"  changed px: f0->f1 {d01}, f1->f3 (mid vs mid) {d13}")
    assert d01 > 60, "wingbeat is not reading"
    assert d13 > 20, "the two mid-stroke frames are identical — blur has no direction"

    # the gorget has to detonate and then go out again
    # measured ON the gorget, not over the whole bird: a box wide enough to
    # include the green body is dominated by it and reports nothing
    def redness(im, box=(13, 18, 19, 23)):
        px = im.load()
        return sum(px[x, y][0] - px[x, y][1] for x in range(box[0], box[2])
                   for y in range(box[1], box[3]))
    peak = redness(frames[FRAMES // 4])                  # the top of the bob
    rest = sorted(redness(f_) for f_ in frames)[len(frames) // 2]
    print(f"  gorget redness: peak {peak}, median {rest}")
    assert peak > rest + 900, "the gorget flash is not firing"
    assert peak == max(redness(f_) for f_ in frames), "the flash is off its beat"

    keys = range(0, FRAMES, 2)
    strip = Image.new("RGB", (SIZE * 4 * len(keys) + (len(keys) - 1) * 4, SIZE * 4), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 4, SIZE * 4), Image.NEAREST), (i * (SIZE * 4 + 4), 0))
    strip.save(HERE / "hummingbird.strip.png")
    hero = frames[FRAMES // 4]                          # the frame it flashes on
    hero.resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "hummingbird-big.png")
    hero.save(HERE / "hummingbird.png")

    import gifsafe

    def quant_error(colors):
        """Mean squared error of gifsafe's own quantisation at this table size.

        Chosen on measured error, not on file size: the smallest file here is
        a 16-colour table, and 16 colours turns the violet flower grey.
        """
        montage = Image.new("RGB", (SIZE * len(frames), SIZE))
        for i, f_ in enumerate(frames):
            montage.paste(f_, (i * SIZE, 0))
        pal = montage.quantize(colors=colors, dither=Image.Dither.NONE)
        got = list(montage.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB").getdata())
        want = list(montage.getdata())
        return sum((got[i][c] - want[i][c]) ** 2 for i in range(len(want)) for c in range(3)) / len(want)

    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "hummingbird.gif", duration_ms=DURATION_MS,
                            colors=colors, keep=KEEP)
        err = quant_error(colors)
        print(f"  colors={colors:3d} -> {size} bytes, err {err:7.1f}")
        if size <= 8192 and (best is None or err < best[2]):
            best = (colors, size, err)
    assert best, "no palette fits the 8 KB budget"
    size = gifsafe.save(frames, HERE / "hummingbird.gif", duration_ms=DURATION_MS,
                        colors=best[0], keep=KEEP)

    # the flash has to survive the encoder, not just the render: check the
    # ENCODED frame, where the first version of this piece came back purple
    enc = Image.open(HERE / "hummingbird.gif")
    enc.seek(FRAMES // 4)
    hot_px = [enc.convert("RGB").getpixel((x, y)) for x in range(14, 18) for y in range(17, 20)]
    reddest = max(hot_px, key=lambda c: c[0] - max(c[1], c[2]))
    print(f"  encoded gorget peak: {reddest}")
    assert reddest[0] > 170 and reddest[0] - reddest[2] > 70, \
        f"the encoder ate the flash: {reddest}"
    print(f"hummingbird.gif: {len(frames)} frames, {best[0]} colors, {size} bytes (OK)")
    print("wrote hummingbird.gif + hummingbird.strip.png + hummingbird.png")
