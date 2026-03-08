import streamlit as st
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import streamlit.components.v1 as components

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.get('token')}"}

def is_authenticated():
    return "token" in st.session_state and st.session_state["token"] is not None

def is_admin():
    return st.session_state.get("role") == "admin"

st.set_page_config(page_title="Effet Domino", page_icon="🕸️", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté.")
    st.stop()

if not is_admin():
    st.error("❌ Accès réservé aux administrateurs.")
    st.stop()

st.markdown("# 🕸️ Effet Domino")
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

try:
    # ─── RÉSUMÉ DU GRAPHE ────────────────────────────────
    summary_resp = requests.get(
        f"{API_URL}/domino/summary",
        headers = get_headers(),
        params  = {"week": week, "year": year}
    )

    if summary_resp.status_code != 200:
        st.error("Erreur lors de la récupération du graphe domino.")
        st.stop()

    summary = summary_resp.json()

    # ─── KPIs ────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔗 Total Connexions", summary["total_edges"])
    with col2:
        st.metric("🏢 Départements", summary["total_nodes"])
    with col3:
        bottleneck = summary.get("bottleneck")
        if bottleneck:
            st.metric("🎯 Goulot", bottleneck["department_name"])

    st.markdown("---")

    # ─── LÉGENDE ─────────────────────────────────────────
    st.markdown("### 🎨 Légende")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("🔴 **Bloquant** — source du problème")
    with col2:
        st.markdown("🟠 **Impacté** — bloqué par un autre")
    with col3:
        st.markdown("🟡 **Bloquant + Impacté**")
    with col4:
        st.markdown("🟢 **Neutre** — non affecté")

    st.markdown("---")

    # ─── GRAPHE PYVIS ────────────────────────────────────
    st.markdown("### 🕸️ Graphe des Dépendances")

    graph_resp = requests.get(
        f"{API_URL}/domino/graph-html",
        headers = get_headers(),
        params  = {"week": week, "year": year}
    )

    if graph_resp.status_code == 200:
        html_content = graph_resp.text
        components.html(html_content, height=600, scrolling=True)
    else:
        st.warning("Graphe non disponible pour cette semaine.")

    st.markdown("---")

    # ─── LISTE DES DÉPENDANCES ───────────────────────────
    st.markdown("### 🔗 Chaînes de Blocage")

    edges = summary.get("edges", [])
    if not edges:
        st.info("Aucune dépendance détectée pour cette semaine.")
    else:
        for edge in edges:
            st.markdown(
                f"**{edge['source']}** → **{edge['target']}** "
                f"| Poids : `{edge['weight']}` "
                f"| Problèmes : {edge['problem_ids']}"
            )

    st.markdown("---")

    # ─── SIMULATION DÉBLOCAGE ────────────────────────────
    st.markdown("### 🔧 Simuler un Déblocage")

    # Récupérer les départements
    depts_resp = requests.get(
        f"{API_URL}/departments",
        headers = get_headers()
    )
    depts = depts_resp.json() if depts_resp.status_code == 200 else []

    if depts:
        dept_options = {d["name"]: d["id"] for d in depts}
        selected_dept = st.selectbox(
            "Choisir le département à débloquer",
            options = list(dept_options.keys())
        )

        if st.button("🚀 Simuler le déblocage", use_container_width=True):
            dept_id = dept_options[selected_dept]
            sim_resp = requests.get(
                f"{API_URL}/domino/simulate",
                headers = get_headers(),
                params  = {
                    "dept_id": dept_id,
                    "week"   : week,
                    "year"   : year
                }
            )

            if sim_resp.status_code == 200:
                result = sim_resp.json()
                st.success(result["message"])

                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "🔓 Problèmes libérés",
                        result["freed_count"]
                    )
                with col2:
                    st.metric(
                        "🏢 Départements impactés",
                        len(result["impacted_departments"])
                    )

                if result["impacted_departments"]:
                    st.markdown(
                        "**Départements libérés :** " +
                        ", ".join(result["impacted_departments"])
                    )
            else:
                st.error("Erreur lors de la simulation.")

except Exception as e:
    st.error(f"Erreur de connexion à l'API : {e}")