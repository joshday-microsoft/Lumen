"""One big violin, seen close up — a still.

Nothing in the ledger makes a sound. This is the first musical subject, and the
first piece composed as a CROP rather than a whole object: the panel is filled
by the lower two thirds of a violin's belly, so every part of it gets real
pixels instead of a whole instrument shrunk to a diagram. The frame runs from
the waist (with both C-bout corners in shot) down past the widest part of the
lower bout to the bottom edge and its saddle. The strings run off the top.

The lighting model is the varnish. There are no outlines anywhere: the plate is
shaded purely by DISTANCE TO ITS OWN EDGE, so the arching glows in the middle
of every bout and rolls off into the recurve groove, the purfling line and the
lit rim — the same four bands all the way around the shape, bottom curve
included. Everything small is value, not hue: the f-holes are a one-pixel dark
slot that only reads because the plate on their upper-left side is brightened
where the cut rolls over, the spruce grain is a +/-3.5% modulation that tightens
toward the centre joint, and the four strings are sub-pixel tonal lines that
differ from each other only in width and metal.

Designed as a still (art/violin.png). It ships through /paint rather than
/image because this unit's image-upload path renders blank (see the lumen
skill). The stroke order is a luthier's: bare room, varnish flooded on in
sweeps, one lap around the edge to lay the purfling, the f-holes cut, the
tailpiece hung, the strings drawn on in four long runs, the bridge stood up
last — and then a final pass that lets the light into the room.

Run (perform):  .venv\\Scripts\\python.exe art\\violin.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\violin.py preview -> art\\violin.png
"""

import bisect
import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                       # supersampling per axis

# ------------------------------------------------------------------ frame ---
# Dead vertical, and the centre line sits on a pixel CENTRE. A 5 degree tilt
# looked more like a photograph and cost the piece its strings: over the 20px
# they cross, the drift is a full 1.7px string spacing, so four sub-pixel lines
# smear through every phase and land as one grey band. Vertical and phase-locked,
# each string owns a column outright and the amber between them survives.
THETA = math.radians(0.0)
CX, CY = 16.0, 16.0          # rotation centre
X0 = 15.5                    # the instrument's centre line, in panel x
YB = 10.0                    # the bridge line, in panel y
MM = 6.9                     # millimetres per pixel at this crop
# Foreshortening, as if the eye were ~30 degrees off the plate's normal instead
# of straight above it. Dead-on, the crop that keeps the bottom edge in frame
# pushes both C-bout corners off the top, and without the corners the waist
# reads as a gentle taper and the whole silhouette stops saying violin. At 0.93
# the corners land on the top row and the bottom edge on the last one, which is
# the least squash that still buys the whole hourglass.
VS = 0.93

# --------------------------------------------------------------- palette ----
BG_TOP = (10, 13, 21)
BG_LOW = (17, 20, 30)

VARN_MID = (238, 166, 82)    # the arched middle of a bout, full light
VARN_EDGE = (146, 80, 32)    # varnish pooling dark down in the recurve
RIM = (250, 208, 142)        # the plate edge itself, catching the key light
PURF = (26, 14, 11)          # purfling, sub-millimetre — a tonal line only

FHOLE = (9, 6, 7)
FCUT = (252, 214, 152)       # the cut edge of the f, rolling into the light

TAIL = (33, 29, 36)          # ebony
TAIL_SHEEN = (128, 120, 130)
BRIDGE_HI = (248, 232, 196)  # maple, kept paler and cooler than the varnish
BRIDGE_LO = (198, 168, 118)  # or it smears into the belly it stands on
BRIDGE_FOOT = (110, 80, 48)

# Silver on a lit amber belly is the same VALUE, so pale strings dissolve into
# the wood. Real ones read dark: they are thin, and what faces the eye is
# mostly their shaded underside with one specular line down the lit edge.
STRINGS = [                  # u at the bridge, half-width, colour
    (-3.0, 0.42, (98, 74, 54)),       # G, copper wound
    (-1.0, 0.39, (104, 102, 112)),    # D
    (1.0, 0.37, (122, 122, 132)),     # A
    (3.0, 0.34, (152, 152, 164)),     # E, bare steel
]

# ------------------------------------------------------------- body shape ---
# Half-widths down the body, in pixels, measured from the bridge line (v=0).
# Three segments meeting at the two C-bout corners: the corners are SEGMENT
# ENDS, so the interpolation kinks there and they come out as points instead of
# knuckles. Concave between them, round at both bouts.
SEG_UPPER = [(-21.7, 12.2), (-17.4, 11.9), (-13.8, 10.4), (-10.9, 9.55)]
SEG_C = [(-10.9, 9.55), (-8.0, 8.35), (-5.8, 8.08), (-1.4, 7.97),
         (1.4, 8.19), (3.6, 9.55)]
SEG_LOWER = [(3.6, 9.55), (8.0, 12.3), (13.0, 15.1), (17.4, 14.2),
             (21.0, 10.4), (22.9, 5.8), (23.55, 0.0)]
V_BOT = 23.55

# ------------------------------------------------------------- f-hole path --
# Anatomically the f-hole notches sit at the bridge's own width, which would put
# this slot straight underneath the outer string in a top view — true, and
# illegible at 32px. The whole f is pushed 1.3px outboard so the strings and the
# holes each get clear pixels; nothing else in the drawing moves.
FPATH = [(4.20, -6.1), (4.50, -4.2), (4.72, -2.2), (4.85, -0.4),
         (5.25, 1.6), (5.85, 3.6), (5.80, 5.6)]
FEYE_UP = (4.15, -6.45, 0.82)
FEYE_LO = (5.80, 5.95, 1.05)

# -------------------------------------------------------------- tailpiece ---
TAIL_PROFILE = [(8.0, 2.45), (9.0, 2.52), (14.0, 2.30), (19.0, 1.95),
                (21.5, 1.70), (22.4, 1.20), (22.8, 0.0)]

# ----------------------------------------------------------------- bridge ---
BRIDGE = [(-3.50, 0.0), (-3.00, -0.8), (-2.25, -1.1), (-1.90, -2.0),
          (-2.75, -2.7), (-2.45, -3.4), (2.45, -3.4), (2.75, -2.7),
          (1.90, -2.0), (2.25, -1.1), (3.00, -0.8), (3.50, 0.0)]
BR_TOP = -3.4


# --------------------------------------------------------------- helpers ----
def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale(c, f):
    return tuple(max(0.0, min(255.0, v * f)) for v in c)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def catmull(pts, n=48):
    """Sample a Catmull-Rom spline through pts (endpoints duplicated)."""
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(q) - 3):
        p0, p1, p2, p3 = q[i], q[i + 1], q[i + 2], q[i + 3]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                       + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                for j in range(2)))
    out.append(tuple(pts[-1]))
    return out


def make_lut(segments):
    """One monotone (v -> half-width) table from the three body segments."""
    pts = []
    for seg in segments:
        pts.extend(catmull(seg, 40))
    pts.sort(key=lambda p: p[0])
    vs, ws, last = [], [], -1e9
    for v, w in pts:
        if v > last + 1e-6:
            vs.append(v)
            ws.append(max(0.0, w))
            last = v
    return vs, ws


LUT_V, LUT_W = make_lut([SEG_UPPER, SEG_C, SEG_LOWER])


BODY_W = 0.967               # trims the widest bout so both margins survive
                             # the half-pixel offset of the centre line


def halfwidth(v):
    if v <= LUT_V[0]:
        return LUT_W[0] * BODY_W
    if v >= LUT_V[-1]:
        return 0.0
    i = bisect.bisect_left(LUT_V, v)
    v0, v1 = LUT_V[i - 1], LUT_V[i]
    t = (v - v0) / (v1 - v0)
    return (LUT_W[i - 1] + (LUT_W[i] - LUT_W[i - 1]) * t) * BODY_W


def profile_at(table, v):
    if v <= table[0][0] or v >= table[-1][0]:
        return 0.0
    for i in range(1, len(table)):
        if v <= table[i][0]:
            (v0, w0), (v1, w1) = table[i - 1], table[i]
            return w0 + (w1 - w0) * (v - v0) / (v1 - v0)
    return 0.0


# closed outline of the plate, for the edge distance field
def build_outline():
    # built in PANEL units (v foreshortened), so that one unit of edge distance
    # is one pixel on the bottom curve as well as on the flanks — otherwise the
    # purfling runs 15% thinner along the bottom than up the sides
    vs = [-20.0 + i * (V_BOT + 20.0) / 150.0 for i in range(151)]
    right = [(halfwidth(v), v * VS) for v in vs]
    left = [(-w, v) for w, v in reversed(right)]
    return right + left


OUTLINE = build_outline()
OUT_SEGS = [(OUTLINE[i], OUTLINE[(i + 1) % len(OUTLINE)])
            for i in range(len(OUTLINE))]

FCURVE = catmull(FPATH, 12)
BR_SEGS = [(BRIDGE[i], BRIDGE[(i + 1) % len(BRIDGE)]) for i in range(len(BRIDGE))]


def inside_poly(pt, poly):
    x, y = pt
    hit = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                hit = not hit
    return hit


def seg_dist(pt, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else clamp(((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / L2)
    return math.hypot(pt[0] - (a[0] + t * dx), pt[1] - (a[1] + t * dy))


def edge_distance(u, v):
    """Signed distance to the plate outline in panel pixels, positive inside."""
    p = (u, v * VS)
    best = 1e9
    for a, b in OUT_SEGS:
        d = seg_dist(p, a, b)
        if d < best:
            best = d
    return best if inside_poly(p, OUTLINE) else -best


def fhole_metrics(u, v):
    """(distance past the slot wall, side sign) for the nearer f-hole."""
    au = abs(u)
    best, bp = 1e9, None
    for i in range(len(FCURVE) - 1):
        d = seg_dist((au, v), FCURVE[i], FCURVE[i + 1])
        if d < best:
            best, bp = d, FCURVE[i]
    t = clamp((v - FPATH[0][1]) / (FPATH[-1][1] - FPATH[0][1]))
    w = 0.54 + 0.12 * math.sin(math.pi * t)
    d_slot = best - w
    for ex, ey, er in (FEYE_UP, FEYE_LO):
        d_slot = min(d_slot, math.hypot(au - ex, v - ey) - er)
    # which side of the cut a pixel sits on, in the mirrored half-space
    side = 1.0 if (au - (bp[0] if bp else 0.0)) < 0 else -1.0
    if u < 0:
        side = -side
    return d_slot, side


def string_spread(v):
    """Dead parallel down to the bridge, then in hard to the tailpiece.

    The real taper toward the nut is about a sixth of a pixel across this crop —
    not worth blurring every column above the bridge to say it.
    """
    if v <= 0:
        return 1.0
    return 1.0 - 0.18 * (v / 8.05)


def string_at(u, v):
    """(index, offset across the string) if a string covers this point."""
    if v > 8.05:
        return None
    f = string_spread(v)
    for i, (ub, w, _) in enumerate(STRINGS):
        du = u - ub * f
        if abs(du) <= w:
            return i, du
    return None


def string_shadow(u, v):
    """How much a string darkens the plate just to its lower-right.

    Silver on amber is nearly the same value at this size — the strings only
    read as strings because of the four thin shadows lying beside them.
    """
    if v > 8.4:
        return 1.0
    f = string_spread(v)
    dark = 1.0
    for ub, w, _ in STRINGS:
        du = abs(u - ub * f - 0.66)
        if du < w + 0.24:
            dark = min(dark, 0.68 + 0.32 * clamp((du - w) / 0.24))
    return dark


def grain(u, v):
    """Spruce: tight at the centre joint, opening toward the flanks."""
    au = abs(u)
    phase = au / (0.55 + 0.052 * au ** 1.35) + 0.18 * math.sin(v * 0.31 + au * 0.5)
    return 1.0 + 0.026 * math.sin(2.0 * math.pi * phase)


def keylight(x, y):
    t = clamp(((16.0 - x) * 0.62 + (20.0 - y) * 0.78) / 30.0 + 0.5)
    return 0.83 + 0.36 * t


def sheen(x, y):
    """Varnish gloss: one long soft blaze across the upper-left lower bout."""
    dx, dy = x - 10.2, y - 20.6
    a = math.radians(-38.0)
    p = dx * math.cos(a) - dy * math.sin(a)
    q = dx * math.sin(a) + dy * math.cos(a)
    return 0.30 * math.exp(-((p / 7.4) ** 2 + (q / 2.5) ** 2))


def to_instrument(x, y):
    dx, dy = x - CX, y - CY
    c, s = math.cos(-THETA), math.sin(-THETA)
    rx = dx * c - dy * s
    ry = dx * s + dy * c
    return (rx + CX) - X0, ((ry + CY) - YB) / VS


# --------------------------------------------------------------- geometry ---
def geom(x, y):
    u, v = to_instrument(x, y)
    g = {"x": x, "y": y, "u": u, "v": v}
    g["d"] = edge_distance(u, v)

    part = "bg"
    if g["d"] > 0.0:
        part = "plate"
        ds, side = fhole_metrics(u, v)
        g["fd"], g["fside"] = ds, side
        tw = profile_at(TAIL_PROFILE, v)
        st = string_at(u, v)
        # the bridge stands in front of its own strings, except for the sliver
        # of top edge they actually cross over
        onbridge = inside_poly((u, v), BRIDGE)
        if onbridge and not (st is not None and v < BR_TOP + 0.85):
            part = "bridge"
        elif st is not None:
            part, g["s"] = "string", st
        elif tw > 0.0 and abs(u) <= tw:
            part = "tail"
        elif ds <= 0.0:
            part = "fhole"
        elif g["d"] < 3.4:
            part = "edge"
    g["part"] = part

    # cast shadows, in panel space, offset down-right from the key light
    sx, sy = x - 0.95, y - 1.15
    su, sv = to_instrument(sx, sy)
    stw = profile_at(TAIL_PROFILE, sv)
    g["shadow"] = (inside_poly((su, sv), BRIDGE)
                   or (stw > 0.0 and abs(su) <= stw))
    return g


# ---------------------------------------------------------------- shading ---
def plate_colour(g, lit):
    d, u, v, x, y = g["d"], g["u"], g["v"], g["x"], g["y"]

    # 1. the arching: brightness is purely a function of distance to the edge,
    #    so every bout glows in its own middle and the bottom curve behaves
    #    exactly like the flanks
    a = 1.0 - clamp(d / 5.5)
    c = lerp(VARN_MID, VARN_EDGE, a ** 1.35)

    # 2. the four edge bands: recurve groove, purfling, roll, lit rim
    if d < 3.4:
        c = scale(c, 0.72 + 0.28 * clamp((d - 1.9) / 1.5)) if d >= 1.9 else c
    if d < 1.95:
        if d < 0.55:
            c = RIM
        elif d < 1.05:
            c = lerp(RIM, PURF, (d - 0.55) / 0.5)
        else:
            c = lerp(PURF, scale(VARN_EDGE, 0.78), clamp((d - 1.05) / 0.9) ** 1.6)

    c = scale(c, grain(u, v))

    # 3. the cut edge of the f-hole rolls into the light on its upper-left
    fd = g.get("fd", 9.0)
    if 0.0 < fd < 0.70:
        f = (1.0 - fd / 0.70) ** 1.1
        c = lerp(c, FCUT, 0.58 * f) if g["fside"] > 0 else scale(c, 1.0 - 0.34 * f)

    c = scale(c, string_shadow(u, v))
    c = scale(c, keylight(x, y))
    if lit:
        if g["shadow"]:
            c = scale(c, 0.58)
        c = lerp(c, (255, 228, 180), sheen(x, y))
    return c


def shade(g, lit):
    part, x, y = g["part"], g["x"], g["y"]

    if part == "bg":
        c = lerp(BG_TOP, BG_LOW, clamp(y / 31.0) ** 1.3)
        if lit and -2.6 < g["d"] <= 0.0:          # the plate seats itself
            c = scale(c, 0.55 + 0.45 * (-g["d"] / 2.6))
        return c

    if part in ("plate", "edge"):
        return plate_colour(g, lit)

    if part == "fhole":
        return scale(FHOLE, keylight(x, y) * 0.9)

    if part == "tail":
        u, v = g["u"], g["v"]
        c = lerp(TAIL, TAIL_SHEEN, 0.55 * math.exp(-((u + 0.55) / 0.95) ** 2))
        if v < 8.4:                                # lit top edge, where strings end
            c = lerp(c, (186, 176, 186), 0.35)
        if v > 22.0:
            c = scale(c, 0.7)
        return scale(c, keylight(x, y))

    if part == "bridge":
        v = g["v"]
        c = BRIDGE_HI if v < -2.35 else (BRIDGE_LO if v < -0.75 else BRIDGE_FOOT)
        return scale(c, keylight(x, y) * 1.02)

    if part == "string":
        i, du = g["s"]
        c = STRINGS[i][2]
        c = scale(c, 1.55 if du < 0 else 0.86)
        return scale(c, keylight(x, y))

    return (0, 0, 0)


# ----------------------------------------------------------------- render ---
def render():
    off = [(k + 0.5) / SS - 0.5 for k in range(SS)]
    flat, final, owner = {}, {}, {}
    for y in range(SIZE):
        for x in range(SIZE):
            af = [0.0, 0.0, 0.0]
            al = [0.0, 0.0, 0.0]
            for dy in off:
                for dx in off:
                    g = geom(x + dx, y + dy)
                    cf, cl = shade(g, False), shade(g, True)
                    for i in range(3):
                        af[i] += cf[i]
                        al[i] += cl[i]
            n = SS * SS
            flat[(x, y)] = tuple(v / n for v in af)
            final[(x, y)] = tuple(v / n for v in al)
            owner[(x, y)] = geom(x + 0.5, y + 0.5)["part"]
    return flat, final, owner


# ---------------------------------------------------------------- strokes ---
def build_strokes(flat, final, owner):
    steps = []

    def take(names, key, src):
        px = sorted([p for p in owner if owner[p] in names], key=key)
        for p in px:
            steps.append((p[0], p[1], src[p]))

    def serp(p):
        return (p[1], p[0] if p[1] % 2 == 0 else -p[0])

    # 1. the bare room
    take({"bg"}, serp, final)
    # 2. varnish flooded on in sweeps, edge bands still unlaid
    take({"plate"}, serp, flat)
    # 3. one lap around the edge: recurve, purfling, rim
    take({"edge"}, lambda p: math.atan2(p[1] - 16, p[0] - 16), flat)
    # 4. the f-holes cut, left one then right, each top to bottom
    take({"fhole"}, lambda p: (p[0] > 16, p[1]), flat)
    # 5. the tailpiece hung
    take({"tail"}, lambda p: (p[1], p[0]), flat)
    # 6. four long runs of string
    take({"string"}, lambda p: (p[0] > 16.5, abs(p[0] - 16.2) // 1.7, p[1]), flat)
    # 7. the bridge stood up last
    take({"bridge"}, lambda p: (-p[1], p[0]), flat)

    # 8. let the light in: sheen, cast shadows, seating
    detail = [p for p in owner if final[p] != flat[p]]
    detail.sort(key=lambda p: math.hypot(p[0] - 10.2, p[1] - 20.6))
    for p in detail:
        steps.append((p[0], p[1], final[p]))
    return steps


def render_preview(final, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for (x, y), c in final.items():
        px[x, y] = tuple(max(0, min(255, round(v))) for v in c)
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    flat, final, owner = render()
    counts = {}
    for p in owner.values():
        counts[p] = counts.get(p, 0) + 1
    print("regions:", counts)

    steps = build_strokes(flat, final, owner)
    print(f"{len(steps)} strokes")

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(final, "art/violin.png")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.016
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
