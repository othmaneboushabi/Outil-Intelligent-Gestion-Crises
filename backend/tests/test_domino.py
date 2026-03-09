# ─── TESTS DOMINO ────────────────────────────────────────

class TestDominoSummary:

    def test_domino_summary_admin(self, client, admin_token):
        """Admin peut accéder au résumé domino"""
        resp = client.get(
            "/domino/summary",
            params  = {"week": 3, "year": 2025},
            headers = {"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "total_edges" in data

    def test_domino_summary_no_token(self, client):
        """Sans token → 401"""
        resp = client.get(
            "/domino/summary",
            params = {"week": 3, "year": 2025}
        )
        assert resp.status_code == 401

    def test_domino_summary_user_forbidden(self, client, user_token):
        """User normal → 403"""
        resp = client.get(
            "/domino/summary",
            params  = {"week": 3, "year": 2025},
            headers = {"Authorization": f"Bearer {user_token}"}
        )
        assert resp.status_code == 403


class TestDominoSimulate:

    def test_simulate_existing_dept(self, client, admin_token, user_token):
        """Simulation domino depuis département IT"""
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        headers_user  = {"Authorization": f"Bearer {user_token}"}

        depts_resp = client.get("/departments", headers=headers_admin)
        depts = depts_resp.json()

        if len(depts) >= 2:
            dept_id = depts[0]["id"]
            client.post("/reports", json={
                "week_number"   : 10,
                "year"          : 2025,
                "global_summary": "Test domino",
                "problems"      : [
                    {
                        "description"             : "Panne serveur critique",
                        "type"                    : "technique",
                        "impact"                  : 5,
                        "urgency"                 : 5,
                        "repetitions"             : 3,
                        "dependent_department_ids": [depts[1]["id"]]
                    }
                ]
            }, headers=headers_user)

            resp = client.get(
                "/domino/simulate",
                params  = {"dept_id": dept_id, "week": 10, "year": 2025},
                headers = headers_admin
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "impacted_departments" in data

    def test_simulate_no_token(self, client):
        """Sans token → 401"""
        resp = client.get(
            "/domino/simulate",
            params = {"dept_id": 1, "week": 3, "year": 2025}
        )
        assert resp.status_code == 401


class TestDominoGraph:

    def test_graph_html_admin(self, client, admin_token):
        """Admin peut accéder au graphe HTML"""
        resp = client.get(
            "/domino/graph-html",
            params  = {"week": 3, "year": 2025},
            headers = {"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200

    def test_graph_html_no_token(self, client):
        """Sans token → 401"""
        resp = client.get(
            "/domino/graph-html",
            params = {"week": 3, "year": 2025}
        )
        assert resp.status_code == 401


class TestDominoAlerts:

    def test_alerts_active(self, client, admin_token):
        """GET /alerts/active → liste des alertes"""
        resp = client.get(
            "/alerts/active",
            params  = {"week": 3, "year": 2025},
            headers = {"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_alerts_no_token(self, client):
        """Sans token → 401"""
        resp = client.get(
            "/alerts/active",
            params = {"week": 3, "year": 2025}
        )
        assert resp.status_code == 401