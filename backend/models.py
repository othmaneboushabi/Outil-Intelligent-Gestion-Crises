from sqlalchemy import (
    Column, Integer, String, Boolean,
    Float, Text, SmallInteger, Enum,
    ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


# ─── ÉNUMÉRATIONS ────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class ProblemType(str, enum.Enum):
    technique = "technique"
    humain = "humain"
    financier = "financier"
    logistique = "logistique"
    autre = "autre"


# ─── TABLE : departments ──────────────────────────────────

class Department(Base):
    __tablename__ = "departments"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relations
    users                = relationship("User", back_populates="department")
    problem_dependencies = relationship("ProblemDependency", back_populates="department")


# ─── TABLE : users ────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, server_default=func.now())
    last_login    = Column(DateTime, nullable=True)

    # Relations
    department          = relationship("Department", back_populates="users")
    reports             = relationship("Report", back_populates="author")
    executive_summaries = relationship("ExecutiveSummary", back_populates="generated_by_user")


# ─── TABLE : reports ─────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id             = Column(Integer, primary_key=True, index=True)
    submitted_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_number    = Column(Integer, nullable=False)
    year           = Column(Integer, nullable=False)
    global_summary = Column(Text, nullable=False)
    created_at     = Column(DateTime, server_default=func.now())

    # Relations
    author   = relationship("User", back_populates="reports")
    problems = relationship("Problem", back_populates="report", cascade="all, delete-orphan")


# ─── TABLE : problems ────────────────────────────────────

class Problem(Base):
    __tablename__ = "problems"

    id                   = Column(Integer, primary_key=True, index=True)
    report_id            = Column(Integer, ForeignKey("reports.id"), nullable=False)
    description          = Column(Text, nullable=False)
    cleaned_description  = Column(Text, nullable=True)
    type                 = Column(Enum(ProblemType), nullable=False)
    impact               = Column(SmallInteger, nullable=False)
    urgency              = Column(SmallInteger, nullable=False)
    repetitions          = Column(SmallInteger, default=1)
    criticality_score    = Column(Float, nullable=True)
    alert_sent           = Column(Boolean, default=False)
    probable_responsible = Column(String(255), nullable=True)
    cluster_id           = Column(Integer, nullable=True)
    created_at           = Column(DateTime, server_default=func.now())

    # Relations
    report       = relationship("Report", back_populates="problems")
    dependencies = relationship("ProblemDependency", back_populates="problem", cascade="all, delete-orphan")


# ─── TABLE : problem_dependencies ────────────────────────

class ProblemDependency(Base):
    __tablename__ = "problem_dependencies"

    problem_id              = Column(Integer, ForeignKey("problems.id"), primary_key=True)
    dependent_department_id = Column(Integer, ForeignKey("departments.id"), primary_key=True)
    created_at              = Column(DateTime, server_default=func.now())
    resolved_at             = Column(DateTime, nullable=True)

    # Relations
    problem    = relationship("Problem", back_populates="dependencies")
    department = relationship("Department", back_populates="problem_dependencies")


# ─── TABLE : executive_summaries ─────────────────────────

class ExecutiveSummary(Base):
    __tablename__ = "executive_summaries"

    id           = Column(Integer, primary_key=True, index=True)
    week_number  = Column(Integer, nullable=False)
    year         = Column(Integer, nullable=False)
    content      = Column(Text, nullable=False)
    model_used   = Column(String(100), nullable=True)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, server_default=func.now())

    # Relations
    generated_by_user = relationship("User", back_populates="executive_summaries")