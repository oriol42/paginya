import { launch } from "./cdp.mjs";
import fs from "node:fs";
const text = fs.readFileSync("/home/oriol/Documents/propre/api/tests/fixtures/rapport_brut.txt", "utf8");
const p = await launch({ width: 390, height: 844 });
const click = (label) => p.eval(`(() => { const b=[...document.querySelectorAll('button,a,label')].find(x=>x.textContent.includes(${JSON.stringify(label)})); if(!b) throw new Error('no '+${JSON.stringify(label)}); b.click(); })()`);
const type = (sel, v) => p.eval(`(() => { const el=document.querySelector(${JSON.stringify(sel)}); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('input',{bubbles:true})); })()`);
await p.goto("http://localhost:3000/document", 3000);
await p.eval("localStorage.clear()");
await p.goto("http://localhost:3000/document", 3000);
// Photos flow
await click("Photos"); await p.sleep(400);
const docNode = await p.send("DOM.getDocument", {});
const input = await p.send("DOM.querySelector", { nodeId: docNode.result.root.nodeId, selector: 'input[type=file][capture]' });
await p.send("DOM.setFileInputFiles", { nodeId: input.result.nodeId, files: [process.cwd() + "/photo.jpg", process.cwd() + "/photo.jpg"] });
await p.sleep(800);
await p.shot("m1-photos.png");
await p.eval(`document.querySelector('input[type=checkbox]').click()`);
await click("Lire 2 pages");
for (let i=0;i<30;i++){ if (await p.eval(`document.body.innerText.includes('Vérifie le texte lu')`)) break; await p.sleep(500); }
await p.sleep(800);
await p.shot("m2-review.png");
// Text flow + drawer
await p.goto("http://localhost:3000/document", 2000);
await p.eval("localStorage.clear()");
await p.goto("http://localhost:3000/document", 3000);
await click("Texte"); await p.sleep(300);
await type("textarea", text);
await click("Continuer");
await p.sleep(1500);
await click("C'est bon");
for (let i=0;i<60;i++){ if (await p.eval(`document.body.innerText.includes('Ce que Propre a fait')`)) break; await p.sleep(500); }
await p.sleep(2500);
await p.shot("m3-editor.png");
await click("🎨 Style"); await p.sleep(800);
await p.shot("m4-drawer.png");
p.close();
