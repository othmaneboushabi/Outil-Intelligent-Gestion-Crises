from sqlalchemy.orm import Session
from models import Problem, ProblemDependency

# ─── FORMULE DE CRITICITÉ V2.1 ───────────────────────────

def calculate_criticality_score(
    impact: int,
    urgency: int,
    repetitions: int,
    nb_dependencies: int
) -> float:
    """
    Formule v2.1 :
    score_brut = (Impact × 0.4) + (Urgence × 0.3)
               + (Dépendances × 0.2) + (Répétitions × 0.1)
    bonus      = (Impact × Urgence) / 25 × 0.5
    score_final = Normaliser(score_brut + bonus) entre 0.0 et 5.0
    """
    score_brut = (
        (impact      * 0.4) +
        (urgency     * 0.3) +
        (nb_dependencies * 0.2) +
        (repetitions * 0.1)
    )
    bonus = (impact * urgency) / 25 * 0.5
    score_final = score_brut + bonus
    score_normalise = round(min(max(score_final, 0.0), 5.0), 2)
    return score_normalise


def get_criticality_level(score: float) -> str:
    """Retourne le niveau de criticité selon le score."""
    if score <= 1.5:
        return "Faible — Surveiller"
    elif score <= 2.5:
        return "Modéré — Planifier une action"
    elif score <= 3.5:
        return "Élevé — Traiter cette semaine"
    elif score <= 4.5:
        return "Critique — Action immédiate"
    else:
        return "Alerte Maximale — Escalade direction"


def compute_and_save_score(db: Session, problem: Problem) -> float:
    """
    Calcule le score d'un problème depuis la DB
    et le sauvegarde dans criticality_score.
    """
    nb_dependencies = db.query(ProblemDependency).filter(
        ProblemDependency.problem_id == problem.id
    ).count()

    score = calculate_criticality_score(
        impact          = problem.impact,
        urgency         = problem.urgency,
        repetitions     = problem.repetitions,
        nb_dependencies = nb_dependencies
    )

    problem.criticality_score = score
    db.commit()
    db.refresh(problem)
    return score


def compute_scores_for_report(db: Session, report_id: int) -> dict:
    """
    Calcule et sauvegarde les scores de tous les problèmes
    d'un rapport. Retourne un résumé.
    """
    from models import Report
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return {}

    results = {}
    for problem in report.problems:
        score = compute_and_save_score(db, problem)
        results[problem.id] = {
            "description"  : problem.description[:50] + "...",
            "score"        : score,
            "niveau"       : get_criticality_level(score)
        }
    return results