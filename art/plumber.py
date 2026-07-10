"""Endless platformer loop, classic style — 24 frames, single 4k block.

Beat sheet: fade in → hero pops out of the left pipe → walks right → bumps
the ?-block (coin!) → mushroom emerges → grabs it, grows → walks to the
right pipe → descends → fade to black → loop (reset to small).

Run:  .venv\\Scripts\\python.exe art\\plumber.py   → plumber.gif (+ strip)
"""

from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32

SKY = (92, 148, 252)
GROUND_L = (228, 132, 60)
GROUND_D = (136, 60, 12)
PIPE_L = (64, 176, 64)
PIPE_D = (20, 116, 20)
BLOCK = (252, 188, 44)
BLOCK_D = (168, 96, 8)
BLOCK_USED = (140, 88, 32)
COIN = (252, 220, 60)
WHITE = (252, 252, 252)
CAP = (216, 40, 20)
SKIN = (252, 188, 148)
BLUE = (32, 64, 200)
SHOE = (88, 40, 8)
MUSH_R = (228, 52, 36)
MUSH_C = (252, 224, 180)
EYE = (24, 24, 24)

GROUND_Y = 28          # first ground row; feet stand on 27
BLOCK_X, BLOCK_Y = 13, 13   # ?-block 5x5 at rest


def put(img, x, y, c):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((x, y), c)


def rect(img, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(img, x, y, c)


def draw_block(img, used=False, bump=0, coin=None, sparkle=False):
    y = BLOCK_Y - bump
    if used:
        rect(img, BLOCK_X, y, BLOCK_X + 4, y + 4, BLOCK_USED)
        put(img, BLOCK_X + 2, y + 2, GROUND_D)
    else:
        rect(img, BLOCK_X, y, BLOCK_X + 4, y + 4, BLOCK)
        for cx, cy in ((BLOCK_X, y), (BLOCK_X + 4, y), (BLOCK_X, y + 4), (BLOCK_X + 4, y + 4)):
            put(img, cx, cy, BLOCK_D)
        put(img, BLOCK_X + 2, y + 2, BLOCK_D)   # the "?"
    if coin is not None:                         # coin y-offset above block
        cy = y - 4 - coin
        rect(img, BLOCK_X + 1, cy, BLOCK_X + 3, cy + 2, COIN)
        put(img, BLOCK_X + 2, cy + 1, WHITE)
        if sparkle:
            for sx, sy in ((BLOCK_X - 1, cy), (BLOCK_X + 5, cy + 1), (BLOCK_X + 2, cy - 2)):
                put(img, sx, sy, WHITE)


def draw_mushroom(img, x, top):
    rect(img, x, top, x + 4, top + 1, MUSH_R)         # cap
    put(img, x + 1, top, MUSH_C)                       # spots
    put(img, x + 3, top + 1, MUSH_C)
    rect(img, x + 1, top + 2, x + 3, top + 3, MUSH_C)  # stem


def draw_hero(img, x, feet_y, big=False, pose=0, flash=False):
    def c(color):
        return WHITE if flash else color
    rows = []
    # (dx spans, color) per row, top to bottom
    head = [
        [((1, 3), c(CAP))],
        [((0, 4), c(CAP))],
        [((1, 2), c(SKIN)), ((3, 3), c(EYE))],
    ]
    if big:
        body = [
            [((1, 3), c(SKIN))],
            [((0, 0), c(SKIN)), ((1, 3), c(CAP)), ((4, 4), c(SKIN))],
            [((1, 3), c(CAP))],
            [((1, 3), c(BLUE))],
            [((1, 3), c(BLUE))],
        ]
    else:
        body = [
            [((0, 0), c(SKIN)), ((1, 3), c(BLUE)), ((4, 4), c(SKIN))],
            [((1, 3), c(BLUE))],
        ]
    if pose == 1:  # legs apart mid-stride
        legs = [
            [((0, 0), c(BLUE)), ((4, 4), c(BLUE))],
            [((0, 0), c(SHOE)), ((4, 4), c(SHOE))],
        ]
    else:
        legs = [
            [((1, 1), c(BLUE)), ((3, 3), c(BLUE))],
            [((1, 1), c(SHOE)), ((3, 3), c(SHOE))],
        ]
    rows = head + body + legs
    top = feet_y - len(rows) + 1
    for dy, row in enumerate(rows):
        for (a, b), color in row:
            for dx in range(a, b + 1):
                put(img, x + dx, top + dy, color)


def draw_pipes(img):
    for lip_x, body_x in ((1, 2), (25, 26)):
        rect(img, lip_x, 21, lip_x + 5, 22, PIPE_L)
        put(img, lip_x + 5, 21, PIPE_D)
        put(img, lip_x + 5, 22, PIPE_D)
        rect(img, body_x, 23, body_x + 3, 27, PIPE_L)
        for y in range(23, 28):
            put(img, body_x + 3, y, PIPE_D)


def scene(used=False, bump=0, coin=None, sparkle=False):
    img = Image.new("RGB", (SIZE, SIZE), SKY)
    draw_block(img, used=used, bump=bump, coin=coin, sparkle=sparkle)
    for y in range(GROUND_Y, SIZE):
        for x in range(SIZE):
            put(img, x, y, GROUND_D if (x + (y % 2) * 2) % 4 == 0 else GROUND_L)
    return img


def dim(img, k):
    return img.point(lambda v: int(v * k))


def build():
    # 16-frame budget (panel decoder limit) — same story, tighter cuts
    frames = []

    def emit(img, k=1.0):
        frames.append(dim(img, k) if k < 1.0 else img)

    # f0 fade-in, empty, block fresh
    img = scene()
    draw_pipes(img)
    emit(img, 0.45)

    # f1 emerge onto the left pipe
    img = scene(); draw_hero(img, 1, 20); draw_pipes(img); emit(img)

    # f2-3 walk right
    for i, x in enumerate((7, 10)):
        img = scene()
        draw_hero(img, x, 27, pose=(i % 2))
        draw_pipes(img)
        emit(img)

    # f4 jump, f5 hit (bump + coin), f6 fall (used, coin sparkles away)
    img = scene(); draw_hero(img, 13, 24); draw_pipes(img); emit(img)
    img = scene(bump=1, coin=0); draw_hero(img, 13, 23); draw_pipes(img); emit(img)
    img = scene(used=True, coin=3, sparkle=True); draw_hero(img, 13, 26); draw_pipes(img); emit(img)

    # f7 mushroom on the block
    img = scene(used=True); draw_hero(img, 13, 27)
    draw_mushroom(img, 13, 9); draw_pipes(img); emit(img)

    # f8 mushroom drops, f9 they meet
    img = scene(used=True); draw_hero(img, 13, 27, pose=1)
    draw_mushroom(img, 20, 24); draw_pipes(img); emit(img)
    img = scene(used=True); draw_hero(img, 15, 27)
    draw_mushroom(img, 18, 24); draw_pipes(img); emit(img)

    # f10 flash + f11 grown
    img = scene(used=True); draw_hero(img, 15, 27, big=True, flash=True); draw_pipes(img); emit(img)
    img = scene(used=True); draw_hero(img, 15, 27, big=True); draw_pipes(img); emit(img)

    # f12 big walk right
    img = scene(used=True); draw_hero(img, 20, 27, big=True, pose=1); draw_pipes(img); emit(img)

    # f13-14 onto the right pipe and down
    for feet in (20, 24):
        img = scene(used=True)
        draw_hero(img, 25, feet, big=True)
        draw_pipes(img)
        emit(img)

    # f15 fade toward black (the reset happens in the dark)
    img = scene(used=True); draw_pipes(img)
    emit(img, 0.2)

    return frames


if __name__ == "__main__":
    frames = build()
    import gifsafe
    size = gifsafe.save(frames, HERE / "plumber.gif", duration_ms=200, colors=32)
    print(f"plumber.gif: {len(frames)} frames, {size} bytes ({'OK, single block' if size <= 4080 else 'TOO BIG!'})")
    keys = (1, 5, 11, 13)   # emerge, coin hit, grown, pipe descent
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (20, 20, 24))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "plumber.strip.png")
