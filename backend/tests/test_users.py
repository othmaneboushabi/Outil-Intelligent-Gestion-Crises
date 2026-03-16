import pytest


# ─── TESTS CRÉER USER ────────────────────────────────────

def test_create_user_success(client, auth_headers_admin, test_department):
    """Admin crée un user"""
    resp = client.post("/users",
        json = {
            "full_name"    : "New User",
            "email"        : "newuser@test.com",
            "password"     : "Test1234",
            "role"         : "user",
            "department_id": test_department["id"]
        },
        headers = auth_headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "newuser@test.com"


def test_create_user_duplicate_email(client, auth_headers_admin, test_department):
    """Email dupliqué → 400"""
    payload = {
        "full_name"    : "Dup",
        "email"        : "dup2@test.com",
        "password"     : "Test1234",
        "role"         : "user",
        "department_id": test_department["id"]
    }
    client.post("/users", json=payload, headers=auth_headers_admin)
    resp = client.post("/users", json=payload, headers=auth_headers_admin)
    assert resp.status_code == 400


def test_create_user_unauthorized(client, auth_headers_user, test_department):
    """User ne peut pas créer d'autres users → 403"""
    resp = client.post("/users",
        json = {
            "full_name"    : "Unauth",
            "email"        : "unauth@test.com",
            "password"     : "Test1234",
            "role"         : "user",
            "department_id": test_department["id"]
        },
        headers = auth_headers_user
    )
    assert resp.status_code == 403


# ─── TESTS LISTER USERS ──────────────────────────────────

def test_get_all_users_admin(client, auth_headers_admin):
    """Admin liste tous les users"""
    resp = client.get("/users", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_users_unauthorized(client, auth_headers_user):
    """User ne peut pas lister les users → 403"""
    resp = client.get("/users", headers=auth_headers_user)
    assert resp.status_code == 403


# ─── TESTS MODIFIER USER ─────────────────────────────────

def test_update_user_success(client, auth_headers_admin, test_department):
    """Admin modifie un user"""
    resp = client.post("/users",
        json = {
            "full_name"    : "To Update",
            "email"        : "update@test.com",
            "password"     : "Test1234",
            "role"         : "user",
            "department_id": test_department["id"]
        },
        headers = auth_headers_admin
    )
    user_id = resp.json()["id"]
    update  = client.put(f"/users/{user_id}",
        json    = {"full_name": "Updated Name"},
        headers = auth_headers_admin
    )
    assert update.status_code == 200
    assert update.json()["full_name"] == "Updated Name"


# ─── TESTS TOGGLE USER ───────────────────────────────────

def test_toggle_user(client, auth_headers_admin, user_token, test_department):
    """Toggle user actif/inactif"""
    users = client.get("/users", headers=auth_headers_admin).json()
    user  = next(u for u in users if u["role"] == "user")
    resp  = client.patch(
        f"/users/{user['id']}/toggle",
        headers = auth_headers_admin
    )
    assert resp.status_code == 200


def test_toggle_admin_forbidden(client, auth_headers_admin):
    """Toggle admin → 403"""
    users    = client.get("/users", headers=auth_headers_admin).json()
    admin    = next(u for u in users if u["role"] == "admin")
    resp     = client.patch(
        f"/users/{admin['id']}/toggle",
        headers = auth_headers_admin
    )
    assert resp.status_code == 403


def test_toggle_not_found(client, auth_headers_admin):
    """User inexistant → 404"""
    resp = client.patch("/users/9999/toggle", headers=auth_headers_admin)
    assert resp.status_code == 404