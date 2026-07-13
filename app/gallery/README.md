# Lumen Gallery

A small Windows desktop app to browse the art in [`../../art/`](../../art) and
send any piece straight to the LED wall.

![icon](icon-preview.png)

- **Live grid** of every still (`.png`) and loop (`.gif`) in `art/`, newest
  first — new daily pieces appear on relaunch. Reads the folder directly.
- **On the wall now** — mirrors the panel's current canvas, updated live.
- **Click** a piece to select, **Send to Wall** (or double-click) pushes it:
  stills via `POST /image`, GIF loops via `POST /gif`.
- **Play a show** — start the self-playing games (Pac-Man / Snake / Galaga)
  or Conway's Life on the wall; **Stop show** halts it and returns the wall to
  the Day Labs logo default.
- Connection status, brightness slider, screen on/off — all talk to the
  Lumen daemon at `http://127.0.0.1:7788`.

The Day Labs mark (`art/daylabs-mark-32.png`) is the daemon's default boot
image — what the panel shows on power-up until a scene, game, or send replaces
it.

Pure Python stdlib + Tkinter + Pillow (already in the repo's `.venv`) — no
extra installs, no packaging step.

## Run

```powershell
.venv\Scripts\pythonw.exe app\gallery\lumen_gallery.pyw
```

## Desktop shortcut

```powershell
powershell -File app\gallery\install-shortcut.ps1
```

Creates **Lumen Gallery** on the Desktop (windowless `pythonw` launch, custom
icon). Re-run `make_icon.py` to regenerate `icon.ico`.

The daemon must be running (it auto-starts at logon; otherwise
`powershell .\start-lumen.ps1`).
