"""Gulp — one big frog on a lily pad, and the firefly that lights it.

An original loop for the Lumen wall. The frog fills the panel from the eyes
down: two bulging gold eyes on top of a broad mottled head, a wide smiling
mouth, a pale throat, both front feet planted on the pad. It never moves from
the spot. The show is a single joke told in eighteen frames:

  * a firefly drifts across the sky and the eyes TRACK it, both pupils and
    both highlights, every frame;
  * the tongue snaps out, takes it, and comes back;
  * and then the frog GLOWS, because it just swallowed the only light in the
    picture;
  * the afterglow fades, another firefly blinks on at the left edge exactly
    where the first one entered, and the whole thing starts again.

The unifying decision: there is ONE light in this scene and it is the firefly.
Every warm pixel on the frog is that light falling on it, so the modelling is
ambient-only (form comes from distance-to-own-edge, never from a fixed key
light) and the entire mood of a frame is set by where the bug happens to be.
When it is taken, the light does not switch off — it rides the tongue home and
keeps burning from INSIDE the throat. The gaze target and the light position
are the same variable, which is why the eyes follow it down into the mouth for
free.

Run:  .venv\\Scripts\\python.exe art\\gulp.py   -> gulp.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
SS = 3                          # supersample factor
FRAMES = 14
DURATION_MS = 120

# ------------------------------------------------------------------ scene ---
# Dusk sky, banded FLAT into three steps: every row is then a single LZW run,
# and the background is re-encoded in all 18 full frames (chameleon lesson).
SKY = ((0, (10, 18, 30)), (7, (13, 24, 37)), (13, (17, 31, 43)))
PAD = (24, 56, 38)
PAD_RIM = (36, 78, 48)

DORSAL = (54, 100, 48)          # top of the head
FLANK = (104, 150, 64)          # lower body
THROAT = (166, 176, 116)        # kept dim on purpose: the bug is the brightest
                                # thing in this picture until it is eaten, and
                                # a near-white resting throat leaves the glow
                                # nowhere to go but 255
BLOTCH = 0.80                   # mottling multiplier
DARK = (18, 28, 22)             # mouth, eye rims, nostrils
IRIS = (216, 168, 52)
IRIS_DEEP = (150, 104, 26)
PUPIL = (10, 12, 14)
SPEC = (248, 250, 228)
TONGUE = (228, 106, 122)
TONGUE_TIP = (246, 152, 162)
FIRE_CORE = (232, 255, 186)
# The same light, two colours, and the difference is the whole point: in AIR a
# firefly is yellow-green, but light that has travelled through a BODY comes
# back warm, because flesh passes red and eats the rest — hold a torch behind
# your hand. So the moment the bug goes down the throat the glow changes hue,
# and the colour shift alone tells you where the light now is.
FIRE_AIR = (150, 255, 110)
FIRE_FLESH = (255, 152, 48)

BODY = (16.0, 27.8, 13.4, 10.6)         # cx, cy, rx, ry — deliberately
                                        # NOT panel-wide: a subject that
                                        # runs off both edges has no
                                        # silhouette left to read
HEAD = (16.0, 20.5, 12.8, 7.6)
EYE_R = 4.7
EYE_L_C = (9.2, 13.8)
EYE_R_C = (22.8, 13.8)
MOUTH_Y = 23.2
MOUTH_ANCHOR = (16.0, 23.9)

# ------------------------------------------------------------- choreography ---
# t 0-6   hunting, one blink   t 9-10   tongue home, bug riding the tip
# t 7     tongue half out      t 11-12  swallow: cheeks out, eyes shut, lit
# t 8     contact              t 13     afterglow, and a new bug blinks on
STRIKE = 8
GONE = (11, 12)                                        # frames with no bug at all
TONGUE_OUT = {7: 0.50, 8: 1.0, 9: 0.55, 10: 0.18}
LID = {3: 0.85, 7: 0.25, 8: 0.25, 9: 0.35, 10: 0.50, 11: 0.80, 12: 1.0, 13: 0.35}
PUFF = {10: 0.35, 11: 1.0, 12: 1.0, 13: 0.50}          # cheeks + throat swell
GLOW_IN = {9: 0.70, 10: 0.85, 11: 0.80, 12: 1.55, 13: 0.42}


def fly_pos(t):
    """Where the firefly is at frame t — one continuous periodic wander.

    Phased so p(STRIKE) lands up and slightly right of the mouth: the tongue
    then passes in FRONT of the inner edge of the right eye, which is where a
    tongue actually goes. Because the path is periodic and the replacement bug
    rides the same curve, frame 17 flows into frame 0 with no jump.
    """
    a = 2.0 * math.pi * t / FRAMES - 0.9204
    b = 4.0 * math.pi * t / FRAMES + 2.858
    return (16.0 + 11.0 * math.sin(a), 5.0 + 2.6 * math.sin(b))


def fly_pulse(t):
    """Fireflies breathe rather than burn — slow, never fully out."""
    return 0.62 + 0.38 * math.sin(2.0 * math.pi * t / FRAMES * 2.0 + 0.6)


def tongue_tip(t):
    e = TONGUE_OUT.get(t, 0.0)
    tx, ty = fly_pos(STRIKE)
    mx, my = MOUTH_ANCHOR
    return (mx + (tx - mx) * e, my + (ty - my) * e)


def lights(t):
    """(x, y, strength, indoors) for every light in frame t.

    indoors=True means the light is inside the frog, which is the whole gag:
    the source is swallowed but the scene stays lit — from the throat.
    """
    if t <= STRIKE:
        return [(*fly_pos(t), fly_pulse(t), False)]
    if t in (9, 10):
        return [(*tongue_tip(t), GLOW_IN[t], False)]
    out = [(16.0, 27.6, GLOW_IN.get(t, 0.0), True)]
    if t == FRAMES - 1:
        out.append((*fly_pos(t), 0.45 * fly_pulse(t), False))
    return out


def gaze(t):
    """The eyes look at the light — including all the way down into the gulp."""
    ls = lights(t)
    lx = sum(l[0] * l[2] for l in ls) / max(1e-6, sum(l[2] for l in ls))
    ly = sum(l[1] * l[2] for l in ls) / max(1e-6, sum(l[2] for l in ls))
    return lx, ly


# ------------------------------------------------------------------- paint ---
def ellv(x, y, e, grow=0.0):
    cx, cy, rx, ry = e
    return ((x - cx) / (rx + grow)) ** 2 + ((y - cy) / (ry + grow)) ** 2


def inside_dist(x, y, e, grow=0.0):
    """Approximate distance from (x,y) in to the ellipse edge (<=0 = outside)."""
    cx, cy, rx, ry = e
    v = math.sqrt(max(0.0, ellv(x, y, e, grow)))
    return (1.0 - v) * min(rx + grow, ry + grow)


def n2(i, j):
    h = (i * 374761393 + j * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def lerp(a, b, u):
    u = max(0.0, min(1.0, u))
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


def mul(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def sky_at(y):
    col = SKY[0][1]
    for top, c in SKY:
        if y >= top:
            col = c
    return col


def shade(x, y, t):
    """Colour of the scene at panel point (x,y), before the light pass.

    Returns (rgb, on_frog) — the flag lets the light diffuse further through
    the frog than it does through air, which is what sells the lit throat.
    """
    puff = PUFF.get(t, 0.0)
    lid = LID.get(t, 0.0)
    gx, gy = gaze(t)

    col = sky_at(y)
    on_frog = False

    # lily pad — a dark disc the frog is sitting on, seen at the bottom corners
    dpad = inside_dist(x, y, (16.0, 33.0, 20.5, 5.6))
    if dpad > 0.0:
        col = PAD_RIM if dpad < 0.9 else PAD

    d_body = inside_dist(x, y, BODY)
    d_head = inside_dist(x, y, HEAD, grow=0.9 * puff)
    de_l = EYE_R - math.hypot(x - EYE_L_C[0], y - EYE_L_C[1])
    de_r = EYE_R - math.hypot(x - EYE_R_C[0], y - EYE_R_C[1])
    d = max(d_body, d_head, de_l, de_r)

    if d <= 0.0:
        return tongue_over(col, x, y, t), on_frog
    on_frog = True

    # --- skin ------------------------------------------------------------
    # form is distance-to-own-edge only: no key light exists in this scene
    # except the bug, so a baked highlight would fight it every frame.
    # every ramp here is BANDED into steps for the same reason the light is:
    # a smooth gradient across a 30x20 body is thousands of near-unique values
    # re-encoded in all 18 frames, and it costs more than the animation does.
    base = lerp(DORSAL, FLANK, int(((y - 12.0) / 12.0) * 4.0) / 4.0)
    if n2(int(x / 3.2), int(y / 2.6)) > 0.68 and y < 24.0:
        base = mul(base, BLOTCH)
    base = mul(base, 0.70 + 0.30 * (int(min(1.0, d / 3.0) * 4.0) / 4.0))

    # throat: pale, and it swells as the bug goes down. Hard-edged — the
    # supersampler gives it its one pixel of softness for free.
    dth = inside_dist(x, y, (16.0, 29.0, 7.6 + 0.9 * puff, 3.8 + 0.7 * puff))
    if dth > 0.0:
        base = lerp(base, THROAT, 0.92 if dth > 0.55 else 0.55)

    # front feet — three toes each, planted on the pad
    for fx in (7.0, 25.0):
        for k in (-1, 0, 1):
            tx = fx + k * 2.2 + (0.5 if fx > 16 else -0.5) * abs(k)
            r = math.hypot(x - tx, y - 30.6)
            if r < 1.15:
                base = mul(FLANK, 0.70)                 # toes have to be a VALUE
            elif r < 1.55:                              # step below the belly or
                base = mul(base, 0.48)                  # they vanish into it

    # mouth: a wide grin, one dark line with a lit lower lip under it. The
    # curvature is NEGATIVE — corners above the centre. Positive reads as a
    # frown, which on a frog is not a subtle wrongness, it is a different
    # animal. Left unclipped in x and cut by the silhouette instead, so the
    # grin runs the full width of the head the way a frog's actually does.
    my = MOUTH_Y - 1.5 * ((x - 16.0) / 13.0) ** 2
    if abs(y - my) < 0.80:
        base = DARK
    elif 0.80 <= y - my < 1.7:
        base = lerp(base, (150, 190, 100), 0.45)

    # nostrils
    for nx in (13.0, 19.0):
        if math.hypot(x - nx, y - 19.5) < 0.75:
            base = mul(DARK, 1.4)

    # --- eyes ------------------------------------------------------------
    for c, de in ((EYE_L_C, de_l), (EYE_R_C, de_r)):
        if de <= 0.0:
            continue
        lid_y = c[1] - EYE_R + lid * 2.0 * EYE_R
        if y < lid_y:                                   # eyelid, closing down
            base = mul(lerp(DORSAL, FLANK, 0.25), 0.90 + 0.10 * min(1.0, de))
            if lid_y - y < 0.7:
                base = mul(base, 0.60)                  # lash line
            continue
        if de < 0.85:
            base = DARK                                 # rim where it meets skin
            continue
        base = lerp(IRIS, IRIS_DEEP, max(0.0, 1.0 - de / 3.4))
        ax, ay = gx - c[0], gy - c[1]
        m = math.hypot(ax, ay) or 1.0
        ax, ay = ax / m, ay / m
        px, py = c[0] + ax * 1.15, c[1] + ay * 1.15
        if ((x - px) / 2.0) ** 2 + ((y - py) / 1.45) ** 2 < 1.0:
            base = PUPIL
        if math.hypot(x - (c[0] + ax * 2.7), y - (c[1] + ay * 2.7)) < 0.85:
            base = SPEC                                 # highlight sits toward the light

    return tongue_over(base, x, y, t), on_frog


def tongue_over(col, x, y, t):
    """The tongue, painted over EVERYTHING — face, sky, whatever it crosses.

    It lives outside the silhouette test on purpose. Drawn inside it (which is
    where it started) the strike is clipped at the frog's own outline: the
    tongue stops dead at the top of the eye, and the bug it is supposedly
    catching sits eight pixels beyond the end of it.
    """
    e = TONGUE_OUT.get(t, 0.0)
    if e <= 0.0:
        return col
    mx, my = MOUTH_ANCHOR
    tx, ty = tongue_tip(t)
    vx, vy = tx - mx, ty - my
    u = max(0.0, min(1.0, ((x - mx) * vx + (y - my) * vy) / (vx * vx + vy * vy)))
    px, py = mx + vx * u, my + vy * u
    if math.hypot(x - px, y - py) < 1.25 - 0.45 * u:
        col = TONGUE if u < 0.82 else TONGUE_TIP
    if math.hypot(x - tx, y - ty) < 1.5:
        col = TONGUE_TIP
    return col


def fly_core(x, y, t):
    """The bug's own body — the one thing in the scene that emits."""
    if t in GONE:
        return None                                     # swallowed
    fx, fy = tongue_tip(t) if t in (9, 10) else fly_pos(t)
    return FIRE_CORE if math.hypot(x - fx, y - fy) < 1.05 else None


GLOW_STEP = 0.22                # the light is BANDED, not smooth — see render()


def render(t):
    """Two passes, deliberately at different resolutions.

    The scene (pass 1) is supersampled, because a frog is all curves and its
    silhouette has to be smooth. The light (pass 2) is computed once per PANEL
    pixel and quantised into steps of GLOW_STEP, because a smooth radial field
    that moves every frame is the single most expensive thing you can put in
    this GIF: it perturbs every pixel of the subject in all 18 full frames, so
    nothing repeats and LZW has nothing to fold. Banded, the lit body collapses
    into a handful of flat regions per frame, and the same bands recur across
    frames. Same picture, 40% of the bytes.
    """
    n = SIZE * SS
    ls = lights(t)

    base = [[0.0, 0.0, 0.0] for _ in range(SIZE * SIZE)]
    skin = [0.0] * (SIZE * SIZE)
    for py in range(n):
        y = (py + 0.5) / SS
        for px in range(n):
            x = (px + 0.5) / SS
            col, on_frog = shade(x, y, t)
            core = fly_core(x, y, t)
            if core is not None:
                col = core
            i = (py // SS) * SIZE + (px // SS)
            base[i][0] += col[0]
            base[i][1] += col[1]
            base[i][2] += col[2]
            skin[i] += 1.0 if on_frog else 0.0

    q = float(SS * SS)
    img = Image.new("RGB", (SIZE, SIZE))
    for py in range(SIZE):
        for px in range(SIZE):
            i = py * SIZE + px
            r, g, b = (c / q for c in base[i])
            x, y = px + 0.5, py + 0.5
            flesh = skin[i] / q > 0.5

            k_air = k_in = 0.0
            for lx, ly, s, indoors in ls:
                if s <= 0.0:
                    continue
                dd = (x - lx) ** 2 + (y - ly) ** 2
                if indoors:
                    # inside the body the light DIFFUSES: wide, soft, quadratic
                    k = s / (1.0 + dd / 49.0)
                    if not flesh:
                        k *= 0.20                        # barely spills into the air
                    k_in += k
                else:
                    # in air it does not: a slow falloff over a dark sky is a
                    # brown stain, not a lamp. Quartic keeps the halo tight
                    # enough to read as a light source at 32px.
                    rad = 6.5 if flesh else 2.1
                    k = s / (1.0 + (dd / (rad * rad)) ** 2)
                    k_air += k
            add = 0.0, 0.0, 0.0
            for ktot, hue, gain in ((k_air, FIRE_AIR, 0.46), (k_in, FIRE_FLESH, 0.42)):
                ktot = int(min(ktot, 1.7) / GLOW_STEP) * GLOW_STEP
                if ktot > 0.0:
                    add = (add[0] + hue[0] * ktot * gain,
                           add[1] + hue[1] * ktot * gain,
                           add[2] + hue[2] * ktot * gain)
            r += add[0]
            g += add[1]
            b += add[2]

            img.putpixel((px, py), (min(255, int(r + 0.5)),
                                    min(255, int(g + 0.5)),
                                    min(255, int(b + 0.5))))
    return img


def main():
    frames = [render(t) for t in range(FRAMES)]

    # --- the piece has to actually do what it claims -----------------------
    tx, ty = tongue_tip(STRIKE)
    bx, by = fly_pos(STRIKE)
    assert math.hypot(tx - bx, ty - by) < 0.01, "the tongue misses the bug"
    assert math.hypot(*(a - b for a, b in zip(fly_pos(FRAMES), fly_pos(0)))) < 0.01, \
        "the path does not close, so 17 -> 0 will jump"

    keys = range(0, FRAMES, 2)
    strip = Image.new("RGB", (SIZE * 4 * len(keys) + (len(keys) - 1) * 4, SIZE * 4), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 4, SIZE * 4), Image.NEAREST), (i * (SIZE * 4 + 4), 0))
    strip.save(HERE / "gulp.strip.png")
    hero = frames[12]
    hero.resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "gulp-big.png")
    hero.save(HERE / "gulp.png")

    # --- the glow has to be an EVENT, not a warm tint ----------------------
    # Measured as brightness above the piece's own resting level, because the
    # throat is pale cream to begin with: a raw amber count says "lit" on
    # every frame and hides the beat entirely.
    def lum(img, box):
        return sum(sum(img.getpixel((x, y))) for x in range(box[0], box[2])
                   for y in range(box[1], box[3]))

    throat = (9, 24, 24, 31)
    lit = [lum(f, throat) for f in frames]
    rest = sorted(lit)[len(lit) // 2]
    for t in range(FRAMES):
        mark = "-" if t in GONE else "o"
        print(f"  t{t:02d} throat {lit[t]:6d}  (+{lit[t] - rest:5d})  bug {mark}")
    assert lit.index(max(lit)) == 12, f"the glow peaks on frame {lit.index(max(lit))}, not 12"
    assert max(lit) > rest * 1.35, "the swallow does not read as a glow"
    assert lit[FRAMES - 1] > rest * 1.05, "the afterglow died too early to sell the gag"

    import gifsafe

    def quant_error(colors):
        montage = Image.new("RGB", (SIZE * len(frames), SIZE))
        for i, f_ in enumerate(frames):
            montage.paste(f_, (i * SIZE, 0))
        pal = montage.quantize(colors=colors, dither=Image.Dither.NONE)
        got = list(montage.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB").getdata())
        want = list(montage.getdata())
        return sum((got[i][c] - want[i][c]) ** 2 for i in range(len(want)) for c in range(3)) / len(want)

    keep = [FIRE_CORE, FIRE_AIR, FIRE_FLESH, TONGUE, TONGUE_TIP, IRIS, SPEC]
    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "gulp.gif", duration_ms=DURATION_MS,
                            colors=colors, keep=keep)
        err = quant_error(colors)
        print(f"  colors={colors:3d} -> {size} bytes, err {err:7.1f}")
        if size <= 8192 and (best is None or err < best[2]):
            best = (colors, size, err)
    assert best, "no palette fits the 8 KB budget"
    size = gifsafe.save(frames, HERE / "gulp.gif", duration_ms=DURATION_MS,
                        colors=best[0], keep=keep)

    # the tongue has to survive the encoder too: it is ~30 pink pixels on two
    # frames out of eighteen, exactly the profile median cut throws away
    enc = Image.open(HERE / "gulp.gif")
    enc.seek(STRIKE)
    px = [enc.convert("RGB").getpixel((x, y)) for x in range(14, 23) for y in range(6, 22)]
    pink = max(px, key=lambda c: c[0] - c[1])
    print(f"  encoded tongue: {pink}")
    # pink, specifically: a 16-colour table maps the tongue to the firefly's
    # own amber, which passes any test that only asks whether it is warm
    assert pink[0] > 180 and pink[0] - pink[1] > 70 and pink[2] > pink[1] + 8,         f"the encoder ate the tongue: {pink}"
    print(f"gulp.gif: {len(frames)} frames, {best[0]} colors, {size} bytes (OK)")


if __name__ == "__main__":
    main()
