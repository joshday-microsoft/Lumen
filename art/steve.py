"""Blocky miner guy (Steve-style) waving — 10-frame loop for the 32x32 wall.

Run:  .venv\\Scripts\\python.exe art\\steve.py   → steve.gif (+ previews)
"""

import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 10

SKY = (111, 159, 232)
SUN = (255, 215, 94)
CLOUD = (238, 242, 248)
GRASS = (92, 191, 63)
DIRT = (111, 74, 44)
DIRT_DK = (88, 57, 31)

HAIR = (58, 42, 28)
SKIN = (185, 138, 103)
SKIN_DK = (138, 98, 72)
MOUTH = (111, 74, 51)
EYE_W = (244, 244, 244)
EYE_P = (53, 49, 143)
SHIRT = (10, 163, 163)
PANTS = (52, 52, 160)
PANTS_DK = (38, 38, 122)
SHOE = (90, 90, 90)


def rect(img, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= x < SIZE and 0 <= y < SIZE:
                img.putpixel((x, y), c)


def scene(f):
    img = Image.new("RGB", (SIZE, SIZE), SKY)
    rect(img, 2, 2, 5, 5, SUN)
    # clouds drift left 1px per frame, wrapping over a 40px track
    for cx0, cy in ((8, 4), (24, 8)):
        cx = (cx0 - f) % 40 - 4
        rect(img, cx, cy, cx + 5, cy + 1, CLOUD)
    # ground: grass lip + speckled dirt
    rect(img, 0, 27, 31, 27, GRASS)
    rect(img, 0, 28, 31, 31, DIRT)
    rng = random.Random(9)
    for _ in range(18):
        img.putpixel((rng.randrange(SIZE), rng.randrange(28, SIZE)), DIRT_DK)
    return img


def steve(img, f, blink=False):
    # left arm, always down (sleeve + skin)
    rect(img, 9, 10, 11, 11, SHIRT)
    rect(img, 9, 12, 11, 19, SKIN)

    # right arm: wave cycle
    if f == 0 or f == FRAMES - 1:  # down
        rect(img, 20, 10, 22, 11, SHIRT)
        rect(img, 20, 12, 22, 19, SKIN)
    elif f in (1, FRAMES - 2):  # mid raise, diagonal
        rect(img, 20, 9, 22, 10, SHIRT)
        for i, (dx, dy) in enumerate(((1, -2), (2, -4), (3, -6))):
            rect(img, 20 + dx, 9 + dy, 22 + dx, 10 + dy, SKIN)
    else:  # up beside head, hand tilting
        rect(img, 20, 9, 22, 10, SHIRT)
        rect(img, 20, 5, 22, 8, SKIN)
        tilt = {2: 0, 3: 1, 4: -1, 5: 1, 6: -1, 7: 0}.get(f, 0)
        rect(img, 20 + tilt, 3, 22 + tilt, 4, SKIN)

    # body
    rect(img, 12, 10, 19, 16, SHIRT)
    rect(img, 12, 17, 19, 24, PANTS)
    rect(img, 15, 17, 15, 26, PANTS_DK)  # leg seam
    rect(img, 12, 25, 19, 26, SHOE)
    img.putpixel((15, 25), (60, 60, 60))
    img.putpixel((15, 26), (60, 60, 60))

    # head
    rect(img, 12, 2, 19, 9, SKIN)
    rect(img, 12, 2, 19, 3, HAIR)
    img.putpixel((12, 4), HAIR)
    img.putpixel((19, 4), HAIR)
    if blink:
        rect(img, 13, 6, 14, 6, SKIN_DK)
        rect(img, 17, 6, 18, 6, SKIN_DK)
    else:
        img.putpixel((13, 6), EYE_W)
        img.putpixel((14, 6), EYE_P)
        img.putpixel((17, 6), EYE_P)
        img.putpixel((18, 6), EYE_W)
    rect(img, 15, 7, 16, 7, SKIN_DK)  # nose
    rect(img, 14, 8, 17, 8, MOUTH)


if __name__ == "__main__":
    frames = []
    for f in range(FRAMES):
        img = scene(f)
        steve(img, f, blink=(f == 6))
        frames.append(img)

    frames[0].save(HERE / "steve.gif", save_all=True, append_images=frames[1:], duration=140, loop=0)
    frames[0].resize((SIZE * 8, SIZE * 8), Image.NEAREST).save(HERE / "steve.gif.preview.png")

    # 4-frame strip (down, up, tilt right, blink+tilt left) for review
    keys = (0, 2, 3, 6)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "steve.strip.png")
    print("wrote steve.gif")
