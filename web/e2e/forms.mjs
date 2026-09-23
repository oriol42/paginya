import { launch } from "./cdp.mjs";
// Letter + exam pages: fill a few fields, wait for the real render, screenshot (desktop).
const p = await launch({ width: 1400, height: 1000 });
const type = (sel, v) => p.eval(`(() => { const el=document.querySelector(${JSON.stringify(sel)}); const proto = el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('input',{bubbles:true})); })()`);
const idle = async () => { await p.sleep(1500); for (let i=0;i<40;i++){ const busy = await p.eval(`[...document.querySelectorAll('span')].some(s=>s.textContent.includes('Mise à jour') && getComputedStyle(s).opacity==='1')`); if(!busy) break; await p.sleep(400);} await p.sleep(1200); };
await p.goto("http://localhost:3000/lettre", 3000);
await p.eval("localStorage.clear()"); await p.goto("http://localhost:3000/lettre", 3000);
await type('input[placeholder="MBALLA Junior"]', "NGONO Marie");
await type('input[placeholder="de ENEO Cameroun"]', "de ORANGE Cameroun");
await type('input[placeholder="Douala"]', "Douala");
await idle(); await p.shot("f-lettre.png");
await p.goto("http://localhost:3000/epreuve", 3000);
await type('input[placeholder="Lycée de Biyem-Assi"]', "Lycée Bilingue d'Essos");
await type('input[placeholder="Mathématiques"]', "Mathématiques");
await type('input[placeholder="Terminale C"]', "Terminale D");
await idle(); await p.shot("f-epreuve.png");
p.close();
