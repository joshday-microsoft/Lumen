# Lumen Gallery

React + TypeScript UI for the LED wall. Built by Vite straight into
`server/static/app/`, served by the daemon at <http://127.0.0.1:7788/app>, and
wrapped by the Electron shell in `app/desktop` — so `npm run build` is the whole
deploy.

```bash
npm install
npm run build     # -> server/static/app, picked up by /app immediately
npm run dev       # hot reload on :5173, API proxied to the daemon on :7788
```

## How the library is organised

`GET /library` is the catalog, and `art/DAILY.md` is its source of truth. The
ledger already records every real piece with its date, medium and description,
so the gallery no longer globs the art directory and guesses with filename
substrings — that heuristic is what listed `eclipse-big` (a 10x preview render)
as browsable art, and showed `eclipse` twice, once as a LOOP and once as a
STILL.

- **pieces** — one entry per ledger row. A loop's `<name>.png` is attached as a
  `companion` (its hero frame), not listed as a second piece.
- **unlisted** — on disk but not in the ledger. Reachable under "Extras" so
  nothing silently disappears.
- **shows** — the daemon's self-driving modes (games, Life, spiral).

## The one rule worth keeping

**A piece's medium is not its transport.** The ledger calls something a "still"
or a "painting"; that says nothing about how it has to reach the panel. This
unit does not honour the PNG upload path (`/image`) — every write acks and
nothing renders — so stills go by `/paint` (per-pixel graffiti) and loops go by
`/gif`. The server decides that per piece (`transport`) and `api.ts#send()` is
the only way anything reaches the wall.

Both previous UIs made that decision at the button instead:

```js
endpoint = medium === "loop" ? "/gif" : "/image"   // tkinter app AND app.html
```

...so every still sent from either one silently did nothing.

GIF palettes are capped at 64 colours (`art/gifsafe.py`). Above that the panel
plays the file but scrambles the colours, so the gallery shows a piece's palette
size and flags anything oversized.
