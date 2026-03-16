import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.get('token')}"}

def is_authenticated():
    return "token" in st.session_state and st.session_state["token"] is not None

def is_admin():
    return st.session_state.get("role") == "admin"

st.set_page_config(page_title="Administration", page_icon="⚙️", layout="wide")

if not is_authenticated():
    st.error("❌ Vous devez être connecté.")
    st.stop()

if not is_admin():
    st.error("❌ Accès réservé aux administrateurs.")
    st.stop()

st.markdown("# ⚙️ Administration")
st.markdown("---")

# ─── TABS ────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🏢 Départements", "👥 Utilisateurs"])


# ══════════════════════════════════════════════════════════
# TAB 1 — DÉPARTEMENTS
# ══════════════════════════════════════════════════════════

with tab1:
    st.markdown("### 🏢 Gestion des Départements")

    st.markdown("#### ➕ Créer un Département")

    with st.form("form_dept"):
        dept_name = st.text_input("Nom du département",
                                   placeholder="ex: IT, Finance, RH...")
        dept_desc = st.text_area("Description (optionnel)",
                                  placeholder="Description du département...")
        submit_dept = st.form_submit_button(
            "✅ Créer le Département",
            use_container_width=True
        )

        if submit_dept:
            if not dept_name:
                st.error("Le nom est obligatoire.")
            else:
                resp = requests.post(
                    f"{API_URL}/departments",
                    headers = get_headers(),
                    json    = {
                        "name"       : dept_name,
                        "description": dept_desc or ""
                    }
                )
                if resp.status_code == 200:
                    st.success(f"✅ Département '{dept_name}' créé avec succès !")
                    st.rerun()
                elif resp.status_code == 400:
                    st.warning("⚠️ Ce département existe déjà.")
                else:
                    st.error(f"Erreur : {resp.status_code}")

    st.markdown("---")

    st.markdown("#### 📋 Liste des Départements")

    depts_resp = requests.get(
        f"{API_URL}/departments",
        headers = get_headers()
    )

    if depts_resp.status_code == 200:
        depts = depts_resp.json()

        if not depts:
            st.info("Aucun département créé.")
        else:
            for dept in depts:
                col1, col2, col3, col4 = st.columns([3, 3, 1, 1])
                with col1:
                    st.markdown(f"**🏢 {dept['name']}**")
                with col2:
                    st.markdown(
                        dept.get("description") or "_Pas de description_"
                    )
                with col3:
                    if dept.get("is_active", True):
                        st.markdown("🟢 Actif")
                    else:
                        st.markdown("🔴 Archivé")
                with col4:
                    if st.button("🗑️", key=f"del_dept_{dept['id']}",
                                  help=f"Supprimer/Archiver {dept['name']}"):
                        del_resp = requests.delete(
                            f"{API_URL}/departments/{dept['id']}",
                            headers = get_headers()
                        )
                        if del_resp.status_code == 200:
                            result = del_resp.json()
                            if result.get("archived"):
                                st.warning(
                                    f"📦 '{dept['name']}' archivé "
                                    f"({result['reason']})"
                                )
                            else:
                                st.success(
                                    f"✅ '{dept['name']}' supprimé définitivement."
                                )
                            st.rerun()
                        else:
                            st.error("Impossible de supprimer ce département.")
    else:
        st.error("Erreur lors de la récupération des départements.")


# ══════════════════════════════════════════════════════════
# TAB 2 — UTILISATEURS
# ══════════════════════════════════════════════════════════

with tab2:
    st.markdown("### 👥 Gestion des Utilisateurs")

    st.markdown("#### ➕ Créer un Utilisateur")

    depts_resp2 = requests.get(
        f"{API_URL}/departments",
        headers = get_headers()
    )
    depts2 = depts_resp2.json() if depts_resp2.status_code == 200 else []
    dept_options = {d["name"]: d["id"] for d in depts2}

    with st.form("form_user"):
        col1, col2 = st.columns(2)
        with col1:
            user_fullname = st.text_input("Nom complet",
                                           placeholder="ex: Karim Benali")
            user_email    = st.text_input("Email",
                                           placeholder="ex: karim@crisis.com")
            user_dept     = st.selectbox(
                "Département",
                options = list(dept_options.keys())
            )
        with col2:
            user_password = st.text_input("Mot de passe", type="password")
            user_role     = st.selectbox(
                "Rôle",
                options = ["user", "admin"],
                index   = 0,
                help    = "Par défaut : user"
            )

        submit_user = st.form_submit_button(
            "✅ Créer l'Utilisateur",
            use_container_width=True
        )

        if submit_user:
            if not all([user_fullname, user_email, user_password]):
                st.error("Tous les champs sont obligatoires.")
            else:
                resp = requests.post(
                    f"{API_URL}/users",
                    headers = get_headers(),
                    json    = {
                        "full_name"    : user_fullname,
                        "email"        : user_email,
                        "password"     : user_password,
                        "role"         : user_role,
                        "department_id": dept_options.get(user_dept)
                    }
                )
                if resp.status_code == 200:
                    st.success(
                        f"✅ Utilisateur '{user_fullname}' créé avec succès !"
                    )
                    st.rerun()
                elif resp.status_code == 400:
                    st.warning("⚠️ Cet email existe déjà.")
                else:
                    st.error(f"Erreur : {resp.status_code} — {resp.text}")

    st.markdown("---")

    st.markdown("#### 📋 Liste des Utilisateurs")

    users_resp = requests.get(
        f"{API_URL}/users",
        headers = get_headers()
    )

    if users_resp.status_code == 200:
        users = users_resp.json()

        if not users:
            st.info("Aucun utilisateur créé.")
        else:
            # ─── BARRE DE RECHERCHE ───────────────────────────
            search = st.text_input(
                "🔍 Rechercher un utilisateur",
                placeholder = "Entrez le nom...",
                key         = "search_user"
            )

            # Filtrer selon la recherche
            if search:
                users_filtered = [
                    u for u in users
                    if search.lower() in u.get("full_name", "").lower()
                ]
            else:
                users_filtered = users

            # Afficher le nombre de résultats
            if search:
                st.caption(f"🔎 {len(users_filtered)} résultat(s) pour **'{search}'**")

            if not users_filtered:
                st.warning(f"⚠️ Aucun utilisateur trouvé pour '{search}'")
            else:
                # ─── EN-TÊTE ──────────────────────────────────
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                with col1:
                    st.markdown("**👤 Nom**")
                with col2:
                    st.markdown("**📧 Email**")
                with col3:
                    st.markdown("**🏢 Département**")
                with col4:
                    st.markdown("**🎭 Rôle**")
                with col5:
                    st.markdown("**⚡ Statut**")
                st.divider()

                # ─── LISTE DES USERS ──────────────────────────
                for user in users_filtered:
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])

                    full_name = user.get("full_name") or user.get("email", "Inconnu")

                    with col1:
                        st.markdown(f"**{full_name}**")
                    with col2:
                        st.markdown(f"📧 {user['email']}")
                    with col3:
                        dept_name = next(
                            (d["name"] for d in depts2
                             if d["id"] == user.get("department_id")),
                            "—"
                        )
                        st.markdown(f"🏢 {dept_name}")
                    with col4:
                        if user["role"] == "admin":
                            st.markdown("👑 Admin")
                        else:
                            st.markdown("👤 User")
                    with col5:
                        is_active = user.get("is_active", True)
                        if user["role"] != "admin":
                            btn_label = "🔴" if is_active else "🟢"
                            btn_help  = "Désactiver" if is_active else "Activer"

                            if st.button(
                                btn_label,
                                key  = f"toggle_{user['id']}",
                                help = btn_help
                            ):
                                toggle_resp = requests.patch(
                                    f"{API_URL}/users/{user['id']}/toggle",
                                    headers = get_headers()
                                )
                                if toggle_resp.status_code == 200:
                                    st.rerun()
                                else:
                                    st.error("Erreur lors de la modification.")
                        else:
                            st.markdown("🔒")

                    st.divider()
    else:
        st.error("Erreur lors de la récupération des utilisateurs.")