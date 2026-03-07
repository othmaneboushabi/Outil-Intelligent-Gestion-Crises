import spacy
from typing import Dict, List, Optional
from nlp.cleaner import load_spacy_model

# ─── EXTRACTION D'ENTITÉS NER ────────────────────────────

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extrait les entités nommées depuis le texte via SpaCy NER.
    Retourne un dictionnaire avec les entités par type :
    - PER  : personnes
    - ORG  : organisations
    - DATE : dates
    - LOC  : lieux
    - PRODUCT : outils / produits
    """
    model = load_spacy_model()
    doc = model(text)

    entities = {
        "PER"     : [],
        "ORG"     : [],
        "DATE"    : [],
        "LOC"     : [],
        "PRODUCT" : [],
        "MISC"    : []
    }

    for ent in doc.ents:
        label = ent.label_
        value = ent.text.strip()
        if label in entities and value not in entities[label]:
            entities[label].append(value)

    return entities


def detect_probable_responsible(text: str) -> Optional[str]:
    """
    Identifie le responsable probable d'un blocage
    en cherchant les entités de type PER ou ORG dans le texte.
    Retourne la première personne ou organisation détectée.
    """
    entities = extract_entities(text)

    # Priorité : personne > organisation
    if entities["PER"]:
        return entities["PER"][0]
    if entities["ORG"]:
        return entities["ORG"][0]
    return None


def analyze_problem(text: str) -> Dict:
    """
    Analyse complète d'un texte de problème.
    Retourne les entités extraites + le responsable probable.
    """
    entities            = extract_entities(text)
    probable_responsible = detect_probable_responsible(text)

    return {
        "entities"             : entities,
        "probable_responsible" : probable_responsible,
        "summary": {
            "nb_persons"       : len(entities["PER"]),
            "nb_organisations" : len(entities["ORG"]),
            "nb_dates"         : len(entities["DATE"]),
            "nb_locations"     : len(entities["LOC"]),
        }
    }