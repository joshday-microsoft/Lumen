"""One big origami crane, standing on a dark table — a still.

Nothing in the ledger is folded paper. This piece is the opposite of the last
few: no motion, no glow, no creature anatomy — just flat facets, hard creases
and value. A single sheet's worth of shapes fills the whole panel: keel body,
neck rising to a bent head and a sharp beak, a tail blade swept up-right, the
far wing behind and the near wing in front.

Everything is drawn as polygons with ONE fold line each. The fold splits the
polygon into a lit facet and a shaded facet, and the fold itself is scored a
shade darker. That is the entire lighting model — at 32px, paper reads as
paper because adjacent facets of one object have different values, not because
of gradients.

Designed as a still (art/crane.png). It ships to the wall through /paint
rather than /image because this unit's image-upload path renders blank (see the
lumen skill). The stroke order is the folding: ground first, then body, neck,
head, beak, tail, far wing, and the near wing spreading last — then a final
pass that scores every crease and catches every lit edge.

Run (perform):  .venv\\Scripts\\python.exe art\\crane.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\crane.py preview  -> art\\crane.png
"""

import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                      # supersampling per axis, for clean diagonal folds

# ---------------------------------------------------------------- palette ---
PAPER_HI = (250, 246, 236)      # near wing, neck front, head — full light
PAPER_MID = (203, 202, 200)     # body front, tail top
PAPER_LO = (143, 148, 164)      # turned-away facets, cool
PAPER_DEEP = (92, 99, 124)      # keel underside
# the far wing sits a whole step further back than everything else, so that it
# never competes with the tail blade crossing the same corner of the panel
FAR_HI = (112, 119, 142)
FAR_LO = (72, 78, 100)

BG_TOP = (11, 13, 24)
BG_LOW = (23, 26, 44)
# the wall stays cool and the table runs warm, so white paper sits between the
# two temperatures and reads whiter than either
TABLE = (58, 52, 62)
TABLE_FAR = (25, 22, 31)
SHADOW = (11, 9, 14)

TABLE_Y = 26.8                  # horizon; the keel tip stands just in front of it

# ------------------------------------------------------------- geometry ----
# body kite
BT, BL, BR, BB = (16.0, 13.6), (10.3, 17.6), (21.6, 17.2), (16.6, 28.4)
BODY = [BL, BT, BR, BB]
KEEL = [(13.6, 23.0), (19.2, 22.4), BB]

NECK = [(12.9, 17.4), (8.5, 5.9), (11.2, 5.0), (16.2, 16.4)]
HEAD = [(8.2, 6.4), (11.3, 5.2), (10.5, 2.3), (7.3, 3.5)]
BEAK = [(7.6, 3.9), (2.3, 5.5), (7.9, 6.4)]

TAIL = [(18.6, 15.4), (28.6, 6.6), (29.4, 9.2), (20.6, 17.6)]
WINGR = [(18.6, 16.4), (30.6, 14.4), (29.4, 18.0), (19.6, 22.0)]
WINGL = [(14.2, 15.6), (1.2, 11.6), (2.6, 15.4), (11.6, 23.4)]

# the near wing's own edges, used for the contact shadow it drops on the body
WL_ROOT = ((11.6, 23.4), (14.2, 15.6))
WL_TRAIL = ((2.6, 15.4), (11.6, 23.4))

# painter's order, bottom first: the body hides the roots of neck/tail/far wing,
# the near wing lies over the body, head and beak cap the neck.
PARTS = [
    dict(name="tail", poly=TAIL, fold=((19.4, 16.2), (29.0, 8.0)),
         lit_at=(24.0, 10.0), lit=PAPER_MID, shade=PAPER_LO,
         lights=[((18.6, 15.4), (28.6, 6.6), 0.30, 0.55)]),
    dict(name="wingR", poly=WINGR, fold=((19.5, 17.6), (29.8, 15.9)),
         lit_at=(25.0, 15.2), lit=FAR_HI, shade=FAR_LO,
         lights=[((18.6, 16.4), (30.6, 14.4), 0.34, 0.55)]),
    dict(name="neck", poly=NECK, fold=((14.5, 17.0), (9.85, 5.45)),
         lit_at=(10.5, 10.0), lit=PAPER_HI, shade=PAPER_LO,
         lights=[((12.9, 17.4), (8.5, 5.9), 0.16, 0.45)]),
    dict(name="body", poly=BODY, fold=(BT, BB),
         lit_at=(13.5, 19.0), lit=PAPER_MID, shade=PAPER_LO,
         lights=[(BL, BT, 0.26, 0.5)]),
    # the keel carries the body's centre fold straight down, and is scored
    # again across the top where the underside folds up into the hull
    dict(name="keel", poly=KEEL, fold=(BT, BB),
         lit_at=(14.6, 25.0), lit=PAPER_DEEP, shade=(68, 74, 96),
         creases=[(BT, BB), ((13.6, 23.0), (19.2, 22.4))], lights=[]),
    dict(name="wingL", poly=WINGL, fold=((13.5, 18.5), (2.0, 13.5)),
         lit_at=(6.0, 12.8), lit=PAPER_HI, shade=PAPER_MID,
         lights=[((14.2, 15.6), (1.2, 11.6), 0.34, 0.55)]),
    dict(name="head", poly=HEAD, fold=((7.4, 4.6), (10.9, 3.4)),
         lit_at=(9.0, 3.0), lit=PAPER_HI, shade=PAPER_MID, lights=[]),
    dict(name="beak", poly=BEAK, fold=((7.8, 5.0), (2.3, 5.4)),
         lit_at=(6.0, 4.3), lit=PAPER_HI, shade=PAPER_LO,
         lights=[((7.7, 3.8), (2.3, 5.4), 0.30, 0.45)]),
]

CREASE_W = 0.42                 # half-width of a scored fold, in pixels
CREASE_F = 0.74                 # how much a crease darkens its facet


# --------------------------------------------------------------- helpers ---
def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale(c, f):
    return tuple(max(0.0, min(255.0, v * f)) for v in c)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def inside(pt, poly):
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


def cross(pt, seg):
    (x0, y0), (x1, y1) = seg
    return (x1 - x0) * (pt[1] - y0) - (y1 - y0) * (pt[0] - x0)


def seg_dist(pt, seg):
    (x0, y0), (x1, y1) = seg
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((pt[0] - x0) * dx + (pt[1] - y0) * dy) / L2))
    return math.hypot(pt[0] - (x0 + t * dx), pt[1] - (y0 + t * dy))


def mottle(x, y):
    """Deterministic paper tooth, +/- 3.5% — keeps the flats off plastic."""
    h = (int(x * 512) * 73856093) ^ (int(y * 512) * 19349663)
    return 0.965 + ((h >> 7) % 8) / 100.0


# fold sides are resolved against a reference point on the lit facet, so the
# sign convention never has to be reasoned about per part
for p in PARTS:
    p["lit_sign"] = 1.0 if (p["fold"] is None or cross(p["lit_at"], p["fold"]) >= 0) else -1.0
    p.setdefault("creases", [p["fold"]] if p["fold"] else [])


# ---------------------------------------------------------------- shading ---
def background(x, y):
    if y >= TABLE_Y:
        # the table catches the light where it meets the wall and falls away
        # toward the viewer, so the crane's shadow has something to sit in
        t = min(1.0, (y - TABLE_Y) / 5.0)
        c = lerp(TABLE, TABLE_FAR, t ** 0.8)
        d = math.hypot((x - 16.3) / 9.0, (y - 28.9) / 2.3)
        if d < 1.0:
            c = lerp(SHADOW, c, min(1.0, d * d))
        return c
    return lerp(BG_TOP, BG_LOW, max(0.0, min(1.0, y / TABLE_Y)) ** 1.4)


def part_at(pt):
    for p in reversed(PARTS):
        if inside(pt, p["poly"]):
            return p
    return None


def sample(x, y, scored):
    """Colour of one subpixel. `scored` toggles creases + lit edges."""
    p = part_at((x, y))
    if p is None:
        return background(x, y)

    if p["fold"] is None or cross((x, y), p["fold"]) * p["lit_sign"] >= 0:
        c = p["lit"]
    else:
        c = p["shade"]
    c = scale(c, mottle(x, y))

    # the near wing drops a contact shadow on whatever it overlaps
    if p["name"] != "wingL":
        d = min(seg_dist((x, y), WL_ROOT), seg_dist((x, y), WL_TRAIL))
        if d < 1.9 and inside((x, y), [(14.2, 15.6), (1.2, 11.6), (2.6, 15.4),
                                       (11.6, 23.4), (16.0, 24.5)]) is False:
            if x < 17.0 and 14.0 < y < 26.0:
                c = scale(c, 0.66 + 0.34 * (d / 1.9))

    if not scored:
        return c

    if any(seg_dist((x, y), s) < CREASE_W for s in p["creases"]):
        c = scale(c, CREASE_F)
    for a, b, strength, w in p["lights"]:
        if seg_dist((x, y), (a, b)) < w:
            c = lerp(c, (255, 253, 246), strength)
    return c


def render(scored):
    grid = {}
    off = [(k + 0.5) / SS - 0.5 for k in range(SS)]
    for y in range(SIZE):
        for x in range(SIZE):
            acc = [0.0, 0.0, 0.0]
            for dy in off:
                for dx in off:
                    c = sample(x + dx, y + dy, scored)
                    for i in range(3):
                        acc[i] += c[i]
            n = SS * SS
            grid[(x, y)] = tuple(v / n for v in acc)
    return grid


def region_map():
    """Which part owns each pixel, by its centre — drives the reveal order."""
    return {(x, y): (part_at((x + 0.5, y + 0.5)) or {}).get("name", "bg")
            for y in range(SIZE) for x in range(SIZE)}


# ----------------------------------------------------------------- strokes --
def build_strokes():
    flat = render(False)
    final = render(True)
    owner = region_map()
    steps = []

    def take(names, key):
        px = [p for p in owner if owner[p] in names]
        px.sort(key=key)
        for p in px:
            steps.append((p[0], p[1], flat[p]))

    def serp(p):
        return (p[1], p[0] if p[1] % 2 == 0 else -p[0])

    # 1. the room, then the table it stands on
    take({"bg"}, lambda p: serp(p) if p[1] < TABLE_Y else (99, 0))
    take({"bg"}, lambda p: (0, 0) if p[1] < TABLE_Y else serp(p))

    # 2. the fold, part by part, each one root -> tip
    take({"body"}, lambda p: (p[1], -abs(p[0] - 16)))
    take({"keel"}, lambda p: (p[1], p[0]))
    take({"neck"}, lambda p: (-p[1], p[0]))
    take({"head"}, lambda p: (-p[1], p[0]))
    take({"beak"}, lambda p: (-p[0], p[1]))
    take({"tail"}, lambda p: (p[0] - p[1], p[1]))
    take({"wingR"}, lambda p: (p[0], p[1]))
    take({"wingL"}, lambda p: (-p[0], p[1]))

    # 3. score every crease and catch every lit edge, outward from the body
    detail = [p for p in owner if final[p] != flat[p]]
    detail.sort(key=lambda p: math.hypot(p[0] - 16, p[1] - 19))
    for p in detail:
        steps.append((p[0], p[1], final[p]))

    return steps, final


# ----------------------------------------------------------------- output ---
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
    steps, final = build_strokes()
    print(f"{len(steps)} strokes")

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(final, "art/crane.png")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.018
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay, "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued at {delay}s")
