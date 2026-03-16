import pytest


def test_create_department_success(client, auth_headers_admin):
    """Créer département — admin"""
    resp = client.post("/departments",
        json    = {"name": "Finance", "description": "Dept Finance"},
        headers = auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"]      == "Finance"
    assert data["is_active"] == True


def test_create_department_duplicate(client, auth_headers_admin):
    """Département dupliqué → 400"""
    client.post("/departments",
        json    = {"name": "RH"},
        headers = auth_headers_admin
    )
    resp = client.post("/departments",
        json    = {"name": "RH"},
        headers = auth_headers_admin
    )
    assert resp.status_code == 400


def test_create_department_unauthorized(client, auth_headers_user):
    """User ne peut pas créer département → 403"""
    resp = client.post("/departments",
        json    = {"name": "Marketing"},
        headers = auth_headers_user
    )
    assert resp.status_code == 403


def test_get_departments_admin(client, auth_headers_admin):
    """Admin peut lister les départements"""
    resp = client.get("/departments", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_departments_user(client, auth_headers_user):
    """User peut lister les départements"""
    resp = client.get("/departments", headers=auth_headers_user)
    assert resp.status_code == 200


def test_get_departments_unauthenticated(client):
    """Non authentifié → 401"""
    resp = client.get("/departments")
    assert resp.status_code == 401


def test_hard_delete_empty_department(client, auth_headers_admin):
    """Département vide → suppression physique"""
    resp = client.post("/departments",
        json    = {"name": "Empty Dept"},
        headers = auth_headers_admin
    )
    dept_id = resp.json()["id"]
    del_resp = client.delete(
        f"/departments/{dept_id}",
        headers = auth_headers_admin
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["archived"] == False


def test_soft_delete_department_with_users(client, auth_headers_admin, user_token):
    """
    Département avec user lié → soft delete (archivage)
    Le user_token crée automatiquement un user dans test_department
    On crée un nouveau dept avec un user lié
    """
    # Créer un nouveau département
    dept_resp = client.post("/departments",
        json    = {"name": "Dept To Archive"},
        headers = auth_headers_admin
    )
    dept_id = dept_resp.json()["id"]

    # Créer un user dans ce département
    client.post("/users",
        json = {
            "full_name"    : "User Archive",
            "email"        : "archive@test.com",
            "password"     : "Test1234",
            "role"         : "user",
            "department_id": dept_id
        },
        headers = auth_headers_admin
    )

    # Supprimer → doit archiver car user lié
    del_resp = client.delete(
        f"/departments/{dept_id}",
        headers = auth_headers_admin
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["archived"] == True


def test_delete_department_not_found(client, auth_headers_admin):
    """Département inexistant → 404"""
    resp = client.delete("/departments/9999", headers=auth_headers_admin)
    assert resp.status_code == 404