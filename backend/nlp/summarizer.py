import requests
import os
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

# ─── CONFIGURATION ───────────────────────────────────────

HF_API_TOKEN    = os.getenv("HF_API_TOKEN")
HF_API_URL      = "https://api-inference.huggingface.co/models/"
MODEL_MAIN      = "mistralai/Mistral-7B-Instruct-v0.2"
MODEL_FALLBACK  = "moussaKam/barthez-orangesum-abstract"

HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}


# ─── CONSTRUCTION DU PROMPT ──────────────────────────────

def build_prompt(context: dict) -> str:
    """
    Construit le prompt en français pour Mistral-7B.
    """
    top_problems = context.get("top_problems", [])
    dept_stats   = context.get("dept_stats", {})
    global_score = context.get("global_score", 0)
    week         = context.get("week_number", 0)
    year         = context.get("year", 0)

    problems_text = "\n".join([
        f"- {p['description'][:100]} (score: {p['score']}, département: {p['dept']})"
        for p in top_problems[:3]
    ])

    dept_text = "\n".join([
        f"- {dept}: {count} problème(s)"
        for dept, count in dept_stats.items()
    ])

    prompt = f"""<s>[INST]
Tu es un assistant de gestion de crise organisationnelle.
Génère un résumé exécutif en français pour la semaine {week} de {year}.

DONNÉES DE LA SEMAINE :
Score de risque global : {global_score}/5

Répartition des problèmes par département :
{dept_text}

Top 3 problèmes critiques :
{problems_text}

Génère un résumé exécutif structuré contenant :
1. Situation globale (2 phrases)
2. Département le plus critique
3. Top 3 actions prioritaires recommandées
4. Niveau de risque global

Réponds uniquement en français, de façon concise et professionnelle.
[/INST]</s>"""

    return prompt


# ─── APPEL HUGGING FACE ──────────────────────────────────

def call_mistral(prompt: str) -> Optional[str]:
    """
    Appelle Mistral-7B via l'API Inference Hugging Face.
    """
    try:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens" : 500,
                "temperature"    : 0.7,
                "return_full_text": False
            }
        }
        response = requests.post(
            HF_API_URL + MODEL_MAIN,
            headers = HEADERS,
            json    = payload,
            timeout = 30
        )
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0].get("generated_text", "").strip()
        return None
    except Exception as e:
        print(f"Erreur Mistral-7B : {e}")
        return None


def call_barthez(context: dict) -> Optional[str]:
    """
    Fallback : appelle barthez-orangesum-abstract
    (modèle BART francophone).
    """
    try:
        top_problems = context.get("top_problems", [])
        dept_stats   = context.get("dept_stats", {})
        global_score = context.get("global_score", 0)

        text = f"Rapport hebdomadaire. Score global: {global_score}/5. "
        text += "Problèmes: " + ". ".join([
            p["description"][:80] for p in top_problems[:3]
        ])
        text += ". Départements: " + ", ".join(dept_stats.keys())

        payload  = {"inputs": text}
        response = requests.post(
            HF_API_URL + MODEL_FALLBACK,
            headers = HEADERS,
            json    = payload,
            timeout = 30
        )
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                return result[0].get("summary_text", "").strip()
        return None
    except Exception as e:
        print(f"Erreur barthez : {e}")
        return None


# ─── COLLECTE DES DONNÉES ────────────────────────────────

def collect_week_data(db: Session, week_number: int, year: int) -> dict:
    """
    Collecte et agrège les données de la semaine
    pour construire le contexte du prompt.
    """
    from models import Problem, Report, Department, User
    from sqlalchemy import func

    problems = (
        db.query(Problem)
        .join(Report)
        .filter(
            Report.week_number == week_number,
            Report.year        == year
        )
        .order_by(Problem.criticality_score.desc())
        .all()
    )

    if not problems:
        return {}

    # Top 3 problèmes critiques
    top_problems = []
    for p in problems[:3]:
        report = db.query(Report).filter(Report.id == p.report_id).first()
        user   = db.query(User).filter(User.id == report.submitted_by).first()
        dept   = db.query(Department).filter(
            Department.id == user.department_id
        ).first() if user and user.department_id else None

        top_problems.append({
            "description" : p.description,
            "score"       : p.criticality_score or 0,
            "dept"        : dept.name if dept else "Inconnu"
        })

    # Répartition par département
    dept_stats = {}
    for p in problems:
        report = db.query(Report).filter(Report.id == p.report_id).first()
        user   = db.query(User).filter(User.id == report.submitted_by).first()
        dept   = db.query(Department).filter(
            Department.id == user.department_id
        ).first() if user and user.department_id else None
        dept_name = dept.name if dept else "Inconnu"
        dept_stats[dept_name] = dept_stats.get(dept_name, 0) + 1

    # Score global moyen
    scores = [p.criticality_score for p in problems if p.criticality_score]
    global_score = round(sum(scores) / len(scores), 2) if scores else 0

    return {
        "week_number"  : week_number,
        "year"         : year,
        "top_problems" : top_problems,
        "dept_stats"   : dept_stats,
        "global_score" : global_score,
        "total_problems": len(problems)
    }


# ─── GÉNÉRATION DU RÉSUMÉ ────────────────────────────────

def generate_executive_summary(
    db: Session,
    week_number: int,
    year: int,
    user_id: int,
    force_regenerate: bool = False
) -> dict:
    """
    Génère le résumé exécutif pour la semaine donnée.
    - Vérifie le cache PostgreSQL avant d'appeler l'API
    - Essaie Mistral-7B puis fallback barthez
    - Stocke le résultat en base
    """
    from crud import get_summary_by_week, create_or_update_summary

    # Vérifier le cache
    if not force_regenerate:
        existing = get_summary_by_week(db, week_number, year)
        if existing:
            return {
                "content"    : existing.content,
                "model_used" : existing.model_used,
                "cached"     : True,
                "generated_at": str(existing.generated_at)
            }

    # Collecter les données
    context = collect_week_data(db, week_number, year)
    if not context:
        return {
            "content"    : "Aucune donnée disponible pour cette semaine.",
            "model_used" : "none",
            "cached"     : False
        }

    # Essayer Mistral-7B
    content    = None
    model_used = None

    prompt  = build_prompt(context)
    content = call_mistral(prompt)

    if content:
        model_used = MODEL_MAIN
    else:
        print("Mistral-7B indisponible — utilisation du fallback barthez")
        content    = call_barthez(context)
        model_used = MODEL_FALLBACK

    if not content:
        content    = (
            f"Résumé semaine {week_number}/{year} — "
            f"Score global : {context['global_score']}/5. "
            f"Problèmes détectés : {context['total_problems']}. "
            f"Départements concernés : {', '.join(context['dept_stats'].keys())}."
        )
        model_used = "fallback_local"

    # Sauvegarder en base
    create_or_update_summary(
        db          = db,
        week_number = week_number,
        year        = year,
        content     = content,
        model_used  = model_used,
        generated_by= user_id
    )

    return {
        "content"    : content,
        "model_used" : model_used,
        "cached"     : False,
        "context"    : context
    }