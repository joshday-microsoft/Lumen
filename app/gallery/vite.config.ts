import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built straight into the daemon's static dir: the daemon serves the bundle at
// /app, and the Electron shell (app/desktop) already points there — so a build
// is the whole deploy. In dev, proxy the API to the running daemon so `npm run
// dev` works against the real panel.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: { outDir: "../../server/static/app", emptyOutDir: true },
  server: {
    proxy: Object.fromEntries(
      ["/library", "/status", "/canvas.png", "/art", "/gif", "/image", "/paint",
       "/text", "/brightness", "/screen", "/pacman", "/snake", "/galaga", "/life",
       "/spiral", "/clock", "/color", "/draw", "/clear", "/push", "/notify"]
        .map((p) => [p, { target: "http://127.0.0.1:7788", changeOrigin: true }])
    ),
  },
});
