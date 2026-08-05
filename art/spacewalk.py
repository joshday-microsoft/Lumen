"""One big astronaut helmet, alone in orbit — painted LIVE on the wall.

Nothing in the ledger is a portrait, and nothing has told its story through a
REFLECTION. The helmet fills the whole panel; the face is unknowable behind the
glass, and the only thing that says where we are is what the visor is showing
back: the limb of a blue planet rising across the bottom-left of the gold glass,
deep space and one hard sun-glint in the top-right.

Light discipline, because at 32px a white sphere on black space is the hard part:
  * the sun is behind-left of the viewer, so the shell is lit from the upper-left
    and its own reflected image lands mirrored in the top-right of the glass —
    which is exactly the empty half of the reflection, opposite the planet mass;
  * the shell's lower-right would otherwise dissolve into the black background,
    so it is caught by a COOL planet-shine rim from below-front, while the
    upper-left edge takes a warm sun rim. The helmet is never allowed to touch
    the background at the same value.

The stroke order is the show, and it is an arrival: space, stars, then the helmet
lands as one dark silhouette before it becomes anything, the shell is shaded
band by band, the glass is cut in as a hole, the planet RISES into the glass
bottom-up, the frame ring sweeps around, the collar clamps on, gold glazes the
glass, the rims light the edges, the life-support LED blinks awake, and the very
last stroke is the sun-glint hitting the visor.

Run (perform):  .venv\\Scripts\\python.exe art\\spacewalk.py [delay_seconds]
Run (preview):  .venv\\Scripts\\python.exe art\\spacewalk.py preview
"""

import json
import math
import sys
import urllib.request

SIZE = 32
SS = 3                              # supersampling per axis — round shapes

# ------------------------------------------------------------------ shapes --
HCX, HCY, R = 16.0, 17.2, 13.2      # helmet sphere
VCX, VCY = 16.0, 15.2               # visor superellipse
VA, VB, VN = 9.7, 7.6, 2.6
FRAME_R = 1.14                      # outer edge of the visor frame, in visor r
RING_Y0, RING_Y1 = 26.9, 30.2       # neck ring band

PCX, PCY, PR = 9.5, 33.0, 15.4      # the planet, reflected in the glass
# the glint has to sit WELL inside the glass: pushed out toward the rim it lands
# in the gold edge glow and against the lit frame, and stops reading as a spark
GLINT = (21.8, 11.6)                # sun's mirrored image on the glass
LED = (25.3, 23.6)                  # life-support light on the shell

SUN = (-0.52, -0.60, 0.61)          # key light, upper-left front
SHINE = (0.10, 0.80, 0.59)          # planet-shine, below front
PSUN = (0.50, -0.60, 0.62)          # sun as it falls on the reflected planet

# ----------------------------------------------------------------- palette --
SPACE_TOP = (5, 6, 14)
SPACE_LOW = (13, 11, 26)
NEBULA = (46, 26, 62)
SIL = (26, 28, 40)

SHELL = (238, 242, 250)
GLASS_TOP = (5, 7, 14)
GLASS_LOW = (10, 14, 26)

OCEAN = (14, 44, 104)
LAND = (58, 116, 62)
DRY = (128, 120, 72)
CLOUD = (238, 246, 252)
HAZE = (120, 200, 255)
ATMO = (60, 130, 220)

FRAME_HI = (236, 238, 244)
FRAME_LO = (104, 110, 128)
RING_MID = (126, 134, 154)
RING_HI = (206, 214, 230)
RING_LO = (46, 52, 68)
GOLD = (255, 200, 110)
GOLD_EDGE = (214, 158, 66)
WARM_RIM = (255, 242, 218)
COOL_RIM = (98, 168, 236)

# stars: (x, y, brightness) — sparse, so the helmet stays the subject
STARS = [(2.5, 3.5, 0.9), (29.5, 6.5, 0.7), (5.5, 27.5, 0.6), (30.5, 20.5, 0.85),
         (1.5, 14.5, 0.5), (27.5, 1.5, 0.6), (13.5, 1.5, 0.45), (31.5, 29.5, 0.55)]
# stars seen INSIDE the reflection, in the dark half of the glass
GSTARS = [(20.2, 12.4, 0.80), (17.4, 9.6, 0.55), (24.8, 16.2, 0.62), (12.6, 10.4, 0.45)]

# stages, in painting order
(SPACE, STARLIGHT, SILHOUETTE, SHELLING, GLASSCUT, REFLECT,
 FRAMING, COLLAR, GLAZE, RIMLIGHT, LIFELIGHT, SUNGLINT) = range(12)


# --------------------------------------------------------------- helpers ----
def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scale(c, f):
    return tuple(max(0.0, min(255.0, v * f)) for v in c)


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in c))


def visor_r(x, y):
    f = (abs(x - VCX) / VA) ** VN + (abs(y - VCY) / VB) ** VN
    return f ** (1.0 / VN)


def ring_half(y):
    return 9.7 - 0.34 * (y - RING_Y0)


def region(x, y):
    """Which piece of the helmet owns this subpixel — collar sits in front."""
    if RING_Y0 <= y <= RING_Y1 and abs(x - HCX) <= ring_half(y):
        return "ring"
    if (x - HCX) ** 2 + (y - HCY) ** 2 <= R * R:
        r = visor_r(x, y)
        if r <= 1.0:
            return "glass"
        if r <= FRAME_R:
            return "frame"
        return "shell"
    return None


def sphere_n(x, y):
    nx, ny = (x - HCX) / R, (y - HCY) / R
    return nx, ny, math.sqrt(max(0.015, 1.0 - nx * nx - ny * ny))


# ---------------------------------------------------------------- painting --
def space(x, y):
    c = lerp(SPACE_TOP, SPACE_LOW, clamp01(y / SIZE) ** 1.3)
    d = math.hypot((x - 29.0) / 13.0, (y - 2.0) / 10.0)       # faint corner nebula
    if d < 1.0:
        c = lerp(c, NEBULA, 0.55 * (1.0 - d) ** 2)
    return c


def starlight(x, y, c):
    for sx, sy, b in STARS:
        d = math.hypot(x - sx, y - sy)
        if d < 1.5:
            a = b * (1.0 - d / 1.5) ** 2
            c = lerp(c, (226, 232, 248), min(1.0, a * 1.4))
    return c


def shell_colour(x, y):
    nx, ny, nz = sphere_n(x, y)
    key = max(0.0, nx * SUN[0] + ny * SUN[1] + nz * SUN[2])
    c = scale(SHELL, 0.20 + 0.88 * key ** 1.05)
    fill = max(0.0, nx * SHINE[0] + ny * SHINE[1] + nz * SHINE[2])
    c = tuple(c[i] + (60, 120, 190)[i] * 0.55 * fill ** 1.4 for i in range(3))
    # the visor is set INTO the shell: contact shadow just outside the frame
    vr = visor_r(x, y)
    if FRAME_R < vr < FRAME_R + 0.16:
        c = scale(c, 0.60 + 0.40 * (vr - FRAME_R) / 0.16)
    return tuple(min(255.0, v) for v in c)


def glass_base(x, y):
    return lerp(GLASS_TOP, GLASS_LOW, clamp01((y - (VCY - VB)) / (2 * VB)))


def surface_noise(x, y):
    return (math.sin(0.55 * x + 0.31 * y)
            + 0.8 * math.sin(0.27 * x - 0.63 * y + 1.7)
            + 0.5 * math.sin(0.90 * x + 0.75 * y + 4.2))


def cloud_noise(x, y):
    return math.sin(0.42 * x - 0.50 * y + 2.2) + 0.7 * math.sin(0.85 * x + 0.33 * y - 1.1)


def reflection(x, y):
    """What the glass is showing: planet limb below-left, deep space above."""
    c = glass_base(x, y)
    for sx, sy, b in GSTARS:                       # stars in the reflection
        d = math.hypot(x - sx, y - sy)
        if d < 1.2:
            c = lerp(c, (200, 214, 240), b * (1.0 - d / 1.2) ** 2)

    pd = math.hypot(x - PCX, y - PCY)
    if pd <= PR:
        nx, ny = (x - PCX) / PR, (y - PCY) / PR
        nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
        d = max(0.0, nx * PSUN[0] + ny * PSUN[1] + nz * PSUN[2])
        lum = 0.20 + 1.05 * d
        n = surface_noise(x, y)
        surf = OCEAN
        if n > 0.55:
            surf = lerp(LAND, DRY, clamp01((n - 0.55) / 1.6))
        elif n > 0.30:
            surf = lerp(OCEAN, LAND, (n - 0.30) / 0.25)
        else:
            surf = lerp(OCEAN, (44, 110, 196), clamp01((n + 1.4) / 1.7))
        c = scale(surf, lum)
        ca = clamp01((cloud_noise(x, y) - 0.45) / 0.9) * 0.8 * (0.25 + 0.85 * d)
        c = lerp(c, scale(CLOUD, min(1.0, 0.35 + lum)), ca)
        t = (pd - (PR - 1.6)) / 1.6                # atmosphere thickening at the limb
        if t > 0.0:
            c = lerp(c, scale(HAZE, min(1.0, 0.42 + lum)), 0.72 * t ** 1.3)
    elif pd <= PR + 1.9:
        a = (1.0 - (pd - PR) / 1.9) ** 2 * 0.70
        c = lerp(c, ATMO, a)
    return c


def frame_colour(x, y):
    nx, ny, _ = sphere_n(x, y)
    t = clamp01(0.5 - 0.72 * (nx * 0.62 + ny * 0.78))
    c = lerp(FRAME_LO, FRAME_HI, t ** 1.2)
    if visor_r(x, y) < 1.045:                      # inner lip, darker against glass
        c = scale(c, 0.62)
    return c


def ring_colour(x, y):
    t = (y - RING_Y0) / (RING_Y1 - RING_Y0)
    if t < 0.24:
        c = lerp(RING_HI, RING_MID, t / 0.24)
    elif t > 0.74:
        c = lerp(RING_MID, RING_LO, (t - 0.74) / 0.26)
    else:
        c = RING_MID
    c = scale(c, 1.0 - 0.34 * clamp01((x - HCX + 4.0) / 16.0))   # lit from the left
    for lx in (10.4, 16.0, 21.6):                  # latches
        if abs(x - lx) < 1.15 and 0.28 < t < 0.72:
            c = lerp(c, (222, 230, 244), 0.75)
    return c


def glaze(x, y, c):
    """Gold coating: a broad diagonal sheen, and glowing edges of the glass."""
    px, py = x - 7.0, y - 9.0
    d = abs(px * 0.62 - py * 0.78)                 # distance from the sheen line
    c = lerp(c, GOLD, 0.13 * math.exp(-(d / 1.9) ** 2))
    # the coating can only glow at the EDGE of the glass — spread it any wider
    # and the deep-space half of the reflection goes olive and stops being space
    t = clamp01((visor_r(x, y) - 0.74) / 0.26)
    return lerp(c, GOLD_EDGE, 0.30 * t ** 2.6)


def rimlight(x, y, c):
    nx, ny, _ = sphere_n(x, y)
    e = clamp01((math.hypot(nx, ny) - 0.84) / 0.16)
    if e <= 0.0:
        return c
    warm = max(0.0, -(nx * 0.62 + ny * 0.74))
    cool = max(0.0, ny * 0.86 + nx * 0.36)
    c = lerp(c, WARM_RIM, 0.55 * e * warm ** 1.2)
    return lerp(c, COOL_RIM, 0.62 * e * cool ** 1.1)


def sample(x, y, stage):
    c = space(x, y)
    if stage >= STARLIGHT:
        c = starlight(x, y, c)

    reg = region(x, y)
    if reg and stage >= SILHOUETTE:
        c = SIL
    if reg and stage >= SHELLING and reg in ("shell", "frame"):
        c = shell_colour(x, y)
    if reg == "glass" and stage >= GLASSCUT:
        c = glass_base(x, y)
    if reg == "glass" and stage >= REFLECT:
        c = reflection(x, y)
    if reg == "frame" and stage >= FRAMING:
        c = frame_colour(x, y)
    if reg == "ring" and stage >= COLLAR:
        c = ring_colour(x, y)
    if reg == "glass" and stage >= GLAZE:
        c = glaze(x, y, c)
    if reg == "shell" and stage >= RIMLIGHT:
        c = rimlight(x, y, c)

    if stage >= LIFELIGHT and reg == "shell":
        d = math.hypot(x - LED[0], y - LED[1])
        if d < 2.4:
            c = lerp(c, (255, 96, 62), 0.30 * (1.0 - d / 2.4) ** 2)
        if d < 0.95:
            c = lerp(c, (255, 186, 150), 0.85 * (1.0 - d / 0.95) ** 0.5)
    if stage >= SUNGLINT and reg in ("glass", "frame"):
        dx, dy = x - GLINT[0], y - GLINT[1]
        d = math.hypot(dx, dy)
        streak = max(math.exp(-((dx / 3.2) ** 2 + (dy / 0.50) ** 2)),
                     math.exp(-((dx / 0.48) ** 2 + (dy / 2.2) ** 2)))
        a = max(1.0 * math.exp(-(d / 1.55) ** 2), 0.88 * streak)
        if a > 0.01:
            c = lerp(c, (255, 250, 236), min(1.0, a))
    return c


# ----------------------------------------------------------------- raster ---
def render(stage):
    off = [(k + 0.5) / SS - 0.5 for k in range(SS)]
    grid = {}
    for y in range(SIZE):
        for x in range(SIZE):
            acc = [0.0, 0.0, 0.0]
            for dy in off:
                for dx in off:
                    c = sample(x + dx, y + dy, stage)
                    for i in range(3):
                        acc[i] += c[i]
            grid[(x, y)] = tuple(v / (SS * SS) for v in acc)
    return grid


def serp(p):
    return (p[1], p[0] if p[1] % 2 == 0 else -p[0])


def sprinkle(p):
    h = (p[0] * 73856093) ^ (p[1] * 19349663)
    return (h >> 5) % 997


def angle_from(p, cx, cy, start):
    a = math.atan2(p[1] + 0.5 - cy, p[0] + 0.5 - cx) - start
    return a % (2 * math.pi)


ORDER = {
    SPACE:      serp,
    STARLIGHT:  sprinkle,
    SILHOUETTE: lambda p: math.hypot(p[0] + 0.5 - HCX, p[1] + 0.5 - HCY),
    SHELLING:   serp,
    GLASSCUT:   lambda p: math.hypot(p[0] + 0.5 - VCX, p[1] + 0.5 - VCY),
    REFLECT:    lambda p: (-p[1], p[0]),                     # the planet rises
    FRAMING:    lambda p: angle_from(p, VCX, VCY, -math.pi / 2),
    COLLAR:     lambda p: (p[0], p[1]),
    GLAZE:      lambda p: math.hypot(p[0] + 0.5 - 7.0, p[1] + 0.5 - 9.0),
    RIMLIGHT:   lambda p: angle_from(p, HCX, HCY, -2.4),
    LIFELIGHT:  lambda p: math.hypot(p[0] + 0.5 - LED[0], p[1] + 0.5 - LED[1]),
    SUNGLINT:   lambda p: math.hypot(p[0] + 0.5 - GLINT[0], p[1] + 0.5 - GLINT[1]),
}


def build_strokes():
    steps = []
    canvas = {}
    grids = {}
    for stage in range(12):
        g = render(stage)
        grids[stage] = g
        px = [p for p in g
              if p not in canvas or max(abs(g[p][i] - canvas[p][i]) for i in range(3)) > 2.0]
        px.sort(key=ORDER[stage])
        for p in px:
            steps.append((p[0], p[1], g[p]))
            canvas[p] = g[p]
    return steps, grids[11]


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
        render_preview(final, "art/spacewalk.png")
        raise SystemExit

    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.015
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
