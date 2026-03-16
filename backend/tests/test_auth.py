import pytest


def test_register_success(client, test_department):
    """Inscription réussie d'un user"""
    resp = client.post("/auth/register", json={
        "full_name"    : "Test User",
        "email"        : "testuser@test.com",
        "password"     : "Test1234",
        "role"         : "user",
        "department_id": test_department["id"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"]     == "testuser@test.com"
    assert data["full_name"] == "Test User"
    assert data["role"]      == "user"
    assert data["is_active"] == True
    assert "password" not in data


def test_register_admin_no_dept(client):
    """Admin peut s'inscrire sans département"""
    resp = client.post("/auth/register", json={
        "full_name"    : "Admin2",
        "email"        : "admin2@test.com",
        "password"     : "Admin1234",
        "role"         : "admin",
        "department_id": None
    })
    assert resp.status_code == 200


def test_register_user_no_dept(client):
    """User sans département → 422"""
    resp = client.post("/auth/register", json={
        "full_name"    : "No Dept",
        "email"        : "nodept@test.com",
        "password"     : "Test1234",
        "role"         : "user",
        "department_id": None
    })
    assert resp.status_code == 422


def test_register_duplicate_email(client, test_department):
    """Email déjà utilisé → 400"""
    payload = {
        "full_name"    : "Dup",
        "email"        : "dup@test.com",
        "password"     : "Test1234",
        "role"         : "user",
        "department_id": test_department["id"]
    }
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_register_short_password(client, test_department):
    """Mot de passe trop court → 422"""
    resp = client.post("/auth/register", json={
        "full_name"    : "Short",
        "email"        : "short@test.com",
        "password"     : "123",
        "role"         : "user",
        "department_id": test_department["id"]
    })
    assert resp.status_code == 422


def test_login_success(client, admin_token):
    """Login admin réussi — utilise le bon email du conftest"""
    resp = client.post("/auth/login",
        data={"username": "admin_test@crisis.com", "password": "Admin1234"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"]       == "admin"


def test_login_wrong_password(client, admin_token):
    """Mauvais mot de passe → 401"""
    resp = client.post("/auth/login",
        data={"username": "admin_test@crisis.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_unknown_email(client):
    """Email inconnu → 401"""
    resp = client.post("/auth/login",
        data={"username": "unknown@test.com", "password": "Test1234"}
    )
    assert resp.status_code == 401


def test_get_me(client, admin_token):
    """GET /auth/me retourne le profil de l'admin connecté"""
    resp = client.get("/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin_test@crisis.com"
    assert data["role"]  == "admin"