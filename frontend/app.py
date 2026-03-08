import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ─── CONFIGURATION PAGE ──────────────────────────────────

st.set_page_config(
    page_title = "Gestion de Crises",
    page_icon  = "🚨",
    layout     = "wide",
    initial_sidebar_state = "expanded"
)

# ─── FONCTIONS AUTH ───────────────────────────────────────

def login(email: str, password: str) -> dict:
    response = requests.post(
        f"{API_URL}/auth/login",
        data = {"username": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()
    return None

def get_headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"}

def is_authenticated() -> bool:
    return "token" in st.session_state and st.session_state["token"] is not None

def is_admin() -> bool:
    return st.session_state.get("role") == "admin"

def logout():
    for key in ["token", "role", "full_name", "department_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ─── PAGE DE CONNEXION ────────────────────────────────────

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🚨 Outil Intelligent de Gestion de Crises")
        st.markdown("---")
        st.markdown("### Connexion")

        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="admin@crisis.com")
            password = st.text_input("Mot de passe", type="password")
            submit   = st.form_submit_button("Se connecter", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Veuillez remplir tous les champs")
                else:
                    result = login(email, password)
                    if result:
                        st.session_state["token"]         = result["access_token"]
                        st.session_state["role"]          = result["role"]
                        st.session_state["full_name"]     = result["full_name"]
                        st.session_state["department_id"] = result.get("department_id")
                        st.success("Connexion réussie !")
                        st.rerun()
                    else:
                        st.error("Email ou mot de passe incorrect")

# ─── SIDEBAR ──────────────────────────────────────────────

def show_sidebar():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.get('full_name', '')}")
        st.markdown(f"**Rôle :** {st.session_state.get('role', '').upper()}")
        st.markdown("---")

        if is_admin():
            st.markdown("### 📊 Navigation Admin")
            st.page_link("pages/0_Alertes.py",           label="🚨 Alertes Actives")
            st.page_link("pages/1_Dashboard_Global.py",  label="📈 Dashboard Global")
            st.page_link("pages/2_Graphiques.py",        label="📊 Graphiques")
            st.page_link("pages/3_Effet_Domino.py",      label="🕸️ Effet Domino")
            st.page_link("pages/4_Resume_IA.py",         label="🤖 Résumé IA")
            st.page_link("pages/6_Admin_Gestion.py",     label="⚙️ Administration") 
            st.page_link("pages/5_Mon_Departement.py", label="🔍 Analyser via IA") 
        else:
            st.markdown("### 📋 Navigation")
            st.page_link("pages/5_Mon_Departement.py",   label="🏢 Mon Département")

        st.markdown("---")
        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()

# ─── MAIN ─────────────────────────────────────────────────

def main():
    if not is_authenticated():
        show_login_page()
    else:
        show_sidebar()
        st.markdown("## 🏠 Accueil")
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"👤 Connecté en tant que **{st.session_state.get('full_name')}**")
        with col2:
            st.info(f"🎭 Rôle : **{st.session_state.get('role', '').upper()}**")
        with col3:
            if is_admin():
                st.success("✅ Accès complet")
            else:
                st.warning("⚠️ Accès limité à votre département")

        if is_admin():
            st.markdown("### Navigation rapide")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.page_link("pages/0_Alertes.py",          label="🚨 Alertes Actives")
                st.page_link("pages/1_Dashboard_Global.py", label="📈 Dashboard Global")
            with col2:
                st.page_link("pages/2_Graphiques.py",       label="📊 Graphiques")
                st.page_link("pages/3_Effet_Domino.py",     label="🕸️ Effet Domino")
            with col3:
                st.page_link("pages/4_Resume_IA.py",        label="🤖 Résumé IA")
                st.page_link("pages/6_Admin_Gestion.py",    label="⚙️ Administration")
             
if __name__ == "__main__":
    main()