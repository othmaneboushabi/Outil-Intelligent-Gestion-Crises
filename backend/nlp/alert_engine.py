import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from models import Problem, Report, User, Department

load_dotenv()

# ─── CONFIGURATION SMTP ──────────────────────────────────

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

ALERT_THRESHOLD = 4.6


# ─── ENVOI EMAIL ─────────────────────────────────────────

def send_email(recipient: str, subject: str, body: str) -> bool:
    """
    Envoie un email d'alerte via SMTP.
    Retourne True si l'envoi réussit, False sinon.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = recipient

        html = f"""
        <html><body>
        <div style="font-family: Arial; padding: 20px;">
            <h2 style="color: #d32f2f;">⚠️ ALERTE MAXIMALE — Gestion de Crises</h2>
            <div style="background: #ffebee; padding: 15px; border-radius: 8px;">
                {body}
            </div>
            <p style="color: #666; font-size: 12px;">
                Système automatique — Outil Intelligent de Gestion de Crises
            </p>
        </div>
        </body></html>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient, msg.as_string())

        return True

    except Exception as e:
        print(f"Erreur envoi email : {e}")
        return False


# ─── DÉTECTION DES ALERTES ───────────────────────────────

def check_and_trigger_alerts(db: Session, week_number: int, year: int) -> List[dict]:
    """
    Vérifie tous les problèmes de la semaine.
    Déclenche une alerte pour ceux dont le score > 4.6
    et alert_sent = False.
    Retourne la liste des alertes déclenchées.
    """
    problems = (
        db.query(Problem)
        .join(Report)
        .filter(
            Report.week_number        == week_number,
            Report.year               == year,
            Problem.criticality_score  > ALERT_THRESHOLD,
            Problem.alert_sent        == False
        )
        .all()
    )

    alerts_triggered = []

    for problem in problems:
        report = db.query(Report).filter(Report.id == problem.report_id).first()
        user   = db.query(User).filter(User.id == report.submitted_by).first()
        dept   = db.query(Department).filter(
            Department.id == user.department_id
        ).first() if user and user.department_id else None

        dept_name = dept.name if dept else "Inconnu"

        alert_info = {
            "problem_id"           : problem.id,
            "description"          : problem.description,
            "criticality_score"    : problem.criticality_score,
            "department"           : dept_name,
            "probable_responsible" : problem.probable_responsible,
        }

        # Envoyer email aux admins
        admins = db.query(User).filter(User.role == "admin", User.is_active == True).all()
        for admin in admins:
            body = f"""
                <p><strong>Département :</strong> {dept_name}</p>
                <p><strong>Score de criticité :</strong>
                    <span style="color: #d32f2f; font-size: 18px;">
                        {problem.criticality_score}
                    </span>
                </p>
                <p><strong>Description :</strong> {problem.description}</p>
                <p><strong>Responsable probable :</strong>
                    {problem.probable_responsible or 'Non identifié'}
                </p>
            """
            send_email(
                recipient = admin.email,
                subject   = f"⚠️ Alerte Maximale — {dept_name} — Score {problem.criticality_score}",
                body      = body
            )

        # Marquer l'alerte comme envoyée
        problem.alert_sent = True
        db.commit()

        alerts_triggered.append(alert_info)

    return alerts_triggered


# ─── RÉCUPÉRER LES ALERTES ACTIVES ───────────────────────

def get_active_alerts_for_dashboard(
    db: Session,
    week_number: int,
    year: int
) -> List[dict]:
    """
    Retourne tous les problèmes en Alerte Maximale
    pour la semaine donnée (alert_sent = True).
    Utilisé pour la Page 0 du dashboard Admin.
    """
    problems = (
        db.query(Problem)
        .join(Report)
        .filter(
            Report.week_number        == week_number,
            Report.year               == year,
            Problem.criticality_score  > ALERT_THRESHOLD,
            Problem.alert_sent        == True
        )
        .all()
    )

    results = []
    for problem in problems:
        report = db.query(Report).filter(Report.id == problem.report_id).first()
        user   = db.query(User).filter(User.id == report.submitted_by).first()
        dept   = db.query(Department).filter(
            Department.id == user.department_id
        ).first() if user and user.department_id else None

        dep_depts = [
            db.query(Department).filter(
                Department.id == d.dependent_department_id
            ).first().name
            for d in problem.dependencies
            if db.query(Department).filter(
                Department.id == d.dependent_department_id
            ).first()
        ]

        results.append({
            "problem_id"           : problem.id,
            "description"          : problem.description,
            "criticality_score"    : problem.criticality_score,
            "department"           : dept.name if dept else "Inconnu",
            "probable_responsible" : problem.probable_responsible,
            "dependent_departments": dep_depts
        })

    return results