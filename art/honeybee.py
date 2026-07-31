"""One big honeybee standing on the comb, painted LIVE stroke by stroke.

Big subject, minimal scene: the whole panel is honeycomb, and a single fat bee
sits on top of it. The stroke ORDER is the show —

  1. a wax wash over the whole panel (gessoing the board),
  2. the comb BUILDS outward from the middle, one hexagonal cell at a time,
     each cell filling from its own centre out (some full of honey, some capped
     with pale wax, some empty and dark),
  3. the bee is blocked in as a flat dark silhouette from its middle outward,
  4. then it gets painted: abdomen band by band top-to-bottom, fuzzy thorax
     dabbed in, head, eyes, antennae, legs, pollen baskets,
  5. and LAST the four wings unfurl from their roots outward — translucent, so
     the comb reads straight through them (each wing pixel is blended with
     whatever was already painted underneath).

The hexagons are not drawn: the comb is a Voronoi diagram of a triangular
lattice of cell centres, which *is* a hexagonal tiling. Wall pixels are the ones
whose two nearest centres are nearly tied.

Run (perform):  .venv\\Scripts\\python.exe art\\honeybee.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\honeybee.py preview  -> art\\honeybee.png
"""

import json
import math
import random
import sys
import urllib.request

SIZE = 32
CX = 15.5                      # the bee's axis of symmetry

# ---------------------------------------------------------------- palette ---
WALL_TOP = (236, 200, 130)     # lit wax septa
WALL_BOT = (206, 166, 96)
CELL_KINDS = (
    ((198, 132, 28), (108, 64, 14)),    # bright honey  (centre, rim)
    ((162, 100, 22), (86, 50, 12)),     # deep honey
    ((186, 148, 78), (120, 88, 40)),    # capped wax
    ((60, 36, 14), (96, 60, 22)),       # empty cell (dark in the middle)
)
CELL_WEIGHTS = (0, 1, 3, 0, 2, 1, 3, 0)  # honey-heavy mix

BEE_DARK = (26, 22, 20)
STRIPE_GOLD = ((168, 110, 20), (255, 224, 122))   # shadow .. highlight
STRIPE_BLACK = ((10, 9, 9), (74, 62, 52))
FUZZ = ((150, 100, 44), (214, 158, 72), (242, 198, 124))
WING_TINT = (204, 226, 246)    # cool, so it separates from all that amber

# body masses (cx, cy, rx, ry)
HEAD = (CX, 6.6, 4.3, 3.3)
THORAX = (CX, 12.8, 5.6, 4.6)
ABDOMEN = (CX, 22.0, 6.3, 7.4)

# abdomen banding, by row
GOLD_ROWS = {16, 17, 20, 21, 24, 25}

# wings: (cx, cy, ux, uy, a, b) — ux,uy is the unit long axis, pointing outward
WINGS = (
    (6.4, 8.4, -0.93, -0.37, 7.8, 2.6),    # left forewing
    (8.8, 16.8, -0.93, 0.37, 5.0, 2.0),    # left hindwing
)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def ell(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0


def in_body(x, y):
    return ell(x, y, *HEAD) or ell(x, y, *THORAX) or ell(x, y, *ABDOMEN)


def row_half(y, mass):
    """Half-width of an ellipse mass at row y (0 if the row misses it)."""
    _, cy, rx, ry = mass
    t = 1.0 - ((y - cy) / ry) ** 2
    return rx * math.sqrt(t) if t > 0 else 0.0


# ------------------------------------------------------------------ comb ---
HEX_R = 4.6                    # circumradius; sqrt(3)*R across, 1.5*R per row


def comb_centres():
    pts = []
    for j in range(-1, 7):
        cy = -3.0 + j * 1.5 * HEX_R
        for i in range(-1, 6):
            cx = -3.0 + i * math.sqrt(3) * HEX_R + (math.sqrt(3) * HEX_R / 2 if j % 2 else 0.0)
            pts.append((cx, cy))
    return pts


def _line(x0, y0, x1, y1, out):
    """Bresenham — the hex walls are drawn, not derived, so they stay 1px."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        if 0 <= x0 < SIZE and 0 <= y0 < SIZE:
            out.add((x0, y0))
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def comb_map():
    """A real hexagonal tiling: every cell's six edges rasterised as 1px walls,
    interiors assigned to the nearest centre and depth-shaded from the wall in."""
    pts = comb_centres()
    walls = set()
    for cx, cy in pts:
        verts = [(cx + HEX_R * math.cos(math.radians(a)), cy + HEX_R * math.sin(math.radians(a)))
                 for a in range(90, 450, 60)]
        for i in range(6):
            x0, y0 = verts[i]
            x1, y1 = verts[(i + 1) % 6]
            _line(round(x0), round(y0), round(x1), round(y1), walls)

    cells = {}
    for y in range(SIZE):
        for x in range(SIZE):
            if (x, y) in walls:
                continue
            k = min(range(len(pts)), key=lambda k: (x - pts[k][0]) ** 2 + (y - pts[k][1]) ** 2)
            d = min(abs(x - wx) + abs(y - wy) for wx, wy in walls)
            cells.setdefault(k, []).append((x, y, min(1.0, (d - 1) / 2.5)))
    return pts, cells, walls


# --------------------------------------------------------------- strokes ---
def build_strokes():
    steps = []
    fb = {}

    def put(x, y, c):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            c = tuple(int(v) for v in c)
            fb[(x, y)] = c
            steps.append((x, y, c))

    # 1. wax wash over the whole board, serpentine
    for y in range(SIZE):
        wall = lerp(WALL_TOP, WALL_BOT, y / (SIZE - 1))
        for x in (range(SIZE) if y % 2 == 0 else range(SIZE - 1, -1, -1)):
            put(x, y, wall)

    # 2. the comb builds outward from the middle, cell by cell
    pts, cells, _ = comb_map()
    order = sorted(cells, key=lambda k: math.hypot(pts[k][0] - CX, pts[k][1] - 15.5))
    for k in order:
        centre, rim = CELL_KINDS[CELL_WEIGHTS[(k * 7 + 3) % len(CELL_WEIGHTS)]]
        for x, y, depth in sorted(cells[k], key=lambda p: -p[2]):
            lit = 1.0 - 0.10 * ((x + y) / 62.0)          # faint upper-left light
            put(x, y, lerp(rim, centre, (0.5 + 0.5 * depth) * lit))

    # 3. block the bee in flat, from its middle outward
    body = [(x, y) for y in range(SIZE) for x in range(SIZE) if in_body(x, y)]
    body.sort(key=lambda p: math.hypot(p[0] - CX, (p[1] - 15.0) * 0.8))
    for x, y in body:
        put(x, y, BEE_DARK)

    # 4a. abdomen — band by band, top to bottom, each band swept side to side
    for y in range(15, SIZE):
        half = row_half(y, ABDOMEN)
        if half <= 0:
            continue
        shadow, hi = STRIPE_GOLD if y in GOLD_ROWS else STRIPE_BLACK
        xs = [x for x in range(SIZE) if abs(x - CX) <= half and in_body(x, y)]
        if y % 2:
            xs.reverse()
        for x in xs:
            edge = abs(x - CX) / max(half, 0.6)
            lit = 1.0 - 0.62 * edge ** 1.4 + (0.16 if x < CX else -0.06)
            put(x, y, lerp(shadow, hi, lit))

    # 4b. thorax — fuzzy, dabbed on in random order
    rng = random.Random(1907)
    fur = [(x, y) for y in range(7, 19) for x in range(SIZE)
           if ell(x, y, *THORAX) and not ell(x, y, *HEAD)]
    rng.shuffle(fur)
    for x, y in fur:
        lit = 1.0 - 0.5 * (abs(x - CX) / 5.6) - 0.35 * max(0.0, (y - 12.8) / 4.6)
        base = lerp(FUZZ[0], FUZZ[1], lit + 0.15)
        put(x, y, base)
    for x, y in rng.sample(fur, len(fur) // 4):          # bright fuzz flecks
        if x < CX + 1 and y < 14:
            put(x, y, FUZZ[2])
    for x, y in rng.sample(fur, len(fur) // 5):          # dark fuzz flecks
        put(x, y, FUZZ[0])
    for x in range(SIZE):                                # collar shadow
        if abs(x - CX) <= row_half(16, THORAX) and in_body(x, 16):
            pass
    for x in range(SIZE):
        h = row_half(15, THORAX)
        if h > 0 and abs(x - CX) <= h and not ell(x, 15, *ABDOMEN):
            put(x, 15, (58, 38, 20))

    # 4c. head, eyes, antennae
    for y in range(2, 11):
        for x in range(SIZE):
            if ell(x, y, *HEAD):
                put(x, y, lerp((16, 14, 13), (56, 48, 42), 1.0 - abs(x - CX) / 4.3))
    for ex in (12.2, 18.8):
        for y in range(SIZE):
            for x in range(SIZE):
                if ell(x, y, ex, 6.6, 2.0, 2.5) and ell(x, y, *HEAD):
                    put(x, y, lerp((62, 44, 32), (138, 104, 74), 1.0 - (y - 4.2) / 5.0))
    put(11, 5, (198, 168, 132))                          # eye glints
    put(19, 5, (176, 146, 114))
    for x, y in ((14, 9), (17, 9)):                      # face plate
        put(x, y, (128, 96, 56))
    for x, y in ((14, 3), (13, 2), (12, 1), (11, 1)):    # antennae
        put(x, y, (34, 29, 26))
        put(31 - x, y, (34, 29, 26))

    # 4d. legs, and a loaded pollen basket on each hind leg
    legs = (((10, 11), (8, 10), (6, 10)),
            ((10, 15), (8, 16), (6, 17)),
            ((11, 18), (9, 20), (7, 22)))
    for leg in legs:
        for x, y in leg:
            put(x, y, (24, 20, 18))
            put(31 - x, y, (24, 20, 18))
    for (x, y), c in (((7, 23), (240, 162, 38)), ((6, 23), (255, 202, 76)), ((7, 24), (214, 132, 26))):
        put(x, y, c)
        put(31 - x, y, c)

    # 5. the wings unfurl last — translucent over everything already painted
    for cx, cy, ux, uy, a, b in WINGS:
        for mirror in (False, True):
            wx, wux = (31 - cx, -ux) if mirror else (cx, ux)
            root = (wx - wux * a * 0.95, cy - uy * a * 0.95)
            px = []
            for y in range(SIZE):
                for x in range(SIZE):
                    dx, dy = x - wx, y - cy
                    u = dx * wux + dy * uy
                    v = -dx * uy + dy * wux
                    q = (u / a) ** 2 + (v / b) ** 2
                    if q <= 1.0 and not in_body(x, y):
                        px.append((x, y, q, v))
            px.sort(key=lambda p: math.hypot(p[0] - root[0], p[1] - root[1]))
            for x, y, q, v in px:
                # the shape has to read as an OUTLINE — a filled wing at this
                # size is just a pale blob sitting on the comb
                alpha = 0.34
                if q > 0.82:                       # membrane rim catches light
                    alpha = 0.72
                elif abs(v) < 0.5 or abs(abs(v) - 1.3) < 0.35:   # veins
                    alpha = 0.50
                under = fb.get((x, y), (0, 0, 0))
                put(x, y, lerp(under, WING_TINT, alpha))

    # 6. a little pollen dust in the air
    for x, y in ((2, 29), (29, 28), (30, 22), (1, 25), (26, 2)):
        put(x, y, (252, 218, 118))

    return steps, fb


def render_preview(fb, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for (x, y), c in fb.items():
        px[x, y] = c
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"wrote {path}")


if __name__ == "__main__":
    steps, fb = build_strokes()
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(fb, "art/honeybee.png")
        print(f"{len(steps)} strokes")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay, "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued")
