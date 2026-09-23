"""Learned structure correction: better than the rules alone, safe on bullets, fast."""
import time

import pytest

from app.doc import ml
from app.doc.detect import detect
from app.doc.extract import from_text

pytestmark = pytest.mark.skipif(ml.model() is None, reason="structure model not trained (ml/train.py)")


def _levels(res):
    return {b["text"]: b.get("level") for b in res["blocks"] if b["type"] == "heading"}


def test_unformatted_numbered_sections_become_headings():
    text = "\n".join([
        "INTRODUCTION", "Ce rapport présente notre stage effectué au sein de la structure pendant trois mois, avec de nombreuses activités.",
        "CHAPITRE I : PRÉSENTATION", "Cette structure a été créée en 2005 et compte aujourd'hui plus de cent employés répartis dans trois services.",
        "1 Historique", "L'entreprise a connu plusieurs phases de développement depuis sa création jusqu'à aujourd'hui dans la ville.",
        "2 Organisation", "Elle est organisée en directions, services et cellules, sous l'autorité d'un directeur général nommé.",
    ])
    lv = _levels(detect(from_text(text)))
    assert lv.get("1 Historique") == 2 and lv.get("2 Organisation") == 2


def test_bullets_are_never_promoted():
    text = "\n".join([
        "I. Tâches", "Nous avons réalisé les tâches suivantes au cours de notre stage dans le service archives :",
        "• Scanner les dossiers actifs", "• Sauvegarder les fichiers sur le serveur",
        "Pour plus d'informations, consulter le responsable du service qui centralise toutes les demandes des usagers.",
    ])
    blocks = detect(from_text(text))["blocks"]
    assert all(b["type"] == "list" for b in blocks if "fichiers" in b.get("text", "") or "Scanner" in b.get("text", ""))


def test_fast_enough():
    text = "\n".join(["Titre de section", "Un paragraphe de texte assez long pour ressembler à un vrai paragraphe de rapport de stage."] * 100)
    raws = from_text(text)
    t = time.time()
    detect(raws)
    assert time.time() - t < 1.0
