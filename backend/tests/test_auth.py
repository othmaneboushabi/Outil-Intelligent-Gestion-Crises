# ─── TESTS AUTH ──────────────────────────────────────────

class TestRegister:

    def test_register_success(self, client):
        """Inscription réussie"""
        resp = client.post("/auth/register", json={
            "full_name"    : "Nouveau User",
            "email"        : "nouveau@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "nouveau@crisis.com"
        assert data["full_name"] == "Nouveau User"
        assert "password" not in data

    def test_register_duplicate_email(self, client):
        """Email déjà existant → 400"""
        client.post("/auth/register", json={
            "full_name"    : "User A",
            "email"        : "duplicate@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        })
        resp = client.post("/auth/register", json={
            "full_name"    : "User B",
            "email"        : "duplicate@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        })
        assert resp.status_code == 400

    def test_register_missing_fields(self, client):
        """Champs manquants → 422"""
        resp = client.post("/auth/register", json={
            "email": "incomplet@crisis.com"
        })
        assert resp.status_code == 422


class TestLogin:

    def test_login_success(self, client):
        """Login réussi → token JWT"""
        client.post("/auth/register", json={
            "full_name"    : "Login User",
            "email"        : "login@crisis.com",
            "password"     : "Password123",
            "role"         : "user",
            "department_id": None
        })
        resp = client.post("/auth/login", data={
            "username": "login@crisis.com",
            "password": "Password123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        """Mauvais mot de passe → 401"""
        client.post("/auth/register", json={
            "full_name"    : "Wrong Pass",
            "email"        : "wrongpass@crisis.com",
            "password"     : "CorrectPass123",
            "role"         : "user",
            "department_id": None
        })
        resp = client.post("/auth/login", data={
            "username": "wrongpass@crisis.com",
            "password": "MauvaisPass"
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        """Email inconnu → 401"""
        resp = client.post("/auth/login", data={
            "username": "inconnu@crisis.com",
            "password": "Password123"
        })
        assert resp.status_code == 401


class TestMe:

    def test_get_me_success(self, client, admin_token):
        """GET /auth/me → infos utilisateur connecté"""
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert "role" in data

    def test_get_me_no_token(self, client):
        """Sans token → 401"""
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Token invalide → 401"""
        resp = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer token_invalide"}
        )
        assert resp.status_code == 401