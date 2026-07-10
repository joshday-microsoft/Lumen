---
name: lumen
description: Drive Josh's iDotMatrix LED wall (Lumen) — draw pixel art, scroll messages, show images/GIFs/clock/scenes, set brightness, screen on/off. Use for /lumen, "on the wall", "on the panel", "LED wall", "draw X on the wall", "flash/notify me when done".
---

# /lumen — the LED wall (canonical)

A 32×32 iDotMatrix BLE panel, driven by the **Lumen daemon** on `http://127.0.0.1:7788`.
Repo: `C:\Users\JoshDay\source\repos\Lumen`. Live browser preview: <http://127.0.0.1:7788>.

Interpret the argument freely and pick the right surface:

| Josh says | Do |
|---|---|
| draw/sketch X | `lumen_draw` with ops (below); verify with `lumen_canvas` |
| tell/flash/notify me ... | `lumen_notify` (scrolls, then auto-restores the canvas) |
| show image/GIF ... | generate or locate file → `lumen_image` / `lumen_gif` |
| clock / mood light / off / dim | `lumen_clock` / `lumen_color` / `lumen_screen` / `lumen_brightness` |
| sunset / starfield | ready-made scenes: `art\sunset.png`, `art\starfield.gif` in the repo |
| status / is it working | `lumen_status` |

## Tools

Prefer the user-scope `lumen_*` MCP tools (`lumen_status, lumen_draw, lumen_canvas,
lumen_clear, lumen_text, lumen_notify, lumen_image, lumen_gif, lumen_clock, lumen_color,
lumen_brightness, lumen_screen, lumen_config`). If they aren't loaded, ToolSearch "lumen".
No MCP at all? The daemon is plain HTTP — same verbs as endpoints (`POST /draw`, `/notify`,
`/image`, `/gif`, `/clock`, `/color`, `/brightness`, `/screen`, `GET /status`, `/canvas.png`).

## Canvas rules

- 32×32, origin top-left. The canvas **persists between calls** — draw incrementally, or start with `{op:"clear"}`.
- Ops: `clear, pixel, line, rect, circle, ellipse, polygon, text, image`. Colors `#rrggbb` / CSS names / `[r,g,b]`.
- `text` op = built-in 3×5 font, 4px per char ⇒ **max ~8 chars per line** at scale 1; `align:"center"`, `scale`, `\n` supported. Longer message? Use `lumen_notify` instead.
- Clock/text/GIF modes take over the panel; the canvas is retained — any `lumen_draw` or `POST /push` restores it.
- **Check your work**: `lumen_canvas` returns the canvas as an image.
- Rich art: generate a PNG/GIF with Pillow (see `art\generate.py` for the pattern; venv at `.venv\Scripts\python.exe`), then `lumen_image` / `lumen_gif`. Short GIF loops only — BLE is slow (~24 frames is fine).

## Troubleshooting

- `503 not connected`: panel is off, out of range, or the phone app has grabbed it (single connection!). The daemon retries every ~10 s — no action needed once the blocker clears.
- Connection refused: daemon down. It auto-starts at logon (Scheduled Task "Lumen LED Wall"); start manually with `powershell C:\Users\JoshDay\source\repos\Lumen\start-lumen.ps1`. Log: `tmp\lumen.log`.
- Rendering tiled/cropped/scrambled: panel size mismatch — `lumen_config` size 16/32/64 (persists to `config.json`).
