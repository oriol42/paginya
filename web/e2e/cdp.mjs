// Minimal Chrome DevTools Protocol driver (Node 24 has a global WebSocket).
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export async function launch({ width = 390, height = 844, port = 9333 } = {}) {
  const dir = mkdtempSync(join(process.env.SCRATCH ?? tmpdir(), "chrome-"));
  const proc = spawn("google-chrome", ["--headless=new", "--no-sandbox", "--disable-gpu", `--remote-debugging-port=${port}`,
    `--user-data-dir=${dir}`, `--window-size=${width},${height}`, "--autoplay-policy=no-user-gesture-required", "about:blank"], { stdio: "ignore" });
  let target;
  for (let i = 0; i < 50 && !target; i++) {
    await new Promise((r) => setTimeout(r, 200));
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {}
  }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0; const waiting = new Map();
  ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } });
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiting.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Page.enable"); await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 600 });
  const page = {
    send,
    goto: async (url, wait = 4000) => { await send("Page.navigate", { url }); await new Promise((r) => setTimeout(r, wait)); },
    eval: async (expr) => { const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails)); return r.result?.result?.value; },
    shot: async (path, full = false) => {
      const fs = await import("node:fs");
      const r = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: full });
      fs.writeFileSync(path, Buffer.from(r.result.data, "base64"));
    },
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
    close: () => { ws.close(); proc.kill(); },
  };
  return page;
}
