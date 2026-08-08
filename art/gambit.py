"""One big ebony knight, carved live on the wall — a painting.

Nothing in the ledger is BACKLIT. Every piece so far is a lit subject sitting on
a dark field; this one inverts it. A chess knight in black wood stands against a
lamp burning behind it, so the subject is the darkest thing on the panel and the
room is the brightest, and the horse is read as a silhouette first, a form
second. It is also the first game piece, and the first carved figure.

The performance is the carving. The room is washed in, the board is laid square
by square in perspective, and then a rectangular BILLET of ebony is dropped over
almost the whole panel — a solid dark rectangle that hides everything. From
there the waste is cut away chip by chip, farthest chip first, closing in on the
final surface, so the horse arrives out of a block the way it actually would.
Only then is it shaped: the neck banded, the jaw and muzzle worked, the mane
notched crest-to-withers, the eye drilled, and last of all the light is allowed
around the contour — the rim sweeps from the muzzle up over the ears and down
the mane, which is the moment the piece stops being a shape and becomes wood.

Lighting model: one lamp behind the piece at upper right. Every rim pixel takes
its brightness from the halo sampled just OUTSIDE the silhouette along the
outward normal, so the rim is automatically hottest where the room is hottest
(ears, crest) and nearly absent down at the plinth, with no per-part tuning. The
front planes are held off pure black by a cool bounce off the board from the
lower left — the knight is never allowed to meet the background at equal value.

Ships through /paint rather than /image because this unit's image-upload path
renders blank (see the lumen skill).

Run (perform):  .venv\\Scripts\\python.exe art\\gambit.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\gambit.py preview -> art\\gambit.png
"""

import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                                  # supersamples per axis for the silhouette

# ------------------------------------------------------------------ light ---
# The lamp sits behind the piece, up and to the right. Everything else in the
# scene is derived from this: halo, rim, bounce, and the direction of the shadow
# thrown forward onto the board.
GLOW = (19.5, 6.5)
GLOW_SIG = 12.5
BOUNCE_DIR = (-0.78, 0.63)              # cool fill off the board, from front-left

COOL_DARK = (26, 32, 52)                # the room where the lamp does not reach
AMBER = (214, 146, 62)                  # the lamp itself, at the core of the halo
EBONY = (25, 21, 27)                    # the block, before any light touches it
BOUNCE = (52, 60, 82)                   # what the board throws back onto the front
BOUNCE_RIM = (150, 172, 214)            # and the cold edge it leaves on the front
RIM = (255, 198, 118)

SQ_LIGHT = (132, 103, 70)
SQ_DARK = (52, 39, 34)

# --------------------------------------------------------------- geometry ---
# The knight, in panel coordinates, facing left. Traced as one closed profile:
# plinth, collar, breast, throat, jaw, muzzle, bridge, brow, both ears, crest,
# and the mane ridge running back down to the withers.
KNIGHT = [
    (5.6, 31.8), (5.6, 29.3), (7.6, 28.1), (8.9, 26.7), (8.5, 25.2),
    (10.0, 24.0), (9.5, 21.0), (8.3, 17.9), (6.5, 14.6), (5.1, 12.1),
    (3.3, 10.7), (2.2, 9.3), (2.7, 7.8), (4.8, 6.9), (7.5, 5.3),
    (9.2, 3.2), (10.2, 0.6), (12.2, 4.6), (14.3, 1.4), (15.4, 5.3),
    (17.7, 7.6), (19.9, 11.1), (21.5, 15.1), (22.5, 19.6), (23.1, 23.6),
    (23.6, 25.7), (24.4, 26.9), (25.2, 28.2), (26.3, 29.3), (26.3, 31.8),
]

# The mane, as a line rather than a region: a band is grown off it, and the
# notches are cut at a fixed spacing along its arc length.
MANE = [(13.6, 4.8), (16.3, 7.4), (18.5, 10.5), (20.1, 14.3), (21.1, 18.5),
        (21.7, 22.6)]

BILLET = (1, 0, 27, 32)                 # x0, y0, x1, y1 — the block of wood

EYE = (7.5, 8.1)
NOSTRIL = (3.7, 9.3)
MOUTH = ((2.9, 10.5), (5.3, 11.2))
JAW = ((6.1, 9.4), (7.6, 13.4))         # the cheek break, as a value step


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def add(c, d, k=1.0):
    return tuple(c[i] + d[i] * k for i in range(3))


def scale(c, k):
    return tuple(c[i] * k for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def norm(v):
    m = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / m, v[1] / m)


def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = p[0] - a[0], p[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return math.hypot(wx - t * vx, wy - t * vy), t


def path_dist(p, pts):
    """Distance to a polyline, plus arc length at the closest point."""
    best, best_s = 1e9, 0.0
    s = 0.0
    for a, b in zip(pts, pts[1:]):
        d, t = seg_dist(p, a, b)
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if d < best:
            best, best_s = d, s + t * seg
        s += seg
    return best, best_s


def poly_dist(p):
    pts = KNIGHT + [KNIGHT[0]]
    return min(seg_dist(p, a, b)[0] for a, b in zip(pts, pts[1:]))


def inside(p):
    x, y = p
    hit = False
    n = len(KNIGHT)
    for i in range(n):
        ax, ay = KNIGHT[i]
        bx, by = KNIGHT[(i + 1) % n]
        if (ay > y) != (by > y):
            xc = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < xc:
                hit = not hit
    return hit


def sdf(p):
    d = poly_dist(p)
    return d if inside(p) else -d


def coverage(x, y):
    n = 0
    for i in range(SS):
        for j in range(SS):
            if inside((x + (i + 0.5) / SS, y + (j + 0.5) / SS)):
                n += 1
    return n / (SS * SS)


def glow_at(p):
    r2 = (p[0] - GLOW[0]) ** 2 + (p[1] - GLOW[1]) ** 2
    return math.exp(-r2 / (2 * GLOW_SIG ** 2))


def grain(x, y, k=0.055):
    """Deterministic figure in the wood — a fine vertical figure, never noise."""
    h = (x * 73856093) ^ (y * 19349663)
    h = (h * 2654435761) & 0xFFFFFFFF
    speckle = ((h >> 12) & 0xFF) / 255.0 - 0.5
    fig = math.sin(x * 1.9 + y * 0.22) * 0.5
    return 1.0 + k * (fig + speckle * 0.7)


# ------------------------------------------------------------------ scene ---
def room():
    """The lamp-lit room and the board, as a full-panel background."""
    bg = {}
    for y in range(SIZE):
        for x in range(SIZE):
            p = (x + 0.5, y + 0.5)
            g = glow_at(p)
            c = lerp(COOL_DARK, AMBER, g ** 0.85 * 1.05)
            # the room floor falls away toward the viewer
            c = scale(c, 1.0 - 0.10 * max(0.0, (y - 16) / 16))
            bg[(x, y)] = c

    board = set()
    for y in range(SIZE):
        for x in range(SIZE):
            p = (x + 0.5, y + 0.5)
            if p[1] <= 24.6:
                continue
            # honest perspective: screen y -> ground depth, screen x -> ground X
            z = 26.0 / (p[1] - 23.0)
            X = (p[0] - 16.0) * z / 30.0
            checker = (math.floor(X / 4.4) + math.floor(z / 4.4)) % 2
            lit = 0.62 + 0.85 * glow_at(p)
            c = scale(SQ_LIGHT if checker == 0 else SQ_DARK, lit)
            # the lamp is behind, so the piece throws its shadow AT the viewer:
            # a pool that starts at the plinth and spreads down and to the left,
            # never backward — the far strip of board stays lit, and that lit
            # strip is the only thing that keeps the black plinth off the floor.
            sx, sy = p[0] - 12.0, max(0.0, p[1] - 27.6)
            sh = (sx + sy * 0.9) ** 2 / 190.0 + (p[1] - 27.6) ** 2 / 55.0
            if p[1] > 27.0:
                c = scale(c, 0.30 + 0.70 * min(1.0, sh))
            bg[(x, y)] = c
            board.add((x, y))
    return bg, board


def carve():
    """The knight itself: coverage, region ownership, flat tone, final tone."""
    cov, dist, normal = {}, {}, {}
    for y in range(SIZE):
        for x in range(SIZE):
            a = coverage(x, y)
            if a <= 0.0:
                continue
            p = (x + 0.5, y + 0.5)
            cov[(x, y)] = a
            d = sdf(p)
            dist[(x, y)] = d
            # outward normal from the gradient of the signed distance field
            gx = sdf((p[0] + 0.6, p[1])) - sdf((p[0] - 0.6, p[1]))
            gy = sdf((p[0], p[1] + 0.6)) - sdf((p[0], p[1] - 0.6))
            normal[(x, y)] = norm((-gx, -gy))

    owner, flat, final = {}, {}, {}
    for (x, y), a in cov.items():
        p = (x + 0.5, y + 0.5)
        d = max(0.0, dist[(x, y)])
        n = normal[(x, y)]

        md, ms = path_dist(p, MANE)
        is_mane = md < 3.0
        if p[1] >= 25.4:
            region = "base"
        elif is_mane:
            region = "mane"
        elif p[1] < 5.6 and 8.6 < p[0] < 15.2:
            region = "ear"
        elif p[1] < 9.6 or (p[0] < 8.2 and p[1] < 14.4):
            region = "head"
        else:
            region = "neck"
        owner[(x, y)] = region

        # --- form. The core goes darker than the edges; the board bounces a
        # cool fill onto whatever faces front-left.
        core = 1.0 - 0.30 * min(d, 5.0) / 5.0
        bounce = max(0.0, n[0] * BOUNCE_DIR[0] + n[1] * BOUNCE_DIR[1]) ** 1.3
        c = scale(EBONY, core * grain(x, y))
        # the bounce has to die fast with depth: spread over the whole front it
        # stops being ebony and becomes granite.
        c = add(c, BOUNCE, bounce * math.exp(-d / 1.7))
        if region == "base":
            c = scale(c, 0.86 + 0.10 * math.cos((p[1] - 26.0) * 1.9))
        flat[(x, y)] = c

        # --- shaping cuts, all value, no hue.
        if region == "mane":
            groove = (ms % 2.7) < 1.15               # the notches
            c = scale(c, 0.62 if groove else 1.18)
            if 1.15 <= (ms % 2.7) < 1.6:             # the lit lip below each notch
                c = add(c, RIM, 0.10)
            if md > 2.35:                            # where the mane meets the neck
                c = scale(c, 0.74)
        if region in ("head", "neck"):
            jd, _ = path_dist(p, [JAW[0], JAW[1]])
            if jd < 0.95:
                c = scale(c, 0.70)                   # the cheek break
        if region == "head":
            if math.hypot(p[0] - EYE[0], p[1] - EYE[1]) < 1.15:
                c = scale(c, 0.36)
            if math.hypot(p[0] - EYE[0] - 0.4, p[1] - EYE[1] - 0.3) < 0.6:
                c = add(c, RIM, 0.50)                # the drilled eye catches the lamp
            if math.hypot(p[0] - NOSTRIL[0], p[1] - NOSTRIL[1]) < 0.9:
                c = scale(c, 0.55)
            mdst, _ = path_dist(p, [MOUTH[0], MOUTH[1]])
            if mdst < 0.75:
                c = scale(c, 0.66)

        # --- the rim, taken from the halo just outside the silhouette.
        out = (p[0] + n[0] * 2.2, p[1] + n[1] * 2.2)
        edge = math.exp(-max(0.0, d - 0.15) / 0.95)
        bias = 0.45 + 0.55 * max(0.0, n[0] * 0.45 + n[1] * -0.89)
        c = add(c, RIM, min(0.95, glow_at(out) * 1.55) * edge * bias)
        # and a cold counter-rim off the board on the front contour, so the
        # muzzle and the breast never meet the dark left of the room at value.
        front = max(0.0, n[0] * BOUNCE_DIR[0] + n[1] * BOUNCE_DIR[1]) ** 1.6
        c = add(c, BOUNCE_RIM, front * edge * 0.32)
        final[(x, y)] = c
    return cov, owner, flat, final


def compose():
    bg, board = room()
    cov, owner, flat, final = carve()

    # The halo: the lamp spills around the silhouette, so the room is hottest
    # immediately outside the wood. Applied to the background itself, which
    # means it goes down with the room wash and the carving reveals it again.
    for k in bg:
        if cov.get(k, 0.0) >= 0.999:
            continue
        p = (k[0] + 0.5, k[1] + 0.5)
        d = poly_dist(p)
        if d < 3.4:
            bloom = math.exp(-d / 1.5) * glow_at(p) * 0.55 * (1.0 - cov.get(k, 0.0))
            bg[k] = add(bg[k], RIM, bloom)

    def over(sub, back, a):
        return tuple(sub[i] * a + back[i] * (1 - a) for i in range(3))

    flat_px, final_px = dict(bg), dict(bg)
    for k, a in cov.items():
        flat_px[k] = over(flat[k], bg[k], a)
        final_px[k] = over(final[k], bg[k], a)

    # dust hanging in the beam — the very last strokes
    motes = [(27, 10), (29, 15), (24, 4), (30, 21)]
    motes = [m for m in motes if m not in cov]
    for m in motes:
        final_px[m] = add(final_px[m], (255, 214, 150), 0.22)
    return bg, board, cov, owner, flat_px, final_px, motes


# ------------------------------------------------------------------ order ---
def build_strokes():
    bg, board, cov, owner, flat_px, final_px, motes = compose()
    steps = []

    def push(px, src):
        for p in px:
            steps.append((p[0], p[1], src[p]))

    def serp(p):
        return (p[1], p[0] if p[1] % 2 == 0 else -p[0])

    # 1. the room, washed in
    room_px = sorted([p for p in bg if p not in board], key=serp)
    push(room_px, bg)

    # 2. the board, laid far row to near row
    push(sorted(board, key=lambda p: (p[1], abs(p[0] - 16))), bg)

    # 3. the billet: a block of ebony dropped over the whole panel, top down
    x0, y0, x1, y1 = BILLET
    block = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
    block.sort(key=serp)
    for (x, y) in block:
        steps.append((x, y, scale(EBONY, 0.92 * grain(x, y, 0.09))))

    # 4. the cut: waste chipped away, farthest chip first, closing on the surface
    waste = [p for p in block if cov.get(p, 0.0) < 0.999]
    waste.sort(key=lambda p: -(poly_dist((p[0] + 0.5, p[1] + 0.5))
                               + 0.6 * ((p[0] * 7 + p[1] * 13) % 5) / 5.0))
    push(waste, flat_px)

    # 5. shaping, in the order a carver would work: neck down, then jaw and
    #    muzzle, the ears, and the mane notched crest to withers
    push(sorted([p for p in owner if owner[p] == "neck"], key=lambda p: (p[1], p[0])), flat_px)
    push(sorted([p for p in owner if owner[p] == "base"], key=lambda p: (p[1], p[0])), flat_px)
    push(sorted([p for p in owner if owner[p] == "head"],
                key=lambda p: (-p[0], p[1])), flat_px)
    push(sorted([p for p in owner if owner[p] == "ear"], key=lambda p: (p[1], p[0])), flat_px)
    push(sorted([p for p in owner if owner[p] == "mane"],
                key=lambda p: path_dist((p[0] + 0.5, p[1] + 0.5), MANE)[1]), flat_px)

    # 6. the detail pass: notches, cheek, eye, nostril, mouth, and the rim
    #    sweeping the contour from the muzzle up over the ears and down the mane
    detail = [p for p in cov if final_px[p] != flat_px[p]]
    detail.sort(key=lambda p: math.atan2(p[1] - 15.0, p[0] - 15.0))
    push(detail, final_px)

    # 7. dust in the beam
    push(motes, final_px)
    return steps, final_px, owner


def render_preview(final_px, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for (x, y), c in final_px.items():
        px[x, y] = tuple(max(0, min(255, round(v))) for v in c)
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    steps, final_px, owner = build_strokes()
    counts = {}
    for r in owner.values():
        counts[r] = counts.get(r, 0) + 1
    print("regions:", counts, "subject px:", len(owner))
    print(f"{len(steps)} strokes")

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(final_px, "art/gambit.png")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.013
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay,
               "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued at {delay}s")
