"""Lumen Gallery — a Windows desktop app to browse the created art and send
any piece straight to the LED wall.

Reads the repo's art/ folder directly (so new daily pieces appear on relaunch),
renders a live thumbnail grid, mirrors what's currently on the panel, and sends
the selected image (still -> /image, GIF loop -> /gif) to the Lumen daemon.

Runs windowless via pythonw; launched from the Desktop shortcut created by
install-shortcut.ps1. Pure stdlib + Pillow (already in the venv) — no installs.
"""

import io
import json
import queue
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import font as tkfont

from PIL import Image, ImageTk

DAEMON = "http://127.0.0.1:7788"


def _resource(name):
    """A bundled resource, whether running as a script or a PyInstaller exe."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / name          # noqa: SLF001  (PyInstaller temp dir)
    return Path(__file__).resolve().parent / name


def _find_root():
    """Locate the Lumen repo (holds art/ + server/) from the script or exe."""
    starts = []
    if getattr(sys, "frozen", False):
        starts.append(Path(sys.executable).resolve().parent)
    starts.append(Path(__file__).resolve().parent)
    for start in starts:
        p = start
        for _ in range(6):
            if (p / "art").is_dir() and (p / "server").is_dir():
                return p
            p = p.parent
    return Path(r"C:\Users\JoshDay\source\repos\Lumen")   # known-good fallback


ROOT = _find_root()
ART = ROOT / "art"
ICON = _resource("icon.ico")

THUMB = 104
WALL_PX = 116
COLS = 3

# self-playing shows the daemon can run (start endpoint per label)
GAMES = [("Pac-Man", "/pacman"), ("Snake", "/snake"),
         ("Galaga", "/galaga"), ("Life", "/life")]

# non-art helpers living in art/ that shouldn't show in the gallery
IGNORE_SUBSTR = ("strip", "preview", "frametest", "-1x", "icon", "mark-")
IGNORE_STEM = {"koi-big"}

# palette
BG = "#0b0e14"
PANEL = "#121722"
CARD = "#161d2b"
CARD_HI = "#1d2637"
ACCENT = "#4db8ff"
GREEN = "#2ecc71"
TEXT = "#cdd8e6"
MUTED = "#6b7a90"
DANGER = "#e7614c"


# ---------- data ----------

def discover():
    """Return sendable art files, newest first: [(path, medium)]."""
    if not ART.exists():
        return []
    out = []
    for p in list(ART.glob("*.png")) + list(ART.glob("*.gif")):
        stem = p.stem.lower()
        if stem in IGNORE_STEM or any(s in stem for s in IGNORE_SUBSTR):
            continue
        out.append(p)
    out.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p, "LOOP" if p.suffix.lower() == ".gif" else "STILL") for p in out]


def make_thumb(path: Path, size: int) -> ImageTk.PhotoImage:
    im = Image.open(path)
    try:
        im.seek(0)  # first frame for GIFs
    except (EOFError, ValueError):
        pass
    im = im.convert("RGB")
    if im.size != (32, 32):                       # normalize to native 32
        im = im.resize((32, 32), Image.LANCZOS)
    im = im.resize((size, size), Image.NEAREST)   # crisp pixel upscale
    return ImageTk.PhotoImage(im)


# ---------- networking (background thread -> queue) ----------

def http_json(method, path, payload=None, timeout=8):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(DAEMON + path, data=data, method=method,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def http_bytes(path, timeout=8):
    with urllib.request.urlopen(DAEMON + path, timeout=timeout) as r:
        return r.read()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.q = queue.Queue()
        self.selected = None            # (path, medium)
        self.cards = {}                 # path -> card frame
        self._thumb_refs = []           # keep PhotoImage refs alive
        self._wall_img = None
        self._wall_src = None           # what the mirror currently shows (dedupe)
        self._sel_img = None
        self.sending = False

        root.title("Lumen Gallery")
        root.configure(bg=BG)
        root.geometry("760x716")
        root.minsize(680, 640)
        try:
            root.iconbitmap(default=str(ICON))
        except Exception:
            pass

        self.f_title = tkfont.Font(family="Segoe UI Semibold", size=15)
        self.f_h = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.f = tkfont.Font(family="Segoe UI", size=9)
        self.f_small = tkfont.Font(family="Segoe UI", size=8)
        self.f_btn = tkfont.Font(family="Segoe UI Semibold", size=11)

        # imageless tk.Labels treat width/height as CHARACTERS/LINES, which
        # blows the placeholder tiles up and pushes the sidebar off-window —
        # give both tiles a real black image so dimensions stay pixels
        self._blank = ImageTk.PhotoImage(Image.new("RGB", (WALL_PX, WALL_PX), (0, 0, 0)))

        self._build_header()
        self._build_body()
        self._load_gallery()

        # background poller + UI drain loop
        threading.Thread(target=self._poll_loop, daemon=True).start()
        self.root.after(120, self._drain)

    # ---------- UI construction ----------
    def _build_header(self):
        h = tk.Frame(self.root, bg=BG)
        h.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(h, text="■ LUMEN", font=self.f_title, fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(h, text="  Gallery", font=self.f_title, fg=MUTED, bg=BG).pack(side="left")

        status = tk.Frame(h, bg=BG)
        status.pack(side="right")
        self.dot = tk.Canvas(status, width=12, height=12, bg=BG, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 6))
        self._dot_id = self.dot.create_oval(2, 2, 11, 11, fill=DANGER, outline="")
        self.status_lbl = tk.Label(status, text="connecting…", font=self.f, fg=MUTED, bg=BG)
        self.status_lbl.pack(side="left")

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # --- left column: gallery (scrollable) + send-text bar ---
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        gal = tk.Frame(left, bg=PANEL, highlightthickness=1, highlightbackground="#20293a")
        gal.pack(side="top", fill="both", expand=True)
        self.canvas = tk.Canvas(gal, bg=PANEL, highlightthickness=0)
        vs = tk.Scrollbar(gal, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grid = tk.Frame(self.canvas, bg=PANEL)
        self._grid_win = self.canvas.create_window((0, 0), window=self.grid, anchor="nw")
        self.grid.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._grid_win, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

        # --- send text to wall (with styling) ---
        tp = tk.Frame(left, bg=PANEL, highlightthickness=1, highlightbackground="#20293a")
        tp.pack(side="bottom", fill="x", pady=(10, 0))
        tk.Label(tp, text="SEND TEXT", font=self.f_small, fg=MUTED, bg=PANEL).pack(anchor="w", padx=10, pady=(8, 2))
        erow = tk.Frame(tp, bg=PANEL)
        erow.pack(fill="x", padx=10)
        self.text_entry = tk.Entry(erow, font=self.f, bg=CARD, fg=TEXT, relief="flat",
                                   insertbackground=TEXT, highlightthickness=1,
                                   highlightbackground="#22304a", highlightcolor=ACCENT)
        self.text_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.text_entry.bind("<Return>", lambda e: self._send_text())
        tk.Button(erow, text="Send Text", font=self.f, fg="#062033", bg=ACCENT,
                  activebackground="#79cbff", activeforeground="#062033", relief="flat",
                  bd=0, cursor="hand2", command=self._send_text
                  ).pack(side="left", padx=(8, 0), ipady=4, ipadx=8)

        crow = tk.Frame(tp, bg=PANEL)
        crow.pack(fill="x", padx=10, pady=(6, 10))
        self.text_color = "#4db8ff"
        self.color_btn = tk.Button(crow, text="  ", bg=self.text_color, relief="flat", bd=0,
                                   cursor="hand2", width=3, command=self._pick_text_color)
        self.color_btn.pack(side="left")
        self.rainbow_var = tk.BooleanVar(value=False)
        tk.Checkbutton(crow, text="Rainbow", variable=self.rainbow_var, font=self.f_small,
                       fg=TEXT, bg=PANEL, activebackground=PANEL, activeforeground=TEXT,
                       selectcolor=CARD, cursor="hand2").pack(side="left", padx=(10, 0))
        self.text_mode = tk.StringVar(value="Marquee")
        om = tk.OptionMenu(crow, self.text_mode, "Marquee", "Static", "Blink",
                           "Fade", "Tetris", "Filling")
        om.configure(font=self.f_small, fg=TEXT, bg=CARD, activebackground=CARD_HI,
                     activeforeground=TEXT, relief="flat", bd=0, highlightthickness=0,
                     cursor="hand2", indicatoron=False, padx=10, pady=3)
        om["menu"].configure(font=self.f_small, fg=TEXT, bg=CARD,
                             activebackground=ACCENT, activeforeground="#062033")
        om.pack(side="left", padx=(10, 0))
        tk.Label(crow, text="speed", font=self.f_small, fg=MUTED, bg=PANEL).pack(side="left", padx=(12, 4))
        self.text_speed = tk.Scale(crow, from_=40, to=100, orient="horizontal", showvalue=False,
                                   bg=PANEL, troughcolor="#1b2333", highlightthickness=0,
                                   activebackground=ACCENT, bd=0, length=90)
        self.text_speed.set(95)
        self.text_speed.pack(side="left")

        # --- sidebar ---
        side = tk.Frame(body, bg=BG, width=232)
        side.pack(side="right", fill="y", padx=(14, 0))
        side.pack_propagate(False)

        tk.Label(side, text="ON THE WALL NOW", font=self.f_small, fg=MUTED, bg=BG).pack(anchor="w")
        self.wall_lbl = tk.Label(side, image=self._blank, compound="center", text="",
                                 fg=MUTED, font=self.f_small, bg="#000000",
                                 width=WALL_PX, height=WALL_PX,
                                 highlightthickness=1, highlightbackground="#22304a")
        self.wall_lbl.pack(pady=(4, 14))

        tk.Frame(side, height=1, bg="#20293a").pack(fill="x", pady=(0, 12))

        tk.Label(side, text="SELECTED", font=self.f_small, fg=MUTED, bg=BG).pack(anchor="w")
        self.sel_name = tk.Label(side, text="— pick a piece —", font=self.f_h, fg=TEXT, bg=BG)
        self.sel_name.pack(anchor="w", pady=(1, 4))
        self.sel_lbl = tk.Label(side, image=self._blank, compound="center", text="",
                                bg="#000000", width=WALL_PX, height=WALL_PX,
                                highlightthickness=1, highlightbackground="#22304a")
        self.sel_lbl.pack(pady=(0, 12))

        self.send_btn = tk.Button(side, text="Send to Wall", font=self.f_btn, fg="#062033",
                                  bg=ACCENT, activebackground="#79cbff", activeforeground="#062033",
                                  relief="flat", bd=0, cursor="hand2", state="disabled",
                                  command=self._send_selected)
        self.send_btn.pack(fill="x", ipady=7, pady=(0, 6))

        # live-paint a still, stroke by stroke (the wall's party trick)
        self.paint_btn = tk.Button(side, text="🖌  Paint to Wall", font=self.f, fg="#dff0d8",
                                   bg="#1d3a29", activebackground=GREEN, activeforeground="#04150b",
                                   relief="flat", bd=0, cursor="hand2", state="disabled",
                                   command=self._paint_selected)
        self.paint_btn.pack(fill="x", ipady=5, pady=(0, 12))

        # games / self-playing shows
        tk.Label(side, text="PLAY A SHOW", font=self.f_small, fg=MUTED, bg=BG).pack(anchor="w", pady=(0, 3))
        gwrap = tk.Frame(side, bg=BG)
        gwrap.pack(fill="x")
        gwrap.columnconfigure(0, weight=1)
        gwrap.columnconfigure(1, weight=1)
        for i, (label, ep) in enumerate(GAMES):
            tk.Button(gwrap, text=label, font=self.f, fg=TEXT, bg=CARD,
                      activebackground=ACCENT, activeforeground="#062033", relief="flat",
                      bd=0, cursor="hand2",
                      command=lambda e=ep, l=label: self._start_game(e, l)
                      ).grid(row=i // 2, column=i % 2, sticky="nsew", padx=2, pady=2, ipady=4)
        tk.Button(side, text="■  Stop show", font=self.f, fg="#f0c4bb", bg="#3a1f1f",
                  activebackground=DANGER, activeforeground="#ffffff", relief="flat", bd=0,
                  cursor="hand2", command=self._stop_show).pack(fill="x", pady=(4, 14), ipady=3)

        # brightness
        br = tk.Frame(side, bg=BG)
        br.pack(fill="x")
        tk.Label(br, text="BRIGHTNESS", font=self.f_small, fg=MUTED, bg=BG).pack(side="left")
        self.br_val = tk.Label(br, text="", font=self.f_small, fg=MUTED, bg=BG)
        self.br_val.pack(side="right")
        self.bright = tk.Scale(side, from_=5, to=100, orient="horizontal", showvalue=False,
                               bg=BG, fg=TEXT, troughcolor="#1b2333", highlightthickness=0,
                               activebackground=ACCENT, bd=0, command=self._on_bright_move)
        self.bright.set(80)
        self.bright.pack(fill="x")
        self.bright.bind("<ButtonRelease-1>", self._apply_bright)

        # screen on/off
        row = tk.Frame(side, bg=BG)
        row.pack(fill="x", pady=(12, 0))
        self._mk_ghost(row, "Screen On", lambda: self._screen(True)).pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._mk_ghost(row, "Off", lambda: self._screen(False)).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.toast = tk.Label(side, text="", font=self.f_small, fg=MUTED, bg=BG,
                              wraplength=210, justify="left", anchor="w")
        self.toast.pack(fill="x", pady=(14, 0), side="bottom")

    def _mk_ghost(self, parent, text, cmd):
        return tk.Button(parent, text=text, font=self.f, fg=TEXT, bg=CARD,
                         activebackground=CARD_HI, activeforeground=TEXT, relief="flat",
                         bd=0, cursor="hand2", command=cmd)

    # ---------- gallery ----------
    def _load_gallery(self):
        for w in self.grid.winfo_children():
            w.destroy()
        self.cards.clear()
        self._thumb_refs.clear()
        items = discover()
        if not items:
            tk.Label(self.grid, text="No art found in\n" + str(ART), font=self.f,
                     fg=MUTED, bg=PANEL, justify="center").pack(padx=30, pady=30)
            return
        for c in range(COLS):
            self.grid.columnconfigure(c, weight=1)
        for i, (path, medium) in enumerate(items):
            self._add_card(path, medium, i // COLS, i % COLS)

    def _add_card(self, path: Path, medium: str, r: int, c: int):
        try:
            thumb = make_thumb(path, THUMB)
        except Exception as e:
            return
        self._thumb_refs.append(thumb)
        card = tk.Frame(self.grid, bg=CARD, highlightthickness=2, highlightbackground=CARD,
                        cursor="hand2")
        card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
        img = tk.Label(card, image=thumb, bg=CARD, bd=0)
        img.pack(padx=8, pady=(8, 4))
        name = tk.Label(card, text=path.stem, font=self.f, fg=TEXT, bg=CARD)
        name.pack()
        badge_fg = GREEN if medium == "LOOP" else ACCENT
        tk.Label(card, text=medium, font=self.f_small, fg=badge_fg, bg=CARD).pack(pady=(0, 8))

        for w in (card, img, name):
            w.bind("<Button-1>", lambda e, p=path, m=medium: self._select(p, m))
            w.bind("<Double-Button-1>", lambda e, p=path, m=medium: (self._select(p, m), self._send_selected()))
            w.bind("<Enter>", lambda e, cc=card: self._hover(cc, True))
            w.bind("<Leave>", lambda e, cc=card: self._hover(cc, False))
        self.cards[path] = card

    def _hover(self, card, on):
        if self.selected and self.cards.get(self.selected[0]) is card:
            return
        bg = CARD_HI if on else CARD
        card.configure(bg=bg)
        for w in card.winfo_children():
            w.configure(bg=bg)

    def _select(self, path, medium):
        # reset previous
        if self.selected and self.selected[0] in self.cards:
            prev = self.cards[self.selected[0]]
            prev.configure(highlightbackground=CARD, bg=CARD)
            for w in prev.winfo_children():
                w.configure(bg=CARD)
        self.selected = (path, medium)
        card = self.cards[path]
        card.configure(highlightbackground=ACCENT, bg=CARD_HI)
        for w in card.winfo_children():
            w.configure(bg=CARD_HI)
        self.sel_name.configure(text=path.stem)
        try:
            self._sel_img = make_thumb(path, WALL_PX)
            self.sel_lbl.configure(image=self._sel_img, width=WALL_PX, height=WALL_PX)
        except Exception:
            pass
        self.send_btn.configure(state="normal")
        # painting replays stills stroke-by-stroke; loops play device-side
        self.paint_btn.configure(state="normal" if medium == "STILL" else "disabled")

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    # ---------- actions ----------
    def _set_toast(self, text, color=MUTED):
        self.toast.configure(text=text, fg=color)

    def _send_selected(self):
        if not self.selected or self.sending:
            return
        path, medium = self.selected
        self.sending = True
        self.send_btn.configure(state="disabled", text="Sending…")
        self._set_toast(f"Sending {path.stem} to the wall…", ACCENT)
        endpoint = "/gif" if medium == "LOOP" else "/image"

        def work():
            try:
                try:                                   # stop any running show so the image sticks
                    http_json("POST", "/paint/stop")
                    time.sleep(0.35)
                except Exception:
                    pass
                http_json("POST", endpoint, {"path": str(path)}, timeout=90)
                self.q.put(("sent", (path.stem, True, "")))
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:160]
                self.q.put(("sent", (path.stem, False, msg)))
            except Exception as e:
                self.q.put(("sent", (path.stem, False, str(e)[:160])))

        threading.Thread(target=work, daemon=True).start()

    TEXT_MODES = {"Marquee": 1, "Static": 0, "Blink": 5, "Fade": 6, "Tetris": 7, "Filling": 8}

    def _pick_text_color(self):
        from tkinter import colorchooser
        rgb, hexval = colorchooser.askcolor(initialcolor=self.text_color, parent=self.root,
                                            title="Text color")
        if hexval:
            self.text_color = hexval
            self.color_btn.configure(bg=hexval)

    def _send_text(self):
        msg = self.text_entry.get().strip()
        if not msg:
            self._set_toast("type a message first", MUTED)
            return
        payload = {"text": msg, "color": self.text_color,
                   "speed": int(self.text_speed.get()),
                   "mode": self.TEXT_MODES.get(self.text_mode.get(), 1),
                   "rainbow": bool(self.rainbow_var.get())}
        self._set_toast(f"sending text to the wall…", ACCENT)

        def work():
            try:
                http_json("POST", "/paint/stop")       # free the wall from any show
                time.sleep(0.35)
            except Exception:
                pass
            try:
                http_json("POST", "/text", payload, timeout=30)
                self.q.put(("toast", (f"✓ text on the wall ({self.text_mode.get().lower()})", GREEN)))
            except urllib.error.HTTPError as e:
                self.q.put(("toast", (f"✗ text: {e.read().decode()[:100]}", DANGER)))
            except Exception as e:
                self.q.put(("toast", (f"✗ text: {str(e)[:100]}", DANGER)))

        threading.Thread(target=work, daemon=True).start()

    def _paint_selected(self):
        if not self.selected:
            return
        path, medium = self.selected
        if medium != "STILL":
            return
        self._set_toast(f"🖌 painting {path.stem} live on the wall…", ACCENT)

        def work():
            try:
                http_json("POST", "/paint/stop")
                time.sleep(0.35)
            except Exception:
                pass
            for _ in range(8):
                try:
                    r = http_json("POST", "/paint", {"path": str(path), "delay": 0.015})
                    eta = int(r.get("eta_s", 0))
                    self.q.put(("toast", (f"🖌 painting {path.stem} — watch the wall (~{eta}s)", GREEN)))
                    return
                except urllib.error.HTTPError as e:
                    if e.code == 409:
                        time.sleep(0.35)
                        continue
                    self.q.put(("toast", (f"✗ paint: {e.read().decode()[:100]}", DANGER)))
                    return
                except Exception as e:
                    self.q.put(("toast", (f"✗ paint: {str(e)[:100]}", DANGER)))
                    return
            self.q.put(("toast", ("✗ paint: wall still busy", DANGER)))

        threading.Thread(target=work, daemon=True).start()

    def _on_bright_move(self, v):
        self.br_val.configure(text=f"{int(float(v))}%")

    def _apply_bright(self, _e):
        pct = int(self.bright.get())
        threading.Thread(target=lambda: self._fire("/brightness", {"percent": pct},
                         f"brightness {pct}%"), daemon=True).start()

    def _screen(self, on):
        threading.Thread(target=lambda: self._fire("/screen", {"on": on},
                         "screen on" if on else "screen off"), daemon=True).start()

    def _fire(self, endpoint, payload, label):
        try:
            http_json("POST", endpoint, payload)
            self.q.put(("toast", (f"✓ {label}", GREEN)))
        except Exception as e:
            self.q.put(("toast", (f"✗ {label}: {str(e)[:120]}", DANGER)))

    def _start_game(self, endpoint, label):
        self._set_toast(f"Starting {label}…", ACCENT)

        def work():
            try:                                       # clear any running show first
                http_json("POST", "/paint/stop")
            except Exception:
                pass
            for _ in range(8):                         # then start, retrying while it frees
                try:
                    http_json("POST", endpoint, {})
                    self.q.put(("toast", (f"▶ {label} playing on the wall", GREEN)))
                    return
                except urllib.error.HTTPError as e:
                    if e.code == 409:
                        time.sleep(0.35)
                        continue
                    self.q.put(("toast", (f"✗ {label}: {e.read().decode()[:100]}", DANGER)))
                    return
                except Exception as e:
                    self.q.put(("toast", (f"✗ {label}: {str(e)[:100]}", DANGER)))
                    return
            self.q.put(("toast", (f"✗ {label}: show still busy", DANGER)))

        threading.Thread(target=work, daemon=True).start()

    def _stop_show(self):
        logo = ART / "daylabs-mark-32.png"

        def work():
            try:
                http_json("POST", "/paint/stop")
                time.sleep(0.3)
            except Exception:
                pass
            if logo.exists():                          # return to the Day Labs default
                try:
                    http_json("POST", "/image", {"path": str(logo)})
                    self.q.put(("toast", ("✓ stopped — back to Day Labs", GREEN)))
                    return
                except Exception as e:
                    self.q.put(("toast", (f"✗ stop: {str(e)[:100]}", DANGER)))
                    return
            self.q.put(("toast", ("✓ stopped the show", GREEN)))

        threading.Thread(target=work, daemon=True).start()

    # ---------- polling ----------
    def _poll_loop(self):
        while True:
            try:
                s = http_json("GET", "/status", timeout=4)
                self.q.put(("status", s))
                mode = s.get("display_mode")
                if mode == "gif":
                    # the canvas doesn't mirror device-side GIFs — render the
                    # actual file the daemon says is playing (now_playing)
                    np = s.get("now_playing") or {}
                    self.q.put(("wallfile", np.get("path")))
                elif mode in ("text", "clock", "color", "off"):
                    self.q.put(("wallmode", mode))
                else:                                  # canvas/graffiti/games mirror live
                    try:
                        self.q.put(("wall", http_bytes("/canvas.png?scale=4", timeout=4)))
                    except Exception:
                        pass
            except Exception:
                self.q.put(("status", None))
            time.sleep(1.4)

    def _drain(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "status":
                    self._apply_status(data)
                elif kind == "wall":
                    self._apply_wall(data)
                elif kind == "wallfile":
                    self._apply_wallfile(data)
                elif kind == "wallmode":
                    self._apply_wallmode(data)
                elif kind == "sent":
                    stem, ok, msg = data
                    self.sending = False
                    self.send_btn.configure(state="normal", text="Send to Wall")
                    if ok:
                        self._set_toast(f"✓ {stem} is on the wall", GREEN)
                    else:
                        self._set_toast(f"✗ couldn't send: {msg}", DANGER)
                elif kind == "toast":
                    text, color = data
                    self._set_toast(text, color)
        except queue.Empty:
            pass
        self.root.after(140, self._drain)

    def _apply_status(self, s):
        if not s:
            self.dot.itemconfig(self._dot_id, fill=DANGER)
            self.status_lbl.configure(text="daemon offline", fg=MUTED)
            return
        if s.get("connected"):
            self.dot.itemconfig(self._dot_id, fill=GREEN)
            mode = s.get("display_mode", "?")
            self.status_lbl.configure(text=f"connected · {mode}", fg=TEXT)
        else:
            self.dot.itemconfig(self._dot_id, fill="#e0a52e")
            self.status_lbl.configure(text="searching for panel…", fg=MUTED)

    def _apply_wall(self, png_bytes):
        try:
            im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            if im.size != (32, 32):
                im = im.resize((32, 32), Image.LANCZOS)
            im = im.resize((WALL_PX, WALL_PX), Image.NEAREST)
            self._wall_img = ImageTk.PhotoImage(im)
            self.wall_lbl.configure(image=self._wall_img, text="",
                                    width=WALL_PX, height=WALL_PX)
            self._wall_src = "canvas"
        except Exception:
            pass

    def _apply_wallfile(self, path):
        """GIF mode: mirror the file the daemon says is playing (first frame)."""
        if not path:
            self._apply_wallmode("loop playing")
            return
        if self._wall_src == path:                     # already showing it
            return
        try:
            self._wall_img = make_thumb(Path(path), WALL_PX)
            self.wall_lbl.configure(image=self._wall_img, text="",
                                    width=WALL_PX, height=WALL_PX)
            self._wall_src = path
        except Exception:
            self._apply_wallmode("loop playing")

    def _apply_wallmode(self, label):
        """Modes with nothing to mirror (text/clock/color) get a labeled tile."""
        key = f"mode:{label}"
        if self._wall_src == key:
            return
        self.wall_lbl.configure(image=self._blank, text=label, fg=MUTED,
                                width=WALL_PX, height=WALL_PX)
        self._wall_src = key


def main():
    # proper taskbar grouping + icon on Windows
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("JoshDay.Lumen.Gallery")
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
