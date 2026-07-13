# Lumen

AI design-and-communication window on an iDotMatrix BLE LED wall.

A local daemon owns the Bluetooth LE connection to the panel and exposes a
localhost HTTP API; an MCP server gives every Claude session `lumen_*` tools to
draw on a persistent pixel canvas, show images/GIFs, and scroll messages.

```
┌─────────────┐   MCP (stdio)   ┌──────────────┐   HTTP :7788   ┌────────────┐   BLE   ┌───────────┐
│ Claude      │ ──────────────► │ lumen-mcp.cjs │ ─────────────► │ daemon      │ ──────► │ iDotMatrix │
│ sessions    │                 │ (Node)        │                │ (FastAPI)   │         │ panel      │
└─────────────┘                 └──────────────┘                └────────────┘         └───────────┘
                                                   browser ► http://127.0.0.1:7788  (live preview)
```

## Run

```powershell
.\start-lumen.ps1     # daemon; auto-scans for IDM_* and connects, retries forever
```

Preview page: <http://127.0.0.1:7788> — live view of the canvas + connection state.

The panel advertises as `IDM_...`. It is **invisible while the phone app is
connected** — close the iDotMatrix app (or power-cycle the panel) and the daemon
latches on within ~15 s. The address is cached in `config.json` after first find.

## HTTP API (localhost:7788)

| Endpoint | What |
|---|---|
| `GET /status` | connected?, size, mode, last error |
| `GET /canvas.png?scale=8` | current canvas as PNG |
| `POST /draw {ops:[...], push?}` | draw primitives on the persistent canvas |
| `POST /clear {color?}` | wipe canvas |
| `POST /push` | re-push canvas (e.g. after clock/text mode) |
| `POST /text {text, color?, speed?, mode?, rainbow?}` | device-side scrolling marquee |
| `POST /notify {text, seconds?}` | scroll message, then auto-restore canvas |
| `POST /image {path}` | fit an image file to the panel |
| `POST /gif {path}` | play an animated GIF |
| `POST /pacman {delay?}` | self-playing arcade Pac-Man (real ghost AI); `POST /pacman/stop` to end |
| `POST /snake` / `POST /galaga` / `POST /life` | other self-running shows (each has a `/stop`) |
| `POST /clock {style?, color?}` | built-in clock face |
| `POST /color {color}` | fullscreen color |
| `POST /brightness {percent}` / `POST /screen {on}` | panel controls |
| `PUT /config {size?, address?}` | panel size (16/32/64) / BLE address |

Draw ops: `clear, pixel, line, rect, circle, ellipse, polygon, text, image` —
colors are `#rrggbb` / CSS names / `[r,g,b]`; `text` uses a built-in 3×5 pixel
font (`align:"center"`, `scale`, `\n` supported). The canvas persists across
calls, so draws can be incremental.

## MCP

```
claude mcp add --scope user lumen -- node C:\Users\JoshDay\source\repos\Lumen\mcp\lumen-mcp.cjs
```

Tools: `lumen_status, lumen_draw, lumen_canvas (see the canvas as an image),
lumen_clear, lumen_text, lumen_notify, lumen_image, lumen_gif, lumen_clock,
lumen_color, lumen_brightness, lumen_screen, lumen_config`.

## Notes

- Panel size defaults to **32** in `config.json`; set 16/64 via `PUT /config`
  or `lumen_config` if rendering looks scrambled.
- BLE is single-connection: the phone app and Lumen fight over the panel.
- Scroll text renders with `C:\Windows\Fonts\arialbd.ttf` by default
  (the `idotmatrix` lib ships no font); override per-call with `font`.
- Stack: Python 3.14, `idotmatrix` 0.0.9, `bleak` 3.x, FastAPI, Pillow; Node ≥18 for MCP.
