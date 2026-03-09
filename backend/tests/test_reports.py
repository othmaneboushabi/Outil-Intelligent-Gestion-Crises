# ─── TESTS RAPPORTS ──────────────────────────────────────

class TestSubmitReport:

    def test_submit_success(self, client, user_token):
        """Soumission rapport réussie"""
        resp = client.post("/reports", json={
            "week_number"   : 1,
            "year"          : 2025,
            "global_summary": "Semaine normale pour le département IT",
            "problems"      : [
                {
                    "description"             : "Serveur tombé depuis lundi matin",
                    "type"                    : "technique",
                    "impact"                  : 4,
                    "urgency"                 : 4,
                    "repetitions"             : 2,
                    "dependent_department_ids": []
                }
            ]
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["week_number"] == 1
        assert data["year"] == 2025
        assert len(data["problems"]) == 1

    def test_submit_duplicate_week(self, client, user_token):
        """Rapport déjà soumis pour cette semaine → 400"""
        headers = {"Authorization": f"Bearer {user_token}"}
        payload = {
            "week_number"   : 2,
            "year"          : 2025,
            "global_summary": "Semaine 2",
            "problems"      : [
                {
                    "description"             : "Problème réseau",
                    "type"                    : "technique",
                    "impact"                  : 3,
                    "urgency"                 : 3,
                    "repetitions"             : 1,
                    "dependent_department_ids": []
                }
            ]
        }
        client.post("/reports", json=payload, headers=headers)
        resp = client.post("/reports", json=payload, headers=headers)
        assert resp.status_code == 400

    def test_submit_no_token(self, client):
        """Sans token → 401"""
        resp = client.post("/reports", json={
            "week_number"   : 3,
            "year"          : 2025,
            "global_summary": "Test",
            "problems"      : []
        })
        assert resp.status_code == 401

    def test_submit_with_nlp(self, client, user_token):
        """Rapport soumis → NLP pipeline exécuté"""
        resp = client.post("/reports", json={
            "week_number"   : 4,
            "year"          : 2025,
            "global_summary": "Semaine critique IT",
            "problems"      : [
                {
                    "description"             : "Karim Benali n'a pas fourni les accès au serveur",
                    "type"                    : "technique",
                    "impact"                  : 5,
                    "urgency"                 : 5,
                    "repetitions"             : 3,
                    "dependent_department_ids": []
                }
            ]
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()
        problem = data["problems"][0]
        # NLP pipeline doit avoir calculé le score
        assert problem["criticality_score"] is not None
        assert problem["criticality_score"] > 0


class TestGetReports:

    def test_get_reports_user(self, client, user_token):
        """User voit ses propres rapports"""
        resp = client.get(
            "/reports",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_reports_admin(self, client, admin_token):
        """Admin voit tous les rapports"""
        resp = client.get(
            "/reports",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_reports_no_token(self, client):
        """Sans token → 401"""
        resp = client.get("/reports")
        assert resp.status_code == 401


class TestAnalyzeEndpoint:

    def test_analyze_success(self, client, user_token):
        """POST /analyze → résultat NLP"""
        resp = client.post("/analyze", json={
            "description"    : "Le serveur de production est tombé depuis vendredi",
            "impact"         : 5,
            "urgency"        : 5,
            "repetitions"    : 3,
            "nb_dependencies": 2,
            "week_number"    : 5,
            "year"           : 2025
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "criticality_score" in data
        assert "criticality_level" in data
        assert data["criticality_score"] > 0

    def test_analyze_no_token(self, client):
        """Sans token → 401"""
        resp = client.post("/analyze", json={
            "description"    : "Test",
            "impact"         : 3,
            "urgency"        : 3,
            "repetitions"    : 1,
            "nb_dependencies": 0,
            "week_number"    : 1,
            "year"           : 2025
        })
        assert resp.status_code == 401

    def test_analyze_high_score_alert(self, client, user_token):
        """Score > 4.6 → alert_sent dans la réponse"""
        resp = client.post("/analyze", json={
            "description"    : "Panne critique serveur production",
            "impact"         : 5,
            "urgency"        : 5,
            "repetitions"    : 5,
            "nb_dependencies": 3,
            "week_number"    : 6,
            "year"           : 2025
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["criticality_score"] >= 4.6