# Spike: DOCX with bilingual cover, roman prelim numbering, TOC field, captions (SEQ), arabic body numbering
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def field(par, instr):
    r = par.add_run()
    for t, extra in (("begin", None), ("instr", instr), ("separate", None), ("end", None)):
        if t == "instr":
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = instr
        else:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), t)
        r._r.append(el)

def page_numbering(section, fmt, start=1):
    pg = OxmlElement("w:pgNumType"); pg.set(qn("w:fmt"), fmt); pg.set(qn("w:start"), str(start))
    section._sectPr.append(pg)
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    field(p, "PAGE")

d = Document()
st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.paragraph_format.line_spacing = 1.5
for s in ("Heading 1", "Heading 2"):
    d.styles[s].font.name = "Times New Roman"
sec = d.sections[0]
for m in ("left_margin",): setattr(sec, m, Cm(3))
sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.5)

# cover: 2-col bilingual table
t = d.add_table(rows=1, cols=2)
fr = ["RÉPUBLIQUE DU CAMEROUN", "Paix – Travail – Patrie", "********", "UNIVERSITÉ DE YAOUNDÉ I", "********", "FACULTÉ DES SCIENCES"]
en = ["REPUBLIC OF CAMEROON", "Peace – Work – Fatherland", "********", "THE UNIVERSITY OF YAOUNDE I", "********", "FACULTY OF SCIENCE"]
for cell, lines in zip(t.rows[0].cells, (fr, en)):
    cell.paragraphs[0].text = lines[0]
    for l in lines[1:]: cell.add_paragraph(l)
    for p in cell.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs: r.bold = True; r.font.size = Pt(10)
p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("\n\nRAPPORT DE STAGE"); r.bold = True; r.font.size = Pt(20)

# prelim section (roman)
s2 = d.add_section(WD_SECTION.NEW_PAGE); page_numbering(s2, "lowerRoman")
d.add_paragraph("SOMMAIRE", style="Title")
d.add_paragraph('[[TOC]]')
d.add_page_break()
d.add_paragraph("LISTE DES TABLEAUX", style="Title")
d.add_paragraph('[[LOT]]')

# body section (arabic from 1)
s3 = d.add_section(WD_SECTION.NEW_PAGE); page_numbering(s3, "decimal", 1)
d.add_heading("INTRODUCTION", level=1)
d.add_paragraph("Texte d'introduction. " * 80)
for i in range(1, 4):
    d.add_page_break()
    d.add_heading(f"CHAPITRE {['I','II','III'][i-1]} : TITRE DU CHAPITRE", level=1)
    d.add_heading(f"{i}.1 Section", level=2)
    d.add_paragraph("Paragraphe. " * 150)
    cap = d.add_paragraph(style="Caption"); cap.add_run("Tableau "); field(cap, "SEQ Tableau \\* ARABIC"); cap.add_run(f" : Données du chapitre {i}")
    tb = d.add_table(rows=2, cols=3); tb.style = "Table Grid"
d.save("spike.docx")
print("docx ok")
