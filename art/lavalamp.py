"""Lava Lamp — a groovy retro lava lamp, blobs of hot wax rising and falling.

An original piece for the Lumen wall: a seamless loop. One big lamp fills the
panel against a dark room. Metaball blobs merge and pinch off organically as
they bob on sinusoidal cycles (period = FRAMES ⇒ the loop closes on itself).
The wax runs hot-yellow near the glowing bulb at the base and cools to deep
red toward the top; the fluid glows warm near the bulb. Mood: chill, hypnotic.

Run:  .venv\\Scripts\\python.exe art\\lavalamp.py   → lavalamp.gif (+ strip)
"""

import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 32
FRAMES = 24
CX = 16.0

# vertical bands
CAP_TOP, CAP_BOT = 2, 4          # metal cap
GTOP, GBOT = 5, 24               # glass vessel
BASE_TOP, BASE_BOT = 25, 30      # metal base (bulb lives at the seam)

# palette
ROOM_TOP = (10, 6, 16)
ROOM_BOT = (20, 8, 20)
GLASS = (36, 20, 66)             # fluid: deep indigo/violet
GLASS_HI = (70, 44, 110)         # glass rim highlight
BULB = (255, 210, 120)           # warm glow at the base
METAL = (70, 66, 82)
METAL_HI = (150, 146, 168)
METAL_DK = (34, 30, 44)

WAX_HOT = (255, 236, 140)        # bottom, near the bulb
WAX_MID = (255, 120, 44)
WAX_TOP = (206, 44, 52)          # cooled, near the top


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def half_width(y):
    """Half-width of the glass silhouette at row y, else None (outside glass)."""
    if y < GTOP or y > GBOT:
        return None
    t = (y - GTOP) / (GBOT - GTOP)
    # cone widening downward with a small domed shoulder up top
    hw = 2.4 + 6.1 * t
    if y <= GTOP + 1:
        hw = min(hw, 2.2)
    return hw


def wax_color(y):
    """Hot-to-cool gradient by height inside the glass."""
    t = (y - GTOP) / (GBOT - GTOP)          # 0 top .. 1 bottom
    if t > 0.5:
        return lerp(WAX_MID, WAX_HOT, (t - 0.5) / 0.5)
    return lerp(WAX_TOP, WAX_MID, t / 0.5)


def blobs(phase):
    """(cx, cy, r) metaballs. Vertical motion is sinusoidal in phase so the
    loop closes; opposite phases make one rise while another sinks."""
    return [
        (CX,        23.5 + 0.7 * math.sin(phase),           4.6),   # wax pool
        (CX - 1.5,  18.0 + 6.2 * math.sin(phase),           2.7),
        (CX + 2.0,  14.5 - 5.4 * math.sin(phase + 0.9),     2.3),
        (CX - 0.5,  10.5 + 4.4 * math.sin(phase + 2.0),     1.9),
        (CX + 1.0,   8.0 + 3.0 * math.sin(phase + 3.6),     1.5),
    ]


def field(x, y, bs):
    s = 0.0
    for cx, cy, r in bs:
        s += (r * r) / ((x - cx) ** 2 + (y - cy) ** 2 + 0.6)
    return s


def frame(f):
    phase = 2 * math.pi * f / FRAMES
    bs = blobs(phase)
    img = Image.new("RGB", (SIZE, SIZE))

    for y in range(SIZE):
        # room background with a faint warm ambient near the base
        base_bg = lerp(ROOM_TOP, ROOM_BOT, y / (SIZE - 1))
        for x in range(SIZE):
            hw = half_width(y)
            if hw is not None and abs(x - CX) <= hw:
                # inside the glass
                edge = hw - abs(x - CX)
                # fluid, glowing warm toward the bulb at the bottom
                db = math.hypot(x - CX, y - (BASE_TOP - 0.5))
                fluid = lerp(GLASS, (150, 70, 90), max(0.0, 1.0 - db / 16))
                if edge < 1.0:                      # glass rim highlight
                    fluid = lerp(fluid, GLASS_HI, 0.5)
                fv = field(x, y, bs)
                if fv >= 1.0:
                    wax = wax_color(y)
                    # brighten the blob cores, keep a soft edge
                    core = min(1.0, (fv - 1.0) * 0.8)
                    col = lerp(wax, WAX_HOT, core * 0.35)
                    if fv < 1.22:                   # anti-aliased blob edge
                        col = lerp(fluid, col, (fv - 1.0) / 0.22)
                    img.putpixel((x, y), col)
                else:
                    img.putpixel((x, y), fluid)
            else:
                img.putpixel((x, y), base_bg)

    # metal cap (top)
    for y in range(CAP_TOP, CAP_BOT + 1):
        t = (y - CAP_TOP) / max(1, CAP_BOT - CAP_TOP)
        hw = 1.4 + 1.4 * t
        for x in range(int(CX - hw), int(CX + hw) + 1):
            img.putpixel((x, y), METAL if x > CX else METAL_HI)
    img.putpixel((int(CX), CAP_TOP - 0)  , METAL_HI)

    # metal base (bottom) with the glowing bulb at the seam
    for y in range(BASE_TOP, BASE_BOT + 1):
        t = (y - BASE_TOP) / max(1, BASE_BOT - BASE_TOP)
        hw = 8.4 + 2.2 * t
        for x in range(int(CX - hw), int(CX + hw) + 1):
            if y == BASE_TOP:                       # bulb glow slit
                gx = 1.0 - abs(x - CX) / (hw + 0.01)
                img.putpixel((x, y), lerp(METAL, BULB, gx))
            elif y == BASE_BOT and abs(x - CX) < hw - 0.5:
                img.putpixel((x, y), METAL_DK)
            else:
                img.putpixel((x, y), METAL if x > CX else lerp(METAL, METAL_HI, 0.5))
    # warm bloom rising off the bulb into the fluid
    for y in range(BASE_TOP - 3, BASE_TOP):
        hw = half_width(y)
        if hw is None:
            continue
        for x in range(int(CX - hw), int(CX + hw) + 1):
            g = max(0.0, 1.0 - (BASE_TOP - y) / 3.5) * (1.0 - abs(x - CX) / (hw + 1))
            if g > 0.05:
                img.putpixel((x, y), lerp(img.getpixel((x, y)), BULB, g * 0.5))
    return img


if __name__ == "__main__":
    frames = [frame(f) for f in range(FRAMES)]
    import gifsafe
    size = gifsafe.save(frames, HERE / "lavalamp.gif", duration_ms=150, colors=16)
    ok = size <= 8192 and len(frames) <= 60
    print(f"lavalamp.gif: {len(frames)} frames, {size} bytes ({'OK' if ok else 'TOO BIG!'})")
    keys = (0, 6, 12, 18)
    strip = Image.new("RGB", (SIZE * 6 * len(keys) + (len(keys) - 1) * 4, SIZE * 6), (18, 16, 22))
    for i, k in enumerate(keys):
        strip.paste(frames[k].resize((SIZE * 6, SIZE * 6), Image.NEAREST), (i * (SIZE * 6 + 4), 0))
    strip.save(HERE / "lavalamp.strip.png")
    # single hero still
    frames[6].resize((SIZE, SIZE)).save(HERE / "lavalamp.png")
    print("wrote lavalamp.gif + strip")
