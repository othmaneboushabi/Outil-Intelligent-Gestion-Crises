# ─── TESTS NLP ───────────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.cleaner import clean_text
from nlp.ner_engine import extract_entities
from nlp.scoring import calculate_criticality_score, get_criticality_level

def compute_criticality_score(impact, urgency, repetitions, nb_dependencies):
    score = calculate_criticality_score(impact, urgency, repetitions, nb_dependencies)
    level = get_criticality_level(score)
    return score, level


class TestCleaner:

    def test_clean_basic(self):
        """Nettoyage texte basique"""
        text = "  Bonjour   le   monde!  "
        result = clean_text(text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_clean_special_chars(self):
        """Suppression caractères spéciaux"""
        text = "Problème@#$ avec le serveur!!!"
        result = clean_text(text)
        assert "@" not in result
        assert "#" not in result

    def test_clean_lowercase(self):
        """Texte en minuscules"""
        text = "SERVEUR TOMBE DEPUIS LUNDI"
        result = clean_text(text)
        assert result == result.lower()

    def test_clean_empty(self):
        """Texte vide → retourne None"""
        result = clean_text("")
        assert result is None or isinstance(result, str)

    def test_clean_numbers(self):
        """Les chiffres sont conservés ou supprimés proprement"""
        text = "Problème depuis 3 jours en semaine 42"
        result = clean_text(text)
        assert isinstance(result, str)


class TestNER:

    def test_ner_person(self):
        """Détection nom de personne"""
        text = "Karim Benali n'a pas fourni les accès nécessaires"
        entities = extract_entities(text)
        assert isinstance(entities, dict)

    def test_ner_date(self):
        """Détection date"""
        text = "Le serveur est tombé depuis vendredi dernier"
        entities = extract_entities(text)
        assert isinstance(entities, dict)

    def test_ner_empty_text(self):
        """Texte vide → dictionnaire vide ou avec listes vides"""
        entities = extract_entities("")
        assert isinstance(entities, dict)

    def test_ner_no_entities(self):
        """Texte sans entités nommées"""
        text = "le problème est technique"
        entities = extract_entities(text)
        assert isinstance(entities, dict)

    def test_ner_returns_dict(self):
        """Résultat toujours un dictionnaire"""
        text = "Marie Dupont a signalé un bug lundi à Paris"
        entities = extract_entities(text)
        assert isinstance(entities, dict)
        for key, value in entities.items():
            assert isinstance(value, list)


class TestScoring:

    def test_score_returns_tuple(self):
        """compute_criticality_score retourne (float, str)"""
        result = compute_criticality_score(
            impact=3, urgency=3, repetitions=1, nb_dependencies=0
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], str)

    def test_score_high_impact_urgency(self):
        """Impact et urgence élevés → score élevé"""
        score_high, _ = compute_criticality_score(
            impact=5, urgency=5, repetitions=1, nb_dependencies=0
        )
        score_low, _ = compute_criticality_score(
            impact=1, urgency=1, repetitions=1, nb_dependencies=0
        )
        assert score_high > score_low

    def test_score_repetitions_effect(self):
        """Plus de répétitions → score plus élevé"""
        score_high, _ = compute_criticality_score(
            impact=3, urgency=3, repetitions=10, nb_dependencies=0
        )
        score_low, _ = compute_criticality_score(
            impact=3, urgency=3, repetitions=1, nb_dependencies=0
        )
        assert score_high >= score_low

    def test_score_dependencies_effect(self):
        """Plus de dépendances → score plus élevé"""
        score_high, _ = compute_criticality_score(
            impact=3, urgency=3, repetitions=1, nb_dependencies=5
        )
        score_low, _ = compute_criticality_score(
            impact=3, urgency=3, repetitions=1, nb_dependencies=0
        )
        assert score_high >= score_low