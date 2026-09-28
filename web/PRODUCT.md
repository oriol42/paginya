# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: students in Cameroon (university and grandes écoles) who must hand in an internship report, a thesis (mémoire), a course summary or an exposé formatted to their school's norms, often the night before the deadline. Secondary: teachers (exam papers / épreuves) and individuals writing administrative letters, requests and CVs.

## Product Purpose

Paginya turns a messy document (Word, PDF, pasted or Markdown text, photos of handwritten pages) into a clean document formatted to Cameroonian norms in about a minute: real headings and levels, lists, tables, table of contents when the document type needs it, page numbers, official bilingual header (République du Cameroun / Paix – Travail – Patrie, school, logo) and cover page. The preview is free and complete; the user pays once by Mobile Money to download Word + PDF. Success: a student gets a document their supervisor accepts without spending hours in Word or paying a cybercafé.

## Positioning

Local norms built in: Cameroonian cover pages and bilingual official headers, logos of Cameroonian universities and schools, document types chosen by the user (cours, exposé, lettre, rapport, rapport de stage, mémoire) so nothing is added that the document doesn't need, structure detection trained on badly written student documents, payment by MTN MoMo / Orange Money at small prices. It formats; it never writes the content for the student.

## Operating Context

Users are mostly on Android phones (entry to mid range), on slow and unstable 3G/4G where data is expensive; some finish on a cybercafé or laptop. Documents arrive from Word, WhatsApp copies, ChatGPT/Notion Markdown, PDFs and phone photos. Servers are free tiers that sleep: the first action after a quiet period can take about a minute, rendering a long document takes 40–80 s. Interface language: French, informal "tu".

## Capabilities and Constraints

- Flows: import (file, photos, paste) → automatic analysis → editor with Style (document type, what Paginya adds, official header, theme), Cover page (Garde) and Plan panels → before/after/side-by-side preview → pay → download Word + PDF; modifications free for 7 days. Also standalone cover page studio (/garde), letters (/lettre), exam papers (/epreuve), pricing, legal pages.
- Prices (FCFA): cover page and letter 350, CV and exam paper 550, document ≤ 15 pages 1 000, report 16–40 pages 2 000, thesis > 40 pages 3 000. Fapshi takes 3 %.
- Static Next.js export on Cloudflare Pages (paginya.pages.dev); API on Render.
- No accounts or passwords; documents deleted after 7 days.

## Brand Commitments

Name Paginya, green brand colour (#0E9F6E) and existing logo. No emojis anywhere in the interface (the founder finds them "AI-looking"); use real icons. Voice: short, friendly, informal French ("tu"), reassuring about deadlines and norms. "On présente ton travail, on ne l'écrit pas à ta place."

## Evidence on Hand

Real before/after renders of a student course (docs, `public/exemples`), 25 Cameroonian school logos (`public/logos`, sources in `../docs/LOGOS.md`), study of real internship reports (`../docs/ETUDE-DOCUMENTS.md`). No customer testimonials, user counts or partnerships exist yet: never invent them.

## Product Principles

1. Fast on a bad connection: every tap answers immediately, heavy work shows honest progress.
2. The document is the hero: show the real result, as big and readable as possible, early.
3. Nothing imposed: the user decides what gets added (contents, cover, header).
4. Trust through local precision: norms, schools, Mobile Money, clear prices before paying.
5. Zero manual operator: the app does all the work itself.

## Accessibility & Inclusion

Readable on small screens in sunlight (strong contrast, large tap targets), works with low-end Android browsers, respects reduced-motion, light pages for expensive data.
