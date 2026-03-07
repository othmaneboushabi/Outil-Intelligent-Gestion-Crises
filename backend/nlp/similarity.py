import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from sqlalchemy.orm import Session

# ─── CHARGEMENT DU MODÈLE ────────────────────────────────

model = None

def load_transformer_model() -> SentenceTransformer:
    global model
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


# ─── CALCUL DES EMBEDDINGS ───────────────────────────────

def compute_embeddings(texts: List[str]) -> np.ndarray:
    """
    Transforme une liste de textes en vecteurs numériques.
    Chaque texte devient un vecteur de 384 dimensions.
    """
    transformer = load_transformer_model()
    embeddings = transformer.encode(texts, convert_to_numpy=True)
    return embeddings


# ─── SIMILARITÉ COSINUS ───────────────────────────────────

def compute_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Calcule la matrice de similarité cosinus entre tous les embeddings.
    Retourne une matrice N×N où chaque valeur est entre 0 et 1.
    """
    return cosine_similarity(embeddings)


def find_similar_problems(
    target_text: str,
    candidate_texts: List[str],
    candidate_ids: List[int],
    threshold: float = 0.75
) -> List[dict]:
    """
    Trouve les problèmes similaires au texte cible.
    Seuil par défaut : 0.75 (similarité cosinus)
    """
    if not candidate_texts:
        return []

    all_texts = [target_text] + candidate_texts
    embeddings = compute_embeddings(all_texts)

    target_embedding     = embeddings[0].reshape(1, -1)
    candidate_embeddings = embeddings[1:]

    similarities = cosine_similarity(target_embedding, candidate_embeddings)[0]

    results = []
    for i, score in enumerate(similarities):
        if score >= threshold:
            results.append({
                "problem_id"       : candidate_ids[i],
                "similarity_score" : round(float(score), 3),
                "text"             : candidate_texts[i][:80] + "..."
            })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results


# ─── CLUSTERING ───────────────────────────────────────────

def cluster_problems(
    texts: List[str],
    problem_ids: List[int],
    threshold: float = 0.75
) -> dict:
    """
    Regroupe les problèmes similaires en clusters.
    Retourne un dictionnaire {problem_id: cluster_id}.
    Utilise AgglomerativeClustering de sklearn.
    """
    if len(texts) < 2:
        return {pid: 0 for pid in problem_ids}

    embeddings = compute_embeddings(texts)

    distance_threshold = 1 - threshold

    clustering = AgglomerativeClustering(
        n_clusters         = None,
        distance_threshold = distance_threshold,
        metric             = "cosine",
        linkage            = "average"
    )
    labels = clustering.fit_predict(embeddings)

    return {problem_ids[i]: int(labels[i]) for i in range(len(problem_ids))}


# ─── MISE À JOUR DES CLUSTERS EN BASE ────────────────────

def update_clusters_in_db(db: Session, week_number: int, year: int) -> dict:
    """
    Récupère tous les problèmes de la semaine,
    calcule les clusters et met à jour cluster_id en base.
    """
    from models import Problem, Report

    problems = (
        db.query(Problem)
        .join(Report)
        .filter(Report.week_number == week_number, Report.year == year)
        .all()
    )

    if len(problems) < 2:
        return {}

    texts      = [p.cleaned_description or p.description for p in problems]
    ids        = [p.id for p in problems]
    clusters   = cluster_problems(texts, ids)

    for problem in problems:
        problem.cluster_id = clusters.get(problem.id, 0)

    db.commit()
    return clusters