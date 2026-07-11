"""Frame-count boundary probe for the panel decoder.

Each frame shows its own number + a progress bar, so a frozen panel
displays exactly where the decoder died. Generates frametest-<N>.gif
for every N given on the command line.

Run:  .venv\\Scripts\\python.exe art\\frametest.py 23 22 21 20 19 18 17
"""

import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from server.font3x5 import GLYPH_W, glyph  # noqa: E402
import gifsafe  # noqa: E402

SIZE = 32


def draw_text(img, text, y, color, scale=1):
    w = len(text) * (GLYPH_W * scale + scale) - scale
    x = (SIZE - w) // 2
    for ch in text:
        g = glyph(ch)
        for gy, row in enumerate(g):
            for gx, cell in enumerate(row):
                if cell == "#":
                    for dx in range(scale):
                        for dy in range(scale):
                            px, py = x + gx * scale + dx, y + gy * scale + dy
                            if 0 <= px < SIZE and 0 <= py < SIZE:
                                img.putpixel((px, py), color)
        x += GLYPH_W * scale + scale


def build(n):
    frames = []
    for f in range(n):
        img = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
        draw_text(img, f"OF {n}", 3, (110, 110, 130), 1)
        draw_text(img, str(f + 1), 11, (255, 255, 255), 2)
        fill = round(f / (n - 1) * 31)
        for x in range(fill + 1):
            img.putpixel((x, 28), (30, 160, 60))
            img.putpixel((x, 29), (30, 160, 60))
        img.putpixel((fill, 28), (120, 255, 150))
        img.putpixel((fill, 29), (120, 255, 150))
        frames.append(img)
    return frames


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        n = int(arg)
        frames = build(n)
        size = gifsafe.save(frames, HERE / f"frametest-{n}.gif", duration_ms=300, colors=32)
        ok = "single block" if size <= 4080 else "MULTI-BLOCK — invalidates the test!"
        print(f"frametest-{n}.gif: {n} frames, {size} bytes ({ok})")
