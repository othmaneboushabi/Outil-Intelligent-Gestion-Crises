import pytest
from nlp.scoring import calculate_criticality_score, get_criticality_level

# ─── FORMULE RÉELLE v2.1 ─────────────────────────────────
# score_brut = (impact×0.4) + (urgency×0.3) + (nb_deps×0.2) + (rep×0.1)
# bonus      = (impact × urgency) / 25 × 0.5
# score_final= min(max(score_brut + bonus, 0.0), 5.0)

# ─── NIVEAUX RÉELS ───────────────────────────────────────
# <= 1.5 → "Faible — Surveiller"
# <= 2.5 → "Modéré — Planifier une action"
# <= 3.5 → "Élevé — Traiter cette semaine"
# <= 4.5 → "Critique — Action immédiate"
# >  4.5 → "Alerte Maximale — Escalade direction"


def test_score_critique():
    """impact=5,urgency=5,rep=3,deps=2 → 4.7"""
    # brut=5×0.4+5×0.3+2×0.2+3×0.1=2+1.5+0.4+0.3=4.2
    # bonus=25/25×0.5=0.5 → total=4.7
    score = calculate_criticality_score(5, 5, 3, 2)
    assert score == 4.7
    assert score > 4.5


def test_score_max():
    """Score plafonné à 5.0"""
    score = calculate_criticality_score(5, 5, 10, 10)
    assert score == 5.0


def test_score_faible():
    """Score faible impact=1,urgency=1,rep=1,deps=0"""
    score = calculate_criticality_score(1, 1, 1, 0)
    assert score <= 1.5


def test_score_sans_deps():
    """impact=4,urgency=4,rep=2,deps=0 → 3.32"""
    # brut=4×0.4+4×0.3+0×0.2+2×0.1=1.6+1.2+0+0.2=3.0
    # bonus=16/25×0.5=0.32 → total=3.32
    score = calculate_criticality_score(4, 4, 2, 0)
    assert score == 3.32


def test_score_avec_deps():
    """Score avec deps > sans deps"""
    score_sans = calculate_criticality_score(4, 4, 2, 0)
    score_avec = calculate_criticality_score(4, 4, 2, 2)
    assert score_avec > score_sans


def test_score_plafond():
    """Score ne dépasse pas 5.0"""
    score = calculate_criticality_score(5, 5, 10, 10)
    assert score <= 5.0


def test_score_positif():
    """Score toujours positif"""
    score = calculate_criticality_score(1, 1, 1, 0)
    assert score >= 0.0


def test_score_avec_deps_calcul():
    """impact=4,urgency=4,rep=2,deps=3 → 3.92"""
    # brut=4×0.4+4×0.3+3×0.2+2×0.1=1.6+1.2+0.6+0.2=3.6
    # bonus=16/25×0.5=0.32 → total=3.92
    score = calculate_criticality_score(4, 4, 2, 3)
    assert score == 3.92


def test_niveau_alerte_maximale():
    """Score > 4.5 → Alerte Maximale"""
    level = get_criticality_level(4.7)
    assert "Alerte Maximale" in level


def test_niveau_critique():
    """Score entre 3.5 et 4.5 → Critique"""
    level = get_criticality_level(4.0)
    assert "Critique" in level


def test_niveau_eleve():
    """Score entre 2.5 et 3.5 → Élevé"""
    level = get_criticality_level(3.0)
    assert "levé" in level or "lev" in level.lower()


def test_niveau_modere():
    """Score entre 1.5 et 2.5 → Modéré"""
    level = get_criticality_level(2.0)
    assert "Mod" in level


def test_niveau_faible():
    """Score <= 1.5 → Faible"""
    level = get_criticality_level(1.0)
    assert "Faible" in level