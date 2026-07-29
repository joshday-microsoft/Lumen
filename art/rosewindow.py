"""A cathedral rose window, glowing on a dark stone wall — a still.

Nothing in the ledger yet is architectural or symmetric: this one is pure geometry,
the light coming from BEHIND the piece instead of falling on it. One big radial
window fills the whole panel: stone corners, black leading, two rings of jewel
glass (cobalt/ruby outside, amber/emerald inside) and a gold boss burning at the
centre. Big subject, minimal scene.

Designed as a still (art/rosewindow.png). It ships to the wall through /paint
rather than /image because this unit's image-upload path renders blank (see the
lumen skill) — the strokes are ordered stone -> leading -> glass outward -> boss,
so the assembly still reads like a window being glazed.

Run (perform):  .venv\\Scripts\\python.exe art\\rosewindow.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\rosewindow.py preview  -> art\\rosewindow.png
"""

import json
import math
import sys
import urllib.request

SIZE = 32
CX = CY = 15.5

# concentric structure, in pixels of radius
R_FRAME_OUT = 15.4       # outside this -> dark corner stone
R_FRAME_IN = 13.5        # stone frame ring
R_LEAD_OUT = 12.7        # black leading ring under the frame
R_GLASS_OUT_IN = 8.6     # outer ring of glass: R_GLASS_OUT_IN .. R_LEAD_OUT
R_LEAD_MID = 8.0         # leading ring between the two glass rings
R_GLASS_IN_IN = 3.6      # inner ring of glass: R_GLASS_IN_IN .. R_LEAD_MID
R_LEAD_BOSS = 3.0        # leading ring around the centre boss

SECTORS = 8
OUTER_OFFSET = 0.0                      # sector boundaries, in turns
INNER_OFFSET = 0.5 / SECTORS            # inner petals straddle the outer joints

LEAD = (16, 14, 20)
STONE = (112, 105, 114)      # carved frame — pale limestone
STONE_DARK = (30, 28, 35)    # the wall it is set into

COBALT = (38, 76, 196)
RUBY = (186, 30, 54)
AMBER = (230, 156, 42)
EMERALD = (26, 142, 96)
GOLD = (250, 206, 96)
CORE = (255, 246, 214)

OUTER_GLASS = [COBALT, RUBY] * (SECTORS // 2)
INNER_GLASS = [AMBER, EMERALD] * (SECTORS // 2)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def scale(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def mottle(x, y):
    """Deterministic hand-blown-glass unevenness, +/- 7%."""
    h = (x * 73856093) ^ (y * 19349663)
    return 0.93 + ((h >> 5) % 15) / 100.0


def polar(x, y):
    dx, dy = x - CX, y - CY
    return math.hypot(dx, dy), (math.atan2(dy, dx) / (2 * math.pi)) % 1.0


def sector_lead(r, turn, offset):
    """True on the radial mullions: constant ~0.6px wide however far out we are."""
    step = 1.0 / SECTORS
    rel = (turn - offset) % step
    d = min(rel, step - rel) * 2 * math.pi * r
    return d < 0.62


def sector_index(turn, offset):
    return int(((turn - offset) % 1.0) * SECTORS)


def pixel(x, y):
    r, turn = polar(x, y)

    # dark stone wall in the corners, vignetting away from the window
    if r >= R_FRAME_OUT:
        t = min(1.0, (r - R_FRAME_OUT) / 5.0)
        return scale(lerp(STONE_DARK, (16, 15, 20), t), mottle(x, y))

    # carved stone frame, lit from the upper left and warmed by the glass behind it
    if r >= R_FRAME_IN:
        light = 1.0 + 0.34 * math.cos((turn - 0.625) * 2 * math.pi)
        return lerp(scale(STONE, light * 0.92 * mottle(x, y)), (150, 118, 78), 0.18)

    if r >= R_LEAD_OUT:
        return LEAD

    # glow: the window is backlit, brightest at the heart
    glow = 1.28 - 0.32 * (r / R_LEAD_OUT)

    if r >= R_GLASS_OUT_IN:
        if sector_lead(r, turn, OUTER_OFFSET):
            return LEAD
        base = OUTER_GLASS[sector_index(turn, OUTER_OFFSET)]
        return scale(base, glow * mottle(x, y))

    if r >= R_LEAD_MID:
        return LEAD

    if r >= R_GLASS_IN_IN:
        if sector_lead(r, turn, INNER_OFFSET):
            return LEAD
        base = INNER_GLASS[sector_index(turn, INNER_OFFSET)]
        return scale(base, glow * mottle(x, y))

    if r >= R_LEAD_BOSS:
        return LEAD

    # the boss: gold burning out to near-white at the very centre
    return lerp(CORE, GOLD, min(1.0, r / R_LEAD_BOSS))


def build_strokes():
    """Order is the glazing: stone, then leading, then glass outward, boss last."""
    grid = {(x, y): pixel(x, y) for y in range(SIZE) for x in range(SIZE)}
    steps = []

    def take(keep, key=None):
        px = [p for p in grid if keep(*p)]
        px.sort(key=key or (lambda p: (p[1], p[0])))
        for p in px:
            steps.append((p[0], p[1], grid[p]))

    def rad(p):
        return polar(p[0], p[1])[0]

    # 1. the wall and its carved frame — serpentine wash, outside in
    take(lambda x, y: polar(x, y)[0] >= R_FRAME_IN,
         key=lambda p: (-rad(p), p[0] if int(rad(p)) % 2 else -p[0]))

    # 2. the leadwork skeleton — every black line at once, so the tracery
    #    stands empty for a beat before any colour arrives
    take(lambda x, y: polar(x, y)[0] < R_FRAME_IN and grid[(x, y)] == LEAD,
         key=lambda p: -rad(p))

    # 3. glass, glazed outward ring by ring
    take(lambda x, y: R_GLASS_OUT_IN <= polar(x, y)[0] < R_LEAD_OUT
         and grid[(x, y)] != LEAD,
         key=lambda p: (polar(p[0], p[1])[1], -rad(p)))
    take(lambda x, y: R_GLASS_IN_IN <= polar(x, y)[0] < R_LEAD_MID
         and grid[(x, y)] != LEAD,
         key=lambda p: (polar(p[0], p[1])[1], -rad(p)))

    # 4. the boss lit last, centre outward
    take(lambda x, y: polar(x, y)[0] < R_LEAD_BOSS, key=rad)

    return steps


def render_preview(steps, path):
    from PIL import Image
    img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    px = img.load()
    for x, y, c in steps:
        if 0 <= x < SIZE and 0 <= y < SIZE:
            px[x, y] = tuple(c)
    img.save(path)
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save(path.replace(".png", "-big.png"))
    print(f"wrote {path} ({len(steps)} px)")


if __name__ == "__main__":
    steps = build_strokes()
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_preview(steps, "art/rosewindow.png")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.012
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": delay, "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode())
    print(f"{len(steps)} strokes queued")
