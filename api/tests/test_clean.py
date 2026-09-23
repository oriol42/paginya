"""Automatic clean-up of what students often get wrong (case, cut paragraphs, lists, typography)."""
from app.doc.clean import clean, fix_caps, sentence_case, typo_fr, unmarked_lists, vocabulary
from app.doc.detect import detect
from app.doc.extract import from_text


def texts(res, kind):
    return [b["text"] for b in res["blocks"] if b["type"] == kind]


def test_capitals_at_sentence_starts_but_not_after_abbreviations():
    s, n = fix_caps("la structure compte 12 agents. elle a été créée en 2005, cf. annexe 2. Le taux est de 3.5 %.")
    assert s == "La structure compte 12 agents. Elle a été créée en 2005, cf. annexe 2. Le taux est de 3.5 %."
    assert n == 2


def test_all_caps_title_keeps_acronyms_places_and_gets_its_accents_back():
    acr, proper = vocabulary(["Le partenariat avec MTN et la CNPS a été signé à Garoua par Monsieur Fotso."])
    assert sentence_case("PRESENTATION GENERALE DE LA CNPS A DOUALA", acr, proper) == "Présentation générale de la CNPS à Douala"


def test_paragraph_cut_by_enter_is_glued_back():
    items = [{"type": "paragraph", "text": "ADVANS Cameroun est une institution de"}, {"type": "paragraph", "text": "microfinance créée en 2007 à Douala."}]
    unmarked_lists(items)
    assert clean(items)["merged"] == 1 and items[0]["text"] == "ADVANS Cameroun est une institution de microfinance créée en 2007 à Douala."


def test_enumeration_without_bullets_becomes_a_list_with_french_punctuation():
    text = "\n".join([
        "I. Missions",
        "Les missions principales de l'institution sont les suivantes :",
        "Collecter l'épargne des ménages",
        "Octroyer des crédits aux PME",
        "Accompagner les clients",
        "Ces missions sont exercées dans les dix agences du pays, sous la supervision de la direction générale.",
    ])
    res = detect(from_text(text))
    assert texts(res, "list") == ["collecter l'épargne des ménages ;", "octroyer des crédits aux PME ;", "accompagner les clients."]
    assert any("énumération" in c for c in res["meta"]["changes"])


def test_all_caps_paragraph_and_section_title_are_rewritten():
    text = "\n".join([
        "CHAPITRE I : PRÉSENTATION",
        "1. LES ACTIVITES DE LA STRUCTURE",
        "LA STRUCTURE OFFRE DES SERVICES DE TRANSFERT D'ARGENT ET DE CREDIT A SES CLIENTS DEPUIS 2005.",
        "Elle travaille avec MTN et Orange pour les paiements mobiles à Douala et dans tout le Cameroun.",
    ])
    res = detect(from_text(text))
    assert "1. Les activités de la structure" in texts(res, "heading")
    assert "CHAPITRE I : PRÉSENTATION" in texts(res, "heading")  # chapters stay in capitals (norm)
    assert texts(res, "paragraph")[0].startswith("La structure offre des services de transfert")


def test_french_typography():
    t = typo_fr('Le taux , selon le rapport , est de 10 % ; il faut agir ! Voici les points : "qualité" et ( délais ) à 10:30')
    assert t == 'Le taux, selon le rapport, est de 10 % ; il faut agir ! Voici les points : « qualité » et (délais) à 10:30'.replace("10 %", "10 %")
