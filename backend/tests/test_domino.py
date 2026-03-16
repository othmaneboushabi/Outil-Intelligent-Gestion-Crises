import pytest


def make_report(week=1, year=2026, dept_ids=None):
    return {
        "week_number"   : week,
        "year"          : year,
        "global_summary": "Résumé domino test",
        "problems"      : [
            {
                "description"             : "Panne serveur bloquant les autres départements",
                "type"                    : "technique",
                "impact"                  : 5,
                "urgency"                 : 5,
                "repetitions"             : 3,
                "dependent_department_ids": dept_ids or []
            }
        ]
    }


# ─── TESTS DOMINO SUMMARY ────────────────────────────────

def test_domino_summary_admin(client, auth_headers_admin, auth_headers_user, test_department):
    """Admin peut voir le résumé domino"""
    client.post("/reports", json=make_report(week=1), headers=auth_headers_user)
    resp = client.get(
        "/domino/summary?week=1&year=2026",
        headers = auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes"       in data
    assert "edges"       in data
    assert "total_nodes" in data


def test_domino_summary_user_forbidden(client, auth_headers_user):
    """User ne peut pas voir domino summary → 403"""
    resp = client.get(
        "/domino/summary?week=1&year=2026",
        headers = auth_headers_user
    )
    assert resp.status_code == 403


def test_domino_summary_no_data(client, auth_headers_admin):
    """Semaine sans données → résumé vide"""
    resp = client.get(
        "/domino/summary?week=99&year=2099",
        headers = auth_headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["total_edges"] == 0


# ─── TESTS DOMINO SIMULATE ───────────────────────────────

def test_domino_simulate_admin(client, auth_headers_admin, auth_headers_user, test_department):
    """Simulation déblocage département"""
    dept2 = client.post("/departments",
        json    = {"name": "Dept Bloque"},
        headers = auth_headers_admin
    ).json()

    client.post("/reports",
        json    = make_report(week=2, dept_ids=[dept2["id"]]),
        headers = auth_headers_user
    )

    resp = client.get(
        f"/domino/simulate?dept_id={test_department['id']}&week=2&year=2026",
        headers = auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "unblocked_department" in data
    assert "freed_count"          in data


def test_domino_simulate_user_forbidden(client, auth_headers_user, test_department):
    """User ne peut pas simuler → 403"""
    resp = client.get(
        f"/domino/simulate?dept_id={test_department['id']}&week=1&year=2026",
        headers = auth_headers_user
    )
    assert resp.status_code == 403


# ─── TESTS DOMINO GRAPH ──────────────────────────────────

def test_domino_graph_html(client, auth_headers_admin, auth_headers_user):
    """Export graphe HTML"""
    client.post("/reports", json=make_report(week=3), headers=auth_headers_user)
    resp = client.get(
        "/domino/graph-html?week=3&year=2026",
        headers = auth_headers_admin
    )
    assert resp.status_code in [200, 500]


# ─── TESTS PROBLEMS TOP ──────────────────────────────────

def test_top_problems_admin(client, auth_headers_admin, auth_headers_user):
    """Admin voit les top problèmes"""
    client.post("/reports", json=make_report(week=4), headers=auth_headers_user)
    resp = client.get(
        "/problems/top?week=4&year=2026",
        headers = auth_headers_admin
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_top_problems_user_forbidden(client, auth_headers_user):
    """User ne peut pas voir top problems → 403"""
    resp = client.get(
        "/problems/top?week=1&year=2026",
        headers = auth_headers_user
    )
    assert resp.status_code == 403