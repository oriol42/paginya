"""Whitelist sanitizer for cover SVGs sent by the browser.

The browser builds the cover SVG (it measures and wraps text with the real
fonts); the server only rasterizes it. We therefore strip anything that is not
plain vector drawing: scripts, event handlers, external references, foreign
objects. Only data: images (the user's logo) are kept.
"""
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

ALLOWED_TAGS = {
    "svg", "g", "defs", "rect", "circle", "ellipse", "line", "polyline",
    "polygon", "path", "text", "tspan", "image", "linearGradient",
    "radialGradient", "stop", "clipPath", "title",
}
ALLOWED_ATTRS = {
    "id", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
    "width", "height", "viewBox", "points", "d", "fill", "fill-opacity",
    "stroke", "stroke-width", "stroke-opacity", "stroke-dasharray",
    "stroke-linecap", "stroke-linejoin", "opacity", "transform",
    "font-family", "font-size", "font-weight", "font-style",
    "letter-spacing", "text-anchor", "dominant-baseline", "offset",
    "stop-color", "stop-opacity", "gradientUnits", "gradientTransform",
    "clip-path", "preserveAspectRatio", "href", "xml:space",
    "clipPathUnits", "fx", "fy",
}
MAX_SVG_BYTES = 3_000_000  # logos are embedded as data: URIs


class UnsafeSvg(ValueError):
    pass


def _local(name: str) -> str:
    return name.split("}", 1)[1] if name.startswith("{") else name


def sanitize_svg(svg: str) -> str:
    if len(svg.encode()) > MAX_SVG_BYTES:
        raise UnsafeSvg("SVG trop volumineux")
    if "<!DOCTYPE" in svg or "<!ENTITY" in svg:
        raise UnsafeSvg("DOCTYPE/ENTITY interdits")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise UnsafeSvg(f"SVG invalide : {exc}") from exc
    if _local(root.tag) != "svg":
        raise UnsafeSvg("La racine doit être <svg>")

    def clean(el: ET.Element) -> None:
        for child in list(el):
            if _local(child.tag) not in ALLOWED_TAGS:
                el.remove(child)
                continue
            clean(child)
        for attr in list(el.attrib):
            name = _local(attr)
            if attr == f"{{{XLINK_NS}}}href":
                name = "href"
            value = el.attrib[attr]
            if name not in ALLOWED_ATTRS:
                del el.attrib[attr]
            elif name == "href" and not value.startswith("data:image/"):
                del el.attrib[attr]
            elif "url(" in value and not value.replace(" ", "").startswith("url(#"):
                del el.attrib[attr]

    clean(root)
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    return ET.tostring(root, encoding="unicode")
