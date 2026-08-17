/**
 * The whole surface the gallery has on the daemon, in one typed place.
 *
 * The single most important thing in this file is `send()`. The old app decided
 * how to deliver a piece at the call site:
 *
 *     endpoint = medium === "loop" ? "/gif" : "/image"
 *
 * ...and `/image` is the one path this panel does not honour — every write acks,
 * nothing renders. That line existed in the tkinter app AND in app.html, so
 * every still sent from either UI silently did nothing. Delivery is not a
 * decision a button should be making: the server already says how each piece has
 * to travel (`transport`), and `send()` is the only way to put anything on the
 * wall.
 */

export type Transport = "gif" | "paint";

export interface Piece {
  id: string;
  name: string;
  file: string;
  medium: string; // what the ledger calls it: loop / still / painting / simulation
  kind: "loop" | "still";
  transport: Transport; // how it must be DELIVERED — not the same question
  date: string;
  description: string;
  bytes: number;
  mtime: number;
  palette: number | null; // GIF global colour table size
  companion?: Piece; // a loop's hero still frame
}

export interface Show {
  id: string;
  name: string;
  endpoint: string;
  blurb: string;
}

export interface Library {
  pieces: Piece[];
  unlisted: Piece[];
  shows: Show[];
  max_palette: number;
}

export interface Status {
  connected: boolean;
  display_mode: string;
  now_playing: { kind: string; path: string; name: string } | null;
  scanning: boolean;
  last_error: string | null;
}

export class ApiError extends Error {}

async function req<T>(method: string, path: string, body?: unknown, timeoutMs = 15000): Promise<T> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(path, {
      method,
      signal: ctl.signal,
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await r.text();
    if (!r.ok) {
      let detail = text.slice(0, 200);
      try {
        detail = JSON.parse(text).detail ?? detail;
      } catch {
        /* plain-text error */
      }
      throw new ApiError(detail);
    }
    return (text ? JSON.parse(text) : {}) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") throw new ApiError("timed out");
    throw new ApiError(e instanceof Error ? e.message : String(e));
  } finally {
    clearTimeout(timer);
  }
}

export const getLibrary = () => req<Library>("GET", "/library");
export const getStatus = () => req<Status>("GET", "/status", undefined, 5000);

/** Free the wall from a painting or a self-driving show before taking it over. */
async function clearWall() {
  try {
    await req("POST", "/paint/stop");
    await new Promise((r) => setTimeout(r, 350));
  } catch {
    /* nothing was running */
  }
}

/**
 * Retry through 409s. Every takeover races whatever the wall was already doing,
 * and the daemon answers 409 while a painter is still winding down — the old
 * app open-coded this loop three separate times, once per button.
 */
async function takeover<T>(fn: () => Promise<T>, tries = 8): Promise<T> {
  for (let i = 0; ; i++) {
    try {
      return await fn();
    } catch (e) {
      const busy = e instanceof ApiError && /409|in progress|busy/i.test(e.message);
      if (!busy || i >= tries - 1) throw e;
      await new Promise((r) => setTimeout(r, 350));
    }
  }
}

/** Put a piece on the wall. The ONLY way anything gets displayed. */
export async function send(piece: Piece): Promise<void> {
  await clearWall();
  await takeover(() =>
    piece.transport === "gif"
      ? req("POST", "/gif", { path: piece.file }, 90000)
      : req("POST", "/paint", { path: piece.file, delay: 0.015 }, 90000)
  );
}

/**
 * Push a still as a single image upload instead of painting it stroke by
 * stroke. Instant rather than ~30s — but this is the panel's DIY image path,
 * which this unit has failed on repeatedly (2026-07-15 and 2026-08-05): every
 * write acks and nothing renders. Kept because it is genuinely the fast way
 * and it does work on a good day; the UI labels it as the unreliable one so a
 * blank wall reads as "that path again" rather than a mystery.
 */
export async function sendImage(piece: Piece): Promise<void> {
  await clearWall();
  await takeover(() => req("POST", "/image", { path: piece.file }, 60000));
}

/** Move a piece to art/.trash (recoverable), then the caller reloads. */
export const removePiece = (piece: Piece) =>
  req<{ moved_to: string }>("DELETE", `/library/${encodeURIComponent(piece.file)}`);

export async function startShow(show: Show): Promise<void> {
  await clearWall();
  await takeover(() => req("POST", show.endpoint, {}));
}

export async function stopShow(): Promise<void> {
  await clearWall();
  // back to the Day Labs mark — via /paint, because /image renders blank here
  await takeover(() => req("POST", "/paint", { path: "daylabs-mark-32.png", delay: 0.008 }, 60000));
}

export interface TextOptions {
  text: string;
  color: string;
  speed: number;
  mode: number;
  rainbow: boolean;
}
export const sendText = (o: TextOptions) => req("POST", "/text", o);
export const setBrightness = (percent: number) => req("POST", "/brightness", { percent });
export const setScreen = (on: boolean) => req("POST", "/screen", { on });

export const artUrl = (file: string) => `/art/file/${encodeURIComponent(file)}`;
