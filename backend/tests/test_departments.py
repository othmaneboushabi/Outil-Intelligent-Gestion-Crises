# ─── TESTS DÉPARTEMENTS ───────────────────────────────────

class TestCreateDepartment:

    def test_create_success(self, client, admin_token):
        """Création département réussie"""
        resp = client.post("/departments", json={
            "name"       : "Finance",
            "description": "Département Finance"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Finance"

    def test_create_duplicate(self, client, admin_token):
        """Département déjà existant → 400"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        client.post("/departments", json={
            "name": "Doublon", "description": ""
        }, headers=headers)
        resp = client.post("/departments", json={
            "name": "Doublon", "description": ""
        }, headers=headers)
        assert resp.status_code == 400

    def test_create_unauthorized(self, client, user_token):
        """User normal ne peut pas créer → 403"""
        resp = client.post("/departments", json={
            "name": "Interdit", "description": ""
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403

    def test_create_no_token(self, client):
        """Sans token → 401"""
        resp = client.post("/departments", json={
            "name": "SansToken", "description": ""
        })
        assert resp.status_code == 401


class TestGetDepartments:

    def test_get_all(self, client, admin_token):
        """GET /departments → liste"""
        resp = client.get(
            "/departments",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_authenticated(self, client, user_token):
        """User normal peut voir les départements"""
        resp = client.get(
            "/departments",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert resp.status_code == 200


class TestSoftDelete:

    def test_soft_delete_with_users(self, client, admin_token, user_token):
        """Département avec users → archivé (soft delete)"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Créer département
        resp = client.post("/departments", json={
            "name": "A Archiver", "description": ""
        }, headers=headers)
        dept_id = resp.json()["id"]

        # Créer user lié à ce département
        client.post("/users", json={
            "full_name"    : "User Lié",
            "email"        : "userlie@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": dept_id
        }, headers=headers)

        # Supprimer → doit archiver
        del_resp = client.delete(
            f"/departments/{dept_id}",
            headers=headers
        )
        assert del_resp.status_code == 200
        result = del_resp.json()
        assert result["archived"] == True

    def test_hard_delete_empty(self, client, admin_token):
        """Département vide → suppression physique"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Créer département vide
        resp = client.post("/departments", json={
            "name": "Vide", "description": ""
        }, headers=headers)
        dept_id = resp.json()["id"]

        # Supprimer → suppression physique
        del_resp = client.delete(
            f"/departments/{dept_id}",
            headers=headers
        )
        assert del_resp.status_code == 200
        result = del_resp.json()
        assert result["archived"] == False

    def test_delete_not_found(self, client, admin_token):
        """Département inexistant → 404"""
        resp = client.delete(
            "/departments/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 404