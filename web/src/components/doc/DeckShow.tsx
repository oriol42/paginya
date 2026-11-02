"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { docs, type DeckShowPlan } from "@/lib/documents";
import { Icon } from "../Icon";

/** The presentation as it will play: slides change with their transition, things appear one after the other. */
export function DeckShow({ docId, onClose }: { docId: string; onClose: () => void }) {
  const [plan, setPlan] = useState<DeckShowPlan | null>(null);
  const [error, setError] = useState("");
  const [slide, setSlide] = useState(0);
  const [frame, setFrame] = useState(0);
  const sheet = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let gone = false;
    docs.show(docId).then((p) => { if (!gone) setPlan(p); }).catch((e) => { if (!gone) setError((e as Error).message); });
    return () => { gone = true; };
  }, [docId]);

  // every picture loaded ahead: on a slow line, the next step must already be there
  useEffect(() => {
    if (!plan) return;
    plan.slides.forEach((s, i) => {
      for (let f = 0; f < s.frames; f++) new Image().src = docs.showUrl(docId, i + 1, f, plan.version);
    });
  }, [plan, docId]);

  const total = plan?.slides.length ?? 0;
  const current = plan?.slides[slide];

  // things appear on their own, one step every half second
  useEffect(() => {
    if (!current || frame >= current.frames - 1) return;
    const timer = setTimeout(() => setFrame(frame + 1), frame === 0 ? 650 : 480);
    return () => clearTimeout(timer);
  }, [current, frame]);

  const go = useCallback((to: number) => {
    if (!plan) return;
    if (to >= total) return onClose();
    if (to < 0) return;
    setFrame(0);
    setSlide(to);
  }, [plan, total, onClose]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (["ArrowRight", " ", "Enter", "PageDown"].includes(e.key)) { e.preventDefault(); go(slide + 1); }
      if (["ArrowLeft", "PageUp"].includes(e.key)) go(slide - 1);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [go, slide, onClose]);

  return (
    <div role="dialog" aria-modal="true" aria-label="Diaporama" className="fixed inset-0 z-50 flex flex-col bg-[#08090b] text-white">
      <div className="flex items-center justify-between px-4 py-2 text-[14px] text-white/70">
        <span className="tabular">{plan ? `${slide + 1} / ${total}` : ""}</span>
        <button type="button" onClick={onClose} aria-label="Fermer" className="press grid h-10 w-10 place-items-center rounded-md hover:bg-white/10"><Icon name="x" size={20} /></button>
      </div>
      <div ref={sheet} className="relative flex min-h-0 flex-1 cursor-pointer items-center justify-center overflow-hidden px-2" onClick={() => go(slide + 1)}>
        {!plan && !error && <p className="flex items-center gap-2 text-[16px]"><Icon name="loader-circle" size={20} className="animate-spin" />Préparation du diaporama… (20 secondes environ)</p>}
        {error && !plan && <p className="text-[16px]">{error}</p>}
        {plan && current && (
          <div key={slide} className={`relative aspect-video max-h-full w-full max-w-[calc((100dvh-7rem)*16/9)] ${current.push ? "show-push" : "show-fade"}`}>
            {Array.from({ length: current.frames }, (_, f) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={f} src={docs.showUrl(docId, slide + 1, f, plan.version)} alt={f === current.frames - 1 ? `Diapositive ${slide + 1}` : ""}
                className={`absolute inset-0 h-full w-full transition-opacity duration-300 ${f <= frame ? "opacity-100" : "opacity-0"}`} />
            ))}
          </div>
        )}
      </div>
      <div className="flex items-center justify-center gap-3 px-4 py-3">
        <button type="button" disabled={slide === 0} onClick={() => go(slide - 1)} aria-label="Diapositive précédente" className="press grid h-11 w-11 place-items-center rounded-md ring-1 ring-white/25 disabled:opacity-30"><Icon name="arrow-left" size={20} /></button>
        <button type="button" onClick={() => go(slide + 1)} aria-label="Diapositive suivante" className="press grid h-11 w-11 place-items-center rounded-md ring-1 ring-white/25"><Icon name="arrow-right" size={20} /></button>
      </div>
    </div>
  );
}
