import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, get_db
import models  # ← IMPORTANT : importer tous les modèles avant create_all
from main import app

# ─── CONFIGURATION BASE DE TEST ──────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ─── FIXTURES ────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """
    Base de données de test — SQLite fichier
    Créée avant chaque test, supprimée après
    """
    # S'assurer que tous les modèles sont chargés
    from models import (
        User, Department, Report, Problem,
        ProblemDependency, ExecutiveSummary
    )
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Client HTTP de test avec base de données isolée"""
    def override_get_db():
        try:
            db_session = TestingSessionLocal()
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token(client):
    """Crée un admin et retourne son token"""
    client.post("/auth/register", json={
        "full_name"    : "Admin Test",
        "email"        : "admin_test@crisis.com",
        "password"     : "Admin1234",
        "role"         : "admin",
        "department_id": None
    })
    resp = client.post("/auth/login", data={
        "username": "admin_test@crisis.com",
        "password": "Admin1234"
    })
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def test_department(client, admin_token):
    """Crée un département de test et retourne ses données"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/departments", json={
        "name"       : "IT Test",
        "description": "Département IT Test"
    }, headers=headers)
    return resp.json()


@pytest.fixture(scope="function")
def user_token(client, admin_token, test_department):
    """Crée un user et retourne son token"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    dept_id = test_department["id"]  # ← ID dynamique

    client.post("/users", json={
        "full_name"    : "User Test",
        "email"        : "user_test@crisis.com",
        "password"     : "User1234",
        "role"         : "user",
        "department_id": dept_id
    }, headers=headers)

    resp = client.post("/auth/login", data={
        "username": "user_test@crisis.com",
        "password": "User1234"
    })
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers_admin(admin_token):
    """Headers avec token admin"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def auth_headers_user(user_token):
    """Headers avec token user"""
    return {"Authorization": f"Bearer {user_token}"}