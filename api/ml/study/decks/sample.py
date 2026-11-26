"""A realistic defence deck built by Paginya's engine, with real photos fetched as the server does.

Usage: python sample.py <theme> <out.pptx> [--reuse]
--reuse takes the photos found the first time (images/deck.json next to out.pptx): two versions of the engine
are then compared on the same pictures.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # api/
from app.doc import art  # noqa: E402
from app.doc.slides import build_pptx, title_info  # noqa: E402


def item(head: str, text: str) -> dict:
    return {"head": head, "text": text}


PARTS = ["Contexte", "Analyse", "Solution", "Résultats"]
SLIDES = [
    {"type": "section", "title": "Contexte et problématique", "part": "Contexte", "photo": "warehouse workers"},
    {"type": "liste", "title": "Une gestion des stocks encore manuelle", "part": "Contexte", "highlight": "manuelle", "photo": "paper notebook writing",
     "items": [item("Registres papier", "Les entrées et sorties sont notées à la main"), item("Erreurs fréquentes", "Écarts constatés lors des inventaires"),
               item("Lenteur", "Plusieurs jours pour un état des stocks")], "takeaway": "Le service a besoin d'un outil fiable"},
    {"type": "encadre", "title": "La question de départ", "part": "Contexte", "label": "Problématique",
     "text": "Comment fiabiliser le suivi des stocks de la CAMTEL sans alourdir le travail des magasiniers ?"},
    {"type": "section", "title": "Analyse du besoin", "part": "Analyse", "photo": "people meeting whiteboard"},
    {"type": "grille", "title": "Les objectifs du projet", "part": "Analyse",
     "items": [item("Centraliser", "Une base unique pour tous les magasins"), item("Alerter", "Seuils minimaux et ruptures"),
               item("Tracer", "Historique de chaque mouvement"), item("Restituer", "Tableaux de bord mensuels")]},
    {"type": "etapes", "title": "La démarche suivie", "part": "Analyse",
     "items": [item("Observation", "Deux semaines au magasin central"), item("Modélisation", "Merise : MCD puis MLD"),
               item("Développement", "Laravel et MySQL"), item("Tests", "Avec trois magasiniers")]},
    {"type": "section", "title": "La solution réalisée", "part": "Solution", "photo": "tablet warehouse inventory"},
    {"type": "panneau", "title": "Une application pensée pour le magasin", "part": "Solution", "key": "Tout se fait depuis une tablette",
     "items": [item("Saisie rapide", "Un mouvement enregistré en trois touches"), item("Alertes", "Le magasinier est prévenu avant la rupture"),
               item("Tableau de bord", "L'état des stocks en direct")]},
    {"type": "chronologie", "title": "Le déroulement du stage", "part": "Solution",
     "items": [item("Juillet", "Intégration et observation"), item("Août", "Analyse et conception"), item("Septembre", "Développement et tests")]},
    {"type": "comparaison", "title": "Avant et après l'application", "part": "Solution",
     "left": {"title": "Avant", "points": ["Registres papier", "Inventaire en 3 jours", "Ruptures découvertes trop tard"]},
     "right": {"title": "Après", "points": ["Saisie sur tablette", "État des stocks en direct", "Alerte dès le seuil atteint"]}},
    {"type": "section", "title": "Résultats et bilan", "part": "Résultats", "photo": "team office success"},
    {"type": "chiffres", "title": "Les résultats après un mois", "part": "Résultats",
     "stats": [{"value": "3", "label": "magasins équipés"}, {"value": "12", "label": "agents formés"}, {"value": "1", "label": "jour pour l'inventaire"}]},
    {"type": "graphique", "title": "Répartition des mouvements", "part": "Résultats", "chart": "barres",
     "series": [{"label": "Entrées", "value": 40}, {"label": "Sorties", "value": 45}, {"label": "Retours", "value": 15}], "key": "Les sorties dominent"},
    {"type": "grand", "title": "Ce que je retiens", "part": "Résultats", "value": "Fiabilité", "text": "Un outil simple, adopté par les magasiniers",
     "photo": "team meeting office"},
]
COVER = {"doc_label": "Rapport de stage", "header_fr": ["RÉPUBLIQUE DU CAMEROUN", "UNIVERSITÉ DE YAOUNDÉ I"], "specialty": "Licence en génie logiciel",
         "authors": [{"name": "KAMGA Paul"}], "supervisors": ["Dr NKE Marie"], "year": "2025-2026"}
TITLE = "Conception d'une application de gestion des stocks"


def build(theme: str, out: Path, reuse: bool = False) -> Path:
    images = out.parent / "images"
    images.mkdir(parents=True, exist_ok=True)
    saved = images / "deck.json"
    if reuse and saved.is_file():
        deck = json.loads(saved.read_text())
    else:
        deck = {"slides": json.loads(json.dumps(SLIDES)), "parts": PARTS, "notes": "Bonjour", "thanks": "Merci de votre attention", "photo": "office team laptop"}
        start = time.time()
        art.illustrate(deck, images)
        print("photos en", round(time.time() - start), "s")
        saved.write_text(json.dumps(deck, ensure_ascii=False))
    info = title_info({"blocks": [], "meta": {"title": TITLE, "cover": COVER}}, images)
    out.write_bytes(build_pptx(deck, info, theme, images))
    return out


if __name__ == "__main__":
    print("ok", build(sys.argv[1], Path(sys.argv[2]), "--reuse" in sys.argv))
