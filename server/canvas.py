"""Persistent drawing canvas for the LED panel.

All draw operations mutate an in-memory PIL image that mirrors what the
panel shows (in image mode). Ops are JSON dicts; see apply_ops.
"""

import base64
import io
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw

from . import font3x5


class CanvasError(ValueError):
    pass


def parse_color(value, default=(255, 255, 255)):
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        if len(value) not in (3, 4):
            raise CanvasError(f"color list must be [r,g,b], got {value!r}")
        return tuple(int(c) for c in value[:3])
    if isinstance(value, str):
        try:
            rgb = ImageColor.getrgb(value)
            return rgb[:3]
        except ValueError as e:
            raise CanvasError(str(e))
    raise CanvasError(f"unsupported color: {value!r}")


class Canvas:
    def __init__(self, size: int):
        self.size = size
        self.img = Image.new("RGB", (size, size), (0, 0, 0))

    def resize(self, size: int):
        self.size = size
        self.img = Image.new("RGB", (size, size), (0, 0, 0))

    # ---- ops ----

    def apply_ops(self, ops: list) -> int:
        if not isinstance(ops, list):
            raise CanvasError("ops must be a list of {op: ...} dicts")
        draw = ImageDraw.Draw(self.img)
        for i, op in enumerate(ops):
            if not isinstance(op, dict) or "op" not in op:
                raise CanvasError(f"ops[{i}] must be a dict with an 'op' key")
            try:
                self._apply(draw, op)
            except CanvasError:
                raise
            except Exception as e:
                raise CanvasError(f"ops[{i}] ({op.get('op')}): {e}")
        return len(ops)

    def _apply(self, draw: ImageDraw.ImageDraw, op: dict):
        kind = op["op"]
        if kind in ("clear", "fill"):
            color = parse_color(op.get("color"), (0, 0, 0))
            draw.rectangle([0, 0, self.size - 1, self.size - 1], fill=color)
        elif kind == "pixel":
            draw.point((op["x"], op["y"]), fill=parse_color(op.get("color")))
        elif kind == "line":
            draw.line(
                [op["x1"], op["y1"], op["x2"], op["y2"]],
                fill=parse_color(op.get("color")),
                width=int(op.get("width", 1)),
            )
        elif kind == "rect":
            x, y = op["x"], op["y"]
            w, h = op["w"], op["h"]
            draw.rectangle(
                [x, y, x + w - 1, y + h - 1],
                fill=parse_color(op.get("fill"), None) if "fill" in op else None,
                outline=parse_color(op.get("outline"), None) if "outline" in op else None,
            )
        elif kind == "circle":
            cx, cy, r = op["cx"], op["cy"], op["r"]
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                fill=parse_color(op.get("fill"), None) if "fill" in op else None,
                outline=parse_color(op.get("outline"), None) if "outline" in op else None,
            )
        elif kind == "ellipse":
            x, y = op["x"], op["y"]
            w, h = op["w"], op["h"]
            draw.ellipse(
                [x, y, x + w - 1, y + h - 1],
                fill=parse_color(op.get("fill"), None) if "fill" in op else None,
                outline=parse_color(op.get("outline"), None) if "outline" in op else None,
            )
        elif kind == "polygon":
            pts = [tuple(p) for p in op["points"]]
            if len(pts) < 3:
                raise CanvasError("polygon needs >= 3 points")
            draw.polygon(
                pts,
                fill=parse_color(op.get("fill"), None) if "fill" in op else None,
                outline=parse_color(op.get("outline"), None) if "outline" in op else None,
            )
        elif kind == "text":
            self._draw_text(op)
        elif kind == "image":
            self._paste_image(op)
        else:
            raise CanvasError(f"unknown op '{kind}'")

    def _draw_text(self, op: dict):
        text = str(op.get("text", ""))
        color = parse_color(op.get("color"))
        scale = max(1, int(op.get("scale", 1)))
        spacing = int(op.get("spacing", 1))
        x0 = int(op.get("x", 0))
        y = int(op.get("y", 0))
        # multi-line via \n, line gap of one scaled pixel row
        for line in text.split("\n"):
            x = x0
            if op.get("align") == "center":
                w, _ = font3x5.measure(line, scale, spacing)
                x = max(0, (self.size - w) // 2)
            for ch in line:
                g = font3x5.glyph(ch)
                for gy, row in enumerate(g):
                    for gx, cell in enumerate(row):
                        if cell == "#":
                            px = x + gx * scale
                            py = y + gy * scale
                            for dx in range(scale):
                                for dy in range(scale):
                                    if 0 <= px + dx < self.size and 0 <= py + dy < self.size:
                                        self.img.putpixel((px + dx, py + dy), color)
                x += (font3x5.GLYPH_W + spacing) * scale
            y += (font3x5.GLYPH_H + 1) * scale

    def _paste_image(self, op: dict):
        if "path" in op:
            src = Image.open(op["path"])
        elif "b64" in op:
            src = Image.open(io.BytesIO(base64.b64decode(op["b64"])))
        else:
            raise CanvasError("image op needs 'path' or 'b64'")
        src = src.convert("RGB")
        if "w" in op or "h" in op:
            w = int(op.get("w", src.width))
            h = int(op.get("h", src.height))
            src = src.resize((w, h), Image.LANCZOS)
            self.img.paste(src, (int(op.get("x", 0)), int(op.get("y", 0))))
        elif "x" in op or "y" in op:
            self.img.paste(src, (int(op.get("x", 0)), int(op.get("y", 0))))
        else:
            # fit whole canvas, preserving aspect, centered on black
            src.thumbnail((self.size, self.size), Image.LANCZOS)
            ox = (self.size - src.width) // 2
            oy = (self.size - src.height) // 2
            self.img.paste((0, 0, 0), [0, 0, self.size, self.size])
            self.img.paste(src, (ox, oy))

    # ---- output ----

    def png_bytes(self, scale: int = 1) -> bytes:
        img = self.img
        if scale > 1:
            img = img.resize((self.size * scale, self.size * scale), Image.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def save_png(self, path: Path):
        self.img.save(path, format="PNG")
