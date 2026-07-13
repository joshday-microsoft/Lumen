"""Generate the Lumen Gallery app icon — a glowing LED-wall mark.

A dark rounded panel holding a grid of luminous dots that sweep a cyan-to-
magenta spectrum diagonally, with a few pixels lit hot-white like an LED
matrix mid-frame. Rendered at several sizes into a single multi-res .ico.

Run:  .venv\\Scripts\\python.exe app\\gallery\\make_icon.py
"""

import colorsys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "icon.ico"
SS = 8  # supersample factor for smooth rounded corners


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def render(size: int) -> Image.Image:
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # dark panel body with a faint inner border
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=(11, 14, 20, 255))
    d.rounded_rectangle([int(S * 0.03)] * 2 + [int(S * 0.97)] * 2,
                        radius=int(S * 0.19), outline=(38, 52, 74, 255), width=max(1, S // 90))

    # LED dot grid — 6x6, diagonal cyan->magenta spectrum, brighter toward a sweep
    n = 6
    pad = S * 0.15
    cell = (S - 2 * pad) / n
    r = cell * 0.30
    for gy in range(n):
        for gx in range(n):
            cx = pad + cell * (gx + 0.5)
            cy = pad + cell * (gy + 0.5)
            t = (gx + gy) / (2 * (n - 1))                 # 0..1 diagonal
            hue = (0.52 + 0.42 * t) % 1.0                 # cyan/blue -> violet -> magenta
            # a bright diagonal sweep band lights some dots hot
            sweep = 1.0 - min(1.0, abs((gx - gy)) / 2.2)
            val = 0.40 + 0.60 * sweep
            sat = 0.95 - 0.35 * sweep
            rr, gg, bb = colorsys.hsv_to_rgb(hue % 1.0, sat, val)
            col = (int(rr * 255), int(gg * 255), int(bb * 255), 255)
            # glow halo
            d.ellipse([cx - r * 1.8, cy - r * 1.8, cx + r * 1.8, cy + r * 1.8],
                      fill=(col[0], col[1], col[2], 40))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
            if sweep > 0.75:  # hot core
                d.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4],
                          fill=(255, 255, 255, 235))

    img = img.resize((size, size), Image.LANCZOS)
    # clip to rounded panel so corners stay transparent after downscale
    img.putalpha(rounded_mask(size, int(size * 0.22)))
    return img


if __name__ == "__main__":
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [render(s) for s in sizes]
    frames[0].save(OUT, format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[1:])
    # also drop a PNG preview to eyeball
    render(256).save(OUT.with_name("icon-preview.png"))
    print(f"wrote {OUT} ({', '.join(map(str, sizes))})")
