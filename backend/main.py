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

from database import get_db, engine, Base
from models import User, UserRole
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
        access_token=token,
        token_type="bearer",
        role=user.role,
        full_name=user.full_name,
        department_id=user.department_id
    )

@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ─── USERS ROUTES ─────────────────────────────────────────

@app.get("/users", response_model=List[UserResponse], tags=["Users"])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return get_all_users(db)

@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def modify_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
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
    success = delete_department(db, dept_id)
    if not success:
        raise HTTPException(status_code=404, detail="Département introuvable")
    return {"message": f"Département {dept_id} supprimé"}

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
    # Vérifier doublon semaine
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

    # Créer le rapport
    report = create_report(db, report_data, current_user.id)

    # Pipeline NLP sur chaque problème
    for problem in report.problems:

        # 1. Nettoyage du texte
        problem.cleaned_description = clean_text(problem.description)

        # 2. Extraction NER → responsable probable
        problem.probable_responsible = detect_probable_responsible(
            problem.description
        )

        # 3. Calcul du score de criticité
        compute_and_save_score(db, problem)

    db.commit()

    # 4. Clustering des problèmes similaires
    update_clusters_in_db(db, report_data.week_number, report_data.year)

    # 5. Vérification et déclenchement des alertes
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

# ─── EXECUTIVE SUMMARY ROUTES ─────────────────────────────

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
        raise HTTPException(status_code=404, detail="Résumé introuvable pour cette semaine")
    return summary
# ─── DOMINO ROUTES ────────────────────────────────────────

@app.get("/domino/summary", tags=["Domino"])
def domino_summary(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Retourne le résumé complet du graphe domino."""
    return get_domino_summary(db, week, year)


@app.get("/domino/simulate", tags=["Domino"])
def domino_simulate(
    dept_id: int,
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Simule le déblocage d'un département."""
    graph = build_dependency_graph(db, week, year)
    return simulate_unblock(graph, dept_id, db)


@app.get("/domino/graph-html", tags=["Domino"])
def domino_graph_html(
    week: int,
    year: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Génère et retourne le graphe PyVis en HTML."""
    from fastapi.responses import FileResponse
    import os

    graph       = build_dependency_graph(db, week, year)
    output_path = f"domino_week{week}_{year}.html"
    export_graph_html(graph, db, output_path)

    if os.path.exists(output_path):
        return FileResponse(
            path         = output_path,
            media_type   = "text/html",
            filename     = output_path
        )
    raise HTTPException(status_code=500, detail="Erreur génération graphe")