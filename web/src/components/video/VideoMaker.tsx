"use client";

import { useEffect, useRef, useState } from "react";
import { loadCoverFonts, renderCover } from "@/lib/cover";
import { emptyForm } from "@/lib/cover/kinds";
import { PALETTES } from "@/lib/cover/palettes";
import type { CoverForm, StyleId } from "@/lib/cover/types";
import { INSTITUTIONS, institution } from "@/lib/institutions";
import { Field, Input, Segmented, Select } from "../ui";

const W = 1080;
const H = 1920;
const FPS = 30;
const DURATION = 15; // seconds

// Fonts must be embedded for SVG drawn as an image on a canvas.
const FONT_FILES: [string, number, string, string][] = [
  ["Poppins", 400, "normal", "poppins-Regular.ttf"],
  ["Poppins", 600, "normal", "poppins-SemiBold.ttf"],
  ["Poppins", 800, "normal", "poppins-ExtraBold.ttf"],
  ["Tinos", 400, "normal", "tinos-400.ttf"],
  ["Tinos", 700, "normal", "tinos-700.ttf"],
  ["Tinos", 400, "italic", "tinos-400-italic.ttf"],
  ["Playfair Display", 400, "normal", "playfair-display-400.ttf"],
  ["Playfair Display", 700, "normal", "playfair-display-700.ttf"],
  ["Playfair Display", 400, "italic", "playfair-display-400-italic.ttf"],
  ["Inter", 400, "normal", "inter-400.ttf"],
  ["Inter", 600, "normal", "inter-600.ttf"],
];

let fontCss: Promise<string> | null = null;
function embeddedFonts(): Promise<string> {
  fontCss ??= Promise.all(
    FONT_FILES.map(async ([family, weight, style, file]) => {
      const buf = await (await fetch(`/fonts/${file}`)).arrayBuffer();
      let bin = "";
      new Uint8Array(buf).forEach((b) => (bin += String.fromCharCode(b)));
      return `@font-face{font-family:"${family}";font-weight:${weight};font-style:${style};src:url(data:font/ttf;base64,${btoa(bin)}) format("truetype");}`;
    }),
  ).then((rules) => rules.join(""));
  return fontCss;
}

async function svgImage(svg: string): Promise<HTMLImageElement> {
  const css = await embeddedFonts();
  const withFonts = svg.replace(/^<svg([^>]*)>/, `<svg$1><style>${css}</style>`);
  const img = new Image();
  img.src = URL.createObjectURL(new Blob([withFonts], { type: "image/svg+xml" }));
  await img.decode();
  return img;
}

const ease = (t: number) => 1 - Math.pow(1 - Math.min(Math.max(t, 0), 1), 3);

function drawCover(ctx: CanvasRenderingContext2D, img: HTMLImageElement, cx: number, cy: number, w: number, rot = 0, alpha = 1) {
  const h = w * (842 / 595);
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(cx, cy);
  ctx.rotate(rot);
  ctx.shadowColor = "rgba(2,44,34,.35)";
  ctx.shadowBlur = 60;
  ctx.shadowOffsetY = 24;
  ctx.fillStyle = "#fff";
  ctx.fillRect(-w / 2, -h / 2, w, h);
  ctx.shadowColor = "transparent";
  ctx.drawImage(img, -w / 2, -h / 2, w, h);
  ctx.restore();
}

function text(ctx: CanvasRenderingContext2D, lines: string[], x: number, y: number, size: number, color: string, weight = 800, lh = 1.12) {
  ctx.font = `${weight} ${size}px Poppins`;
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  lines.forEach((l, i) => ctx.fillText(l, x, y + i * size * lh));
}

type Assets = { typing: HTMLImageElement[]; styles: HTMLImageElement[]; icon: HTMLImageElement };

export function VideoMaker() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [instId, setInstId] = useState("uy2-esstic");
  const [title, setTitle] = useState("Gestion électronique des archives d'une microfinance");
  const [name, setName] = useState("NGNICHANG Honorine");
  const [hook, setHook] = useState("Ta page de garde|en 30 secondes ⏱️");
  const [cta, setCta] = useState("paginya.com");
  const [status, setStatus] = useState<"idle" | "prep" | "rec" | "done">("idle");
  const [video, setVideo] = useState<{ url: string; ext: string } | null>(null);
  const assets = useRef<Assets | null>(null);
  const frame = useRef(0);

  async function prepare(): Promise<Assets> {
    await loadCoverFonts();
    const inst = institution(instId);
    const base: CoverForm = {
      ...emptyForm("rapport_stage"),
      institutionId: inst.id,
      headerFr: inst.fr.join("\n"),
      headerEn: inst.en.join("\n"),
      title,
      authors: [{ name, info: "Licence 3" }],
      structure: "ADVANS Cameroun",
      period: "du 4 juillet au 4 octobre 2026",
      degree: "Licence professionnelle",
      date: "Novembre 2026",
    };
    const steps = 18;
    const typing = await Promise.all(
      Array.from({ length: steps + 1 }, (_, i) =>
        svgImage(renderCover({ ...base, title: title.slice(0, Math.round((title.length * i) / steps)) || " " }, "officiel", { palette: PALETTES[0], mono: false, frame: true }, false)),
      ),
    );
    const combos: [StyleId, number][] = [["moderne", 0], ["corporate", 1], ["minimal", 2], ["moderne", 3], ["officiel", 1], ["corporate", 4]];
    const styles = await Promise.all(
      combos.map(([s, p]) => svgImage(renderCover({ ...base, kind: s === "corporate" ? "rapport_stage" : base.kind }, s, { palette: PALETTES[p], mono: false, frame: true }, false))),
    );
    const icon = new Image();
    icon.src = "/icon.svg";
    await icon.decode();
    return { typing, styles, icon };
  }

  function draw(t: number) {
    const ctx = canvas.current?.getContext("2d");
    const a = assets.current;
    if (!ctx || !a) return;
    // background
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, "#ECFDF5");
    g.addColorStop(1, "#A7F3D0");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "rgba(14,159,110,.10)";
    ctx.beginPath(); ctx.arc(W * 0.9, H * 0.12, 320, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(W * 0.05, H * 0.9, 280, 0, Math.PI * 2); ctx.fill();

    const [l1, l2] = hook.split("|");
    if (t < 2.6) {
      // 1. Hook
      const k = ease(t / 0.6);
      ctx.save();
      ctx.translate(W / 2, H / 2 - 120);
      ctx.scale(0.8 + 0.2 * k, 0.8 + 0.2 * k);
      ctx.globalAlpha = k;
      text(ctx, [l1 ?? ""], 0, 0, 104, "#0F172A");
      text(ctx, [l2 ?? ""], 0, 130, 104, "#0E9F6E");
      ctx.restore();
      ctx.globalAlpha = ease((t - 0.9) / 0.5);
      text(ctx, ["sans toucher à Word 👇"], W / 2, H / 2 + 200, 52, "#334155", 600);
      ctx.globalAlpha = 1;
    } else if (t < 7.4) {
      // 2. The cover builds itself while the title is "typed"
      const p = (t - 2.6) / 4.2;
      const idx = Math.min(a.typing.length - 1, Math.floor(ease(p) * a.typing.length));
      const inK = ease((t - 2.6) / 0.5);
      text(ctx, ["Tu tapes ton thème…"], W / 2, 250, 64, "#0F172A");
      drawCover(ctx, a.typing[idx], W / 2, H / 2 + 130, 840 * (0.92 + 0.08 * inK), 0, inK);
    } else if (t < 11.4) {
      // 3. Style carousel
      const p = (t - 7.4) / 4;
      const n = a.styles.length;
      const pos = p * n;
      const i = Math.min(n - 1, Math.floor(pos));
      const local = pos - i;
      text(ctx, ["…et tu choisis ton style ✨"], W / 2, 250, 64, "#0F172A");
      // Hold, then slide to the next style (no transparency: stays crisp on phones).
      const q = i < n - 1 ? ease((local - 0.72) / 0.28) : 0;
      drawCover(ctx, a.styles[i], W / 2 - q * W, H / 2 + 130, 840, 0, 1);
      if (q > 0) drawCover(ctx, a.styles[i + 1], W / 2 + (1 - q) * W, H / 2 + 130, 840, 0, 1);
    } else {
      // 4. Call to action
      const k = ease((t - 11.4) / 0.6);
      ctx.globalAlpha = k;
      ctx.drawImage(a.icon, W / 2 - 110, H / 2 - 520, 220, 220);
      text(ctx, ["C'est propre ! 🎉"], W / 2, H / 2 - 160, 96, "#0F172A");
      text(ctx, ["Word + PDF · normes de ton école", "Dès 350 F · MoMo & Orange Money"], W / 2, H / 2 - 20, 46, "#334155", 600, 1.4);
      ctx.fillStyle = "#0E9F6E";
      const bw = 720, bh = 150;
      ctx.beginPath(); ctx.roundRect(W / 2 - bw / 2, H / 2 + 180, bw, bh, 75); ctx.fill();
      text(ctx, [cta], W / 2, H / 2 + 280, 72, "#FFFFFF");
      ctx.globalAlpha = 1;
    }
  }

  async function record() {
    setVideo(null);
    setStatus("prep");
    assets.current = await prepare();
    const c = canvas.current!;
    const types = ["video/mp4;codecs=avc1.42E01E", "video/mp4", "video/webm;codecs=vp9", "video/webm"];
    const mime = types.find((m) => MediaRecorder.isTypeSupported(m)) ?? "video/webm";
    const rec = new MediaRecorder(c.captureStream(FPS), { mimeType: mime, videoBitsPerSecond: 8_000_000 });
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      setVideo({ url: URL.createObjectURL(new Blob(chunks, { type: mime })), ext: mime.startsWith("video/mp4") ? "mp4" : "webm" });
      setStatus("done");
    };
    setStatus("rec");
    rec.start();
    const start = performance.now();
    const loop = () => {
      const t = (performance.now() - start) / 1000;
      draw(Math.min(t, DURATION));
      if (t < DURATION) frame.current = requestAnimationFrame(loop);
      else rec.stop();
    };
    frame.current = requestAnimationFrame(loop);
  }

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  return (
    <div className="mx-auto grid w-full max-w-5xl gap-8 px-5 py-8 lg:grid-cols-[1fr_360px]">
      <div className="space-y-5">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-ink">Générateur de vidéos TikTok</h1>
          <p className="mt-2 text-ink/70">Vidéo verticale 1080×1920 de 15 s, fabriquée avec le vrai moteur de Paginya. Change l&apos;école pour faire une vidéo par établissement.</p>
        </div>
        <Field label="Établissement">
          <Select value={instId} onChange={(e) => setInstId(e.target.value)}>
            {INSTITUTIONS.filter((i) => i.id !== "autre").map((i) => <option key={i.id} value={i.id}>{i.short}</option>)}
          </Select>
        </Field>
        <Field label="Thème affiché"><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label="Nom de l'étudiant (exemple)"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Accroche" hint="« | » = retour à la ligne (2e ligne en vert)">
          <Segmented
            value={hook}
            onChange={setHook}
            options={[
              { value: "Ta page de garde|en 30 secondes ⏱️", label: "30 s" },
              { value: "Plus besoin|du cyber 😅", label: "Cyber" },
              { value: "Ton rapport de stage|au propre ✨", label: "Stage" },
            ]}
          />
        </Field>
        <Field label="Adresse affichée à la fin"><Input value={cta} onChange={(e) => setCta(e.target.value)} /></Field>
        <button
          type="button"
          onClick={record}
          disabled={status === "prep" || status === "rec"}
          className="w-full rounded-md bg-brand-500 py-4 font-display text-lg font-bold text-white disabled:opacity-60"
        >
          {status === "prep" ? "Préparation…" : status === "rec" ? "Enregistrement (15 s)…" : "Générer la vidéo"}
        </button>
        {video && (
          <a href={video.url} download={`paginya-${instId}.${video.ext}`} className="block rounded-md bg-ink py-4 text-center font-display text-lg font-bold text-white">
            ⬇ Télécharger la vidéo ({video.ext.toUpperCase()})
          </a>
        )}
        {video?.ext === "webm" && (
          <p className="text-xs text-ink/60">Pour convertir en MP4 : <code>ffmpeg -i paginya-{instId}.webm -c:v libx264 -pix_fmt yuv420p propre.mp4</code></p>
        )}
      </div>
      <div>
        <canvas ref={canvas} width={W} height={H} className="aspect-[9/16] w-full rounded-md bg-brand-50 shadow-xl ring-1 ring-black/10" />
        {video && <video src={video.url} controls className="mt-4 aspect-[9/16] w-full rounded-md bg-black" />}
      </div>
    </div>
  );
}
