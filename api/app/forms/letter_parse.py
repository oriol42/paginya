"""A letter typed freely (pasted, Word, PDF) read back into the fields of /lettre, which lays it out the
Cameroonian way: sender, place and date, recipient, s/c, subject, attachments, body, signature.

Only what is really in the text is filled; the user checks everything in the letter form.
"""
from __future__ import annotations

import re

SUBJECT = re.compile(r"^\s*obj(?:et)?\s*[:.]\s*(.+)$", re.I)
ATTACH = re.compile(r"^\s*(?:p\.?\s?j\.?|pi[èe]ces?\s+jointes?)\s*[:.]\s*(.+)$", re.I)
PLACE_DATE = re.compile(r"^\s*([A-ZÀ-Ýa-zà-ÿ'’\- ]{2,40}?)\s*,?\s+le\s+(\d{1,2}(?:er)?\s+\S+\s+\d{4}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})\s*$", re.I)
SALUTATION = re.compile(r"^\s*(Monsieur|Madame|Mesdames|Messieurs|Honorable|Excellence|Cher|Chère)\b.{0,90},\s*$")
CLOSING = re.compile(r"(agr[ée]er|l['’]expression|salutations|consid[ée]ration|sentiments|respectueux|mes respects)", re.I)
TO = re.compile(r"^\s*(?:[àaÀA]\s+l['’]attention\s+d[eu]|[àaÀA](?=\s*$|\s+[A-ZÀ-Ý]))\s*")
VIA = re.compile(r"^\s*s\s*/\s*c\s*(?:de|du|des)?\s*(.+)$", re.I)
PHONE = re.compile(r"(?:t[ée]l\.?\s*:?\s*)?((?:\+?237\s?)?6\d(?:[\s.]?\d){7})", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SIGN_LABEL = re.compile(r"^\s*(l['’]int[ée]ress[ée]e?|le demandeur|la demanderesse|le requ[ée]rant|la requ[ée]rante|signature)\s*$", re.I)


def letter_signals(text: str) -> bool:
    """A letter: a subject line, a salutation ("Monsieur le …,") and a closing formula."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or len(lines) > 80:
        return False
    has_subject = any(SUBJECT.match(ln) for ln in lines[:25])
    has_salutation = any(SALUTATION.match(ln) for ln in lines[:30])
    has_closing = any(CLOSING.search(ln) and len(ln) > 30 for ln in lines[-12:])
    return has_subject and has_salutation and has_closing


def _civility(line: str) -> tuple[str, str]:
    m = re.match(r"^(Monsieur|Madame)\s+(.+)$", line.strip())
    return (m.group(1), m.group(2).strip()) if m else ("Monsieur", line.strip())


def parse_letter(text: str) -> dict:
    """The fields of /lettre found in the text (see components/forms/LetterForm.tsx: Letter)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").splitlines() if ln.strip()]
    i_subj = next((i for i, ln in enumerate(lines) if SUBJECT.match(ln)), len(lines))
    i_sal = next((i for i, ln in enumerate(lines) if i > i_subj and SALUTATION.match(ln)), None)
    i_date = next((i for i, ln in enumerate(lines[:i_subj]) if PLACE_DATE.match(ln)), None)

    out: dict = {"sender": {"name": "", "extra": "", "address": "", "phone": "", "email": ""},
                 "recipient": {"civility": "Monsieur", "title": "", "org": "", "city": ""},
                 "place": "", "date": "", "via": "", "subject": "", "attachments": [], "body": "", "bodyEdited": True, "type": "libre"}

    head = lines[:i_subj]
    # recipient: from the "À" line (or the first "Monsieur le…" line after the date) to the subject
    i_to = next((i for i, ln in enumerate(head) if TO.match(ln) and (len(ln) < 4 or re.search(r"monsieur|madame", ln, re.I))), None)
    if i_to is None:
        i_to = next((i for i, ln in enumerate(head) if re.match(r"^(Monsieur|Madame)\b", ln) and (i_date is None or i > i_date)), None)
    sender_end = min(x for x in (i_date, i_to, len(head)) if x is not None)
    for ln in head[:sender_end]:
        s = out["sender"]
        if not s["name"]:
            s["name"] = ln
        elif EMAIL.search(ln):
            s["email"] = EMAIL.search(ln).group(0)
        elif PHONE.search(ln) and len(re.sub(r"\D", "", ln)) >= 8 and len(ln) < 40:
            s["phone"] = PHONE.search(ln).group(1)
        elif re.search(r"\bB\.?P\.?\b|bo[iî]te postale|quartier|rue\b", ln, re.I) and not s["address"]:
            s["address"] = ln
        else:
            s["extra"] = f"{s['extra']} · {ln}".strip(" ·")[:120]
    if i_date is not None:
        m = PLACE_DATE.match(head[i_date])
        out["place"], out["date"] = m.group(1).strip().title() if m.group(1).isupper() else m.group(1).strip(), m.group(2).strip()

    if i_to is not None:
        rec = [ln for ln in head[i_to:] if not (i_date is not None and ln == head[i_date])]
        first = TO.sub("", rec[0]).strip()
        rec = ([first] if first else []) + rec[1:]
        rest = []
        for ln in rec:
            via = VIA.match(ln)
            if via:
                out["via"] = via.group(1).strip()
            elif not out["recipient"]["title"]:
                out["recipient"]["civility"], out["recipient"]["title"] = _civility(ln)
            else:
                rest.append(ln)
        if rest and len(rest[-1].split()) <= 2 and not re.match(r"^(de|du|des|d['’])\s|^(universit|facult|[ée]cole|institut|minist)", rest[-1], re.I):
            out["recipient"]["city"] = rest.pop().title() if rest[-1].isupper() else rest.pop()
        out["recipient"]["org"] = " ".join(rest)

    m = SUBJECT.match(lines[i_subj]) if i_subj < len(lines) else None
    if m:
        out["subject"] = m.group(1).strip().rstrip(".")
        if out["subject"].isupper():
            out["subject"] = out["subject"][:1] + out["subject"][1:].lower()
        out["subject"] = out["subject"][:1].upper() + out["subject"][1:]
        low = out["subject"].lower()
        out["type"] = next((t for t, w in (("emploi", "emploi"), ("stage", "stage"), ("conge", "congé"), ("absence", "absence"), ("explication", "explication")) if w in low), "libre")
    for ln in lines[i_subj + 1:(i_sal if i_sal is not None else i_subj + 3)]:
        a = ATTACH.match(ln)
        if a:
            out["attachments"] = [x.strip(" .") for x in re.split(r"[;,]", a.group(1)) if x.strip(" .")]

    # body: the paragraphs after the salutation, up to and including the closing formula
    if i_sal is not None:
        sal = lines[i_sal]
        start = next((k for k, p in enumerate(paras) if p.splitlines()[0].strip() == sal), None)
        body: list[str] = []
        for p in paras[(start + 1) if start is not None else 0:]:
            flat = " ".join(x.strip() for x in p.splitlines())
            if SIGN_LABEL.match(p.splitlines()[0]) or flat == out["sender"]["name"]:
                break
            body.append(flat)
            if CLOSING.search(flat) and re.search(r"agr[ée]er|veuillez|recevoir", flat, re.I):
                break
        out["body"] = "\n\n".join(body)
    return out
