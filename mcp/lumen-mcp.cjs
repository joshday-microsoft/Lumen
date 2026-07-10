#!/usr/bin/env node
/**
 * Lumen MCP server — thin stdio JSON-RPC proxy to the Lumen daemon
 * (http://127.0.0.1:7788), which owns the BLE connection to the
 * iDotMatrix LED wall. Register once:
 *   claude mcp add --scope user lumen -- node C:\Users\JoshDay\source\repos\Lumen\mcp\lumen-mcp.cjs
 */
"use strict";

const BASE = process.env.LUMEN_URL || "http://127.0.0.1:7788";

const OPS_DOC =
  "Draw ops (JSON array). Coordinates are pixels, origin top-left, canvas is size x size (see lumen_status). " +
  "Colors: '#rrggbb', CSS names, or [r,g,b]. Ops: " +
  "{op:'clear',color?} | {op:'pixel',x,y,color} | {op:'line',x1,y1,x2,y2,color,width?} | " +
  "{op:'rect',x,y,w,h,fill?,outline?} | {op:'circle',cx,cy,r,fill?,outline?} | " +
  "{op:'ellipse',x,y,w,h,fill?,outline?} | {op:'polygon',points:[[x,y],..],fill?,outline?} | " +
  "{op:'text',text,x?,y?,color?,scale?,align?:'center'} (3x5 pixel font, ~4px/char; \\n for new lines) | " +
  "{op:'image',path?|b64?,x?,y?,w?,h?} (no x/y/w/h = fit whole canvas). " +
  "The canvas persists between calls — draw incrementally, or start with a clear op.";

const TOOLS = [
  {
    name: "lumen_status",
    description: "Status of the LED wall: connected?, panel size, current display mode, last error.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "lumen_draw",
    description: "Draw on the LED wall canvas and push it to the panel. " + OPS_DOC,
    inputSchema: {
      type: "object",
      properties: {
        ops: { type: "array", description: "array of draw op objects (see tool description)" },
        push: { type: "boolean", description: "push to panel after drawing (default true)" },
      },
      required: ["ops"],
    },
  },
  {
    name: "lumen_canvas",
    description: "See the current canvas as an image (what the panel is showing in canvas mode). Use this to check your work after drawing.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "lumen_clear",
    description: "Clear the LED wall canvas to a color (default black) and push.",
    inputSchema: { type: "object", properties: { color: { type: "string" } } },
  },
  {
    name: "lumen_text",
    description: "Scroll a text message across the LED wall (device-side smooth marquee — good for longer messages; for short static text prefer lumen_draw with a text op). Leaves canvas mode.",
    inputSchema: {
      type: "object",
      properties: {
        text: { type: "string" },
        color: { type: "string", description: "'#rrggbb' or CSS name (default white)" },
        speed: { type: "number", description: "0-100, default 95" },
        rainbow: { type: "boolean" },
        mode: { type: "number", description: "0 static, 1 marquee (default), 5 blink, 6 fade, 7 tetris, 8 filling" },
      },
      required: ["text"],
    },
  },
  {
    name: "lumen_notify",
    description: "Communicate with Josh via the LED wall: scroll a message, then automatically restore the canvas after `seconds` (default 12). Use for alerts, status updates, greetings.",
    inputSchema: {
      type: "object",
      properties: {
        text: { type: "string" },
        color: { type: "string" },
        seconds: { type: "number", description: "how long before restoring the canvas (default 12)" },
      },
      required: ["text"],
    },
  },
  {
    name: "lumen_image",
    description: "Show an image file (PNG/JPG) on the LED wall — fitted to the panel, centered. Pass an absolute path.",
    inputSchema: {
      type: "object",
      properties: { path: { type: "string" } },
      required: ["path"],
    },
  },
  {
    name: "lumen_gif",
    description: "Play an animated GIF on the LED wall (absolute path). Short loops work best over BLE.",
    inputSchema: {
      type: "object",
      properties: { path: { type: "string" } },
      required: ["path"],
    },
  },
  {
    name: "lumen_clock",
    description: "Switch the LED wall to clock mode.",
    inputSchema: {
      type: "object",
      properties: {
        style: { type: "number", description: "clock face style 0-7 (default 0)" },
        color: { type: "string" },
      },
    },
  },
  {
    name: "lumen_color",
    description: "Fill the whole LED wall with one color (mood light).",
    inputSchema: {
      type: "object",
      properties: { color: { type: "string" } },
      required: ["color"],
    },
  },
  {
    name: "lumen_brightness",
    description: "Set LED wall brightness, 5-100 percent.",
    inputSchema: {
      type: "object",
      properties: { percent: { type: "number" } },
      required: ["percent"],
    },
  },
  {
    name: "lumen_screen",
    description: "Turn the LED wall screen on or off.",
    inputSchema: {
      type: "object",
      properties: { on: { type: "boolean" } },
      required: ["on"],
    },
  },
  {
    name: "lumen_config",
    description: "Get/set panel config. Set size (16/32/64) if rendering looks wrong, or clear the saved BLE address to re-scan.",
    inputSchema: {
      type: "object",
      properties: {
        size: { type: "number" },
        address: { type: "string", description: "BLE MAC, or empty string to forget and re-scan" },
      },
    },
  },
];

async function api(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if (!res.ok) throw new Error(`${res.status}: ${data.detail || text}`);
  return data;
}

function colorArg(c) {
  return c === undefined ? undefined : c;
}

async function callTool(name, args) {
  args = args || {};
  switch (name) {
    case "lumen_status":
      return json(await api("GET", "/status"));
    case "lumen_draw": {
      const r = await api("POST", "/draw", { ops: args.ops, push: args.push !== false });
      return json(r);
    }
    case "lumen_canvas": {
      const res = await fetch(BASE + "/canvas.png?scale=8");
      if (!res.ok) throw new Error("canvas fetch failed: " + res.status);
      const buf = Buffer.from(await res.arrayBuffer());
      return {
        content: [
          { type: "image", data: buf.toString("base64"), mimeType: "image/png" },
        ],
      };
    }
    case "lumen_clear":
      return json(await api("POST", "/clear", { color: colorArg(args.color) }));
    case "lumen_text":
      return json(await api("POST", "/text", args));
    case "lumen_notify":
      return json(await api("POST", "/notify", args));
    case "lumen_image":
      return json(await api("POST", "/image", { path: args.path }));
    case "lumen_gif":
      return json(await api("POST", "/gif", { path: args.path }));
    case "lumen_clock":
      return json(await api("POST", "/clock", args));
    case "lumen_color":
      return json(await api("POST", "/color", { color: args.color }));
    case "lumen_brightness":
      return json(await api("POST", "/brightness", { percent: args.percent }));
    case "lumen_screen":
      return json(await api("POST", "/screen", { on: args.on }));
    case "lumen_config":
      if (args.size === undefined && args.address === undefined) return json(await api("GET", "/status"));
      return json(await api("PUT", "/config", args));
    default:
      throw new Error("unknown tool: " + name);
  }
}

function json(obj) {
  return { content: [{ type: "text", text: JSON.stringify(obj) }] };
}

// ---- minimal stdio JSON-RPC ----

let buffer = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  let idx;
  while ((idx = buffer.indexOf("\n")) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (line) handle(line);
  }
});

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

async function handle(line) {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  const { id, method, params } = msg;
  try {
    if (method === "initialize") {
      send({
        jsonrpc: "2.0", id,
        result: {
          protocolVersion: params?.protocolVersion || "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: { name: "lumen", version: "1.0.0" },
        },
      });
    } else if (method === "notifications/initialized" || method === "initialized") {
      // notification, no reply
    } else if (method === "tools/list") {
      send({ jsonrpc: "2.0", id, result: { tools: TOOLS } });
    } else if (method === "tools/call") {
      try {
        const result = await callTool(params.name, params.arguments);
        send({ jsonrpc: "2.0", id, result });
      } catch (e) {
        const hint = /ECONNREFUSED|fetch failed/i.test(String(e))
          ? " — Lumen daemon not running. Start it: powershell C:\\Users\\JoshDay\\source\\repos\\Lumen\\start-lumen.ps1"
          : "";
        send({
          jsonrpc: "2.0", id,
          result: { content: [{ type: "text", text: "error: " + e.message + hint }], isError: true },
        });
      }
    } else if (id !== undefined) {
      send({ jsonrpc: "2.0", id, error: { code: -32601, message: "method not found: " + method } });
    }
  } catch (e) {
    if (id !== undefined) send({ jsonrpc: "2.0", id, error: { code: -32000, message: String(e) } });
  }
}
