import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
import sys
import os

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ─── BASE DE DONNÉES DE TEST ─────────────────────────────
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

@pytest.fixture(scope="session")
def db():
    """Base de données de test — SQLite en mémoire"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Client HTTP de test"""
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
    # Créer admin
    client.post("/auth/register", json={
        "full_name" : "Admin Test",
        "email"     : "admin_test@crisis.com",
        "password"  : "Admin1234",
        "role"      : "admin",
        "department_id": None
    })
    # Login
    resp = client.post("/auth/login", data={
        "username": "admin_test@crisis.com",
        "password": "Admin1234"
    })
    return resp.json()["access_token"]

@pytest.fixture(scope="function")
def user_token(client, admin_token):
    """Crée un département + user et retourne son token"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Créer département IT
    client.post("/departments", json={
        "name"       : "IT",
        "description": "Département IT"
    }, headers=headers)

    # Créer user
    client.post("/users", json={
        "full_name"    : "User Test",
        "email"        : "user_test@crisis.com",
        "password"     : "User1234",
        "role"         : "user",
        "department_id": 1
    }, headers=headers)

    # Login
    resp = client.post("/auth/login", data={
        "username": "user_test@crisis.com",
        "password": "User1234"
    })
    return resp.json()["access_token"]