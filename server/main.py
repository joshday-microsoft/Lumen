"""Lumen daemon — owns the BLE connection to the iDotMatrix panel and
exposes a localhost HTTP API for drawing and communication.

Run:  .venv\\Scripts\\python.exe -m uvicorn server.main:app --port 7788 --app-dir <repo root>
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from bleak import BleakScanner
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from idotmatrix import (
    Clock as IdmClock,
    Common as IdmCommon,
    ConnectionManager,
    FullscreenColor,
    Gif as IdmGif,
    Image as IdmImage,
    Text as IdmText,
)

from .canvas import Canvas, CanvasError, parse_color

log = logging.getLogger("lumen")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)

DEFAULT_SCROLL_FONT = r"C:\Windows\Fonts\arialbd.ttf"


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


async def push_canvas_locked():
    """Push the current canvas to the panel. Caller must hold dev_lock."""
    path = TMP / "canvas.png"
    canvas.save_png(path)
    await IdmImage().setMode(1)
    await IdmImage().uploadProcessed(str(path), pixel_size=canvas.size)
    state["display_mode"] = "canvas"
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


async def on_connected():
    state["connected_since"] = time.time()
    state["last_error"] = None
    async with dev_lock:
        try:
            now = datetime.now()
            await IdmCommon().setTime(now.year, now.month, now.day, now.hour, now.minute, now.second)
        except Exception as e:
            log.warning("setTime failed (non-fatal): %s", e)
        await push_canvas_locked()
    log.info("connected to %s, canvas pushed", cm.address)


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
    # boot splash on the canvas so the first connect shows something
    if all(p == (0, 0, 0) for p in canvas.img.getdata()):
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
    try:
        canvas.apply_ops([{"op": "image", **{k: v for k, v in body.items() if k in ("path", "b64", "x", "y", "w", "h")}}])
    except CanvasError as e:
        raise HTTPException(400, str(e))
    pushed = False
    if is_connected():
        await device_call(push_canvas_locked)
        pushed = True
    else:
        state["needs_push"] = True
    return {"pushed": pushed}


@app.post("/gif")
async def gif(body: dict = Body(...)):
    path = body.get("path")
    if not path or not Path(path).exists():
        raise HTTPException(400, f"gif path not found: {path}")

    async def _send():
        await IdmGif().uploadProcessed(str(path), pixel_size=canvas.size)

    await device_call(_send, mode="gif")
    state["needs_push"] = True
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
