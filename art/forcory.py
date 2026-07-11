"""For Cory — live-painted dedication: a heart fills up like liquid,
then his name signs it in gold, sparkles last.

Run:  .venv\\Scripts\\python.exe art\\forcory.py
"""

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from server.font3x5 import GLYPH_W, glyph  # noqa: E402

SIZE = 32

HEART = [
    ".##...##.",
    "####.####",
    "#########",
    "#########",
    ".#######.",
    "..#####..",
    "...###...",
    "....#....",
]


def hx(c):
    return "#{:02x}{:02x}{:02x}".format(*c)


def build():
    steps = []

    # the heart, scale 2, centered: fills bottom-up like it's being poured
    ox, oy = 7, 13
    rows = []
    for r, row in enumerate(HEART):
        for c, cell in enumerate(row):
            if cell == "#":
                rows.append((r, c))
    for r, c in sorted(rows, key=lambda rc: (-rc[0], rc[1])):   # bottom row first
        for dy in (1, 0):
            for dx in (0, 1):
                steps.append((ox + c * 2 + dx, oy + r * 2 + dy, (229, 72, 77)))

    # highlights on the left lobe
    for x, y in ((9, 14), (10, 14), (9, 15), (12, 16), (10, 16)):
        steps.append((x, y, (255, 128, 132)))

    # "CORY" in gold, letter by letter, above the heart
    text = "CORY"
    w = len(text) * (GLYPH_W * 2 + 2) - 2
    x0 = (SIZE - w) // 2
    for ch in text:
        g = glyph(ch)
        for gy, row in enumerate(g):
            for gx, cell in enumerate(row):
                if cell == "#":
                    for dx in range(2):
                        for dy in range(2):
                            steps.append((x0 + gx * 2 + dx, 2 + gy * 2 + dy, (255, 205, 80)))
        x0 += GLYPH_W * 2 + 2

    # sparkles
    for x, y in ((4, 16), (27, 15), (3, 25), (28, 24), (15, 30), (5, 4), (26, 5)):
        steps.append((x, y, (240, 245, 255)))

    return steps


if __name__ == "__main__":
    steps = build()
    payload = {"pixels": [[x, y, hx(c)] for x, y, c in steps], "delay": 0.02, "clear": True}
    req = urllib.request.Request(
        "http://127.0.0.1:7788/paint",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode())
