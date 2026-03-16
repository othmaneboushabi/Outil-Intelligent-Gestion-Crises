import re
from typing import Dict, List, Optional
from nlp.cleaner import load_spacy_model

# ─── MOTS-CLÉS DATES EN FRANÇAIS ─────────────────────────

DATE_KEYWORDS = [
    "lundi", "mardi", "mercredi", "jeudi", "vendredi",
    "samedi", "dimanche", "hier", "aujourd'hui", "demain",
    "semaine", "mois", "janvier", "février", "mars", "avril",
    "mai", "juin", "juillet", "août", "septembre", "octobre",
    "novembre", "décembre", "dernier", "prochain", "depuis",
    "matin", "soir", "midi", "nuit"
]

# ─── MOTS-CLÉS LIEUX EN FRANÇAIS ─────────────────────────

LOC_KEYWORDS = [
    "serveur", "datacenter", "bureau", "salle", "bâtiment",
    "site", "local", "agence", "siège", "entrepôt", "usine",
    "cloud", "réseau", "infrastructure", "plateforme"
]

# ─── EXTRACTION D'ENTITÉS NER ────────────────────────────

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extrait les entités nommées depuis le texte via SpaCy NER.
    Complété par une détection manuelle pour DATE et LOC.

    Retourne un dictionnaire avec les entités par type :
    - PER     : personnes
    - ORG     : organisations
    - DATE    : dates et références temporelles
    - LOC     : lieux et infrastructures
    - PRODUCT : outils / produits
    - MISC    : divers
    """
    model = load_spacy_model()
    doc   = model(text)

    entities = {
        "PER"    : [],
        "ORG"    : [],
        "DATE"   : [],
        "LOC"    : [],
        "PRODUCT": [],
        "MISC"   : []
    }

    # ① SpaCy NER standard
    for ent in doc.ents:
        label = ent.label_
        value = ent.text.strip()
        if label in entities and value not in entities[label]:
            entities[label].append(value)

    # ② Détection manuelle des dates
    text_lower = text.lower()
    for keyword in DATE_KEYWORDS:
        if keyword in text_lower:
            pattern = r'[a-zA-ZÀ-ÿ]*\s*' + keyword + r'\s*[a-zA-ZÀ-ÿ]*'
            matches = re.findall(pattern, text_lower)
            for match in matches:
                match = match.strip()
                if match and match not in entities["DATE"]:
                    entities["DATE"].append(match)
                    break

    # ③ Détection manuelle des lieux/infrastructures
    for keyword in LOC_KEYWORDS:
        if keyword in text_lower:
            pattern = r'[a-zA-ZÀ-ÿ]*\s*' + keyword + r'\s*[a-zA-ZÀ-ÿ]*'
            matches = re.findall(pattern, text_lower)
            for match in matches:
                match = match.strip()
                if match and match not in entities["LOC"]:
                    entities["LOC"].append(match)
                    break

    return entities


# ─── DÉTECTION RESPONSABLE PROBABLE ─────────────────────

def detect_probable_responsible(text: str) -> Optional[str]:
    """
    Identifie le responsable probable d'un blocage
    en cherchant les entités de type PER ou ORG dans le texte.
    Priorité : personne > organisation
    """
    entities = extract_entities(text)

    if entities["PER"]:
        return entities["PER"][0]
    if entities["ORG"]:
        return entities["ORG"][0]
    return None


# ─── ANALYSE COMPLÈTE D'UN PROBLÈME ─────────────────────

def analyze_problem(text: str) -> Dict:
    """
    Analyse complète d'un texte de problème.
    Retourne les entités extraites + le responsable probable.
    """
    entities             = extract_entities(text)
    probable_responsible = detect_probable_responsible(text)

    return {
        "entities"            : entities,
        "probable_responsible": probable_responsible,
        "summary": {
            "nb_persons"      : len(entities["PER"]),
            "nb_organisations": len(entities["ORG"]),
            "nb_dates"        : len(entities["DATE"]),
            "nb_locations"    : len(entities["LOC"]),
        }
    }