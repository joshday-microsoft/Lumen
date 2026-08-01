"""Chameleon — one big lizard on a branch, running colour through itself.

An original loop for the Lumen wall. The chameleon fills the panel: helmeted
head and a swivelling turret eye at the right, body sloping down to the left,
tail coiled into a spiral, two pincer feet clamped on a branch. Nothing about
the animal moves except two things, and both of them close the loop exactly:

  * a hue wave travels head-to-tail along the body's arc length, one full turn
    of the colour wheel per loop, so frame N is frame 0 again;
  * the eye's aperture orbits once around the turret in the same period,
    speeding up and dwelling twice on the way round — the sly beat.

Everything else (silhouette, shading, branch, background) is computed once and
reused, which is also what keeps this inside the panel's 8 KB budget: only the
~430 skin pixels change from frame to frame.

The coil is the hard part at 32x32. Ring spacing is under 3 px, so adjacent
turns would fuse into a blob; every skin pixel that sits next to a MUCH later
part of the tail (arc-length jump, not distance) is darkened into a cast
shadow, which is what actually separates the turns.

Run:  .venv\\Scripts\\python.exe art\\chameleon.py   -> chameleon.gif (+ strip)
"""

import colorsys
import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 24
DURATION_MS = 130

HUE_SPAN = 0.85          # turns of the colour wheel visible along the body
HUE_START = 0.30

# spine of the animal: nose first, then head, neck, shoulder, hip
SPINE = [
    (31.2, 14.6, 1.2),
    (29.4, 13.4, 2.7),
    (27.3, 11.9, 3.9),
    (24.4, 11.2, 4.6),
    (21.8, 12.6, 4.4),
    (19.0, 14.4, 5.1),
    (16.2, 16.2, 4.9),
    (13.6, 17.7, 3.9),
    (11.8, 18.7, 2.7),
    (10.6, 19.3, 1.9),
]

# tail: a spiral continuing from the last spine point
TAIL_C = (6.6, 21.2)
TAIL_R0, TAIL_R1 = 4.43, 1.40
TAIL_TH0, TAIL_TH1 = 1.70, 0.50
TAIL_TH0_DEG = -25.4
TAIL_SWEEP = 400.0

# legs: (start, knee, foot, r_start, r_end)
LEGS = [
    ((19.6, 17.8), (20.6, 21.8), (19.8, 25.4), 1.9, 1.2),   # foreleg
    ((12.8, 19.6), (11.2, 22.8), (12.8, 25.4), 1.9, 1.2),   # hind leg
]

# the casque — the helmet ridge over the back of the skull. Without it the head
# is just a rounded blob; it is the single silhouette cue that says "chameleon"
CASQUE = [(28.8, 9.4), (26.2, 3.8), (22.4, 4.6), (19.8, 9.6), (22.2, 12.8)]
HEAD_C = (24.6, 11.0)

EYE_C = (26.9, 11.1)
EYE_R = 3.3
APERTURE_ORBIT = 1.15
APERTURE_R = 1.55
PUPIL_R = 0.85

MOUTH = [(24, 15), (25, 15), (26, 15), (27, 15), (28, 15), (29, 15), (30, 14), (31, 14)]

BRANCH_TOP = 26
BRANCH_BOT = 29

BG_EDGE = (7, 13, 17)
BG_MID = (20, 38, 36)
BARK_DK = (42, 28, 19)
BARK = (92, 62, 38)
BARK_HI = (138, 100, 60)
IRIS = (255, 198, 62)
IRIS_DK = (176, 116, 24)
CLAW = (226, 214, 186)
LIGHT = (-0.55, -0.83)          # from the upper left


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hashp(x, y, salt=0):
    h = ((x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)) & 0xFFFFFFFF
    h = (h * 2654435761) & 0xFFFFFFFF
    return ((h >> 13) ^ h) & 0xFF


def samples():
    """Dense (x, y, radius, arclen) samples down the spine and out the tail."""
    pts = []
    for i in range(len(SPINE) - 1):
        x0, y0, r0 = SPINE[i]
        x1, y1, r1 = SPINE[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(seg / 0.2))
        for k in range(n):
            t = k / n
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r0 + (r1 - r0) * t))
    n = 460
    for k in range(n + 1):
        t = k / n
        ang = math.radians(TAIL_TH0_DEG + TAIL_SWEEP * t)
        rad = TAIL_R0 + (TAIL_R1 - TAIL_R0) * t
        th = TAIL_TH0 + (TAIL_TH1 - TAIL_TH0) * (t ** 0.75)
        pts.append((TAIL_C[0] + rad * math.cos(ang), TAIL_C[1] + rad * math.sin(ang), th))

    out, arc = [], 0.0
    for i, (x, y, r) in enumerate(pts):
        if i:
            arc += math.hypot(x - pts[i - 1][0], y - pts[i - 1][1])
        out.append([x, y, r, arc])
    total = out[-1][3]
    for p in out:
        p[3] /= total
    return out


PTS = samples()


def dorsal_ridge(skin):
    """Serrated ridge: every other column's topmost back pixel, lit.

    Spikes pushed OUTSIDE the silhouette were the first attempt and they came
    out as five scattered dots — at 32x32 a detached 1 px bump is dirt on the
    panel, not a ridge. Riding the existing top edge costs no extra pixels and
    actually reads as serration.
    """
    top = {}
    for (x, y), (u, s, n, kind) in skin.items():
        if kind != "body" or not (0.05 < s < 0.50):
            continue
        if x not in top or y < top[x][0]:
            top[x] = (y, s, n)
    return [(x, y, s, n) for x, (y, s, n) in top.items() if x % 2 == 0]


def leg_pixels():
    """Skin mask for the two legs, plus the claw pixels that grip the branch."""
    body, claws = {}, set()
    for (a, k, b, r0, r1) in LEGS:
        n = 90
        for i in range(n + 1):
            t = i / n
            # quadratic bend through the knee
            px = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * k[0] + t * t * b[0]
            py = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * k[1] + t * t * b[1]
            r = r0 + (r1 - r0) * t
            for yy in range(SIZE):
                for xx in range(SIZE):
                    if (xx - px) ** 2 + (yy - py) ** 2 <= r * r:
                        d = math.hypot(xx - px, yy - py)
                        prev = body.get((xx, yy))
                        if prev is None or d / r < prev[0]:
                            body[(xx, yy)] = (d / r, 0.30 + 0.30 * t,
                                              (xx - px, yy - py))
        fx, fy = b
        for dx in (-2, -1, 1, 2):
            claws.add((int(round(fx + dx)), BRANCH_TOP))
        claws.add((int(round(fx)), BRANCH_TOP - 1))
    return body, claws


def build_maps():
    """Static per-pixel geometry: arclen, inside-ness, normal, kind."""
    skin = {}
    for y in range(SIZE):
        for x in range(SIZE):
            best = None
            for (px, py, r, s) in PTS:
                d2 = (x - px) ** 2 + (y - py) ** 2
                if d2 <= r * r:
                    if best is None or s > best[0]:
                        d = math.sqrt(d2)
                        best = (s, d / r, (x - px, y - py))
            if best is not None:
                skin[(x, y)] = (best[1], best[0], best[2], "body")

    mask = Image.new("1", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).polygon(CASQUE, fill=1)
    mpx = mask.load()
    for y in range(SIZE):
        for x in range(SIZE):
            if not mpx[x, y] or (x, y) in skin:
                continue
            d = math.hypot(x - HEAD_C[0], y - HEAD_C[1])
            # cap the inside-ness: the casque is a flat plate catching the
            # light, not a sphere, and letting u reach 1 turns it into a dark
            # lump sitting on a bright head
            skin[(x, y)] = (min(0.55, d / 9.0), 0.045,
                            (x - HEAD_C[0], y - HEAD_C[1]), "casque")

    legs, claws = leg_pixels()
    for (p, (u, s, n)) in legs.items():
        if p not in skin:
            skin[p] = (u, s, n, "leg")

    for (x, y, s, n) in dorsal_ridge(skin):
        skin[(x, y)] = (0.55, s, n, "crest")

    # Cast shadow where a later turn of the coil lies over an earlier one:
    # neighbours that are close in space but FAR apart in arc length. One full
    # turn of the coil is ~0.4 of the total arc, so the threshold has to sit
    # well above the ~0.07 jump between the casque and the neck behind it —
    # at 0.055 this rule quietly halved the brightness of the whole helmet.
    shadow = set()
    for (x, y), (u, s, n, kind) in skin.items():
        if s < 0.30:                            # tail only; the head has no coil
            continue
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                q = skin.get((x + dx, y + dy))
                if q and q[1] > s + 0.18 and dx * dx + dy * dy <= 4:
                    shadow.add((x, y))
    return skin, claws, shadow


SKIN, CLAWS, SHADOW = build_maps()


def background():
    # Flat horizontal bands, not a radial vignette. Every row is then a single
    # LZW run, and since the background is re-encoded in all 24 full frames
    # that choice alone is worth ~2 KB of the 8 KB budget.
    img = Image.new("RGB", (SIZE, SIZE))
    for y in range(SIZE):
        g = min(1.0, max(0.0, (y - 2) / 26.0))
        row = lerp(BG_EDGE, BG_MID, round(g * 2) / 2.0)
        for x in range(SIZE):
            img.putpixel((x, y), row)

    # the branch: a lit top edge, body, dark underside, sparse grain
    for y in range(BRANCH_TOP, BRANCH_BOT + 1):
        t = (y - BRANCH_TOP) / (BRANCH_BOT - BRANCH_TOP)
        base = lerp(BARK_HI, BARK_DK, t ** 0.7)
        for x in range(SIZE):
            img.putpixel((x, y), base)
    for x in range(SIZE):                       # a few grain streaks only
        if hashp(x, 0, 9) > 214:
            img.putpixel((x, BRANCH_TOP + 1), lerp(BARK, BARK_DK, 0.45))
        if hashp(x, 0, 17) > 226:
            img.putpixel((x, BRANCH_TOP + 2), lerp(BARK, BARK_HI, 0.35))
    return img


BG = background()


def skin_rgb(s, u, n, kind, phase):
    hue = (HUE_START + s * HUE_SPAN - phase) % 1.0
    nx, ny = n
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    lam = max(0.0, nx * LIGHT[0] + ny * LIGHT[1])
    belly = max(0.0, min(1.0, ny * 0.9 + 0.15))

    v = 0.70 + 0.36 * lam
    v *= 1.0 - 0.26 * (u ** 1.8)                # rounded volume
    v *= 1.0 + 0.16 * belly                     # pale underside
    sat = 0.94 - 0.34 * belly
    # blues and violets at equal V read as a black hole on an LED panel; lift
    # the cold half of the wheel so the wave keeps its weight all the way round
    v *= 1.0 + 0.30 * max(0.0, math.cos(2 * math.pi * (hue - 0.66)))

    band = math.cos(s * 24.0)                   # lateral flank banding
    v *= 1.0 + 0.11 * band
    sat *= 1.0 - 0.10 * band

    if kind == "crest":
        v *= 1.22
    elif kind == "casque":
        v *= 1.10 - 0.25 * u                    # lit ridge falling into shadow
    elif kind == "leg":
        v *= 0.80
    return v, sat, hue


def frame(f):
    img = BG.copy()
    px = img.load()
    phase = f / FRAMES

    for (x, y), (u, s, n, kind) in SKIN.items():
        v, sat, hue = skin_rgb(s, u, n, kind, phase)
        if (x, y) in SHADOW:
            v *= 0.42
            sat *= 0.85
        v = max(0.05, min(1.0, v))
        r, g, b = colorsys.hsv_to_rgb(hue, max(0.0, min(1.0, sat)), v)
        px[x, y] = (round(r * 255), round(g * 255), round(b * 255))

    # eye turret: a cone of skin, then the aperture orbiting once per loop
    u_t = f / FRAMES
    ang = 2 * math.pi * (u_t + 0.14 * math.sin(4 * math.pi * u_t))
    ax = EYE_C[0] + APERTURE_ORBIT * math.cos(ang)
    ay = EYE_C[1] + APERTURE_ORBIT * math.sin(ang)
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - EYE_C[0], y - EYE_C[1])
            if d > EYE_R:
                continue
            base = SKIN.get((x, y))
            s = base[1] if base else 0.06
            v, sat, hue = skin_rgb(s, min(1.0, d / EYE_R), (x - EYE_C[0], y - EYE_C[1]),
                                   "body", phase)
            v *= 1.28 - 0.42 * (d / EYE_R)      # domed lid, ridged rim
            if d > EYE_R - 1.0:
                v *= 0.62
            v = max(0.05, min(1.0, v))
            r, g, b = colorsys.hsv_to_rgb(hue, max(0.0, min(1.0, sat)), v)
            px[x, y] = (round(r * 255), round(g * 255), round(b * 255))

            da = math.hypot(x - ax, y - ay)
            if da <= PUPIL_R:
                px[x, y] = (10, 8, 10)
            elif da <= APERTURE_R:
                px[x, y] = IRIS if (x - ax) + (y - ay) < 0 else IRIS_DK

    # mouth line, drawn AFTER the turret so the lid cannot swallow the jaw
    for (x, y) in MOUTH:
        if (x, y) in SKIN:
            u, s, n, kind = SKIN[(x, y)]
            v, sat, hue = skin_rgb(s, u, n, kind, phase)
            r, g, b = colorsys.hsv_to_rgb(hue, min(1.0, sat * 1.15), max(0.04, v * 0.28))
            px[x, y] = (round(r * 255), round(g * 255), round(b * 255))
    px[30, 12] = tuple(round(c * 0.45) for c in px[30, 12])     # nostril

    for (x, y) in CLAWS:
        if 0 <= x < SIZE and 0 <= y < SIZE and (x, y) not in SKIN:
            px[x, y] = CLAW
    return img


def build():
    return [frame(f) for f in range(FRAMES)]


if __name__ == "__main__":
    frames = build()

    body_px = sum(1 for k in SKIN if SKIN[k][3] == "body")
    print(f"  skin pixels: {len(SKIN)} (body {body_px}), coil shadow {len(SHADOW)}")
    assert 240 < len(SKIN) < 700, "silhouette is the wrong size for the panel"
    assert len(SHADOW) >= 6, "coil turns are not being separated"
    assert not any(SKIN[p][1] < 0.30 for p in SHADOW), "head must never be shadowed"

    # the loop must close: frame 0 and frame FRAMES are the same phase, and the
    # aperture must come back to where it started
    for f in (0,):
        a = frame(f)
        assert list(a.getdata()) == list(frames[f].getdata()), "frames not deterministic"
    ang_end = 2 * math.pi * (1.0 + 0.14 * math.sin(4 * math.pi))
    drift = (ang_end - 2 * math.pi + math.pi) % (2 * math.pi) - math.pi
    assert abs(drift) < 1e-6, f"eye orbit does not close ({drift})"

    # the hue really has to travel — compare mean colour of two distant frames
    def mean(im):
        d = list(im.getdata())
        return tuple(sum(c[i] for c in d) / len(d) for i in range(3))
    m0, m6 = mean(frames[0]), mean(frames[FRAMES // 2])
    print(f"  mean rgb f0={tuple(round(v) for v in m0)} f{FRAMES//2}={tuple(round(v) for v in m6)}")
    assert sum(abs(m0[i] - m6[i]) for i in range(3)) > 12, "colour wave is not moving"

    # previews first — look at the art before arguing with the encoder
    keys = range(0, FRAMES, 3)
    strip = Image.new("RGB", (SIZE * 4 * len(keys) + (len(keys) - 1) * 4, SIZE * 4), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 4, SIZE * 4), Image.NEAREST), (i * (SIZE * 4 + 4), 0))
    strip.save(HERE / "chameleon.strip.png")
    frames[0].resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "chameleon-big.png")
    frames[0].save(HERE / "chameleon.png")

    import gifsafe
    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "chameleon.gif", duration_ms=DURATION_MS, colors=colors)
        print(f"  colors={colors:3d} -> {size} bytes")
        # BIGGEST palette that fits, not smallest file: this piece is a hue
        # sweep, and a 16-colour table posterises the wave into visible steps
        if size <= 8192:
            best = (colors, size)
    assert best, "no palette fits the 8 KB budget"
    size = gifsafe.save(frames, HERE / "chameleon.gif", duration_ms=DURATION_MS, colors=best[0])
    print(f"chameleon.gif: {len(frames)} frames, {best[0]} colors, {size} bytes (OK)")
    print("wrote chameleon.gif + chameleon.strip.png + chameleon.png")
