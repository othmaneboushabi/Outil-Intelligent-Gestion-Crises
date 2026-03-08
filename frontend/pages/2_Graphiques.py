import streamlit as st
import requests
import os
import pandas as pd
import altair as alt
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

st.set_page_config(page_title="Graphiques", page_icon="📊", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté.")
    st.stop()

if not is_admin():
    st.error("❌ Accès réservé aux administrateurs.")
    st.stop()

st.markdown("# 📊 Graphiques & Analyses")
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
    # Récupérer les rapports
    reports_resp = requests.get(
        f"{API_URL}/reports",
        headers = get_headers()
    )
    reports = reports_resp.json() if reports_resp.status_code == 200 else []

    # Filtrer par semaine
    week_reports = [
        r for r in reports
        if r["week_number"] == week and r["year"] == year
    ]

    # Collecter tous les problèmes
    all_problems = []
    for r in week_reports:
        all_problems.extend(r.get("problems", []))

    if not all_problems:
        st.info("Aucune donnée pour cette semaine.")
        st.stop()
        
    # ─── CAMEMBERT — PROBLÈMES PAR DÉPARTEMENT ───────────
    st.markdown("### 🥧 Répartition par Département")

    # Récupérer tous les départements
    depts_resp = requests.get(
        f"{API_URL}/departments",
        headers = get_headers()
    )
    depts_map = {}
    if depts_resp.status_code == 200:
        for d in depts_resp.json():
            depts_map[d["id"]] = d["name"]

    # Compter les problèmes par département
    dept_counts = {}
    for r in week_reports:
        report_resp = requests.get(
            f"{API_URL}/reports/{r['id']}",
            headers = get_headers()
        )
        if report_resp.status_code == 200:
            report_detail = report_resp.json()
            # Récupérer le département via submitted_by
            user_resp = requests.get(
                f"{API_URL}/auth/me",
                headers = get_headers()
            )

        nb_problems = len(r.get("problems", []))
        # Trouver le département du rapport via les données disponibles
        for p in r.get("problems", []):
            for dep in p.get("dependencies", []):
                dep_id   = dep.get("dependent_department_id")
                dep_name = depts_map.get(dep_id, f"Dept {dep_id}")
                dept_counts[dep_name] = dept_counts.get(dep_name, 0) + 1

    # Si pas de dépendances, grouper par rapport
    if not dept_counts:
        for r in week_reports:
            dept_counts[f"Rapport #{r['id']}"] = len(r.get("problems", []))

    df_dept = pd.DataFrame(
        list(dept_counts.items()),
        columns=["Département", "Nombre"]
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        pie_chart = alt.Chart(df_dept).mark_arc(innerRadius=50).encode(
            theta   = alt.Theta("Nombre:Q"),
            color   = alt.Color(
                "Département:N",
                scale=alt.Scale(scheme="tableau10")
            ),
            tooltip = ["Département", "Nombre"]
        ).properties(width=400, height=300)

        st.altair_chart(pie_chart, use_container_width=True)

    with col2:
        st.markdown("**Détail :**")
        for dept, count in dept_counts.items():
            total = sum(dept_counts.values())
            pct   = round(count / total * 100, 1) if total > 0 else 0
            st.markdown(f"🏢 **{dept}** : {count} ({pct}%)")

    # ─── CAMEMBERT — PROBLÈMES PAR TYPE ─────────────────
    st.markdown("### 🥧 Répartition par Type de Problème")

    type_counts = {}
    for p in all_problems:
        t = p.get("type", "autre")
        type_counts[t] = type_counts.get(t, 0) + 1

    df_type = pd.DataFrame(
        list(type_counts.items()),
        columns=["Type", "Nombre"]
    )

    pie_chart2 = alt.Chart(df_type).mark_arc(innerRadius=50).encode(
        theta   = alt.Theta("Nombre:Q"),
        color   = alt.Color("Type:N", scale=alt.Scale(scheme="set2")),
        tooltip = ["Type", "Nombre"]
    ).properties(width=400, height=300)

    st.altair_chart(pie_chart2, use_container_width=True)

  

    st.markdown("---")

    # ─── HISTOGRAMME — SCORES DE CRITICITÉ ───────────────
    st.markdown("### 📊 Distribution des Scores de Criticité")

    scores_data = [
        {
            "id"   : p["id"],
            "score": p.get("criticality_score") or 0,
            "type" : p.get("type", "autre"),
            "desc" : p["description"][:40] + "..."
        }
        for p in all_problems
    ]

    df_scores = pd.DataFrame(scores_data)

    def get_color(score):
        if score >= 4.6:
            return "🔴 Alerte Maximale"
        elif score >= 3.6:
            return "🟠 Critique"
        elif score >= 2.6:
            return "🟡 Élevé"
        else:
            return "🟢 Faible"

    df_scores["niveau"] = df_scores["score"].apply(get_color)

    color_scale = alt.Scale(
        domain = ["🔴 Alerte Maximale", "🟠 Critique", "🟡 Élevé", "🟢 Faible"],
        range  = ["#f44336", "#ff9800", "#ffeb3b", "#4caf50"]
    )

    bar_chart = alt.Chart(df_scores).mark_bar().encode(
        x       = alt.X("desc:N", title="Problème",
                        axis=alt.Axis(labelAngle=-45)),
        y       = alt.Y("score:Q", title="Score de Criticité",
                        scale=alt.Scale(domain=[0, 5])),
        color   = alt.Color("niveau:N", scale=color_scale, title="Niveau"),
        tooltip = ["desc:N", "score:Q", "type:N", "niveau:N"]
    ).properties(height=350)

    st.altair_chart(bar_chart, use_container_width=True)

    st.markdown("---")

    # ─── COURBE D'ÉVOLUTION ───────────────────────────────
    st.markdown("### 📈 Évolution des Scores sur les Dernières Semaines")

    evolution_data = []
    for r in reports:
        for p in r.get("problems", []):
            if p.get("criticality_score"):
                evolution_data.append({
                    "semaine" : f"S{r['week_number']}/{r['year']}",
                    "score"   : p["criticality_score"],
                    "week_num": r["week_number"]
                })

    if evolution_data:
        df_evolution = pd.DataFrame(evolution_data)
        df_avg = df_evolution.groupby(
            "semaine"
        )["score"].mean().reset_index()
        df_avg.columns = ["semaine", "score_moyen"]

        line_chart = alt.Chart(df_avg).mark_line(
            point = True,
            color = "#2196f3"
        ).encode(
            x       = alt.X("semaine:N", title="Semaine"),
            y       = alt.Y("score_moyen:Q", title="Score Moyen",
                            scale=alt.Scale(domain=[0, 5])),
            tooltip = ["semaine:N", "score_moyen:Q"]
        ).properties(height=300)

        st.altair_chart(line_chart, use_container_width=True)
    else:
        st.info("Pas assez de données pour afficher l'évolution.")

    st.markdown("---")

    # ─── TABLEAU RÉCAPITULATIF ────────────────────────────
    st.markdown("### 📋 Tableau Récapitulatif")

    df_table = pd.DataFrame([
        {
            "ID"          : p["id"],
            "Description" : p["description"][:60] + "...",
            "Type"        : p["type"],
            "Impact"      : p["impact"],
            "Urgence"     : p["urgency"],
            "Score"       : p.get("criticality_score") or 0,
            "Responsable" : p.get("probable_responsible") or "Non identifié",
            "Alerte"      : "🚨" if p.get("alert_sent") else "✅"
        }
        for p in all_problems
    ])

    st.dataframe(df_table, use_container_width=True)

except Exception as e:
    st.error(f"Erreur de connexion à l'API : {e}")