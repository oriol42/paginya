import { launch } from "./cdp.mjs";
import fs from "node:fs";
const p = await launch({ width: 1280, height: 900 });
await p.goto("http://localhost:3000/outils/video", 6000);
await p.eval(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Générer')).click()`);
const snaps = [1.5, 5, 9, 13.5];
let t0 = Date.now(); let waitedPrep = false;
// wait until recording starts
for (let i = 0; i < 60; i++) { const s = await p.eval(`document.body.innerText.includes('Enregistrement')`); if (s) break; await p.sleep(250); }
t0 = Date.now();
for (const s of snaps) {
  await p.sleep(Math.max(0, s * 1000 - (Date.now() - t0)));
  const data = await p.eval(`document.querySelector('canvas').toDataURL('image/jpeg', .6)`);
  fs.writeFileSync(`frame-${s}.jpg`, Buffer.from(data.split(',')[1], 'base64'));
}
for (let i = 0; i < 40; i++) { if (await p.eval(`!!document.querySelector('a[download]')`)) break; await p.sleep(500); }
const info = await p.eval(`(async () => { const a = document.querySelector('a[download]'); const b = await (await fetch(a.href)).blob(); const buf = new Uint8Array(await b.arrayBuffer()); let s=''; for (let i=0;i<buf.length;i+=32768) s+=String.fromCharCode(...buf.subarray(i,i+32768)); return {name:a.download, type:b.type, size:b.size, data:btoa(s)}; })()`);
fs.writeFileSync(info.name, Buffer.from(info.data, "base64"));
console.log(info.name, info.type, info.size);
p.close();
