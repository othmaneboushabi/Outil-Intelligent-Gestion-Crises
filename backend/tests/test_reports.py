import pytest


# ─── PAYLOAD RAPPORT ─────────────────────────────────────

def make_report(week=1, year=2026, dept_ids=None):
    return {
        "week_number"   : week,
        "year"          : year,
        "global_summary": "Résumé test semaine",
        "problems"      : [
            {
                "description"             : "Problème technique critique serveur tombé",
                "type"                    : "technique",
                "impact"                  : 5,
                "urgency"                 : 5,
                "repetitions"             : 3,
                "dependent_department_ids": dept_ids or []
            }
        ]
    }


# ─── TESTS SOUMETTRE RAPPORT ─────────────────────────────

def test_submit_report_success(client, auth_headers_user):
    """User soumet un rapport avec succès"""
    resp = client.post("/reports",
        json    = make_report(week=1),
        headers = auth_headers_user
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["week_number"] == 1
    assert len(data["problems"]) == 1


def test_submit_report_nlp_processed(client, auth_headers_user):
    """Pipeline NLP déclenché automatiquement"""
    resp = client.post("/reports",
        json    = make_report(week=2),
        headers = auth_headers_user
    )
    assert resp.status_code == 200
    problem = resp.json()["problems"][0]
    assert problem["criticality_score"] is not None
    assert problem["criticality_score"] > 0


def test_submit_report_duplicate_week(client, auth_headers_user):
    """Rapport dupliqué même semaine → 400"""
    client.post("/reports", json=make_report(week=3), headers=auth_headers_user)
    resp = client.post("/reports", json=make_report(week=3), headers=auth_headers_user)
    assert resp.status_code == 400


def test_submit_report_invalid_week(client, auth_headers_user):
    """Semaine invalide (>52) → 422"""
    resp = client.post("/reports",
        json    = make_report(week=60),
        headers = auth_headers_user
    )
    assert resp.status_code == 422


def test_submit_report_with_dependencies(client, auth_headers_user, auth_headers_admin):
    """Rapport avec dépendances"""
    dept = client.post("/departments",
        json    = {"name": "Dept Dep"},
        headers = auth_headers_admin
    ).json()
    resp = client.post("/reports",
        json    = make_report(week=4, dept_ids=[dept["id"]]),
        headers = auth_headers_user
    )
    assert resp.status_code == 200
    deps = resp.json()["problems"][0]["dependencies"]
    assert len(deps) == 1


# ─── TESTS LISTER RAPPORTS ───────────────────────────────

def test_get_reports_user_own(client, auth_headers_user):
    """User voit uniquement ses rapports"""
    client.post("/reports", json=make_report(week=5), headers=auth_headers_user)
    resp = client.get("/reports", headers=auth_headers_user)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_reports_admin_all(client, auth_headers_admin, auth_headers_user):
    """Admin voit tous les rapports"""
    client.post("/reports", json=make_report(week=6), headers=auth_headers_user)
    resp = client.get("/reports", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_report_by_id(client, auth_headers_user, auth_headers_admin):
    """Récupérer rapport par ID"""
    created = client.post("/reports",
        json    = make_report(week=7),
        headers = auth_headers_user
    ).json()
    resp = client.get(f"/reports/{created['id']}", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_report_not_found(client, auth_headers_admin):
    """Rapport inexistant → 404"""
    resp = client.get("/reports/9999", headers=auth_headers_admin)
    assert resp.status_code == 404


# ─── TESTS ANALYZE ───────────────────────────────────────

def test_analyze_endpoint(client, auth_headers_user):
    """Analyse IA en temps réel"""
    resp = client.post("/analyze",
        json = {
            "description"    : "Karim Benali a bloqué le serveur depuis lundi",
            "impact"         : 5,
            "urgency"        : 5,
            "repetitions"    : 3,
            "nb_dependencies": 2,
            "week_number"    : 1,
            "year"           : 2026
        },
        headers = auth_headers_user
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "criticality_score"    in data
    assert "probable_responsible" in data
    assert "entities"             in data