// Lumen Gallery desktop shell (same-UI local twin pattern, like brain-web):
// a thin Electron window around the daemon-served web app at :7788/app.
// If the daemon isn't up yet, shows a holding card and retries until it is.
const { app, BrowserWindow } = require("electron");
const path = require("path");

const APP_URL = "http://127.0.0.1:7788/app";
const HOLDING = "data:text/html;charset=utf-8," + encodeURIComponent(`
  <body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
               background:#05080F;color:#5C6678;font:13px 'Segoe UI',sans-serif">
    <div style="text-align:center">
      <div style="width:12px;height:12px;background:#2E7BE8;border-radius:2px;margin:0 auto 14px"></div>
      waiting for the Lumen daemon&hellip;
    </div>
  </body>`);

let win;

function load() {
  win.loadURL(APP_URL).catch(() => {
    win.loadURL(HOLDING).catch(() => {});
    setTimeout(load, 1500);
  });
}

function create() {
  win = new BrowserWindow({
    width: 1120,
    height: 780,
    minWidth: 900,
    minHeight: 640,
    backgroundColor: "#05080F",
    autoHideMenuBar: true,
    icon: path.join(__dirname, "icon.ico"),
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  win.webContents.on("did-fail-load", () => {
    win.loadURL(HOLDING).catch(() => {});
    setTimeout(load, 1500);
  });
  load();
}

const got = app.requestSingleInstanceLock();
if (!got) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
  app.whenReady().then(create);
  app.on("window-all-closed", () => app.quit());
}
