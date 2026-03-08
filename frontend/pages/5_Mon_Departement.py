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

st.set_page_config(page_title="Mon Département", page_icon="🏢", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté.")
    st.stop()

# ─── TITRE SELON RÔLE ────────────────────────────────────
if is_admin():
    st.markdown("# 🔍 Analyse IA en Temps Réel")
else:
    st.markdown("# 🏢 Mon Département")

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
    # ─── SOUMETTRE UN RAPPORT ────────────────────────────
    if is_admin():
        st.markdown("### 🔍 Analyser un Problème via IA")
    else:
        st.markdown("### 📝 Soumettre un Rapport")

    with st.form("rapport_form"):

        # L'admin n'a pas besoin du résumé global
        if not is_admin():
            global_summary = st.text_area(
                "Résumé global de la semaine",
                placeholder="Décrivez la situation générale de votre département..."
            )
        else:
            global_summary = "Analyse IA Admin"

        st.markdown("#### 🔴 Problème 1")
        desc1 = st.text_area("Description", key="desc1",
                              placeholder="Décrivez le problème en détail...")
        col1, col2 = st.columns(2)
        with col1:
            type1   = st.selectbox("Type", ["technique", "humain", "financier",
                                            "logistique", "autre"], key="type1")
            impact1 = st.slider("Impact", 1, 5, 3, key="impact1")
        with col2:
            urgency1     = st.slider("Urgence", 1, 5, 3, key="urgency1")
            repetitions1 = st.number_input("Répétitions", 1, 10, 1, key="rep1")

        # Dépendances
        depts_resp = requests.get(
            f"{API_URL}/departments",
            headers = get_headers()
        )
        depts = depts_resp.json() if depts_resp.status_code == 200 else []
        dept_options = {d["name"]: d["id"] for d in depts}

        selected_deps1 = st.multiselect(
            "Départements bloqués",
            options = list(dept_options.keys()),
            key     = "deps1"
        )

        # ─── BOUTON ANALYSER VIA IA ──────────────────────
        analyze_btn = st.form_submit_button(
            "🔍 Analyser via IA",
            use_container_width=False
        )

        if analyze_btn and desc1:
            with st.spinner("Analyse IA en cours..."):
                analyze_resp = requests.post(
                    f"{API_URL}/analyze",
                    headers = get_headers(),
                    json    = {
                        "description"    : desc1,
                        "impact"         : impact1,
                        "urgency"        : urgency1,
                        "repetitions"    : repetitions1,
                        "nb_dependencies": len(selected_deps1),
                        "week_number"    : int(week),
                        "year"           : int(year)
                    }
                )
            if analyze_resp.status_code == 200:
                result = analyze_resp.json()
                score  = result["criticality_score"]
                level  = result["criticality_level"]

                if score >= 4.6:
                    color = "🔴"
                elif score >= 3.6:
                    color = "🟠"
                elif score >= 2.6:
                    color = "🟡"
                else:
                    color = "🟢"

                st.markdown("#### 🤖 Résultat de l'Analyse IA")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Score de Criticité", f"{score}/5")
                with col2:
                    st.markdown(f"**Niveau :** {color} {level}")

                if result.get("probable_responsible"):
                    st.info(
                        f"👤 **Responsable probable :** "
                        f"{result['probable_responsible']}"
                    )

                entities = result.get("entities", {})
                if any(entities.values()):
                    with st.expander("🔍 Entités détectées par SpaCy"):
                        for ent_type, values in entities.items():
                            if values:
                                st.markdown(
                                    f"**{ent_type}** : {', '.join(values)}"
                                )

                similar = result.get("similar_problems", [])
                if similar:
                    st.warning(
                        f"⚠️ {len(similar)} problème(s) similaire(s) "
                        f"détecté(s) cette semaine !"
                    )
                    for s in similar:
                        st.markdown(
                            f"- Problème ID {s['problem_id']} "
                            f"— similarité : {s['similarity_score']}"
                        )
                else:
                    st.success("✅ Aucun problème similaire détecté.")
            else:
                st.error("Erreur lors de l'analyse IA.")

        # ─── DEUXIÈME PROBLÈME (User seulement) ──────────
        if not is_admin():
            add_problem2 = st.checkbox("➕ Ajouter un deuxième problème")

            desc2 = type2 = impact2 = urgency2 = repetitions2 = None
            selected_deps2 = []

            if add_problem2:
                st.markdown("#### 🟠 Problème 2")
                desc2 = st.text_area("Description", key="desc2")
                col1, col2 = st.columns(2)
                with col1:
                    type2   = st.selectbox("Type", ["technique", "humain",
                                                     "financier", "logistique",
                                                     "autre"], key="type2")
                    impact2 = st.slider("Impact", 1, 5, 3, key="impact2")
                with col2:
                    urgency2     = st.slider("Urgence", 1, 5, 3, key="urgency2")
                    repetitions2 = st.number_input("Répétitions", 1, 10, 1,
                                                    key="rep2")

                selected_deps2 = st.multiselect(
                    "Départements bloqués",
                    options = list(dept_options.keys()),
                    key     = "deps2"
                )

            # Bouton soumettre uniquement pour User
            submit = st.form_submit_button(
                "📤 Soumettre le Rapport",
                use_container_width=True
            )

            if submit:
                if not global_summary or not desc1:
                    st.error(
                        "Veuillez remplir le résumé global et au moins un problème."
                    )
                else:
                    problems = [
                        {
                            "description"             : desc1,
                            "type"                    : type1,
                            "impact"                  : impact1,
                            "urgency"                 : urgency1,
                            "repetitions"             : repetitions1,
                            "dependent_department_ids": [
                                dept_options[d] for d in selected_deps1
                            ]
                        }
                    ]

                    if add_problem2 and desc2:
                        problems.append({
                            "description"             : desc2,
                            "type"                    : type2,
                            "impact"                  : impact2,
                            "urgency"                 : urgency2,
                            "repetitions"             : repetitions2,
                            "dependent_department_ids": [
                                dept_options[d] for d in selected_deps2
                            ]
                        })

                    payload = {
                        "week_number"   : int(week),
                        "year"          : int(year),
                        "global_summary": global_summary,
                        "problems"      : problems
                    }

                    with st.spinner("Soumission en cours..."):
                        resp = requests.post(
                            f"{API_URL}/reports",
                            headers = get_headers(),
                            json    = payload
                        )

                    if resp.status_code == 200:
                        st.success("✅ Rapport soumis avec succès !")
                        st.balloons()
                    elif resp.status_code == 400:
                        st.warning(
                            "⚠️ Vous avez déjà soumis un rapport pour cette semaine."
                        )
                    else:
                        st.error(f"Erreur : {resp.status_code} — {resp.text}")

    st.markdown("---")

    # ─── MES RAPPORTS (User seulement) ───────────────────
    if not is_admin():
        st.markdown("### 📋 Mes Rapports Soumis")

        reports_resp = requests.get(
            f"{API_URL}/reports",
            headers = get_headers()
        )

        if reports_resp.status_code == 200:
            reports = reports_resp.json()

            if not reports:
                st.info("Aucun rapport soumis pour le moment.")
            else:
                for report in reports:
                    with st.expander(
                        f"📋 Rapport Semaine {report['week_number']}/{report['year']} "
                        f"— {report['created_at'][:10]}"
                    ):
                        st.write(f"**Résumé :** {report['global_summary']}")
                        st.write(
                            f"**Nombre de problèmes :** {len(report['problems'])}"
                        )

                        for p in report["problems"]:
                            score = p.get("criticality_score") or 0
                            if score >= 4.6:
                                color = "🔴"
                            elif score >= 3.6:
                                color = "🟠"
                            elif score >= 2.6:
                                color = "🟡"
                            else:
                                color = "🟢"

                            st.markdown(
                                f"{color} **Score {score}** "
                                f"— {p['description'][:80]}..."
                            )
                            if p.get("probable_responsible"):
                                st.markdown(
                                    f"👤 Responsable probable : "
                                    f"**{p['probable_responsible']}**"
                                )
                            if p.get("alert_sent"):
                                st.error("🚨 Alerte Maximale déclenchée !")

except Exception as e:
    st.error(f"Erreur de connexion à l'API : {e}")
