import { useMemo, useState, useEffect } from "react";
import {
  removePiece,
  send,
  sendImage,
  sendText,
  setBrightness,
  setScreen,
  startShow,
  stopShow,
  type Piece,
} from "./api";
import { useLibrary, useStatus, useToasts } from "./hooks";
import { PieceCard, ShowCard, StatusPill, Toasts, WallMirror } from "./components";

/** The gallery's own organisation of the library — the "manage" part. */
type Filter = "all" | "loop" | "still" | "extras";

const TEXT_MODES: [string, number][] = [
  ["Marquee", 1],
  ["Static", 0],
  ["Blink", 5],
  ["Fade", 6],
  ["Tetris", 7],
  ["Filling", 8],
];

export default function App() {
  const { status, reachable } = useStatus();
  const { library, error, reload } = useLibrary();
  const { toasts, run } = useToasts();

  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Piece | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);

  // the live canvas mirror needs a cache-busting tick; GIF/label modes do not
  useEffect(() => {
    const t = window.setInterval(() => setTick((n) => n + 1), 1400);
    return () => window.clearInterval(t);
  }, []);

  const [text, setText] = useState("");
  const [color, setColor] = useState("#4db8ff");
  const [speed, setSpeed] = useState(50);
  const [mode, setMode] = useState(1);
  const [rainbow, setRainbow] = useState(false);
  const [bright, setBright] = useState(80);

  const shown = useMemo(() => {
    if (!library) return [];
    const pool =
      filter === "extras"
        ? library.unlisted
        : library.pieces.filter((p) => filter === "all" || p.kind === filter);
    const q = query.trim().toLowerCase();
    return q
      ? pool.filter(
          (p) => p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q)
        )
      : pool;
  }, [library, filter, query]);

  const counts = useMemo(
    () => ({
      all: library?.pieces.length ?? 0,
      loop: library?.pieces.filter((p) => p.kind === "loop").length ?? 0,
      still: library?.pieces.filter((p) => p.kind === "still").length ?? 0,
      extras: library?.unlisted.length ?? 0,
    }),
    [library]
  );

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    const ok = await run(label, fn);
    setBusy(false);
    return ok;
  };

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <span className="mark" />
          <h1>Lumen</h1>
          <span className="sub">Gallery</span>
        </div>
        <StatusPill status={status} reachable={reachable} />
      </header>

      <main className="body">
        <section className="left">
          <div className="toolbar">
            <div className="tabs">
              {(["all", "loop", "still", "extras"] as Filter[]).map((f) => (
                <button
                  key={f}
                  className={`tab${filter === f ? " on" : ""}`}
                  onClick={() => setFilter(f)}
                >
                  {f === "all" ? "Everything" : f === "extras" ? "Extras" : `${f}s`}
                  <span className="count">{counts[f]}</span>
                </button>
              ))}
            </div>
            <input
              className="search"
              placeholder="Search pieces…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          {error && (
            <div className="empty">
              Couldn&apos;t read the library: {error}
              <button className="btn ghost" onClick={reload}>
                Retry
              </button>
            </div>
          )}

          <div className="grid">
            {shown.map((p) => (
              <PieceCard
                key={p.file}
                piece={p}
                selected={selected?.file === p.file}
                onSelect={setSelected}
              />
            ))}
          </div>
          {!error && shown.length === 0 && (
            <div className="empty">{library ? "Nothing matches." : "Loading the library…"}</div>
          )}
        </section>

        <aside className="right">
          <h2>On the wall now</h2>
          <WallMirror status={status} tick={tick} />

          <h2>Selected</h2>
          {selected ? (
            <div className="sel-box">
              <div className="sel-name">{selected.name}</div>
              <div className="sel-sub">
                {selected.medium}
                {selected.date && ` · ${selected.date}`}
                {selected.palette && ` · ${selected.palette} colours`}
              </div>
              {selected.description && <p className="sel-desc">{selected.description}</p>}
              <button
                className="btn primary"
                disabled={busy || !status?.connected}
                onClick={() => act(`sent ${selected.name}`, () => send(selected))}
              >
                {selected.kind === "loop" ? "Play on the wall" : "Paint on the wall"}
              </button>
              {selected.kind === "still" && (
                <button
                  className="btn ghost"
                  disabled={busy || !status?.connected}
                  title="Instant, but this panel's image path is unreliable — if the wall goes blank, paint it instead"
                  onClick={() => act(`pushed ${selected.name}`, () => sendImage(selected))}
                >
                  Send image (instant)
                </button>
              )}
              {selected.companion && (
                <button
                  className="btn ghost"
                  disabled={busy || !status?.connected}
                  onClick={() =>
                    act(`painted ${selected.name} still`, () => send(selected.companion!))
                  }
                >
                  Paint its still frame
                </button>
              )}
              <button
                className="btn danger sm-inline"
                disabled={busy}
                onClick={async () => {
                  if (!confirm(`Move "${selected.name}" to art/.trash?\n\nThe generator script and its ledger row stay — only the image is removed.`))
                    return;
                  const ok = await act(`removed ${selected.name}`, () => removePiece(selected));
                  if (ok) {
                    setSelected(null);
                    reload();
                  }
                }}
              >
                Delete
              </button>
            </div>
          ) : (
            <div className="sel-box muted">Pick a piece from the gallery.</div>
          )}

          <h2>Shows</h2>
          <div className="shows">
            {library?.shows.map((s) => (
              <ShowCard
                key={s.id}
                show={s}
                onStart={(sh) => act(`${sh.name} playing`, () => startShow(sh))}
              />
            ))}
          </div>
          <button className="btn danger" disabled={busy} onClick={() => act("stopped", stopShow)}>
            ■ Stop show
          </button>

          <h2>Message</h2>
          <div className="row">
            <input
              className="search grow"
              placeholder="Scroll a message…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <input
              type="color"
              className="swatch"
              value={color}
              onChange={(e) => setColor(e.target.value)}
            />
          </div>
          <div className="row">
            <select value={mode} onChange={(e) => setMode(Number(e.target.value))}>
              {TEXT_MODES.map(([label, v]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
            <label className="chk">
              <input
                type="checkbox"
                checked={rainbow}
                onChange={(e) => setRainbow(e.target.checked)}
              />
              Rainbow
            </label>
            <button
              className="btn primary sm"
              disabled={busy || !text.trim()}
              onClick={() => act("message sent", () => sendText({ text, color, speed, mode, rainbow }))}
            >
              Send
            </button>
          </div>
          <label className="slider">
            Speed <span>{speed}</span>
            <input
              type="range"
              min={1}
              max={100}
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            />
          </label>

          <h2>Panel</h2>
          <label className="slider">
            Brightness <span>{bright}%</span>
            <input
              type="range"
              min={5}
              max={100}
              value={bright}
              onChange={(e) => setBright(Number(e.target.value))}
              onMouseUp={() => act(`brightness ${bright}%`, () => setBrightness(bright))}
              onTouchEnd={() => act(`brightness ${bright}%`, () => setBrightness(bright))}
            />
          </label>
          <div className="row">
            <button className="btn ghost" onClick={() => act("screen on", () => setScreen(true))}>
              Screen on
            </button>
            <button className="btn ghost" onClick={() => act("screen off", () => setScreen(false))}>
              Off
            </button>
          </div>
        </aside>
      </main>

      <Toasts toasts={toasts} />
    </div>
  );
}
