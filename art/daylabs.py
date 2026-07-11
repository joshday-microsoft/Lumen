"""Day Labs mark — animated reveal for the wall, built from the real asset.

The L draws itself in (brand blue), the D sweeps around it clockwise
(steel navy, brightened for LED legibility), a gleam passes, hold, fade.

Run:  .venv\\Scripts\\python.exe art\\daylabs.py
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
MARK = r"C:\Users\JoshDay\source\repos\daylabs\assets\daylabs-mark.png"
SIZE = 32
FRAMES = 36

CANVAS = (5, 8, 15)          # brand canvas #05080F
D_NAVY = (44, 76, 128)       # D stroke, lifted for LED visibility
L_TOP = (99, 164, 244)       # accent-bright #63A4F4
L_BOT = (46, 123, 232)       # accent #2E7BE8
GLEAM = (235, 242, 252)


def classify_mark():
    """Downscale the 512px mark to 32px via majority vote -> 'D'/'L'/None grid."""
    src = Image.open(MARK).convert("RGBA")
    hi = src.resize((128, 128), Image.LANCZOS)
    grid = [[None] * SIZE for _ in range(SIZE)]
    for gy in range(SIZE):
        for gx in range(SIZE):
            votes = {"bg": 0, "D": 0, "L": 0}
            for sy in range(4):
                for sx in range(4):
                    r, g, b, a = hi.getpixel((gx * 4 + sx, gy * 4 + sy))
                    if a < 128 or (r > 225 and g > 225 and b > 225):
                        votes["bg"] += 1
                    elif b > 110 and b > r + 40 and g > 60:
                        votes["L"] += 1
                    else:
                        votes["D"] += 1
            winner = max(votes, key=votes.get)
            grid[gy][gx] = None if winner == "bg" else winner
    return grid


def build_frames(grid):
    # pixel lists with reveal ordering
    l_px, d_px = [], []
    ys = [y for y in range(SIZE) for x in range(SIZE) if grid[y][x] == "L"]
    l_ymin, l_ymax = (min(ys), max(ys)) if ys else (0, 1)
    for y in range(SIZE):
        for x in range(SIZE):
            kind = grid[y][x]
            if kind == "L":
                t = (y - l_ymin) / max(1, l_ymax - l_ymin)
                l_px.append(((y, x), (x, y), tuple(round(L_TOP[i] + (L_BOT[i] - L_TOP[i]) * t) for i in range(3))))
            elif kind == "D":
                ang = (math.atan2(y - 15.5, x - 15.5) + math.pi / 2) % (2 * math.pi)
                d_px.append((ang, (x, y), D_NAVY))
    l_px.sort(key=lambda p: p[0])       # top-to-bottom, like writing the L
    d_px.sort(key=lambda p: p[0])       # clockwise sweep from 12 o'clock

    def base(l_n, d_n, dimk=1.0, gleam_c=None):
        img = Image.new("RGB", (SIZE, SIZE), tuple(round(c * dimk) for c in CANVAS))
        for _, (x, y), c in l_px[:l_n]:
            img.putpixel((x, y), tuple(round(v * dimk) for v in c))
        for _, (x, y), c in d_px[:d_n]:
            img.putpixel((x, y), tuple(round(v * dimk) for v in c))
        if gleam_c is not None:
            for _, (x, y), c in l_px[:l_n] + d_px[:d_n]:
                if gleam_c <= x + y <= gleam_c + 2:
                    img.putpixel((x, y), GLEAM)
        return img

    nl, nd = len(l_px), len(d_px)
    frames = [base(0, 0)]                                        # f0 dark
    for f in range(1, 8):                                        # f1-7 L writes in
        frames.append(base(round(nl * f / 7), 0))
    for f in range(1, 13):                                       # f8-19 D sweeps
        frames.append(base(nl, round(nd * f / 12)))
    for c in (14, 26, 38):                                       # f20-22 gleam pass
        frames.append(base(nl, nd, gleam_c=c))
    for _ in range(10):                                          # f23-32 hold
        frames.append(base(nl, nd))
    for k in (0.55, 0.22, 0.06):                                 # f33-35 fade out
        frames.append(base(nl, nd, dimk=k))
    return frames


if __name__ == "__main__":
    import gifsafe

    grid = classify_mark()
    frames = build_frames(grid)
    size = gifsafe.save(frames, HERE / "daylabs.gif", duration_ms=130, colors=32)
    print(f"daylabs.gif: {len(frames)} frames, {size} bytes ({'OK' if size <= 8192 else 'TOO BIG'})")
    frames[28].save(HERE / "daylabs-mark-32.png")                # the held mark, as a still
    keys = (4, 13, 21, 28)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "daylabs.strip.png")
