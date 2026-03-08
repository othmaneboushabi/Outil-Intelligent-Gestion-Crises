import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.get('token')}"}

def is_authenticated():
    return "token" in st.session_state and st.session_state["token"] is not None

def is_admin():
    return st.session_state.get("role") == "admin"

st.set_page_config(page_title="Dashboard Global", page_icon="📈", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté.")
    st.stop()

if not is_admin():
    st.error("❌ Accès réservé aux administrateurs.")
    st.stop()

st.markdown("# 📈 Dashboard Global")
st.markdown("---")

# Sélecteur semaine/année
col1, col2 = st.columns(2)
with col1:
    week = st.number_input("Semaine", min_value=1, max_value=52,
                           value=datetime.now().isocalendar()[1])
with col2:
    year = st.number_input("Année", min_value=2024, max_value=2030,
                           value=datetime.now().year)

st.markdown("---")

# ─── RÉCUPÉRER LES DONNÉES ───────────────────────────────

try:
    # Récupérer tous les rapports
    reports_resp = requests.get(
        f"{API_URL}/reports",
        headers = get_headers()
    )

    # Récupérer les alertes
    alerts_resp = requests.get(
        f"{API_URL}/alerts/active",
        headers = get_headers(),
        params  = {"week": week, "year": year}
    )

    # Récupérer le top problèmes
    top_resp = requests.get(
        f"{API_URL}/problems/top",
        headers = get_headers(),
        params  = {"week": week, "year": year, "limit": 5}
    )

    reports = reports_resp.json() if reports_resp.status_code == 200 else []
    alerts  = alerts_resp.json()  if alerts_resp.status_code == 200  else []
    tops    = top_resp.json()     if top_resp.status_code == 200     else []

    # Filtrer rapports par semaine
    week_reports = [
        r for r in reports
        if r["week_number"] == week and r["year"] == year
    ]

    # Calcul KPIs
    all_problems = []
    for r in week_reports:
        all_problems.extend(r.get("problems", []))

    total_problems = len(all_problems)
    scores = [p["criticality_score"] for p in all_problems if p["criticality_score"]]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0
    max_score = max(scores) if scores else 0
    nb_alerts = len(alerts)

    # ─── KPIs ────────────────────────────────────────────
    st.markdown("### 📊 Indicateurs Clés")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📋 Total Problèmes", total_problems)
    with col2:
        st.metric("⚡ Score Moyen", f"{avg_score}/5")
    with col3:
        st.metric("🔥 Score Maximum", f"{max_score}/5")
    with col4:
        st.metric("🚨 Alertes Actives", nb_alerts,
                  delta=f"{nb_alerts} critique(s)" if nb_alerts > 0 else None,
                  delta_color="inverse")

    st.markdown("---")

    # ─── JAUGE DE SANTÉ ──────────────────────────────────
    st.markdown("### 🏥 Santé de l'Organisation")

    health = 100 - (avg_score / 5 * 100)
    if health >= 70:
        color  = "🟢"
        status = "Bonne"
    elif health >= 40:
        color  = "🟡"
        status = "Modérée"
    else:
        color  = "🔴"
        status = "Critique"

    col1, col2 = st.columns([2, 1])
    with col1:
        st.progress(int(health) / 100)
    with col2:
        st.markdown(f"### {color} {status} ({int(health)}%)")

    st.markdown("---")

    # ─── TOP PROBLÈMES ────────────────────────────────────
    st.markdown("### 🔥 Top Problèmes Critiques")

    if not tops:
        st.info("Aucun problème pour cette semaine.")
    else:
        for i, problem in enumerate(tops, 1):
            score = problem.get("criticality_score", 0) or 0
            if score >= 4.6:
                color = "🔴"
            elif score >= 3.6:
                color = "🟠"
            elif score >= 2.6:
                color = "🟡"
            else:
                color = "🟢"

            with st.expander(
                f"{color} #{i} — Score {score} — {problem['description'][:60]}..."
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Description :** {problem['description']}")
                    st.write(f"**Type :** {problem['type']}")
                    st.write(f"**Impact :** {problem['impact']}/5")
                with col2:
                    st.write(f"**Urgence :** {problem['urgency']}/5")
                    st.write(f"**Répétitions :** {problem['repetitions']}")
                    st.write(f"**Responsable probable :** "
                             f"{problem.get('probable_responsible') or 'Non identifié'}")

    st.markdown("---")

    # ─── RÉSUMÉ RAPPORTS ─────────────────────────────────
    st.markdown("### 📋 Rapports de la Semaine")

    if not week_reports:
        st.info("Aucun rapport soumis pour cette semaine.")
    else:
        for report in week_reports:
            with st.expander(f"Rapport #{report['id']} — Semaine {report['week_number']}"):
                st.write(f"**Résumé :** {report['global_summary']}")
                st.write(f"**Nombre de problèmes :** {len(report['problems'])}")
                st.write(f"**Soumis le :** {report['created_at'][:10]}")

except Exception as e:
    st.error(f"Erreur de connexion à l'API : {e}")