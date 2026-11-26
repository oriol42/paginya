"""What a slide looks like, in numbers: the same measures for decks made by designers and for Paginya's.

Usage: python -I measure.py out.jsonl deck.pptx [deck.pptx ...]
One JSON line per deck: its transitions, its animations and, for each slide, sizes, margins, photos, density.
The decks are read as data (lxml without entities, nothing run); a broken file is skipped.

Positions are shares of the slide (0..1): a 16:9 and a 4:3 deck compare. What a slide shows includes its
layout and master (a background photo, a band) unless the slide hides them.
"""
import json
import re
import sys
import zipfile
from collections import Counter

from lxml import etree

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
    "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
SPEED = {"slow": 1000, "med": 750, "fast": 500}  # transition speeds before PowerPoint 2010 wrote exact durations
WORD = re.compile(r"[\wÀ-ÿ'’-]+")


def q(tag: str) -> str:
    prefix, name = tag.split(":")
    return f"{{{NS[prefix]}}}{name}"


class Deck:
    def __init__(self, path: str):
        self.zip = zipfile.ZipFile(path)
        self.names = set(self.zip.namelist())
        self.cache: dict[str, etree._Element] = {}
        pres = self.xml("ppt/presentation.xml")
        size = pres.find(q("p:sldSz"))
        self.w, self.h = int(size.get("cx")), int(size.get("cy"))
        rels = self.rels("ppt/presentation.xml")
        self.slides = [rels[el.get(q("r:id"))] for el in pres.iter(q("p:sldId"))]
        self.default_size = self._size_in(pres.find(q("p:defaultTextStyle")), 1) or 18.0

    def xml(self, name: str):
        if name not in self.cache:
            data = self.zip.read(name)
            if len(data) > 8_000_000:
                raise ValueError("part too large")
            self.cache[name] = etree.fromstring(data, PARSER)
        return self.cache[name]

    def rels(self, part: str) -> dict[str, str]:
        folder, _, base = part.rpartition("/")
        name = f"{folder}/_rels/{base}.rels"
        if name not in self.names:
            return {}
        out = {}
        for rel in self.xml(name).iter(REL):
            if rel.get("TargetMode") == "External":
                continue
            target = rel.get("Target")
            out[rel.get("Id")] = (target.lstrip("/") if target.startswith("/") else _join(folder, target))
        return out

    def rel_of_type(self, part: str, kind: str) -> str | None:
        folder, _, base = part.rpartition("/")
        name = f"{folder}/_rels/{base}.rels"
        if name not in self.names:
            return None
        for rel in self.xml(name).iter(REL):
            if rel.get("Type", "").endswith("/" + kind):
                return _join(folder, rel.get("Target"))
        return None

    @staticmethod
    def _size_in(style, level: int) -> float | None:
        if style is None:
            return None
        lvl = style.find(q(f"a:lvl{level}pPr"))
        if lvl is not None:
            d = lvl.find(q("a:defRPr"))
            if d is not None and d.get("sz"):
                return int(d.get("sz")) / 100
        return None


def _join(folder: str, target: str) -> str:
    parts = folder.split("/") if folder else []
    for piece in target.split("/"):
        if piece == "..":
            parts = parts[:-1]
        elif piece and piece != ".":
            parts.append(piece)
    return "/".join(parts)


def _ph(sp):
    ph = sp.find(f".//{q('p:nvPr')}/{q('p:ph')}")
    if ph is None:
        return None
    return ph.get("type", "body"), ph.get("idx", "0")


def _find_ph(tree, key):
    """The layout's (or master's) placeholder a slide's placeholder inherits from."""
    kind, idx = key
    by_idx = by_type = None
    for sp in tree.iter(q("p:sp")):
        other = _ph(sp)
        if other is None:
            continue
        if idx != "0" and other[1] == idx:
            by_idx = by_idx if by_idx is not None else sp
        family = lambda k: "title" if k in ("title", "ctrTitle") else ("body" if k in ("body", "obj", "subTitle") else k)
        if family(other[0]) == family(kind):
            by_type = by_type if by_type is not None else sp
    return by_idx if by_idx is not None else by_type


def _xfrm(sp):
    x = sp.find(f"./{q('p:spPr')}/{q('a:xfrm')}")
    if x is None:
        x = sp.find(f"./{q('p:grpSpPr')}/{q('a:xfrm')}")
    if x is None:
        x = sp.find(f"./{q('p:xfrm')}")
    if x is None:
        return None
    off, ext = x.find(q("a:off")), x.find(q("a:ext"))
    if off is None or ext is None:
        return None
    return [int(off.get("x", 0)), int(off.get("y", 0)), int(ext.get("cx", 0)), int(ext.get("cy", 0))]


def _hex(fill) -> str | None:
    if fill is None:
        return None
    c = fill.find(q("a:srgbClr"))
    if c is not None:
        return c.get("val", "").upper()
    c = fill.find(q("a:schemeClr"))
    if c is not None:
        return "scheme:" + c.get("val", "")
    return None


def _lum(hexv: str | None) -> float | None:
    if not hexv or len(hexv) != 6:
        return None
    try:
        r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return None
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


class Theme:
    def __init__(self, deck: Deck, master: str):
        self.colors = {}
        name = deck.rel_of_type(master, "theme")
        if name and name in deck.names:
            scheme = deck.xml(name).find(f".//{q('a:clrScheme')}")
            if scheme is not None:
                for child in scheme:
                    tag = etree.QName(child).localname
                    val = child.find(q("a:srgbClr"))
                    sysc = child.find(q("a:sysClr"))
                    self.colors[tag] = val.get("val").upper() if val is not None else (sysc.get("lastClr", "").upper() if sysc is not None else "")
        self.map = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
        mapping = deck.xml(master).find(q("p:clrMap"))
        if mapping is not None:
            self.map = {k: mapping.get(k) for k in ("bg1", "tx1", "bg2", "tx2")}

    def resolve(self, value: str | None) -> str | None:
        if value and value.startswith("scheme:"):
            key = value[7:]
            key = self.map.get(key, key)
            return self.colors.get(key) or None
        return value


def _background(trees, theme: Theme) -> str | None:
    for tree in trees:
        bg = tree.find(f".//{q('p:cSld')}/{q('p:bg')}")
        if bg is None:
            continue
        pr = bg.find(q("p:bgPr"))
        if pr is not None:
            if pr.find(q("a:blipFill")) is not None:
                return "picture"
            solid = pr.find(q("a:solidFill"))
            if solid is not None:
                return theme.resolve(_hex(solid))
            grad = pr.find(q("a:gradFill"))
            if grad is not None:
                stop = grad.find(f".//{q('a:gs')}")
                return theme.resolve(_hex(stop)) if stop is not None else None
        ref = bg.find(q("p:bgRef"))
        if ref is not None:
            return theme.resolve(_hex(ref))
    return None


def _walk(tree, origin=(0, 0, 1.0, 1.0)):
    """Every drawn thing of a shape tree with its place on the slide (groups unfolded)."""
    root = tree.find(f".//{q('p:cSld')}/{q('p:spTree')}")
    if root is None:
        return

    def inner(group, tx):
        for el in group:
            tag = etree.QName(el).localname
            if tag == "AlternateContent":
                choice = el.find(q("mc:Choice"))
                if choice is not None:
                    yield from inner(choice, tx)
                continue
            if tag not in ("sp", "pic", "grpSp", "graphicFrame", "cxnSp"):
                continue
            box = _xfrm(el)
            if box is not None:
                ox, oy, sx, sy = tx
                box = [ox + box[0] * sx, oy + box[1] * sy, box[2] * sx, box[3] * sy]
            if tag == "grpSp":
                x = el.find(f"./{q('p:grpSpPr')}/{q('a:xfrm')}")
                if x is not None and box is not None:
                    ch_off, ch_ext = x.find(q("a:chOff")), x.find(q("a:chExt"))
                    if ch_off is not None and ch_ext is not None and int(ch_ext.get("cx", 0)) and int(ch_ext.get("cy", 0)):
                        gsx, gsy = box[2] / int(ch_ext.get("cx")), box[3] / int(ch_ext.get("cy"))
                        yield from inner(el, (box[0] - int(ch_off.get("x", 0)) * gsx, box[1] - int(ch_off.get("y", 0)) * gsy, gsx, gsy))
                        continue
                yield from inner(el, tx)
                continue
            yield el, tag, box

    yield from inner(root, origin)


def _union(boxes, w, h, cells=64) -> float:
    """Share of the slide covered by these boxes (on a grid: overlaps counted once)."""
    grid = [[False] * cells for _ in range(cells)]
    for x, y, bw, bh in boxes:
        x0, y0 = max(0, int(x / w * cells)), max(0, int(y / h * cells))
        x1, y1 = min(cells, int((x + bw) / w * cells + 0.999)), min(cells, int((y + bh) / h * cells + 0.999))
        for i in range(y0, y1):
            row = grid[i]
            for j in range(x0, x1):
                row[j] = True
    return sum(map(sum, grid)) / cells / cells


def _font_size(run, para, sp, inherited) -> float | None:
    rpr = run.find(q("a:rPr"))
    if rpr is not None and rpr.get("sz"):
        return int(rpr.get("sz")) / 100
    ppr = para.find(q("a:pPr"))
    level = int(ppr.get("lvl", 0)) + 1 if ppr is not None else 1
    if ppr is not None:
        d = ppr.find(q("a:defRPr"))
        if d is not None and d.get("sz"):
            return int(d.get("sz")) / 100
    for style in inherited:
        size = Deck._size_in(style, level)
        if size:
            return size
    return None


def _scale(sp) -> float:
    """PowerPoint's own shrinking of text that overflows (normAutofit fontScale)."""
    fit = sp.find(f".//{q('a:bodyPr')}/{q('a:normAutofit')}")
    if fit is not None and fit.get("fontScale"):
        return int(fit.get("fontScale")) / 100000
    return 1.0


def measure_slide(deck: Deck, part: str) -> dict:
    slide = deck.xml(part)
    layout = deck.rel_of_type(part, "slideLayout")
    master = deck.rel_of_type(layout, "slideMaster") if layout else None
    lt = deck.xml(layout) if layout and layout in deck.names else None
    ms = deck.xml(master) if master and master in deck.names else None
    theme = Theme(deck, master) if ms is not None else None
    styles = ms.find(q("p:txStyles")) if ms is not None else None

    trees = [slide]
    if slide.find(f".//{q('p:cSld')}").getparent().get("showMasterSp", "1") != "0" and lt is not None:
        trees.append(lt)
        if lt.get("showMasterSp", "1") != "0" and ms is not None:
            trees.append(ms)
    bg = _background([t for t in (slide, lt, ms) if t is not None], theme) if theme else None

    W, H = deck.w, deck.h
    texts, pics, inks, sizes, fonts, fills, kinds = [], [], [], [], Counter(), Counter(), Counter()
    words = paras = shadows = gradients = charts = tables = bleed = 0
    lefts, tops, rights = [], [], []
    title_size = None
    for k, tree in enumerate(trees):
        own = k == 0
        for el, tag, box in _walk(tree):
            ph = _ph(el) if tag == "sp" else None
            if not own and ph is not None:
                continue  # a layout's placeholder only shows through the slide's own
            if box is None and ph is not None and own:
                src = _find_ph(lt, ph) if lt is not None else None
                if src is None and ms is not None:
                    src = _find_ph(ms, ph)
                box = _xfrm(src) if src is not None else None
                if box is None and ms is not None and lt is not None and src is not None:
                    up = _find_ph(ms, ph)
                    box = _xfrm(up) if up is not None else None
            if box is None or box[2] <= 0 or box[3] <= 0:
                continue
            x, y, bw, bh = box
            if x >= W or y >= H or x + bw <= 0 or y + bh <= 0:
                continue  # off the slide (parked out of sight, or waiting for a Morph)
            x0, y0 = max(0, x), max(0, y)
            clip = [x0, y0, min(W, x + bw) - x0, min(H, y + bh) - y0]
            area = clip[2] * clip[3] / W / H
            if tag == "pic" or el.find(f".//{q('a:blipFill')}") is not None:
                pics.append(clip)
                if area > 0.85:
                    bleed += 1
                continue
            if tag == "graphicFrame":
                uri = el.find(f".//{q('a:graphicData')}")
                uri = uri.get("uri", "") if uri is not None else ""
                charts += "chart" in uri
                tables += "table" in uri
                inks.append(clip)
                continue
            geom = el.find(f".//{q('a:prstGeom')}")
            kinds[geom.get("prst") if geom is not None else ("custom" if el.find(f".//{q('a:custGeom')}") is not None else tag)] += 1
            if el.find(f".//{q('a:effectLst')}/{q('a:outerShdw')}") is not None:
                shadows += 1
            sppr = el.find(q("p:spPr"))
            if sppr is not None:
                if sppr.find(q("a:gradFill")) is not None:
                    gradients += 1
                solid = sppr.find(q("a:solidFill"))
                if solid is not None and theme is not None:
                    colour = theme.resolve(_hex(solid))
                    if colour:
                        fills[colour] += 1
            body = el.find(q("p:txBody"))
            content = "".join(t.text or "" for t in body.iter(q("a:t"))) if body is not None else ""
            if content.strip() and own:
                inherited = []
                lst = body.find(q("a:lstStyle"))
                if lst is not None:
                    inherited.append(lst)
                if ph is not None:
                    for tree2 in (lt, ms):
                        if tree2 is None:
                            continue
                        src = _find_ph(tree2, ph)
                        if src is not None:
                            st = src.find(f".//{q('a:lstStyle')}")
                            if st is not None:
                                inherited.append(st)
                    if styles is not None:
                        family = "titleStyle" if ph[0] in ("title", "ctrTitle") else ("bodyStyle" if ph[0] in ("body", "obj", "subTitle") else "otherStyle")
                        inherited.append(styles.find(q(f"p:{family}")))
                elif styles is not None:
                    inherited.append(styles.find(q("p:otherStyle")))
                scale = _scale(el)
                biggest = 0.0
                for para in body.iter(q("a:p")):
                    line = "".join(t.text or "" for t in para.iter(q("a:t")))
                    if not line.strip():
                        continue
                    paras += 1
                    for run in para.iter(q("a:r")):
                        t = run.find(q("a:t"))
                        if t is None or not (t.text or "").strip():
                            continue
                        size = (_font_size(run, para, el, inherited) or deck.default_size) * scale
                        sizes.append((size, len(t.text.strip())))
                        biggest = max(biggest, size)
                        latin = run.find(f"./{q('a:rPr')}/{q('a:latin')}")
                        if latin is not None and latin.get("typeface"):
                            fonts[latin.get("typeface")] += len(t.text)
                    words += len(WORD.findall(line))
                if ph is not None and ph[0] in ("title", "ctrTitle"):
                    title_size = max(title_size or 0, biggest)
                texts.append(clip)
                lefts.append(clip[0] / W)
                tops.append(clip[1] / H)
                rights.append(1 - (clip[0] + clip[2]) / W)
            elif area < 0.9:
                inks.append(clip)
    sizes.sort(key=lambda s: -s[0])
    chars = sum(c for _, c in sizes)
    body = []  # the size most of the reading is done at: every character counts once
    for size, count in sizes:
        if size < sizes[0][0] * 0.8:
            body += [size] * count
    timing = slide.find(q("p:timing"))
    anims = []
    if timing is not None:
        for ctn in timing.iter(q("p:cTn")):
            if ctn.get("presetClass"):
                durs = [int(d) for d in (c.get("dur") for c in ctn.iter(q("p:cTn"))) if d and d.isdigit()]
                cond = ctn.find(f"./{q('p:stCondLst')}/{q('p:cond')}")
                delay = cond.get("delay") if cond is not None else "0"
                anims.append({"cls": ctn.get("presetClass"), "id": int(ctn.get("presetID", 0)), "sub": int(ctn.get("presetSubtype", 0) or 0),
                              "node": ctn.get("nodeType", ""), "dur": max(durs) if durs else 0, "delay": int(delay) if delay and delay.lstrip("-").isdigit() else 0})
        paragraphs = len(timing.findall(f".//{q('p:bldP')}"))
    else:
        paragraphs = 0
    transition = _transition(slide)
    return {
        "words": words, "paras": paras, "n_text": len(texts), "n_pics": len(pics), "n_ink": len(inks),
        "pic_area": round(_union(pics, W, H), 3), "big_pic": round(max((b[2] * b[3] / W / H for b in pics), default=0), 3), "bleed": bleed,
        "text_area": round(_union(texts, W, H), 3), "ink_area": round(_union(texts + inks + pics, W, H), 3),
        "title_size": title_size, "max_size": sizes[0][0] if sizes else None,
        "body_size": round(sorted(body)[len(body) // 2], 1) if body else None,
        "n_sizes": len({round(s) for s, _ in sizes}), "chars": chars,
        "left": round(min(lefts), 3) if lefts else None, "top": round(min(tops), 3) if tops else None,
        "right": round(min(rights), 3) if rights else None,
        "edges": len({round(v * 50) for v in lefts}),
        "fonts": dict(fonts.most_common(3)), "fills": len(fills), "bg": bg, "bg_lum": None if bg in (None, "picture") else _lum(bg),
        "kinds": dict(kinds), "shadows": shadows, "gradients": gradients, "charts": charts, "tables": tables,
        "transition": transition, "anims": anims, "bldP": paragraphs,
    }


def _transition(slide) -> dict | None:
    for child in slide:
        tag = etree.QName(child).localname
        if tag == "AlternateContent":
            choice = child.find(q("mc:Choice"))
            tr = choice.find(q("p:transition")) if choice is not None else None
        elif tag == "transition":
            tr = child
        else:
            continue
        if tr is None:
            return None
        effect = next((etree.QName(c).localname for c in tr if etree.QName(c).localname not in ("sndAc", "extLst")), "none")
        dur = tr.get(q("p14:dur")) or tr.get("dur")
        return {"kind": effect, "dur": int(dur) if dur and dur.isdigit() else SPEED.get(tr.get("spd", "fast"), 500),
                "auto": tr.get("advTm") is not None}
    return None


def measure(path: str) -> dict:
    deck = Deck(path)
    slides = []
    for part in deck.slides:
        try:
            slides.append(measure_slide(deck, part))
        except (KeyError, ValueError, etree.XMLSyntaxError, AttributeError, TypeError):
            continue
    return {"file": path.rsplit("/", 1)[-1], "ratio": round(deck.w / deck.h, 3), "width_in": round(deck.w / 914400, 2), "slides": slides}


if __name__ == "__main__":
    out = open(sys.argv[1], "w")
    for path in sys.argv[2:]:
        try:
            row = measure(path)
        except Exception as e:  # noqa: BLE001 - one broken template must not stop the study
            print("skip", path.rsplit("/", 1)[-1], type(e).__name__, e, file=sys.stderr)
            continue
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
    out.close()
