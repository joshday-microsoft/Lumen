"""Eclipse — the day goes out, and something else comes on.

An original loop for the Lumen wall. One big sun filling the panel, a low ridge
of land along the bottom, and the moon crossing on a slight downward slant.
First sky event in the ledger, and the first piece whose SUBJECT IS THE LIGHT
ITSELF: the sun's surface never dims (a crescent photosphere is exactly as
bright as a full one), so everything that happens here happens to the sky, the
ground, and the observer.

Three ideas hold it together.

1. THE MOON IS NEVER PAINTED. It has no colour of its own in this piece; it
   exists only as a subtraction — the sun is drawn where `d_sun <= R_sun AND
   d_moon > R_moon`. That is not a shortcut, it is what makes the loop close:
   the two states where the moon is clear of the disc render identically no
   matter which side it has already left, so frame 16 IS frame 0 with nothing
   to tune. (The disc only earns ink in totality, where it is blacked out
   against the corona — gated on coverage, which is 0 at both clear states, so
   the gate can never show a seam.)

2. COVERAGE DRIVES EVERYTHING. One number per frame — the exact circle/circle
   lens area over the sun's area — sets the sky colour, the ground, the sun's
   aureole, when stars come out, when the horizon lights up, and when the
   corona is allowed to exist. No per-frame art direction anywhere.

3. THE TIMING IS A LIE, DELIBERATELY. A real totality is about one percent of
   the eclipse; here it is three frames of sixteen. The moon's offsets are a
   hand-authored symmetric table rather than a linear or eased sweep, because
   the show lives inside the last two pixels of approach: 2.4px out is the
   diamond ring, 0.9px is second contact with the chromosphere still showing,
   0.0 is deep totality. Everything wider than 5px is just travel.

16 frames at 130ms. Run:
    .venv\\Scripts\\python.exe art\\eclipse.py     -> eclipse.gif (+ strip, hero)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
SS = 3
DURATION_MS = 130

# ---------------------------------------------------------------- geometry ---
CX, CY = 16.0, 13.6                     # sun centre, high enough to clear the ridge
# The discs are sized by what TOTALITY needs, not by what the partials want.
# A moon that fills 26 of 32 pixels is faithful and useless: it leaves the
# corona a two-pixel rind, and the money frame reads as a hole punched in the
# panel. Backing both radii off by a pixel doubles the corona's room and costs
# the crescents nothing anyone can see.
RS = 8.8                                # sun radius
RM = 10.0                               # moon radius (bigger: this is a TOTAL eclipse)
TILT = math.radians(11.0)               # the moon crosses on a slant, not a wipe
DIRX, DIRY = math.cos(TILT), math.sin(TILT)

# offset of the moon centre along its track, per frame. Symmetric, hand-authored:
# the interesting range is |x| < 6, so that is where the frames are spent.
OFFSETS = [-19.8, -16.2, -12.8, -9.6, -6.6, -4.2, -2.4, -0.9,
             0.0,   0.9,   2.4,  4.2,  6.6,  9.6, 12.8, 16.2]
WRAP = 19.8                             # moon clear on the far side == clear on the near side
FRAMES = len(OFFSETS)
TOTAL_FRAMES = (7, 8, 9)                # fully covered
RING_FRAMES = (6, 10)                   # diamond ring

# ----------------------------------------------------------------- palette ---
SKY_DAY = (70, 132, 202)
SKY_NIGHT = (9, 11, 30)
GROUND_DAY = (52, 60, 44)
GROUND_NIGHT = (5, 6, 12)
SUN_CORE = (255, 250, 226)
SUN_MID = (255, 214, 116)
SUN_LIMB = (252, 170, 60)
SUN_EDGE = (240, 126, 44)
AUREOLE = (255, 206, 130)
CORONA = (224, 234, 255)
CHROMO = (255, 88, 136)                 # chromosphere / prominences: pink, and rare
HORIZON = (208, 104, 52)                # the 360-degree sunset that only totality has
STAR = (208, 222, 255)
VENUS = (255, 244, 214)

# stars sit in the corners, out of the corona's way; (x, y, magnitude)
STARS = [(3.5, 3.5, 0.75), (28.5, 2.5, 0.62), (26.5, 7.5, 0.45),
         (2.5, 9.5, 0.50), (30.5, 12.5, 0.40), (5.5, 21.5, 0.44),
         (27.5, 20.5, 0.52), (1.5, 16.5, 0.36)]
VENUS_AT = (24.5, 4.5)


def ridge(x):
    """Low land silhouette across the bottom rows."""
    return 27.9 + 1.15 * math.cos(x * 0.30 + 1.1) + 0.65 * math.cos(x * 0.79 + 2.4)


def coverage(off):
    """Fraction of the sun's DISC AREA hidden by the moon. Exact lens area."""
    d = abs(off)
    if d >= RS + RM:
        return 0.0
    if d <= RM - RS:
        return 1.0
    a = (d * d + RS * RS - RM * RM) / (2 * d * RS)
    b = (d * d + RM * RM - RS * RS) / (2 * d * RM)
    a = max(-1.0, min(1.0, a))
    b = max(-1.0, min(1.0, b))
    area = (RS * RS * math.acos(a) + RM * RM * math.acos(b)
            - 0.5 * math.sqrt(max(0.0, (-d + RM + RS) * (d + RM - RS)
                                  * (d - RM + RS) * (d + RM + RS))))
    return area / (math.pi * RS * RS)


def mix(c0, c1, t):
    t = max(0.0, min(1.0, t))
    return (c0[0] + (c1[0] - c0[0]) * t,
            c0[1] + (c1[1] - c0[1]) * t,
            c0[2] + (c1[2] - c0[2]) * t)


def band(v, step):
    """Quantise a smooth field into flat steps.

    Every frame here is a FULL frame, so any smooth gradient is re-encoded
    sixteen times and LZW can fold none of it. Banding the corona and the
    aureole is worth kilobytes; the sky costs nothing either way because it is
    one flat colour per frame.
    """
    return math.floor(v / step) * step


def smooth(v, lo, hi):
    """Hermite ramp from lo to hi. hi < lo is a DESCENDING ramp, on purpose —
    most of the gates here (the ring, the chromosphere) switch off as the moon
    closes in, and (v-lo)/(hi-lo) already handles that. Special-casing the
    inverted range is what broke the first build: it returned 1.0 for every
    value above hi, so the diamond ring was blazing with the moon 25px clear
    of the disc, and the loop-closure assert was the only thing that noticed.
    """
    if hi == lo:
        return 1.0 if v >= hi else 0.0
    t = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


class Frame:
    """Everything that is constant over one frame, computed once."""

    def __init__(self, off):
        self.off = off
        self.f = coverage(off)
        # daylight left. Illumination is linear in uncovered area but the eye
        # is not: the 0.45 keeps a half-eclipsed sky looking like normal day,
        # which is exactly the trap the real thing plays on people.
        self.k = max(0.0, 1.0 - self.f) ** 0.45
        self.sky = mix(SKY_NIGHT, SKY_DAY, self.k)
        self.ground = mix(GROUND_NIGHT, GROUND_DAY, self.k)
        self.mx = CX + off * DIRX
        self.my = CY + off * DIRY
        self.dark = smooth(self.f, 0.90, 1.0)          # moon disc blacks out
        self.tot = smooth(self.f, 0.994, 1.0)          # corona is allowed
        self.night = smooth(self.k, 0.34, 0.12)        # stars / horizon glow
        # the diamond ring: a sliver narrower than ~2.5px reads as a bead, and
        # the bead sits on the sun's limb OPPOSITE the moon's offset
        d = abs(off)
        self.ring = smooth(d, 4.6, 2.6) * smooth(d, 1.5, 2.2)
        s = -1.0 if off > 0 else 1.0
        self.bx = CX + s * DIRX * RS * 0.94
        self.by = CY + s * DIRY * RS * 0.94
        # chromosphere: the pink arc that survives a beat past second contact,
        # on the side where the two limbs are closest to parting
        self.chromo = smooth(d, 0.15, 0.55) * smooth(d, 1.62, 1.15)
        self.cax, self.cay = s * DIRX, s * DIRY


def sun_colour(rr):
    """Limb darkening as four flat bands — at 32px a gradient just reads muddy."""
    if rr < 0.42:
        return SUN_CORE
    if rr < 0.72:
        return SUN_MID
    if rr < 0.90:
        return SUN_LIMB
    return SUN_EDGE


EQUATOR = 0.25                          # the corona's long axis, tilted on the sky


def corona_at(fr, dx, dy, d):
    """A hot rim and a short oval halo. Banded, and only in totality.

    This started as real streamers — eight spokes plus four needle rays — and
    then as angular noise before that. Both die for the same reason, and it is
    a size argument, not a taste one: the moon's limb is 10px from its centre,
    so a ray narrow enough to READ as a ray (0.08 rad) is 0.4px wide out where
    it lives, and supersampling averages it straight back into the field. What
    survives is a shape: a white-hot rim, a halo that fades inside five pixels,
    and pure night beyond it. The only angular structure kept is a slow
    stretch along the solar equator, which is an ellipse — and an ellipse is a
    shape a 32px panel can hold.
    """
    over = d - RM
    theta = math.atan2(dy, dx)
    eq = math.cos(theta - EQUATOR)
    over /= 1.0 + 0.55 * eq * eq                     # slower fade along the equator
    v = math.exp(-over / 1.85)
    if over < 1.3:                                   # white-hot inner corona
        v = max(v, 0.98 - 0.17 * over)
    return band(max(0.0, min(1.0, v)) * fr.tot, 0.15)


def sample(fr, x, y):
    """Colour at one sample point, in layers: sky, stars, land, sun, corona."""
    ds = math.hypot(x - CX, y - CY)
    dmx, dmy = x - fr.mx, y - fr.my
    dm = math.hypot(dmx, dmy)

    r, g, b = fr.sky

    # stars, only once the sky has actually gone
    if fr.night > 0.01:
        for sx, sy, mag in STARS:
            dd = math.hypot(x - sx, y - sy)
            if dd < 1.15:
                a = fr.night * mag * (1.0 - dd / 1.15)
                r += STAR[0] * a
                g += STAR[1] * a
                b += STAR[2] * a
        dd = math.hypot(x - VENUS_AT[0], y - VENUS_AT[1])
        if dd < 1.5:
            a = fr.night * 0.95 * (1.0 - dd / 1.5)
            r += VENUS[0] * a
            g += VENUS[1] * a
            b += VENUS[2] * a

    ry = ridge(x)
    if y < ry:
        # the sun's own aureole, dimming with what is left of it
        if ds > RS:
            a = band((1.0 - fr.f) * math.exp(-(ds - RS) / 3.2) * 0.55, 0.07)
            r += (AUREOLE[0] - r) * a
            g += (AUREOLE[1] - g) * a
            b += (AUREOLE[2] - b) * a
        # totality lights the whole horizon like a sunset in every direction
        if fr.night > 0.01:
            a = band(fr.night * 0.90 * math.exp(-(ry - y) / 2.3), 0.08)
            r += (HORIZON[0] - r) * a
            g += (HORIZON[1] - g) * a
            b += (HORIZON[2] - b) * a
    else:
        # No warm bleed onto the land: the whole point of the horizon band is
        # that a black ridge stands against it. Light the ground too and the
        # silhouette dissolves exactly when it matters most.
        return fr.ground

    # the photosphere: present wherever the moon is not. The moon is never
    # drawn — it is the absence, and that is what makes the loop close.
    if ds <= RS and dm > RM:
        r, g, b = sun_colour(ds / RS)
    elif dm > RM:
        if fr.tot > 0.01:
            v = corona_at(fr, dmx, dmy, dm)
            if v > 0:
                r += (CORONA[0] - r) * min(1.0, v)
                g += (CORONA[1] - g) * min(1.0, v)
                b += (CORONA[2] - b) * min(1.0, v)
        if fr.chromo > 0.01 and dm < RM + 1.4:
            ang = (dmx * fr.cax + dmy * fr.cay) / max(1e-6, dm)
            if ang > 0.42:
                a = fr.chromo * (ang - 0.42) / 0.58 * (1.0 - (dm - RM) / 1.4)
                a = max(0.0, min(1.0, a * 1.35))
                r += (CHROMO[0] - r) * a
                g += (CHROMO[1] - g) * a
                b += (CHROMO[2] - b) * a
        elif fr.tot > 0.5 and dm < RM + 1.0:
            # two prominences, same two every totality frame
            for pa in (2.15, 5.25):
                px, py = fr.mx + math.cos(pa) * (RM + 0.45), fr.my + math.sin(pa) * (RM + 0.45)
                dd = math.hypot(x - px, y - py)
                if dd < 1.0:
                    a = fr.tot * (1.0 - dd) * 0.9
                    r += (CHROMO[0] - r) * a
                    g += (CHROMO[1] - g) * a
                    b += (CHROMO[2] - b) * a
    else:
        # inside the moon: sky during the partials (a bite of sky out of the
        # sun), true black once it is the only thing in front of the corona
        r = r + (5 - r) * fr.dark
        g = g + (5 - g) * fr.dark
        b = b + (10 - b) * fr.dark

    # diamond ring: the last bead of photosphere blooms and throws a cross
    if fr.ring > 0.01:
        bd = math.hypot(x - fr.bx, y - fr.by)
        a = math.exp(-bd / 1.45)
        along = (x - fr.bx) * DIRX + (y - fr.by) * DIRY
        perp = -(x - fr.bx) * DIRY + (y - fr.by) * DIRX
        a += 0.55 * math.exp(-abs(perp) / 3.6) * math.exp(-(along * along) / 0.9)
        a += 0.55 * math.exp(-abs(along) / 3.6) * math.exp(-(perp * perp) / 0.9)
        a = band(min(1.0, a) * fr.ring, 0.10)
        if a > 0:
            r += (255 - r) * a
            g += (252 - g) * a
            b += (232 - b) * a

    return r, g, b


def render(off):
    fr = Frame(off)
    img = Image.new("RGB", (SIZE, SIZE))
    inv = 1.0 / (SS * SS)
    for py in range(SIZE):
        for px in range(SIZE):
            r = g = b = 0.0
            for sy in range(SS):
                y = py + (sy + 0.5) / SS
                for sx in range(SS):
                    x = px + (sx + 0.5) / SS
                    cr, cg, cb = sample(fr, x, y)
                    r += cr
                    g += cg
                    b += cb
            img.putpixel((px, py), (min(255, max(0, int(r * inv + 0.5))),
                                    min(255, max(0, int(g * inv + 0.5))),
                                    min(255, max(0, int(b * inv + 0.5)))))
    return img


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def mean_luma(img):
    px = list(img.getdata())
    return sum(luma(c) for c in px) / len(px)


def main():
    cov = [coverage(o) for o in OFFSETS]
    for t, (o, f) in enumerate(zip(OFFSETS, cov)):
        print(f"  t{t:2d}  offset {o:6.1f}  covered {f * 100:5.1f}%  daylight {(1 - f) ** 0.45 * 100:5.1f}%")
    assert cov[0] == 0.0 and coverage(WRAP) == 0.0, "the moon must start and end clear of the disc"
    for t in TOTAL_FRAMES:
        assert cov[t] == 1.0, f"frame {t} is meant to be total, got {cov[t]:.4f}"
    for t in RING_FRAMES:
        assert 0.90 < cov[t] < 1.0, f"frame {t} needs a sliver left, got {cov[t]:.4f}"
    for t in range(1, 8):
        assert cov[t] > cov[t - 1], "coverage must grow to totality"

    frames = [render(o) for o in OFFSETS]

    # the loop closes because a sun the moon has left looks the same as a sun
    # the moon has not reached yet — assert it rather than trusting it
    wrap = render(WRAP)
    assert list(wrap.getdata()) == list(frames[0].getdata()), "frame 16 != frame 0"

    # "The day goes out" is a claim about the SKY, not about the panel. Whole-
    # panel mean luma fails the piece for succeeding: a bright corona lifts the
    # average right back up, and a corona is not daylight. Measure the far
    # field — everything well outside the discs — which is sky and nothing else.
    def sky_luma(img):
        px = [img.getpixel((x, y)) for y in range(SIZE) for x in range(SIZE)
              if math.hypot(x + 0.5 - CX, y + 0.5 - CY) > RM + 5.0
              and y + 0.5 < ridge(x + 0.5)]
        return sum(luma(c) for c in px) / len(px)

    day, night = sky_luma(frames[0]), sky_luma(frames[8])
    print(f"  panel mean luma: day {mean_luma(frames[0]):6.2f} -> totality {mean_luma(frames[8]):6.2f}")
    print(f"  sky luma:        day {day:6.2f} -> totality {night:6.2f} ({night / day * 100:.1f}%)")
    assert night < day * 0.30, "the day never actually goes out"
    assert sky_luma(frames[4]) > day * 0.55, "a half eclipse should still look like daytime"

    # The corona must EXIST in totality and must not in the partials — but the
    # measure has to be EXCESS OVER THIS FRAME'S OWN SKY, not absolute
    # brightness. A flat daytime sky is luma 121, brighter than any corona
    # pixel at totality, so an absolute threshold reports the noon sky as a
    # blazing corona and the real corona as nothing.
    def excess(img, t, margin=60):
        base = luma(Frame(OFFSETS[t]).sky)
        return sum(1 for y in range(SIZE) for x in range(SIZE)
                   if math.hypot(x + 0.5 - CX, y + 0.5 - CY) > RS + 0.5
                   and y + 0.5 < ridge(x + 0.5)
                   and luma(img.getpixel((x, y))) > base + margin)
    halo = excess(frames[8], 8)
    quiet = excess(frames[3], 3)
    print(f"  corona pixels: totality {halo}, mid-partial {quiet}")
    assert halo > 40, "no corona at totality"
    assert quiet < 12, "the partial sky is glowing like a corona"

    # the bead has to be the brightest thing on its frame, and brighter than
    # anything on the frame after it
    bead = max(luma(c) for c in frames[6].getdata())
    assert bead > 235, f"the diamond ring never lights ({bead:.0f})"
    assert bead > max(luma(c) for c in frames[8].getdata()), "totality outshines the ring"

    keys = list(range(FRAMES))
    strip = Image.new("RGB", (SIZE * 3 * len(keys) + (len(keys) - 1) * 3, SIZE * 3), (18, 18, 22))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 3, SIZE * 3), Image.NEAREST), (i * (SIZE * 3 + 3), 0))
    strip.save(HERE / "eclipse.strip.png")
    hero = frames[8]
    hero.save(HERE / "eclipse.png")
    hero.resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "eclipse-big.png")
    frames[6].resize((SIZE * 10, SIZE * 10), Image.NEAREST).save(HERE / "eclipse-ring.png")

    import gifsafe

    def quant_error(colors):
        montage = Image.new("RGB", (SIZE * len(frames), SIZE))
        for i, f_ in enumerate(frames):
            montage.paste(f_, (i * SIZE, 0))
        pal = montage.quantize(colors=colors, dither=Image.Dither.NONE)
        got = list(montage.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB").getdata())
        want = list(montage.getdata())
        return sum((got[i][c] - want[i][c]) ** 2 for i in range(len(want)) for c in range(3)) / len(want)

    # the corona and the chromosphere are a few dozen pixels on three frames —
    # exactly the profile median cut drops on the floor (hummingbird, 2026-08-07)
    keep = [CORONA, CHROMO, SUN_CORE, SUN_MID, SUN_EDGE, HORIZON, VENUS, SKY_NIGHT]
    best = None
    for colors in (16, 32, 64, 128, 256):
        size = gifsafe.save(frames, HERE / "eclipse.gif", duration_ms=DURATION_MS,
                            colors=colors, keep=keep)
        err = quant_error(colors)
        print(f"  colors={colors:3d} -> {size} bytes, err {err:7.1f}")
        if size <= 8192 and (best is None or err < best[2]):
            best = (colors, size, err)
    assert best, "no palette fits the 8 KB budget"
    size = gifsafe.save(frames, HERE / "eclipse.gif", duration_ms=DURATION_MS,
                        colors=best[0], keep=keep)

    # check the ENCODED pixels, not the rendered ones
    enc = Image.open(HERE / "eclipse.gif")
    enc.seek(8)
    tot = enc.convert("RGB")
    # "Brightest pixel in the ring around the moon" sounds like a corona test
    # and is not: the annulus also contains the orange horizon band (same
    # distance from the sun's centre, below it) and Venus (warm, and by design
    # the brightest point in the sky). Both were reported as a warm corona
    # before the sample was fenced off from them.
    def clear_of_stars(x, y):
        return all(math.hypot(x + 0.5 - sx, y + 0.5 - sy) > 2.0
                   for sx, sy, _ in STARS + [VENUS_AT + (0,)])
    pearl = max((tot.getpixel((x, y)) for x in range(SIZE) for y in range(20)
                 if RM + 0.6 < math.hypot(x + 0.5 - CX, y + 0.5 - CY) < RM + 4.0
                 and clear_of_stars(x, y)),
                key=luma)
    assert luma(pearl) > 95 and pearl[2] >= pearl[0] - 12, f"the encoder ate the corona: {pearl}"
    enc.seek(7)
    arc = enc.convert("RGB")
    pink = max((arc.getpixel((x, y)) for x in range(SIZE) for y in range(SIZE)),
               key=lambda c: c[0] - c[1])
    assert pink[0] - pink[1] > 60 and pink[2] > pink[1], f"the encoder ate the chromosphere: {pink}"
    print(f"eclipse.gif: {FRAMES} frames, {best[0]} colors, {size} bytes (OK)")


if __name__ == "__main__":
    main()
