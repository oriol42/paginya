"""Studio: the premium family of slides, after the presentation tools people admire (Gamma, Pitch, Beautiful.ai).

What makes those decks look expensive, and what this module keeps to:
- few things per slide and a lot of air, on one grid (0.8 in margins, content between 2.0 and 6.7 in);
- big tight titles (Arial bold, 36 pt, a little letter spacing removed), body text never under 15 pt;
- content laid on white cards with large rounded corners and a soft shadow, on an off-white page (or dark cards on
  a dark page);
- one strong visual per slide instead of many small decorations: a colour panel at the right edge (Gamma's
  "accent image", drawn here: no photo, no AI picture), with a big icon and a grid of dots;
- one layout logic repeated through the deck, so the eye knows where to look;
- motion that serves: things rise one after the other, and with Morph the progress bar grows and the panel stays.
Deliberately absent (the marks of generated slides): spaced capital kickers, coloured bars before a text, serif
display titles, glows. Everything stays editable in PowerPoint.
"""
from __future__ import annotations

from pathlib import Path

from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from . import slides as S

W, H = S.WIDTH, S.HEIGHT
M = 0.8  # left and right margin
TOP, BOTTOM = 2.0, 6.72
PANEL, INSET = 4.1, 0.32  # the colour panel at the right edge
PANEL_X = W - INSET - PANEL
TITLE_FONT, BODY = "Arial", "Calibri"

# name: (label, page, card, ink, muted, accent, second, deep)
PALETTES = {
    "studio": ("Studio", "F5F4F0", "FFFFFF", "16181D", "5D626B", "2F5BD3", "F2994A", "1E3C8F"),
    "studio_encre": ("Studio encre", "0D0E12", "17191F", "F3F4F6", "A7ACB7", "8AA4FF", "5EEAD4", "4F67D8"),
    "studio_corail": ("Studio corail", "FBF5F0", "FFFFFF", "2A1813", "73605A", "D04A26", "2B3A55", "A3361A"),
    "studio_foret": ("Studio forêt", "F2F5F0", "FFFFFF", "13211A", "52615A", "1E7A4C", "E3A008", "125536"),
    "studio_prune": ("Studio prune", "F6F3F9", "FFFFFF", "23162F", "625872", "6B2FD6", "13A89E", "4B1FA0"),
    "studio_nuit": ("Studio nuit", "0A1222", "121D33", "EEF3FA", "A3B3CA", "4FB3F6", "F27BA8", "2272C3"),
}


def themes() -> dict:
    out = {}
    for name, (label, page, card, ink, muted, accent, second, deep) in PALETTES.items():
        t = S._style(label, page, S._mix(page, accent, 0.07), ink, muted, accent, second, "FFFFFF", deep, TITLE_FONT, "studio", "soft", "studio", "")
        t.update(studio=True, card_fill=card, badge=MSO_SHAPE.ROUNDED_RECTANGLE, corner=MSO_SHAPE.ROUNDED_RECTANGLE, frame="box", caps=False,
                 foot="studio", kicker=False, alt=False)
        t["tint"] = S._mix(card, accent, 0.12 if not t["dark"] else 0.22)  # behind an icon, a label
        t["line"] = S._mix(card if not t["dark"] else page, ink, 0.12)  # hairlines
        t["text_accent"] = accent  # big numbers, the coloured words of a title
        out[name] = t
    return out


# --- drawing helpers ------------------------------------------------------------------------------

def _round(sp, radius: float) -> None:
    w, h = sp.width / 914400, sp.height / 914400
    sp.adjustments[0] = min(0.5, radius / max(min(w, h), 0.01))


def card(pen: S.Painter, x: float, y: float, w: float, h: float, fill: str | None = None, name: str = "Carte", lift: bool = True):
    t = pen.t
    sp = pen.slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.name = name
    sp.fill.solid()
    sp.fill.fore_color.rgb = S._rgb(fill or t["card_fill"])
    if t["dark"] and fill is None:
        sp.line.color.rgb = S._rgb(t["line"])
        sp.line.width = Pt(1)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    S._no_style_effect(sp)
    _round(sp, 0.18)
    if lift and not t["dark"]:
        S._lift(sp, blur=22, drop=4, strength=8)
    return sp


def _colours(t: dict) -> tuple[str, str]:
    """The two ends of a colour block: on a dark page, the deep shade, so white text keeps its contrast."""
    return (t["deep"], S._mix(t["deep"], "000000", 0.35)) if t["dark"] else (t["accent"], t["deep"])


def gradient_card(pen: S.Painter, x: float, y: float, w: float, h: float, name: str = "Carte en couleur"):
    t = pen.t
    sp = pen.gradient(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, *_colours(t), 315, name)
    _round(sp, 0.18)
    return sp


def chip(pen: S.Painter, icon: str, x: float, y: float, size: float, on_colour: bool = False) -> None:
    """An icon in a soft rounded square: tinted on a card, translucent white on a colour."""
    t = pen.t
    sp = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, size, size, "FFFFFF" if on_colour else t["tint"], "Pastille")
    _round(sp, size * 0.28)
    if on_colour:
        S._alpha(sp.fill._xPr.find(qn("a:solidFill")), 18)
    pen.icon(icon, x + size * 0.22, y + size * 0.22, size * 0.56, "FFFFFF" if on_colour else t["accent"])


def hairline(pen: S.Painter, x: float, y: float, w: float) -> None:
    pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, 0.014, pen.t["line"], "Filet")


def tight(shape, spacing: int = -60) -> None:
    """Big titles read better with a little less space between letters (in hundredths of a point)."""
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            r._r.get_or_add_rPr().set("spc", str(spacing))


def points(pen: S.Painter, x: float, y: float, w: float, h: float, items: list[str], size: float, mark: str, color: str | None = None) -> None:
    """Short points with a round bullet in colour."""
    room = w - 0.34
    gap = 10
    while size > 13 and sum(S.text_height(p, size, room) + gap / 72 for p in items) > h:
        size -= 1
    box = pen.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for i, text in enumerate(items):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.space_after = Pt(gap)
        ppr = p._p.get_or_add_pPr()
        ppr.set("marL", str(Inches(0.34)))
        ppr.set("indent", str(-Inches(0.34)))
        clr = ppr.makeelement(qn("a:buClr"), {})
        clr.append(clr.makeelement(qn("a:srgbClr"), {"val": mark}))
        ppr.append(clr)
        ppr.append(ppr.makeelement(qn("a:buFont"), {"typeface": "Arial"}))
        ppr.append(ppr.makeelement(qn("a:buChar"), {"char": "•"}))
        S._run(p, text, size, color or pen.t["ink"])


def panel(pen: S.Painter, icon: str, x: float = PANEL_X, y: float = INSET, w: float = PANEL, h: float = H - 2 * INSET) -> None:
    """The slide's one strong visual: a colour panel, a grid of dots, a big icon in a soft circle."""
    t = pen.t
    sp = pen.gradient(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, *_colours(t), 300, "!!Panneau")
    _round(sp, 0.26)
    for r in range(4):
        for c in range(6):
            dot = pen.shape(MSO_SHAPE.OVAL, x + 0.42 + c * 0.24, y + 0.42 + r * 0.24, 0.06, 0.06, "FFFFFF", "Décor")
            S._alpha(dot.fill._xPr.find(qn("a:solidFill")), 45)
    d = min(w - 1.0, 2.9)
    cx, cy = x + w / 2, y + h * 0.58
    ring = pen.shape(MSO_SHAPE.OVAL, cx - d / 2, cy - d / 2, d, d, "FFFFFF", "Décor")
    S._alpha(ring.fill._xPr.find(qn("a:solidFill")), 14)
    small = pen.shape(MSO_SHAPE.OVAL, cx + d * 0.22, cy - d * 0.62, d * 0.34, d * 0.34, t["second"], "Décor")
    S._alpha(small.fill._xPr.find(qn("a:solidFill")), 85)
    pen.icon(icon, cx - d * 0.24, cy - d * 0.24, d * 0.48, "FFFFFF")


def _fit(n: int, pairs: list[tuple[int, float]]) -> float:
    return S._fit(n, pairs)


def word_fit(text: str, size: float, w: float, font: str = TITLE_FONT, bold: bool = True) -> float:
    """A size at which the longest word fits the width: a word is never cut in two ("Développeme-nt")."""
    longest = max(text.split(), key=len, default="")
    while size > 12 and S._span(longest, size, font, bold) > w * 0.97:
        size -= 1
    return size


def need(head: str, text: str, w: float, head_size: float, body_size: float) -> float:
    """Height of a short title and its text: a card is as tall as what it holds, as on Gamma."""
    return S.text_height(head, head_size, w, TITLE_FONT, True) + (0.1 + S.text_height(text, body_size, w) if text else 0)


# --- the frame of every slide ---------------------------------------------------------------------

def wants_panel(s: dict) -> bool:
    """The layouts that leave the right of the slide to the colour panel."""
    kind = s.get("type")
    if kind == "liste":
        return len(s.get("items") or []) <= 4
    return kind in ("grand", "plan")


def header(prs, t: dict, title: str, with_panel: bool) -> S.Painter:
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    S._background(slide, t["bg"])
    pen = S.Painter(slide, t)
    pen.right = (PANEL_X - 0.55) if with_panel else W - M
    pen.side = (W - PANEL_X + 0.15) if with_panel else 0.0
    room = pen.right - M
    size = 36 if len(title) <= 46 else 31 if len(title) <= 68 else 27
    if with_panel:
        size = min(size, 32 if len(title) <= 40 else 27)
    return pen, room, size


def title(pen: S.Painter, text: str, mark: str, room: float, size: float) -> None:
    t = pen.t
    S._set_title(pen.slide, text, t["ink"], TITLE_FONT, size, M, 0.62, room, 1.22, MSO_ANCHOR.TOP, mark=mark, mark_color=t["text_accent"])
    tight(pen.slide.shapes.title)


def standard(prs, t: dict, text: str, part: str | None, mark: str, s: dict | None = None) -> S.Painter:
    pen, room, size = header(prs, t, text, wants_panel(s or {}))
    title(pen, text, mark, room, size)
    pen.part = part
    return pen


def footer(pen: S.Painter, parts: list[str], current: str | None, number: int, total: int) -> None:
    """Where we are: the part's name, a thin bar that fills along the talk (Morph makes it grow), the slide number."""
    t = pen.t
    end = getattr(pen, "right", W - M) if pen.side else W - M
    y = 6.98
    track = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M, y, end - M, 0.04, t["line"], "Piste")
    _round(track, 0.02)
    done = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M, y, max((end - M) * number / max(total, 1), 0.06), 0.04, t["accent"], "!!Progression")
    _round(done, 0.02)
    pen.text(M, y + 0.12, 5.0, 0.28, current or "", 11, t["muted"]).name = "!!Partie"
    pen.text(end - 1.2, y + 0.12, 1.2, 0.28, f"{number} / {total}", 11, t["muted"], align=PP_ALIGN.RIGHT)


def takeaway(pen: S.Painter, text: str) -> None:
    t = pen.t
    y = pen.bottom + 0.16
    right = getattr(pen, "right", W - M)
    band = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M, y, right - M, 0.6, t["tint"], "À retenir")
    _round(band, 0.3)
    pen.icon("lightbulb", M + 0.22, y + 0.14, 0.32, t["accent"])
    pen.text(M + 0.7, y, right - M - 1.0, 0.6, text, 17, t["ink"], True, anchor=MSO_ANCHOR.MIDDLE)


# --- pages ----------------------------------------------------------------------------------------

def cover(prs, t: dict, info: dict, images_dir: Path, seed: int = 0):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    S._background(slide, t["bg"])
    pen = S.Painter(slide, t)
    big = 5.0
    panel(pen, "graduation-cap" if info.get("school") else "lightbulb", W - INSET - big, INSET, big, H - 2 * INSET)
    right = W - INSET - big - 0.6
    room = right - M
    y = 0.62
    if info.get("logos"):
        for i, name in enumerate(info["logos"][:2]):
            S._picture(pen, images_dir / str(name), M + i * 1.1, y, 0.95, 0.95)
        y += 1.1
    head = [line for line in info.get("header") or [] if line.strip()][-3:]
    if head:
        box = pen.text(M, y, room, 0.26 * len(head), "\n".join(head), 11, t["muted"])
        y += 0.26 * len(head) + 0.25
    else:
        y = max(y, 1.3)
    if info.get("label"):
        label = info["label"][:60]
        width = min(0.105 * len(label) + 0.55, room)
        pill = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M, y, width, 0.4, t["tint"], "Étiquette")
        _round(pill, 0.2)
        pen.text(M, y, width, 0.4, label, 13, t["text_accent"], True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        y += 0.6
    name = info["title"]
    size = 40 if len(name) <= 50 else 34 if len(name) <= 80 else 28 if len(name) <= 120 else 24
    S._set_title(slide, name, t["ink"], TITLE_FONT, size, M, y, room, 2.3, MSO_ANCHOR.TOP)
    tight(slide.shapes.title)
    used = min(S.text_height(name, size, room, TITLE_FONT, True), 2.3)
    y += used + 0.25
    if info.get("specialty"):
        pen.text(M, y, room, 0.36, info["specialty"], 15, t["muted"])
    people = [(info.get("by_label") or "Présenté par", info.get("author_lines") or info.get("authors") or []),
              (info.get("under_label") or "", info.get("supervisor_lines") or [])]
    people = [(label, names) for label, names in people if names and label]
    col = room / max(len(people), 1)
    for i, (label, names) in enumerate(people):
        x = M + i * col
        pen.text(x, 5.25, col - 0.2, 0.28, label, 12, t["muted"])
        pen.text(x, 5.55, col - 0.2, 0.9, "\n".join(names[:3]), 15 if len(names) <= 2 else 13, t["ink"], True)
    if info.get("year"):
        pen.text(M, 6.72, room, 0.3, info["year"], 13, t["muted"])
    return slide


def _colour_page(prs, t: dict):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    S._background(slide, t["deep"])
    pen = S.Painter(slide, t)
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, W, H, *_colours(t), 300, "Fond")
    for r in range(5):
        for c in range(8):
            dot = pen.shape(MSO_SHAPE.OVAL, W - 2.6 + c * 0.24, 0.6 + r * 0.24, 0.06, 0.06, "FFFFFF", "Décor")
            S._alpha(dot.fill._xPr.find(qn("a:solidFill")), 40)
    circle = pen.shape(MSO_SHAPE.OVAL, W - 5.2, H - 4.6, 6.2, 6.2, "FFFFFF", "Décor")
    S._alpha(circle.fill._xPr.find(qn("a:solidFill")), 8)
    return slide, pen


def section(prs, t: dict, text: str, number: int, seed: int = 0):
    slide, pen = _colour_page(prs, t)
    pen.text(M, 1.6, 5, 1.8, f"{number:02d}", 120, "FFFFFF", True, TITLE_FONT).name = "Numéro"
    S._set_title(slide, text, "FFFFFF", TITLE_FONT, 46 if len(text) <= 40 else 38, M, 3.75, 9.6, 2.2, MSO_ANCHOR.TOP)
    tight(slide.shapes.title)
    return slide


def end(prs, t: dict, thanks: str, info: dict, images_dir: Path, seed: int = 0):
    slide, pen = _colour_page(prs, t)
    S._set_title(slide, thanks, "FFFFFF", TITLE_FONT, 52 if len(thanks) <= 28 else 42, M, 2.35, W - 2 * M, 1.7, MSO_ANCHOR.BOTTOM, PP_ALIGN.CENTER)
    tight(slide.shapes.title)
    pen.text(M + 1.0, 4.3, W - 2 * M - 2.0, 0.9, info["title"], 18, S._mix("FFFFFF", t["accent"], 0.2), align=PP_ALIGN.CENTER)
    who = ", ".join((info.get("authors") or [])[:3])
    if who:
        pen.text(M, 5.35, W - 2 * M, 0.4, who, 15, "FFFFFF", True, align=PP_ALIGN.CENTER)
    return slide


def plan(pen: S.Painter, parts: list[str]) -> None:
    t = pen.t
    n = max(len(parts), 1)
    row = min(0.95, (BOTTOM - TOP) / n)
    y0 = TOP + ((BOTTOM - TOP) - row * n) * 0.35
    for i, name in enumerate(parts):
        pen.step()
        y = y0 + i * row
        pen.text(M, y, 0.9, row - 0.1, f"{i + 1:02d}", 26, t["text_accent"], True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
        pen.text(M + 1.05, y, pen.right - M - 1.05, row - 0.1, name, 24, t["ink"], True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
        if i < n - 1:
            hairline(pen, M, y + row - 0.04, pen.right - M)
    panel(pen, "compass")


# --- content layouts ------------------------------------------------------------------------------

def _liste(pen: S.Painter, s: dict) -> None:
    t, items = pen.t, s["items"]
    n = len(items)
    right = pen.right
    avail = pen.bottom - TOP
    row = min(1.28, avail / n)
    y0 = TOP + (avail - row * n) * 0.3
    for i, it in enumerate(items):
        pen.step()
        y = y0 + i * row
        chip(pen, it["icon"], M, y + 0.06, 0.62)
        pen.stack(M + 0.95, y + 0.02, right - M - 0.95, row - 0.2, it["head"], it["text"], 22, 17)
        if i < n - 1:
            hairline(pen, M + 0.95, y + row - 0.1, right - M - 0.95)
    if pen.side:
        panel(pen, s.get("icon") or items[0]["icon"])


def _card_sizes(cols: int) -> tuple[float, float]:
    return (22, 17) if cols <= 3 else (20, 15.5)


def _cards_height(items: list[dict], cols: int, width: float = W - 2 * M) -> float:
    w = (width - 0.3 * (cols - 1)) / cols
    hs, bs = _card_sizes(cols)
    return max(need(it["head"], it["text"], w - 0.64, word_fit(it["head"], hs, w - 0.64), bs) for it in items) + 1.2 + 0.45


def _cards_row(pen: S.Painter, items: list[dict], y: float, h: float, cols: int, first_strong: bool, x0: float = M, width: float | None = None) -> None:
    t = pen.t
    gap = 0.3
    width = width or (W - 2 * M)
    w = (width - gap * (cols - 1)) / cols
    hs, bs = _card_sizes(cols)
    for i, it in enumerate(items):
        pen.step()
        x = x0 + i * (w + gap)
        strong = first_strong and i == 0
        if strong:
            gradient_card(pen, x, y, w, h)
        else:
            card(pen, x, y, w, h)
        if h < 2.4:  # two rows of short cards: the icon beside the text
            chip(pen, it["icon"], x + 0.26, y + 0.26, 0.56, on_colour=strong)
            pen.stack(x + 1.0, y + 0.2, w - 1.24, h - 0.4, it["head"], it["text"], word_fit(it["head"], hs - 2, w - 1.24), bs - 1,
                      head_color="FFFFFF" if strong else None, body_color=S._mix("FFFFFF", t["accent"], 0.15) if strong else None)
            continue
        chip(pen, it["icon"], x + 0.32, y + 0.32, 0.64, on_colour=strong)
        pen.stack(x + 0.32, y + 1.2, w - 0.64, h - 1.45, it["head"], it["text"], word_fit(it["head"], hs, w - 0.64), bs,
                  head_color="FFFFFF" if strong else None, body_color=S._mix("FFFFFF", t["accent"], 0.15) if strong else None)


def _grille(pen: S.Painter, s: dict) -> None:
    items = s["items"]
    n = len(items)
    avail = pen.bottom - TOP
    strong = pen.variant("studio-grille", 2) == 1 and n in (3, 4)
    if n <= 4:
        h = min(max(_cards_height(items, n), 2.6), avail - 0.1)
        _cards_row(pen, items, TOP + (avail - h) * 0.45, h, n, strong)
    else:
        cols = 3
        h = min(max(_cards_height(items, cols), 2.2), (avail - 0.3) / 2)
        _cards_row(pen, items[:cols], TOP, h, cols, False)
        _cards_row(pen, items[cols:], TOP + h + 0.3, h, cols, False)


def _schema(pen: S.Painter, s: dict) -> None:
    """The idea in the middle, its parts around it, linked by thin lines."""
    t, items = pen.t, s["items"]
    avail = pen.bottom - TOP
    d = 2.3
    cx, cy = W / 2, TOP + avail / 2
    left, right = items[: (len(items) + 1) // 2], items[(len(items) + 1) // 2:]
    cw = (W - 2 * M - d - 1.4) / 2
    links = []
    boxes = []
    for side, group in ((0, left), (1, right)):
        k = len(group)
        gap = 0.25
        ch = min(1.45, (avail - gap * (k - 1)) / k)
        y0 = TOP + (avail - (ch * k + gap * (k - 1))) / 2
        for j, it in enumerate(group):
            x = M if side == 0 else W - M - cw
            y = y0 + j * (ch + gap)
            boxes.append((x, y, cw, ch, it))
            links.append((x + cw if side == 0 else x, y + ch / 2))
    for x2, y2 in links:
        line = pen.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(cx), Inches(cy), Inches(x2), Inches(y2))
        line.line.color.rgb = S._rgb(S._mix(t["bg"], t["accent"], 0.35))
        line.line.width = Pt(1.25)
        line.name = "Lien"
    pen.step()
    hub = pen.gradient(MSO_SHAPE.OVAL, cx - d / 2, cy - d / 2, d, d, *_colours(t), 315, "Centre")
    hub.shadow.inherit = False
    pen.icon(s.get("icon") or "target", cx - 0.27, cy - d / 2 + 0.32, 0.54, "FFFFFF")
    key = s.get("key") or s["title"].split(" ")[0]
    size = word_fit(key, _fit(len(key), [(14, 20), (24, 17), (40, 14), (10_000, 12)]), d - 0.5)
    pen.text(cx - d / 2 + 0.25, cy - 0.2, d - 0.5, d / 2 - 0.05, key, size, "FFFFFF", True, TITLE_FONT, PP_ALIGN.CENTER)
    for x, y, w, h, it in boxes:
        pen.step()
        card(pen, x, y, w, h)
        chip(pen, it["icon"], x + 0.22, y + (h - 0.52) / 2, 0.52)
        pen.stack(x + 0.92, y + 0.1, w - 1.1, h - 0.2, it["head"], it["text"], 17, 13.5, anchor=MSO_ANCHOR.MIDDLE)


def _panneau(pen: S.Painter, s: dict) -> None:
    t, items = pen.t, s["items"]
    avail = pen.bottom - TOP
    bw = 4.9
    pen.step()
    gradient_card(pen, M, TOP, bw, avail)
    chip(pen, s.get("icon") or "lightbulb", M + 0.42, TOP + 0.42, 0.72, on_colour=True)
    key = s.get("key") or ""
    pen.text(M + 0.42, TOP + 1.45, bw - 0.84, avail - 1.8, key, _fit(len(key), [(50, 30), (80, 26), (10_000, 22)]), "FFFFFF", True, TITLE_FONT)
    x = M + bw + 0.55
    room = W - M - x
    n = len(items)
    row = min(1.3, avail / n)
    for i, it in enumerate(items):
        pen.step()
        y = TOP + i * row
        pen.stack(x, y + 0.05, room, row - 0.22, it["head"], it["text"], 20, 15.5)
        if i < n - 1:
            hairline(pen, x, y + row - 0.1, room)


def _chronologie(pen: S.Painter, s: dict) -> None:
    t, items = pen.t, s["items"]
    n = len(items)
    avail = pen.bottom - TOP
    w = (W - 2 * M) / n
    size = 17 if n <= 4 else 14.5
    tall = max(S.text_height(x["text"], size, w - 0.6) for x in items)
    block = 1.0 + 0.45 + max(1.05 + tall + 0.4, 1.9)
    line_y = TOP + max((avail - block) * 0.45, 0) + 1.0
    track = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M, line_y - 0.025, W - 2 * M, 0.05, S._mix(t["bg"], t["accent"], 0.3), "Ligne")
    _round(track, 0.025)
    for i, it in enumerate(items):
        pen.step()
        cx = M + i * w + w / 2
        pen.text(M + i * w + 0.1, line_y - 1.0, w - 0.2, 0.75, it["head"], 21 if n <= 4 else 17, t["text_accent"], True, TITLE_FONT, PP_ALIGN.CENTER, MSO_ANCHOR.BOTTOM)
        dot = pen.shape(MSO_SHAPE.OVAL, cx - 0.17, line_y - 0.17, 0.34, 0.34, t["accent"], "Point")
        dot.line.color.rgb = S._rgb(t["bg"])
        dot.line.width = Pt(3)
        top = line_y + 0.45
        h = min(max(1.05 + tall + 0.4, 1.9), pen.bottom - top)
        card(pen, M + i * w + 0.1, top, w - 0.2, h)
        chip(pen, it["icon"], cx - 0.28, top + 0.28, 0.56)
        pen.text(M + i * w + 0.3, top + 1.05, w - 0.6, h - 1.25, it["text"], size, t["muted"], align=PP_ALIGN.CENTER)


def _etapes(pen: S.Painter, s: dict) -> None:
    t, items = pen.t, s["items"]
    n = len(items)
    avail = pen.bottom - TOP
    gap = 0.46
    w = (W - 2 * M - gap * (n - 1)) / n
    hs, bs = (21, 16.5) if n <= 4 else (18, 14.5)
    hs = min(word_fit(it["head"], hs, w - 0.6) for it in items)  # the same size on every step
    h = min(max(max(need(it["head"], it["text"], w - 0.6, hs, bs) for it in items) + 1.15 + 0.45, 2.6), avail - 0.1)
    y = TOP + (avail - h) * 0.45
    for i, it in enumerate(items):
        pen.step()
        x = M + i * (w + gap)
        card(pen, x, y, w, h)
        pen.text(x + 0.3, y + 0.28, w - 0.6, 0.7, f"{i + 1:02d}", 30, t["text_accent"], True, TITLE_FONT)
        pen.icon(it["icon"], x + w - 0.3 - 0.42, y + 0.36, 0.42, S._mix(t["card_fill"], t["accent"], 0.55))
        pen.stack(x + 0.3, y + 1.15, w - 0.6, h - 1.4, it["head"], it["text"], hs, bs)
        if i < n - 1:
            arrow = pen.shape(MSO_SHAPE.CHEVRON, x + w + gap / 2 - 0.1, y + h / 2 - 0.15, 0.2, 0.3, S._mix(t["bg"], t["accent"], 0.45), "Flèche")
            arrow.shadow.inherit = False


def _comparaison(pen: S.Painter, s: dict) -> None:
    t = pen.t
    avail = pen.bottom - TOP
    gap = 0.4
    w = (W - 2 * M - gap) / 2
    size = 22
    tall = max(sum(S.text_height(p, size, w - 0.84 - 0.34) + 10 / 72 for p in side["points"]) for side in (s["left"], s["right"]))
    h = min(max(1.15 + tall + 0.45, 3.0), avail - 0.1)
    top = TOP + (avail - h) * 0.45
    for i, side in enumerate((s["left"], s["right"])):
        pen.step("zoom" if i == 1 else "")
        x = M + i * (w + gap)
        strong = i == 1
        sp = card(pen, x, top, w, h, fill=t["tint"] if strong else None, lift=not strong)
        if strong:
            sp.line.color.rgb = S._rgb(t["accent"])
            sp.line.width = Pt(2)
        pen.text(x + 0.42, top + 0.36, w - 0.84, 0.6, side["title"] or " ", 23, t["text_accent"] if strong else t["ink"], True, TITLE_FONT)
        points(pen, x + 0.42, top + 1.15, w - 0.84, h - 1.4, side["points"], size, t["accent"] if strong else t["muted"])


def _chiffres(pen: S.Painter, s: dict) -> None:
    t, stats = pen.t, s["stats"]
    n = len(stats)
    avail = pen.bottom - TOP
    gap = 0.3
    w = (W - 2 * M - gap * (n - 1)) / n
    h = min(3.6, avail - 0.1)
    y = TOP + (avail - h) * 0.45
    longest = max(len(x["value"]) for x in stats)
    size = _fit(int(longest * 4 / n), [(6, 60), (9, 50), (13, 40), (10_000, 30)])
    for i, st in enumerate(stats):
        pen.step("zoom")
        x = M + i * (w + gap)
        strong = i == 0
        (gradient_card if strong else card)(pen, x, y, w, h)
        chip(pen, st.get("icon") or "trending-up", x + 0.32, y + 0.32, 0.6, on_colour=strong)
        pen.text(x + 0.32, y + 1.15, w - 0.64, 1.25, st["value"], size, "FFFFFF" if strong else t["text_accent"], True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
        pen.text(x + 0.32, y + 2.45, w - 0.64, h - 2.65, st["label"], 16, S._mix("FFFFFF", t["accent"], 0.12) if strong else t["muted"])


def _graphique(pen: S.Painter, s: dict) -> None:
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION

    t = pen.t
    key = s.get("key") or ""
    avail = pen.bottom - TOP
    w = 7.9 if key else W - 2 * M
    donut = s.get("chart") == "donut"
    pen.step()
    card(pen, M, TOP, w, avail)
    data = CategoryChartData()
    data.categories = [x["label"] for x in s["series"]]
    data.add_series(s["title"][:40], [x["value"] for x in s["series"]])
    pen.step("roue" if donut else "trace")
    frame = pen.slide.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT if donut else XL_CHART_TYPE.BAR_CLUSTERED,
                                       Inches(M + 0.3), Inches(TOP + 0.3), Inches(w - 0.6), Inches(avail - 0.6), data)
    chart = frame.chart
    chart.font.size, chart.font.name = Pt(15), BODY
    chart.font.color.rgb = S._rgb(t["ink"])
    chart.has_title = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.show_value, labels.font.size, labels.font.bold = True, Pt(15), True
    series = plot.series[0]
    colors = [t["accent"], t["second"], S._mix(t["accent"], t["card_fill"], 0.45), S._mix(t["second"], t["card_fill"], 0.45), t["deep"], t["muted"]]
    if donut:
        labels.show_percentage = False
        chart.has_legend = True
        chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.RIGHT, False
        chart.legend.font.size = Pt(14)
        for i in range(len(s["series"])):
            point = series.points[i]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = S._rgb(colors[i % len(colors)])
    else:
        chart.has_legend = False
        plot.gap_width = 45
        labels.position = XL_LABEL_POSITION.OUTSIDE_END
        chart.value_axis.visible, chart.value_axis.has_major_gridlines = False, False
        chart.category_axis.reverse_order = True
        chart.category_axis.format.line.fill.background()
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = S._rgb(t["accent"])
    if not key:
        return
    pen.step()
    x = M + w + 0.3
    room = W - M - x
    top = max(s["series"], key=lambda v: v["value"])
    figure = f"{top['value']:g}".replace(".", ",")
    gradient_card(pen, x, TOP, room, avail)
    chip(pen, s.get("icon") or "chart-pie", x + 0.36, TOP + 0.36, 0.62, on_colour=True)
    pen.text(x + 0.36, TOP + 1.2, room - 0.72, 1.0, figure, 50 if len(figure) <= 4 else 38, "FFFFFF", True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
    pen.text(x + 0.36, TOP + 2.2, room - 0.72, 0.5, top["label"], 15, S._mix("FFFFFF", t["accent"], 0.15), True)
    pen.text(x + 0.36, TOP + 2.85, room - 0.72, avail - 3.1, key, _fit(len(key), [(70, 21), (120, 18), (10_000, 16)]), "FFFFFF", True, TITLE_FONT)


def _encadre(pen: S.Painter, s: dict) -> None:
    t = pen.t
    avail = pen.bottom - TOP
    h = avail - 0.15
    pen.step()
    sp = card(pen, M, TOP, W - 2 * M, h, fill=t["tint"], lift=False)
    sp.name = "Encadré"
    if s.get("label"):
        label = s["label"][:40]
        width = 0.11 * len(label) + 0.6
        pill = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M + 0.5, TOP + 0.45, width, 0.42, t["accent"], "Étiquette")
        _round(pill, 0.21)
        pen.text(M + 0.5, TOP + 0.45, width, 0.42, label, 14, "FFFFFF", True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    pen.text(M + 0.45, TOP + 0.95, 1.2, 1.4, "“", 110, t["accent"], True, TITLE_FONT)
    pen.step()
    text = s["text"]
    pen.text(M + 1.6, TOP + 1.1, W - 2 * M - 2.4, h - 1.5, text, _fit(len(text), [(90, 34), (150, 29), (10_000, 25)]), t["ink"], True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)


def _grand(pen: S.Painter, s: dict) -> None:
    t = pen.t
    value = s["value"]
    room = pen.right - M
    pen.step("zoom")
    size = _fit(len(value), [(5, 140), (9, 100), (14, 72), (10_000, 50)])
    pen.text(M, TOP + 0.1, room, 2.6, value, size, t["text_accent"], True, TITLE_FONT, anchor=MSO_ANCHOR.BOTTOM)
    pen.step()
    pen.text(M, TOP + 2.95, room, 1.6, s.get("text") or "", 24, t["ink"], True)
    panel(pen, s.get("icon") or "target")


def _figure(pen: S.Painter, s: dict, images_dir: Path) -> None:
    t = pen.t
    items = s.get("points") or []
    caption = s.get("caption") or ""
    avail = pen.bottom - TOP
    w = 7.9 if items else W - 2 * M
    h = avail - (0.42 if caption else 0)
    pen.step()
    card(pen, M, TOP, w, h, fill="FFFFFF")
    if not S._picture(pen, images_dir / s["image"], M + 0.2, TOP + 0.2, w - 0.4, h - 0.4):
        return
    if caption:
        pen.text(M, TOP + h + 0.08, w, 0.36, caption[:150], 13, t["muted"], align=PP_ALIGN.CENTER)
    if items:
        pen.step()
        x = M + w + 0.35
        points(pen, x, TOP + 0.2, W - M - x, avail - 0.3, items, 19, t["accent"])


def _table(pen: S.Painter, s: dict) -> None:
    t = pen.t
    rows = s["rows"]
    cols = len(rows[0])
    caption = s.get("caption") or ""
    width = W - 2 * M
    room = pen.bottom - TOP - (0.42 if caption else 0)
    column = width / cols - 0.24

    def heights(size: float) -> list[float]:
        return [max(max(S.text_height(c, size, column, bold=r == 0) for c in row) + 0.16, 0.46) for r, row in enumerate(rows)]

    size = 18
    while size > 11 and sum(heights(size)) > room:
        size -= 1
    tall = heights(size)
    pen.step()
    shape = pen.slide.shapes.add_table(len(rows), cols, Inches(M), Inches(TOP), Inches(width), Inches(sum(tall)))
    table = shape.table
    tbl_pr = shape._element.graphic.graphicData.tbl.tblPr
    tbl_pr.set("bandRow", "0")
    tbl_pr.set("firstRow", "0")
    for r, height in enumerate(tall):
        table.rows[r].height = Inches(height)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.fill.solid()
            cell.fill.fore_color.rgb = S._rgb(t["accent"] if r == 0 else t["card_fill"] if r % 2 else t["tint"])
            S._run(cell.text_frame.paragraphs[0], value, size, "FFFFFF" if r == 0 else t["ink"], r == 0)
    if caption:
        pen.text(M, pen.bottom - 0.32, width, 0.35, caption[:150], 13, t["muted"], align=PP_ALIGN.CENTER)


DRAW = {"liste": _liste, "grille": _grille, "schema": _schema, "panneau": _panneau, "chronologie": _chronologie, "etapes": _etapes,
        "comparaison": _comparaison, "chiffres": _chiffres, "graphique": _graphique, "encadre": _encadre, "tableau": _table, "grand": _grand}
