"""Lumen daemon — owns the BLE connection to the iDotMatrix panel and
exposes a localhost HTTP API for drawing and communication.

Run:  .venv\\Scripts\\python.exe -m uvicorn server.main:app --port 7788 --app-dir <repo root>
"""

import asyncio
import colorsys
import io
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from bleak import BleakScanner
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from idotmatrix import (
    Clock as IdmClock,
    Common as IdmCommon,
    ConnectionManager,
    FullscreenColor,
    Gif as IdmGif,
    Graffiti as IdmGraffiti,
    Image as IdmImage,
    Text as IdmText,
)

from idotmatrix.const import UUID_READ_DATA, UUID_WRITE_DATA
from PIL import Image as PilImage

from .canvas import Canvas, CanvasError, parse_color
from .galaga import Galaga
from .pacman import PacMan
from .snake import SnakeGame

log = logging.getLogger("lumen")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)

# headless runs (scheduled task / pythonw) have no console — keep a file log too
_fh = logging.FileHandler(TMP / "lumen.log", encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_fh)

DEFAULT_SCROLL_FONT = r"C:\Windows\Fonts\arialbd.ttf"

# panel limits per instrumented probes (art/frametest.py, 2026-07-10):
# with gifsafe encoding there is NO frame cliff at 24 — the old freezes were
# Pillow delta frames. Proven playback envelope: 60 frames / 8.1KB / 2 blocks
# (5-block transport also acked; playback beyond 60f unverified). Guards sit
# at the proven envelope; body {"force":true} bypasses for boundary testing.
MAX_GIF_FRAMES = 60
MAX_GIF_BYTES = 8192


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config():
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


config = {"size": 32, "address": None, "port": 7788, **load_config()}

canvas = Canvas(int(config["size"]))
cm = ConnectionManager()
dev_lock = asyncio.Lock()

state = {
    "connected_since": None,
    "last_error": None,
    "display_mode": "canvas",  # canvas | text | gif | clock | color | off
    "needs_push": False,
    "last_push": None,
    "scanning": False,
    "now_playing": None,   # {"kind","path","name"} when a GIF is on the wall — lets clients mirror it
}


def is_connected() -> bool:
    return bool(cm.client and cm.client.is_connected)


async def find_device() -> str | None:
    """Scan for any device advertising an IDM_/IDM- name."""
    state["scanning"] = True
    try:
        devices = await BleakScanner.discover(timeout=6.0, return_adv=True)
        for _key, (device, adv) in devices.items():
            name = (adv.local_name or device.name or "")
            if name.upper().startswith("IDM"):
                log.info("found panel %s (%s)", name, device.address)
                return device.address
        return None
    finally:
        state["scanning"] = False


async def _send_png_acked(path):
    """Upload a still PNG to the panel with ACKED BLE writes.

    The idotmatrix library's uploadProcessed fires write-without-response for
    every chunk with no confirmation (connectionManager.send, response=False);
    on a flaky link chunks silently drop and the panel receives a corrupt PNG
    that it renders as a blank screen — while a single-write command like
    FullscreenColor always survives. Writing with response=True makes each
    chunk wait for the peripheral's ack so nothing is lost. Falls back to a
    throttled write-without-response if the characteristic rejects acked
    writes. Caller must hold dev_lock.
    """
    with PilImage.open(path) as img:
        if img.size != (canvas.size, canvas.size):
            img = img.resize((canvas.size, canvas.size), PilImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    payload = bytearray(IdmImage()._createPayloads(bytearray(png_bytes)))
    try:
        await cm.send(payload, response=True)
    except Exception as e:                       # char may be write-without-response only
        log.warning("acked image write failed (%s); throttled fallback", e)
        ch = cm.client.services.get_characteristic(UUID_WRITE_DATA).max_write_without_response_size
        for i in range(0, len(payload), ch):
            await cm.client.write_gatt_char(UUID_WRITE_DATA, payload[i:i + ch], response=False)
            await asyncio.sleep(0.008)


async def push_canvas_locked():
    """Push the current canvas to the panel. Caller must hold dev_lock."""
    path = TMP / "canvas.png"
    canvas.save_png(path)
    leaving_gif = state["display_mode"] == "gif"
    await IdmImage().setMode(1)
    if leaving_gif:
        # leaving GIF playback: the mode switch blanks the screen but the
        # panel drops image data sent immediately after — settle, then send
        # twice (observed: gif -> instant image push renders black)
        await asyncio.sleep(0.5)
    await _send_png_acked(path)
    if leaving_gif:
        await asyncio.sleep(0.3)
        await _send_png_acked(path)
    state["display_mode"] = "canvas"
    state["now_playing"] = None
    state["needs_push"] = False
    state["last_push"] = time.time()


async def device_call(fn, *, mode: str | None = None):
    """Serialize a device operation; drop the connection on failure so the
    reconnect loop can recover it."""
    if not is_connected():
        raise HTTPException(503, "panel not connected (it may be off, out of range, or held by the phone app)")
    async with dev_lock:
        try:
            result = await fn()
            if mode:
                state["display_mode"] = mode
            return result
        except HTTPException:
            raise
        except Exception as e:
            state["last_error"] = f"{type(e).__name__}: {e}"
            log.warning("device call failed: %s", state["last_error"])
            try:
                await cm.disconnect()
            except Exception:
                pass
            cm.client = None
            raise HTTPException(503, f"device call failed: {e}")


# Modes that redraw the panel from their own loop — a reconnect must not fight
# them: the games and life stream their next frame within a second or two, the
# clock runs on the panel itself, "off" must stay off, and scrolling text has
# its own restore timer.
SELF_DRIVING = {"life", "snake", "galaga", "pacman", "text", "clock", "off"}


async def restore_display():
    """Put back whatever was on the panel when the link dropped.

    The PNG upload path is NOT trusted for this. It has failed twice on this
    unit: 2026-07-15, and again 2026-08-05, when a three-hour drop ended in a
    reconnect that logged "canvas pushed" while the wall stayed dark — every
    BLE write acked, nothing rendered, and the day's painting was gone until a
    human noticed. Graffiti per-pixel writes are the path this panel always
    honours, so the canvas is REPAINTED: ~1024 writes at roughly 30 ms each
    (~30 s). The image upload still goes FIRST, because that is what the panel
    stores and redisplays on its own power-up; the repaint is what guarantees
    the picture is actually on the wall now.

    GIF playback is re-sent through the GIF flow, which is proven reliable —
    before this, a drop during a loop restored the canvas instead of the GIF.
    """
    if _painter_busy() or spiral_state["running"]:
        return                              # paint_runner resumes on its own pixel
    if state["display_mode"] in SELF_DRIVING:
        return

    playing = state.get("now_playing") or {}
    if playing.get("kind") == "gif" and playing.get("path") and Path(playing["path"]).exists():
        try:
            async with dev_lock:
                await send_gif_flow_controlled(Path(playing["path"]).read_bytes())
            log.info("reconnect: re-sent gif %s", playing.get("name"))
        except Exception as e:
            log.warning("reconnect: gif restore failed: %s", e)
        return

    try:
        async with dev_lock:
            await push_canvas_locked()
    except Exception as e:
        log.warning("reconnect: canvas upload failed (%s) — repainting anyway", e)

    steps = [(x, y, canvas.img.getpixel((x, y))) for x, y in spiral_coords(canvas.size)]
    log.info("reconnect: repainting canvas via graffiti (%d pixels)", len(steps))
    spiral_state["task"] = asyncio.create_task(_repaint_canvas(steps))


async def _repaint_canvas(steps):
    await paint_runner(steps, delay=0.0, clear=False, label="restore")
    # paint_runner leaves the mode as "graffiti"; hand it back so the NEXT
    # reconnect still recognises this as a restorable still
    state["display_mode"] = "canvas"
    state["needs_push"] = False


async def on_connected():
    state["connected_since"] = time.time()
    state["last_error"] = None
    async with dev_lock:
        try:
            now = datetime.now()
            await IdmCommon().setTime(now.year, now.month, now.day, now.hour, now.minute, now.second)
        except Exception as e:
            log.warning("setTime failed (non-fatal): %s", e)
    log.info("connected to %s", cm.address)
    asyncio.create_task(restore_display())      # outside dev_lock: it repaints


async def connection_loop():
    while True:
        try:
            if is_connected():
                await asyncio.sleep(3)
                continue
            addr = config.get("address")
            if not addr:
                addr = await find_device()
                if addr:
                    config["address"] = addr
                    save_config()
            if addr:
                cm.address = addr
                log.info("connecting to %s ...", addr)
                await asyncio.wait_for(cm.connect(), timeout=30)
                if is_connected():
                    await on_connected()
                    continue
        except Exception as e:
            state["last_error"] = f"{type(e).__name__}: {e}"
            cm.client = None
            log.info("connect attempt failed: %s", e)
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # default boot image: the Day Labs mark. It's what the first connect pushes
    # (and therefore what the panel stores and redisplays on power-up) until a
    # scene, game, or gallery send replaces it.
    if all(p == (0, 0, 0) for p in canvas.img.getdata()):
        # prefer the last picture that was on the wall, so restarting the daemon
        # does not throw away the day's art; the mark is the fallback
        last = TMP / "canvas.png"
        boot = last if last.exists() else ROOT / "art" / "daylabs-mark-32.png"
        try:
            canvas.apply_ops([{"op": "image", "path": str(boot)}])
        except Exception as e:
            log.warning("boot logo failed (%s) — using text splash", e)
            canvas.apply_ops([
                {"op": "rect", "x": 0, "y": 0, "w": canvas.size, "h": canvas.size, "outline": "#123a5c"},
                {"op": "text", "text": "LUMEN", "y": canvas.size // 2 - 3, "align": "center", "color": "#4db8ff"},
            ])
    task = asyncio.create_task(connection_loop())
    yield
    task.cancel()
    try:
        await cm.disconnect()
    except Exception:
        pass


app = FastAPI(title="Lumen", lifespan=lifespan)


@app.get("/status")
async def status():
    return {
        "connected": is_connected(),
        "address": config.get("address"),
        "size": canvas.size,
        "display_mode": state["display_mode"],
        "needs_push": state["needs_push"],
        "connected_since": state["connected_since"],
        "last_push": state["last_push"],
        "last_error": state["last_error"],
        "scanning": state["scanning"],
        "now_playing": state["now_playing"],
        "spiral": {k: spiral_state[k] for k in ("running", "index", "total", "delay")},
    }


@app.get("/canvas.png")
async def canvas_png(scale: int = 1):
    return Response(canvas.png_bytes(scale=max(1, min(scale, 32))), media_type="image/png")


@app.post("/draw")
async def draw(body: dict = Body(...)):
    ops = body.get("ops")
    try:
        n = canvas.apply_ops(ops or [])
    except CanvasError as e:
        raise HTTPException(400, str(e))
    pushed = False
    if body.get("push", True):
        if is_connected():
            await device_call(push_canvas_locked)
            pushed = True
        else:
            state["needs_push"] = True
    return {"applied": n, "pushed": pushed, "connected": is_connected()}


@app.post("/clear")
async def clear(body: dict = Body(default={})):
    canvas.apply_ops([{"op": "clear", "color": body.get("color", "#000000")}])
    pushed = False
    if is_connected():
        await device_call(push_canvas_locked)
        pushed = True
    else:
        state["needs_push"] = True
    return {"pushed": pushed}


@app.post("/push")
async def push():
    await device_call(push_canvas_locked)
    return {"pushed": True}


@app.post("/text")
async def text(body: dict = Body(...)):
    msg = body.get("text")
    if not msg:
        raise HTTPException(400, "text required")
    color = parse_color(body.get("color"), (255, 255, 255))
    speed = int(body.get("speed", 95))
    text_mode = int(body.get("mode", 1))  # 0 static, 1 marquee, 5 blink, 6 fade, 7 tetris, 8 filling
    color_mode = 2 if body.get("rainbow") else 1
    font_size = int(body.get("font_size", 16))
    font_path = body.get("font") or DEFAULT_SCROLL_FONT

    async def _send():
        result = await IdmText().setMode(
            str(msg),
            font_size=font_size,
            font_path=font_path,
            text_mode=text_mode,
            speed=speed,
            text_color_mode=color_mode,
            text_color=tuple(color),
        )
        if result is False:
            raise RuntimeError("Text.setMode failed (see daemon log)")

    await device_call(_send, mode="text")
    state["needs_push"] = True  # canvas no longer on screen
    return {"ok": True, "mode": "text"}


@app.post("/notify")
async def notify(body: dict = Body(...)):
    """Scroll a message, then return to the canvas after `seconds` (estimate)."""
    seconds = float(body.get("seconds", 12))
    resp = await text(body)

    async def _restore():
        await asyncio.sleep(seconds)
        if is_connected() and state["display_mode"] == "text":
            try:
                await device_call(push_canvas_locked)
            except HTTPException:
                pass

    if body.get("restore", True):
        asyncio.create_task(_restore())
    return {**resp, "restore_after": seconds}


@app.post("/image")
async def image(body: dict = Body(...)):
    op = {k: v for k, v in body.items() if k in ("path", "b64", "x", "y", "w", "h")}
    if op.get("path"):
        op["path"] = resolve_art(op["path"])   # bare filenames live in art/
    try:
        canvas.apply_ops([{"op": "image", **op}])
    except CanvasError as e:
        raise HTTPException(400, str(e))
    pushed = False
    if is_connected():
        await device_call(push_canvas_locked)
        pushed = True
    else:
        state["needs_push"] = True
    return {"pushed": pushed}


async def send_gif_flow_controlled(gif_bytes: bytes):
    """Send a GIF with per-block flow control. The device acks each 4k block
    with a notification (05 00 01 00 01 ...); the library fires blocks
    blind, which drops everything past the first block on this panel and
    truncates animations. Caller must hold dev_lock."""
    chunks = IdmGif()._createPayloads(bytearray(gif_bytes))
    client = cm.client
    ack = asyncio.Event()

    def on_notify(_char, payload: bytearray):
        log.info("gif ack notification: %s", bytes(payload[:8]).hex())
        ack.set()

    notify_ok = True
    try:
        await client.start_notify(UUID_READ_DATA, on_notify)
    except Exception as e:
        notify_ok = False
        log.warning("start_notify failed (%s) — falling back to fixed delays", e)
    try:
        char = client.services.get_characteristic(UUID_WRITE_DATA)
        mtu = char.max_write_without_response_size
        for ci, chunk in enumerate(chunks):
            ack.clear()
            for i in range(0, len(chunk), mtu):
                await client.write_gatt_char(UUID_WRITE_DATA, chunk[i:i + mtu], response=True)
            if notify_ok:
                try:
                    await asyncio.wait_for(ack.wait(), timeout=2.5)
                except asyncio.TimeoutError:
                    log.warning("no ack for gif block %d/%d — pausing instead", ci + 1, len(chunks))
                    await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(0.5)
        log.info("gif upload done: %d bytes in %d blocks", len(gif_bytes), len(chunks))
    finally:
        if notify_ok:
            try:
                await client.stop_notify(UUID_READ_DATA)
            except Exception:
                pass


@app.post("/gif")
async def gif(body: dict = Body(...)):
    path = resolve_art(body.get("path") or "")
    if not body.get("path") or not Path(path).exists():
        raise HTTPException(400, f"gif path not found: {path}")

    # panel-native GIFs go up verbatim; anything else gets resized first.
    # (the library's uploadProcessed re-encode also bloats files — avoid it)
    from PIL import Image as PilImage
    import io as _io
    with PilImage.open(path) as im:
        if im.size == (canvas.size, canvas.size):
            gif_bytes = Path(path).read_bytes()
        else:
            frames, durations = [], []
            try:
                while True:
                    durations.append(im.info.get("duration", 120))
                    frames.append(im.copy().convert("RGB").resize((canvas.size, canvas.size), PilImage.NEAREST))
                    im.seek(im.tell() + 1)
            except EOFError:
                pass
            buf = _io.BytesIO()
            frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                           duration=durations, loop=0)
            gif_bytes = buf.getvalue()

    with PilImage.open(_io.BytesIO(gif_bytes)) as chk:
        nframes = getattr(chk, "n_frames", 1)
    if body.get("force"):
        log.warning("gif limits bypassed via force=true (%d frames, %d bytes) — boundary testing", nframes, len(gif_bytes))
    else:
        if nframes > MAX_GIF_FRAMES:
            raise HTTPException(400, f"GIF has {nframes} frames — the panel's decoder freezes above {MAX_GIF_FRAMES} (needs a power-cycle to recover). Re-cut to <= {MAX_GIF_FRAMES} frames.")
        if len(gif_bytes) > MAX_GIF_BYTES:
            raise HTTPException(400, f"GIF is {len(gif_bytes)} bytes — must fit one protocol block (<= {MAX_GIF_BYTES}). Fewer frames / smaller palette.")

    async def _send():
        await send_gif_flow_controlled(gif_bytes)

    await device_call(_send, mode="gif")
    state["needs_push"] = True
    state["now_playing"] = {"kind": "gif", "path": str(path), "name": Path(path).stem}
    return {"ok": True, "mode": "gif"}


@app.post("/clock")
async def clock(body: dict = Body(default={})):
    style = int(body.get("style", 0))
    color = parse_color(body.get("color"), (255, 255, 255))

    async def _send():
        await IdmClock().setMode(
            style,
            visibleDate=bool(body.get("date", True)),
            hour24=bool(body.get("hour24", True)),
            r=color[0], g=color[1], b=color[2],
        )

    await device_call(_send, mode="clock")
    state["needs_push"] = True
    return {"ok": True, "mode": "clock", "style": style}


@app.post("/color")
async def fullscreen_color(body: dict = Body(...)):
    color = parse_color(body.get("color"))

    async def _send():
        await FullscreenColor().setMode(color[0], color[1], color[2])

    await device_call(_send, mode="color")
    state["needs_push"] = True
    return {"ok": True, "color": list(color)}


@app.post("/brightness")
async def brightness(body: dict = Body(...)):
    pct = max(5, min(100, int(body.get("percent", 80))))

    async def _send():
        await IdmCommon().setBrightness(pct)

    await device_call(_send)
    return {"ok": True, "percent": pct}


@app.post("/screen")
async def screen(body: dict = Body(...)):
    on = bool(body.get("on", True))

    async def _send():
        if on:
            await IdmCommon().screenOn()
        else:
            await IdmCommon().screenOff()

    await device_call(_send, mode=("canvas" if on else "off"))
    return {"ok": True, "on": on}


spiral_state = {"running": False, "index": 0, "total": 0, "delay": 1.0, "task": None}


def spiral_coords(n: int):
    """Outside-in clockwise spiral over the full n x n grid."""
    coords = []
    top, left, bottom, right = 0, 0, n - 1, n - 1
    while top <= bottom and left <= right:
        for x in range(left, right + 1):
            coords.append((x, top))
        for y in range(top + 1, bottom + 1):
            coords.append((right, y))
        if bottom > top:
            for x in range(right - 1, left - 1, -1):
                coords.append((x, bottom))
        if right > left:
            for y in range(bottom - 1, top, -1):
                coords.append((left, y))
        top += 1
        left += 1
        bottom -= 1
        right -= 1
    return coords


async def paint_runner(steps, delay: float, clear: bool, label: str):
    """Live-paint pixels via Graffiti mode, in order, mirrored on the canvas.
    Survives BLE drops (waits and resumes on the same pixel)."""
    total = len(steps)
    spiral_state.update(running=True, total=total, delay=delay, index=0)
    log.info("%s: painting %d pixels, %.3fs delay (~%.1f min)", label, total, delay, total * max(delay, 0.03) / 60)
    try:
        if clear:
            canvas.apply_ops([{"op": "clear"}])   # clean slate on panel + mirror
            if is_connected():
                try:
                    async with dev_lock:
                        await push_canvas_locked()
                except Exception:
                    pass
        state["display_mode"] = "graffiti"
        for i, (x, y, (r, g, b)) in enumerate(steps):
            spiral_state["index"] = i
            while spiral_state["running"]:
                if is_connected():
                    try:
                        async with dev_lock:
                            await IdmGraffiti().setPixel(r, g, b, x, y)
                        break
                    except Exception as e:
                        state["last_error"] = f"{type(e).__name__}: {e}"
                        log.warning("%s pixel %d failed (%s), waiting for reconnect", label, i, e)
                        try:
                            await cm.disconnect()
                        except Exception:
                            pass
                        cm.client = None
                await asyncio.sleep(2)
            if not spiral_state["running"]:
                log.info("%s stopped at pixel %d", label, i)
                return
            canvas.img.putpixel((x, y), (r, g, b))
            if i % 64 == 0:
                log.info("%s progress: %d/%d", label, i, total)
            if delay:
                await asyncio.sleep(delay)
        log.info("%s complete: %d pixels", label, total)
        # snapshot the finished picture — tmp/canvas.png otherwise still holds
        # the pre-paint clear frame (paintings never push), so archived stills
        # copied from it would be black
        try:
            canvas.save_png(TMP / "canvas.png")
        except Exception:
            pass
    finally:
        spiral_state["running"] = False


def _painter_busy():
    task = spiral_state.get("task")
    return task and not task.done()


AGE_COLORS = [
    (140, 255, 205),   # newborn
    (80, 220, 170),
    (50, 170, 175),
    (45, 120, 185),
    (65, 75, 180),
    (95, 45, 150),     # elder
]


async def life_runner(delay: float, density: float):
    """Conway's Game of Life, streamed to the panel as it evolves.
    Torus wrap, cells colored by age, self-reseeding on stagnation."""
    import time as _t

    n = canvas.size
    rng = __import__("random").Random(int(_t.time()))

    def fresh_soup():
        return {(x, y) for y in range(n) for x in range(n) if rng.random() < density}

    def step(cells):
        counts = {}
        for (x, y) in cells:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx or dy:
                        k = ((x + dx) % n, (y + dy) % n)
                        counts[k] = counts.get(k, 0) + 1
        return {k for k, c in counts.items() if c == 3 or (c == 2 and k in cells)}

    cells = fresh_soup()
    ages = {c: 0 for c in cells}
    history, stagnant, gen = [], 0, 0
    spiral_state.update(running=True, total=0, delay=delay, index=0)
    log.info("life: starting, density %.2f, %.2fs/gen", density, delay)
    state["display_mode"] = "life"
    try:
        while spiral_state["running"]:
            # render generation onto the canvas
            img = canvas.img
            for y in range(n):
                for x in range(n):
                    if (x, y) in cells:
                        img.putpixel((x, y), AGE_COLORS[min(ages[(x, y)], len(AGE_COLORS) - 1)])
                    else:
                        img.putpixel((x, y), (3, 4, 8))
            if is_connected():
                try:
                    async with dev_lock:
                        await push_canvas_locked()
                    state["display_mode"] = "life"
                except Exception as e:
                    state["last_error"] = f"{type(e).__name__}: {e}"
                    try:
                        await cm.disconnect()
                    except Exception:
                        pass
                    cm.client = None
            spiral_state["index"] = gen

            # evolve
            new_cells = step(cells)
            ages = {c: (ages.get(c, -1) + 1) for c in new_cells}
            cells = new_cells
            gen += 1

            # stagnation / extinction -> reseed
            h = hash(frozenset(cells))
            if not cells or h in history:
                stagnant += 1
            else:
                stagnant = 0
            history = (history + [h])[-8:]
            if not cells or stagnant > 10:
                log.info("life: reseeding at generation %d", gen)
                cells = fresh_soup()
                ages = {c: 0 for c in cells}
                history, stagnant = [], 0
            await asyncio.sleep(delay)
        log.info("life: stopped at generation %d", gen)
    finally:
        spiral_state["running"] = False


@app.post("/life")
async def life(body: dict = Body(default={})):
    if _painter_busy():
        raise HTTPException(409, "a show is already running — POST /life/stop first")
    delay = max(0.3, float(body.get("delay", 0.5)))
    density = min(0.6, max(0.05, float(body.get("density", 0.28))))
    spiral_state["task"] = asyncio.create_task(life_runner(delay, density))
    return {"started": True, "delay": delay, "density": density}


@app.post("/life/stop")
async def life_stop():
    spiral_state["running"] = False
    return {"stopped": True, "generation": spiral_state["index"]}


SNAKE_HEAD = (230, 255, 235)
SNAKE_BODY = (40, 210, 90)
SNAKE_FOOD = (255, 45, 45)
SNAKE_BG = (2, 3, 8)


def _snake_frame(game) -> dict:
    """The lit cells for the current game state: {(x, y): (r, g, b)}."""
    cur: dict = {}
    if game.food is not None:
        cur[game.food] = SNAKE_FOOD
    for i, cell in enumerate(game.snake):
        cur[cell] = SNAKE_HEAD if i == 0 else SNAKE_BODY
    return cur


async def _push_clear(color="#020308"):
    """One authoritative black frame (a single image push). Used only at start
    and on the rare hard-reset — never per step — so it doesn't cause flashing."""
    canvas.apply_ops([{"op": "clear", "color": color}])
    if is_connected():
        try:
            async with dev_lock:
                await push_canvas_locked()
        except Exception:
            pass


async def snake_runner(delay: float):
    """Self-playing Snake (classic rules — walls and self are lethal). Renders by
    diffing frames and pushing only the ~3 changed pixels per move via Graffiti, so
    the panel is never full-refreshed mid-game (no flashing). A single black push
    handles the hard-reset blink on a crash."""
    import time as _t

    n = canvas.size
    game = SnakeGame(n, __import__("random").Random(int(_t.time())))
    spiral_state.update(running=True, total=0, delay=delay, index=0)
    state["display_mode"] = "snake"
    log.info("snake: starting, %.3fs/step on %dx%d", delay, n, n)

    await _push_clear()             # clean start (single push, not per-step)
    state["display_mode"] = "snake"
    prev: dict = {}
    try:
        while spiral_state["running"]:
            cur = _snake_frame(game)
            spiral_state["index"] = game.score
            for cell in list(prev):
                if cell not in cur:
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], SNAKE_BG)
            for cell, color in cur.items():
                if prev.get(cell) != color:
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], color)
            prev = cur

            game.step()
            if game.dead:
                log.info("snake: crash at length %d, score %d — hard reset",
                         len(game.snake), game.score)
                await asyncio.sleep(0.15)
                await _push_clear()      # instant hard-reset blink (one push)
                state["display_mode"] = "snake"
                game.reset()
                prev = {}
                await asyncio.sleep(0.1)
                continue
            if delay:
                await asyncio.sleep(delay)
        log.info("snake: stopped at score %d", spiral_state["index"])
    finally:
        spiral_state["running"] = False


@app.post("/snake")
async def snake(body: dict = Body(default={})):
    if _painter_busy():
        raise HTTPException(409, "a show is already running — stop it first")
    delay = max(0.0, float(body.get("delay", 0.05)))
    spiral_state["task"] = asyncio.create_task(snake_runner(delay))
    return {"started": True, "delay": delay}


@app.post("/snake/stop")
async def snake_stop():
    spiral_state["running"] = False
    return {"stopped": True, "score": spiral_state["index"]}


def _graffiti_cmd(r: int, g: int, b: int, x: int, y: int) -> bytearray:
    """The 10-byte Graffiti setPixel command (from idotmatrix Graffiti.setPixel)."""
    return bytearray([10, 0, 5, 1, 0, r % 256, g % 256, b % 256, x % 256, y % 256])


# Fire-and-forget writes are fast but drop pixels when fired back-to-back (→ stray
# dots). Acked writes don't drop but are ~6x slower. Pacing the fire-and-forget
# writes a few ms apart (like Lumen's paint engine) keeps them fast AND reliable.
GRAFFITI_PACE = 0.015


async def _graffiti_set(x: int, y: int, rgb) -> bool:
    """Set one pixel via Graffiti (no full-panel refresh → no flash), paced so the
    write actually lands. Returns False if the show was stopped while waiting."""
    while spiral_state["running"]:
        if is_connected():
            try:
                async with dev_lock:
                    await cm.send(_graffiti_cmd(rgb[0], rgb[1], rgb[2], x, y), response=False)
                canvas.img.putpixel((x, y), rgb)
                await asyncio.sleep(GRAFFITI_PACE)
                return True
            except Exception as e:
                state["last_error"] = f"{type(e).__name__}: {e}"
                try:
                    await cm.disconnect()
                except Exception:
                    pass
                cm.client = None
        await asyncio.sleep(1.0)
    return False


async def galaga_runner(delay: float):
    """Self-playing Galaga mock. Renders by diffing frames and pushing only the
    changed pixels via Graffiti — the panel is never full-refreshed, so it doesn't
    flash. See server/galaga.py."""
    import time as _t

    n = canvas.size
    game = Galaga(n, __import__("random").Random(int(_t.time())))
    spiral_state.update(running=True, total=0, delay=delay, index=0)
    state["display_mode"] = "galaga"
    log.info("galaga: starting, %.3fs/frame on %dx%d", delay, n, n)

    # one clean black frame to start (single image push; then pure Graffiti)
    canvas.apply_ops([{"op": "clear", "color": "#000000"}])
    if is_connected():
        try:
            async with dev_lock:
                await push_canvas_locked()
        except Exception:
            pass
    state["display_mode"] = "galaga"

    prev: dict = {}
    try:
        while spiral_state["running"]:
            cur = game.render()
            spiral_state["index"] = game.score
            # erase cells that went dark
            for cell in list(prev):
                if cell not in cur:
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], (0, 0, 0))
            # draw new / changed cells
            for cell, color in cur.items():
                if prev.get(cell) != color:
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], color)
            prev = cur

            if game.dead:
                log.info("galaga: game over — wave %d, score %d — resetting", game.wave, game.score)
                await asyncio.sleep(0.6)
                for cell in list(prev):        # graffiti-erase (no flash)
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], (0, 0, 0))
                prev = {}
                game.reset_all()
                continue

            game.step()
            if delay:
                await asyncio.sleep(delay)
        log.info("galaga: stopped at score %d", spiral_state["index"])
    finally:
        spiral_state["running"] = False


@app.post("/galaga")
async def galaga(body: dict = Body(default={})):
    if _painter_busy():
        raise HTTPException(409, "a show is already running — stop it first")
    delay = max(0.0, float(body.get("delay", 0.04)))
    spiral_state["task"] = asyncio.create_task(galaga_runner(delay))
    return {"started": True, "delay": delay}


@app.post("/galaga/stop")
async def galaga_stop():
    spiral_state["running"] = False
    return {"stopped": True, "score": spiral_state["index"]}


async def pacman_runner(delay: float):
    """Self-playing Pac-Man. Faithful maze + real ghost AI (see server/pacman.py).
    Renders by diffing frames and pushing only changed pixels via Graffiti, so the
    panel is never full-refreshed (no flashing). One black push on level reset."""
    import time as _t

    n = canvas.size
    game = PacMan(n, __import__("random").Random(int(_t.time())))
    spiral_state.update(running=True, total=0, delay=delay, index=0)
    state["display_mode"] = "pacman"
    log.info("pacman: starting, %.3fs/frame on %dx%d", delay, n, n)

    canvas.apply_ops([{"op": "clear", "color": "#000000"}])
    if is_connected():
        try:
            async with dev_lock:
                await push_canvas_locked()
        except Exception:
            pass
    state["display_mode"] = "pacman"

    prev: dict = {}
    try:
        while spiral_state["running"]:
            cur = game.render()
            spiral_state["index"] = game.score
            for cell in list(prev):                      # erase vacated cells
                if cur.get(cell) != prev[cell] and cell not in cur:
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], (0, 0, 0))
            for cell, color in cur.items():              # draw new / changed
                if prev.get(cell) != color:
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], color)
            prev = cur

            if game.dead:                                # level cleared / all lives lost
                log.info("pacman: round over — score %d — resetting", game.score)
                await asyncio.sleep(0.7)
                for cell in list(prev):
                    if not spiral_state["running"]:
                        break
                    await _graffiti_set(cell[0], cell[1], (0, 0, 0))
                prev = {}
                game.reset_all()
                continue

            game.step()
            if delay:
                await asyncio.sleep(delay)
        log.info("pacman: stopped at score %d", spiral_state["index"])
    finally:
        spiral_state["running"] = False


@app.post("/pacman")
async def pacman(body: dict = Body(default={})):
    if _painter_busy():
        raise HTTPException(409, "a show is already running — stop it first")
    delay = max(0.0, float(body.get("delay", 0.09)))
    spiral_state["task"] = asyncio.create_task(pacman_runner(delay))
    return {"started": True, "delay": delay}


@app.post("/pacman/stop")
async def pacman_stop():
    spiral_state["running"] = False
    return {"stopped": True, "score": spiral_state["index"]}


@app.post("/spiral")
async def spiral(body: dict = Body(default={})):
    if _painter_busy():
        raise HTTPException(409, "a painting is already in progress — POST /paint/stop first")
    delay = max(0.05, float(body.get("delay", 1.0)))
    start = max(0, int(body.get("start", 0)))
    coords = spiral_coords(canvas.size)
    n = len(coords)
    steps = [
        (x, y, tuple(round(c * 255) for c in colorsys.hsv_to_rgb(i / (n - 1), 1.0, 1.0)))
        for i, (x, y) in enumerate(coords)
    ][start:]
    spiral_state["task"] = asyncio.create_task(paint_runner(steps, delay, clear=(start == 0), label="spiral"))
    return {"started": True, "delay": delay, "total": len(steps), "eta_min": round(len(steps) * delay / 60, 1)}


def strokes_from_still(path: str, size: int):
    """Auto-choreograph a still image into a painterly stroke order:
    largest color regions first (background washes), then progressively
    smaller ones (subject, then details), serpentine within each region."""
    from PIL import Image as PilImage
    im = PilImage.open(path).convert("RGB")
    if im.size != (size, size):
        im = im.resize((size, size), PilImage.NEAREST)
    regions = {}
    for y in range(size):
        for x in range(size):
            regions.setdefault(im.getpixel((x, y)), []).append((x, y))
    steps = []
    for color, px in sorted(regions.items(), key=lambda kv: -len(kv[1])):
        px.sort(key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else size - p[0]))
        steps.extend((x, y, color) for x, y in px)
    return steps


@app.post("/paint")
async def paint(body: dict = Body(...)):
    """Live-paint: {pixels: [[x, y, color], ...]} for explicit choreography,
    OR {path: <still image>} to auto-choreograph it (washes -> details).
    delay?: seconds between strokes; clear?: start from black (default true).
    The stroke ORDER is the performance."""
    if _painter_busy():
        raise HTTPException(409, "a painting is already in progress — POST /paint/stop first")
    src = resolve_art(body.get("path")) if body.get("path") else None
    raw = body.get("pixels")
    if src:
        if not Path(src).exists():
            raise HTTPException(400, f"paint path not found: {src}")
        steps = strokes_from_still(str(src), canvas.size)
        state["now_playing"] = {"kind": "painting", "path": str(src), "name": Path(src).stem}
    elif isinstance(raw, list) and raw:
        steps = []
        try:
            for p in raw:
                x, y, c = int(p[0]), int(p[1]), parse_color(p[2])
                if not (0 <= x < canvas.size and 0 <= y < canvas.size):
                    raise ValueError(f"pixel out of bounds: {x},{y}")
                steps.append((x, y, c))
        except (ValueError, TypeError, IndexError, CanvasError) as e:
            raise HTTPException(400, f"bad pixel entry: {e}")
    else:
        raise HTTPException(400, "provide pixels: [[x, y, color], ...] or path: <still image>")
    delay = max(0.0, float(body.get("delay", 0.02)))
    spiral_state["task"] = asyncio.create_task(
        paint_runner(steps, delay, clear=bool(body.get("clear", True)), label="paint")
    )
    return {"started": True, "pixels": len(steps), "delay": delay,
            "eta_s": round(len(steps) * max(delay, 0.03), 1)}


@app.post("/paint/stop")
@app.post("/spiral/stop")
async def paint_stop():
    spiral_state["running"] = False
    return {"stopped": True, "at": spiral_state["index"]}


@app.post("/scan")
async def scan():
    devices = await BleakScanner.discover(timeout=6.0, return_adv=True)
    seen = []
    for _key, (device, adv) in devices.items():
        name = adv.local_name or device.name or ""
        if name:
            seen.append({"address": device.address, "name": name, "idm": name.upper().startswith("IDM")})
    return {"devices": sorted(seen, key=lambda d: not d["idm"])}


@app.put("/config")
async def put_config(body: dict = Body(...)):
    changed = {}
    if "size" in body:
        size = int(body["size"])
        if size not in (16, 32, 64):
            raise HTTPException(400, "size must be 16, 32 or 64")
        config["size"] = size
        canvas.resize(size)
        state["needs_push"] = True
        changed["size"] = size
    if "address" in body:
        config["address"] = body["address"] or None
        if cm.client:
            try:
                await cm.disconnect()
            except Exception:
                pass
            cm.client = None
        changed["address"] = config["address"]
    if changed:
        save_config()
    return {"changed": changed, "config": {k: config[k] for k in ("size", "address", "port")}}


PREVIEW_HTML = """<!doctype html>
<meta charset="utf-8"><title>Lumen</title>
<style>
 body{background:#0b0e14;color:#c8d3e0;font:14px/1.5 'Segoe UI',sans-serif;display:flex;flex-direction:column;align-items:center;gap:12px;padding-top:28px}
 img{image-rendering:pixelated;border:1px solid #223;border-radius:6px;background:#000}
 .row{display:flex;gap:14px;align-items:center}
 .dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px}
 .ok{background:#2ecc71}.bad{background:#e74c3c}
 code{color:#7aa2c9}
</style>
<h3 style="margin:0">Lumen <span style="color:#456">&mdash; LED wall preview</span></h3>
<img id="c" width="384" height="384">
<div class="row"><span id="conn"></span><span id="mode"></span><span id="err" style="color:#e74c3c"></span></div>
<script>
async function tick(){
  try{
    const s = await (await fetch('/status')).json();
    document.getElementById('conn').innerHTML = '<span class="dot '+(s.connected?'ok':'bad')+'"></span>'+(s.connected?'connected':'searching for panel...');
    document.getElementById('mode').innerHTML = 'mode: <code>'+s.display_mode+'</code> &middot; '+s.size+'&times;'+s.size;
    document.getElementById('err').textContent = s.connected||!s.last_error ? '' : s.last_error;
    document.getElementById('c').src = '/canvas.png?scale=8&t='+Date.now();
  }catch(e){ document.getElementById('conn').innerHTML = '<span class="dot bad"></span>daemon unreachable'; }
}
tick(); setInterval(tick, 1000);
</script>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return PREVIEW_HTML


# ---------- gallery web app (served UI — the desktop shell loads this) ----------

ART_DIR = ROOT / "art"
ART_IGNORE = ("strip", "preview", "frametest", "-1x", "icon", "mark-")


def resolve_art(path: str) -> str:
    """Bare filenames resolve against art/ so web clients needn't know disk paths."""
    p = Path(path)
    return str(p if p.is_absolute() else ART_DIR / path)


@app.get("/art")
async def art_list():
    """Sendable art pieces, newest first."""
    items = []
    if ART_DIR.exists():
        for p in list(ART_DIR.glob("*.png")) + list(ART_DIR.glob("*.gif")):
            stem = p.stem.lower()
            if stem == "koi-big" or any(s in stem for s in ART_IGNORE):
                continue
            items.append({
                "name": p.stem,
                "file": p.name,
                "medium": "loop" if p.suffix.lower() == ".gif" else "still",
                "mtime": p.stat().st_mtime,
            })
    items.sort(key=lambda i: i["mtime"], reverse=True)
    return {"items": items}


@app.get("/art/file/{filename}")
async def art_file(filename: str):
    from fastapi.responses import FileResponse
    p = (ART_DIR / filename).resolve()
    if p.parent != ART_DIR.resolve() or not p.exists() or p.suffix.lower() not in (".png", ".gif"):
        raise HTTPException(404, "no such art file")
    return FileResponse(p)


# ---------- the library: one curated catalog, from the ledger ----------
#
# art/DAILY.md is already a hand-curated list of every real piece, with its date,
# its medium and a description. The gallery used to ignore all of that and glob
# the directory, filtering with substring guesses ("strip", "preview", "-1x"),
# which is why eclipse-big and skein-big showed up as browsable "stills" next to
# the real pieces: a -big file is a 10x preview render, not art to send.
#
# So the ledger is the source of truth for what a piece IS, and the directory is
# consulted only for what is actually on disk. Anything on disk the ledger does
# not name is still reachable, grouped as "unlisted", so nothing silently
# disappears — but it does not clutter the gallery.

DAILY_MD = ART_DIR / "DAILY.md"

SHOWS = [
    {"id": "pacman", "name": "Pac-Man", "endpoint": "/pacman",
     "blurb": "arcade-faithful maze, real ghost AI"},
    {"id": "snake", "name": "Snake", "endpoint": "/snake", "blurb": "plays itself"},
    {"id": "galaga", "name": "Galaga", "endpoint": "/galaga", "blurb": "formation attack waves"},
    {"id": "life", "name": "Life", "endpoint": "/life",
     "blurb": "Conway, age-coloured, self-reseeding"},
    {"id": "spiral", "name": "Spectrum spiral", "endpoint": "/spiral",
     "blurb": "1,024 LEDs coiled inward"},
]

# Renders and scratch output that live in art/ but are not sendable pieces.
NOT_ART = ("strip", "preview", "frametest", "-1x", "-big", "icon", "mark-", "encoded")


def _gif_palette(p: Path) -> int | None:
    """Global colour table size, so the UI can show it (see gifsafe.MAX_COLORS)."""
    try:
        b = p.read_bytes()[:11]
        return 2 ** ((b[10] & 7) + 1) if len(b) >= 11 and b[10] & 0x80 else None
    except Exception:
        return None


def _ledger_rows():
    """(date, name, medium, description) for every row of the daily ledger."""
    rows = []
    if not DAILY_MD.exists():
        return rows
    for line in DAILY_MD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| 20"):
            continue
        cells = line.strip().strip("|").split("|", 3)
        if len(cells) < 4:
            continue
        rows.append(tuple(c.strip() for c in cells))
    return rows


def _piece(name, file: Path, medium, date="", description=""):
    st = file.stat()
    is_gif = file.suffix.lower() == ".gif"
    return {
        "id": file.stem,
        "name": name,
        "file": file.name,
        # what it IS in the ledger (loop / still / painting / simulation) vs how
        # it has to be DELIVERED — the two are not the same thing, and conflating
        # them is what sent every still down the broken /image path
        "medium": medium,
        "kind": "loop" if is_gif else "still",
        "transport": "gif" if is_gif else "paint",
        "date": date,
        "description": description,
        "bytes": st.st_size,
        "mtime": st.st_mtime,
        "palette": _gif_palette(file) if is_gif else None,
    }


@app.get("/library")
async def library():
    pieces, claimed = [], set()
    for date, name, medium, desc in _ledger_rows():
        for ext in (".gif", ".png"):
            f = ART_DIR / f"{name}{ext}"
            if f.exists():
                p = _piece(name, f, medium, date, desc)
                # A loop's <name>.png is its hero FRAME, not a second artwork.
                # Listing both is what put "eclipse LOOP" and "eclipse STILL"
                # side by side in the old grid looking like two pieces. It is
                # still sendable — as a companion of the one piece it belongs to.
                still = ART_DIR / f"{name}.png"
                if ext == ".gif" and still.exists():
                    p["companion"] = _piece(name, still, "still frame", date, "")
                    claimed.add(still.name)
                pieces.append(p)
                claimed.add(f.name)
                break
    pieces.sort(key=lambda p: (p["date"], p["mtime"]), reverse=True)

    unlisted = []
    if ART_DIR.exists():
        for f in sorted(list(ART_DIR.glob("*.png")) + list(ART_DIR.glob("*.gif"))):
            if f.name in claimed or any(s in f.stem.lower() for s in NOT_ART):
                continue
            unlisted.append(_piece(f.stem, f, "unlisted"))
        unlisted.sort(key=lambda p: p["mtime"], reverse=True)

    return {"pieces": pieces, "unlisted": unlisted, "shows": SHOWS,
            "max_palette": 64}


_STATIC = ROOT / "server" / "static" / "app"
if _STATIC.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC / "assets"), name="assets")


@app.get("/app", response_class=HTMLResponse)
async def gallery_app():
    """The React gallery (built to server/static/app), with the hand-written
    app.html kept as a fallback so the desktop shell still has a UI if the
    bundle has not been built on this machine."""
    built = ROOT / "server" / "static" / "app" / "index.html"
    if built.exists():
        return built.read_text(encoding="utf-8")
    page = ROOT / "server" / "app.html"
    if not page.exists():
        raise HTTPException(404, "no gallery UI built (run: cd app/gallery && npm run build)")
    return page.read_text(encoding="utf-8")
