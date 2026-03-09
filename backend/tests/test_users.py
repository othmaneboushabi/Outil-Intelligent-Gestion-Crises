# ─── TESTS UTILISATEURS ──────────────────────────────────

class TestCreateUser:

    def test_create_success(self, client, admin_token):
        """Création utilisateur réussie"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Créer département
        dept_resp = client.post("/departments", json={
            "name": "RH", "description": "Département RH"
        }, headers=headers)
        dept_id = dept_resp.json()["id"]

        resp = client.post("/users", json={
            "full_name"    : "Karim Benali",
            "email"        : "karim@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": dept_id
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "karim@crisis.com"
        assert data["full_name"] == "Karim Benali"
        assert data["is_active"] == True

    def test_create_duplicate_email(self, client, admin_token):
        """Email déjà existant → 400"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        client.post("/auth/register", json={
            "full_name"    : "Existant",
            "email"        : "existant@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        })
        resp = client.post("/users", json={
            "full_name"    : "Doublon",
            "email"        : "existant@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        }, headers=headers)
        assert resp.status_code == 400

    def test_create_unauthorized(self, client, user_token):
        """User normal ne peut pas créer → 403"""
        resp = client.post("/users", json={
            "full_name"    : "Interdit",
            "email"        : "interdit@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403


class TestGetUsers:

    def test_get_all_admin(self, client, admin_token):
        """Admin peut voir tous les users"""
        resp = client.get(
            "/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_unauthorized(self, client, user_token):
        """User normal ne peut pas voir la liste → 403"""
        resp = client.get(
            "/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert resp.status_code == 403

    def test_get_no_token(self, client):
        """Sans token → 401"""
        resp = client.get("/users")
        assert resp.status_code == 401


class TestToggleUser:

    def test_toggle_user(self, client, admin_token):
        """Toggle actif/inactif d'un user"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = client.post("/auth/register", json={
            "full_name"    : "Toggle User",
            "email"        : "toggle@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        })
        user_id = resp.json()["id"]

        # Toggle → désactiver
        toggle_resp = client.patch(
            f"/users/{user_id}/toggle",
            headers=headers
        )
        assert toggle_resp.status_code == 200

        # Toggle → réactiver
        toggle_resp2 = client.patch(
            f"/users/{user_id}/toggle",
            headers=headers
        )
        assert toggle_resp2.status_code == 200

    def test_toggle_admin_forbidden(self, client, admin_token):
        """Toggle sur un admin → 403"""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Récupérer l'id de l'admin
        me = client.get("/auth/me", headers=headers)
        admin_id = me.json()["id"]

        resp = client.patch(
            f"/users/{admin_id}/toggle",
            headers=headers
        )
        assert resp.status_code == 403

    def test_toggle_not_found(self, client, admin_token):
        """User inexistant → 404"""
        resp = client.patch(
            "/users/99999/toggle",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 404