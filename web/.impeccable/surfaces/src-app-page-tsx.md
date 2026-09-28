---
version: 1
slug: "src-app-page-tsx"
primary_target: "src/app/page.tsx"
related_targets: ["src/app/document/page.tsx"]
---

# Surface brief — Paginya (whole app: landing + document flow)

Scope: the whole Paginya web app, first surface the landing (Persuade), then import, working, editor, pay (Operate). Mode per surface: landing Persuade; app screens Operate.
Audience: Cameroonian students on Android phones with slow data, often the night before a deadline. Job: turn their document into one their school accepts, then pay by MoMo.
Proof available: real before/after renders of a student course, school logos, real prices. No testimonials or user counts exist.
Constraints: fast (no heavy libraries, CSS/transform-only motion, reduced-motion respected), no emojis, informal French.

## Direction contract

THESIS: Paginya is the university notice board ("les valves"): a messy sheet arrives, a clean sheet is pinned and stamped CONFORME. It refuses the category default of a white SaaS page with a floating document mockup and green buttons.

OWN-WORLD: a deep board green field (painted notice board, wood frame edge), pure white A4 sheets with real paper shadow pinned by coloured push-pins, violet stamp ink for every status (EN COURS, CONFORME, PAYÉ), highlighter yellow for the one thing to act on, ballpoint blue for hand notes. Type: a grotesk workhorse for the interface, a condensed display face for sheet titles and numerals, sheets set like typed documents.

STORY: the student recognises the valves, sees their own messy page become a clean one in seconds, understands the three steps and the price, and taps the pinned label to start.

FIRST VIEWPORT: full-height board. Top: Paginya wordmark stencilled on the frame. Center: two sheets pinned side by side (phone: stacked with overlap) — "avant" rumpled page, "après" clean page with the violet CONFORME stamp that lands on load. Headline in large display type on a pinned strip: "Ton document, aux normes de ton école." Primary action: a yellow pinned label "Mettre mon document au propre" at thumb height, plus "Aperçu gratuit · dès 350 F · MoMo".

FORM: grounded list position 3 ("les valves"), seed key eb5695c0. Raises: numbered giant steps (from the notice challenger), text size carries importance (Massin), states printed as stamps (terminal).

Signature interaction: the stamp — every success state lands as an ink stamp with a short press (scale 1.15→1, 180 ms, slight rotation), never a toast.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
