import re
import unicodedata
import spacy
from typing import Optional

# ─── CHARGEMENT DU MODÈLE SPACY ──────────────────────────

nlp = None

def load_spacy_model():
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("fr_core_news_md")
        except OSError:
            raise OSError(
                "Modèle SpaCy 'fr_core_news_md' non trouvé. "
                "Exécutez : python -m spacy download fr_core_news_md"
            )
    return nlp

# ─── STOPWORDS FRANÇAIS ───────────────────────────────────

STOPWORDS_FR = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "en",
    "au", "aux", "ce", "se", "sa", "son", "ses", "mon", "ma", "mes",
    "ton", "ta", "tes", "nous", "vous", "ils", "elles", "je", "tu",
    "il", "elle", "on", "que", "qui", "quoi", "dont", "où", "par",
    "sur", "sous", "dans", "avec", "sans", "pour", "mais", "ou",
    "donc", "or", "ni", "car", "est", "sont", "été", "être", "avoir",
    "avons", "avez", "ont", "cette", "cet", "ces", "tout", "tous",
    "plus", "pas", "ne", "se", "si", "même", "aussi", "très", "bien",
    "encore", "depuis", "alors", "ainsi", "comme", "quand", "après",
    "avant", "pendant", "entre", "vers", "chez", "lors", "afin"
}

# ─── FONCTIONS DE NETTOYAGE ───────────────────────────────

def normalize_unicode(text: str) -> str:
    """Normalise les caractères Unicode — supprime les accents parasites."""
    return unicodedata.normalize("NFC", text)

def remove_special_characters(text: str) -> str:
    """Supprime les caractères spéciaux en gardant lettres, chiffres et espaces."""
    text = re.sub(r"[^\w\s\-àâäéèêëîïôùûüç]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def lemmatize_and_filter(text: str) -> str:
    """Lemmatise le texte et supprime les stopwords via SpaCy."""
    model = load_spacy_model()
    doc = model(text.lower())
    tokens = [
        token.lemma_
        for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.is_space
        and token.lemma_ not in STOPWORDS_FR
        and len(token.lemma_) > 2
    ]
    return " ".join(tokens)

def clean_text(text: str) -> Optional[str]:
    """
    Pipeline complet de nettoyage :
    1. Normalisation Unicode
    2. Suppression caractères spéciaux
    3. Lemmatisation + suppression stopwords
    """
    if not text or not text.strip():
        return None
    text = normalize_unicode(text)
    text = remove_special_characters(text)
    text = lemmatize_and_filter(text)
    return text if text.strip() else None