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

st.set_page_config(page_title="Résumé IA", page_icon="🤖", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté.")
    st.stop()

if not is_admin():
    st.error("❌ Accès réservé aux administrateurs.")
    st.stop()

st.markdown("# 🤖 Résumé Exécutif IA")
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

# ─── BOUTONS GÉNÉRER / RÉGÉNÉRER ─────────────────────────

col1, col2 = st.columns(2)
with col1:
    generate_btn    = st.button("🤖 Générer le Résumé", use_container_width=True)
with col2:
    regenerate_btn  = st.button("🔄 Régénérer", use_container_width=True)

# ─── GÉNÉRATION ──────────────────────────────────────────

if generate_btn or regenerate_btn:
    endpoint = "/summaries/regenerate" if regenerate_btn else "/summaries/generate"

    with st.spinner("Génération en cours..."):
        try:
            resp = requests.post(
                f"{API_URL}{endpoint}",
                headers = get_headers(),
                params  = {"week": week, "year": year},
                timeout = 60
            )

            if resp.status_code == 200:
                result = resp.json()

                # Afficher le résumé
                st.markdown("### 📄 Résumé Généré")

                cached = result.get("cached", False)
                model  = result.get("model_used", "inconnu")

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"🤖 Modèle : `{model}`")
                with col2:
                    if cached:
                        st.success("✅ Depuis le cache PostgreSQL")
                    else:
                        st.warning("🔄 Nouvellement généré")

                st.markdown("---")
                st.markdown(result.get("content", "Aucun contenu généré."))

                # Contexte utilisé
                context = result.get("context")
                if context:
                    st.markdown("---")
                    with st.expander("📊 Contexte utilisé pour la génération"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Score Global", f"{context['global_score']}/5")
                        with col2:
                            st.metric("Total Problèmes", context["total_problems"])
                        with col3:
                            st.metric("Départements", len(context["dept_stats"]))

                        st.markdown("**Top Problèmes :**")
                        for p in context.get("top_problems", []):
                            st.markdown(
                                f"- **{p['dept']}** — Score `{p['score']}` "
                                f"— {p['description'][:80]}..."
                            )
            else:
                st.error(f"Erreur API : {resp.status_code} — {resp.text}")

        except Exception as e:
            st.error(f"Erreur : {e}")

st.markdown("---")

# ─── HISTORIQUE DES RÉSUMÉS ───────────────────────────────

st.markdown("### 📚 Historique des Résumés")

try:
    history_resp = requests.get(
        f"{API_URL}/summaries",
        headers = get_headers()
    )

    if history_resp.status_code == 200:
        summaries = history_resp.json()

        if not summaries:
            st.info("Aucun résumé généré pour le moment.")
        else:
            for summary in summaries:
                with st.expander(
                    f"📄 Semaine {summary['week_number']}/{summary['year']} "
                    f"— {summary['generated_at'][:10]} "
                    f"— Modèle : {summary.get('model_used', 'inconnu')}"
                ):
                    st.markdown(summary["content"])
    else:
        st.error("Erreur lors de la récupération de l'historique.")

except Exception as e:
    st.error(f"Erreur : {e}")