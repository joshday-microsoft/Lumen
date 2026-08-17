import { artUrl, type Piece, type Show, type Status } from "./api";
import type { Toast } from "./hooks";

/** 32x32 art, upscaled with hard pixel edges — never smoothed. */
export function Pixels({ file, size, alt }: { file: string; size: number; alt: string }) {
  return (
    <img
      src={artUrl(file)}
      alt={alt}
      width={size}
      height={size}
      style={{ width: size, height: size, imageRendering: "pixelated", display: "block" }}
    />
  );
}

export function StatusPill({ status, reachable }: { status: Status | null; reachable: boolean }) {
  const [tone, label] = !reachable
    ? ["off", "daemon offline"]
    : !status?.connected
      ? ["warn", status?.scanning ? "searching for panel…" : "panel disconnected"]
      : ["ok", `connected · ${status.display_mode}`];
  return (
    <span className="pill">
      <span className={`dot ${tone}`} />
      {label}
    </span>
  );
}

export function PieceCard({
  piece,
  selected,
  onSelect,
}: {
  piece: Piece;
  selected: boolean;
  onSelect: (p: Piece) => void;
}) {
  const oversized = piece.palette !== null && piece.palette > 64;
  return (
    <button
      className={`card${selected ? " sel" : ""}`}
      onClick={() => onSelect(piece)}
      title={piece.description || piece.name}
    >
      <Pixels file={piece.file} size={96} alt={piece.name} />
      <span className="card-name">{piece.name}</span>
      <span className="card-meta">
        <span className={`tag ${piece.kind}`}>{piece.medium}</span>
        {piece.date && <span className="date">{piece.date.slice(5)}</span>}
      </span>
      {/* the fault that broke four loops, made visible instead of invisible */}
      {oversized && <span className="warn-flag">{piece.palette} colours</span>}
    </button>
  );
}

export function ShowCard({ show, onStart }: { show: Show; onStart: (s: Show) => void }) {
  return (
    <button className="show" onClick={() => onStart(show)}>
      <span className="show-name">{show.name}</span>
      <span className="show-blurb">{show.blurb}</span>
    </button>
  );
}

/**
 * What is on the wall right now.
 *
 * GIF playback has no canvas mirror on this panel, so in gif mode the daemon's
 * now_playing file is shown instead of the (stale) canvas — and modes with
 * nothing to mirror at all get an honest label rather than a misleading image.
 */
export function WallMirror({ status, tick }: { status: Status | null; tick: number }) {
  const mode = status?.display_mode;
  let body: React.ReactNode;

  if (!status?.connected) {
    body = <div className="wall-label">no panel</div>;
  } else if (mode === "gif" && status.now_playing) {
    const file = status.now_playing.path.split(/[\\/]/).pop()!;
    body = <Pixels file={file} size={132} alt={status.now_playing.name} />;
  } else if (mode && ["text", "clock", "color", "off"].includes(mode)) {
    body = <div className="wall-label">{mode === "off" ? "screen off" : `${mode} mode`}</div>;
  } else {
    body = (
      <img
        src={`/canvas.png?scale=4&t=${tick}`}
        alt="the wall"
        width={132}
        height={132}
        style={{ width: 132, height: 132, imageRendering: "pixelated", display: "block" }}
      />
    );
  }

  return (
    <div className="wall">
      <div className="wall-frame">{body}</div>
      {mode === "gif" && status?.now_playing && (
        <div className="wall-cap">{status.now_playing.name} · looping</div>
      )}
    </div>
  );
}

export function Toasts({ toasts }: { toasts: Toast[] }) {
  return (
    <div className="toasts">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.tone}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
}
