"""Draws the presentation written by deck.py as a real PowerPoint: titles, text, shapes, tables and charts stay editable.

A style is a palette + a skin: how the title sits (rule, band, side, tab), how a card looks (soft, line, bar), which
page de garde (classic, split, full). Fonts are Calibri, Cambria and Arial: on every PowerPoint, and drawn with the same
widths by Carlito, Caladea and Liberation on the server, so the preview tells the truth about what fits.
Icons: Lucide (icons/LICENSE).
"""
from __future__ import annotations

import io
import math
import re
import zlib
from collections import Counter
from functools import lru_cache
from pathlib import Path

import resvg_py
from lxml import etree
from PIL import Image, ImageFont
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from .art import halo, mesh

WIDTH, HEIGHT = 13.333, 7.5  # inches, everything below is in inches
LEFT = 0.75
CONTENT_WIDTH = WIDTH - 2 * LEFT
TOP = 1.8
BOTTOM = 6.78
STRIP = 7.04  # the progress bar: the parts of the talk, the current one lit, as in a thesis defence
ICONS_DIR = Path(__file__).with_name("icons")
DARK = "1C1C1E"


def _style(label, bg, panel, ink, muted, accent, second, on_accent, deep, font, skin, card, cover, motif):
    return {"label": label, "bg": bg, "panel": panel, "ink": ink, "muted": muted, "accent": accent, "second": second, "on_accent": on_accent,
            "deep": deep, "title_font": font, "skin": skin, "card": card, "cover": cover, "motif": motif, "dark": int(bg[:2], 16) < 90}


THEMES = {
    "academique": _style("Académique", "FFFFFF", "EEF2F7", "14233A", "4D5D73", "1F3A5F", "C9A227", "FFFFFF", "142842", "Cambria", "rule", "soft", "classic", "barre"),
    "sorbonne": _style("Sorbonne", "FBF8F3", "F1E8DD", "33151A", "6E5257", "7A1F2E", "C49A3A", "FFFFFF", "561420", "Cambria", "band", "line", "classic", ""),
    "campus": _style("Campus", "FFFFFF", "EAF6F0", "12322A", "4F6B62", "0E7C5A", "F2B632", "FFFFFF", "0A5A41", "Calibri", "side", "soft", "split", "cercles"),
    "savane": _style("Savane", "FDF9F0", "F5EAD3", "33261A", "6F5C47", "B4581F", "3F7D4E", "FFFFFF", "85400F", "Cambria", "tab", "bar", "split", "diagonale"),
    "ocean": _style("Océan", "FFFFFF", "E4F4F6", "0D3440", "47686F", "0B7A8C", "F97352", "FFFFFF", "075766", "Calibri", "band", "soft", "full", ""),
    "medical": _style("Médical", "F7FBFC", "E1F1F3", "10343B", "4B6A70", "0F8B8D", "3B82C4", "FFFFFF", "0A6668", "Calibri", "tab", "line", "split", "points"),
    "royal": _style("Royal", "FFFFFF", "ECEBFB", "1E1B4B", "57537F", "4338CA", "EC4899", "FFFFFF", "2F2692", "Calibri", "side", "bar", "full", "cercles"),
    "corail": _style("Corail", "FFF8F1", "FFE9DB", "3A1D14", "7A5A4E", "E4572E", "F3A712", "FFFFFF", "B23E1B", "Cambria", "rule", "soft", "full", "diagonale"),
    "soleil": _style("Soleil", "FFFDF5", "FFF3C7", "26221A", "5F5745", "26221A", "F5B800", "FFFFFF", "000000", "Arial", "band", "bar", "split", ""),
    "ardoise": _style("Ardoise", "F4F4F2", "FFFFFF", "1C1C1E", "5C5C60", "2B2D33", "D97706", "FFFFFF", "16171A", "Cambria", "rule", "line", "classic", "barre"),
    "nuit": _style("Nuit", "0F172A", "1E293B", "F1F5F9", "A9B6C8", "22D3EE", "A78BFA", "0F172A", "0EA5C0", "Calibri", "rule", "soft", "full", "points"),
    "neon": _style("Néon", "14101F", "241C38", "F5F0FF", "B5A9CF", "E879F9", "22D3EE", "14101F", "B63FCB", "Arial", "tab", "line", "split", "cercles"),
}
# Each style has its own shapes, not only its colours: pastille, card, frame of the title, decoration.
LOOKS = {
    "academique": (MSO_SHAPE.OVAL, MSO_SHAPE.ROUNDED_RECTANGLE, "double", "barre"),
    "sorbonne": (MSO_SHAPE.OCTAGON, MSO_SHAPE.RECTANGLE, "double", ""),
    "campus": (MSO_SHAPE.OVAL, MSO_SHAPE.ROUND_2_SAME_RECTANGLE, "ribbon", "cercles"),
    "savane": (MSO_SHAPE.HEXAGON, MSO_SHAPE.SNIP_1_RECTANGLE, "wave", "triangles"),
    "ocean": (MSO_SHAPE.TEAR, MSO_SHAPE.ROUNDED_RECTANGLE, "wave", "vague"),
    "medical": (MSO_SHAPE.ROUNDED_RECTANGLE, MSO_SHAPE.ROUNDED_RECTANGLE, "ribbon", "croix"),
    "royal": (MSO_SHAPE.DIAMOND, MSO_SHAPE.RECTANGLE, "wave", "rayures"),
    "corail": (MSO_SHAPE.OVAL, MSO_SHAPE.ROUND_1_RECTANGLE, "ribbon", "arcs"),
    "soleil": (MSO_SHAPE.HEXAGON, MSO_SHAPE.SNIP_2_DIAG_RECTANGLE, "box", "soleil"),
    "ardoise": (MSO_SHAPE.RECTANGLE, MSO_SHAPE.RECTANGLE, "double", "barre"),
    "nuit": (MSO_SHAPE.HEXAGON, MSO_SHAPE.SNIP_1_RECTANGLE, "box", "points"),
    "neon": (MSO_SHAPE.OCTAGON, MSO_SHAPE.ROUND_2_DIAG_RECTANGLE, "box", "hexagones"),
    "contraste": (MSO_SHAPE.RECTANGLE, MSO_SHAPE.RECTANGLE, "ribbon", ""),
    "vitamine": (MSO_SHAPE.ROUNDED_RECTANGLE, MSO_SHAPE.ROUND_2_DIAG_RECTANGLE, "wave", "organique"),
    "terre": (MSO_SHAPE.TEAR, MSO_SHAPE.ROUNDED_RECTANGLE, "double", "organique"),
    "foret": (MSO_SHAPE.ROUND_2_DIAG_RECTANGLE, MSO_SHAPE.ROUND_2_DIAG_RECTANGLE, "wave", "feuilles"),
}
THEMES["contraste"] = _style("Contraste", "FFFFFF", "F5F5F5", "111111", "55585C", "FF6A00", "111111", "FFFFFF", "D95500", "Arial", "rule", "line", "full", "")
THEMES["vitamine"] = _style("Vitamine", "FFFFFF", "FFF0E6", "3A2A20", "75635A", "F4600C", "FFB000", "FFFFFF", "C93F00", "Calibri", "rule", "soft", "full", "organique")
THEMES["terre"] = _style("Terre", "FFFCF8", "F3EADF", "3B2A20", "75625A", "8A5A3C", "C9A27E", "FFFFFF", "63402A", "Cambria", "rule", "soft", "split", "organique")
THEMES["foret"] = _style("Forêt", "FFFFFF", "E8F5EC", "143323", "4D6B5A", "00843D", "F7C800", "FFFFFF", "005C2A", "Calibri", "rule", "soft", "full", "organique")
for name, theme in THEMES.items():
    modern = name in ("contraste", "vitamine", "terre", "foret", "royal", "corail", "neon", "nuit", "ocean")
    theme.update(badge=LOOKS[name][0], corner=LOOKS[name][1], frame=LOOKS[name][2])
    theme["motif"] = LOOKS[name][3]
    theme.update(caps=name == "contraste", foot="line" if modern and name not in ("ocean", "neon") else "strip", kicker=modern and theme["skin"] == "rule", alt=name == "contraste")
# New generation: a field of colour on every slide, glass cards, big type.
GLASS = {
    "aurora": _style("Aurora", "12102B", "FFFFFF", "FFFFFF", "C9C6E8", "A78BFA", "22D3EE", "12102B", "7C5CF0", "Arial", "rule", "soft", "hero", "") | {"mesh": ("12102B", "3B1E8F", "0E7490", "6D28D9", "1E1B4B")},
    "braise": _style("Braise", "1A0B0B", "FFFFFF", "FFFFFF", "E9CFC4", "FF7A3D", "FFC24B", "1A0B0B", "D9480F", "Arial", "rule", "soft", "hero", "") | {"mesh": ("1A0B0B", "9A2A12", "D9480F", "6B1D3A", "2B0F12")},
    "lagon": _style("Lagon", "04232B", "FFFFFF", "FFFFFF", "BFE3E6", "2DD4BF", "FDE68A", "04232B", "0F9D8F", "Calibri", "rule", "soft", "hero", "") | {"mesh": ("04232B", "0F766E", "0369A1", "134E4A", "082F49")},
    "minuit": _style("Minuit", "0B1220", "FFFFFF", "FFFFFF", "C4CDDC", "E9C46A", "60A5FA", "0B1220", "C9A227", "Cambria", "rule", "soft", "hero", "") | {"mesh": ("0B1220", "1E3A5F", "1F2A44", "3A2E12", "0F1B33")},
    "perle": _style("Perle", "F6F3FF", "FFFFFF", "1E1B3A", "54507A", "6D3BEA", "EC4899", "FFFFFF", "4C22C2", "Arial", "rule", "soft", "hero", "") | {"mesh": ("F4F1FF", "D9CCFF", "FFD6E8", "C7E9FF", "FFF1CC")},
    "menthe": _style("Menthe", "F1FBF6", "FFFFFF", "10302A", "47665E", "0E8F6E", "F59E0B", "FFFFFF", "0A6B52", "Calibri", "rule", "soft", "hero", "") | {"mesh": ("EFFBF5", "BFF0DD", "FDE9B8", "C5EAFB", "DDF7E9")},
}
for name, theme in GLASS.items():
    theme.update(badge=MSO_SHAPE.ROUNDED_RECTANGLE, corner=MSO_SHAPE.ROUNDED_RECTANGLE, frame="box", caps=False, foot="line", kicker=True, alt=False, glass=True)
THEMES.update(GLASS)
# Sweeping curves, as on the great PowerPoint templates: on the cover, at the corner of every slide, on the edge of the colour block.
CURVES = {
    "prairie": _style("Prairie", "FFFFFF", "EFF6E8", "1F3312", "56694B", "4E8A1F", "8CC63F", "FFFFFF", "2F5D14", "Calibri", "curve", "soft", "sweep", ""),
    "horizon": _style("Horizon", "FFFFFF", "E9F4F1", "12403C", "4D6A66", "1B6F6A", "7CB518", "FFFFFF", "0F4F4B", "Calibri", "curve", "soft", "wave", ""),
    "azur": _style("Azur", "F7F8FA", "E8EEF7", "16263F", "526077", "2A5CAA", "7FA8D9", "FFFFFF", "173B75", "Arial", "curve", "soft", "fold", ""),
    "graphite": _style("Graphite", "FFFFFF", "F0F1F3", "202328", "5A5F67", "3C4047", "9AA0A8", "FFFFFF", "24272C", "Calibri", "curve", "soft", "sweep", ""),
    "ambre": _style("Ambre", "FFFBF2", "FBEFD3", "3A1A10", "6F5546", "5A1A0E", "F2B71F", "FFFFFF", "3C0F07", "Cambria", "curve", "soft", "swoosh", ""),
    "citron": _style("Citron", "FFFFFF", "F0F9E3", "20370C", "57694A", "3F9A0A", "B6E34A", "FFFFFF", "2B7004", "Arial", "curve", "soft", "arc", ""),
}
# Light and airy: a veil of colour at the top, serif titles with a word in italics, the plan as a small menu.
HALO = {
    "halo": _style("Halo", "FFFFFF", "F1F7EC", "24421A", "5B6D54", "2F6B1F", "8BBF5A", "FFFFFF", "1F4D13", "Arial", "halo", "accent", "halo", ""),
    "iris": _style("Iris", "FFFFFF", "F1EFFC", "1E1B3A", "5A5677", "4C2AB0", "E0245E", "FFFFFF", "331B85", "Cambria", "halo", "accent", "halo", ""),
    "brume": _style("Brume", "FFFFFF", "EAF4F8", "12303C", "4E6771", "12708C", "F08A5D", "FFFFFF", "0B4F66", "Cambria", "halo", "accent", "halo", ""),
}
for name, theme in (CURVES | HALO).items():
    theme.update(badge=MSO_SHAPE.OVAL, corner=MSO_SHAPE.ROUNDED_RECTANGLE, frame="box", caps=False, foot="line", kicker=True, alt=False, lean=name in HALO)
THEMES.update(CURVES | HALO)
DEFAULT_THEME = "academique"
# The style that suits the subject, when the user lets Paginya choose ("auto").
SUBJECTS = (
    (r"infirm|sant[eé]\b|m[eé]dic|h[oô]pital|soins|pharma|patient|maladie|clinique|health", ("medical", "brume", "horizon", "menthe")),
    (r"informatique|logiciel|d[eé]veloppement web|plateforme|algorithm|r[eé]seau|donn[eé]es|software|machine learning|intelligence artificielle", ("aurora", "minuit", "azur", "iris", "graphite")),
    (r"agricul|agronom|for[eê]t|environnement|[eé]colog|climat|[eé]levage|plantation", ("prairie", "citron", "halo", "horizon", "menthe")),
    (r"droit|juridi|justice|\bloi\b|administration publique|politique", ("minuit", "ambre", "sorbonne", "graphite")),
    (r"gestion|comptab|financ|banque|marketing|commerce|entreprise|microfinance|[eé]conomi", ("azur", "ambre", "minuit", "graphite", "iris")),
    (r"histoire|lettres|litt[eé]rature|philosoph|sociolog|anthropolog|culture", ("ambre", "iris", "sorbonne", "terre")),
    (r"p[eé]dagog|[eé]ducation|enseignement|[eé]cole\b|apprentissage", ("halo", "iris", "perle", "citron")),
)
BY_KIND = {"memoire": ("azur", "ambre", "academique"), "rapport_stage": ("prairie", "azur", "horizon"), "rapport": ("azur", "horizon", "brume"),
           "expose": ("halo", "iris", "citron", "aurora"), "cours": ("brume", "halo", "perle")}


def choose_theme(document: dict) -> str:
    """Two documents about different things do not get the same look; two about the same thing can still differ."""
    blocks = document.get("blocks") or []
    text = " ".join(str(b.get("text") or "") for b in blocks[:150]).lower()
    best, hits = (), 0
    for pattern, themes in SUBJECTS:
        found = len(re.findall(pattern, text))
        if found > hits:
            best, hits = themes, found
    choices = best or BY_KIND.get((document.get("meta") or {}).get("kind"), ("halo", "iris", "azur", "prairie"))
    return choices[zlib.crc32(text[:400].encode()) % len(choices)]
BODY_FONT = "Calibri"


def _rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def _mix(a: str, b: str, part: float) -> str:
    """`part` of colour b over colour a: the see-through look of a shape, without transparency (kept when printed)."""
    return "".join(f"{round(int(a[i:i + 2], 16) * (1 - part) + int(b[i:i + 2], 16) * part):02X}" for i in (0, 2, 4))


def _readable(fill: str, t: dict) -> str:
    """Dark or light text, whichever reads on this colour."""
    r, g, b = (int(fill[i:i + 2], 16) for i in (0, 2, 4))
    return DARK if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "FFFFFF"


@lru_cache(maxsize=256)
def _icon_png(name: str, color: str) -> bytes | None:
    path = ICONS_DIR / f"{name}.svg"
    if not path.is_file():
        path = ICONS_DIR / "circle-check.svg"
    svg = path.read_text(encoding="utf-8").replace("currentColor", f"#{color}")
    return bytes(resvg_py.svg_to_bytes(svg_string=svg, zoom=10))


def _run(p, text: str, size: float, color: str, bold: bool = False, font: str = BODY_FONT, italic: bool = False) -> None:
    run = p.add_run()
    run.text = text
    run.font.size, run.font.bold, run.font.italic, run.font.name = Pt(size), bold, italic, font
    run.font.color.rgb = _rgb(color)


# --- measuring: what is drawn must fit, whatever the AI wrote -------------------

FACES = {("Calibri", False): "crosextra/Carlito-Regular.ttf", ("Calibri", True): "crosextra/Carlito-Bold.ttf",
         ("Cambria", False): "crosextra/Caladea-Regular.ttf", ("Cambria", True): "crosextra/Caladea-Bold.ttf",
         ("Arial", False): "liberation/LiberationSans-Regular.ttf", ("Arial", True): "liberation/LiberationSans-Bold.ttf"}
LINE = 1.22  # line height of these fonts, a little generous
MARGIN = 0.95  # PowerPoint, WPS and LibreOffice do not break lines at exactly the same place


@lru_cache(maxsize=8)
def _face(font: str, bold: bool):
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/{FACES.get((font, bold), FACES['Calibri', bold])}", 100)
    except OSError:
        return None


def _span(text: str, size: float, font: str, bold: bool) -> float:
    """Width in inches."""
    face = _face(font, bold)
    return (face.getlength(text) / 100 if face else len(text) * 0.56) * size / 72


def text_lines(text: str, size: float, width: float, font: str = "Calibri", bold: bool = False) -> int:
    width *= MARGIN
    lines, used = 1, 0.0
    space = _span(" ", size, font, bold)
    for word in text.split():
        span = _span(word, size, font, bold)
        if span > width:  # one word wider than the box: it is cut over several lines
            lines += math.ceil(span / width) - (0 if used else 1)
            used = span % width
        elif used and used + space + span > width:
            lines += 1
            used = span
        else:
            used += (space if used else 0) + span
    return lines


def text_height(text: str, size: float, width: float, font: str = "Calibri", bold: bool = False) -> float:
    return text_lines(text, size, width, font, bold) * size * LINE / 72


def _shrunk(text: str, size: float, width: float, height: float, font: str, bold: bool, floor: float = 0.55) -> float:
    least = max(size * floor, 10)
    while size > least and text_height(text, size, width, font, bold) > height:
        size -= 1
    return size


def _fit(total: int, sizes: list[tuple[int, float]]) -> float:
    """The largest size allowed for this much text."""
    for limit, size in sizes:
        if total <= limit:
            return size
    return sizes[-1][1]


class Painter:
    def __init__(self, slide, theme: dict):
        self.slide, self.t = slide, theme
        self.bottom = BOTTOM  # where the content stops (higher when a « à retenir » band closes the slide)
        self.side = 0.0  # width of a colour block against the right edge
        self.marks: list[int] = []  # where each thing that appears on its own starts (animations)
        self.effects: dict[int, str] = {}  # a step with an effect of its own (a chart that draws itself, a number that pops)
        self.seed, self.used = 0, Counter()
        self.images, self.art = Path("."), ""

    def variant(self, name: str, count: int) -> int:
        """Which composition of this layout: changes from one document to another, and along the talk."""
        self.used[name] += 1
        return (self.seed + self.used[name] - 1) % count

    def step(self, effect: str = "") -> None:
        self.marks.append(len(self.slide.shapes._spTree))
        if effect:
            self.effects[self.marks[-1]] = effect

    def shape(self, kind, x: float, y: float, w: float, h: float, fill: str, name: str = "Forme"):
        sp = self.slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        sp.name = name
        sp.fill.solid()
        sp.fill.fore_color.rgb = _rgb(fill)
        sp.line.fill.background()
        sp.shadow.inherit = False
        if self.t.get("glass") and fill == self.t["panel"]:  # frosted glass: the colours of the background show through
            _alpha(sp.fill._xPr.find(qn("a:solidFill")), 13 if self.t["dark"] else 62)
            sp.line.color.rgb = _rgb("FFFFFF")
            sp.line.width = Pt(1)
            _alpha(sp.line._ln.find(qn("a:solidFill")), 28 if self.t["dark"] else 80)
        return sp

    def gradient(self, kind, x: float, y: float, w: float, h: float, start: str, end: str, angle: float = 315, name: str = "Fond"):
        sp = self.shape(kind, x, y, w, h, start, name)
        sp.fill.gradient()
        sp.fill.gradient_angle = angle
        stops = sp.fill.gradient_stops
        stops[0].color.rgb, stops[1].color.rgb = _rgb(start), _rgb(end)
        return sp

    def curve(self, path: list[tuple], fill: str | None, end: str | None = None, angle: float = 315, name: str = "Décor", stroke: str = "", weight: float = 1.25):
        """A free shape, a real one: it can be recoloured in PowerPoint. Path in inches: M/L x y, C x1 y1 x2 y2 x y, Z."""
        xs = [v for step in path for v in step[1::2]]
        ys = [v for step in path for v in step[2::2]]
        x, y, w, h = min(xs), min(ys), max(max(xs) - min(xs), 0.01), max(max(ys) - min(ys), 0.01)
        sp = self.gradient(MSO_SHAPE.RECTANGLE, x, y, w, h, fill, end, angle, name) if end else self.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, fill or "FFFFFF", name)
        if stroke:
            if not fill:
                sp.fill.background()
            sp.line.color.rgb = _rgb(stroke)
            sp.line.width = Pt(weight)
        _custom(sp, path, x, y, w, h, closed=bool(fill))
        return sp

    def text(self, x: float, y: float, w: float, h: float, text: str, size: float, color: str | None = None, bold: bool = False,
             font: str = BODY_FONT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic: bool = False):
        size = _shrunk(text, size, w, h, font, bold)
        box = self.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.vertical_anchor = anchor
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        p = frame.paragraphs[0]
        p.alignment = align
        _run(p, text, size, color or self.t["ink"], bold, font, italic)
        return box

    def stack(self, x: float, y: float, w: float, h: float, head: str, body: str, head_size: float, body_size: float,
              align=PP_ALIGN.LEFT, head_color: str | None = None, body_color: str | None = None, anchor=MSO_ANCHOR.TOP) -> None:
        """A short title and its text in one box: the text follows the title however many lines it takes."""
        font = self.t["title_font"]
        while head_size > 13 and text_height(head, head_size, w, font, True) + (0.07 + text_height(body, body_size, w) if body else 0) > h:
            head_size, body_size = head_size - 1, max(body_size - 1, 12)
        box = self.text(x, y, w, h, head, head_size, head_color, True, font, align, anchor)
        if body:
            first = box.text_frame.paragraphs[0]
            first.space_after = Pt(5)
            p = box.text_frame.add_paragraph()
            p.alignment = align
            _run(p, body, body_size, body_color or self.t["muted"])

    def bullets(self, x: float, y: float, w: float, h: float, points: list[str], size: float, color: str | None = None, gap: int = 12, mark: str | None = None) -> None:
        room = w - 0.32
        while size > 12 and sum(text_height(p, size, room) + gap / 72 for p in points) > h:
            size -= 1
        box = self.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        for i, point in enumerate(points):
            p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            p.space_after = Pt(gap)
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(Inches(0.32)))
            pPr.set("indent", str(-Inches(0.32)))
            clr = pPr.makeelement(qn("a:buClr"), {})
            clr.append(clr.makeelement(qn("a:srgbClr"), {"val": mark or self.t["accent"]}))
            pPr.append(clr)
            pPr.append(pPr.makeelement(qn("a:buChar"), {"char": "■"}))
            _run(p, point, size, color or self.t["ink"])

    def icon(self, name: str, x: float, y: float, size: float, color: str) -> None:
        png = _icon_png(name, color)
        if png:
            pic = self.slide.shapes.add_picture(io.BytesIO(png), Inches(x), Inches(y), Inches(size), Inches(size))
            pic.name = "Icône"

    def badge(self, name: str, x: float, y: float, size: float, fill: str | None = None) -> None:
        fill = fill or self.t["accent"]
        kind = self.t["badge"]
        sp = self.shape(kind, x, y, size, size, fill, "Pastille")
        if kind == MSO_SHAPE.TEAR:
            sp.rotation = 0
        inset = 0.27 if kind in (MSO_SHAPE.DIAMOND, MSO_SHAPE.HEXAGON, MSO_SHAPE.OCTAGON) else 0.22
        self.icon(name, x + size * inset, y + size * inset, size * (1 - 2 * inset), _readable(fill, self.t))

    def card(self, x: float, y: float, w: float, h: float, i: int = 0) -> None:
        t = self.t
        color = t["accent"] if i % 2 == 0 else t["second"]
        if t["card"] == "accent":
            _corner(self.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, t["panel"], "Carte"), min(0.14 / min(w, h), 0.5))
            bar = self.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.1, y + 0.16, 0.07, h - 0.32, color, "Filet")
            bar.adjustments[0] = 0.5
        elif t["card"] == "line":
            sp = self.shape(t["corner"], x, y, w, h, t["bg"], "Carte")
            _corner(sp)
            sp.line.color.rgb = _rgb(color)
            sp.line.width = Pt(1.75)
        elif t["card"] == "bar":
            self.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, t["panel"], "Carte")
            self.shape(MSO_SHAPE.RECTANGLE, x, y, 0.1, h, color, "Filet")
        else:
            _corner(self.shape(t["corner"], x, y, w, h, t["panel"], "Carte"))

    def tone(self, i: int) -> str:
        return self.t["accent"] if i % 2 == 0 else self.t["second"]

    def hue(self, i: int) -> str:
        """Several colours of one family, for a diagram: every step its own, as on a real infographic."""
        t = self.t
        return (t["accent"], t["second"], t["deep"], _mix(t["accent"], t["second"], 0.5), _mix(t["second"], t["deep"], 0.45), _mix(t["accent"], t["bg"], 0.3))[i % 6]


def _alpha(fill, percent: float) -> None:
    color = fill[0]
    color.append(color.makeelement(qn("a:alpha"), {"val": str(int(percent * 1000))}))


def _custom(sp, path: list[tuple], x: float, y: float, w: float, h: float, closed: bool = True) -> None:
    """Swaps the rectangle of `sp` for this path."""
    def at(px: float, py: float) -> str:
        return f'<a:pt x="{round((px - x) * 1000)}" y="{round((py - y) * 1000)}"/>'

    pieces = []
    for step in path:
        match step[0]:
            case "M":
                pieces.append(f"<a:moveTo>{at(*step[1:])}</a:moveTo>")
            case "L":
                pieces.append(f"<a:lnTo>{at(*step[1:])}</a:lnTo>")
            case "C":
                pieces.append(f"<a:cubicBezTo>{at(*step[1:3])}{at(*step[3:5])}{at(*step[5:7])}</a:cubicBezTo>")
            case "Z":
                pieces.append("<a:close/>")
    wide, high = round(w * 1000), round(h * 1000)
    xml = ('<a:custGeom xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/>'
           f'<a:pathLst><a:path w="{wide}" h="{high}"{"" if closed else " fill=" + chr(34) + "none" + chr(34)}>{"".join(pieces)}</a:path></a:pathLst></a:custGeom>')
    old = sp._element.spPr.find(qn("a:prstGeom"))
    old.addprevious(etree.fromstring(xml))
    old.getparent().remove(old)


def _lift(sp, blur: float = 14, drop: float = 5, strength: int = 16) -> None:
    """A soft shadow: the card floats a little above the slide."""
    effects = sp._element.spPr.find(qn("a:effectLst"))
    if effects is not None:
        effects.getparent().remove(effects)
    xml = ('<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
           f'<a:outerShdw blurRad="{int(blur * 12700)}" dist="{int(drop * 12700)}" dir="5400000" algn="t" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="{strength * 1000}"/></a:srgbClr></a:outerShdw></a:effectLst>')
    sp._element.spPr.find(qn("a:ln")).addnext(etree.fromstring(xml))


def _corner(sp, value: float = 0.08) -> None:
    for i in range(len(sp.adjustments)):
        sp.adjustments[i] = value if i == 0 else (0.0 if sp.auto_shape_type == MSO_SHAPE.ROUND_2_DIAG_RECTANGLE else value)


def _background(slide, color: str) -> None:
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = _rgb(color)


def _motif(pen: Painter) -> None:
    """The style's shapes, in the corners, behind everything and away from the text."""
    t = pen.t
    soft, softer = _mix(t["bg"], t["accent"], 0.16), _mix(t["bg"], t["second"], 0.35)
    match t["motif"]:
        case "cercles":
            pen.shape(MSO_SHAPE.OVAL, 11.7, -1.0, 2.5, 2.5, soft, "Décor")
            pen.shape(MSO_SHAPE.OVAL, 12.45, 0.95, 0.7, 0.7, softer, "Décor")
        case "points":
            for row in range(3):
                for col in range(5):
                    pen.shape(MSO_SHAPE.OVAL, 11.0 + col * 0.34, 0.42 + row * 0.34, 0.1, 0.1, _mix(t["bg"], t["accent"], 0.75 - 0.15 * row), "Décor")
        case "diagonale":
            corner = pen.shape(MSO_SHAPE.RIGHT_TRIANGLE, WIDTH - 2.0, 0, 2.0, 1.6, soft, "Décor")
            corner.rotation = 180
            mini = pen.shape(MSO_SHAPE.RIGHT_TRIANGLE, WIDTH - 0.85, 0, 0.85, 0.68, t["second"], "Décor")
            mini.rotation = 180
        case "organique":
            tilt = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, 11.75, -0.7, 2.1, 2.1, soft, "Décor")
            tilt.adjustments[0], tilt.rotation = 0.25, 24
            pen.shape(MSO_SHAPE.DONUT, 11.5, 1.1, 0.42, 0.42, t["accent"], "Décor").adjustments[0] = 0.22
            pen.shape(MSO_SHAPE.MATH_PLUS, 11.05, 0.32, 0.4, 0.4, t["second"], "Décor")
        case "vague":
            pen.shape(MSO_SHAPE.WAVE, 8.6, -0.32, 5.0, 0.95, soft, "Décor")
            pen.shape(MSO_SHAPE.WAVE, 10.3, -0.22, 3.4, 0.6, softer, "Décor")
        case "croix":
            for x, y, size, color in ((12.05, 0.28, 0.72, soft), (11.35, 0.72, 0.42, t["accent"]), (12.45, 1.05, 0.34, softer)):
                pen.shape(MSO_SHAPE.MATH_PLUS, x, y, size, size, color, "Décor")
        case "triangles":
            for i, (x, y, size, color) in enumerate(((11.9, 0.1, 0.9, soft), (12.35, 0.75, 0.62, t["second"]), (11.45, 0.72, 0.5, softer))):
                pen.shape(MSO_SHAPE.ISOSCELES_TRIANGLE, x, y, size, size, color, "Décor").rotation = 180 * (i % 2)
        case "rayures":
            for i in range(4):
                pen.shape(MSO_SHAPE.PARALLELOGRAM, 11.0 + i * 0.5, 0.25, 0.3, 1.15, t["second"] if i == 3 else _mix(t["bg"], t["accent"], 0.18 + 0.12 * i), "Décor")
        case "arcs":
            for i, size in enumerate((3.2, 2.2, 1.2)):
                arc = pen.shape(MSO_SHAPE.BLOCK_ARC, WIDTH - size / 2 - 0.2, -size / 2, size, size, _mix(t["bg"], t["accent"], 0.2 + 0.2 * i), "Décor")
                arc.rotation = 180
        case "soleil":
            pen.shape(MSO_SHAPE.SUN, 11.75, -0.55, 2.2, 2.2, t["second"], "Décor")
        case "hexagones":
            for x, y, size, color in ((11.9, 0.2, 0.85, soft), (12.5, 0.72, 0.6, _mix(t["bg"], t["second"], 0.5)), (11.45, 0.82, 0.5, _mix(t["bg"], t["accent"], 0.45))):
                pen.shape(MSO_SHAPE.HEXAGON, x, y, size, size, color, "Décor")
        case "feuilles":
            for x, y, size, turn, color in ((12.0, 0.1, 1.05, 0, soft), (11.35, 0.5, 0.68, 90, softer), (12.5, 0.95, 0.5, 180, t["accent"])):
                pen.shape(MSO_SHAPE.TEAR, x, y, size, size, color, "Décor").rotation = turn
        case "barre":
            pen.shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, 0.16, t["accent"], "Décor")
            pen.shape(MSO_SHAPE.RECTANGLE, LEFT, 0, 1.6, 0.16, t["second"], "Décor")


def _night(t: dict) -> dict:
    """The same style on black: slides that must hit hard, between the white ones."""
    return {**t, "bg": "0B0B0C", "panel": "1C1C1F", "ink": "FFFFFF", "muted": "B8BABD", "second": "FFFFFF", "dark": True}


def _set_title(slide, text: str, color: str, font: str, size: float, x: float, y: float, w: float, h: float, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.LEFT,
               mark: str = "", mark_color: str = "", lean: bool = False) -> None:
    """The real title placeholder: PowerPoint's outline and slide sorter show it."""
    shape = slide.shapes.title
    tree = slide.shapes._spTree
    tree.remove(shape._element)
    tree.append(shape._element)  # above the shapes already drawn
    shape.left, shape.top, shape.width, shape.height = Inches(x), Inches(y), Inches(w), Inches(h)
    frame = shape.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    size = _shrunk(text, size, w, h, font, True)
    p = frame.paragraphs[0]
    p.alignment = align
    at = text.lower().find(mark.lower()) if mark else -1
    if at < 0:
        _run(p, text, size, color, True, font)
        return
    for piece, tint, slanted in ((text[:at], color, False), (text[at:at + len(mark)], mark_color, lean), (text[at + len(mark):], color, False)):
        if piece:
            _run(p, piece, size, tint, True, font, slanted)


def _veil(pen: Painter, seed: int) -> None:
    """The soft light at the top of a Halo slide: it follows the colours chosen by the user."""
    t = pen.t
    pic = pen.slide.shapes.add_picture(io.BytesIO(halo(t["accent"], t["second"], t["bg"], seed % 2)), 0, 0, Inches(WIDTH), Inches(HEIGHT))
    pic.name = "Fond"


def _field(pen: Painter, seed: int) -> None:
    """The field of colour under a glass slide (three of them per talk)."""
    pic = pen.slide.shapes.add_picture(io.BytesIO(mesh(pen.t["mesh"], seed % 3 + seed // 7 % 1000)), 0, 0, Inches(WIDTH), Inches(HEIGHT))
    pic.name = "Fond"


def _photo(pen: Painter, images_dir: Path, name: str, x: float = 0, y: float = 0, w: float = WIDTH, h: float = HEIGHT, veil: float = 0) -> bool:
    """A picture cut to fill its place, with a dark veil if text sits on it."""
    path = images_dir / str(name)
    if not name or not path.is_file():
        return False
    with Image.open(path) as img:
        ratio = img.width / img.height
    pic = pen.slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.name = "Image"
    target = w / h
    if ratio > target:
        pic.crop_left = pic.crop_right = (1 - target / ratio) / 2
    else:
        pic.crop_top = pic.crop_bottom = (1 - ratio / target) / 2
    if veil:
        cover = pen.gradient(MSO_SHAPE.RECTANGLE, x, y, w, h, "050510", "050510", 0, "Voile")
        for stop, part in zip(cover.fill._xPr.find(qn("a:gradFill")).find(qn("a:gsLst")), (veil, veil * 0.25)):
            _alpha(stop, part)
    return True


def _corner_curve(pen: Painter) -> None:
    """The cover's curves, small, at the top right of each slide."""
    t = pen.t
    pen.curve([("M", 11.35, 0), ("C", 11.75, 0.75, 12.45, 1.2, WIDTH, 1.42), ("L", WIDTH, 0), ("Z",)], _mix(t["bg"], t["second"], 0.4))
    pen.curve([("M", 11.95, 0), ("C", 12.25, 0.45, 12.75, 0.82, WIDTH, 0.98), ("L", WIDTH, 0), ("Z",)], t["accent"], t["deep"], 0)
    pen.curve([("M", 11.05, 0), ("C", 11.5, 0.95, 12.35, 1.5, WIDTH, 1.72)], None, stroke=t["second"], weight=1)


def _menu(pen: Painter, parts: list[str], current: str | None, end: float) -> None:
    """The parts of the talk as a small menu at the top, the current one lit."""
    t = pen.t
    if not parts or sum(len(p) for p in parts) > 62:
        return
    box = pen.text(end - 8.0, 0.32, 8.0, 0.3, " ", 11, t["muted"], align=PP_ALIGN.RIGHT)
    p = box.text_frame.paragraphs[0]
    p.runs[0].text = ""
    for i, name in enumerate(parts):
        lit = name == current
        _run(p, ("      " if i else "") + name.upper(), 10.5, t["accent"] if lit else _mix(t["muted"], t["bg"], 0.25), lit)


def _standard(prs, theme: dict, title: str, part: str | None = None, mark: str = "", side: float = 0.0, seed: int = 0, parts: list[str] | None = None) -> Painter:
    t = theme
    if t["caps"]:
        title, mark = title.upper(), mark.upper()
    room = 10.4 if not side else WIDTH - side - LEFT - 0.4
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    _background(slide, t["bg"])
    pen = Painter(slide, t)
    pen.side = side
    if t.get("glass"):
        _field(pen, seed)
    if t["skin"] == "halo":
        _veil(pen, seed)
    hi = t["accent"] if not t["dark"] or t["caps"] else t["second"]
    size = 33 if len(title) <= 46 else 28 if len(title) <= 66 else 24
    if t.get("glass"):
        size = 40 if len(title) <= 42 else 33 if len(title) <= 60 else 27
    if t["caps"]:
        size = 30 if len(title) <= 42 else 25 if len(title) <= 58 else 21
    if side:
        size = min(size, 30 if len(title) <= 40 else 25)
    match t["skin"]:
        case "curve":
            if not side:
                _corner_curve(pen)
            if part:
                pen.text(LEFT, 0.34, 7, 0.3, part.upper(), 12.5, t["accent"], True)
            _set_title(slide, title, t["ink"], t["title_font"], size, LEFT, 0.62, room, 1.0, MSO_ANCHOR.TOP, mark=mark, mark_color=hi)
        case "halo":
            if part:
                pen.text(LEFT, 0.32, 3.6, 0.3, part.upper(), 11, t["accent"], True)
            _menu(pen, parts or [], part, (WIDTH - LEFT) if not side else WIDTH - side - 0.4)
            size = max(size, 36 if len(title) <= 42 else 30 if len(title) <= 60 else 25)
            if side:
                size = min(size, 30 if len(title) <= 40 else 25)
            _set_title(slide, title, t["ink"], t["title_font"], size, LEFT, 0.66, room if not side else room, 0.98, MSO_ANCHOR.TOP, mark=mark, mark_color=t["accent"], lean=t["lean"])
        case "band":
            pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, 1.38, t["deep"], t["accent"], 0, "Bandeau")
            pen.shape(MSO_SHAPE.RECTANGLE, 0, 1.38, WIDTH, 0.07, t["second"], "Filet")
            _set_title(slide, title, t["on_accent"], t["title_font"], size, LEFT, 0.14, CONTENT_WIDTH, 1.1, mark=mark, mark_color=t["second"] if _readable(t["second"], t) != _readable(t["accent"], t) else t["on_accent"])
        case "side":
            _motif(pen)
            pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, 0.36, STRIP, t["accent"], t["deep"], 270, "Colonne")
            pen.shape(MSO_SHAPE.RECTANGLE, 0, 0.5, 0.36, 1.0, t["second"], "Filet")
            _set_title(slide, title, t["ink"], t["title_font"], size, LEFT, 0.42, room, 1.15, mark=mark, mark_color=hi)
        case "tab":
            _motif(pen)
            label = (part or "").upper()
            if label:
                width = min(0.125 * len(label) + 0.5, 5.0)
                tag = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, LEFT, 0.3, width, 0.36, t["accent"], "Étiquette")
                tag.adjustments[0] = 0.5
                pen.text(LEFT, 0.3, width, 0.36, label, 12, t["on_accent"], True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            _set_title(slide, title, t["ink"], t["title_font"], size, LEFT, 0.68, room, 0.95, mark=mark, mark_color=hi)
        case _:
            if not side:
                _motif(pen)
            if t["kicker"]:
                if part:
                    pen.text(LEFT, 0.34, 7, 0.3, f"→  {part.upper()}", 12.5, hi, True)
                _set_title(slide, title, t["ink"], t["title_font"], size, LEFT, 0.62, room, 1.0, MSO_ANCHOR.TOP, mark=mark, mark_color=hi)
            else:
                _set_title(slide, title, t["ink"], t["title_font"], size, LEFT, 0.36, room, 1.05, mark=mark, mark_color=hi)
                pen.shape(MSO_SHAPE.RECTANGLE, LEFT, 1.46, 0.9, 0.07, t["second"], "Filet")
    return pen


# --- content layouts ----------------------------------------------------------

def _liste_lines(pen: Painter, s: dict) -> None:
    """Editorial: a big number, the idea, a thin rule. No box."""
    t, items = pen.t, s["items"]
    h = min((pen.bottom - TOP) / len(items), 1.5)
    for i, item in enumerate(items):
        pen.step()
        y = TOP + i * h
        pen.text(LEFT, y, 1.3, h - 0.1, f"{i + 1:02d}", 44, t["accent"] if not t["dark"] or t["caps"] else t["second"], True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
        pen.stack(LEFT + 1.45, y, CONTENT_WIDTH - 1.45, h - 0.1, item["head"], item["text"], 25, 20, anchor=MSO_ANCHOR.MIDDLE)
        if i < len(items) - 1:
            pen.shape(MSO_SHAPE.RECTANGLE, LEFT, y + h - 0.03, CONTENT_WIDTH, 0.015, _mix(t["bg"], t["ink"], 0.2), "Filet")


def _liste_tabs(pen: Painter, s: dict) -> None:
    """A coloured tab with the idea, its explanation beside it."""
    t, items = pen.t, s["items"]
    n = len(items)
    gap = 0.16
    h = min((pen.bottom - TOP - gap * (n - 1)) / n, 1.3)
    tab = 4.6
    for i, item in enumerate(items):
        pen.step()
        y = TOP + i * (h + gap)
        fill = pen.tone(i)
        arrow = pen.shape(MSO_SHAPE.PENTAGON, LEFT, y, tab, h, fill, "Onglet")
        arrow.adjustments[0] = 0.18
        color = _readable(fill, t)
        pen.icon(item["icon"], LEFT + 0.22, y + (h - 0.5) / 2, 0.5, color)
        pen.text(LEFT + 0.85, y, tab - 1.2, h, item["head"], 22, color, True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
        pen.text(LEFT + tab + 0.25, y, CONTENT_WIDTH - tab - 0.25, h, item["text"] or item["head"], 20, t["ink"], anchor=MSO_ANCHOR.MIDDLE)


def _liste(pen: Painter, s: dict) -> None:
    choice = pen.variant("liste", 3)
    if choice == 1:
        return _liste_lines(pen, s)
    if choice == 2:
        return _liste_tabs(pen, s)
    items = s["items"]
    n = len(items)
    gap = 0.17
    h = min((pen.bottom - TOP - gap * (n - 1)) / n, 1.35)
    size = 21 if n <= 4 else 19
    for i, item in enumerate(items):
        pen.step()
        y = TOP + i * (h + gap)
        pen.card(LEFT, y, CONTENT_WIDTH, h, i)
        dot = min(h - 0.26, 0.82)
        pen.badge(item["icon"], LEFT + 0.25, y + (h - dot) / 2, dot, pen.tone(i))
        pen.stack(LEFT + dot + 0.5, y, CONTENT_WIDTH - dot - 0.8, h, item["head"], item["text"], 25 if n <= 4 else 22, size, anchor=MSO_ANCHOR.MIDDLE)


def _grille_columns(pen: Painter, s: dict) -> None:
    """Airy columns, no box, the icon on top."""
    t, items = pen.t, s["items"]
    n = len(items)
    w = CONTENT_WIDTH / n
    for i, item in enumerate(items):
        pen.step()
        x = LEFT + i * w
        pen.badge(item["icon"], x + w / 2 - 0.6, TOP + 0.1, 1.2, pen.tone(i))
        pen.stack(x + 0.15, TOP + 1.5, w - 0.3, pen.bottom - TOP - 1.55, item["head"], item["text"], 24, 20, PP_ALIGN.CENTER)
        if i:
            pen.shape(MSO_SHAPE.RECTANGLE, x, TOP + 0.3, 0.015, pen.bottom - TOP - 0.6, _mix(t["bg"], t["ink"], 0.2), "Filet")


def _grille_tiles(pen: Painter, s: dict) -> None:
    """Tiles of solid colour, the text on the colour."""
    t, items = pen.t, s["items"]
    n = len(items)
    columns = 2 if n == 4 else min(n, 3)
    rows = (n + columns - 1) // columns
    gap = 0.18
    w = (CONTENT_WIDTH - gap * (columns - 1)) / columns
    h = (pen.bottom - TOP - gap * (rows - 1)) / rows
    for i, item in enumerate(items):
        pen.step()
        x, y = LEFT + (i % columns) * (w + gap), TOP + (i // columns) * (h + gap)
        fill = t["accent"] if (i + i // columns) % 2 == 0 else t["deep"] if not t["dark"] else t["panel"]
        _corner(pen.shape(t["corner"], x, y, w, h, fill, "Tuile"))
        color = _readable(fill, t)
        pen.icon(item["icon"], x + w - 0.85, y + 0.22, 0.6, color)
        pen.stack(x + 0.28, y + 0.25, w - 1.2 if rows > 1 else w - 0.5, h - 0.4, item["head"], item["text"], 24, 18, head_color=color, body_color=_mix(color, fill, 0.15),
                  anchor=MSO_ANCHOR.BOTTOM if rows == 1 else MSO_ANCHOR.TOP)


def _grille_bento(pen: Painter, s: dict) -> None:
    """One large tile and smaller ones: the modular look of today's product pages."""
    t, items = pen.t, s["items"]
    gap = 0.22
    room = pen.bottom - TOP
    big = CONTENT_WIDTH * 0.42
    pen.step()
    pen.card(LEFT, TOP, big, room, 0)
    pen.badge(items[0]["icon"], LEFT + 0.35, TOP + 0.35, 1.05, t["accent"])
    pen.stack(LEFT + 0.35, TOP + 1.65, big - 0.7, room - 1.8, items[0]["head"], items[0]["text"], 30, 21)
    rest = items[1:]
    rows = len(rest)
    x = LEFT + big + gap
    w = CONTENT_WIDTH - big - gap
    h = (room - gap * (rows - 1)) / rows
    for i, item in enumerate(rest):
        pen.step()
        y = TOP + i * (h + gap)
        pen.card(x, y, w, h, i + 1)
        pen.badge(item["icon"], x + 0.25, y + (h - 0.75) / 2, 0.75, pen.tone(i + 1))
        pen.stack(x + 1.2, y + 0.1, w - 1.4, h - 0.2, item["head"], item["text"], 24, 19, anchor=MSO_ANCHOR.MIDDLE)


def _grille(pen: Painter, s: dict) -> None:
    if pen.t.get("glass") and 3 <= len(s["items"]) <= 4:
        return _grille_bento(pen, s)
    choice = pen.variant("grille", 5)
    if choice == 1 and len(s["items"]) <= 4:
        return _grille_columns(pen, s)
    if choice == 2:
        return _grille_tiles(pen, s)
    if choice == 3 and 3 <= len(s["items"]) <= 4:
        return _grille_tall(pen, s)
    if choice == 4 and 2 <= len(s["items"]) <= 4:
        return _grille_bubbles(pen, s)
    items = s["items"]
    n = len(items)
    columns = {2: 2, 3: 3, 4: 2, 5: 3, 6: 3}.get(n, 3)
    rows = (n + columns - 1) // columns
    gap = 0.25
    w = (CONTENT_WIDTH - gap * (columns - 1)) / columns
    h = (pen.bottom - TOP - gap * (rows - 1)) / rows
    wide = rows == 2 and columns == 2
    for i, item in enumerate(items):
        pen.step()
        x, y = LEFT + (i % columns) * (w + gap), TOP + (i // columns) * (h + gap)
        pen.card(x, y, w, h, i)
        if rows == 1:
            pen.badge(item["icon"], x + 0.3, y + 0.32, 0.95, pen.tone(i))
            pen.stack(x + 0.3, y + 1.45, w - 0.6, h - 1.6, item["head"], item["text"], 25, 21)
        elif wide:
            pen.badge(item["icon"], x + 0.25, y + 0.28, 0.82, pen.tone(i))
            pen.stack(x + 1.25, y + 0.24, w - 1.45, h - 0.4, item["head"], item["text"], 25, 20)
        else:
            pen.badge(item["icon"], x + 0.22, y + 0.2, 0.62, pen.tone(i))
            pen.stack(x + 0.98, y + 0.2, w - 1.15, 0.7, item["head"], "", 20, 17)
            pen.text(x + 0.22, y + 0.95, w - 0.42, h - 1.05, item["text"], 17, pen.t["muted"])


def _grille_tall(pen: Painter, s: dict) -> None:
    """Tall columns of one family of colours: the number on top, the idea at the bottom."""
    t, items = pen.t, s["items"]
    n = len(items)
    gap = 0.2
    w = (CONTENT_WIDTH - gap * (n - 1)) / n
    h = pen.bottom - TOP
    fills = (t["accent"], _mix(t["accent"], t["second"], 0.62), _mix(t["accent"], t["bg"], 0.26), t["deep"])
    for i, item in enumerate(items):
        pen.step()
        x = LEFT + i * (w + gap)
        fill = fills[i % 4]
        _corner(pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, TOP, w, h, fill, "Colonne"), 0.05)
        on = _readable(fill, t)
        pen.text(x + 0.3, TOP + 0.22, 1.2, 0.6, f"{i + 1:02d}", 26, on, True, t["title_font"])
        pen.icon(item["icon"], x + w - 0.9, TOP + 0.24, 0.6, on)
        pen.stack(x + 0.3, TOP + 0.95, w - 0.6, h - 1.15, item["head"], item["text"], 23, 17, head_color=on, body_color=on, anchor=MSO_ANCHOR.BOTTOM)


def _grille_bubbles(pen: Painter, s: dict) -> None:
    """A speech bubble of colour with its icon, the idea written under the point."""
    t, items = pen.t, s["items"]
    n = len(items)
    w = CONTENT_WIDTH / n
    side = min(pen.bottom - TOP - 1.95, 2.1, w - 0.7)
    for i, item in enumerate(items):
        pen.step()
        x = LEFT + i * w
        fill = pen.hue(i)
        bubble = pen.shape(MSO_SHAPE.ROUNDED_RECTANGULAR_CALLOUT, x + (w - side) / 2, TOP, side, side * 0.86, fill, "Bulle")
        bubble.adjustments[0], bubble.adjustments[1], bubble.adjustments[2] = 0.0, 0.66, 0.14
        _lift(bubble)
        pen.icon(item["icon"], x + w / 2 - side * 0.24, TOP + side * 0.19, side * 0.48, _readable(fill, t))
        y = TOP + side * 0.86 + 0.42
        pen.stack(x + 0.14, y, w - 0.28, pen.bottom - y, item["head"], item["text"], 23, 18, PP_ALIGN.CENTER)


def _hub(pen: Painter, s: dict, cx: float, cy: float, size: float) -> None:
    """The centre of a diagram: a ring, the icon, the word it all turns around."""
    t = pen.t
    pen.shape(MSO_SHAPE.OVAL, cx - size / 2 - 0.14, cy - size / 2 - 0.14, size + 0.28, size + 0.28, _mix(t["bg"], t["accent"], 0.13), "Centre")
    pen.gradient(MSO_SHAPE.OVAL, cx - size / 2, cy - size / 2, size, size, t["accent"], t["deep"], 315, "Centre")
    on = _readable(t["accent"], t)
    key = (s.get("key") or "").strip()
    key = key if len(key) <= 26 else key[:26].rsplit(" ", 1)[0]
    icon = size * (0.3 if key else 0.5)
    pen.icon(s.get("icon") or "target", cx - icon / 2, cy - icon / 2 - (size * 0.17 if key else 0), icon, on)
    if key:
        pen.text(cx - size * 0.4, cy + size * 0.03, size * 0.8, size * 0.32, key, 17, on, True, t["title_font"], PP_ALIGN.CENTER)


def _schema_arc(pen: Painter, s: dict) -> None:
    """The ideas strung on an arc around the centre."""
    t, items = pen.t, s["items"]
    n = len(items)
    room = pen.bottom - TOP
    cy = TOP + room / 2
    radius = max(room / 2 + 0.25, 2.3)
    cx = LEFT + 1.25
    pen.step()
    arc = [("M", cx + math.sqrt(radius ** 2 - (room / 2) ** 2), TOP)]
    for k in range(1, 25):
        y = TOP + room * k / 24
        arc.append(("L", cx + math.sqrt(radius ** 2 - (y - cy) ** 2), y))
    pen.curve(arc, None, stroke=_mix(t["bg"], t["ink"], 0.22), weight=5, name="Arc")
    _hub(pen, s, cx, cy, min(room * 0.56, 2.45))
    step = room / n
    dot = min(step - 0.14, 0.78)
    for i, item in enumerate(items):
        pen.step()
        y = TOP + step * (i + 0.5)
        x = cx + math.sqrt(radius ** 2 - (y - cy) ** 2)
        pen.shape(MSO_SHAPE.OVAL, x - dot / 2 - 0.06, y - dot / 2 - 0.06, dot + 0.12, dot + 0.12, t["bg"], "Pastille")
        pen.badge(item["icon"], x - dot / 2, y - dot / 2, dot, pen.hue(i))
        left = x + dot / 2 + 0.2
        pen.stack(left, y - step / 2 + 0.02, WIDTH - LEFT - left, step - 0.04, item["head"], item["text"], 22 if n <= 4 else 20, 17 if n <= 4 else 15, anchor=MSO_ANCHOR.MIDDLE)


def _schema_pills(pen: Painter, s: dict) -> None:
    """Pills on both sides of the centre, numbered round it."""
    t, items = pen.t, s["items"]
    n = len(items)
    rows = (n + 1) // 2
    room = pen.bottom - TOP
    gap = 0.2
    h = min((room - gap * (rows - 1)) / rows, 1.42)
    start = TOP + (room - rows * h - gap * (rows - 1)) / 2
    w = (CONTENT_WIDTH - 2.5) / 2
    pen.step()
    _hub(pen, s, WIDTH / 2, TOP + room / 2, 1.9)
    for i, item in enumerate(items):
        pen.step()
        right = i < rows
        row = i if right else n - 1 - i
        x, y = (WIDTH - LEFT - w if right else LEFT), start + row * (h + gap)
        fill = pen.hue(i)
        pill = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, t["panel"], "Pilule")
        pill.adjustments[0] = 0.5
        if not t.get("glass"):
            _lift(pill, 10, 3, 12)
        dot = h - 0.2
        inner = x + 0.1 if right else x + w - dot - 0.1
        pen.shape(MSO_SHAPE.OVAL, inner, y + 0.1, dot, dot, fill, "Numéro")
        pen.text(inner, y + 0.1, dot, dot, str(i + 1), 26, _readable(fill, t), True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        pen.icon(item["icon"], x + w - 0.72 if right else x + 0.3, y + h / 2 - 0.21, 0.42, fill if _readable(t["panel"], t) == DARK and _readable(fill, t) == "FFFFFF" else t["accent"])
        text_x = inner + dot + 0.14 if right else x + 0.84
        pen.stack(text_x, y + 0.08, w - dot - 1.08, h - 0.16, item["head"], item["text"], 20, 15, PP_ALIGN.LEFT if right else PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def _schema_arches(pen: Painter, s: dict) -> None:
    """Three crescents, the middle one lower: a number in the colour, the icon in the white."""
    t, items = pen.t, s["items"]
    n = len(items)
    w = CONTENT_WIDTH / n
    size = 1.85
    drop = 0.42
    pen.step()
    y0, y1 = TOP + size / 2, TOP + drop + size / 2
    for i in range(n - 1):
        ax, bx = LEFT + w * (i + 0.5), LEFT + w * (i + 1.5)
        ya, yb = (y0, y1) if i % 2 == 0 else (y1, y0)
        pen.curve([("M", ax, ya), ("C", (ax + bx) / 2, ya, (ax + bx) / 2, yb, bx, yb)], None, stroke=_mix(t["bg"], t["accent"], 0.3), weight=7, name="Lien")
    for i, item in enumerate(items):
        pen.step()
        cx = LEFT + w * (i + 0.5)
        y = TOP + (drop if i % 2 else 0)
        fill = pen.hue(i)
        pen.shape(MSO_SHAPE.OVAL, cx - size / 2, y, size, size, fill, "Arche")
        inner = size - 0.2
        pen.shape(MSO_SHAPE.OVAL, cx - inner / 2, y + 0.42, inner, inner - 0.32, t["bg"] if not t.get("glass") else "FFFFFF", "Arche")
        pen.text(cx - 0.5, y + 0.04, 1.0, 0.38, f"{i + 1:02d}", 17, _readable(fill, t), True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        pen.icon(item["icon"], cx - 0.34, y + 0.74, 0.68, fill if _readable(fill, t) == "FFFFFF" else t["deep"])
        top = TOP + size + drop + 0.12 if i % 2 else TOP + size + 0.14
        pen.stack(cx - w / 2 + 0.12, top, w - 0.24, pen.bottom - top, item["head"], item["text"], 23, 18, PP_ALIGN.CENTER, head_color=fill if _readable(t["bg"], t) == DARK and _readable(fill, t) == "FFFFFF" else t["ink"])


def _schema(pen: Painter, s: dict) -> None:
    n = len(s["items"])
    shapes = {2: (_schema_arc,), 3: (_schema_arches, _schema_arc), 4: (_schema_pills, _schema_arc), 5: (_schema_arc,), 6: (_schema_pills,)}.get(n, (_schema_pills,))
    shapes[pen.variant("schema", len(shapes)) if len(shapes) > 1 else 0](pen, s)


def _block(pen: Painter, icon: str) -> tuple[float, float, str]:
    """A third of the slide in full colour, against the right edge. Gives where its content starts."""
    t = pen.t
    top = 1.45 if t["skin"] == "band" else 0.0
    x = WIDTH - pen.side
    if _photo(pen, pen.images, pen.art, x, top, pen.side, HEIGHT - top, veil=72):
        return x + 0.5, top + 3.2, "FFFFFF"
    if t["skin"] == "curve":
        pen.curve([("M", x + 0.3, 0), ("C", x - 0.3, 2.2, x - 0.3, 5.2, x + 0.45, HEIGHT), ("L", WIDTH, HEIGHT), ("L", WIDTH, 0), ("Z",)], _mix(t["bg"], t["second"], 0.45), name="Bloc de couleur")
        pen.curve([("M", x + 0.5, 0), ("C", x - 0.1, 2.2, x - 0.1, 5.2, x + 0.65, HEIGHT), ("L", WIDTH, HEIGHT), ("L", WIDTH, 0), ("Z",)], t["accent"], t["deep"], 300, "Bloc de couleur")
        on = _readable(t["accent"], t)
        pen.icon(icon, x + 0.65, top + 0.95, 1.05, on)
        return x + 0.65, top + 2.3, on
    if t["skin"] == "halo":
        _corner(pen.gradient(MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.1, 0.4, pen.side - 0.5, 6.5, t["accent"], t["deep"], 300, "Bloc de couleur"), 0.05)
        on = _readable(t["accent"], t)
        pen.icon(icon, x + 0.5, 1.0, 1.05, on)
        return x + 0.5, 2.3, on
    if t.get("glass"):
        pen.shape(MSO_SHAPE.RECTANGLE, x, top, pen.side, HEIGHT - top, t["panel"], "Bloc de verre")
        pen.icon(icon, x + 0.5, top + 0.95, 1.05, t["accent"])
        return x + 0.5, top + 2.3, t["ink"]
    pen.gradient(MSO_SHAPE.RECTANGLE, x, top, pen.side, STRIP - top, t["accent"], t["deep"], 300, "Bloc de couleur")
    on = _readable(t["accent"], t)
    pale = _mix(t["accent"], on, 0.12)
    pen.shape(MSO_SHAPE.OVAL, x + pen.side - 1.7, STRIP - 1.9, 2.6, 2.6, pale, "Décor")
    if t["motif"] == "organique":
        pen.shape(MSO_SHAPE.MATH_PLUS, x + 0.35, top + 0.3, 0.42, 0.42, on, "Décor")
    pen.icon(icon, x + 0.5, top + 0.95, 1.05, on)
    return x + 0.5, top + 2.3, on


def _panneau(pen: Painter, s: dict) -> None:
    """The details on the left, the message of the slide in a block of colour."""
    t, items = pen.t, s["items"]
    pen.step()
    x, y, on = _block(pen, s.get("icon") or items[0]["icon"])
    key = s.get("key") or s["title"]
    pen.text(x, y, pen.side - (1.25 if t["skin"] in ("curve", "halo") else 0.9), 3.4, key, _fit(len(key), [(55, 29), (90, 25), (10_000, 21)]), on, True, t["title_font"])
    room = WIDTH - pen.side - LEFT - 0.4
    n = len(items)
    gap = 0.2
    h = min((pen.bottom - TOP - gap * (n - 1)) / n, 1.45)
    for i, item in enumerate(items):
        pen.step()
        top = TOP + i * (h + gap)
        pen.badge(item["icon"], LEFT, top + (h - 0.72) / 2, 0.72, pen.tone(i))
        pen.stack(LEFT + 0.95, top, room - 0.95, h, item["head"], item["text"], 24, 19, anchor=MSO_ANCHOR.MIDDLE)


def _grand(pen: Painter, s: dict) -> None:
    """One enormous number or phrase: the slide people remember."""
    t = pen.t
    pen.step()
    _block(pen, s.get("icon") or "target")
    pen.step("zoom")
    value = s["value"]
    room = WIDTH - pen.side - LEFT - 0.4
    size = _fit(len(value), [(5, 130), (9, 96), (14, 72), (10_000, 50)])
    pen.text(LEFT, TOP + 0.35, room, 2.3, value, size, t["accent"], True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
    pen.text(LEFT, TOP + 2.85, room, 1.6, s.get("text") or "", 26, t["ink"], True)


def _chronologie(pen: Painter, s: dict) -> None:
    t, items = pen.t, s["items"]
    n = len(items)
    w = CONTENT_WIDTH / n
    line = TOP + 2.45
    pen.shape(MSO_SHAPE.RECTANGLE, LEFT, line - 0.04, CONTENT_WIDTH, 0.08, _mix(t["bg"], t["accent"], 0.45), "Ligne")
    mark = 1.0 if n <= 4 else 0.76
    for i, item in enumerate(items):
        pen.step()
        cx = LEFT + i * w + w / 2
        up = i % 2 == 0
        if n <= 4:  # room to spare: a thread from the mark to its text
            pen.shape(MSO_SHAPE.RECTANGLE, cx - 0.015, line - 0.62 if up else line, 0.03, 0.62, _mix(t["bg"], pen.tone(i), 0.6), "Fil")
        pen.badge(item["icon"], cx - mark / 2, line - mark / 2, mark, pen.tone(i))
        y = TOP - 0.1 if up else line + 0.62
        pen.stack(cx - w / 2 + 0.08, y, w - 0.16, 1.9, item["head"], item["text"],
                  26 if n <= 3 else 22 if n <= 4 else 19, 19 if n <= 4 else 16, PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM if up else MSO_ANCHOR.TOP)


def _etapes_stairs(pen: Painter, s: dict) -> None:
    """An ascending staircase: each step goes further."""
    t, items = pen.t, s["items"]
    n = len(items)
    gap = 0.12
    w = (CONTENT_WIDTH - gap * (n - 1)) / n
    room = pen.bottom - TOP
    for i, step in enumerate(items):
        pen.step()
        h = room * (0.62 + 0.38 * i / max(n - 1, 1))
        x, y = LEFT + i * (w + gap), pen.bottom - h
        fill = _mix(t["accent"], t["bg"], 0.4 * (n - 1 - i) / max(n - 1, 1))
        pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, fill, "Marche")
        color = _readable(fill, t)
        pen.text(x + 0.2, y + 0.12, w - 0.4, 0.75, str(i + 1), 34, color, True, t["title_font"])
        pen.stack(x + 0.2, y + 0.82, w - 0.36, h - 0.92, step["head"], step["text"], 21 if n <= 4 else 18, 18 if n <= 4 else 15, head_color=color, body_color=color)


def _etapes_circles(pen: Painter, s: dict) -> None:
    """Pastilles joined by arrows."""
    t, items = pen.t, s["items"]
    n = len(items)
    w = CONTENT_WIDTH / n
    for i, step in enumerate(items):
        pen.step()
        x = LEFT + i * w
        pen.badge(step["icon"], x + w / 2 - 0.62, TOP + 0.1, 1.24, pen.tone(i))
        if i < n - 1:
            pen.shape(MSO_SHAPE.RIGHT_ARROW, x + w - 0.28, TOP + 0.52, 0.56, 0.4, _mix(t["bg"], t["accent"], 0.5), "Flèche")
        pen.stack(x + 0.1, TOP + 1.55, w - 0.2, pen.bottom - TOP - 1.6, f"{i + 1}. {step['head']}", step["text"], 22 if n <= 4 else 19, 19 if n <= 4 else 16, PP_ALIGN.CENTER)


def _etapes(pen: Painter, s: dict) -> None:
    choice = pen.variant("etapes", 5)
    n = len(s["items"])
    if choice == 1:
        return _etapes_stairs(pen, s)
    if choice == 2:
        return _etapes_circles(pen, s)
    if choice == 3:
        return _etapes_ribbons(pen, s)
    if choice == 4 and n <= 4:
        return _etapes_hexagons(pen, s)
    t, items = pen.t, s["items"]
    n = len(items)
    w = (CONTENT_WIDTH + 0.22 * (n - 1)) / n
    y = TOP + 0.1
    size = 22 if n <= 3 else 20 if n == 4 else 17
    for i, step in enumerate(items):
        pen.step()
        x = LEFT + i * (w - 0.22)
        arrow = pen.shape(MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON, x, y, w, 1.15, t["accent"] if i % 2 == 0 else _mix(t["accent"], t["bg"], 0.28), "Étape")
        arrow.adjustments[0] = 0.25
        color = _readable(t["accent"], t)
        pen.icon(step["icon"], x + w / 2 - 0.42 + (0.1 if i else -0.05), y + 0.3, 0.55, color)
        pen.text(x + (0.42 if i else 0.2), y + 0.3, 0.5, 0.55, str(i + 1), 26, color, True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
        pen.stack(x + 0.1, y + 1.4, w - 0.42, 3.3, step["head"], step["text"], 23 if n <= 4 else 19, size)


def _etapes_ribbons(pen: Painter, s: dict) -> None:
    """Ribbons on a pale column, left then right, the idea on the other side."""
    t, items = pen.t, s["items"]
    n = len(items)
    room = pen.bottom - TOP
    row = room / n
    h = min(row - 0.12, 0.92)
    cx = WIDTH / 2
    pen.step()
    pen.shape(MSO_SHAPE.RECTANGLE, cx - 0.6, TOP - 0.02, 1.2, room + 0.04, _mix(t["bg"], t["ink"], 0.07), "Colonne")
    for i, item in enumerate(items):
        pen.step()
        y = TOP + i * row + (row - h) / 2
        fill = pen.hue(i)
        left = i % 2 == 0
        x = cx - 1.45 if left else cx - 0.6
        tab = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 2.05, h, fill, "Ruban")
        tab.adjustments[0] = 0.5
        on = _readable(fill, t)
        dot = h - 0.16
        pen.text(x + 0.26 if left else x + 2.05 - 0.26 - 0.7, y, 0.7, h, f"{i + 1:02d}", 23, on, True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        circle = x + 2.05 - dot - 0.08 if left else x + 0.08
        pen.shape(MSO_SHAPE.OVAL, circle, y + 0.08, dot, dot, "FFFFFF", "Pastille")
        pen.icon(item["icon"], circle + dot * 0.21, y + 0.08 + dot * 0.21, dot * 0.58, fill if on == "FFFFFF" else t["deep"])
        if left:
            pen.stack(LEFT, y - 0.05, cx - 1.7 - LEFT, h + 0.1, item["head"], item["text"], 21, 16, PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        else:
            pen.stack(cx + 1.7, y - 0.05, WIDTH - LEFT - cx - 1.7, h + 0.1, item["head"], item["text"], 21, 16, anchor=MSO_ANCHOR.MIDDLE)


def _etapes_hexagons(pen: Painter, s: dict) -> None:
    """Soft hexagons that go up and down, the icon above each."""
    t, items = pen.t, s["items"]
    n = len(items)
    w = CONTENT_WIDTH / n
    wave = 0.3
    h = pen.bottom - TOP - wave
    for i, item in enumerate(items):
        pen.step()
        x = LEFT + i * w
        y = TOP + (wave if i % 2 == 0 else 0)
        hue = pen.hue(i)
        fill = _mix(t["bg"], hue, 0.2)
        sp = pen.shape(MSO_SHAPE.HEXAGON, x + 0.04, y, w - 0.08, h, fill, "Hexagone")
        sp.adjustments[0] = 0.16
        pen.badge(item["icon"], x + w / 2 - 0.42, y + 0.24, 0.84, hue)
        pen.stack(x + 0.48, y + 1.18, w - 0.96, h - 1.45, item["head"], item["text"], 21 if n <= 3 else 20, 16 if n <= 3 else 15, PP_ALIGN.CENTER)


def _comparaison(pen: Painter, s: dict) -> None:
    t = pen.t
    if len(s["left"]["points"]) == len(s["right"]["points"]) <= 4 and pen.variant("comparaison", 2) == 0:
        return _comparaison_rows(pen, s)
    gap = 0.5
    w = (CONTENT_WIDTH - gap) / 2
    avail = pen.bottom - TOP
    for size in (27, 25, 23, 21):  # as big as the points allow: few points must not float in an empty column
        need = max(sum(text_height(p, size, w - 0.92) + 0.17 for p in side["points"]) for side in (s["left"], s["right"]))
        if need + 1.45 <= avail * 0.86:
            break
    h = min(max(need + 1.6, avail * 0.78), avail)
    top = TOP + (avail - h) * 0.4
    for i, side in enumerate((s["left"], s["right"])):
        pen.step()
        x = LEFT + i * (w + gap)
        fill = t["accent"] if i == 0 else t["second"]
        pen.shape(MSO_SHAPE.RECTANGLE, x, top, w, h, t["panel"], "Colonne")
        pen.gradient(MSO_SHAPE.RECTANGLE, x, top, w, 0.9, fill, _mix(fill, DARK, 0.2), 0, "Titre de colonne")
        pen.text(x + 0.3, top, w - 0.6, 0.9, side["title"] or " ", 24, _readable(fill, t), True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
        pen.bullets(x + 0.3, top + 1.2, w - 0.6, h - 1.35, side["points"], size, gap=14, mark=fill if not t["dark"] else t["accent"])
    pen.step("zoom")
    pen.shape(MSO_SHAPE.OVAL, LEFT + w - 0.2, top + 0.05, 0.9, 0.9, t["bg"], "VS")
    pen.text(LEFT + w - 0.2, top + 0.05, 0.9, 0.9, "VS", 19, t["ink"], True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)


def _comparaison_rows(pen: Painter, s: dict) -> None:
    """Cause and effect: one wide pill per pair, the link in the middle."""
    t = pen.t
    left, right = s["left"], s["right"]
    gap = 0.45
    w = (CONTENT_WIDTH - gap) / 2
    pen.step()
    for i, side in enumerate((left, right)):
        head = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, LEFT + i * (w + gap) + 0.3, TOP, w - 0.6, 0.66, t["deep"], "Titre de colonne")
        head.adjustments[0] = 0.5
        pen.text(LEFT + i * (w + gap) + 0.5, TOP, w - 1.0, 0.66, side["title"] or " ", 21, _readable(t["deep"], t), True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    n = len(left["points"])
    y0 = TOP + 0.84
    row = 0.17
    h = min((pen.bottom - y0 - row * (n - 1)) / n, 1.05)
    for i, (a, b) in enumerate(zip(left["points"], right["points"])):
        pen.step()
        y = y0 + i * (h + row)
        fill = pen.hue(i + 1 if t["second"] != t["accent"] else i) if i else t["accent"]
        pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, LEFT, y, CONTENT_WIDTH, h, fill, "Ligne").adjustments[0] = 0.5
        on = _readable(fill, t)
        pen.text(LEFT + 0.45, y + 0.04, w - 0.9, h - 0.08, a, 19, on, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        pen.text(LEFT + w + gap + 0.45, y + 0.04, w - 0.9, h - 0.08, b, 19, on, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        dot = min(h + 0.1, 0.84)
        pen.shape(MSO_SHAPE.OVAL, WIDTH / 2 - dot / 2, y + (h - dot) / 2, dot, dot, "FFFFFF", "Lien")
        pen.icon("arrow-right", WIDTH / 2 - dot * 0.28, y + h / 2 - dot * 0.28, dot * 0.56, fill if _readable(fill, t) == "FFFFFF" else t["deep"])


def _chiffres_band(pen: Painter, s: dict) -> None:
    """The figures on one band of colour across the whole slide."""
    t, stats = pen.t, s["stats"]
    y, h = TOP + 0.55, 3.5
    pen.step()
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, y, WIDTH, h, t["accent"], t["deep"], 0, "Bande")
    on = _readable(t["accent"], t)
    w = CONTENT_WIDTH / len(stats)
    for i, stat in enumerate(stats):
        pen.step("zoom")
        x = LEFT + i * w
        pen.icon(stat["icon"], x + w / 2 - 0.3, y + 0.3, 0.6, on)
        pen.text(x + 0.1, y + 1.0, w - 0.2, 1.25, stat["value"], 56, on, True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        pen.text(x + 0.2, y + 2.3, w - 0.4, 1.05, stat["label"], 19, on, align=PP_ALIGN.CENTER)


def _chiffres(pen: Painter, s: dict) -> None:
    if pen.variant("chiffres", 2) == 1:
        return _chiffres_band(pen, s)
    t = pen.t
    stats = s["stats"]
    gap = 0.28
    w = (CONTENT_WIDTH - gap * (len(stats) - 1)) / len(stats)
    h = pen.bottom - TOP - 0.2
    y = TOP + 0.1
    longest = max(len(x["value"]) for x in stats)
    size = _fit(int(longest * 4 / len(stats)), [(6, 62), (9, 50), (13, 40), (10_000, 30)])
    for i, stat in enumerate(stats):
        pen.step("zoom")
        x = LEFT + i * (w + gap)
        strong = i == 0
        if strong:
            pen.gradient(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, t["accent"], t["deep"], 300, "Carte").adjustments[0] = 0.04
        else:
            pen.card(x, y, w, h, i)
        color = _readable(t["accent"], t) if strong else t["accent"] if not t["dark"] else t["second"]
        pen.icon(stat["icon"], x + w / 2 - 0.36, y + 0.42, 0.72, color)
        pen.text(x + 0.2, y + 1.3, w - 0.4, 1.3, stat["value"], size, color, True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        pen.text(x + 0.3, y + 2.75, w - 0.6, 1.7, stat["label"], 18, _readable(t["accent"], t) if strong else t["ink"], align=PP_ALIGN.CENTER)


def _graphique(pen: Painter, s: dict) -> None:
    """A native chart: the student can edit its numbers in PowerPoint."""
    t = pen.t
    data = CategoryChartData()
    data.categories = [x["label"] for x in s["series"]]
    data.add_series(s["title"][:40], [x["value"] for x in s["series"]])
    donut = s.get("chart") == "donut"
    key = s.get("key") or ""
    w = 7.4 if key else CONTENT_WIDTH
    pen.step("roue" if donut else "trace")  # the ring turns, the bars grow
    frame = pen.slide.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT if donut else XL_CHART_TYPE.BAR_CLUSTERED, Inches(LEFT), Inches(TOP), Inches(w), Inches(pen.bottom - TOP), data)
    chart = frame.chart
    chart.font.size, chart.font.name = Pt(15), BODY_FONT
    chart.font.color.rgb = _rgb(t["ink"])
    chart.has_title = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.show_value, labels.font.size, labels.font.bold = True, Pt(15), True
    series = plot.series[0]
    colors = [t["accent"], t["second"], _mix(t["accent"], t["bg"], 0.4), _mix(t["second"], t["bg"], 0.4), t["muted"], _mix(t["accent"], t["second"], 0.5)]
    if donut:
        labels.show_percentage = False
        chart.has_legend = True
        chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.RIGHT, False
        chart.legend.font.size = Pt(14)
        for i in range(len(s["series"])):
            point = series.points[i]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = _rgb(colors[i % len(colors)])
    else:
        chart.has_legend = False
        plot.gap_width = 55
        labels.position = XL_LABEL_POSITION.OUTSIDE_END
        chart.value_axis.visible, chart.value_axis.has_major_gridlines = False, False
        chart.category_axis.reverse_order = True
        chart.category_axis.format.line.fill.background()
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = _rgb(t["accent"])
    if not key:
        return
    pen.step()
    x = LEFT + w + 0.3
    room = CONTENT_WIDTH - w - 0.3
    tint = t["accent"] if not t["dark"] else t["second"]
    top = max(s["series"], key=lambda v: v["value"])  # the chart's own figure: never invented
    figure = f"{top['value']:g}".replace(".", ",")
    size = _fit(len(key), [(70, 24), (120, 21), (10_000, 18)])
    key_h = text_height(key, size, room - 0.6, t["title_font"], True)
    big = 50 if len(figure) <= 4 else 38
    h = min(pen.bottom - TOP - 0.2, 0.45 + 0.65 + 0.95 + 0.45 + 0.35 + key_h + 0.35)
    y = TOP + (pen.bottom - TOP - h) / 2
    pen.card(x, y, room, h, 1)
    pen.icon(s.get("icon") or "chart-pie", x + 0.3, y + 0.4, 0.6, tint)
    pen.text(x + 0.3, y + 1.05, room - 0.6, 0.95, figure, big, tint, True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
    pen.text(x + 0.3, y + 2.0, room - 0.6, 0.45, top["label"], 15, t["muted"], True, anchor=MSO_ANCHOR.TOP)
    pen.shape(MSO_SHAPE.RECTANGLE, x + 0.3, y + 2.5, 0.8, 0.05, tint, "Filet")
    pen.text(x + 0.3, y + 2.75, room - 0.6, key_h + 0.2, key, size, t["ink"], True, t["title_font"])


def _encadre(pen: Painter, s: dict) -> None:
    t = pen.t
    x, y, w, h = LEFT + 0.3, TOP + 0.35, CONTENT_WIDTH - 0.6, 4.2
    frame = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, t["panel"], "Encadré")
    frame.adjustments[0] = 0.04
    frame.line.color.rgb = _rgb(t["accent"])
    frame.line.width = Pt(2.5)
    pen.text(x + 0.45, y + 0.02, 1.2, 1.2, "“", 96, t["second"], True, "Cambria")
    if s.get("label"):
        width = 0.17 * len(s["label"]) + 0.6
        pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.6, y - 0.27, width, 0.54, t["accent"], "Étiquette").adjustments[0] = 0.3
        pen.text(x + 0.6, y - 0.27, width, 0.54, s["label"], 19, _readable(t["accent"], t), True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    size = _fit(len(s["text"]), [(90, 36), (150, 31), (10_000, 26)])
    pen.text(x + 0.8, y + 0.4, w - 1.6, h - 0.7, s["text"], size, bold=True, font=t["title_font"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def _picture(pen: Painter, path: Path, x: float, y: float, w: float, h: float) -> bool:
    try:
        with Image.open(path) as img:
            ratio = img.width / img.height
            data: io.BytesIO | None = None
            if img.format not in ("PNG", "JPEG", "GIF", "BMP", "TIFF"):  # webp and the like: PowerPoint can't read them
                data = io.BytesIO()
                img.convert("RGBA").save(data, "PNG")
                data.seek(0)
    except OSError:
        return False
    draw_w, draw_h = (w, w / ratio) if w / ratio <= h else (h * ratio, h)
    pen.slide.shapes.add_picture(data or str(path), Inches(x + (w - draw_w) / 2), Inches(y + (h - draw_h) / 2), Inches(draw_w), Inches(draw_h))
    return True


def _figure(pen: Painter, s: dict, images_dir: Path) -> None:
    t = pen.t
    points = s["points"]
    caption = s.get("caption") or ""
    width = 7.5 if points else CONTENT_WIDTH
    height = pen.bottom - TOP - (0.42 if caption else 0)
    sheet = pen.shape(MSO_SHAPE.RECTANGLE, LEFT, TOP, width, height, "FFFFFF", "Fond de l'image")
    sheet.line.color.rgb = _rgb(_mix(t["bg"], t["accent"], 0.3))
    sheet.line.width = Pt(1)
    pen.step()
    if not _picture(pen, images_dir / s["image"], LEFT + 0.12, TOP + 0.12, width - 0.24, height - 0.24):
        return
    if caption:
        pen.text(LEFT, TOP + height + 0.07, width, 0.38, caption[:150], 13, t["muted"], italic=True, align=PP_ALIGN.CENTER)
    if points:
        pen.step()
        x = LEFT + width + 0.3
        room = CONTENT_WIDTH - width - 0.3
        pen.card(x, TOP, room, pen.bottom - TOP, 1)
        pen.bullets(x + 0.28, TOP + 0.35, room - 0.5, pen.bottom - TOP - 0.5, points, 21, gap=14)


def _table(pen: Painter, s: dict) -> None:
    t = pen.t
    rows = s["rows"]
    cols = len(rows[0])
    caption = s.get("caption") or ""
    room = pen.bottom - TOP - (0.42 if caption else 0)
    column = CONTENT_WIDTH / cols - 0.22
    def heights(size: float) -> list[float]:
        return [max(max(text_height(c, size, column, bold=r == 0) for c in row) + 0.13, 0.42) for r, row in enumerate(rows)]
    size = 20
    while size > 11 and sum(heights(size)) > room:
        size -= 1
    tall = heights(size)
    spare = min((room - sum(tall)) / len(rows), 0.2) if sum(tall) < room else 0
    pen.step()
    shape = pen.slide.shapes.add_table(len(rows), cols, Inches(LEFT), Inches(TOP), Inches(CONTENT_WIDTH), Inches(sum(tall)))
    table = shape.table
    for r, height in enumerate(tall):
        table.rows[r].height = Inches(height + spare)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.fill.solid()
            cell.fill.fore_color.rgb = _rgb(t["accent"] if r == 0 else t["panel"] if r % 2 == 0 else t["bg"])
            _run(cell.text_frame.paragraphs[0], value, size, _readable(t["accent"], t) if r == 0 else t["ink"], r == 0)
    if caption:
        pen.text(LEFT, pen.bottom - 0.3, CONTENT_WIDTH, 0.35, caption[:150], 13, t["muted"], italic=True, align=PP_ALIGN.CENTER)


def _plan_road(pen: Painter, parts: list[str]) -> None:
    """The plan as a road: the parts in a row, in the order of the talk."""
    t = pen.t
    n = len(parts)
    w = CONTENT_WIDTH / n
    line = TOP + 1.3
    pen.shape(MSO_SHAPE.RECTANGLE, LEFT, line - 0.03, CONTENT_WIDTH, 0.06, _mix(t["bg"], t["accent"], 0.4), "Route")
    for i, part in enumerate(parts):
        pen.step()
        cx = LEFT + i * w + w / 2
        fill = pen.tone(i)
        pen.shape(t["badge"], cx - 0.6, line - 0.6, 1.2, 1.2, fill, "Partie")
        pen.text(cx - 0.6, line - 0.6, 1.2, 1.2, f"{i + 1:02d}", 28, _readable(fill, t), True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        pen.text(cx - w / 2 + 0.08, line + 0.85, w - 0.16, 1.6, part, 23, bold=True, font=t["title_font"], align=PP_ALIGN.CENTER)


def _plan_lines(pen: Painter, parts: list[str]) -> None:
    """A real table of contents: the number, the part, a thin rule."""
    t = pen.t
    columns = 2 if len(parts) > 4 else 1
    rows = (len(parts) + columns - 1) // columns
    gap = 0.7
    w = (CONTENT_WIDTH - gap * (columns - 1)) / columns
    h = min((pen.bottom - TOP - 0.1) / rows, 1.1)
    for i, part in enumerate(parts):
        pen.step()
        x, y = LEFT + (i // rows) * (w + gap), TOP + 0.05 + (i % rows) * h
        pen.text(x, y, 1.1, h - 0.08, f"{i + 1:02d}", 26, t["accent"], True, t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
        pen.text(x + 1.15, y, w - 1.2, h - 0.08, part, 25, bold=True, font=t["title_font"], anchor=MSO_ANCHOR.MIDDLE)
        pen.shape(MSO_SHAPE.RECTANGLE, x, y + h - 0.05, w, 0.012, _mix(t["bg"], t["ink"], 0.18), "Filet")


def _plan(pen: Painter, parts: list[str]) -> None:
    if pen.t["skin"] in ("halo", "curve"):
        return _plan_lines(pen, parts)
    if pen.variant("plan", 2) == 1 and len(parts) <= 6:
        return _plan_road(pen, parts)
    t = pen.t
    columns = 2 if len(parts) > 3 else 1
    rows = (len(parts) + columns - 1) // columns
    gap = 0.25
    w = (CONTENT_WIDTH - gap * (columns - 1)) / columns
    h = min((pen.bottom - TOP - gap * (rows - 1)) / rows, 1.3)
    for i, part in enumerate(parts):
        pen.step()
        x, y = LEFT + (i % columns) * (w + gap), TOP + 0.1 + (i // columns) * (h + gap)
        pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, t["panel"], "Partie")
        pen.gradient(MSO_SHAPE.RECTANGLE, x, y, 1.05, h, t["accent"], t["deep"], 270, "Numéro")
        pen.text(x, y, 1.05, h, f"{i + 1:02d}", 30, _readable(t["accent"], t), True, t["title_font"], PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        pen.text(x + 1.3, y, w - 1.5, h, part, 24, bold=True, font=t["title_font"], anchor=MSO_ANCHOR.MIDDLE)


def _progress(pen: Painter, parts: list[str], current: str | None, number: int, total: int) -> None:
    """The strip at the bottom of every slide: where we are in the talk, and which slide."""
    t = pen.t
    if t["foot"] == "line":
        end = WIDTH - LEFT if not pen.side else WIDTH - pen.side - 0.4
        label = (current or "").upper()
        pen.text(LEFT, 7.0, 3.2, 0.3, label, 11, t["ink"], True, anchor=MSO_ANCHOR.MIDDLE).name = "!!Partie"
        start = LEFT + 0.12 * len(label) + 0.3
        pen.shape(MSO_SHAPE.RECTANGLE, start, 7.145, max(end - start - 0.6, 0.1), 0.02, t["accent"], "Filet")
        pen.text(end - 0.5, 7.0, 0.5, 0.3, str(number), 12, t["ink"], True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        return
    strip = t["deep"] if not t["dark"] else t["panel"]
    pen.shape(MSO_SHAPE.RECTANGLE, 0, STRIP, WIDTH, HEIGHT - STRIP, strip, "Barre")
    on_strip = _readable(strip, t)
    start, room = 0.35, WIDTH - 0.35 - 1.1
    width = room / max(len(parts), 1)
    for i, part in enumerate(parts):
        lit = part == current
        if lit:
            pen.shape(MSO_SHAPE.RECTANGLE, start + i * width + 0.04, STRIP + 0.07, width - 0.08, HEIGHT - STRIP - 0.14, t["second"], "!!Partie en cours")  # glides with Morph
        pen.text(start + i * width + 0.08, STRIP, width - 0.16, HEIGHT - STRIP, part, 11.5, _readable(t["second"], t) if lit else _mix(on_strip, strip, 0.3), lit,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    pen.text(WIDTH - 1.05, STRIP, 0.8, HEIGHT - STRIP, f"{number} / {total}", 12, on_strip, True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


# --- pages de garde -------------------------------------------------------------

def _people(pen: Painter, info: dict, x: float, y: float, w: float, color: str, muted: str, stacked: bool = False, solo=PP_ALIGN.LEFT) -> None:
    groups = [(label, names) for label, names in ((info["by_label"], info["authors"]), (info["under_label"], info["supervisors"])) if names]
    for i, (label, names) in enumerate(groups):
        width = w if stacked else w / len(groups)
        cx, cy = (x, y + i * 1.15) if stacked else (x + i * width, y)
        align = PP_ALIGN.LEFT if stacked or (len(groups) > 1 and i == 0) else solo if len(groups) == 1 else PP_ALIGN.RIGHT
        box = pen.text(cx, cy, width, 1.1, label, 14, muted, align=align)
        shown = [name[:60] for name in names[:3 if not stacked else 2]]
        size = 19
        while size > 11 and sum(text_height(name, size, width, bold=True) for name in shown) > 0.85:
            size -= 1
        for name in shown:
            p = box.text_frame.add_paragraph()
            p.alignment = align
            _run(p, name, size, color, True)


def _logos(pen: Painter, info: dict, images_dir: Path, x: float, y: float, plate: bool = True) -> None:
    logos = info["logos"]
    if not logos:
        return
    if plate:
        pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 1.45 * len(logos) + 0.25, 1.35, "FFFFFF", "Fond des logos").adjustments[0] = 0.1
    for i, name in enumerate(logos):
        _picture(pen, images_dir / str(name), x + 0.17 + i * 1.45, y + 0.12, 1.3, 1.1)


def _cover_classic(pen: Painter, slide, info: dict, images_dir: Path) -> None:
    t, logos, header = pen.t, info["logos"], info["header"]
    y = 0.55
    if logos or header:
        sheet = "FFFFFF" if t["dark"] else t["panel"]
        pen.shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, 1.5, sheet, "En-tête")
        pen.shape(MSO_SHAPE.RECTANGLE, 0, 1.5, WIDTH, 0.06, t["second"], "Filet")
        if logos:
            _picture(pen, images_dir / str(logos[0]), 0.45, 0.14, 1.5, 1.22)
        if len(logos) > 1:
            _picture(pen, images_dir / str(logos[1]), WIDTH - 1.95, 0.14, 1.5, 1.22)
        if header:
            ink = _readable(sheet, t) if t["dark"] else t["ink"]
            box = pen.text(2.2, 0.1, WIDTH - 4.4, 1.3, header[0][:80], 15, ink, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            for line in header[1:4]:
                p = box.text_frame.add_paragraph()
                p.alignment = PP_ALIGN.CENTER
                _run(p, line[:80], 13, ink)
        y = 1.75
    elif not info["authors"]:
        y = 1.6
    if info["label"]:
        pen.text(LEFT, y, CONTENT_WIDTH, 0.42, info["label"].upper()[:80], 17, t["accent"] if not t["dark"] else t["second"], True, align=PP_ALIGN.CENTER)
        y += 0.5
    x, w, h = 1.1, WIDTH - 2.2, 2.3
    pen.gradient(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, t["accent"], t["deep"], 320, "Cadre du titre").adjustments[0] = 0.05
    pen.shape(MSO_SHAPE.RECTANGLE, x + w / 2 - 0.7, y + h - 0.05, 1.4, 0.1, t["second"], "Filet")
    title = info["title"]
    _set_title(slide, title, _readable(t["accent"], t), t["title_font"], _fit(len(title), [(50, 38), (90, 32), (140, 27), (10_000, 22)]), x + 0.4, y + 0.1, w - 0.8, h - 0.25, align=PP_ALIGN.CENTER)
    _people(pen, info, LEFT, y + h + 0.3, CONTENT_WIDTH, t["ink"], t["muted"], solo=PP_ALIGN.CENTER)
    if info["year"]:
        pen.text(LEFT, 6.98, CONTENT_WIDTH, 0.36, info["year"][:60], 15, t["muted"], align=PP_ALIGN.CENTER)


def _cover_split(pen: Painter, slide, info: dict, images_dir: Path) -> None:
    t = pen.t
    w = 7.6
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, w, HEIGHT, t["accent"], t["deep"], 310, "Panneau")
    pen.shape(MSO_SHAPE.OVAL, w - 2.2, -1.4, 3.2, 3.2, _mix(t["accent"], _readable(t["accent"], t), 0.1), "Décor")
    pen.shape(MSO_SHAPE.RECTANGLE, w - 0.1, 0, 0.1, HEIGHT, t["second"], "Filet")
    on = _readable(t["accent"], t)
    if info["label"]:
        pen.text(0.7, 0.95, w - 1.4, 0.42, info["label"].upper()[:60], 16, on, True)
    title = info["title"]
    _set_title(slide, title, on, t["title_font"], _fit(len(title), [(45, 40), (80, 33), (130, 27), (10_000, 22)]), 0.7, 1.5, w - 1.4, 3.9, MSO_ANCHOR.TOP)
    if info["year"]:
        pen.text(0.7, 6.65, w - 1.4, 0.36, info["year"][:60], 15, on)
    x = w + 0.5
    room = WIDTH - x - 0.45
    y = 0.6
    if info["logos"]:
        _logos(pen, info, images_dir, x, y, plate=t["dark"])
        y += 1.55
    if info["header"]:
        ink = t["ink"]
        box = pen.text(x, y, room, 1.35, info["header"][0][:70], 14, ink, True)
        for line in info["header"][1:4]:
            _run(box.text_frame.add_paragraph(), line[:70], 12, t["muted"])
        y += 1.5
    _people(pen, info, x, max(y, 3.2), room, t["ink"], t["muted"], stacked=True)


def _cover_full(pen: Painter, slide, info: dict, images_dir: Path) -> None:
    t = pen.t
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, HEIGHT, t["deep"], t["accent"], 330, "Fond")
    on = _readable(t["accent"], t)
    pale = _mix(t["accent"], on, 0.14)
    pen.shape(MSO_SHAPE.OVAL, 9.6, -2.6, 6.6, 6.6, pale, "Décor")
    pen.shape(MSO_SHAPE.OVAL, 11.4, 2.9, 1.1, 1.1, t["second"], "Décor")
    pen.shape(MSO_SHAPE.OVAL, -1.5, 5.8, 3.0, 3.0, pale, "Décor")
    if t["motif"] == "organique":
        tilt = pen.shape(MSO_SHAPE.ROUNDED_RECTANGLE, 8.9, 4.6, 3.6, 3.6, pale, "Décor")
        tilt.adjustments[0], tilt.rotation = 0.22, 28
        pen.shape(MSO_SHAPE.MATH_PLUS, 12.3, 0.4, 0.5, 0.5, on, "Décor")
        pen.shape(MSO_SHAPE.DONUT, 8.5, 0.55, 0.45, 0.45, on, "Décor").adjustments[0] = 0.2
    _logos(pen, info, images_dir, LEFT, 0.5)
    y = 2.05 if info["logos"] else 1.0
    if info["label"]:
        pen.text(LEFT, y, 9.5, 0.42, info["label"].upper()[:70], 17, t["second"] if _readable(t["second"], t) != on else on, True)
        y += 0.5
    title = info["title"]
    _set_title(slide, title, on, t["title_font"], _fit(len(title), [(50, 42), (90, 34), (140, 28), (10_000, 23)]), LEFT, y, 10.2, 2.4)
    pen.shape(MSO_SHAPE.RECTANGLE, LEFT, y + 2.5, 1.5, 0.09, t["second"], "Filet")
    _people(pen, info, LEFT, y + 2.75, 10.2, on, _mix(on, t["accent"], 0.2))
    if info["year"]:
        pen.text(LEFT, 6.95, 10, 0.36, info["year"][:60], 15, on)


def _school_head(pen: Painter, info: dict, images_dir: Path) -> None:
    """The top of a report's cover: French on the left, the logos between, English on the right."""
    t = pen.t
    sheet = "FFFFFF" if t["dark"] else t["bg"]
    pen.shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, 1.95, sheet, "En-tête")
    pen.shape(MSO_SHAPE.RECTANGLE, 0, 1.95, WIDTH, 0.06, t["second"], "Filet")
    ink = "14233A" if t["dark"] else t["ink"]
    fr, en = info["header"], info["header_en"]

    def column(lines: list[str], x: float, w: float) -> None:
        size = 12.5
        while size > 6 and sum(text_height(line[:90], size, w, bold=True) for line in lines[:7]) > 1.72:
            size -= 0.5
        box = pen.text(x, 0.12, w, 1.75, lines[0][:90], size, ink, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        for i, line in enumerate(lines[1:7], 1):
            p = box.text_frame.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            _run(p, line[:90], size, ink, i != 1)

    logos = info["logos"]
    size = 1.5 if len(logos) < 2 else 1.42
    if fr and en:
        column(fr, 0.3, 4.75)
        column(en, WIDTH - 5.05, 4.75)
    elif fr:
        column(fr, 2.6, WIDTH - 5.2)
    for i, name in enumerate(logos):
        if fr and en:
            x = WIDTH / 2 - (len(logos) * size + (len(logos) - 1) * 0.08) / 2 + i * (size + 0.08)
        else:
            x = 0.5 if i == 0 else WIDTH - 0.5 - size
        _picture(pen, images_dir / str(name), x, 0.25, size, 1.45)


def _school_frame(pen: Painter, x: float, y: float, w: float, h: float) -> tuple[str, float]:
    """The frame of the title, as varied as real report covers. Gives the text colour and the side margin inside it."""
    t = pen.t
    kind = t["frame"]
    if kind == "double":
        outer = pen.shape(MSO_SHAPE.RECTANGLE, x, y, w, h, t["bg"], "Cadre du titre")
        outer.line.color.rgb, outer.line.width = _rgb(t["accent"]), Pt(3)
        inner = pen.shape(MSO_SHAPE.RECTANGLE, x + 0.09, y + 0.09, w - 0.18, h - 0.18, t["bg"], "Cadre du titre")
        inner.line.color.rgb, inner.line.width = _rgb(t["second"]), Pt(1)
        return t["ink"], 0.4
    if kind == "wave":
        pen.gradient(MSO_SHAPE.DOUBLE_WAVE, x - 0.25, y - 0.12, w + 0.5, h + 0.24, t["accent"], t["deep"], 0, "Ruban du titre").adjustments[0] = 0.1
        return _readable(t["accent"], t), 0.7
    if kind == "ribbon":
        pen.gradient(MSO_SHAPE.RECTANGLE, 0, y, WIDTH, h, t["deep"], t["accent"], 0, "Bande du titre")
        pen.shape(MSO_SHAPE.RECTANGLE, 0, y, 0.5, h, t["second"], "Filet")
        pen.shape(MSO_SHAPE.RECTANGLE, WIDTH - 0.5, y, 0.5, h, t["second"], "Filet")
        return _readable(t["accent"], t), 0.1
    pen.gradient(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, t["accent"], t["deep"], 320, "Cadre du titre").adjustments[0] = 0.08
    pen.shape(MSO_SHAPE.RECTANGLE, x + w / 2 - 0.7, y + h - 0.05, 1.4, 0.1, t["second"], "Filet")
    return _readable(t["accent"], t), 0.35


def _cover_school(pen: Painter, slide, info: dict, images_dir: Path) -> None:
    """A presentation for school opens like the report itself."""
    t = pen.t
    _school_head(pen, info, images_dir)
    y = 2.1
    if info["label"]:
        pen.text(LEFT, y, CONTENT_WIDTH, 0.42, info["label"].upper()[:80], 19, t["accent"] if not t["dark"] else t["second"], True, t["title_font"], PP_ALIGN.CENTER)
        y += 0.45
    x, w, h = 0.9, WIDTH - 1.8, 2.2
    color, inside = _school_frame(pen, x, y, w, h)
    title = info["title"]
    _set_title(slide, title, color, t["title_font"], _fit(len(title), [(50, 38), (100, 31), (150, 25), (10_000, 20)]), x + inside, y + 0.15, w - 2 * inside, h - 0.3, align=PP_ALIGN.CENTER)
    y += h + 0.16
    if info["specialty"]:
        pen.text(LEFT, y, CONTENT_WIDTH, 0.34, info["specialty"][:100], 17, t["muted"], italic=True, align=PP_ALIGN.CENTER)
        y += 0.48
    groups = [(label, names) for label, names in ((info["by_label"], info["author_lines"]), (info["under_label"], info["supervisor_lines"])) if names]
    for i, (label, names) in enumerate(groups):
        width = CONTENT_WIDTH / len(groups)
        align = PP_ALIGN.CENTER if len(groups) == 1 else PP_ALIGN.LEFT if i == 0 else PP_ALIGN.RIGHT
        box = pen.text(LEFT + i * width, y, width, 1.3, label.upper(), 14, t["muted"], True, align=align)
        room = 6.98 - y - 0.3
        size = 20
        while size > 11 and sum(text_height(name[:70], size, width, bold=True) for name in names[:4]) > room:
            size -= 1
        for name in names[:4]:
            p = box.text_frame.add_paragraph()
            p.alignment = align
            _run(p, name[:70], size, t["ink"], True)
    if info["year"]:
        pen.text(LEFT, 7.08, CONTENT_WIDTH, 0.32, info["year"][:60], 14, t["muted"], True, align=PP_ALIGN.CENTER)


def _end_school(pen: Painter, slide, thanks: str, info: dict, images_dir: Path) -> None:
    """The last page is the cover again, with the thanks in the frame."""
    t = pen.t
    _school_head(pen, info, images_dir)
    x, w, y, h = 0.9, WIDTH - 1.8, 2.4, 2.3
    color, inside = _school_frame(pen, x, y, w, h)
    _set_title(slide, thanks, color, t["title_font"], 44, x + inside, y + 0.15, w - 2 * inside, h - 0.3, align=PP_ALIGN.CENTER)
    pen.text(1.2, y + h + 0.25, WIDTH - 2.4, 0.8, info["title"][:150], 21, t["ink"], True, t["title_font"], PP_ALIGN.CENTER)
    if info["author_lines"]:
        pen.text(LEFT, y + h + 1.35, CONTENT_WIDTH, 0.4, " · ".join(info["authors"][:3])[:110], 20, t["muted"], True, align=PP_ALIGN.CENTER)
    if info["year"]:
        pen.text(LEFT, 7.08, CONTENT_WIDTH, 0.32, info["year"][:60], 14, t["muted"], True, align=PP_ALIGN.CENTER)


# Where the words go on each curved background: x, y, width, height, align, logos (x, y) if they sit apart from the words.
FIELDS = {"sweep": (LEFT, 1.0, 8.5, 5.7, PP_ALIGN.LEFT, None), "wave": (1.3, 0.75, 10.73, 4.9, PP_ALIGN.CENTER, None), "arc": (6.5, 2.75, 6.1, 4.1, PP_ALIGN.RIGHT, (0.55, 0.45)),
          "fold": (6.3, 0.55, 6.3, 3.95, PP_ALIGN.LEFT, (0.45, 0.4)), "swoosh": (1.3, 1.45, 10.73, 4.6, PP_ALIGN.CENTER, None), "halo": (1.4, 1.0, 10.53, 5.4, PP_ALIGN.CENTER, None)}


def _backdrop(pen: Painter, seed: int = 0) -> str:
    """The great curve of the style, behind a cover, a section or the last page. Gives the colour of the words."""
    t = pen.t
    accent, deep, second = t["accent"], t["deep"], t["second"]
    pale = _mix(t["bg"], second, 0.5)
    on = _readable(accent, t)
    match t["cover"]:
        case "sweep":
            pen.curve([("M", 0, 0), ("L", 11.95, 0), ("C", 10.3, 2.3, 10.5, 5.2, 13.0, HEIGHT), ("L", 0, HEIGHT), ("Z",)], pale)
            pen.curve([("M", 0, 0), ("L", 11.55, 0), ("C", 9.95, 2.4, 10.05, 5.2, 12.05, HEIGHT), ("L", 0, HEIGHT), ("Z",)], second)
            pen.curve([("M", 0, 0), ("L", 11.1, 0), ("C", 9.6, 2.4, 9.55, 5.2, 11.3, HEIGHT), ("L", 0, HEIGHT), ("Z",)], _mix(accent, second, 0.45))
            pen.curve([("M", 0, 0), ("L", 10.75, 0), ("C", 9.3, 2.4, 9.25, 5.2, 10.9, HEIGHT), ("L", 0, HEIGHT), ("Z",)], accent, deep, 270)
            pen.curve([("M", 11.32, 0), ("C", 9.72, 2.4, 9.85, 5.2, 11.75, HEIGHT)], None, stroke="FFFFFF", weight=1.5)
            return on
        case "wave":
            pen.curve([("M", 0, 6.0), ("C", 2.6, 7.1, 5.2, 7.0, 7.4, 6.4), ("C", 9.3, 5.9, 11.4, 5.35, WIDTH, 5.75), ("L", WIDTH, HEIGHT), ("L", 0, HEIGHT), ("Z",)], _mix(t["bg"], t["ink"], 0.08))
            pen.curve([("M", 0, 5.55), ("C", 2.6, 6.8, 5.4, 6.85, 7.6, 6.2), ("C", 9.5, 5.65, 11.5, 5.25, WIDTH, 5.5), ("C", 11.5, 5.5, 9.6, 5.9, 7.7, 6.45), ("C", 5.4, 7.1, 2.6, 7.0, 0, 5.95), ("Z",)], second)
            pen.curve([("M", 0, 5.9), ("C", 2.6, 7.0, 5.4, 7.1, 7.7, 6.45), ("C", 9.6, 5.9, 11.5, 5.5, WIDTH, 5.62), ("C", 11.5, 5.7, 9.6, 6.1, 7.7, 6.65), ("C", 5.4, 7.3, 2.6, 7.2, 0, 6.2), ("Z",)], accent)
            pen.curve([("M", 0, 6.2), ("C", 2.6, 7.2, 5.4, 7.3, 7.7, 6.65), ("C", 9.6, 6.1, 11.5, 5.7, WIDTH, 5.78), ("C", 11.5, 5.86, 9.6, 6.22, 7.7, 6.76), ("C", 5.4, 7.4, 2.6, 7.3, 0, 6.34), ("Z",)], deep)
            return t["accent"]
        case "arc":
            pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, HEIGHT, accent, deep, 300, "Décor")
            pen.curve([("M", WIDTH, 0.72), ("C", 8.2, 0.2, 2.5, 3.2, 2.6, HEIGHT), ("L", WIDTH, HEIGHT), ("Z",)], _mix(accent, second, 0.6))
            pen.curve([("M", WIDTH, 0.95), ("C", 8.4, 0.5, 2.95, 3.4, 3.0, HEIGHT), ("L", WIDTH, HEIGHT), ("Z",)], second)
            pen.curve([("M", WIDTH, 1.2), ("C", 8.6, 0.8, 3.3, 3.6, 3.35, HEIGHT), ("L", WIDTH, HEIGHT), ("Z",)], t["bg"])
            return t["accent"]
        case "fold":
            pen.curve([("M", 0, 0), ("L", 3.1, 0), ("C", 3.3, 3.5, 6.3, 5.5, WIDTH, 5.95), ("L", WIDTH, HEIGHT), ("L", 0, HEIGHT), ("Z",)], accent, deep, 45)
            pen.curve([("M", 6.1, 5.28), ("C", 8.3, 5.75, 11.2, 5.9, WIDTH, 5.95), ("L", 11.7, 6.45), ("L", 12.45, 6.72), ("L", 9.5, 6.55), ("L", 9.9, 6.95), ("Z",)], deep)
            pen.curve([("M", 6.1, 5.28), ("C", 7.2, 5.62, 8.8, 5.85, 10.3, 5.92), ("L", 9.9, 6.2), ("Z",)], second)
            return t["ink"]
        case "swoosh":
            pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, HEIGHT, accent, deep, 300, "Décor")
            pen.curve([("M", 0, 1.3), ("C", 3.4, 0.05, 8.2, 0.05, WIDTH, 0.95), ("L", WIDTH, 0), ("L", 0, 0), ("Z",)], t["bg"])
            pen.curve([("M", 0, 1.3), ("C", 3.4, 0.05, 8.2, 0.05, WIDTH, 0.95), ("C", 8.2, 0.4, 3.4, 0.5, 0, 1.55), ("Z",)], second)
            pen.curve([("M", 0, 6.2), ("C", 4.4, 7.4, 9.2, 7.5, WIDTH, 6.0), ("L", WIDTH, HEIGHT), ("L", 0, HEIGHT), ("Z",)], t["bg"])
            pen.curve([("M", 0, 6.2), ("C", 4.4, 7.4, 9.2, 7.5, WIDTH, 6.0), ("C", 9.2, 7.05, 4.4, 7.0, 0, 5.92), ("Z",)], second)
            return on
    _veil(pen, seed)
    return t["accent"]


def _cover_curve(pen: Painter, slide, info: dict, images_dir: Path, seed: int) -> None:
    t = pen.t
    on = _backdrop(pen, seed)
    x, y, w, h, align, apart = FIELDS[t["cover"]]
    muted = on if on != t["ink"] and on != t["accent"] else t["muted"]
    bottom = y + h
    if info["logos"]:
        if apart:
            _logos(pen, info, images_dir, *apart)
        else:
            wide = 1.45 * len(info["logos"]) + 0.25
            _logos(pen, info, images_dir, x + (w - wide) / 2 if align == PP_ALIGN.CENTER else x, y)
            y += 1.5
    if info["label"]:
        pen.text(x, y, w, 0.4, info["label"].upper()[:70], 15, t["second"] if on in ("FFFFFF", DARK) and _readable(t["second"], t) != on else muted if on not in (t["ink"], t["accent"]) else t["accent"], True, align=align)
        y += 0.5
    people = 1.15 if info["authors"] or info["supervisors"] else 0
    title = info["title"]
    high = bottom - y - people - 0.2
    _set_title(slide, title, on, t["title_font"], _fit(len(title), [(45, 48), (75, 40), (120, 32), (10_000, 24)]), x, y, w, high, MSO_ANCHOR.MIDDLE if people else MSO_ANCHOR.TOP, align)
    if people:
        _people(pen, info, x, bottom - people, w, on if on != t["accent"] else t["ink"], muted, solo=align)


def _end_curve(pen: Painter, slide, thanks: str, info: dict, images_dir: Path, seed: int) -> None:
    t = pen.t
    on = _backdrop(pen, seed)
    x, y, w, h, align, apart = FIELDS[t["cover"]]
    _set_title(slide, thanks, on, t["title_font"], 52, x, y + 0.5, w, 2.0, MSO_ANCHOR.BOTTOM, align)
    pen.text(x, y + 2.65, w, 0.9, info["title"][:140], 21, on if on != t["accent"] else t["ink"], align=align)
    if info["authors"]:
        pen.text(x, y + 3.55, w, 0.45, " · ".join(info["authors"][:3])[:110], 18, on if on != t["accent"] else t["muted"], True, align=align)


def _section_curve(pen: Painter, slide, title: str, number: int, seed: int) -> None:
    t = pen.t
    on = _backdrop(pen, seed)
    x, y, w, _, align, _ = FIELDS[t["cover"]]
    pen.text(x, y + 0.2, w, 1.2, f"{number:02d}", 66, t["second"] if _readable(t["second"], t) == on or on == t["accent"] else on, True, t["title_font"], align=align)
    _set_title(slide, title, on, t["title_font"], 40, x, y + 1.5, w, 2.1, MSO_ANCHOR.TOP, align, lean=t.get("lean", False))


def _cover_hero(pen: Painter, slide, info: dict, images_dir: Path, art: str, seed: int) -> None:
    """The whole slide is the picture, the title sits on it, very large."""
    t = pen.t
    if not _photo(pen, images_dir, art, veil=88):
        _field(pen, seed)
    on = "FFFFFF" if art and (images_dir / art).is_file() else t["ink"]
    y = 0.6
    if info["logos"]:
        _logos(pen, info, images_dir, LEFT, 0.5)
        y = 2.0
    if info["label"]:
        pen.text(LEFT, y, 10, 0.42, info["label"].upper()[:70], 17, t["accent"], True)
    title = info["title"]
    _set_title(slide, title, on, t["title_font"], _fit(len(title), [(40, 60), (70, 50), (110, 40), (10_000, 30)]), LEFT, y + 0.5, 11.2, 3.6, MSO_ANCHOR.BOTTOM)
    _people(pen, info, LEFT, y + 4.25, 11.2, on, on)


def _title_page(prs, theme: dict, info: dict, images_dir: Path, art: str = "", seed: int = 0):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    _background(slide, theme["bg"])
    pen = Painter(slide, theme)
    if info["school"] and (info["header"] or info["logos"]):
        if theme.get("glass"):
            _field(pen, seed)
        _cover_school(pen, slide, info, images_dir)
        return slide
    style = theme["cover"]
    if style == "hero":
        return _cover_hero(pen, slide, info, images_dir, art, seed) or slide
    if style in FIELDS:
        return _cover_curve(pen, slide, info, images_dir, seed) or slide
    if style == "split" and not (info["logos"] or info["header"] or info["authors"] or info["supervisors"]):
        style = "full"  # nothing to put in the right half
    {"split": _cover_split, "full": _cover_full}.get(style, _cover_classic)(pen, slide, info, images_dir)
    return slide


def _end_page(prs, theme: dict, thanks: str, info: dict, images_dir: Path, seed: int = 0):
    t = theme
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    _background(slide, t["bg"] if info["school"] else t["accent"])
    pen = Painter(slide, t)
    if t.get("glass"):
        _field(pen, seed + 1)
    if info["school"] and (info["header"] or info["logos"]):
        _end_school(pen, slide, thanks, info, images_dir)
        return slide
    if t["cover"] in FIELDS:
        _background(slide, t["bg"])
        return _end_curve(pen, slide, thanks, info, images_dir, seed) or slide
    if t.get("glass"):
        _set_title(slide, thanks, t["ink"], t["title_font"], 60, LEFT, 2.1, 11.6, 2.0, MSO_ANCHOR.BOTTOM)
        pen.shape(MSO_SHAPE.RECTANGLE, LEFT, 4.3, 1.6, 0.1, t["accent"], "Filet")
        pen.text(LEFT, 4.6, 11, 0.9, info["title"][:140], 22, t["muted"])
        return slide
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, HEIGHT, t["accent"], t["deep"], 315, "Fond")
    on = _readable(t["accent"], t)
    light = _mix(t["accent"], on, 0.12)
    pen.shape(MSO_SHAPE.OVAL, 10.0, -2.2, 6.0, 6.0, light, "Décor")
    pen.shape(MSO_SHAPE.OVAL, -1.6, 5.4, 3.4, 3.4, light, "Décor")
    pen.shape(MSO_SHAPE.OVAL, 11.5, 5.2, 0.9, 0.9, t["second"], "Décor")
    _logos(pen, info, images_dir, LEFT, 0.6)
    _set_title(slide, thanks, on, t["title_font"], 50, LEFT, 2.3, 10.6, 1.9, MSO_ANCHOR.BOTTOM)
    pen.shape(MSO_SHAPE.RECTANGLE, LEFT, 4.38, 1.6, 0.1, t["second"], "Filet")
    pen.text(LEFT, 4.65, 10.2, 0.9, info["title"][:140], 22, on)
    if info["authors"]:
        pen.text(LEFT, 5.65, 10.2, 0.45, " · ".join(info["authors"][:3])[:110], 20, on, True)
    return slide


def _section(prs, theme: dict, title: str, number: int, seed: int = 0):
    t = theme
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    pen = Painter(slide, t)
    if t["cover"] in FIELDS:
        _background(slide, t["bg"])
        return _section_curve(pen, slide, title, number, seed) or slide
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, HEIGHT, t["deep"], t["accent"], 330, "Fond")
    on = _readable(t["accent"], t)
    pen.shape(MSO_SHAPE.OVAL, 9.2, -2.4, 7.0, 7.0, _mix(t["accent"], on, 0.13), "Décor")
    pen.text(LEFT, 1.7, 3, 1.2, f"{number:02d}", 66, t["second"] if _readable(t["second"], t) != on else on, True, t["title_font"])
    _set_title(slide, title, on, t["title_font"], 42, LEFT, 3.0, 9.2, 2.4, MSO_ANCHOR.TOP)
    return slide


MOTIONS = {"fondu": (10, 0), "monter": (42, 0), "glisser": (2, 8), "zoom": (53, 0), "balayer": (22, 8)}  # PowerPoint's own effect numbers: its panel shows their names
OWN = {"roue": (21, 1), "trace": (22, 8)}  # chosen by a layout for one thing: a ring that turns (Roue), bars that grow (Balayer)
DEFAULT_MOTION = "monter"
STEP_MS, EFFECT_MS = 260, 480  # things overlap a little: a flow, not a queue
SLOW_MS = {"roue": 1100, "trace": 900}  # a chart takes the time to be read as it draws


def _effect(kind: str, spid: str, node: str, delay: int, nid) -> str:
    """One thing appearing: PowerPoint reads this as its own effect, and lets the user change it."""
    target = f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
    fade = f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{nid()}" dur="{EFFECT_MS}"/>{target}</p:cBhvr></p:animEffect>'

    def move(attr: str, start: str, end: str) -> str:
        return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="{nid()}" dur="{EFFECT_MS}" decel="100000" fill="hold"/>{target}'
                f'<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="{start}"/></p:val></p:tav>'
                f'<p:tav tm="100000"><p:val><p:strVal val="{end}"/></p:val></p:tav></p:tavLst></p:anim>')

    preset, subtype = {**MOTIONS, **OWN}[kind]
    head = f'<p:par><p:cTn id="{nid()}" presetID="{preset}" presetClass="entr" presetSubtype="{subtype}" fill="hold" nodeType="{node}"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>'
    show = (f'<p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>{target}'
            '<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>')
    match kind:
        case "monter":
            body = fade + move("ppt_y", "#ppt_y+0.05", "#ppt_y")
        case "glisser":
            body = fade + move("ppt_x", "#ppt_x-0.06", "#ppt_x")
        case "zoom":
            body = fade + move("ppt_w", "#ppt_w*0.82", "#ppt_w") + move("ppt_h", "#ppt_h*0.82", "#ppt_h")
        case "balayer" | "trace":
            body = f'<p:animEffect transition="in" filter="wipe(left)"><p:cBhvr><p:cTn id="{nid()}" dur="{SLOW_MS.get(kind, EFFECT_MS)}"/>{target}</p:cBhvr></p:animEffect>'
        case "roue":
            body = f'<p:animEffect transition="in" filter="wheel(1)"><p:cBhvr><p:cTn id="{nid()}" dur="{SLOW_MS[kind]}"/>{target}</p:cBhvr></p:animEffect>'
        case _:
            body = fade
    return f"{head}{show}{body}</p:childTnLst></p:cTn></p:par>"


def _animate(slide, marks: list[int], end: int, kind: str = DEFAULT_MOTION, click: bool = False, effects: dict[int, str] | None = None) -> None:
    """Things appear one after the other: on their own, or at each click of the presenter.
    `effects`: steps (by their mark) that have an effect of their own instead of `kind`."""
    children = list(slide.shapes._spTree)
    own = effects or {}
    steps = [([str(el.xpath(".//p:cNvPr/@id")[0]) for el in children[a:b]], own.get(a, kind)) for a, b in zip(marks, [*marks[1:], end])]
    steps = [s for s in steps if s[0]][:12]
    if not steps:
        return
    n = [2]

    def nid() -> int:
        n[0] += 1
        return n[0]

    def outer(inner: str, start: str) -> str:
        return (f'<p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst>{start}</p:stCondLst><p:childTnLst>'
                f'<p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{inner}</p:childTnLst></p:cTn></p:par>'
                '</p:childTnLst></p:cTn></p:par>')

    if click:
        pieces = [outer("".join(_effect(how, spid, "clickEffect" if j == 0 else "withEffect", 0, nid) for j, spid in enumerate(ids)), '<p:cond delay="indefinite"/>') for ids, how in steps]
    else:
        flow = "".join(_effect(how, spid, "afterEffect" if k == j == 0 else "withEffect", k * STEP_MS, nid) for k, (ids, how) in enumerate(steps) for j, spid in enumerate(ids))
        pieces = [outer(flow, '<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>')]
    xml = ('<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
           f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{"".join(pieces)}</p:childTnLst></p:cTn>'
           '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
           '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
    _after_cover(slide, xml)


MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _transition_of(sld):
    """The slide's transition element: itself, or the one PowerPoint wraps for Morph (with its fallback)."""
    for child in sld:
        if child.tag == qn("p:transition") or child.tag == f"{{{MC}}}AlternateContent":
            return child
    return None


def _after_cover(slide, xml: str) -> None:
    """transition, then timing: PowerPoint refuses any other order."""
    element = etree.fromstring(xml)
    sld = slide._element
    anchor = sld.find(qn("p:clrMapOvr"))
    if element.tag == qn("p:timing") and _transition_of(sld) is not None:
        anchor = _transition_of(sld)
    anchor.addnext(element)


TRANSITIONS = {"push": '<p:push dir="l"/>', "fade": "<p:fade/>", "zoom": '<p:zoom dir="in"/>', "balayer": '<p:wipe dir="r"/>'}


def _transition(slide, kind: str = "fade") -> None:
    if kind == "morph":
        # PowerPoint 2019 / 365 « Morphose »: what both slides share (title, part marker, decor) glides to its new place,
        # the rest fades. Older PowerPoint, WPS and LibreOffice read the fallback: a plain fade.
        _after_cover(slide, f'<mc:AlternateContent xmlns:mc="{MC}"><mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">'
                            f'<p:transition xmlns:p="{P}" spd="slow"><p159:morph option="byObject"/></p:transition></mc:Choice>'
                            f'<mc:Fallback><p:transition xmlns:p="{P}" spd="med"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>')
        return
    effect = TRANSITIONS.get(kind, TRANSITIONS["fade"])
    _after_cover(slide, f'<p:transition xmlns:p="{P}" spd="med">{effect}</p:transition>')


def _notes(slide, text: str) -> None:
    if text:
        slide.notes_slide.notes_text_frame.text = text


def _prepare(prs) -> None:
    prs.slide_width, prs.slide_height = Inches(WIDTH), Inches(HEIGHT)
    for owner in (prs.slide_master, *prs.slide_layouts):  # the template is 4:3: a slide added by hand must match too
        for ph in list(owner.placeholders):
            name = str(ph.placeholder_format.type)
            if "DATE" in name or "FOOTER" in name or "SLIDE_NUMBER" in name:
                ph._element.getparent().remove(ph._element)
            elif "TITLE" in name and "SUBTITLE" not in name:
                ph.left, ph.top, ph.width, ph.height = Inches(LEFT), Inches(0.36), Inches(10.4), Inches(1.05)
            else:
                ph.left, ph.top, ph.width, ph.height = Inches(LEFT), Inches(TOP), Inches(CONTENT_WIDTH), Inches(BOTTOM - TOP)


DRAW = {"liste": _liste, "grille": _grille, "schema": _schema, "panneau": _panneau, "chronologie": _chronologie, "etapes": _etapes, "comparaison": _comparaison,
        "chiffres": _chiffres, "graphique": _graphique, "encadre": _encadre, "tableau": _table, "grand": _grand}
SIDED = {"panneau": 4.7, "grand": 4.5}
BANDED = ("liste", "grille", "schema", "chronologie", "etapes", "tableau", "comparaison", "graphique")


def _takeaway(pen: Painter, text: str) -> None:
    """The closing line of a slide, in a full-width band."""
    t = pen.t
    y = pen.bottom + 0.14
    pen.gradient(MSO_SHAPE.RECTANGLE, 0, y, WIDTH, 0.62, t["accent"], t["deep"], 0, "À retenir")
    pen.text(LEFT, y, CONTENT_WIDTH, 0.62, text, 20, _readable(t["accent"], t), True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def _customised(theme: dict, colors: dict | None, font: str | None) -> dict:
    """The user's own colours and font on a style: its shapes stay, so every combination is a new look."""
    out = dict(theme)
    accent, second = (colors or {}).get("accent"), (colors or {}).get("second")
    if accent:
        out.update(accent=accent, deep=_mix(accent, "000000", 0.28), panel=_mix(theme["bg"], accent, 0.1 if not theme["dark"] else 0.2), on_accent=_readable(accent, theme))
    if second:
        out["second"] = second
    if font in ("Calibri", "Cambria", "Arial"):
        out["title_font"] = font
    return out


def _passage(motion: str, same_part: bool, morph: bool = False) -> str:
    """How the slide arrives: its animation's cousin; a new part of the talk is felt, a slide of the same part stays quiet.
    `morph`: the slide before was a content slide too: they share their title, part marker and decor, which glide."""
    if motion in ("zoom", "balayer"):
        return motion
    if morph:
        return "morph"
    return "fade" if same_part and motion != "glisser" else "push"


def build_pptx(deck: dict, info: dict, theme_name: str, images_dir: Path, moving: bool = True, colors: dict | None = None, font: str | None = None,
               motion: str = DEFAULT_MOTION, click: bool = False) -> bytes:
    theme = _customised(THEMES.get(theme_name) or THEMES[DEFAULT_THEME], colors, font)
    prs = Presentation()
    _prepare(prs)
    parts = deck.get("parts") or []
    total = len(deck["slides"]) + 3
    seed = zlib.crc32(info["title"].encode())
    first = _title_page(prs, theme, info, images_dir, deck.get("art", ""), seed)
    _notes(first, deck.get("notes", ""))
    if moving:
        _transition(first)
    used = Counter()
    plan = _standard(prs, theme, "Outline" if info["english"] else "Plan de la présentation", seed=seed, parts=parts)
    plan.seed, plan.used = seed, used
    _plan(plan, parts)
    end = len(plan.slide.shapes._spTree)
    _progress(plan, parts, None, 2, total)
    motion = motion if motion in MOTIONS else DEFAULT_MOTION
    if moving:
        _transition(plan.slide, _passage(motion, False))
        _animate(plan.slide, plan.marks, end, motion, click)
    number, sections = 2, 0
    previous_part, after_content = None, False
    for s in deck["slides"]:
        number += 1
        if s["type"] == "section":
            sections += 1
            opener = _section(prs, theme, s["title"], sections, seed)
            _notes(opener, s.get("notes", ""))
            if moving:
                _transition(opener, _passage(motion, False))
            after_content = False
            continue
        style = _night(theme) if theme["alt"] and s["type"] in ("encadre", "grand", "chiffres", "etapes") else theme
        pen = _standard(prs, style, s["title"], s.get("part"), s.get("highlight", ""), SIDED.get(s["type"], 0.0), seed + number // 3, parts)
        pen.images, pen.art = images_dir, s.get("art", "")
        pen.seed, pen.used = seed, used
        base = len(pen.slide.shapes._spTree)  # what a layout draws without steps of its own still appears as one
        takeaway = s.get("takeaway") if s["type"] in BANDED else ""
        if takeaway:
            pen.bottom = BOTTOM - 0.72
        if s["type"] == "figure":
            _figure(pen, s, images_dir)
        else:
            DRAW.get(s["type"], _liste)(pen, s)
        if takeaway:
            pen.bottom = BOTTOM - 0.72
            pen.step()
            _takeaway(pen, takeaway)
        end = len(pen.slide.shapes._spTree)
        _progress(pen, parts, s.get("part"), number, total)
        own = s.get("motion") if s.get("motion") in (*MOTIONS, "aucune") else motion
        if moving and own != "aucune":
            _transition(pen.slide, _passage(own, previous_part == s.get("part"), after_content))
            effects = {at: how for at, how in pen.effects.items() if how != "zoom" or own in ("monter", "zoom")}  # a quiet fade stays quiet
            _animate(pen.slide, pen.marks if pen.marks and pen.marks[0] == base else [base, *pen.marks], end, own, click, effects)
        previous_part, after_content = s.get("part"), True
        _notes(pen.slide, s.get("notes", ""))
    last = _end_page(prs, theme, deck.get("thanks") or "Merci de votre attention", info, images_dir, seed)
    if moving:
        _transition(last)
    prs.core_properties.title = info["title"][:200]
    prs.core_properties.author = ", ".join(info["authors"][:3]) or "Paginya"
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


# --- the slideshow on the site: pictures of each slide as its things appear ------

def _groups(slide) -> list[list[str]]:
    """What appears together: at the same click, or at the same moment of the flow."""
    groups: list[list[str]] = []
    moment = None
    for effect in slide._element.xpath(".//p:timing//p:cTn[@presetID]"):
        target = next(effect.iter(qn("p:spTgt")), None)
        if target is not None:
            delay = effect.find(qn("p:stCondLst"))[0].get("delay")
            if effect.get("nodeType") == "clickEffect" or delay != moment or not groups:
                groups.append([])
            moment = delay
            groups[-1].append(target.get("spid"))
    return groups


def _counts(groups: list) -> list[int]:
    """How many groups each picture shows, ending with all of them: four pictures per slide at most."""
    n = len(groups)
    if not n:
        return [0]
    pictures = min(n, 3)
    return [0, *(math.ceil(n * (k + 1) / pictures) for k in range(pictures))]


def show_plan(path: Path) -> list[dict]:
    plan = []
    for slide in Presentation(path).slides:
        moved = _transition_of(slide._element)
        push = moved is not None and next(moved.iter(qn("p:push")), None) is not None
        first = next(iter(slide._element.xpath(".//p:timing//p:cTn[@presetID]")), None)
        motion = next((k for k, v in MOTIONS.items() if first is not None and str(v[0]) == first.get("presetID")), "")
        plan.append({"frames": len(_counts(_groups(slide))), "push": push, "motion": motion, "click": first is not None and first.get("nodeType") == "clickEffect"})
    return plan


def frame_deck(path: Path, frame: int) -> bytes:
    """The presentation as it looks at this step of its animations."""
    prs = Presentation(path)
    for slide in prs.slides:
        groups = _groups(slide)
        counts = _counts(groups)
        if frame < len(counts) - 1:
            hidden = {spid for group in groups[counts[frame]:] for spid in group}
            for shape in list(slide.shapes):
                if str(shape.shape_id) in hidden:
                    shape._element.getparent().remove(shape._element)
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


def _names(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    out = []
    for v in value if isinstance(value, list) else []:
        name = v.get("name") if isinstance(v, dict) else v
        if name and str(name).strip():
            out.append(str(name).strip())
    return out


def title_info(document: dict, images_dir: Path) -> dict:
    """What the page de garde of the presentation shows, read on the document itself: never left to the AI."""
    blocks = [b for b in document.get("blocks") or [] if not b.get("hidden")]
    meta = document.get("meta") or {}
    cover = meta.get("cover") or {}
    titles = [t for t in (str(b.get("text") or "").strip() for b in blocks if b.get("type") == "title") if t]
    first_heading = next((str(b.get("text") or "").strip() for b in blocks if b.get("type") == "heading"), "")
    written = (document.get("deck") or {}).get("title")  # no cover page in the file: first lines are often not its title
    title = str(cover.get("title") or written or meta.get("title") or (titles[0] if titles else first_heading) or "Présentation").strip()
    logos = [name for name in [document.get("deck_logo"), *(cover.get("logos") or [])] if name and (images_dir / str(name)).is_file()]
    school = document.get("deck_school", True)
    plain = re.compile(r"^[\s*•·.\-_=]*$")
    header = [line for line in _names(cover.get("header_fr")) if not plain.match(line)]
    header_en = [line for line in _names(cover.get("header_en")) if not plain.match(line)]
    structure = str(cover.get("structure") or "").strip()
    if structure and structure not in header:
        header.append(structure)
    english = bool(re.search(r"\b(the|and|of|for)\b", title.lower())) and not re.search(r"\b(le|la|les|des|du|et|pour)\b", title.lower())
    authors = _names(cover.get("authors"))
    with_info = [f"{a.get('name')} ({a.get('info')})" if isinstance(a, dict) and a.get("info") else str(a.get("name") if isinstance(a, dict) else a)
                 for a in (cover.get("authors") or []) if a] if isinstance(cover.get("authors"), list) else authors
    if not school:  # a plain presentation: no establishment, just who speaks
        return {"title": title, "label": "", "header": [], "header_en": [], "logos": [name for name in logos if name == document.get("deck_logo")], "authors": authors, "supervisors": [],
                "author_lines": authors, "supervisor_lines": [], "year": "", "specialty": "", "school": False, "english": english,
                "by_label": "Presented by" if english else "Présenté par", "under_label": ""}
    supervisors = _names(cover.get("supervisors"))
    return {"title": title, "label": str(cover.get("doc_label") or "").strip(), "header": header[:7], "header_en": header_en[:7], "logos": logos[:2], "school": True,
            "authors": authors, "supervisors": supervisors, "author_lines": with_info, "supervisor_lines": supervisors,
            "specialty": str(cover.get("specialty") or "").strip(), "year": str(cover.get("year") or "").strip(),
            "english": english, "by_label": "Presented by" if english else "Présenté par", "under_label": "Supervised by" if english else "Sous la direction de"}
