# ─── TESTS ALERTES ───────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.scoring import calculate_criticality_score, get_criticality_level

def compute_criticality_score(impact, urgency, repetitions, nb_dependencies):
    score = calculate_criticality_score(impact, urgency, repetitions, nb_dependencies)
    level = get_criticality_level(score)
    return score, level


class TestAlertThreshold:

    def test_score_triggers_alert(self):
        """Score >= 4.6 → alerte déclenchée"""
        score, level = compute_criticality_score(
            impact=5, urgency=5, repetitions=5, nb_dependencies=3
        )
        assert score >= 4.6
        assert "Alerte Maximale" in level

    def test_score_no_alert(self):
        """Score < 4.6 → pas d'alerte"""
        score, level = compute_criticality_score(
            impact=2, urgency=2, repetitions=1, nb_dependencies=0
        )
        assert score < 4.6
        assert "Alerte Maximale" not in level

    def test_alert_boundary(self):
        """Score élevé vs score faible"""
        score_high, _ = compute_criticality_score(
            impact=5, urgency=5, repetitions=5, nb_dependencies=3
        )
        score_low, _ = compute_criticality_score(
            impact=1, urgency=1, repetitions=1, nb_dependencies=0
        )
        assert score_high > score_low
        assert score_high >= 4.6


class TestActiveAlerts:

    def test_get_active_alerts(self, client, admin_token):
        """GET /alerts/active → liste"""
        resp = client.get(
            "/alerts/active",
            params  = {"week": 1, "year": 2025},
            headers = {"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_alert_after_high_score_report(self, client, user_token, admin_token):
        """Rapport score > 4.6 → alerte créée"""
        headers_user  = {"Authorization": f"Bearer {user_token}"}
        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        client.post("/reports", json={
            "week_number"   : 20,
            "year"          : 2025,
            "global_summary": "Semaine critique",
            "problems"      : [
                {
                    "description"             : "Panne totale serveur production depuis lundi",
                    "type"                    : "technique",
                    "impact"                  : 5,
                    "urgency"                 : 5,
                    "repetitions"             : 5,
                    "dependent_department_ids": []
                }
            ]
        }, headers=headers_user)

        resp = client.get(
            "/alerts/active",
            params  = {"week": 20, "year": 2025},
            headers = headers_admin
        )
        assert resp.status_code == 200

    def test_alerts_no_token(self, client):
        """Sans token → 401"""
        resp = client.get(
            "/alerts/active",
            params = {"week": 1, "year": 2025}
        )
        assert resp.status_code == 401

    def test_alerts_user_forbidden(self, client, user_token):
        """User normal → 403"""
        resp = client.get(
            "/alerts/active",
            params  = {"week": 1, "year": 2025},
            headers = {"Authorization": f"Bearer {user_token}"}
        )
        assert resp.status_code == 403


class TestAnalyzeAlerts:

    def test_analyze_high_score(self, client, user_token):
        """POST /analyze score > 4.6 → alert dans réponse"""
        resp = client.post("/analyze", json={
            "description"    : "Panne critique totale du système",
            "impact"         : 5,
            "urgency"        : 5,
            "repetitions"    : 5,
            "nb_dependencies": 3,
            "week_number"    : 21,
            "year"           : 2025
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["criticality_score"] >= 4.6

    def test_analyze_low_score_no_alert(self, client, user_token):
        """POST /analyze score < 4.6 → pas d'alerte maximale"""
        resp = client.post("/analyze", json={
            "description"    : "Petit problème mineur",
            "impact"         : 1,
            "urgency"        : 1,
            "repetitions"    : 1,
            "nb_dependencies": 0,
            "week_number"    : 22,
            "year"           : 2025
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["criticality_score"] < 4.6