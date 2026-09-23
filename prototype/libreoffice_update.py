import uno, sys, time, subprocess, os
from com.sun.star.beans import PropertyValue
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore",
    "-env:UserInstallation=file:///tmp/lo-profile-mef",
    '--accept=socket,host=127.0.0.1,port=2002;urp;'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(60):
    try:
        local = uno.getComponentContext()
        res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = res.resolve("uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext"); break
    except Exception: time.sleep(0.5)
desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(sys.argv[1])), "_blank", 0, (pv("Hidden", True),))
text = doc.getText()
def replace_with_index(marker, service, setup):
    sd = doc.createSearchDescriptor(); sd.SearchString = marker
    found = doc.findFirst(sd)
    if found is None: print("marker not found", marker); return
    found.setString("")
    ix = doc.createInstance(service); setup(ix)
    text.insertTextContent(found, ix, False)
def toc(ix):
    ix.Level = 2; ix.CreateFromOutline = True; ix.Title = ""
def lot(ix):
    ix.LabelCategory = "Tableau"; ix.CreateFromLabels = True; ix.Title = ""
replace_with_index("[[TOC]]", "com.sun.star.text.ContentIndex", toc)
replace_with_index("[[LOT]]", "com.sun.star.text.IllustrationsIndex", lot)
doc.getTextFields().refresh()
idx = doc.getDocumentIndexes(); n = idx.getCount()
for _ in range(2):
    for i in range(n): idx.getByIndex(i).update()
    doc.getTextFields().refresh()
out = os.path.abspath(sys.argv[1]).rsplit(".", 1)[0]
doc.storeToURL(uno.systemPathToFileUrl(out + "_final.docx"), (pv("FilterName", "MS Word 2007 XML"),))
doc.storeToURL(uno.systemPathToFileUrl(out + ".pdf"), (pv("FilterName", "writer_pdf_Export"),))
print("indexes:", n)
doc.close(True); proc.terminate()
