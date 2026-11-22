"""Synthetic messy documents read back from a PDF, the way most customers send them.

The same documents as ml/synth.py are written as Word files, printed to PDF by LibreOffice (the one Paginya uses),
then read by the production PDF extractor (app.doc.extract.from_pdf). A PDF loses the paragraph marks: a title
or a paragraph can come back split, merged or with page numbers around. Each paragraph read is matched back to
the element it came from; a document that cannot be matched cleanly is left out rather than mislabelled.

    PROPRE_LO_PIPE=synth_lo python -m ml.synth_pdf 50     # how many documents survive, and how fast
"""
from __future__ import annotations

import random
import re
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

from app.doc import office
from app.doc.extract import Raw, from_pdf
from ml.synth import CAPTION, H1, H4, LIST, PARA, habit, messy_lines, truth_doc, write_docx


def _key(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", t)


def align(raws: list[Raw], lines: list[tuple]) -> list[int] | None:
    """The label of each paragraph read from the PDF, from the element it starts in (None: too unsure)."""
    keys = [_key(t) for _, t in lines]
    labels, j, missed = [], 0, 0
    for r in raws:
        k = _key(r.text)
        if not k:
            labels.append(PARA)
            continue
        probe = k[:40]
        found = None
        for jj in range(j, min(len(keys), j + 6)):  # the next few elements: the PDF keeps the order
            if keys[jj].startswith(probe) or (len(probe) >= 12 and probe in keys[jj]):
                found = jj
                break
        if found is None:
            missed += 1
            labels.append(PARA)  # a page number, a header…: plain text
            continue
        el = lines[found][0]
        starts = keys[found].startswith(probe)
        # a heading read in two pieces: only its first piece is the title; the rest of a split paragraph stays text
        labels.append(el.label if starts else (PARA if el.label in range(H1, H4 + 1) or el.label == CAPTION else el.label))
        j = found if not starts or len(k) < len(keys[found]) - 2 else found + 1
    if missed > max(2, len(raws) // 20):
        return None
    return labels


def samples(seeds: range, workdir: Path | None = None) -> list[tuple[list[Raw], list[int]]]:
    """[(raws, labels)] for the seeds whose PDF could be matched back."""
    out = []
    tmp = Path(workdir or tempfile.mkdtemp())
    tmp.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        rng = random.Random(seed)
        els = truth_doc(rng)
        h = habit(rng)
        if h.mode == "text":
            h.mode = "manual"  # a PDF is always printed from a document with some formatting
        lines = messy_lines(els, h, rng)
        src, pdf = tmp / f"s{seed}.docx", tmp / f"s{seed}.pdf"
        write_docx(lines, h, rng, src)
        try:
            office.finalize(src, None, pdf)
            raws = [r for r in from_pdf(pdf, tmp / "img") if r.text.strip()]
        except Exception:  # noqa: BLE001 - a document LibreOffice cannot print is simply skipped
            continue
        finally:
            src.unlink(missing_ok=True)
        pdf.unlink(missing_ok=True)
        labels = align(raws, lines)
        if labels is not None:
            out.append((raws, labels))
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    t0 = time.time()
    got = samples(range(200_000, 200_000 + n))
    paras = sum(len(r) for r, _ in got)
    print(f"{len(got)}/{n} documents gardés, {paras} paragraphes, {time.time() - t0:.0f} s")
    from collections import Counter

    print(Counter(lab for _, labs in got for lab in labs))
