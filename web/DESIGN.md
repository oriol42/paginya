---
name: Paginya
description: Ton document, aux normes de ton école.
colors:
  board: "#1c3a2a"
  board-2: "#244a36"
  board-3: "#2f5c45"
  frame-wood: "#6b4a2e"
  paper: "#fdfdfa"
  wall: "#eceee6"
  stamp-violet: "#5b2a86"
  pin-red: "#d23a2c"
  highlighter: "#f4d63a"
  highlighter-deep: "#e3bf12"
  ballpoint: "#1d4ed8"
  ink: "#16181a"
  sticky-note: "#fff8c9"
typography:
  display:
    fontFamily: "Sofia Sans Extra Condensed, Sofia Sans, sans-serif"
    fontSize: "clamp(3.4rem, 8vw, 5.4rem)"
    fontWeight: 900
    lineHeight: 0.9
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Sofia Sans Extra Condensed, Sofia Sans, sans-serif"
    fontSize: "clamp(2.6rem, 5vw, 3.4rem)"
    fontWeight: 900
    lineHeight: 0.95
  title:
    fontFamily: "Sofia Sans Extra Condensed, Sofia Sans, sans-serif"
    fontSize: "28px"
    fontWeight: 900
    lineHeight: 1
  body:
    fontFamily: "Sofia Sans, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Sofia Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 700
    letterSpacing: "0.025em"
rounded:
  sheet: "2px"
  label: "3px"
  control: "6px"
spacing:
  gutter: "24px"
  section: "64px"
  section-lg: "80px"
components:
  pin-label:
    backgroundColor: "{colors.highlighter}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    rounded: "{rounded.label}"
    padding: "20px 24px 16px"
  sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
  stamp:
    textColor: "{colors.stamp-violet}"
    rounded: "{rounded.control}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
  button-secondary:
    backgroundColor: "{colors.board}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "14px 20px"
---

# Design System: Paginya

## Overview

**Creative North Star: "Les valves"**

The university notice board where results, timetables and deadlines get pinned. Every screen is a deep green board in a wooden frame; content lives on white A4 sheets held by red push-pins. Statuses are violet rubber stamps (EN COURS, CONFORME, PAYÉ), the one action to take is a yellow highlighter label, notes are written in ballpoint blue. Nothing is decorative: every object is something a Cameroonian student already sees on campus.

The system is light by construction for slow Android data: board grain, wood, creases and stamp ink are all CSS gradients or one tiny inline SVG mask; the only downloads are two variable woff2 fonts.

**Key Characteristics:**
- Green board field, paper sheets, real pins; slight tilts (−5° to +3°) only on pinned objects.
- One yellow action per screen; violet only for status.
- Condensed black uppercase for voice, a plain grotesk for reading.
- Short exponential motion: sheets pin in, stamps press, labels push their pin.

## Colors

A dark, calm field with three loud inks, each with one job.

### Primary
- **Board Green** (#1c3a2a): the field of every hero, app shell header and interstitial band. Lighter steps #244a36 / #2f5c45 for hovers and inner surfaces.
- **Highlighter Yellow** (#f4d63a, edge #e3bf12): the single primary action and the highlighted phrase in a headline.

### Secondary
- **Stamp Violet** (#5b2a86): statuses only, always as a stamp.
- **Pin Red** (#d23a2c): push-pins, never text.
- **Ballpoint Blue** (#1d4ed8): hand notes under steps and on sticky notes; never links styled as buttons.

### Neutral
- **Paper** (#fdfdfa): sheets, panels, inputs. **Sticky note** (#fff8c9) for asides.
- **Wall** (#eceee6): page background between board bands.
- **Ink** (#16181a): all text on paper, with 75/60/40 % alpha steps.
- **Frame Wood** (#6b4a2e): the board edge only.

### Named Rules
**The One Label Rule.** A screen has exactly one yellow pinned label. Secondary actions are board-green buttons or plain links.
**The Stamp Speaks Status Rule.** Status is never a coloured badge or pill; it is a violet stamp.

## Typography

**Display Font:** Sofia Sans Extra Condensed (black, uppercase)
**Body Font:** Sofia Sans

**Character:** the condensed black face reads like a notice header typed in capitals; the grotesk body stays quiet and legible outdoors on cheap screens.

### Hierarchy
- **Display** (900, 3.4–5.4rem, 0.9): hero headline only.
- **Headline** (900, 2.6–3.4rem, 0.95): section titles, uppercase.
- **Title** (900, 19–28px, 1): step names, panel titles, the pin-label text.
- **Body** (400, 16–17px, 1.6): max ~65ch.
- **Label** (700, 13px): field labels.

## Layout

Mobile-first single column at 390px with a 24px gutter; max width 72rem on desktop. Landing alternates board bands and wall bands; compositions vary per section (split hero with overlapping sheets, three giant numerals, sheet-left/text-right, full-width pinned sheet) rather than repeating one text-plus-card template. The editor is a board shell: pinned page previews centre, a paper rail of panels on the side (drawer on phones).

## Elevation & Depth

Depth is physical: paper casts a soft drop shadow on the board, pins cast a small hard one. Panels inside a sheet are separated by rules, never by nested cards.

### Shadow Vocabulary
- **Sheet** (`box-shadow: 0 1px 1px rgba(0,0,0,.12), 0 10px 24px -8px rgba(0,0,0,.45)`): every pinned sheet.
- **Pin** (`box-shadow: 0 3px 4px rgba(0,0,0,.45)`): push-pins.
- **Label** (`box-shadow: 0 2px 0 0 #e3bf12, 0 14px 28px -10px rgba(0,0,0,.6)`): the yellow pin label.

## Shapes

Sheets are nearly square-cornered (2px), labels 3px, controls 6px. Nothing is pill-shaped except toggles and pins. Tilt belongs to pinned paper, not to controls.

## Components

- **Pin label** (`.pin-label` + `.pin`): yellow, uppercase condensed, slight −1° tilt, pin on top; `:active` pushes the pin in.
- **Sheet** (`.paper` + `.pin`): the container for any content on the board. `.crumpled` for "before" documents.
- **Stamp** (`.stamp`, `.stamp-in`): violet border and text, −6°, multiply blend, noise mask for uneven ink; lands with scale 1.15→1 in 180ms.
- **Inputs** (`Input`, `TextArea`, `Select` in `components/ui.tsx`): paper fields with an ink underline that turns highlighter on focus; textareas grow to their line count; selects use a Lucide chevron.
- **Toggle**: board-green track with a check in the knob.
- **Icons**: embedded Lucide set (`components/Icon.tsx`), never emoji.

## Do's and Don'ts

- Do pin every sheet; a sheet without a pin breaks the world.
- Do keep motion to transforms and opacity, ≤ 520ms, ease-out-expo; honour reduced motion.
- Don't use emoji or unicode glyphs as icons.
- Don't use gradients as decoration, gradient text, or glass effects.
- Don't add a second yellow action or colour-coded status badges.
- Don't nest cards inside panels; use rules.
