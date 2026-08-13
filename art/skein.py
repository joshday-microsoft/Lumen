"""One big ball of yarn, WOUND onto the wall strand by strand — a painting.

The first textile in the ledger, and the first subject that is soft. Everything
before it has been shell, metal, glass, stone, wood, bone or flesh; wool is the
one material whose whole character is that it has no hard edge anywhere.

The reason it belongs on the /paint endpoint rather than in a GIF is that a ball
of yarn is not an object, it is a RECORD OF A PROCESS. You cannot draw one that
looks right without deciding what order the strands went on, because every strand
lies over the ones wound before it and under the ones wound after. So the
performance and the drawing are the same thing: the panel winds the ball, one
wrap at a time, in the order it would actually have been wound, and each wrap
covers a little more of the last.

The geometry is one idea. A wrap is a great circle on the sphere: the band of
surface where a point's unit vector is within a whisker of perpendicular to that
wrap's axis. Across the band, the strand's own surface normal tilts away from the
sphere's normal toward the axis, which is what makes a wrap read as a round tube
lying ON the ball rather than a stripe painted on it — one lamp then lights all
forty-four wraps consistently, and the gaps between them go dark by themselves.
The axes are a Fibonacci spiral on the sphere, so consecutive wraps cross at big
angles the way they do when you keep turning the ball in your hand, and the whole
surface is covered about four times over — which leaves a couple of dozen pixels
where you can see straight down into the dark mass underneath, and those gaps are
most of what says wool.

The yarn is SELF-STRIPING, and that is a legibility decision as much as a pretty
one: the dye repeats three times over the winding, so the colour of a wrap is a
function of how far along the strand it is. A single sweep of the ramp would put
the whole outer layer in one hue (the last wraps cover everything), and the piece
would lose the one thing that shows the winding order. Repeating it means the
outermost layer alone carries indigo, violet, rose and coral, and the wraps
underneath show through the gaps in the wrong order — which is exactly what a
wound ball looks like.

The loose end is not decoration either. It leaves the ball at the point where the
last wrap ends, because that is the only place it can leave from, and it carries
the next colour in the dye run — so the tail tells you where the ball stopped.

Run (perform):  .venv\\Scripts\\python.exe art\\skein.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\skein.py preview
"""

import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                                  # supersampling per axis

# ------------------------------------------------------------------ scene ---
CX, CY = 14.0, 17.6                     # the ball, set left of centre so the
R = 11.6                                # loose end has table to lie on
HORIZON = 19.0                          # table edge, mostly behind the ball

_L = (-0.36, -0.42, 0.83)               # one lamp, upper left and well in front
_n = math.sqrt(sum(v * v for v in _L))
LIGHT = tuple(v / _n for v in _L)
_F = (0.46, 0.52, 0.72)                 # the table's bounce, filling the shade
_fn = math.sqrt(sum(v * v for v in _F))
FILL = tuple(v / _fn for v in _F)
_H = tuple(LIGHT[i] + (0.0, 0.0, 1.0)[i] for i in range(3))
_hn = math.sqrt(sum(v * v for v in _H))
HALF = tuple(v / _hn for v in _H)       # for the wool's soft sheen

GROUPS = 4                              # turns of the wrist
PER_GROUP = 4                           # wraps laid before the ball is turned
N_WRAPS = GROUPS * PER_GROUP
SPREAD = 0.40                           # how far a lane steps from its neighbour
BAND = 0.175                            # sin of a wrap's half width => 4.1px
TILT = 0.62                             # how far the tube's normal rolls over
REPEATS = 1.35                          # how much of the dye run the ball ate
                                        # — enough that the LAST family of wraps
                                        # spans a quarter of the run on its own,
                                        # because once the wraps cover the ball
                                        # properly the top family is most of what
                                        # you see, and a single sweep put all of
                                        # it in one hue
PHASE = 0.36                            # where in the dye run the winding began
                                        # — chosen so the LAST wraps are the warm
                                        # end and the cool end is buried, which
                                        # both puts the ball's coolest colour
                                        # deepest (cool recedes) and matches the
                                        # loose end, since the tail is simply the
                                        # dye run carrying on past the last wrap
GOLDEN = math.pi * (3.0 - math.sqrt(5.0))

# The needle goes in at the upper left, the tail comes out at the lower right:
# the two man-made things in the picture sit on opposite ends of one diagonal so
# neither crowds the ball.
NEEDLE_TIP = (3.2, 2.4)
NEEDLE_END = (13.0, 16.5)
NEEDLE_W = 1.05

TAIL_U = (0.66, 0.62)                   # where the last wrap runs off the ball
TAIL_PTS = ((25.2, 28.6), (29.2, 29.8), (31.6, 26.4))   # bezier controls + end

# ---------------------------------------------------------------- palette ---
# Cool room, warm wood, and a yarn that runs the long way round the wheel from
# indigo to coral. The wall is deliberately the coldest thing in the frame so
# the wool reads warm even where the wool is blue.
WALL_TOP = (17, 21, 31)
WALL_LOW = (33, 39, 53)
TABLE_FAR = (52, 40, 35)
TABLE_NEAR = (25, 19, 19)
SHADOW = (13, 11, 13)
MASS = (126, 74, 128)                   # the layers under the top wraps
WOOD_LIT = (224, 198, 152)
WOOD_DARK = (138, 108, 70)
WOOD_TIP = (246, 234, 212)
SHEEN = (255, 244, 232)

# The dye run is pitched HIGH on purpose. The first version ran from a true
# indigo (56, 44, 104) and the ball's whole shaded half then landed at the same
# value as the table it was sitting on — a colour whose brightest channel is 104
# has nowhere to go once the light leaves it. Every stop here clears 175 at its
# brightest channel, so wool in shadow still outranks the room.
STOPS = ((0.00, (96, 82, 186)), (0.20, (152, 76, 180)), (0.42, (218, 70, 120)),
         (0.62, (246, 132, 96)), (0.80, (208, 88, 132)), (1.00, (96, 82, 186)))


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale(c, f):
    return tuple(clamp(v * f, 0.0, 255.0) for v in c)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def norm3(v):
    m = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / m, v[1] / m, v[2] / m)


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


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


def dye(p):
    p = p % 1.0
    for i in range(len(STOPS) - 1):
        a, b = STOPS[i], STOPS[i + 1]
        if a[0] <= p <= b[0]:
            return lerp(a[1], b[1], (p - a[0]) / (b[0] - a[0]))
    return STOPS[-1][1]


# ------------------------------------------------------------------ wraps ---
def spin(a, b, th):
    """Rotate axis a about the perpendicular unit vector b (Rodrigues)."""
    c, s = math.cos(th), math.sin(th)
    ba = cross3(b, a)
    return norm3(tuple(a[i] * c + ba[i] * s for i in range(3)))


def wrap_axes():
    """One axis per wrap — in LANES, because that is how a ball gets wound.

    The first attempt spread all forty-four axes over the sphere by the golden
    angle: perfectly even, perfectly round, and completely illegible, because
    forty-four arcs crossing at forty-four different angles is confetti. Nobody
    winds like that. You lay several wraps side by side, turn the ball in your
    hand, lay several more across them, and turn again — so the surface is a few
    FAMILIES of near-parallel strands crossing each other at big angles, and it
    is the families that the eye reads at 32px, not the strands.

    So the axes come in groups: one base direction per group, spread by the
    golden angle, and within a group the axis steps sideways by SPREAD, which
    walks the wrap across the ball a lane at a time.
    """
    axes = []
    for g in range(GROUPS):
        z = 1.0 - 2.0 * (g + 0.5) / GROUPS
        rr = math.sqrt(max(0.0, 1.0 - z * z))
        a = g * GOLDEN
        base = norm3((rr * math.cos(a), rr * math.sin(a), z))
        perp = norm3(cross3(base, (0.0, 0.0, 1.0) if abs(base[2]) < 0.9
                            else (1.0, 0.0, 0.0)))
        last = g == GROUPS - 1
        if last:
            # The loose end is not free: it can only leave the ball at the end
            # of whichever wrap was on top when the winding stopped. So the
            # final group is built around the axis that puts a wrap through the
            # exit point, and that wrap is laid last.
            ux, uy = TAIL_U
            uz = math.sqrt(max(0.02, 1.0 - ux * ux - uy * uy))
            base = norm3(cross3(norm3((ux, uy, uz)),
                                norm3((-0.55, -0.72, 0.42))))
            perp = norm3(cross3(base, (0.0, 0.0, 1.0)))
        for j in range(PER_GROUP):
            step = (PER_GROUP - 1 - j) if last else (j - (PER_GROUP - 1) / 2.0)
            axes.append(spin(base, perp, step * SPREAD))
    return axes


AXES = wrap_axes()
BASES = []
for _a in AXES:                          # an in-plane basis, to walk the arc
    _e1 = norm3(cross3(_a, (0.0, 0.0, 1.0) if abs(_a[2]) < 0.9 else (1.0, 0.0, 0.0)))
    BASES.append((_e1, cross3(_a, _e1)))


def wool_v(nn, u):
    """How bright wool is at a point: key lamp, table bounce, and the ball.

    The bounce is not decoration. One lamp on a sphere puts half the subject
    below the value of the room it is standing in, and no amount of rim light
    rescues the middle of that half — a fill from the lower right, at a third of
    the key, is what keeps the shaded side reading as lit wool instead of as a
    hole in the picture.

    The second factor is the SPHERE's own broad gradient. A strand's tube
    shading swings violently from pixel to pixel, so on its own it renders a bag
    of loose noodles; multiplying it by one big light-to-dark sweep across the
    whole ball is what turns the noodles into a ball.
    """
    diff = clamp(dot3(nn, LIGHT))
    fill = clamp(dot3(nn, FILL))
    form = clamp(0.5 + 0.5 * dot3(u, LIGHT))
    v = (0.50 + 0.54 * diff + 0.24 * fill) * (0.86 + 0.20 * form ** 1.2)
    v *= 0.86 + 0.14 * clamp(u[2]) ** 0.6
    if u[1] > 0.55:                             # where it sits on the table
        v *= 1.0 - 0.18 * ((u[1] - 0.55) / 0.45) ** 1.6
    return v, form


def strand_colour(u, k):
    """The colour of wrap k where it crosses the surface point u."""
    n = AXES[k]
    t = dot3(u, n) / BAND                       # -1..1 across the strand
    e1, e2 = BASES[k]
    ang = math.atan2(dot3(u, e2), dot3(u, e1))  # how far along the wrap

    # the tube: its normal rolls off the sphere's normal toward the wrap axis,
    # which is the whole reason a wrap reads as round rather than as a stripe
    a = t * TILT
    nn = norm3(tuple(u[i] * math.cos(a) + n[i] * math.sin(a) for i in range(3)))

    v, form = wool_v(nn, u)
    c = scale(dye((k + ang / (2.0 * math.pi)) / N_WRAPS * REPEATS + PHASE), v)
    # The gap between two wraps has to be a LINE, not a fade. Shading a strand
    # smoothly across its width and hoping the flanks read as a boundary is what
    # turned the first three attempts into mush: at three pixels wide there is
    # no room for a gradient to say anything. One dark score at each flank, and
    # the ball becomes rope instead of noise (the ammonite's sutures, again).
    # ...but the groove has to get SHALLOWER as the light leaves, or the
    # shaded half of the ball scores itself into a scatter of near-black dots
    # sitting at the same value as the room, which is the murk that made the
    # right-hand side of the fifth attempt look like torn paper.
    e = abs(t)
    if e > 0.70:
        c = lerp(c, scale(c, 0.44 + 0.22 * (1.0 - form)),
                 clamp((e - 0.70) / 0.30) ** 0.7)
    s = clamp(dot3(nn, HALF))
    return rim_light(u, lerp(c, SHEEN, 0.30 * s ** 14)), ang


def rim_light(u, c):
    """The contour, drawn deliberately.

    Physically this is bounce — off the table, off the wall, off the room. It is
    in the piece because five attempts died on the same thing: a sphere lit by
    one lamp has a terminator, the terminator lands INSIDE the disc, and every
    pixel outside it fades toward the value of the room. At 32px a 23px circle
    has seventy-odd edge pixels, and when they go dark the ball stops being
    round and becomes a lozenge of light with a smear under it. So the whole
    contour is lifted, warm where the lamp reaches it and cold where only the
    room does — the ball is never allowed to meet the background at its own
    value anywhere around the circle (the knight, 2026-08-08).
    """
    edge = clamp((0.42 - u[2]) / 0.42) ** 0.85
    if edge <= 0.0:
        return c
    lamp = clamp(0.5 + 0.8 * (u[0] * LIGHT[0] + u[1] * LIGHT[1]))
    tint = lerp((104, 116, 156), (255, 212, 180), lamp)
    return lerp(c, tint, (0.30 + 0.20 * (1.0 - lamp)) * edge)


def mass_colour(u):
    """What shows in the gaps between the top wraps.

    The first four attempts made this nearly black, on the theory that a gap is
    a hole and holes are dark. It is the single thing that wrecked them: at this
    size the gaps quantise into a scatter of black dots that breaks every strand
    into dashes AND eats the contour, so the ball stopped being a circle. A gap
    in a wound ball is not a hole, it is the LAYER UNDERNEATH — wool a couple of
    wraps down, in shadow but still wool. Lit like the rest of the sphere and
    kept at two thirds the brightness, it reads as depth and the surface stays
    continuous.
    """
    v, _form = wool_v(u, u)
    return rim_light(u, scale(MASS, max(0.58, v) * 0.78))


# ----------------------------------------------------------------- needle ---
def needle(p):
    ax, ay = NEEDLE_TIP
    bx, by = NEEDLE_END
    vx, vy = bx - ax, by - ay
    ln = math.hypot(vx, vy)
    vx, vy = vx / ln, vy / ln
    t = (p[0] - ax) * vx + (p[1] - ay) * vy
    if t < -0.2 or t > ln:
        return None
    off = (p[0] - ax) * -vy + (p[1] - ay) * vx      # signed, across the shaft
    w = NEEDLE_W * clamp(t / 3.2, 0.12, 1.0)        # tapers to a point
    if abs(off) > w:
        return None
    if t < 3.0:
        return lerp(WOOD_TIP, WOOD_LIT, clamp(t / 3.0))
    return lerp(WOOD_LIT, WOOD_DARK, clamp((off / w) * 0.5 + 0.5) ** 0.8)


# ------------------------------------------------------------------- tail ---
def tail_curve():
    ux, uy = TAIL_U
    p0 = (CX + ux * R * 0.88, CY + uy * R * 0.88)   # over the ball's shoulder
    c1, c2, p3 = TAIL_PTS
    pts = []
    for i in range(121):
        t = i / 120.0
        m = 1.0 - t
        x = (m ** 3 * p0[0] + 3 * m * m * t * c1[0]
             + 3 * m * t * t * c2[0] + t ** 3 * p3[0])
        y = (m ** 3 * p0[1] + 3 * m * m * t * c1[1]
             + 3 * m * t * t * c2[1] + t ** 3 * p3[1])
        pts.append((x, y, t))
    return pts


TAIL = tail_curve()


def tail_at(p):
    """(colour, t) if the loose end covers this point, else None."""
    best = None
    for x, y, t in TAIL:
        d = math.hypot(p[0] - x, p[1] - y)
        if best is None or d < best[0]:
            best = (d, t, y)
    d, t, cy = best
    if d > 1.10:
        return None
    # the dye run simply continues past the last wrap, which is what makes the
    # loose end tell you where the ball stopped
    c = dye((N_WRAPS + t * 0.9) / N_WRAPS * REPEATS + PHASE)
    v = 0.78 + 0.50 * clamp(1.0 - (p[1] - cy + 0.6) / 1.7)   # lit along the top
    return scale(c, v), t


def tail_shadow(p):
    for x, y, _t in TAIL:
        if abs(p[0] - x) < 1.5 and 0.2 < p[1] - y < 1.7:
            if math.hypot(p[0] - x, (p[1] - y - 0.9) * 1.6) < 1.0:
                return 0.55
    return 0.0


# ------------------------------------------------------------------- room ---
def room(p, lit):
    x, y = p
    if y < HORIZON:
        c = lerp(WALL_TOP, WALL_LOW, clamp(y / HORIZON) ** 0.8)
        c = lerp(c, scale(c, 1.10), vnoise(x, y, 6.0, 3))
    else:
        g = clamp((y - HORIZON) / (SIZE - HORIZON))
        c = lerp(TABLE_FAR, TABLE_NEAR, g ** 0.75)
        c = lerp(c, scale(c, 1.16), vnoise(x * 0.6, y * 3.0, 4.0, 7))   # grain
    if not lit:
        return c

    # the lamp pool, upper left, and the corners falling away from it
    d = math.hypot(x - 2.0, y - 1.0) / 34.0
    c = scale(c, 1.18 - 0.48 * clamp(d * 1.5))

    if y > HORIZON - 1.0:
        # The ball has to sit on something. The lamp is upper left, so the
        # shadow may only spread to the lower right — a pool centred under the
        # ball would darken the table BEHIND it too, and then the ball floats.
        sx, sy = (x - (CX + 4.6)) / 11.0, (y - (CY + 11.0)) / 3.6
        s = math.hypot(sx, sy)
        if s < 1.0:
            # a shadow is the table with the lamp taken off it, not a hole
            c = lerp(lerp(scale(c, 0.30), SHADOW, 0.35), c, clamp(s) ** 0.7)
        k = tail_shadow(p)
        if k:
            c = lerp(c, SHADOW, k * 0.55)
    return c


def fuzz(p):
    """Wool has no edge. A little halo of stray fibre, thickest where lit."""
    d = math.hypot(p[0] - CX, p[1] - CY)
    if d <= R or d > R + 1.3:
        return None
    u = norm3((p[0] - CX, p[1] - CY, 0.001))
    a = (1.0 - (d - R) / 1.3) ** 1.5
    a *= 0.30 + 0.70 * clamp(0.5 + 0.5 * dot3(u, LIGHT))
    a *= 0.45 + 0.55 * vnoise(p[0] * 2.2, p[1] * 2.2, 1.1, 11)
    # Pale, and faint. Rendered in the wool's own colour at the alpha the shape
    # wanted, the halo stopped being fibre and became a ring of violet blocks
    # parked outside the ball — stray fibre is thin enough to be lit THROUGH,
    # so it belongs near white, and it belongs under a third of an alpha.
    c = lerp(dye((d * 3.1 + p[1] * 0.7) / N_WRAPS * REPEATS + PHASE),
             (255, 226, 206), 0.55)
    return c, clamp(a * 0.38)


# ----------------------------------------------------------------- render ---
def build():
    """One record per subpixel: what is there, and in what order it arrives."""
    off = [(k + 0.5) / SS - 0.5 for k in range(SS)]
    subs = {}
    for y in range(SIZE):
        for x in range(SIZE):
            rec = []
            for dy in off:
                for dx in off:
                    p = (x + dx, y + dy)
                    d = math.hypot(p[0] - CX, p[1] - CY)
                    covers, mass, ang = [], None, {}
                    if d <= R:
                        z = math.sqrt(max(1e-6, R * R - d * d))
                        u = ((p[0] - CX) / R, (p[1] - CY) / R, z / R)
                        mass = mass_colour(u)
                        for k in range(N_WRAPS):
                            if abs(dot3(u, AXES[k])) < BAND:
                                c, a = strand_colour(u, k)
                                covers.append((k, c))
                                ang[k] = a
                    rec.append({
                        "ball": d <= R,
                        "covers": covers,
                        "ang": ang,
                        "mass": mass,
                        "needle": needle(p) if d > R else None,
                        "tail": tail_at(p),
                        "fuzz": fuzz(p),
                        "flat": room(p, False),
                        "lit": room(p, True),
                    })
            subs[(x, y)] = rec
    return subs


def compose(sp, k_max, with_tail, lit):
    if with_tail and sp["tail"]:
        return sp["tail"][0]
    if sp["ball"]:
        top = None
        for k, c in sp["covers"]:
            if k <= k_max:
                top = c
        return top if top is not None else sp["mass"]
    if sp["needle"] is not None:
        return sp["needle"]
    c = sp["lit"] if lit else sp["flat"]
    if lit and sp["fuzz"]:
        c = lerp(c, sp["fuzz"][0], sp["fuzz"][1])
    return c


def avg(recs, fn):
    a = [0.0, 0.0, 0.0]
    for sp in recs:
        c = fn(sp)
        for i in range(3):
            a[i] += c[i]
    return tuple(v / len(recs) for v in a)


# ---------------------------------------------------------------- perform ---
def build_strokes(subs):
    steps = []
    cur = {}

    def emit(p, c):
        steps.append((p[0], p[1], c))
        cur[p] = c

    pts = list(subs.keys())

    # 1. the room, washed in serpentine — the whole panel, ball included: the
    #    ball is going to be built on top of it, the way it would be
    for p in sorted(pts, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0])):
        emit(p, avg(subs[p], lambda sp: sp["flat"]))

    # 2. the needle, behind the ball, laid tip first
    nd = [p for p in pts if any(sp["needle"] is not None and not sp["ball"]
                                for sp in subs[p])]
    for p in sorted(nd, key=lambda p: math.hypot(p[0] - NEEDLE_TIP[0],
                                                 p[1] - NEEDLE_TIP[1])):
        emit(p, avg(subs[p], lambda sp: sp["needle"] if sp["needle"] is not None
                    else sp["flat"]))

    # 3. the mass: the ball arrives as one dark shape before it is any colour
    ball = [p for p in pts if any(sp["ball"] for sp in subs[p])]
    for p in sorted(ball, key=lambda p: math.hypot(p[0] - CX, p[1] - CY)):
        emit(p, avg(subs[p], lambda sp: compose(sp, -1, False, False)))

    # 4. the winding. Each wrap is walked along its own arc, and it paints over
    #    whatever was under it — most wraps are partly buried by the end, which
    #    is what the piece is about.
    for k in range(N_WRAPS):
        vis = []
        for p in ball:
            angs = [sp["ang"][k] for sp in subs[p]
                    if k in sp["ang"] and max(
                        [kk for kk, _ in sp["covers"] if kk <= k], default=-1) == k]
            if angs:
                vis.append((p, sum(angs) / len(angs)))
        if not vis:
            continue
        vis.sort(key=lambda pa: pa[1])
        # start the wrap after its biggest angular gap, so the strand is laid
        # down as one continuous run instead of jumping across the silhouette
        gaps = [( (vis[(i + 1) % len(vis)][1] - vis[i][1]) % (2 * math.pi), i)
                for i in range(len(vis))]
        start = (max(gaps)[1] + 1) % len(vis)
        for i in range(len(vis)):
            p = vis[(start + i) % len(vis)][0]
            emit(p, avg(subs[p], lambda sp: compose(sp, k, False, False)))

    # 5. the loose end unspools out of the ball and across the table
    tl = [(p, min(sp["tail"][1] for sp in subs[p] if sp["tail"]))
          for p in pts if any(sp["tail"] for sp in subs[p])]
    for p, _t in sorted(tl, key=lambda pt: pt[1]):
        emit(p, avg(subs[p], lambda sp: compose(sp, N_WRAPS - 1, True, False)))

    # 6. the light: the shadow that seats it, the lamp pool, the halo of fibre
    final = {p: avg(subs[p], lambda sp: compose(sp, N_WRAPS - 1, True, True))
             for p in pts}
    late = [p for p in pts
            if max(abs(final[p][i] - cur[p][i]) for i in range(3)) > 5.0]
    late.sort(key=lambda p: math.hypot(p[0] - CX, p[1] - CY))
    for p in late:
        emit(p, final[p])

    # cur, not final: the piece is whatever the last stroke on each pixel left
    # there, and the light pass deliberately skips pixels it would barely move.
    # Saving the ideal instead of the delivered thing is how a still ends up
    # not matching the canvas it is supposed to be a mirror of.
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

    # ---- checks: measure the piece, do not eyeball it (hourglass, 2026-07-30)
    ball = [p for p in subs if any(sp["ball"] for sp in subs[p])]
    room_px = [p for p in subs if p not in set(ball)]
    val = lambda c: max(c)

    seen = set()
    bare = 0
    for p in ball:
        for sp in subs[p]:
            if sp["ball"]:
                ks = [k for k, _ in sp["covers"]]
                if ks:
                    seen.add(max(ks))
                else:
                    bare += 1
    bv = [val(final[p]) for p in ball]
    rv = [val(final[p]) for p in room_px]

    # do the wraps actually READ as wraps? a smooth ball and a wound one differ
    # in exactly one measurable way: the second one is not smooth
    diffs = []
    for x in range(1, SIZE - 1):
        for y in range(1, SIZE - 1):
            if (x, y) in set(ball) and (x + 1, y) in set(ball):
                diffs.append(abs(val(final[(x, y)]) - val(final[(x + 1, y)])))
    ridges = sum(diffs) / len(diffs)

    # A wound ball has no BALD SPOT. Nine per cent of the surface being gap
    # says nothing about whether the gaps are spread between the wraps (wool)
    # or pooled into one dead region the size of a thumbprint (a hole in the
    # picture) — the fifth attempt had exactly that in the upper right and the
    # gap fraction was perfectly happy about it. So measure the biggest one.
    bald = set()
    for p in ball:
        if not any(sp["covers"] for sp in subs[p] if sp["ball"]):
            bald.add(p)
    biggest, left = 0, set(bald)
    while left:
        stack, blob = [left.pop()], 1
        while stack:
            x, y = stack.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in left:
                    left.discard(q)
                    stack.append(q)
                    blob += 1
        biggest = max(biggest, blob)

    hues = {}
    for p in ball:
        c = final[p]
        if val(c) > 60:
            h = "blue" if c[2] > c[0] else ("warm" if c[0] > c[2] + 60 else "rose")
            hues[h] = hues.get(h, 0) + 1

    print(f"ball={len(ball)}px  wraps visible={len(seen)}/{N_WRAPS}  "
          f"gaps={round(100 * bare / (len(ball) * SS * SS))}%")
    print(f"value  ball {round(min(bv))}..{round(max(bv))} "
          f"mean {round(sum(bv) / len(bv))}   room mean {round(sum(rv) / len(rv))}")
    # the silhouette test: the ball's WORST lit quadrant still has to sit above
    # the room it is standing in, or the circle stops being a circle
    quad = {}
    for p in ball:
        q = ("N" if p[1] < CY else "S") + ("W" if p[0] < CX else "E")
        quad.setdefault(q, []).append(val(final[p]))
    quads = {q: round(sum(v) / len(v)) for q, v in quad.items()}
    worst = min(quads.values())
    print(f"ridge contrast={round(ridges, 1)}   hues={hues}")
    print(f"quadrants={quads}  worst={worst}  room={round(sum(rv) / len(rv))}")
    print(f"bald pixels={len(bald)}  biggest patch={biggest}px")
    print(f"{len(steps)} strokes")

    assert len(ball) > 380, f"the ball is too small at {len(ball)}px"
    assert len(seen) >= N_WRAPS * 0.6, \
        f"only {len(seen)} of {N_WRAPS} wraps survive to the surface"
    gapfrac = bare / (len(ball) * SS * SS)
    assert 0.005 < gapfrac < 0.30,         f"{round(gapfrac * 100)}% of the surface is gap — the wraps are wrong"
    assert min(bv) < 70 and max(bv) > 205, "the ball has to run dark to lit"
    assert sum(bv) / len(bv) > sum(rv) / len(rv) + 25, "the ball is sinking"
    assert worst > sum(rv) / len(rv) + 18,         f"the {min(quads, key=quads.get)} quadrant ({worst}) has sunk into the room"
    assert biggest <= 6, f"a {biggest}px bald patch — no wrap goes over it"
    assert ridges > 12.0, f"ridge contrast {ridges} — this is a smooth ball"
    assert len(hues) == 3 and min(hues.values()) > 25, \
        f"the dye run is not reaching the surface: {hues}"

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview(final, "art/skein.png")
        raise SystemExit

    preview(final, "art/skein.png")
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.012
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
