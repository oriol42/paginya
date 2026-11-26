"""Studio: the premium family of slides, set on what designers do (measured on their decks, not guessed).

31 free decks by SlidesCarnival's designers were measured slide by slide (api/ml/study/decks: measure.py,
profile.py), then the same measures were taken on Paginya's decks. What the designers do, and this module with them:
- margins of about 7.5 % of the width (1 in on a 13.33 in slide);
- two or three text sizes on a slide, not four or five: a title, a short head in bold, its text (body around 17-19 pt);
  things side by side share one size (`shared`); the cover title is big (median 64 pt), as large as three lines allow;
- photos edge to edge: a column the full height of the slide, on one side or the other along the talk, or the whole
  slide (cover, part openers, last slide); never a small framed picture. Real photos found on the internet for the
  subject (art.illustrate, credited in the notes and on the last slide); a block of colour when there is none;
- almost no shadows (7 % of their slides) nor gradients: flat cards with a hairline, a solid colour for the one that
  matters; figures without boxes, big, with a thin line between them;
- no icons: they are what makes generated slides look generated (asked by Oriol, 22/11/2026);
- motion: designers fade things in, in half a second, one after the other; the slide's photo is laid before the
  slide's things so it stays put, and Morph carries it from slide to slide (cover to outline, part opener to its
  first slide, slide to slide): it grows, shrinks or slides to its new place.
Deliberately absent (the marks of generated slides): spaced capital kickers, coloured bars before a text, labels in
pills, serif display titles, glows. Everything stays editable in PowerPoint.
"""
from __future__ import annotations

from pathlib import Path

from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from . import slides as S

W, H = S.WIDTH, S.HEIGHT
M = 1.0  # left and right margin
TOP, BOTTOM = 2.0, 6.72
COLUMN = 5.0  # the photo column, edge to edge, the full height of the slide
GUTTER = 0.7  # between the column and the text
TITLE_FONT, BODY = "Arial", "Calibri"
LEAD, TEXT = 22, 18  # a short head in bold, its text (designers' body text: median 18.7 pt)
INFO = 16  # the cover's lines

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
        t["tint"] = S._mix(card, accent, 0.12 if not t["dark"] else 0.22)  # a quiet surface: the question, the closing line
        t["line"] = S._mix(card if not t["dark"] else page, ink, 0.14)  # hairlines, card edges
        t["text_accent"] = accent  # big numbers, the coloured words of a title
        out[name] = t
    return out


# --- photos -----------------------------------------------------------------------------------------

class Photos:
    """The real photos of a presentation (found by art.illustrate), handed out so that two slides in a row never
    show the same one. The cover keeps its own. Also decides on which side the next photo column goes."""

    def __init__(self, images_dir: Path, deck: dict):
        self.dir = images_dir
        self.items: list[tuple[str, str]] = []
        for owner in [deck, *deck.get("slides", [])]:
            name = owner.get("art") or ""
            if name.startswith("deck-photo") and (images_dir / name).is_file() and name not in (n for n, _ in self.items):
                self.items.append((name, owner.get("credit") or ""))
        self.own_cover = bool(deck.get("art")) and bool(self.items) and self.items[0][0] == deck.get("art")
        self.k, self.last, self.turn = 0, "", 0
        self.used: list[str] = []

    def cover(self) -> tuple[str, str] | None:
        return self.items[0] if self.items else None

    def pick(self, own: str = "") -> tuple[str, str] | None:
        for name, credit in self.items:
            if own and name == own:
                self.last = name
                return name, credit
        # the cover's photo opens and closes the talk: the slides between take the others (if there are others)
        rest = self.items[1:] if self.own_cover and len(self.items) > 1 else self.items
        if not rest:
            return None
        for _ in range(len(rest)):
            item = rest[self.k % len(rest)]
            self.k += 1
            if item[0] != self.last or len(self.items) == 1:
                self.last = item[0]
                return item
        return None

    def side(self) -> str:
        """Right, then left, then right: the photo changes side along the talk, as in a designer's deck."""
        self.turn += 1
        return "right" if self.turn % 2 else "left"

    def note(self, credit: str) -> None:
        if credit and credit not in self.used:
            self.used.append(credit)


def photo(pen: S.Painter, entry: tuple[str, str] | None, x: float, y: float, w: float, h: float, radius: float = 0.0, name: str = "Photo") -> bool:
    """A photo cut to fill its place (still a picture PowerPoint can swap), with rounded corners if asked."""
    photos = getattr(pen, "photos", None)
    if not entry or photos is None:
        return False
    path = photos.dir / entry[0]
    if not path.is_file():
        return False
    from PIL import Image

    with Image.open(path) as img:
        ratio = img.width / img.height
    pic = pen.slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.name = name
    target = w / h
    if ratio > target:
        pic.crop_left = pic.crop_right = (1 - target / ratio) / 2
    else:
        pic.crop_top = (1 - ratio / target) * 0.4  # keep a little more of the top: faces, skies
        pic.crop_bottom = (1 - ratio / target) * 0.6
    if radius:
        pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
        geom = pic._element.spPr.find(qn("a:prstGeom"))
        av = geom.find(qn("a:avLst"))
        if av is None:
            av = geom.makeelement(qn("a:avLst"), {})
            geom.append(av)
        av.append(av.makeelement(qn("a:gd"), {"name": "adj", "fmla": f"val {int(min(0.5, radius / min(w, h)) * 100000)}"}))
    photos.note(entry[1])
    pen.credits = [*getattr(pen, "credits", []), entry[1]] if entry[1] else getattr(pen, "credits", [])
    return True


def veil(pen: S.Painter, x: float, y: float, w: float, h: float, strength: float = 55) -> None:
    """A flat dark veil over a photo, so white words read on it: one even tint, as designers do (few gradients)."""
    sp = pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, "0B0C10", "Voile")
    S._alpha(sp.fill._xPr.find(qn("a:solidFill")), strength)


def column(pen: S.Painter, entry: tuple[str, str] | None, side: str) -> None:
    """The slide's one strong visual, edge to edge on one side: a real photo; without one, a block of colour.
    Named for Morph: from one slide to the next it moves, grows or shrinks to its new place."""
    x = W - COLUMN if side == "right" else 0.0
    if not photo(pen, entry, x, 0, COLUMN, H, 0, "!!Panneau"):
        pen.shape(MSO_SHAPE.RECTANGLE, x, 0, COLUMN, H, _colours(pen.t)[0], "!!Panneau")


# --- drawing helpers ------------------------------------------------------------------------------

def _round(sp, radius: float) -> None:
    w, h = sp.width / 914400, sp.height / 914400
    sp.adjustments[0] = min(0.5, radius / max(min(w, h), 0.01))


def card(pen: S.Painter, x: float, y: float, w: float, h: float, fill: str | None = None, name: str = "Carte", edge: bool = True):
    """A flat card with a hairline edge: designers' decks almost never cast shadows."""
    t = pen.t
    sp = pen.slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.name = name
    sp.fill.solid()
    sp.fill.fore_color.rgb = S._rgb(fill or t["card_fill"])
    if edge:
        sp.line.color.rgb = S._rgb(t["line"])
        sp.line.width = Pt(0.75)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    S._no_style_effect(sp)
    _round(sp, 0.14)
    return sp


def _colours(t: dict) -> tuple[str, str]:
    """The colour of a block: on a dark page, the deep shade, so white text keeps its contrast."""
    return (t["deep"], S._mix(t["deep"], "000000", 0.35)) if t["dark"] else (t["accent"], t["deep"])


def strong_card(pen: S.Painter, x: float, y: float, w: float, h: float, name: str = "Carte en couleur"):
    """The one card that matters, in solid colour."""
    sp = card(pen, x, y, w, h, fill=_colours(pen.t)[0], name=name, edge=False)
    return sp


def hairline(pen: S.Painter, x: float, y: float, w: float, h: float = 0.014) -> None:
    pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, pen.t["line"], "Filet")


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


def lines(pen: S.Painter, x: float, y: float, w: float, h: float, rows: list[tuple[str, float, str, bool]], anchor=MSO_ANCHOR.TOP):
    """Several lines in one box, each its own paragraph: (text, size, colour, bold)."""
    box = pen.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for i, (text, size, colour, bold) in enumerate(rows):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        S._run(p, text, size, colour, bold)
    return box


def number_field(pen: S.Painter, x: float, y: float, w: float, h: float, number: int, size: float, colour: str) -> None:
    """The slide number as PowerPoint's own field: it follows when slides are moved."""
    box = pen.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.name = "Numéro de diapositive"
    frame = box.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    p = frame.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    fld = p._p.makeelement(qn("a:fld"), {"id": "{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}", "type": "slidenum"})
    rpr = fld.makeelement(qn("a:rPr"), {"lang": "fr-FR", "sz": str(int(size * 100)), "dirty": "0"})
    fill = rpr.makeelement(qn("a:solidFill"), {})
    fill.append(fill.makeelement(qn("a:srgbClr"), {"val": colour}))
    rpr.append(fill)
    rpr.append(rpr.makeelement(qn("a:latin"), {"typeface": BODY}))
    fld.append(rpr)
    text = fld.makeelement(qn("a:t"), {})
    text.text = str(number)
    fld.append(text)
    p._p.append(fld)


def word_fit(text: str, size: float, w: float, font: str = TITLE_FONT, bold: bool = True) -> float:
    """A size at which the longest word fits the width: a word is never cut in two ("Développeme-nt")."""
    longest = max(text.split(), key=len, default="")
    while size > 12 and S._span(longest, size, font, bold) > w * 0.97:
        size -= 1
    return size


def need(head: str, text: str, w: float, head_size: float, body_size: float) -> float:
    """Height of a short title and its text: a card is as tall as what it holds, as on Gamma."""
    return S.text_height(head, head_size, w, TITLE_FONT, True) + (0.1 + S.text_height(text, body_size, w) if text else 0)


def shared(items: list[dict], w: float, h: float, lead: float = LEAD, text: float = TEXT, floor: float = 13) -> tuple[float, float]:
    """One pair of sizes for things side by side, the largest at which every one fits its room: designers keep two
    or three sizes on a slide; shrinking each box on its own gave four or five."""
    lead = min(word_fit(it["head"], lead, w) for it in items)
    while lead > floor and max(need(it["head"], it.get("text") or "", w, lead, text) for it in items) > h:
        lead, text = lead - 1, max(text - 1, 12)
    return lead, text


# --- the frame of every slide ---------------------------------------------------------------------

def wants_panel(s: dict) -> bool:
    """The layouts that give one side of the slide to a photo."""
    kind = s.get("type")
    if kind == "liste":
        return len(s.get("items") or []) <= 4
    return kind in ("grand", "plan", "panneau")


def header(prs, t: dict, title: str, side: str) -> tuple[S.Painter, float, float]:
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    S._background(slide, t["bg"])
    pen = S.Painter(slide, t)
    pen.side = COLUMN if side else 0.0
    pen.left = COLUMN + GUTTER if side == "left" else M
    pen.right = W - COLUMN - GUTTER if side == "right" else W - M
    room = pen.right - pen.left
    size = 34 if len(title) <= 46 else 30 if len(title) <= 68 else 27
    if side:
        size = min(size, 30 if len(title) <= 40 else 27)
    return pen, room, size


def title(pen: S.Painter, text: str, mark: str, room: float, size: float) -> None:
    t = pen.t
    S._set_title(pen.slide, text, t["ink"], TITLE_FONT, size, pen.left, 0.62, room, 1.22, MSO_ANCHOR.TOP, mark=mark, mark_color=t["text_accent"])
    tight(pen.slide.shapes.title)


def standard(prs, t: dict, text: str, part: str | None, mark: str, s: dict | None = None, photos: Photos | None = None) -> S.Painter:
    """A content slide: its title and, for the layouts that take one, its photo column, laid before anything
    appears so that it stays put (and Morph carries it from the slide before)."""
    s = s or {}
    side = ""
    if wants_panel(s):
        side = "left" if s.get("type") == "panneau" else "right" if s.get("type") == "plan" or photos is None else photos.side()
    pen, room, size = header(prs, t, text, side)
    pen.photos = photos
    if side:
        column(pen, photos.pick(s.get("art", "")) if photos else None, side)
    title(pen, text, mark, room, size)
    pen.part = part
    return pen


def footer(pen: S.Painter, parts: list[str], current: str | None, number: int, total: int) -> None:
    """Where we are: a thin bar that fills along the talk (Morph makes it grow) and the slide's number."""
    t = pen.t
    start, end = getattr(pen, "left", M), getattr(pen, "right", W - M)
    y = 6.98
    track = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, start, y, end - start, 0.04, t["line"], "Piste")
    _round(track, 0.02)
    done = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, start, y, max((end - start) * number / max(total, 1), 0.06), 0.04, t["accent"], "!!Progression")
    _round(done, 0.02)
    number_field(pen, end - 1.2, y + 0.12, 1.2, 0.28, number, 11, t["muted"])


def takeaway(pen: S.Painter, text: str) -> None:
    t = pen.t
    y = pen.bottom + 0.16
    left, right = getattr(pen, "left", M), getattr(pen, "right", W - M)
    band = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, y, right - left, 0.6, t["tint"], "À retenir")
    _round(band, 0.3)
    pen.text(left + 0.3, y, right - left - 0.6, 0.6, text, TEXT, t["ink"], True, anchor=MSO_ANCHOR.MIDDLE)


# --- pages ----------------------------------------------------------------------------------------

def _title_size(text: str, room: float, height: float, largest: float = 54, most: int = 3) -> float:
    """As large as the room allows, on `most` lines at most: designers' covers carry a big title (median 64 pt)."""
    size = word_fit(text, largest, room)
    while size > 24 and (S.text_lines(text, size, room, TITLE_FONT, True) > most or S.text_height(text, size, room, TITLE_FONT, True) > height):
        size -= 2
    return size


def cover(prs, t: dict, info: dict, images_dir: Path, seed: int = 0, photos: Photos | None = None):
    """The title as large as it can be, three blocks of one size around it, and the photo: a column the full height
    of the slide, or the whole slide behind a veil (every other document, when there is no logo to show)."""
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    S._background(slide, t["bg"])
    pen = S.Painter(slide, t)
    pen.photos = photos
    entry = photos.cover() if photos else None
    full = bool(entry) and not info.get("logos") and seed % 2 == 1
    if full and photo(pen, entry, 0, 0, W, H, 0, "!!Panneau"):
        veil(pen, 0, 0, W, H, 58)
        ink, muted, right = "FFFFFF", S._mix("FFFFFF", "0B0C10", 0.22), W - M - 2.6
    else:
        wide = 5.6
        if not photo(pen, entry, W - wide, 0, wide, H, 0, "!!Panneau"):
            pen.shape(MSO_SHAPE.RECTANGLE, W - wide, 0, wide, H, _colours(t)[0], "!!Panneau")
        ink, muted, right = t["ink"], t["muted"], W - wide - GUTTER
    room = right - M
    y = 0.7
    if info.get("logos"):
        for i, name in enumerate(info["logos"][:2]):
            S._picture(pen, images_dir / str(name), M + i * 1.1, y, 0.95, 0.95)
        y += 1.15
    head = [line for line in info.get("header") or [] if line.strip()][-3:]
    if head:
        tall = sum(S.text_height(line, 12, room) for line in head)
        lines(pen, M, y, room, tall, [(line, 12, muted, False) for line in head])
        y += tall + 0.3
    sub = ", ".join(x for x in (info.get("label"), info.get("specialty")) if x)
    people = [(info.get("by_label") or "Présenté par", info.get("author_lines") or info.get("authors") or []),
              (info.get("under_label") or "", info.get("supervisor_lines") or [])]
    people = [(label, names[:3]) for label, names in people if names and label]
    if info.get("year"):
        people.append(("Academic year" if info.get("english") else "Année académique", [info["year"]]))
    bottom = 5.3 if people else 6.6
    top = max(y, 1.6)
    name = info["title"]
    height = bottom - 0.35 - top - (0.55 if sub else 0)
    size = _title_size(name, room, height)
    tall = min(S.text_height(name, size, room, TITLE_FONT, True), height)
    top = max(top, top + (height - tall) * 0.5)  # the title block sits in the middle of its room
    S._set_title(slide, name, ink, TITLE_FONT, size, M, top, room, tall + 0.05, MSO_ANCHOR.TOP)
    tight(slide.shapes.title)
    if sub:
        pen.text(M, top + tall + 0.25, room, 0.45, sub, INFO, muted)
    if people:
        space = H - bottom - 0.35
        size = INFO  # one size for the whole foot of the cover, one block

        def tall(size: float) -> float:
            return sum(S.text_height(f"{label} {', '.join(names)}", size, room, bold=True) + 5 / 72 for label, names in people)

        while size > 11 and tall(size) > space:
            size -= 1
        box = lines(pen, M, bottom, room, min(space, tall(size) + 0.05), [])
        frame = box.text_frame
        for i, (label, names) in enumerate(people):
            p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            p.space_after = Pt(5)
            S._run(p, f"{label} ", size, muted)
            S._run(p, ", ".join(names), size, ink, True)
        box.name = "Auteurs"
    slide.credits = getattr(pen, "credits", [])
    return slide


def _colour_page(prs, t: dict, photos: Photos | None = None, entry: tuple[str, str] | None = None):
    """A page all photo (or all colour), named as the photo columns: Morph grows a column into it, or shrinks it
    into the next slide's column."""
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    S._background(slide, t["deep"])
    pen = S.Painter(slide, t)
    pen.photos = photos
    if photo(pen, entry, 0, 0, W, H, 0, "!!Panneau"):
        veil(pen, 0, 0, W, H, 55)
        slide.credits = getattr(pen, "credits", [])
        return slide, pen
    pen.shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H, _colours(t)[0], "!!Panneau")
    slide.credits = []
    return slide, pen


def section(prs, t: dict, text: str, number: int, seed: int = 0, photos: Photos | None = None, own: str = ""):
    slide, pen = _colour_page(prs, t, photos, photos.pick(own) if photos else None)
    pen.text(M, 1.6, 5, 1.8, f"{number:02d}", 120, "FFFFFF", True, TITLE_FONT).name = f"!!Partie {number}"  # the outline's number grows into it (Morph)
    S._set_title(slide, text, "FFFFFF", TITLE_FONT, 46 if len(text) <= 40 else 38, M, 3.75, 9.6, 2.2, MSO_ANCHOR.TOP)
    tight(slide.shapes.title)
    return slide


def end(prs, t: dict, thanks: str, info: dict, images_dir: Path, seed: int = 0, photos: Photos | None = None):
    credits = list(photos.used) if photos else []  # every photo shown before: their authors and licences
    slide, pen = _colour_page(prs, t, photos, photos.cover() if photos else None)
    S._set_title(slide, thanks, "FFFFFF", TITLE_FONT, 52 if len(thanks) <= 28 else 42, M, 2.35, W - 2 * M, 1.7, MSO_ANCHOR.BOTTOM, PP_ALIGN.CENTER)
    tight(slide.shapes.title)
    who = ", ".join((info.get("authors") or [])[:3])
    size, room = 18, W - 2 * M - 2.0
    while size > 12 and S.text_height(info["title"], size, room) + (S.text_height(who, size, room, bold=True) + 8 / 72 if who else 0) > 1.9:
        size -= 1
    rows = [(info["title"], size, S._mix("FFFFFF", t["accent"], 0.2), False)] + ([(who, size, "FFFFFF", True)] if who else [])
    box = lines(pen, M + 1.0, 4.3, room, 2.0, rows)
    for p in box.text_frame.paragraphs:
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(8)
    if photos:
        credits += [c for c in photos.used if c not in credits]
    if credits:
        label = "Images : " if any(not c.startswith("Photo : ") for c in credits) else "Photos : "  # an AI picture is no photo
        pen.text(M, 6.55, W - 2 * M, 0.7, label + " ; ".join(c.removeprefix("Photo : ") for c in credits[:8]), 9, "FFFFFF", align=PP_ALIGN.CENTER).name = "Crédits des photos"
    return slide


def plan(pen: S.Painter, parts: list[str]) -> None:
    t = pen.t
    n = max(len(parts), 1)
    row = min(0.95, (BOTTOM - TOP) / n)
    y0 = TOP + ((BOTTOM - TOP) - row * n) * 0.35
    x, room = pen.left, pen.right - pen.left
    size = min(24, min((word_fit(p, 24, room - 1.05) for p in parts), default=24))
    for i, name in enumerate(parts):
        pen.step()
        y = y0 + i * row
        pen.text(x, y, 0.9, row - 0.1, f"{i + 1:02d}", size, t["text_accent"], True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE).name = f"!!Partie {i + 1}"
        pen.text(x + 1.05, y, room - 1.05, row - 0.1, name, size, t["ink"], True, TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
        if i < n - 1:
            hairline(pen, x, y + row - 0.04, room)


# --- content layouts ------------------------------------------------------------------------------

def _liste(pen: S.Painter, s: dict) -> None:
    t, items = pen.t, s["items"]
    n = len(items)
    x, room = pen.left, pen.right - pen.left
    avail = pen.bottom - TOP
    row = min(1.3, avail / n)
    y0 = TOP + (avail - row * n) * 0.3
    lead, text = shared(items, room, row - 0.22, 24, 18)
    for i, it in enumerate(items):
        pen.step()
        y = y0 + i * row
        pen.stack(x, y + 0.02, room, row - 0.2, it["head"], it["text"], lead, text)
        if i < n - 1:
            hairline(pen, x, y + row - 0.1, room)


def _card_sizes(cols: int) -> tuple[float, float]:
    return (24, 18) if cols <= 3 else (22, 17)


def _cards_height(items: list[dict], cols: int, width: float = W - 2 * M) -> float:
    w = (width - 0.3 * (cols - 1)) / cols - 0.64
    lead, text = shared(items, w, 99, *_card_sizes(cols))
    return max(need(it["head"], it["text"], w, lead, text) for it in items) + 0.9


def _cards_row(pen: S.Painter, items: list[dict], y: float, h: float, cols: int, first_strong: bool, sizes: tuple[float, float], x0: float = M,
               width: float | None = None) -> None:
    t = pen.t
    gap = 0.3
    width = width or (W - 2 * M)
    w = (width - gap * (cols - 1)) / cols
    for i, it in enumerate(items):
        pen.step()
        x = x0 + i * (w + gap)
        strong = first_strong and i == 0
        (strong_card if strong else card)(pen, x, y, w, h)
        pen.stack(x + 0.32, y + 0.36, w - 0.64, h - 0.62, it["head"], it["text"], *sizes,
                  head_color="FFFFFF" if strong else None, body_color=S._mix("FFFFFF", t["accent"], 0.12) if strong else None)


def _grille(pen: S.Painter, s: dict) -> None:
    items = s["items"]
    n = len(items)
    avail = pen.bottom - TOP
    strong = pen.variant("studio-grille", 2) == 1 and n in (3, 4)
    cols = n if n <= 4 else 3
    w = (W - 2 * M - 0.3 * (cols - 1)) / cols - 0.64
    if n <= 4:
        h = min(max(_cards_height(items, n), 2.6), avail - 0.1)
        sizes = shared(items, w, h - 0.62, *_card_sizes(cols))
        _cards_row(pen, items, TOP + (avail - h) * 0.45, h, n, strong, sizes)
    else:
        h = min(max(_cards_height(items, cols), 1.6), (avail - 0.3) / 2)
        sizes = shared(items, w, h - 0.62, 21, 16.5)
        _cards_row(pen, items[:cols], TOP, h, cols, False, sizes)
        _cards_row(pen, items[cols:], TOP + h + 0.3, h, cols, False, sizes)


def _schema(pen: S.Painter, s: dict) -> None:
    """The idea in the middle, its parts around it, linked by thin lines."""
    t, items = pen.t, s["items"]
    avail = pen.bottom - TOP
    d = 2.3
    cx, cy = W / 2, TOP + avail / 2
    left, right = items[: (len(items) + 1) // 2], items[(len(items) + 1) // 2:]
    cw = (W - 2 * M - d - 1.2) / 2
    links = []
    boxes = []
    k = max(len(left), len(right))
    gap = 0.25
    ch = min(1.45, (avail - gap * (k - 1)) / k)
    for side, group in ((0, left), (1, right)):
        y0 = TOP + (avail - (ch * len(group) + gap * (len(group) - 1))) / 2
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
    hub = pen.shape(MSO_SHAPE.OVAL, cx - d / 2, cy - d / 2, d, d, _colours(t)[0], "Centre")
    hub.shadow.inherit = False
    key = s.get("key") or s["title"].split(" ")[0]
    size = word_fit(key, S._fit(len(key), [(14, 22), (24, 18), (40, 15), (10_000, 12)]), d - 0.5)
    pen.text(cx - d / 2 + 0.25, cy - d / 2 + 0.3, d - 0.5, d - 0.6, key, size, "FFFFFF", True, TITLE_FONT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    sizes = shared(items, cw - 0.6, ch - 0.2, 18, 14.5, floor=12)
    for x, y, w, h, it in boxes:
        pen.step()
        card(pen, x, y, w, h)
        pen.stack(x + 0.3, y + 0.1, w - 0.6, h - 0.2, it["head"], it["text"], *sizes, anchor=MSO_ANCHOR.MIDDLE)


def _panneau(pen: S.Painter, s: dict) -> None:
    """The photo column on the left with the slide's key line on it, the points on the right."""
    t, items = pen.t, s["items"]
    avail = pen.bottom - TOP
    key = s.get("key") or ""
    if key:
        pen.step()
        veil(pen, 0, 0, COLUMN, H, 45)
        pen.text(M, TOP, COLUMN - M - 0.6, avail, key, S._fit(len(key), [(50, 32), (80, 28), (10_000, 24)]), "FFFFFF", True, TITLE_FONT,
                 anchor=MSO_ANCHOR.BOTTOM)
    x, room = pen.left, pen.right - pen.left
    n = len(items)
    row = min(1.3, avail / n)
    lead, text = shared(items, room, row - 0.24, 21, 17)
    for i, it in enumerate(items):
        pen.step()
        y = TOP + i * row
        pen.stack(x, y + 0.05, room, row - 0.22, it["head"], it["text"], lead, text)
        if i < n - 1:
            hairline(pen, x, y + row - 0.1, room)


def _chronologie(pen: S.Painter, s: dict) -> None:
    """A line through time: the dates above, what happened below, no boxes."""
    t, items = pen.t, s["items"]
    n = len(items)
    avail = pen.bottom - TOP
    w = (W - 2 * M) / n
    lead = min(word_fit(x["head"], 24 if n <= 4 else 20, w - 0.3) for x in items)
    size = 18 if n <= 4 else 15
    room = pen.bottom - TOP - 1.35
    while size > 12 and max(S.text_height(x["text"], size, w - 0.4) for x in items) > room:
        size -= 1
    tall = max(S.text_height(x["text"], size, w - 0.4) for x in items)
    block = 0.9 + 0.45 + tall
    line_y = TOP + max((avail - block) * 0.45, 0) + 0.9
    track = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, M, line_y - 0.02, W - 2 * M, 0.04, S._mix(t["bg"], t["accent"], 0.3), "Ligne")
    _round(track, 0.02)
    for i, it in enumerate(items):
        pen.step()
        cx = M + i * w + w / 2
        pen.text(M + i * w + 0.15, line_y - 0.9, w - 0.3, 0.7, it["head"], lead, t["text_accent"], True, TITLE_FONT, PP_ALIGN.CENTER, MSO_ANCHOR.BOTTOM)
        dot = pen.shape(MSO_SHAPE.OVAL, cx - 0.15, line_y - 0.15, 0.3, 0.3, t["accent"], "Point")
        dot.line.color.rgb = S._rgb(t["bg"])
        dot.line.width = Pt(3)
        pen.text(M + i * w + 0.2, line_y + 0.45, w - 0.4, pen.bottom - line_y - 0.45, it["text"], size, t["ink"], align=PP_ALIGN.CENTER)


def _etapes(pen: S.Painter, s: dict) -> None:
    """Steps side by side: a line in colour on top of each, its number, its name, what it is. No boxes, no arrows."""
    t, items = pen.t, s["items"]
    n = len(items)
    avail = pen.bottom - TOP
    gap = 0.45
    w = (W - 2 * M - gap * (n - 1)) / n
    lead, text = shared(items, w, avail - 1.0, *((22, 17.5) if n <= 4 else (19, 15)))
    h = max(need(it["head"], it["text"], w, lead, text) for it in items) + 0.95
    y = TOP + max((avail - h) * 0.4, 0)
    for i, it in enumerate(items):
        pen.step()
        x = M + i * (w + gap)
        pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, 0.06, t["accent"], "Trait")
        pen.text(x, y + 0.3, w, 0.5, f"{i + 1:02d}", lead, t["text_accent"], True, TITLE_FONT)
        pen.stack(x, y + 0.85, w, h - 0.85, it["head"], it["text"], lead, text)


def _comparaison(pen: S.Painter, s: dict) -> None:
    t = pen.t
    avail = pen.bottom - TOP
    gap = 0.4
    w = (W - 2 * M - gap) / 2
    size = 19
    tall = max(sum(S.text_height(p, size, w - 0.84 - 0.34) + 10 / 72 for p in side["points"]) for side in (s["left"], s["right"]))
    h = min(max(1.15 + tall + 0.45, 3.0), avail - 0.1)
    top = TOP + (avail - h) * 0.45
    for i, side in enumerate((s["left"], s["right"])):
        pen.step()
        x = M + i * (w + gap)
        strong = i == 1
        sp = card(pen, x, top, w, h, fill=t["tint"] if strong else None)
        if strong:
            sp.line.color.rgb = S._rgb(t["accent"])
            sp.line.width = Pt(1.5)
        pen.text(x + 0.42, top + 0.36, w - 0.84, 0.6, side["title"] or " ", 22, t["text_accent"] if strong else t["ink"], True, TITLE_FONT)
        points(pen, x + 0.42, top + 1.15, w - 0.84, h - 1.4, side["points"], size, t["accent"] if strong else t["muted"])


def _chiffres(pen: S.Painter, s: dict) -> None:
    """Figures as designers set them: very big, no boxes, a thin line between them, what they count below."""
    t, stats = pen.t, s["stats"]
    n = len(stats)
    avail = pen.bottom - TOP
    w = (W - 2 * M) / n
    longest = max(len(x["value"]) for x in stats)
    size = S._fit(int(longest * 4 / n), [(6, 80), (9, 64), (13, 48), (10_000, 34)])
    size = min(word_fit(x["value"], size, w - 0.5) for x in stats)
    label = TEXT
    while label > 13 and max(S.text_height(x["label"], label, w - 0.5) for x in stats) > 1.3:
        label -= 1
    tall = size * S.LINE / 72
    block = tall + 0.25 + 1.3
    y = TOP + max((avail - block) * 0.45, 0)
    for i, st in enumerate(stats):
        pen.step("zoom")
        x = M + i * w
        if i:
            hairline(pen, x, y, 0.014, block)
        inset = 0.25 if i else 0.0
        pen.text(x + inset, y, w - 0.5, tall, st["value"], size, t["text_accent"], True, TITLE_FONT, anchor=MSO_ANCHOR.BOTTOM)
        pen.text(x + inset, y + tall + 0.25, w - 0.5, 1.3, st["label"], label, t["muted"])


def _graphique(pen: S.Painter, s: dict) -> None:
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION

    t = pen.t
    key = s.get("key") or ""
    avail = pen.bottom - TOP
    w = 7.6 if key else W - 2 * M
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
    chart.font.size, chart.font.name = Pt(16), BODY
    chart.font.color.rgb = S._rgb(t["ink"])
    chart.has_title = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.show_value, labels.font.size, labels.font.bold = True, Pt(16), True
    series = plot.series[0]
    colors = [t["accent"], t["second"], S._mix(t["accent"], t["card_fill"], 0.45), S._mix(t["second"], t["card_fill"], 0.45), t["deep"], t["muted"]]
    if donut:
        labels.show_percentage = False
        chart.has_legend = True
        chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.RIGHT, False
        chart.legend.font.size = Pt(16)
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
    strong_card(pen, x, TOP, room, avail)
    pen.text(x + 0.36, TOP + 0.4, room - 0.72, 1.1, figure, word_fit(figure, 56 if len(figure) <= 4 else 40, room - 0.72), "FFFFFF", True, TITLE_FONT,
             anchor=MSO_ANCHOR.BOTTOM)
    pen.text(x + 0.36, TOP + 1.6, room - 0.72, 0.5, top["label"], TEXT, S._mix("FFFFFF", t["accent"], 0.15), True)
    pen.text(x + 0.36, TOP + 2.3, room - 0.72, avail - 2.6, key, S._fit(len(key), [(70, LEAD), (120, 18), (10_000, 16)]), "FFFFFF", True, TITLE_FONT)


def _encadre(pen: S.Painter, s: dict) -> None:
    t = pen.t
    avail = pen.bottom - TOP
    h = avail - 0.15
    pen.step()
    card(pen, M, TOP, W - 2 * M, h, fill=t["tint"], name="Encadré", edge=False)
    if s.get("label"):
        pen.text(M + 0.6, TOP + 0.45, W - 2 * M - 1.2, 0.45, s["label"][:40], LEAD, t["text_accent"], True, TITLE_FONT).name = "Étiquette"
    pen.text(M + 0.5, TOP + 0.95, 1.2, 1.4, "“", 110, t["accent"], True, TITLE_FONT)
    pen.step()
    text = s["text"]
    pen.text(M + 1.6, TOP + 1.1, W - 2 * M - 2.4, h - 1.5, text, S._fit(len(text), [(90, 34), (150, 29), (10_000, 25)]), t["ink"], True, TITLE_FONT,
             anchor=MSO_ANCHOR.MIDDLE)


def _grand(pen: S.Painter, s: dict) -> None:
    t = pen.t
    value = s["value"]
    x, room = pen.left, pen.right - pen.left
    pen.step("zoom")
    size = word_fit(value, S._fit(len(value), [(5, 140), (9, 100), (14, 72), (10_000, 50)]), room)
    pen.text(x, TOP + 0.1, room, 2.6, value, size, t["text_accent"], True, TITLE_FONT, anchor=MSO_ANCHOR.BOTTOM)
    pen.step()
    pen.text(x, TOP + 2.95, room, 1.6, s.get("text") or "", 24, t["ink"], True)


def _figure(pen: S.Painter, s: dict, images_dir: Path) -> None:
    t = pen.t
    items = s.get("points") or []
    caption = s.get("caption") or ""
    avail = pen.bottom - TOP
    w = 7.6 if items else W - 2 * M
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
    column_w = width / cols - 0.24

    def heights(size: float) -> list[float]:
        return [max(max(S.text_height(c, size, column_w, bold=r == 0) for c in row) + 0.16, 0.46) for r, row in enumerate(rows)]

    size = 18
    while size > 10 and sum(heights(size)) > room:
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
