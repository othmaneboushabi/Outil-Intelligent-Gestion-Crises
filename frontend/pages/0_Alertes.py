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

# ─── PAGE ─────────────────────────────────────────────────

st.set_page_config(page_title="Alertes Actives", page_icon="🚨", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté pour accéder à cette page.")
    st.stop()

if not is_admin():
    st.error("❌ Accès réservé aux administrateurs.")
    st.stop()

st.markdown("# 🚨 Alertes Actives")
st.markdown("---")

# Sélecteur semaine/année
col1, col2 = st.columns(2)
with col1:
    week = st.number_input("Semaine", min_value=1, max_value=52, value=datetime.now().isocalendar()[1])
with col2:
    year = st.number_input("Année", min_value=2024, max_value=2030, value=datetime.now().year)

# Récupérer les alertes
try:
    response = requests.get(
        f"{API_URL}/alerts/active",
        headers = get_headers(),
        params  = {"week": week, "year": year}
    )

    if response.status_code == 200:
        alerts = response.json()

        if not alerts:
            st.success("✅ Aucune alerte active pour cette semaine.")
        else:
            st.error(f"⚠️ {len(alerts)} alerte(s) active(s) détectée(s) !")

            for alert in alerts:
                with st.container():
                    st.markdown(f"""
                    <div style="background:#2d1a1a; border-left:4px solid #f44336;
                                padding:15px; border-radius:8px; margin:10px 0;">
                        <h4 style="color:#f44336;">
                            🚨 Score : {alert['criticality_score']} — {alert['department_name']}
                        </h4>
                        <p><strong>Description :</strong> {alert['description']}</p>
                        <p><strong>Responsable probable :</strong>
                            {alert.get('probable_responsible') or 'Non identifié'}
                        </p>
                        <p><strong>Départements bloqués :</strong>
                            {', '.join(alert.get('dependent_departments', [])) or 'Aucun'}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.error(f"Erreur API : {response.status_code}")

except Exception as e:
    st.error(f"Erreur de connexion à l'API : {e}")