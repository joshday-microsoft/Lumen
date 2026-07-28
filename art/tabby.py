"""Tabby — one big cat face filling the panel, alive and a little smug.

An original loop for the Lumen wall. The head is the whole composition: orange
tabby fur, a forehead M, green almond eyes with slit pupils. The show is in the
small stuff — a blink, the pupils darting left then right like it heard
something, one ear flicking — then back to a dead-level stare. Playful /
mischievous.

Run:  .venv\\Scripts\\python.exe art\\tabby.py   -> tabby.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 24

BG = (10, 34, 44)          # deep teal — complement to the orange fur
FUR = (226, 138, 54)
FUR_D = (168, 90, 32)      # stripes + rim shadow
FUR_L = (248, 184, 108)    # top-left light
CREAM = (250, 226, 196)    # muzzle, chin
PINK = (238, 126, 146)
EYE = (132, 210, 88)
EYE_D = (64, 132, 52)
PUPIL = (22, 18, 16)
WHITE = (255, 255, 255)
WHISK = (142, 172, 184)    # muted, or they read as a horizon line

HCX, HCY = 16.0, 19.6      # head centre
HRX, HRY = 12.6, 11.3


def put(img, x, y, c):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((int(x), int(y)), c)


def line(img, x0, y0, x1, y1, c):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        put(img, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def ellipse(img, cx, cy, rx, ry, c):
    for y in range(SIZE):
        for x in range(SIZE):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                put(img, x, y, c)


def triangle(img, p0, p1, p2, c):
    xs = [p[0] for p in (p0, p1, p2)]
    ys = [p[1] for p in (p0, p1, p2)]
    d = ((p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1]))
    if abs(d) < 1e-9:
        return
    for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
        for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
            a = ((p1[1] - p2[1]) * (x - p2[0]) + (p2[0] - p1[0]) * (y - p2[1])) / d
            b = ((p2[1] - p0[1]) * (x - p2[0]) + (p0[0] - p2[0]) * (y - p2[1])) / d
            g = 1 - a - b
            if a >= -0.04 and b >= -0.04 and g >= -0.04:
                put(img, x, y, c)


def shrink(p, centroid, k):
    return (p[0] + (centroid[0] - p[0]) * k, p[1] + (centroid[1] - p[1]) * k)


def ear(img, apex, base_a, base_b):
    """One ear: fur triangle with a smaller pink triangle inside."""
    triangle(img, apex, base_a, base_b, FUR)
    cen = ((apex[0] + base_a[0] + base_b[0]) / 3.0,
           (apex[1] + base_a[1] + base_b[1]) / 3.0)
    triangle(img,
             shrink(apex, cen, 0.34),
             shrink(base_a, cen, 0.44),
             shrink(base_b, cen, 0.44),
             PINK)


def head_base(ear_tilt):
    """Everything that isn't the eyes, drawn fresh (ears depend on the twitch)."""
    img = Image.new("RGB", (SIZE, SIZE), BG)

    # ears — the left one flicks outward on the twitch beat
    t = ear_tilt
    ear(img, (6 - 2.0 * t, 1 + 0.8 * t), (2.5, 12.0), (12.5, 8.0))
    ear(img, (26, 1), (19.5, 8.0), (29.5, 12.0))

    # head
    ellipse(img, HCX, HCY, HRX, HRY, FUR)

    # one clean crescent of shadow down the lower-right rim: the head minus a
    # copy of itself nudged up-left (a smooth band, no speckle -> cheap to pack)
    for y in range(SIZE):
        for x in range(SIZE):
            if ((x - HCX) / HRX) ** 2 + ((y - HCY) / HRY) ** 2 > 1.0:
                continue
            if ((x - HCX + 1.6) / HRX) ** 2 + ((y - HCY + 1.6) / HRY) ** 2 > 1.0:
                put(img, x, y, FUR_D)

    # forehead M — the tabby's signature
    for x, y0, y1 in ((13, 9, 12), (16, 8, 13), (19, 9, 12)):
        for y in range(y0, y1 + 1):
            put(img, x, y, FUR_D)
    put(img, 14, 12, FUR_D)
    put(img, 18, 12, FUR_D)

    # cheek stripes, low and outboard so they don't crowd the eyes
    line(img, 4, 20, 7, 21, FUR_D)
    line(img, 4, 23, 7, 24, FUR_D)
    line(img, 28, 20, 25, 21, FUR_D)
    line(img, 28, 23, 25, 24, FUR_D)

    # muzzle: two cream lobes + chin
    ellipse(img, 12.8, 24.4, 4.3, 3.2, CREAM)
    ellipse(img, 19.2, 24.4, 4.3, 3.2, CREAM)
    ellipse(img, 16.0, 27.2, 3.2, 2.2, CREAM)

    # nose + mouth
    triangle(img, (16, 23.4), (13.8, 21.2), (18.2, 21.2), PINK)
    put(img, 16, 22, (255, 170, 186))
    line(img, 16, 24, 16, 25, FUR_D)
    line(img, 16, 25, 14, 26, FUR_D)
    line(img, 16, 25, 18, 26, FUR_D)

    # whiskers — only the part that clears the head, so the fur stays unbroken
    whisk = Image.new("RGB", (SIZE, SIZE), BG)
    line(whisk, 8, 23, 1, 21, WHISK)
    line(whisk, 8, 26, 1, 29, WHISK)
    line(whisk, 24, 23, 30, 21, WHISK)
    line(whisk, 24, 26, 30, 29, WHISK)
    for y in range(SIZE):
        for x in range(SIZE):
            if whisk.getpixel((x, y)) == WHISK and \
               ((x - HCX) / HRX) ** 2 + ((y - HCY) / HRY) ** 2 > 1.0:
                put(img, x, y, WHISK)
    return img


def eye(img, cx, cy, pupil_dx, lid):
    """Almond eye. lid: 0 wide open .. 1 shut."""
    rx, ry = 4.2, 3.1
    edge = -ry + lid * (2 * ry + 1.0)      # lid sweeps down from the top
    for dy in range(-4, 5):
        for dx in range(-5, 6):
            if (dx / rx) ** 2 + (dy / ry) ** 2 > 1.0:
                continue
            x, y = cx + dx, cy + dy
            if dy < edge:                   # covered by the eyelid
                put(img, x, y, FUR_D if dy > edge - 1.2 else FUR)
                continue
            n = (dx / rx) ** 2 + (dy / ry) ** 2
            put(img, x, y, EYE_D if n > 0.62 else EYE)
    if lid < 0.75:
        # slit pupil
        for dy in range(-3, 4):
            for dx in (-1, 0):
                px, py = dx + pupil_dx, dy
                if (px / rx) ** 2 + (py / ry) ** 2 > 1.0:
                    continue
                if abs(py) > 2.4:
                    continue
                if cy + py < cy + edge:
                    continue
                put(img, cx + px, cy + py, PUPIL)
        if lid < 0.3:
            put(img, cx - 3, cy - 1, WHITE)     # catchlight
    if lid > 0.85:
        line(img, cx - 4, cy, cx + 4, cy, FUR_D)   # closed-eye crease


def beats(f):
    """(pupil_dx, lid, ear_tilt) for frame f — one loop of cat business."""
    lid = 0.0
    if f in (6, 8):
        lid = 0.5
    elif f == 7:
        lid = 1.0
    elif f == 22:
        lid = 0.45          # lazy half-blink on the way out

    dx = 0
    if f in (14, 15, 16):
        dx = -2
    elif f in (13, 17):
        dx = -1
    elif f in (19, 20):
        dx = 2
    elif f == 18 or f == 21:
        dx = 1

    tilt = 0.0
    if f in (10, 12):
        tilt = 0.5
    elif f == 11:
        tilt = 1.0
    return dx, lid, tilt


def frame(f):
    dx, lid, tilt = beats(f)
    img = head_base(tilt)
    eye(img, 10, 17, dx, lid)
    eye(img, 22, 17, dx, lid)
    return img


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    import gifsafe
    # 64 is not about color count (the piece uses ~10) — gifsafe's LZW runs at a
    # constant code width, so a bigger palette buys a bigger dictionary and
    # packs these flat fur runs tighter. Measured: 16->9622, 32->8351,
    # 64->7946, 128->8145, 256->8613 bytes.
    size = gifsafe.save(frames, HERE / "tabby.gif", duration_ms=150, colors=64)
    ok = "OK" if size <= 8192 else "TOO BIG!"
    print(f"tabby.gif: {len(frames)} frames, {size} bytes ({ok})")

    frames[0].save(HERE / "tabby.png")

    keys = (0, 7, 11, 15, 20, 22)
    strip = Image.new("RGB", (SIZE * 5 * len(keys) + (len(keys) - 1) * 4, SIZE * 5), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 5, SIZE * 5), Image.NEAREST),
                    (i * (SIZE * 5 + 4), 0))
    strip.save(HERE / "tabby.strip.png")
    print("wrote tabby.gif + tabby.png + tabby.strip.png")
