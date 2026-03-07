from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime

from models import (
    User, Department, Report,
    Problem, ProblemDependency, ExecutiveSummary,
    UserRole
)
from schemas import (
    UserCreate, UserUpdate,
    DepartmentCreate, DepartmentUpdate,
    ReportCreate, ReportUpdate,
    ProblemCreate
)
from auth import hash_password


# ─── CRUD : USERS ─────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_all_users(db: Session) -> List[User]:
    return db.query(User).all()

def create_user(db: Session, user_data: UserCreate) -> User:
    user = User(
        email         = user_data.email,
        password_hash = hash_password(user_data.password),
        full_name     = user_data.full_name,
        role          = user_data.role,
        department_id = user_data.department_id,
        is_active     = True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

def deactivate_user(db: Session, user_id: int) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user

def update_last_login(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login = datetime.utcnow()
        db.commit()


# ─── CRUD : DEPARTMENTS ───────────────────────────────────

def get_all_departments(db: Session) -> List[Department]:
    return db.query(Department).all()

def get_department_by_id(db: Session, dept_id: int) -> Optional[Department]:
    return db.query(Department).filter(Department.id == dept_id).first()

def get_department_by_name(db: Session, name: str) -> Optional[Department]:
    return db.query(Department).filter(Department.name == name).first()

def create_department(db: Session, dept_data: DepartmentCreate) -> Department:
    dept = Department(
        name        = dept_data.name,
        description = dept_data.description
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

def update_department(db: Session, dept_id: int, dept_data: DepartmentUpdate) -> Optional[Department]:
    dept = get_department_by_id(db, dept_id)
    if not dept:
        return None
    for field, value in dept_data.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept

def delete_department(db: Session, dept_id: int) -> bool:
    dept = get_department_by_id(db, dept_id)
    if not dept:
        return False
    db.delete(dept)
    db.commit()
    return True


# ─── CRUD : REPORTS ───────────────────────────────────────

def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
    return db.query(Report).filter(Report.id == report_id).first()

def get_reports_by_user(db: Session, user_id: int) -> List[Report]:
    return db.query(Report).filter(Report.submitted_by == user_id).all()

def get_all_reports(db: Session) -> List[Report]:
    return db.query(Report).all()

def get_report_by_week_and_user(
    db: Session, user_id: int, week_number: int, year: int
) -> Optional[Report]:
    return db.query(Report).filter(
        and_(
            Report.submitted_by == user_id,
            Report.week_number  == week_number,
            Report.year         == year
        )
    ).first()

def create_report(db: Session, report_data: ReportCreate, user_id: int) -> Report:
    report = Report(
        submitted_by   = user_id,
        week_number    = report_data.week_number,
        year           = report_data.year,
        global_summary = report_data.global_summary
    )
    db.add(report)
    db.flush()

    for problem_data in report_data.problems:
        create_problem(db, problem_data, report.id)

    db.commit()
    db.refresh(report)
    return report

def update_report(db: Session, report_id: int, report_data: ReportUpdate) -> Optional[Report]:
    report = get_report_by_id(db, report_id)
    if not report:
        return None
    if report_data.global_summary:
        report.global_summary = report_data.global_summary
    if report_data.problems:
        for problem in report.problems:
            db.delete(problem)
        db.flush()
        for problem_data in report_data.problems:
            create_problem(db, problem_data, report_id)
    db.commit()
    db.refresh(report)
    return report


# ─── CRUD : PROBLEMS ──────────────────────────────────────

def create_problem(db: Session, problem_data: ProblemCreate, report_id: int) -> Problem:
    problem = Problem(
        report_id   = report_id,
        description = problem_data.description,
        type        = problem_data.type,
        impact      = problem_data.impact,
        urgency     = problem_data.urgency,
        repetitions = problem_data.repetitions,
    )
    db.add(problem)
    db.flush()

    for dept_id in problem_data.dependent_department_ids:
        dependency = ProblemDependency(
            problem_id              = problem.id,
            dependent_department_id = dept_id
        )
        db.add(dependency)

    db.flush()
    return problem

def get_problems_by_report(db: Session, report_id: int) -> List[Problem]:
    return db.query(Problem).filter(Problem.report_id == report_id).all()

def get_top_problems_by_week(
    db: Session, week_number: int, year: int, limit: int = 5
) -> List[Problem]:
    return (
        db.query(Problem)
        .join(Report)
        .filter(and_(Report.week_number == week_number, Report.year == year))
        .order_by(Problem.criticality_score.desc())
        .limit(limit)
        .all()
    )

def get_active_alerts(db: Session, week_number: int, year: int) -> List[Problem]:
    return (
        db.query(Problem)
        .join(Report)
        .filter(
            and_(
                Report.week_number        == week_number,
                Report.year               == year,
                Problem.criticality_score  > 4.6,
                Problem.alert_sent        == True
            )
        )
        .all()
    )

def mark_alert_sent(db: Session, problem_id: int) -> None:
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if problem:
        problem.alert_sent = True
        db.commit()


# ─── CRUD : EXECUTIVE SUMMARIES ───────────────────────────

def get_summary_by_week(
    db: Session, week_number: int, year: int
) -> Optional[ExecutiveSummary]:
    return db.query(ExecutiveSummary).filter(
        and_(
            ExecutiveSummary.week_number == week_number,
            ExecutiveSummary.year        == year
        )
    ).first()

def create_or_update_summary(
    db: Session,
    week_number: int,
    year: int,
    content: str,
    model_used: str,
    generated_by: int
) -> ExecutiveSummary:
    summary = get_summary_by_week(db, week_number, year)
    if summary:
        summary.content      = content
        summary.model_used   = model_used
        summary.generated_at = datetime.utcnow()
    else:
        summary = ExecutiveSummary(
            week_number  = week_number,
            year         = year,
            content      = content,
            model_used   = model_used,
            generated_by = generated_by,
        )
        db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary

def get_all_summaries(db: Session) -> List[ExecutiveSummary]:
    return (
        db.query(ExecutiveSummary)
        .order_by(ExecutiveSummary.generated_at.desc())
        .all()
    )