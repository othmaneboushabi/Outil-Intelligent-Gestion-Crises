from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from nlp.cleaner import clean_text
from nlp.ner_engine import detect_probable_responsible
from nlp.scoring import compute_and_save_score
from nlp.alert_engine import check_and_trigger_alerts
from nlp.similarity import update_clusters_in_db
from nlp.domino import get_domino_summary, simulate_unblock, build_dependency_graph, export_graph_html
from nlp.summarizer import generate_executive_summary
from database import get_db, engine, Base
from models import Department, User, UserRole
from schemas import (
    UserCreate, UserResponse, UserUpdate,
    DepartmentCreate, DepartmentResponse, DepartmentUpdate,
    ReportCreate, ReportResponse, ReportUpdate,
    TokenResponse,
    ExecutiveSummaryResponse, AlertResponse
)
from crud import (
    get_user_by_email, create_user, get_all_users,
    update_user, deactivate_user, update_last_login,
    get_all_departments, get_department_by_id,
    get_department_by_name,
    create_department, update_department, delete_department,
    get_report_by_id, get_reports_by_user, get_all_reports,
    get_report_by_week_and_user, create_report, update_report,
    get_top_problems_by_week, get_active_alerts,
    get_summary_by_week, create_or_update_summary, get_all_summaries
)
from auth import (
    verify_password, create_access_token,
    get_current_user, get_current_admin,
    get_current_active_user
)

# ─── INITIALISATION ───────────────────────────────────────

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Outil Intelligent de Gestion de Crises",
    description="API REST pour la gestion des crises et priorisation des problèmes",
    version="1.0.0"
)

# ─── ROUTE DE SANTÉ ───────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "API opérationnelle"}

# ─── AUTH ROUTES ──────────────────────────────────────────

@app.post("/auth/register", response_model=UserResponse, tags=["Auth"])
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    return create_user(db, user_data)

@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    update_last_login(db, user.id)
    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token  = token,
        token_type    = "bearer",
        role          = user.role,
        full_name     = user.full_name,
        department_id = user.department_id
    )

@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ─── USERS ROUTES ─────────────────────────────────────────

@app.post("/users", response_model=UserResponse, tags=["Users"])
def create_user_admin(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Créer un utilisateur (admin seulement)."""
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    return create_user(db, user_data)

@app.get("/users", response_model=List[UserResponse], tags=["Users"])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return get_all_users(db)

@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def modify_user(
    user_id  : int,
    user_data: UserUpdate,
    db       : Session = Depends(get_db),
    admin    : User    = Depends(get_current_admin)
):
    # Vérifier que le département existe si fourni
    if user_data.department_id is not None:
        dept = get_department_by_id(db, user_data.department_id)
        if not dept:
            raise HTTPException(
                status_code=404,
                detail=f"Département {user_data.department_id} introuvable"
            )

    user = update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user

@app.delete("/users/{user_id}", tags=["Users"])
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    user = deactivate_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"message": f"Utilisateur {user_id} désactivé"}

@app.patch("/users/{user_id}/toggle", tags=["Users"])
def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Activer/Désactiver un utilisateur — interdit sur les admins."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Impossible de désactiver un administrateur"
        )
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"Utilisateur {user_id} — actif: {user.is_active}"}

# ─── DEPARTMENTS ROUTES ───────────────────────────────────

@app.get("/departments", response_model=List[DepartmentResponse], tags=["Departments"])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_all_departments(db)

@app.post("/departments", response_model=DepartmentResponse, tags=["Departments"])
def add_department(
    dept_data: DepartmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    existing = get_department_by_name(db, dept_data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Département déjà existant")
    return create_department(db, dept_data)

@app.put("/departments/{dept_id}", response_model=DepartmentResponse, tags=["Departments"])
def modify_department(
    dept_id: int,
    dept_data: DepartmentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    dept = update_department(db, dept_id, dept_data)
    if not dept:
        raise HTTPException(status_code=404, detail="Département introuvable")
    return dept

@app.delete("/departments/{dept_id}", tags=["Departments"])
def remove_department(
    dept_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    from models import Report, User as UserModel

    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Département non trouvé")

    # Utilisateurs liés
    linked_users = db.query(UserModel).filter(
        UserModel.department_id == dept_id
    ).count()

    # Rapports liés via les users du département
    user_ids = db.query(UserModel.id).filter(
        UserModel.department_id == dept_id
    ).subquery()

    linked_reports = db.query(Report).filter(
        Report.submitted_by.in_(user_ids)
    ).count()

    if linked_users > 0 or linked_reports > 0:
        dept.is_active = False
        db.commit()
        return {
            "message" : f"Département '{dept.name}' archivé",
            "archived": True,
            "reason"  : f"{linked_users} utilisateur(s) et {linked_reports} rapport(s) liés"
        }
    else:
        db.delete(dept)
        db.commit()
        return {
            "message" : f"Département '{dept.name}' supprimé ",
            "archived": False
        }
# ─── REPORTS ROUTES ───────────────────────────────────────

@app.get("/reports", response_model=List[ReportResponse], tags=["Reports"])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.admin:
        return get_all_reports(db)
    return get_reports_by_user(db, current_user.id)

@app.post("/reports", response_model=ReportResponse, tags=["Reports"])
def submit_report(
    report_data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    existing = get_report_by_week_and_user(
        db, current_user.id,
        report_data.week_number,
        report_data.year
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Vous avez déjà soumis un rapport pour cette semaine"
        )

    report = create_report(db, report_data, current_user.id)

    for problem in report.problems:
        problem.cleaned_description  = clean_text(problem.description)
        problem.probable_responsible = detect_probable_responsible(problem.description)
        compute_and_save_score(db, problem)

    db.commit()
    update_clusters_in_db(db, report_data.week_number, report_data.year)
    check_and_trigger_alerts(db, report_data.week_number, report_data.year)
    db.refresh(report)
    return report

@app.put("/reports/{report_id}", response_model=ReportResponse, tags=["Reports"])
def modify_report(
    report_id: int,
    report_data: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    if report.submitted_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return update_report(db, report_id, report_data)

@app.get("/reports/{report_id}", response_model=ReportResponse, tags=["Reports"])
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return report

# ─── PROBLEMS ROUTES ──────────────────────────────────────

@app.get("/problems/top", tags=["Problems"])
def top_problems(
    week: int,
    year: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return get_top_problems_by_week(db, week, year, limit)

# ─── ALERTS ROUTES ────────────────────────────────────────

@app.get("/alerts/active", response_model=List[AlertResponse], tags=["Alerts"])
def active_alerts(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    problems = get_active_alerts(db, week, year)
    result = []
    for p in problems:
        report = get_report_by_id(db, p.report_id)
        user   = db.query(User).filter(User.id == report.submitted_by).first()
        dept   = get_department_by_id(db, user.department_id) if user else None
        dep_depts = [
            get_department_by_id(db, d.dependent_department_id).name
            for d in p.dependencies
        ]
        result.append(AlertResponse(
            problem_id            = p.id,
            description           = p.description,
            criticality_score     = p.criticality_score,
            department_name       = dept.name if dept else "Inconnu",
            probable_responsible  = p.probable_responsible,
            dependent_departments = dep_depts
        ))
    return result

# ─── SUMMARIES ROUTES ─────────────────────────────────────

@app.get("/summaries", response_model=List[ExecutiveSummaryResponse], tags=["Summaries"])
def list_summaries(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return get_all_summaries(db)

@app.get("/summaries/{week}/{year}", response_model=ExecutiveSummaryResponse, tags=["Summaries"])
def get_summary(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    summary = get_summary_by_week(db, week, year)
    if not summary:
        raise HTTPException(status_code=404, detail="Résumé introuvable")
    return summary

@app.post("/summaries/generate", tags=["Summaries"])
def generate_summary(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return generate_executive_summary(
        db=db, week_number=week, year=year,
        user_id=admin.id, force_regenerate=False
    )

@app.post("/summaries/regenerate", tags=["Summaries"])
def regenerate_summary(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return generate_executive_summary(
        db=db, week_number=week, year=year,
        user_id=admin.id, force_regenerate=True
    )

# ─── DOMINO ROUTES ────────────────────────────────────────

@app.get("/domino/summary", tags=["Domino"])
def domino_summary(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return get_domino_summary(db, week, year)

@app.get("/domino/simulate", tags=["Domino"])
def domino_simulate(
    dept_id: int,
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    graph = build_dependency_graph(db, week, year)
    return simulate_unblock(graph, dept_id, db)

@app.get("/domino/graph-html", tags=["Domino"])
def domino_graph_html(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    from fastapi.responses import FileResponse
    import os
    graph       = build_dependency_graph(db, week, year)
    output_path = f"domino_week{week}_{year}.html"
    export_graph_html(graph, db, output_path)
    if os.path.exists(output_path):
        return FileResponse(
            path       = output_path,
            media_type = "text/html",
            filename   = output_path
        )
    raise HTTPException(status_code=500, detail="Erreur génération graphe")
# ─── ANALYZE ROUTE (temps réel) ──────────────────────────

@app.post("/analyze", tags=["NLP"])
def analyze_problem_realtime(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyse un problème en temps réel avant soumission.
    Retourne : entités NER, score criticité, responsable probable,
    problèmes similaires.
    """
    description  = data.get("description", "")
    impact       = data.get("impact", 3)
    urgency      = data.get("urgency", 3)
    repetitions  = data.get("repetitions", 1)
    nb_deps      = data.get("nb_dependencies", 0)
    week_number  = data.get("week_number", 1)
    year         = data.get("year", 2025)

    if not description:
        raise HTTPException(status_code=400, detail="Description obligatoire")

    from nlp.cleaner import clean_text
    from nlp.ner_engine import extract_entities, detect_probable_responsible
    from nlp.scoring import calculate_criticality_score, get_criticality_level
    from nlp.similarity import compute_embeddings, find_similar_problems
    from models import Problem, Report
    import numpy as np

    # 1. Nettoyage
    cleaned = clean_text(description)

    # 2. Entités NER
    entities    = extract_entities(description)
    responsible = detect_probable_responsible(description)

    # 3. Score criticité
    score = calculate_criticality_score(
        impact, urgency, repetitions, nb_deps
    )
    level = get_criticality_level(score)

    # 4. Problèmes similaires dans la semaine
    similar = []
    try:
        problems = (
            db.query(Problem)
            .join(Report)
            .filter(
                Report.week_number == week_number,
                Report.year        == year,
                Problem.cleaned_description != None
            )
            .all()
        )

        if problems:
            candidates = [p.cleaned_description for p in problems]
            ids        = [p.id for p in problems]
            similar    = find_similar_problems(
                cleaned, candidates, ids, threshold=0.75
            )
    except Exception:
        similar = []

    return {
        "cleaned_description" : cleaned,
        "entities"            : entities,
        "probable_responsible": responsible,
        "criticality_score"   : score,
        "criticality_level"   : level,
        "similar_problems"    : similar
    }