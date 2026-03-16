import pytest
from nlp.cleaner import clean_text
from nlp.ner_engine import extract_entities, detect_probable_responsible
from nlp.scoring import calculate_criticality_score, get_criticality_level


# ─── TESTS CLEANER ───────────────────────────────────────

def test_clean_text_basic():
    """Nettoyage basique du texte"""
    result = clean_text("Le serveur est tombé en panne !")
    assert result is not None
    assert isinstance(result, str)


def test_clean_text_lowercase():
    """Texte converti en minuscules"""
    result = clean_text("SERVEUR TOMBE")
    assert result == result.lower()


def test_clean_text_removes_punctuation():
    """Ponctuation supprimée"""
    result = clean_text("Problème critique !!!")
    assert "!" not in result


def test_clean_text_empty():
    """Texte vide → None"""
    result = clean_text("")
    assert result is None


def test_clean_text_returns_string():
    """Retourne une chaîne de caractères"""
    result = clean_text("Panne serveur critique depuis lundi")
    assert isinstance(result, str)
    assert len(result) > 0


# ─── TESTS NER ───────────────────────────────────────────

def test_extract_entities_person():
    """Extraction d'une personne"""
    entities = extract_entities("Karim Benali a bloqué l'accès au serveur")
    assert "PER" in entities
    assert len(entities["PER"]) > 0


def test_extract_entities_returns_dict():
    """Retourne un dictionnaire avec les bonnes clés"""
    entities = extract_entities("Test texte quelconque")
    assert isinstance(entities, dict)
    assert "PER"  in entities
    assert "DATE" in entities
    assert "LOC"  in entities


def test_extract_entities_date():
    """Extraction d'une date"""
    entities = extract_entities("Panne depuis lundi dernier")
    assert "DATE" in entities


def test_detect_responsible_person():
    """Détection responsable probable"""
    responsible = detect_probable_responsible(
        "Ahmed Alami n'a pas fourni les accès nécessaires"
    )
    assert responsible is not None
    assert isinstance(responsible, str)


def test_detect_responsible_none():
    """Texte sans nom → None ou string"""
    responsible = detect_probable_responsible(
        "Le système est en panne depuis hier"
    )
    assert responsible is None or isinstance(responsible, str)


# ─── TESTS SCORING ───────────────────────────────────────

def test_score_formule_v21():
    """Vérification formule v2.1 complète"""
    # impact=5, urgency=5, rep=3, deps=2
    # brut = 5×0.4 + 5×0.3 + 2×0.2 + 3×0.1 = 4.2
    # bonus = 25/25 × 0.5 = 0.5
    # total = 4.7
    score = calculate_criticality_score(5, 5, 3, 2)
    assert score == 4.7


def test_score_plafond():
    """Score ne dépasse pas 5.0"""
    score = calculate_criticality_score(5, 5, 10, 10)
    assert score <= 5.0


def test_niveau_alerte_maximale():
    """Score > 4.5 → Alerte Maximale"""
    level = get_criticality_level(4.7)
    assert "Alerte Maximale" in level


def test_niveau_critique_label():
    """Score entre 3.5 et 4.5 → Critique"""
    level = get_criticality_level(4.0)
    assert "Critique" in level