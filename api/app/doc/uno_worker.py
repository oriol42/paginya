"""LibreOffice finisher, run with the *system* python (the one that ships `uno`).

    python3 uno_worker.py <pipe_name> <profile_dir> <in.docx> <out.docx> <out.pdf> [<layout.json>]

- Reuses a running headless soffice listening on a named pipe (starts it if needed).
- Replaces [[TOC:n]], [[LOT]], [[LOF]] markers with real indexes, updates them
  (twice, so page numbers settle) and exports the final .docx and .pdf.
- With <layout.json>: also writes the real page of every top-level paragraph, as LibreOffice lays the file out.
"""
import json
import os
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def pv(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def connect(pipe, profile):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    url = f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext"
    try:
        return resolver.resolve(url)
    except Exception:
        pass
    subprocess.Popen(
        ["soffice", "--headless", "--invisible", "--norestore", "--nologo", "--nodefault",
         f"-env:UserInstallation={uno.systemPathToFileUrl(profile)}", f"--accept=pipe,name={pipe};urp;"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    for _ in range(120):
        time.sleep(0.25)
        try:
            return resolver.resolve(url)
        except Exception:
            continue
    raise RuntimeError("LibreOffice ne démarre pas")


def insert_index(doc, marker, service, setup):
    search = doc.createSearchDescriptor()
    search.SearchString = marker
    found = doc.findFirst(search)
    if found is None:
        return
    found.setString("")
    index = doc.createInstance(service)
    setup(index)
    doc.getText().insertTextContent(found, index, False)


def layout_of(doc):
    """[[page, text]] for each top-level paragraph, in order; a table is [0, ""]."""
    cursor = doc.getCurrentController().getViewCursor()
    rows = []
    items = doc.getText().createEnumeration()
    while items.hasMoreElements():
        item = items.nextElement()
        if item.supportsService("com.sun.star.text.Paragraph"):
            cursor.gotoRange(item.getStart(), False)
            rows.append([cursor.getPage(), item.getString()[:80]])
        else:
            rows.append([0, ""])
    return rows


def main():
    pipe, profile, src, out_docx, out_pdf = sys.argv[1:6]
    out_layout = sys.argv[6] if len(sys.argv) > 6 else "-"
    ctx = connect(pipe, profile)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(src)), "_blank", 0, (pv("Hidden", True),))
    try:
        def toc(levels):
            def setup(ix):
                ix.Title = ""
                ix.CreateFromOutline = True
                ix.Level = levels
            return setup

        def illus(label):
            def setup(ix):
                ix.Title = ""
                ix.CreateFromLabels = True
                ix.LabelCategory = label
            return setup

        for marker, service, setup in (
            ("[[TOC:2]]", "com.sun.star.text.ContentIndex", toc(2)),
            ("[[TOC:4]]", "com.sun.star.text.ContentIndex", toc(4)),
            ("[[LOT]]", "com.sun.star.text.IllustrationsIndex", illus("Tableau")),
            ("[[LOF]]", "com.sun.star.text.IllustrationsIndex", illus("Figure")),
        ):
            insert_index(doc, marker, service, setup)
        indexes = doc.getDocumentIndexes()
        # Page numbers in the indexes settle after a second pass; without indexes one field refresh is enough.
        for _ in range(2 if indexes.getCount() else 1):
            doc.getTextFields().refresh()
            for i in range(indexes.getCount()):
                indexes.getByIndex(i).update()
        # "-" skips an export: previews only need the PDF, the Word file is made when it is downloaded.
        if out_docx != "-":
            doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(out_docx)), (pv("FilterName", "MS Word 2007 XML"),))
        if out_pdf != "-":
            doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(out_pdf)), (pv("FilterName", "writer_pdf_Export"),))
        if out_layout != "-":
            with open(out_layout, "w", encoding="utf-8") as handle:
                json.dump(layout_of(doc), handle)
    finally:
        doc.close(True)


if __name__ == "__main__":
    main()
