# ─── TESTS FORMULE CRITICITÉ v2.1 ────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.scoring import calculate_criticality_score, get_criticality_level

def compute_criticality_score(impact, urgency, repetitions, nb_dependencies):
    score = calculate_criticality_score(impact, urgency, repetitions, nb_dependencies)
    level = get_criticality_level(score)
    return score, level


class TestScoringFormula:

    def test_score_maximum(self):
        """Impact=5, Urgence=5, Rep=10, Deps=5 → score max"""
        score, level = compute_criticality_score(
            impact=5, urgency=5, repetitions=10, nb_dependencies=5
        )
        assert score >= 4.6
        assert level == "Alerte Maximale — Escalade direction"

    def test_score_minimum(self):
        """Impact=1, Urgence=1, Rep=1, Deps=0 → score faible"""
        score, level = compute_criticality_score(
            impact=1, urgency=1, repetitions=1, nb_dependencies=0
        )
        assert score < 2.6

    def test_score_moyen(self):
        """Impact=3, Urgence=3 → score moyen"""
        score, level = compute_criticality_score(
            impact=3, urgency=3, repetitions=2, nb_dependencies=1
        )
        assert 2.6 <= score < 4.6

    def test_score_alerte_maximale(self):
        """Score > 4.6 → Alerte Maximale"""
        score, level = compute_criticality_score(
            impact=5, urgency=5, repetitions=5, nb_dependencies=3
        )
        assert score >= 4.6
        assert "Alerte Maximale" in level

    def test_score_type_float(self):
        """Le score retourné est un float"""
        score, level = compute_criticality_score(
            impact=3, urgency=3, repetitions=1, nb_dependencies=0
        )
        assert isinstance(score, float)
        assert isinstance(level, str)

    def test_score_range(self):
        """Le score est toujours entre 0 et 5"""
        for impact in range(1, 6):
            for urgency in range(1, 6):
                score, _ = compute_criticality_score(
                    impact=impact, urgency=urgency,
                    repetitions=1, nb_dependencies=0
                )
                assert 0 <= score <= 5


class TestScoringLevels:

    def test_level_faible(self):
        """Score < 2.6 → Faible"""
        score, level = compute_criticality_score(
            impact=1, urgency=1, repetitions=1, nb_dependencies=0
        )
        assert score < 2.6
        assert "Faible" in level or "Surveiller" in level

    def test_level_modere(self):
        """Score entre 2.6 et 3.6 → Modéré"""
        score, level = compute_criticality_score(
            impact=2, urgency=3, repetitions=1, nb_dependencies=0
        )
        assert isinstance(level, str)

    def test_alert_sent_threshold(self):
        """Score >= 4.6 → alerte doit être déclenchée"""
        score, level = compute_criticality_score(
            impact=5, urgency=5, repetitions=5, nb_dependencies=5
        )
        assert score >= 4.6