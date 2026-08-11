"""One big ammonite, weathered out of a slab of slate — a still.

The first FOSSIL in the ledger, and the first subject that is neither alive nor
made: a shell that stopped growing a hundred and fifty million years ago, lying
in the rock that kept it. Everything in the frame is either the animal or the
stone it is stuck in.

This piece began as a cracked-open geode and that version is not in the repo,
because it taught the lesson the hard way and the lesson is worth more than the
attempt: at 32x32 a subject needs a SILHOUETTE. A geode's whole character is
material — banding, druzy, a pocket full of little prisms — and every one of
those is texture, which at this size collapses into noise no matter how it is
lit, quantised or cropped. An ammonite is the same mood (ancient, patient,
mineral) carried by pure geometry, and a logarithmic spiral is about the most
legible shape there is at any resolution.

So the whole drawing is one equation. A point's radius and angle give its
position ALONG the spiral, and everything is a function of where it sits across
the whorl it landed in:

  - the whorl profile is a half-tube, bright along its crest and pinched to
    nothing at both sutures, so the shell reads as coiled rope rather than as
    a flat plate with lines scratched on it;
  - the surface normal rotates with that same coordinate — radially outward at
    the outer suture, at the viewer along the crest, radially inward at the
    inner one — so one lamp at the upper left lights all three and a half turns
    consistently and the underside of the coil goes dark on its own;
  - the ribs are a sinusoid in the spiral parameter, which means they stay
    perpendicular to the shell everywhere and crowd together toward the middle
    exactly as the real ones do, without a single one being placed by hand.

The aperture needs no special case either: the shell simply stops at a fixed
spiral parameter, so past that angle the outer whorl is not there and the next
one down is what you see, which puts a clean radial cut at the mouth.

Delivered via /paint rather than /image because this unit's image-upload path
renders blank (see the lumen skill), and the order is an excavation: the slab
goes down first, then the shell GROWS out of it the way it grew in life, from
the tiny inner coil outward along the spiral, one whorl lapping the last, and
the light and the shadow that seats it in the rock arrive at the end.

Run (perform):  .venv\\Scripts\\python.exe art\\ammonite.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\ammonite.py preview
"""

import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                        # supersampling per axis

_L = (-0.62, -0.78)                    # one lamp, upper left
LIGHT = (_L[0] / math.hypot(*_L), _L[1] / math.hypot(*_L))

# --------------------------------------------------------------- geometry ---
# A spiral's outline is not a circle: at the aperture it reaches R_MAX, but a
# third of a turn round it is back to less than half that. Sizing it so the
# widest point merely fits leaves the panel two thirds empty, so R_MAX is set
# past the frame and the mouth is allowed to graze the right edge.
CX, CY = 13.6, 17.0                    # the umbilicus, placed by MEASURING the
                                       # shell's bounding box and centring that,
                                       # not by centring the coil's eye — a
                                       # spiral's mass sits well off its middle
# Growth rate is a legibility decision, not a taxonomic one. At 2.5x per turn
# the outer whorl is eleven pixels of unbroken shell — a third of the panel
# with nothing happening in it. At 1.95x there are four and a half turns and
# the widest whorl is seven, which is a coil instead of a blob.
B = 0.105
S_MAX = 28.5                           # total sweep, 4.5 turns
R_MAX = 18.0                           # radius at the aperture
A = R_MAX / math.exp(B * S_MAX)        # so R(S_MAX) = R_MAX
PHI_AP = 0.78                          # the mouth opens to the lower right
PHI0 = PHI_AP - S_MAX
TWO_PI = 2.0 * math.pi

NR = 5.25                              # ribs per radian ~ 33 per whorl
UMB = 0.95                             # the dark eye at the middle

# ---------------------------------------------------------------- palette ---
# Warm bone shell against cold stone: the two halves of the picture are told
# apart by temperature as well as by value, so the fossil still separates from
# the matrix where they happen to meet at the same brightness.
SHELL_DARK = (58, 44, 32)
SHELL_MID = (146, 116, 78)
SHELL_LIT = (242, 218, 172)
SUTURE = (40, 30, 22)

ROCK_LIT = (78, 82, 92)
ROCK_DARK = (28, 30, 36)
CONTACT = (16, 17, 21)                 # the shell's shadow in its own hollow


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale(c, f):
    return tuple(max(0.0, min(255.0, v * f)) for v in c)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def hash2(x, y, s):
    h = (x * 374761393 + y * 668265263 + s * 1442695040) & 0xFFFFFFFF
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


# ----------------------------------------------------------------- spiral ---
def spiral(p):
    """Where a point sits on the shell.

    Returns None outside it, else (rho, phi, s_edge, frac):
      s_edge  how far ALONG the spiral this whorl's outer suture is — the
              drawing order, and the rib phase
      frac    across the whorl: 0 at its outer suture, ->1 at the inner one
    """
    dx, dy = p[0] - CX, p[1] - CY
    rho = math.hypot(dx, dy)
    if rho < UMB or rho > R_MAX + 0.5:
        return None
    phi = math.atan2(dy, dx)
    t = phi - PHI0

    # the outermost whorl present at this angle: past the mouth there is one
    # fewer turn, which is what cuts the aperture without a special case
    k = math.floor((S_MAX - t) / TWO_PI)
    s_out = t + TWO_PI * k
    if s_out < 0.0:
        return None
    if rho > A * math.exp(B * s_out):
        return None

    s_p = math.log(rho / A) / B                      # this point's own parameter
    kk = math.ceil((s_p - t) / TWO_PI - 1e-9)
    s_edge = t + TWO_PI * kk                         # the suture just outside it
    return rho, phi, s_edge, clamp((s_edge - s_p) / TWO_PI, 0.0, 0.9999), s_out


def shell_colour(g, lit):
    rho, phi, s_edge, frac, s_out = g

    # the whorl is a half-tube: pinched at both sutures, crested in the middle
    # sin() alone keeps half the whorl within a whisker of full brightness and
    # the coil renders as flat cream with scratches; the crest has to be narrow
    prof = math.sin(math.pi * frac) ** 1.6
    inplane = math.cos(math.pi * frac)               # +1 outward at the outer suture
    nx, ny = math.cos(phi) * inplane, math.sin(phi) * inplane
    diff = clamp(0.78 * (nx * LIGHT[0] + ny * LIGHT[1]) + 0.80 * prof)
    v = 0.22 + 0.94 * diff

    # Ribs, in the spiral parameter, so they stay square to the shell and crowd
    # toward the middle by themselves. Kept faint on purpose: at full strength
    # they cross the sutures at right angles every three pixels and the coil
    # turns into a chequerboard. The spiral is the subject; the ribs are only
    # meant to say the surface is not smooth.
    v *= 1.0 + 0.11 * math.cos(s_edge * NR + 0.9 * frac)

    if v < 0.5:
        c = lerp(SHELL_DARK, SHELL_MID, clamp(v / 0.5))
    else:
        c = lerp(SHELL_MID, SHELL_LIT, clamp((v - 0.5) / 0.62))

    # the suture itself: a hard dark line, not a fade — it is the one place the
    # coil has to be readable as two surfaces meeting
    if frac < 0.085:
        c = lerp(SUTURE, c, clamp(frac / 0.085) ** 0.7)
    elif frac > 0.915:
        c = lerp(SUTURE, c, clamp((1.0 - frac) / 0.085) ** 0.7)

    # The mouth. Without it the outermost whorl simply stops, which reads as a
    # spiral that ran out of room rather than as a shell an animal lived in —
    # the body chamber is open, so its end face is a hole, not more shell.
    ap = S_MAX - s_out
    if ap < 0.155:
        c = lerp(SUTURE, c, clamp(ap / 0.155) ** 0.6)

    # older whorls sit deeper in the rock and are duller
    c = scale(c, 0.86 + 0.20 * clamp(rho / R_MAX))

    # One more light term, across the whole fossil rather than across each
    # whorl. Without it every crest is equally bright wherever it lies, and
    # four turns of equally lit rope is a flat pattern — this is what makes the
    # coil sit in a hollow with a lit side and a shaded one.
    # The floor is not a taste call: below it the shaded whorls go darker than
    # the slab they lie in, and a fossil that meets its matrix at equal value
    # stops having an edge (the knight, 2026-08-08).
    c = scale(c, 0.78 + 0.46 * clamp(0.5 + rho * (
        math.cos(phi) * LIGHT[0] + math.sin(phi) * LIGHT[1]) / 26.0))
    if lit and prof > 0.55:                          # sheen along the crests
        k = (prof - 0.55) / 0.45
        s = clamp(0.55 * (nx * LIGHT[0] + ny * LIGHT[1]) + 0.5)
        c = lerp(c, (255, 246, 224), 0.30 * k * s ** 2)
    return c


def rock_colour(p, lit, near):
    x, y = p
    n = (0.5 * vnoise(x, y, 2.6, 5) + 0.35 * vnoise(x, y, 1.2, 9)
         + 0.15 * vnoise(x, y, 5.0, 13))
    c = lerp(ROCK_DARK, ROCK_LIT, clamp(n * 1.25))
    c = scale(c, 0.84 + 0.32 * clamp(0.5 + ((16 - x) * 0.3 + (16 - y) * 0.4) / 26.0))
    if lit:
        # the shell lies IN the slab, so the rock dips into shadow against it
        if near is not None and near < 2.6:
            c = lerp(CONTACT, c, clamp(near / 2.6) ** 0.75)
        r = math.hypot(x - 15.0, y - 15.0) / 22.0    # corners fall away
        c = scale(c, 1.0 - 0.30 * clamp(r) ** 2)
    return c


def outside_gap(p):
    """Roughly how far a rock pixel is from the fossil, for the contact shadow.

    The lamp is upper left, so the hollow reads deepest on the lower right.
    """
    dx, dy = p[0] - CX, p[1] - CY
    rho = math.hypot(dx, dy)
    phi = math.atan2(dy, dx)
    t = phi - PHI0
    k = math.floor((S_MAX - t) / TWO_PI)
    s_out = t + TWO_PI * k
    if s_out < 0.0:
        return None
    edge = A * math.exp(B * s_out)
    if rho <= edge:
        return None
    d = rho - edge
    side = 0.55 + 0.75 * clamp(0.5 - 0.5 * (math.cos(phi) * LIGHT[0]
                                            + math.sin(phi) * LIGHT[1]))
    return d / side


def shade(p, lit):
    g = spiral(p)
    if g is None:
        if math.hypot(p[0] - CX, p[1] - CY) < UMB:
            return scale(SUTURE, 0.8), "umbilicus"
        return rock_colour(p, lit, outside_gap(p)), "rock"
    return shell_colour(g, lit), "shell"


# ----------------------------------------------------------------- render ---
def render():
    off = [(k + 0.5) / SS - 0.5 for k in range(SS)]
    flat, final, owner, order = {}, {}, {}, {}
    for y in range(SIZE):
        for x in range(SIZE):
            af, al = [0.0] * 3, [0.0] * 3
            for dy in off:
                for dx in off:
                    p = (x + dx, y + dy)
                    cf = shade(p, False)[0]
                    cl = shade(p, True)[0]
                    for i in range(3):
                        af[i] += cf[i]
                        al[i] += cl[i]
            n = SS * SS
            flat[(x, y)] = tuple(v / n for v in af)
            final[(x, y)] = tuple(v / n for v in al)
            c = (x + 0.5, y + 0.5)
            owner[(x, y)] = shade(c, True)[1]
            g = spiral(c)
            order[(x, y)] = (g[2], -g[3]) if g else (0.0, 0.0)
    return flat, final, owner, order


def build_strokes(flat, final, owner, order):
    steps = []
    pts = list(owner.keys())

    def push(sel, key, src):
        for p in sorted([p for p in pts if sel(owner[p])], key=key):
            steps.append((p[0], p[1], src[p]))

    def serp(p):
        return (p[1], p[0] if p[1] % 2 == 0 else -p[0])

    # 1. the bare slab
    push(lambda o: o in ("rock", "umbilicus"), serp, flat)
    # 2. the shell GROWS: along the spiral from the inner coil outward, each
    #    whorl laid outer suture inward so it laps the one before it
    push(lambda o: o == "shell", lambda p: order[p], flat)
    # 3. the light: crest sheen, the hollow it lies in, the corners falling off
    detail = [p for p in pts if final[p] != flat[p]]
    detail.sort(key=lambda p: (owner[p] == "rock",
                               math.hypot(p[0] - CX, p[1] - CY)))
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
    img.resize((SIZE * 14, SIZE * 14), Image.NEAREST).save(
        path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    flat, final, owner, order = render()

    counts = {}
    for o in owner.values():
        counts[o] = counts.get(o, 0) + 1
    print("regions:", counts)

    def meanv(pred):
        vals = [max(final[p]) for p in owner if pred(owner[p])]
        return round(sum(vals) / max(1, len(vals)), 1)

    print(f"value  shell={meanv(lambda o: o == 'shell')} "
          f"rock={meanv(lambda o: o == 'rock')}")

    # how many whorls actually landed on the panel: the spiral is the piece, so
    # count it rather than trusting it (hourglass, 2026-07-30)
    turns = len({int(order[p][0] // TWO_PI) for p in owner if owner[p] == "shell"})
    shell_v = [max(final[p]) for p in owner if owner[p] == "shell"]
    print(f"whorls={turns}  shell range={round(min(shell_v))}..{round(max(shell_v))}")

    preview = len(sys.argv) > 1 and sys.argv[1] == "preview"
    if preview:
        render_preview(final, "art/ammonite.png")

    assert counts.get("shell", 0) > 330, counts
    assert counts.get("rock", 0) > 250, "the slab has to hold the fossil"
    assert turns >= 3, f"only {turns} whorls reached the panel"
    assert min(shell_v) < 85 and max(shell_v) > 215, \
        "the shell has to run dark to bright or the coil is flat"
    # a percentile, not the minimum: the mouth is SUPPOSED to be a hole, and a
    # handful of pixels darker than the slab is the point of it
    lo = sorted(shell_v)[len(shell_v) // 20]
    assert lo > meanv(lambda o: o == "rock") - 6, \
        f"shaded whorls ({lo}) have sunk into the slab and lost their edge"
    assert meanv(lambda o: o == "shell") > meanv(lambda o: o == "rock") + 30, \
        "the fossil is sinking into the slab"

    steps = build_strokes(flat, final, owner, order)
    print(f"{len(steps)} strokes")
    if preview:
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.015
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
