from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── ÉNUMÉRATIONS ────────────────────────────────────────

class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class ProblemType(str, Enum):
    technique = "technique"
    humain = "humain"
    financier = "financier"
    logistique = "logistique"
    autre = "autre"


# ─── DEPARTMENT SCHEMAS ───────────────────────────────────

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── USER SCHEMAS ─────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.user
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── AUTH SCHEMAS ─────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    full_name: str
    department_id: Optional[int] = None


# ─── PROBLEM DEPENDENCY SCHEMAS ───────────────────────────

class ProblemDependencyCreate(BaseModel):
    dependent_department_id: int

class ProblemDependencyResponse(BaseModel):
    problem_id: int
    dependent_department_id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── PROBLEM SCHEMAS ──────────────────────────────────────

class ProblemBase(BaseModel):
    description: str
    type: ProblemType
    impact: int
    urgency: int
    repetitions: int = 1
    dependent_department_ids: List[int] = []

    @field_validator('impact', 'urgency')
    def validate_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('La valeur doit être entre 1 et 5')
        return v

class ProblemCreate(ProblemBase):
    pass

class ProblemResponse(BaseModel):
    id: int
    report_id: int
    description: str
    cleaned_description: Optional[str] = None
    type: ProblemType
    impact: int
    urgency: int
    repetitions: int
    criticality_score: Optional[float] = None
    alert_sent: bool
    probable_responsible: Optional[str] = None
    cluster_id: Optional[int] = None
    created_at: datetime
    dependencies: List[ProblemDependencyResponse] = []

    model_config = {"from_attributes": True}


# ─── REPORT SCHEMAS ───────────────────────────────────────

class ReportBase(BaseModel):
    week_number: int
    year: int
    global_summary: str

    @field_validator('week_number')
    def validate_week(cls, v):
        if not 1 <= v <= 52:
            raise ValueError('Le numéro de semaine doit être entre 1 et 52')
        return v

class ReportCreate(ReportBase):
    problems: List[ProblemCreate]

class ReportUpdate(BaseModel):
    global_summary: Optional[str] = None
    problems: Optional[List[ProblemCreate]] = None

class ReportResponse(ReportBase):
    id: int
    submitted_by: int
    created_at: datetime
    problems: List[ProblemResponse] = []

    model_config = {"from_attributes": True}


# ─── EXECUTIVE SUMMARY SCHEMAS ────────────────────────────

class ExecutiveSummaryResponse(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}

    id: int
    week_number: int
    year: int
    content: str
    model_used: Optional[str] = None
    generated_by: int
    generated_at: datetime


# ─── ALERT SCHEMAS ────────────────────────────────────────

class AlertResponse(BaseModel):
    problem_id: int
    description: str
    criticality_score: float
    department_name: str
    probable_responsible: Optional[str] = None
    dependent_departments: List[str] = []