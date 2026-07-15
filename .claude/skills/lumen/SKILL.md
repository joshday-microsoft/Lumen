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
- Rich art: draw frames with Pillow, then **encode with `art\gifsafe.py`** — `gifsafe.save(frames, path, duration_ms, colors)` — and send via `lumen_gif`. NEVER save animated GIFs with PIL's own `.save()`: Pillow writes delta sub-rectangle frames and the panel's firmware stalls on them (the sneaky part: pieces with large-area motion happen to survive, small-motion ones die). gifsafe writes full frames, one global palette, constant-width LZW, and round-trip-verifies itself. Budget (daemon-enforced; proven envelope, measured 2026-07-10): **≤ 60 frames AND ≤ 8192 bytes** — there is no 24-frame cliff (that was Pillow delta frames all along); 60 frames / 8.1 KB / 2 blocks is the largest *verified* playback, and the true ceiling is likely higher. A genuinely wedged decoder needs a **power-cycle**, and BLE keeps acking while frozen, so uploads "succeed" with nothing showing. Boundary probes: `art\frametest.py` + `{"force":true}` on `/gif`.
- **SELF-PLAYING GAMES:** `POST /pacman {delay?}` runs an arcade-faithful Pac-Man (classic 28x31 maze, real Blinky/Pinky/Inky/Clyde targeting AI, scatter/chase, frightened energizers); `POST /snake` and `POST /galaga` are the other game shows. Each runs until `POST /<game>/stop` or another scene starts. (MCP: `lumen_pacman` / `lumen_snake` / `lumen_galaga`.)
- **LIVE SIMULATION:** `POST /life {delay?, density?}` runs Conway's Game of Life on the panel indefinitely — daemon computes generations and streams them (~2/sec), cells colored by age, self-reseeds on stagnation; `POST /life/stop` halts. The pattern (continuous canvas pushes from a daemon loop) generalizes to any live generative show.
- **PAINTING (preferred for art reveals — no GIF, no limits):** `lumen_paint` / `POST /paint {pixels:[[x,y,"#rrggbb"],...], delay?}` paints strokes live in order — the ORDER is the performance: background washes first (serpentine sweeps look brushy), then subjects, details last. ~20 strokes/sec at delay 0.02. Build stroke lists in a script (pattern: `art\happytree.py`). `POST /spiral {delay}` = spectrum-spiral fill; `/paint/stop` halts. Completed pieces: `art\spectrum-spiral.png`, `art\happy-tree.png` (re-showable via `lumen_image`). Use GIFs only when the piece needs to LOOP; use painting when the making is the show.
- Design law: at 32×32, **big subject, minimal scene** — one large character/element beats a tiny sprite in a detailed level.

## Troubleshooting

- `503 not connected`: panel is off, out of range, or the phone app has grabbed it (single connection!). The daemon retries every ~10 s — no action needed once the blocker clears.
- Connection refused: daemon down. It auto-starts at logon (Scheduled Task "Lumen LED Wall"); start manually with `powershell C:\Users\JoshDay\source\repos\Lumen\start-lumen.ps1`. Log: `tmp\lumen.log`.
- Rendering tiled/cropped/scrambled: panel size mismatch — `lumen_config` size 16/32/64 (persists to `config.json`).
- **Blank panel but pushes "succeed" (`pushed:true`, no log errors), and even a solid `/color` fill won't light it:** the panel's decoder is wedged — BLE keeps acking a frozen device. Fix is a physical **power-cycle** (unplug ~10 s). Verify recovery with a solid `/color` test *before* trying art.
- **`/color` works but `/image` (and `/draw`/`/clear` canvas pushes) render blank** — this happened 2026-07-15, and survived a power-cycle: the panel's DIY **image-upload path (`IdmImage.uploadProcessed`) is unreliable on this unit**, while the graffiti, GIF, color, text and clock paths are solid. The library sends the PNG with blind write-without-response (daemon now uses acked `response=True`, but that alone didn't render it here). **For stills, deliver via `/paint` (graffiti per-pixel) instead of `/image`** — `POST /paint {"path":"foo.png","clear":false}` paints all 1024 pixels reliably (paint_runner even auto-resumes on BLE drops). This is why the daily still is logged as a "painting".
