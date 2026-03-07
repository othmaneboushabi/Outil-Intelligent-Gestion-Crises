from fastapi import FastAPI, Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db, engine, Base
from models import User, UserRole
from schemas import (
    UserCreate, UserResponse, UserUpdate,
    DepartmentCreate, DepartmentResponse, DepartmentUpdate,
    ReportCreate, ReportResponse, ReportUpdate,
    TokenResponse, LoginRequest,
    ExecutiveSummaryResponse, AlertResponse
)
from crud import (
    get_user_by_email, create_user, get_all_users,
    update_user, deactivate_user, update_last_login,
    get_all_departments, get_department_by_id,
    create_department, update_department, delete_department,
    get_report_by_id, get_reports_by_user, get_all_reports,
    get_report_by_week_and_user, create_report, update_report,
    get_top_problems_by_week, get_active_alerts,
    get_summary_by_week, create_or_update_summary, get_all_summaries
)
from auth import (
    verify_password, create_access_token,
    get_current_user, get_current_admin,
    get_current_active_user, bearer_scheme, decode_token
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
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
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
def list_users(db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    return get_all_users(db)

@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def modify_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    user = update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user

@app.delete("/users/{user_id}", tags=["Users"])
def disable_user(user_id: int, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    user = deactivate_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"message": f"Utilisateur {user_id} désactivé"}

# ─── DEPARTMENTS ROUTES ───────────────────────────────────
@app.get("/departments", response_model=List[DepartmentResponse], tags=["Departments"])
def list_departments(db: Session = Depends(get_db), current_user: User = Security(get_current_user)):
    return get_all_departments(db)

@app.post("/departments", response_model=DepartmentResponse, tags=["Departments"])
def add_department(dept_data: DepartmentCreate, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    from crud import get_department_by_name
    existing = get_department_by_name(db, dept_data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Département déjà existant")
    return create_department(db, dept_data)

@app.put("/departments/{dept_id}", response_model=DepartmentResponse, tags=["Departments"])
def modify_department(dept_id: int, dept_data: DepartmentUpdate, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    dept = update_department(db, dept_id, dept_data)
    if not dept:
        raise HTTPException(status_code=404, detail="Département introuvable")
    return dept

@app.delete("/departments/{dept_id}", tags=["Departments"])
def remove_department(dept_id: int, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    success = delete_department(db, dept_id)
    if not success:
        raise HTTPException(status_code=404, detail="Département introuvable")
    return {"message": f"Département {dept_id} supprimé"}

# ─── REPORTS ROUTES ───────────────────────────────────────
@app.get("/reports", response_model=List[ReportResponse], tags=["Reports"])
def list_reports(db: Session = Depends(get_db), current_user: User = Security(get_current_user)):
    if current_user.role == UserRole.admin:
        return get_all_reports(db)
    return get_reports_by_user(db, current_user.id)

@app.post("/reports", response_model=ReportResponse, tags=["Reports"])
def submit_report(report_data: ReportCreate, db: Session = Depends(get_db), current_user: User = Security(get_current_active_user)):
    existing = get_report_by_week_and_user(db, current_user.id, report_data.week_number, report_data.year)
    if existing:
        raise HTTPException(status_code=400, detail="Vous avez déjà soumis un rapport pour cette semaine")
    return create_report(db, report_data, current_user.id)

@app.put("/reports/{report_id}", response_model=ReportResponse, tags=["Reports"])
def modify_report(report_id: int, report_data: ReportUpdate, db: Session = Depends(get_db), current_user: User = Security(get_current_active_user)):
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    if report.submitted_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    return update_report(db, report_id, report_data)

@app.get("/reports/{report_id}", response_model=ReportResponse, tags=["Reports"])
def get_report(report_id: int, db: Session = Depends(get_db), current_user: User = Security(get_current_user)):
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return report

# ─── PROBLEMS ROUTES ──────────────────────────────────────
@app.get("/problems/top", tags=["Problems"])
def top_problems(week: int, year: int, limit: int = 5, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    problems = get_top_problems_by_week(db, week, year, limit)
    return problems

# ─── ALERTS ROUTES ────────────────────────────────────────
@app.get("/alerts/active", response_model=List[AlertResponse], tags=["Alerts"])
def active_alerts(week: int, year: int, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    problems = get_active_alerts(db, week, year)
    result = []
    for p in problems:
        report = get_report_by_id(db, p.report_id)
        user = get_user_by_email(db, db.query(User).filter(User.id == report.submitted_by).first().email)
        dept = get_department_by_id(db, user.department_id)
        dep_depts = [get_department_by_id(db, d.dependent_department_id).name for d in p.dependencies]
        result.append(AlertResponse(
            problem_id=p.id,
            description=p.description,
            criticality_score=p.criticality_score,
            department_name=dept.name if dept else "Inconnu",
            probable_responsible=p.probable_responsible,
            dependent_departments=dep_depts
        ))
    return result

# ─── EXECUTIVE SUMMARY ROUTES ────────────────────────────
@app.get("/summaries", response_model=List[ExecutiveSummaryResponse], tags=["Summaries"])
def list_summaries(db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    return get_all_summaries(db)

@app.get("/summaries/{week}/{year}", response_model=ExecutiveSummaryResponse, tags=["Summaries"])
def get_summary(week: int, year: int, db: Session = Depends(get_db), admin: User = Security(get_current_admin)):
    summary = get_summary_by_week(db, week, year)
    if not summary:
        raise HTTPException(status_code=404, detail="Résumé introuvable pour cette semaine")
    return summary