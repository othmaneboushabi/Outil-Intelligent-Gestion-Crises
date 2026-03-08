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
    generate_btn   = st.button("🤖 Générer le Résumé", use_container_width=True)
with col2:
    regenerate_btn = st.button("🔄 Régénérer", use_container_width=True)

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

                # ─── EXPORT PDF ──────────────────────────
                content_text = result.get("content", "")
                if content_text:
                    if st.button(
                        "📥 Exporter en PDF",
                        use_container_width=False
                    ):
                        try:
                            from fpdf import FPDF
                            import base64
                            import tempfile

                            pdf = FPDF()
                            pdf.add_page()

                            # Titre
                            pdf.set_font("Helvetica", "B", 16)
                            pdf.cell(
                                0, 10,
                                f"Resume Executif - Semaine {week}/{year}",
                                ln=True, align="C"
                            )
                            pdf.ln(5)

                            # Ligne séparatrice
                            pdf.set_draw_color(200, 200, 200)
                            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                            pdf.ln(5)

                            # Modèle utilisé
                            pdf.set_font("Helvetica", "B", 10)
                            pdf.cell(
                                0, 8,
                                f"Modele : {result.get('model_used', 'inconnu')}",
                                ln=True
                            )
                            pdf.ln(3)

                            # Contenu
                            pdf.set_font("Helvetica", "", 11)
                            clean_content = (
                                content_text
                                .replace("→", "->")
                                .replace("—", "-")
                                .replace("•", "-")
                                .replace("\u2019", "'")
                                .replace("\u2018", "'")
                                .replace("\u201c", '"')
                                .replace("\u201d", '"')
                                .encode("latin-1", errors="replace")
                                .decode("latin-1")
                            )

                            for line in clean_content.split("\n"):
                                if line.strip():
                                    pdf.multi_cell(0, 7, line.strip())
                                    pdf.ln(1)
                                else:
                                    pdf.ln(3)

                            # Footer
                            pdf.ln(10)
                            pdf.set_font("Helvetica", "I", 8)
                            pdf.set_text_color(150, 150, 150)
                            pdf.cell(
                                0, 6,
                                "Outil Intelligent de Gestion de Crises"
                                " - Genere automatiquement",
                                ln=True, align="C"
                            )

                            with tempfile.NamedTemporaryFile(
                                suffix=".pdf", delete=False
                            ) as tmp:
                                pdf_path = tmp.name

                            pdf.output(pdf_path)

                            with open(pdf_path, "rb") as f:
                                pdf_bytes = f.read()

                            os.unlink(pdf_path)

                            st.download_button(
                                label     = "📥 Télécharger le PDF",
                                data      = pdf_bytes,
                                file_name = f"resume_S{week}_{year}.pdf",
                                mime      = "application/pdf"
                            )
                            st.success("✅ PDF généré avec succès !")

                        except Exception as e:
                            st.error(f"Erreur génération PDF : {e}")

                # ─── CONTEXTE UTILISÉ ────────────────────
                context = result.get("context")
                if context:
                    st.markdown("---")
                    with st.expander("📊 Contexte utilisé pour la génération"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Score Global",
                                f"{context['global_score']}/5"
                            )
                        with col2:
                            st.metric(
                                "Total Problèmes",
                                context["total_problems"]
                            )
                        with col3:
                            st.metric(
                                "Départements",
                                len(context["dept_stats"])
                            )

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

                    # Export PDF depuis historique
                    hist_content = summary.get("content", "")
                    if hist_content:
                        if st.button(
                            "📥 PDF",
                            key  = f"pdf_{summary['id']}",
                            help = "Exporter ce résumé en PDF"
                        ):
                            try:
                                from fpdf import FPDF
                                import tempfile

                                pdf = FPDF()
                                pdf.add_page()
                                pdf.set_font("Helvetica", "B", 16)
                                pdf.cell(
                                    0, 10,
                                    f"Resume Executif - S{summary['week_number']}"
                                    f"/{summary['year']}",
                                    ln=True, align="C"
                                )
                                pdf.ln(5)
                                pdf.set_font("Helvetica", "", 11)

                                clean = (
                                    hist_content
                                    .replace("→", "->")
                                    .replace("—", "-")
                                    .replace("•", "-")
                                    .replace("\u2019", "'")
                                    .replace("\u2018", "'")
                                    .replace("\u201c", '"')
                                    .replace("\u201d", '"')
                                    .encode("latin-1", errors="replace")
                                    .decode("latin-1")
                                )

                                for line in clean.split("\n"):
                                    if line.strip():
                                        pdf.multi_cell(0, 7, line.strip())
                                        pdf.ln(1)
                                    else:
                                        pdf.ln(3)

                                with tempfile.NamedTemporaryFile(
                                    suffix=".pdf", delete=False
                                ) as tmp:
                                    pdf_path = tmp.name

                                pdf.output(pdf_path)

                                with open(pdf_path, "rb") as f:
                                    pdf_bytes = f.read()

                                os.unlink(pdf_path)

                                st.download_button(
                                    label     = "📥 Télécharger",
                                    data      = pdf_bytes,
                                    file_name = (
                                        f"resume_S{summary['week_number']}"
                                        f"_{summary['year']}.pdf"
                                    ),
                                    mime      = "application/pdf",
                                    key       = f"dl_{summary['id']}"
                                )
                            except Exception as e:
                                st.error(f"Erreur PDF : {e}")
    else:
        st.error("Erreur lors de la récupération de l'historique.")

except Exception as e:
    st.error(f"Erreur : {e}")