"""One big octopus coming out of the dark water — a painting.

The first cephalopod in the ledger, the first invertebrate with limbs, and the
first subject that is SOFT-BODIED AND RADIAL: everything before it has had a
front, a back and a spine, or else has been shell, metal, stone or paper. An
octopus has a bag, two eyes, and arms going every way at once.

Why it belongs on /paint rather than in a GIF: an octopus BLANCHES. When it is
hiding it goes pale grey, and when it decides to show itself the chromatophores
fire and the colour floods across the skin in a wave, in about a second. That
is a performance, not a loop — so the panel paints the animal pale first, in
the order it would arrive (the back arms reach out, the mantle descends, the
front arms reach out over the top), and then ONE WAVE of colour runs down it
from the crown of the mantle out to every arm tip at once, ordered by distance
along the animal's own body rather than by anything on screen. The suckers do
not get a pass of their own: they are pale, so they simply STOP flushing, and
the wave reveals them as it goes past.

The geometry is three ideas.

The bag is a SMOOTH UNION of five ellipses — mantle, eye band, web, and a bump
for each eye — melted together with a polynomial smin. That is what gives an
octopus its particular silhouette (a pear that bulges twice at the sides and
then gathers), and because the union is a signed distance field, the shading
falls out of it for free: the surface normal is the field's own gradient rolled
toward the screen as you move in from the edge, so the whole head is one puffed
balloon lit by one lamp, and the eye bumps light themselves.

An arm is a tapering tube on a curling radial, and the ONE thing that makes it
read as an octopus arm rather than a worm is that it has two different sides.
Each arm carries a roll that changes along its length, face(t) = sin(roll0 +
twist*t): where that is positive the underside is toward you, so the skin goes
pale and the suckers show; where it is negative you are looking at the dark
back of the arm and there are none. That is why the hero arm curling across the
bottom is a double row of cream dots and the ones sweeping up past the mantle
are plain — and it is the only reason the coil reads as a coil.

And the arms are separated by DARK, not by light. Six limbs of the same skin
under the same lamp land at the same value where they cross, and a pair like
that reads as one wide arm no matter how carefully each tube is shaded. What
tells them apart is the shadow the near one throws on the far one, so the
occluder is looked up directly: step from a point toward the lamp and ask
whether something nearer is standing there. It is also the only reason the
crown does not read as a solid apron.

Run (perform):  .venv\\Scripts\\python.exe art\\kraken.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\kraken.py preview
"""

import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                                  # supersampling per axis

# ------------------------------------------------------------------ light ---
# One lamp, high and to the left and slightly in front — sun through water. The
# fill comes back UP off the sand, which is what keeps the undersides of the
# arms from going to the value of the water they are lying against.
def _n3(v):
    m = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / m, v[1] / m, v[2] / m)


LIGHT = _n3((-0.36, -0.80, 0.48))
FILL = _n3((0.30, 0.74, 0.60))

# ------------------------------------------------------------------- body ---
# The mantle is CROPPED by the top edge, the way the violin was cropped by the
# frame (2026-08-06): a whole octopus scaled to fit is a diagram, and the bag
# running off the top of the panel is what says the animal is bigger than the
# wall it is on.
APEX = (15.5, 0.0)                      # where the colour wave starts
CROWN = (15.6, 18.6)                    # where the arms meet

#            cx     cy    rx    ry   blend with what came before
BAG = ((15.5,  6.6,  7.10, 8.30, None),
       (15.5, 13.2,  7.50, 4.20, 2.00),   # the eye band, wider than the mantle
       (15.6, 18.2,  5.10, 3.30, 1.80),   # the web the arms come out of
       ( 9.4, 12.8,  3.95, 3.50, 0.95),   # eye bumps, blended hard so they stay
       (21.8, 12.8,  3.95, 3.50, 0.95))   # bumps instead of melting into the head

# The eyes are deliberately OVERSIZE. At 32px a correctly-proportioned eye is
# three pixels and the animal has no face at all; these are most of the width of
# the head, which is what makes the thing look back at you.
EYE_L = (9.4, 12.8)
EYE_R = (21.8, 12.8)
IRIS_R = 2.90
PUPIL_W, PUPIL_H = 2.30, 0.70

# ------------------------------------------------------------------- arms ---
# (bearing°, length, curl°, base radius, roll0, twist, depth) — depth < 0 is
# behind the bag.
#
# The arms are POLAR, not hand-drawn, and that is a legibility fix rather than a
# convenience. The first version placed eight cubic beziers by eye: they crossed
# each other, bunched three-deep across the bottom, and the whole lower half of
# the panel rendered as one continuous bright mass with no water in it — eight
# arms that cannot be told apart are not eight arms, they are a puddle. Here an
# arm leaves the crown on its own bearing and simply travels outward while its
# bearing drifts, so the gap between two neighbours GROWS with distance and is
# guaranteed by arithmetic. Near the crown they all merge, which is right (that
# is the web); by six pixels out there is dark water between every pair.
#
# And there are SIX of them, not eight, which is the composition decision the
# piece turned on. An octopus has eight arms and the first four attempts drew
# all eight: at this size that is eight three-pixel limbs in fourteen rows of
# panel, and they merged into a single tan apron with no water in it — the exact
# failure the design law warns about, one big element beating a field of small
# ones. Cropping is what fixed it, the way the violin was cropped to its lower
# bout (2026-08-06): the mantle now runs off the top of the panel, and you see
# the arms you would actually see from in front, with the other two behind the
# web where they belong. Six arms at five pixels wide read as an octopus; eight
# at three pixels read as a mop.
ARMS = (
    (203.0, 16.5, -54.0, 2.85, -1.20, 1.40, -3),   # up past the mantle, left
    (-23.0, 16.5,  52.0, 2.75, -1.00, -1.60, -2),  # up past the mantle, right
    (166.0, 14.5, -46.0, 2.95, -0.90, 2.00, -1),   # out left, behind
    (137.0, 14.0, -56.0, 3.10, -1.30, 2.20,  1),   # down-left, in front
    ( 34.0, 15.5,  62.0, 3.00, -1.50, 2.00,  2),   # down-right, in front
    # THE HERO: thickest, nearest, curls hard across the bottom with its
    # underside toward you the whole way, so it is a double row of cream dots
    # and it is the thing that says octopus before anything else does
    ( 74.0, 15.0,  82.0, 3.40,  0.90, 0.90,  3),
)

R_START = 2.30                          # how far out of the crown an arm begins
TILT = 1.34                             # how far a tube's normal rolls over

# ---------------------------------------------------------------- palette ---
# Deep green-teal water, and an animal that runs from rust to ochre. The water
# is the coldest and darkest thing in the frame by a wide margin, because the
# beat of the piece is a warm flush and a warm flush on a warm field is a smudge
# (the hummingbird, 2026-08-07).
WATER_TOP = (10, 38, 48)
WATER_LOW = (2, 9, 15)
MOTE = (168, 214, 216)

# Blanched: what an octopus is when it does not want to be seen. Pale, cold,
# and almost colourless — it has to be a long way from the flushed skin or the
# whole performance is invisible.
PALE = (198, 196, 200)
PALE_UNDER = (216, 214, 214)

SKIN = (238, 118, 58)                   # the flush
SKIN_DEEP = (124, 44, 32)               # blotches
SKIN_UNDER = (234, 170, 126)            # the arms' pale side — warm TAN, not
                                        # cream: a pale underside plus a rim
                                        # light is how the first pass turned
                                        # every arm into a peach stick
SUCKER = (248, 224, 198)
SUCKER_RIM = (132, 74, 56)

IRIS_HOT = (246, 190, 72)
IRIS_COOL = (168, 108, 28)
PUPIL = (18, 12, 14)
GLINT = (255, 250, 236)

# The shaded half of the contour gets a rim too, but a DARK cold one. A cool rim
# bright enough to see is still a lightening, and applied all the way round it
# turns every tube into a bright-edged ribbon with a dark middle — the exact
# inverse of how a lit cylinder looks.
RIM_WARM = (255, 206, 158)
RIM_COLD = (58, 96, 112)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale(c, f):
    return tuple(clamp(v * f, 0.0, 255.0) for v in c)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def val(c):
    return max(c)


def hash2(x, y, s):
    h = (int(x) * 374761393 + int(y) * 668265263 + s * 1442695040) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, y, cell, seed):
    gx, gy = x / cell, y / cell
    x0, y0 = math.floor(gx), math.floor(gy)
    tx, ty = gx - x0, gy - y0
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    a = hash2(x0, y0, seed)
    b = hash2(x0 + 1, y0, seed)
    c = hash2(x0, y0 + 1, seed)
    d = hash2(x0 + 1, y0 + 1, seed)
    top = a + (b - a) * tx
    return top + ((c + (d - c) * tx) - top) * ty


# ------------------------------------------------------------------- shape ---
def smin(a, b, k):
    """Polynomial smooth minimum — the melt between two parts of the bag."""
    h = clamp(0.5 + 0.5 * (b - a) / k)
    return b + (a - b) * h - k * h * (1.0 - h)


def bag_sdf(p):
    """Signed distance to the head: negative inside, roughly in pixels."""
    d = None
    for cx, cy, rx, ry, k in BAG:
        e = (math.hypot((p[0] - cx) / rx, (p[1] - cy) / ry) - 1.0) * min(rx, ry)
        d = e if d is None else smin(d, e, k)
    return d


def bag_normal(p, inside):
    """Puffed-balloon normal: the field's gradient, rolled toward the screen.

    A 2D silhouette has no normals of its own, so the shading has to be invented
    — but it must be invented CONSISTENTLY or the head reads flat. Taking the
    SDF's gradient (which points straight out of the shape everywhere, including
    around each eye bump) and tilting it from face-on at the middle to edge-on
    at the contour gives one rounded solid, and the bumps light themselves.

    The profile is a HEMISPHERE, not a ramp, and that is the difference between
    a bag and a loaf. A linear roll-off saturates: every point further than the
    bulge distance from an edge gets the identical face-on normal, and since the
    mantle is thirteen pixels wide a four-pixel ramp left a flat column four
    pixels across running the whole height of the head — the render came back as
    a rust brick with the corners rounded off. sqrt(1 - q²) is still tilting at
    eighty per cent of the way in, so the curvature survives all the way to the
    middle and the mantle finally reads as something inflated.
    """
    h = 0.35
    gx = bag_sdf((p[0] + h, p[1])) - bag_sdf((p[0] - h, p[1]))
    gy = bag_sdf((p[0], p[1] + h)) - bag_sdf((p[0], p[1] - h))
    m = math.hypot(gx, gy) or 1.0
    gx, gy = gx / m, gy / m
    q = clamp(inside / 7.5)
    s = math.sqrt(max(0.0, 1.0 - q * q))
    return _n3((gx * s, gy * s, math.sqrt(max(0.03, 1.0 - s * s))))


class Arm:
    """A tapering tube on a curling radial, indexed so the lookup is cheap.

    The centreline is polar about the crown: the arm's bearing drifts by `curl`
    over its length while its distance from the crown grows steadily, which is
    what a tentacle does and, unlike a hand-placed spline, cannot accidentally
    lie on top of its neighbour.
    """

    N = 120
    CELL = 2.0

    def __init__(self, spec):
        th, length, curl, self.r0, self.roll0, self.twist, self.depth = spec
        th, curl = math.radians(th), math.radians(curl)
        pts = []
        for i in range(self.N):
            f = i / (self.N - 1.0)
            a = th + curl * f ** 1.5
            rad = R_START + length * f
            pts.append((CROWN[0] + rad * math.cos(a),
                        CROWN[1] + rad * math.sin(a)))
        self.base = pts[0]
        u, self.s = 0.0, []
        for i, q in enumerate(pts):
            if i:
                u += math.dist(q, pts[i - 1])
            a = pts[max(0, i - 1)]
            b = pts[min(self.N - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            m = math.hypot(tx, ty) or 1.0
            self.s.append((q[0], q[1], u, tx / m, ty / m))
        self.length = u
        self.grid = {}
        for i, (x, y, _u, _tx, _ty) in enumerate(self.s):
            for cx in range(int((x - 3.5) / self.CELL), int((x + 3.5) / self.CELL) + 1):
                for cy in range(int((y - 3.5) / self.CELL), int((y + 3.5) / self.CELL) + 1):
                    self.grid.setdefault((cx, cy), []).append(i)

    def radius(self, t):
        return max(0.62, self.r0 * (1.0 - 0.80 * t) ** 0.80)

    def hit(self, p):
        """(t, u, s, r, tangent) if this arm covers p, else None."""
        cand = self.grid.get((int(p[0] / self.CELL), int(p[1] / self.CELL)))
        if not cand:
            return None
        best, bi = 1e9, -1
        for i in cand:
            x, y, _u, _tx, _ty = self.s[i]
            d = (p[0] - x) ** 2 + (p[1] - y) ** 2
            if d < best:
                best, bi = d, i
        x, y, u, tx, ty = self.s[bi]
        t = u / self.length
        r = self.radius(t)
        d = math.sqrt(best)
        if d > r:
            return None
        off = (p[0] - x) * -ty + (p[1] - y) * tx
        return t, u, clamp(off / r, -1.0, 1.0), r, (tx, ty)

    def face(self, t):
        """+1 = the suckered underside is toward you, -1 = the dark back is."""
        return math.sin(self.roll0 + self.twist * t)


ARM = [Arm(a) for a in ARMS]
ARM_ORDER = sorted(range(len(ARM)), key=lambda k: ARM[k].depth)
BAG_ORDER = 0                                   # depth key of the head
TOP = max(a.depth for a in ARM)                 # nothing can occlude this one
BASE_GEO = {k: math.dist(ARM[k].base, APEX) for k in range(len(ARM))}


# ----------------------------------------------------------------- shading ---
def surface(n, t_depth):
    """One lamp, one bounce, and a little falling-off with distance."""
    diff = clamp(dot3(n, LIGHT))
    fill = clamp(dot3(n, FILL))
    return (0.40 + 0.64 * diff + 0.20 * fill) * (1.0 - 0.13 * t_depth)


def mottle(p):
    """Skin, not texture. Low amplitude on purpose — at 32px a busy surface is
    noise (the geode that never shipped, 2026-08-11), so the blotches are few
    and everything else is one gentle drift.

    And they are WEIGHTED DOWNWARD, which is the fix for the thing that made
    four renders in a row look like a dark loaf. The blotch field is six pixels
    across; one of its dark cells happened to sit on the crown of the mantle,
    the exact place the lamp makes brightest, and lerping the skin all the way
    to the deep tone there simply deleted the highlight — the head lost its top
    and the whole subject went flat. Texture is not allowed to overwrite form:
    the mottling now fades out toward the lit top and lives in the shaded lower
    half, where mottling on a real animal is mostly what you see anyway.
    """
    f = vnoise(p[0], p[1], 3.6, 21)
    b = vnoise(p[0] * 0.8, p[1] * 0.8, 5.2, 33)
    lower = 0.30 + 0.70 * clamp(p[1] / 15.0)
    return 0.92 + 0.16 * f, clamp((b - 0.56) / 0.28) * 0.55 * lower


def sucker_at(arm, t, u, s, r):
    """(0..1 strength, is_rim) for the sucker rows on an arm's underside.

    Two staggered rows, spaced by the arm's OWN width, so they crowd toward the
    tip exactly as real ones do and nothing is placed by hand. At this size a
    sucker is a single pale pixel with a darker one beside it — which is all a
    sucker row ever is on a wall this small, and it is enough.
    """
    f = arm.face(t)
    if f <= 0.25:
        return 0.0, 0.0
    step = 0.62 * r + 0.55
    i = round(u / step)
    uc = i * step
    sc = 0.40 if (i % 2) else -0.40
    d = math.hypot(u - uc, (s - sc) * r)
    rad = 0.26 * r + 0.20
    core = clamp((rad - d) / 0.45) * clamp((f - 0.25) / 0.30)
    ring = clamp((d - rad) / 0.50) * clamp((rad + 0.6 - d) / 0.4) * core * 1.4
    return core, clamp(ring)


def arm_colour(k, hit, p, flushed):
    t, u, s, r, (tx, ty) = hit
    arm = ARM[k]
    phi = s * TILT
    n = _n3((-ty * math.sin(phi), tx * math.sin(phi), math.cos(phi)))
    v = surface(n, t)
    f = arm.face(t)
    # Gated hard, not eased from zero. With `under` opening as soon as the arm
    # rolled at all, six of the eight came out mostly pale and the whole lower
    # half of the panel was one tan field — the pale side has to be a MINORITY
    # report, or there is nothing for the hero arm's cream underside to be pale
    # against.
    under = clamp((f - 0.25) / 0.55)
    if not flushed:
        return scale(lerp(PALE, PALE_UNDER, under), v)
    m, blot = mottle(p)
    base = lerp(SKIN, SKIN_UNDER, under)
    base = lerp(base, SKIN_DEEP, blot * (1.0 - 0.6 * under))
    c = scale(base, v * m)
    core, ring = sucker_at(arm, t, u, s, r)
    if ring > 0.0:
        c = lerp(c, scale(SUCKER_RIM, v), 0.55 * ring)
    if core > 0.0:
        c = lerp(c, scale(SUCKER, 0.72 + 0.42 * v), core)
    return c


def bag_colour(p, inside, flushed, eyes):
    n = bag_normal(p, inside)
    # One broad top-to-bottom sweep over the whole bag, on top of the per-pixel
    # normal. The normal alone gives local curvature but no overall FORM: at
    # 32px what makes a dome look like a dome is that its top is plainly lighter
    # than its bottom, and that is a gradient across the whole shape, not
    # something any surface normal in the middle of it knows about.
    v = surface(n, 0.0) * (1.26 - 0.44 * clamp(p[1] / 19.0))
    # the eyes sit in a socket: a crease over the top of each dome, which is
    # what stops them reading as two balls stuck on the side of a bag
    for ex, ey in (EYE_L, EYE_R):
        d = math.hypot((p[0] - ex) / 3.25, (p[1] - ey + 2.15) / 1.30)
        if d < 1.0:
            v *= 1.0 - 0.34 * (1.0 - d) ** 0.6
    if not flushed:
        c = scale(PALE, v)
    else:
        m, blot = mottle(p)
        c = scale(lerp(SKIN, SKIN_DEEP, blot), v * m)
    if not eyes:
        return c
    return eye_colour(p, c, v)


def eye_colour(p, c, v):
    """The iris, the horizontal slit, and the one spark of specular.

    An octopus pupil is a horizontal BAR, and that is the whole reason the face
    reads as an octopus and not a doll: it is the only rectangle on the animal.
    """
    for ex, ey in (EYE_L, EYE_R):
        d = math.hypot(p[0] - ex, (p[1] - ey) * 1.06)
        if d > IRIS_R + 0.55:
            continue
        if d > IRIS_R:
            return lerp(c, scale(IRIS_COOL, 0.55), clamp((IRIS_R + 0.55 - d) / 0.55))
        iris = lerp(IRIS_HOT, IRIS_COOL, clamp(d / IRIS_R) ** 0.75)
        col = scale(iris, 0.70 + 0.42 * v)
        px = abs(p[0] - ex) / PUPIL_W
        py = abs(p[1] - ey + 0.10) / PUPIL_H
        q = max(px, py) if max(px, py) > 0 else 0.0
        blend = math.hypot(px, py) * 0.35 + q * 0.65
        if blend < 1.12:
            col = lerp(col, PUPIL, clamp((1.12 - blend) / 0.34))
        g = math.hypot(p[0] - (ex - 0.72), p[1] - (ey - 0.86))
        if g < 0.78:
            col = lerp(col, GLINT, clamp((0.78 - g) / 0.62) ** 0.7)
        return col
    return c


# ------------------------------------------------------------------ water ---
def water(p, lit):
    x, y = p
    g = clamp(y / (SIZE - 1.0))
    c = lerp(WATER_TOP, WATER_LOW, g ** 0.72)
    c = lerp(c, scale(c, 1.14), vnoise(x * 0.7, y * 0.7, 7.0, 5))
    if not lit:
        return c
    c = scale(c, 1.0 + 0.30 * math.exp(-y / 9.0))            # light from above
    d = math.hypot(x - 15.5, y - 13.0) / 26.0
    c = scale(c, 1.06 - 0.42 * clamp(d * 1.25) ** 1.4)       # the dark corners
    h = hash2(int(x), int(y), 17)
    if h > 0.978:
        c = lerp(c, MOTE, 0.30 + 0.28 * hash2(int(y), int(x), 23))
    return c


# ----------------------------------------------------------------- records ---
def covered(p):
    if bag_sdf(p) <= 0.0:
        return True
    return any(a.hit(p) is not None for a in ARM)


def contact_shadow(p, win_depth, top_depth):
    """How much of the lamp a NEARER part of the animal is taking from p.

    Eight limbs crossing each other in fourteen rows is the whole difficulty of
    this piece, and no amount of per-tube shading solves it: two arms lit by the
    same lamp, made of the same skin, land at the same value where they touch,
    and the pair reads as one wide arm. What separates them is not light, it is
    DARK — the shadow the front one throws on the back one. So the occluder is
    looked up directly: step from p toward the lamp and ask whether something
    with a higher depth key is standing there.
    """
    if win_depth >= top_depth:
        return 0.0, 0
    occ, who = 0.0, 0
    for k, w in ((1.20, 0.32), (2.20, 0.16)):
        q = (p[0] + LIGHT[0] * k, p[1] + LIGHT[1] * k)
        d = BAG_ORDER if bag_sdf(q) <= 0.0 else -99
        for kk in ARM_ORDER:
            if ARM[kk].depth > win_depth and ARM[kk].hit(q) is not None:
                d = max(d, ARM[kk].depth)
        if d > win_depth and w > occ:
            occ, who = w, d
    return occ, who


def rim_strength(p):
    """How close p is to the animal's OUTER silhouette.

    It has to be the outer edge, not each part's own edge, or every arm gets a
    bright line where it crosses the head and the whole thing looks welded. So
    it is measured by asking whether the animal is still there a pixel away in
    each direction — the union, not the parts.

    The count is then band-passed, and that is the whole lesson of the first
    attempt. A rim is meant to say "this is where the subject ENDS", which only
    means anything when there is subject on one side and water on the other. On
    an arm two pixels wide every single pixel has water all the way round it, so
    a plain "is there an edge here" test fires at full strength across the entire
    limb — and eight tentacles came out uniformly bleached to the rim's own pale
    peach, with no tube shading left to see. Where the neighbourhood is MOSTLY
    outside there is no interior to separate from, so the rim has to fade back
    out again: it peaks on a real contour and dies on a sliver.
    """
    out = 0
    for i in range(8):
        a = i * math.pi / 4.0
        if not covered((p[0] + 1.05 * math.cos(a), p[1] + 1.05 * math.sin(a))):
            out += 1
    if out == 0:
        return 0.0, 0.0
    s = clamp(out / 3.0) * clamp((8.0 - out) / 3.5)
    lamp = clamp(0.5 - 0.055 * (p[0] - 15.8) - 0.075 * (p[1] - 14.0))
    return s, lamp


def build():
    off = [(k + 0.5) / SS - 0.5 for k in range(SS)]
    subs = {}
    for y in range(SIZE):
        for x in range(SIZE):
            rec = []
            for dy in off:
                for dx in off:
                    p = (x + dx, y + dy)
                    stack = []                  # (depth, pale, flushed, geo)
                    for k in ARM_ORDER:
                        h = ARM[k].hit(p)
                        if h is None:
                            continue
                        stack.append((ARM[k].depth, k,
                                      arm_colour(k, h, p, False),
                                      arm_colour(k, h, p, True),
                                      BASE_GEO[k] + h[1]))
                    f = bag_sdf(p)
                    if f <= 0.0:
                        stack.append((BAG_ORDER, -1,
                                      bag_colour(p, -f, False, False),
                                      bag_colour(p, -f, True, False),
                                      math.dist(p, APEX)))
                    stack.sort(key=lambda e: e[0])
                    eye = None
                    if f <= 0.0 and not any(e[0] > BAG_ORDER for e in stack):
                        n = bag_normal(p, -f)
                        base = bag_colour(p, -f, True, False)
                        lit = eye_colour(p, base, surface(n, 0.0))
                        if lit != base:
                            eye = lit
                    rec.append({
                        "stack": stack,
                        "eye": eye,
                        "occ": (0.0, 0),
                        "flat": water(p, False),
                        "lit": water(p, True),
                        "rim": None,
                    })
            subs[(x, y)] = rec

    # the contour pass, only where it can possibly matter
    for y in range(SIZE):
        for x in range(SIZE):
            for i, dy in enumerate(off):
                for j, dx in enumerate(off):
                    sp = subs[(x, y)][i * SS + j]
                    if not sp["stack"]:
                        continue
                    sp["rim"] = rim_strength((x + dx, y + dy))
                    sp["occ"] = contact_shadow((x + dx, y + dy),
                                               max(e[0] for e in sp["stack"]), TOP)
    return subs


# ---------------------------------------------------------------- compose ---
def compose(sp, done, flushed, eyes, lit):
    """done = set of depth keys already painted; flushed = keys already flushed."""
    top, win = None, None
    for depth, k, pale, hot, _geo in sp["stack"]:
        if depth in done:
            top = hot if depth in flushed else pale
            win = depth
    if top is None:
        return sp["lit"] if lit else sp["flat"]
    # the shadow only exists once the thing casting it has been painted
    occ, who = sp["occ"]
    if occ and who in done:          # the shadow only exists once its caster does
        top = lerp(scale(top, 1.0 - occ), (14, 26, 34), occ * 0.30)
    if eyes and sp["eye"] is not None and BAG_ORDER in flushed \
            and not any(d > BAG_ORDER and d in done for d, *_ in sp["stack"]):
        top = sp["eye"]
    if lit and sp["rim"]:
        s, lamp = sp["rim"]
        if s > 0.0:
            tint = lerp(RIM_COLD, RIM_WARM, clamp(lamp))
            top = lerp(top, tint, (0.10 + 0.30 * clamp(lamp)) * s)
    return top


def avg(recs, fn):
    a = [0.0, 0.0, 0.0]
    for sp in recs:
        c = fn(sp)
        for i in range(3):
            a[i] += c[i]
    return tuple(v / len(recs) for v in a)


# ---------------------------------------------------------------- perform ---
def build_strokes(subs):
    steps, cur = [], {}
    pts = list(subs.keys())

    def emit(p, c):
        steps.append((p[0], p[1], c))
        cur[p] = c

    def paint(order, fn, thresh=4.0):
        for p in order:
            c = fn(p)
            if p not in cur or max(abs(c[i] - cur[p][i]) for i in range(3)) > thresh:
                emit(p, c)

    def owner(p, depth):
        return any(any(d == depth for d, *_ in sp["stack"]) for sp in subs[p])

    def geo_of(p, depth):
        gs = [g for sp in subs[p] for d, _k, _a, _b, g in sp["stack"] if d == depth]
        return sum(gs) / len(gs) if gs else 1e9

    done, flushed = set(), set()
    depths = [ARM[k].depth for k in ARM_ORDER]

    # 1. the water, washed in serpentine over the whole panel
    for p in sorted(pts, key=lambda q: (q[1], q[0] if q[1] % 2 == 0 else -q[0])):
        emit(p, avg(subs[p], lambda sp: sp["flat"]))

    # 2. the animal ARRIVES, blanched: back arms reach out root to tip, the
    #    mantle comes down out of the dark, then the front arms reach out over
    #    the top of it. Nothing has any colour yet.
    def stage(depth, key):
        done.add(depth)
        own = [p for p in pts if owner(p, depth)]
        own.sort(key=key)
        paint(own, lambda p: avg(subs[p],
                                 lambda sp: compose(sp, done, flushed, False, False)))

    for d in [x for x in depths if x < BAG_ORDER]:
        stage(d, lambda p, d=d: geo_of(p, d))
    stage(BAG_ORDER, lambda p: p[1] * 2.0 + abs(p[0] - APEX[0]))
    for d in [x for x in depths if x > BAG_ORDER]:
        stage(d, lambda p, d=d: geo_of(p, d))

    # 3. THE FLUSH. One wave, ordered by distance along the ANIMAL — down the
    #    mantle and out along every arm at once — and the suckers appear in its
    #    wake because they are the only thing that does not go dark.
    allg = []
    for p in pts:
        gs = [g for sp in subs[p] for _d, _k, _a, _b, g in sp["stack"]]
        if gs:
            allg.append((p, min(gs)))
    flushed.update(done)
    for p, _g in sorted(allg, key=lambda pg: pg[1]):
        c = avg(subs[p], lambda sp: compose(sp, done, flushed, False, False))
        emit(p, c)

    # 4. the light in the water comes up: the shafts from above, the dark
    #    corners, the motes, and the rim that keeps the animal off the ground
    lit_all = {p: avg(subs[p], lambda sp: compose(sp, done, flushed, False, True))
               for p in pts}
    late = [p for p in pts
            if max(abs(lit_all[p][i] - cur[p][i]) for i in range(3)) > 4.0]
    late.sort(key=lambda p: math.hypot(p[0] - 15.8, p[1] - 14.0), reverse=True)
    for p in late:
        emit(p, lit_all[p])

    # 5. the eyes open. Last stroke of all is the spark in the right one.
    final = {p: avg(subs[p], lambda sp: compose(sp, done, flushed, True, True))
             for p in pts}
    eyes = [p for p in pts
            if max(abs(final[p][i] - cur[p][i]) for i in range(3)) > 3.0]

    def eye_key(p):
        dl = math.hypot(p[0] - EYE_L[0], p[1] - EYE_L[1])
        dr = math.hypot(p[0] - EYE_R[0], p[1] - EYE_R[1])
        # left eye first, outside in; then the right; the glints last of all
        near = min(dl, dr)
        return (0 if dl <= dr else 1, -near)

    for p in sorted(eyes, key=eye_key):
        emit(p, final[p])

    assert len(cur) == SIZE * SIZE, "some pixel never got a stroke"
    return steps, cur


def preview(final, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for (x, y), c in final.items():
        px[x, y] = tuple(max(0, min(255, round(v))) for v in c)
    img.save(path)
    img.resize((SIZE * 14, SIZE * 14), Image.NEAREST).save(
        path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    subs = build()
    steps, final = build_strokes(subs)

    # ---- measure it, do not eyeball it (the hourglass, 2026-07-30) ----------
    animal = [p for p in subs if any(sp["stack"] for sp in subs[p])]
    aset = set(animal)
    sea = [p for p in subs if p not in aset]
    av = [val(final[p]) for p in animal]
    wv = [val(final[p]) for p in sea]

    # every arm has to actually SURVIVE to the surface — an arm buried by the
    # ones in front of it is an arm that is not in the picture
    vis = {}
    for p in animal:
        for sp in subs[p]:
            if sp["stack"]:
                d, k, *_ = max(sp["stack"], key=lambda e: e[0])
                if k >= 0:
                    vis[k] = vis.get(k, 0) + 1

    # the composition has to REACH: eight arms that all stop short leave a blob
    edges = {"L": 0, "R": 0, "T": 0, "B": 0}
    for x, y in animal:
        if x <= 2:
            edges["L"] += 1
        if x >= 29:
            edges["R"] += 1
        if y <= 2:
            edges["T"] += 1
        if y >= 29:
            edges["B"] += 1

    # the flush has to be a real change, and it has to be a change of HUE, not
    # just of brightness — a blanched animal and a flushed one that differ only
    # in value is a light switch, not a chromatophore
    pale = {p: avg(subs[p], lambda sp: compose(
        sp, set(d for d, *_ in sp["stack"]), set(), False, False)) for p in animal}
    warmth = lambda c: c[0] - (c[1] + c[2]) / 2.0
    dp = sum(warmth(pale[p]) for p in animal) / len(animal)
    df = sum(warmth(final[p]) for p in animal) / len(animal)

    # the suckers: pale dots that have to stay pale against flushed skin
    suck = [p for p in animal if val(final[p]) > 196
            and final[p][0] > final[p][2] + 20]

    # THE DOME TEST. A lit bag has a light top and a dark bottom, and that one
    # gradient is most of what says "inflated" at this size. It is also the
    # check that four bad renders needed and did not have: a blotch of the
    # mottling field sat on the crown of the mantle and lerped the highlight
    # away, the head went flat, and every measurement above was perfectly
    # content because the animal was still bright ON AVERAGE. Averages cannot
    # see form. Measure the gradient itself.
    luma = lambda c: 0.30 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    crest = [luma(final[p]) for p in animal if p[1] <= 5]
    belly = [luma(final[p]) for p in animal if 8 <= p[1] <= 11
             and abs(p[0] - EYE_L[0]) > 3.4 and abs(p[0] - EYE_R[0]) > 3.4]
    dome = sum(crest) / len(crest) - sum(belly) / len(belly)

    quad = {}
    for p in animal:
        q = ("N" if p[1] < 15 else "S") + ("W" if p[0] < 16 else "E")
        quad.setdefault(q, []).append(val(final[p]))
    quads = {q: round(sum(v) / len(v)) for q, v in quad.items()}
    worst = min(quads.values())

    print(f"animal={len(animal)}px ({round(100 * len(animal) / 1024)}% of panel)"
          f"   water mean={round(sum(wv) / len(wv))}  animal mean="
          f"{round(sum(av) / len(av))}")
    print(f"arms visible={sorted(vis.items())}")
    print(f"edge reach={edges}   quadrants={quads} worst={worst}")
    print(f"flush warmth {round(dp, 1)} -> {round(df, 1)}   sucker px={len(suck)}")
    print(f"dome gradient crest-belly={round(dome, 1)}")
    print(f"{len(steps)} strokes")

    assert len(animal) > 520, f"the octopus is too small at {len(animal)}px"
    assert len(vis) == len(ARM), f"only {len(vis)} of {len(ARM)} arms survive"
    assert min(vis.values()) >= 9, f"an arm is nearly buried: {sorted(vis.items())}"
    assert all(v >= 6 for v in edges.values()), f"it does not fill the panel: {edges}"
    assert sum(av) / len(av) > sum(wv) / len(wv) + 40, "the animal is sinking"
    assert worst > sum(wv) / len(wv) + 22, \
        f"the {min(quads, key=quads.get)} quadrant ({worst}) has sunk into the water"
    assert df - dp > 55, f"the flush is not a flush: warmth {dp} -> {df}"
    assert 26 <= len(suck) <= 260, f"sucker count {len(suck)} is wrong"
    assert dome > 34, f"the mantle is flat: crest-belly is only {round(dome, 1)}"

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview(final, "art/kraken.png")
        raise SystemExit

    preview(final, "art/kraken.png")
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.013
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay,
               "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued at {delay}s")
