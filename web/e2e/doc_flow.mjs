import { launch } from "./cdp.mjs";
import fs from "node:fs";
const text = fs.readFileSync("/home/oriol/Documents/propre/api/tests/fixtures/rapport_brut.txt", "utf8");
const p = await launch({ width: 390, height: 844 });
const click = (label) => p.eval(`(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.textContent.includes(${JSON.stringify(label)})); if(!b) throw new Error('no ' + ${JSON.stringify(label)}); b.click(); return true; })()`);
await p.goto("http://localhost:3000/document", 5000);
await p.eval(`localStorage.clear()`);
await p.goto("http://localhost:3000/document", 4000);
await p.shot("f1-import.png");
await click("Coller le texte");
await p.sleep(300);
// set the textarea value the React way
await p.eval(`(() => { const ta=document.querySelector('textarea'); const set=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set; set.call(ta, ${JSON.stringify(text)}); ta.dispatchEvent(new Event('input',{bubbles:true})); })()`);
await p.sleep(300);
await click("Continuer");
await p.sleep(1500);
await click("C'est bon");
await p.sleep(700);
await p.shot("f2-working.png");
for (let i=0;i<40;i++){ if (await p.eval(`document.body.innerText.includes('pages au propre')`)) break; await p.sleep(500); }
await p.sleep(1500);
await p.shot("f3-editor.png");
console.log("url", await p.eval("location.href"));
await click("Style");
await p.sleep(600);
await p.shot("f4-style.png");
await click("Moderne");
await p.sleep(400);
await p.eval(`document.querySelector('[aria-label="Fermer"]').click()`);
for (let i=0;i<40;i++){ await p.sleep(500); if (!(await p.eval(`document.body.innerText.includes('Mise à jour de la mise en page')`)) ) { const op = await p.eval(`getComputedStyle([...document.querySelectorAll('span')].find(s=>s.textContent.includes('Mise à jour'))).opacity`); if (op === '0') break; } }
await p.sleep(1500);
await p.shot("f5-moderne.png");
await click("Plan");
await p.sleep(600);
await p.shot("f6-plan.png");
await p.eval(`document.querySelector('[aria-label="Fermer"]').click()`);
await click("Télécharger");
await p.sleep(600);
await p.eval(`(() => { const i=document.querySelector('input[inputmode=tel]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'670000000'); i.dispatchEvent(new Event('input',{bubbles:true})); })()`);
await p.sleep(300);
await p.shot("f7-pay.png");
await click("Payer");
await p.sleep(1500);
await p.shot("f8-pending.png");
for (let i=0;i<20;i++){ if (await p.eval(`document.body.innerText.includes('Télécharge ton fichier')`)) break; await p.sleep(1000); }
await p.shot("f9-paid.png");
const hrefs = await p.eval(`[...document.querySelectorAll('a')].map(a=>a.href).filter(h=>h.includes('/file.'))`);
console.log(hrefs);
for (const h of hrefs) { const r = await fetch(h); console.log(h.split('/').pop(), r.status, r.headers.get('content-type'), (await r.arrayBuffer()).byteLength); }
p.close();
