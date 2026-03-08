# Journal de Développement — Outil Intelligent de Gestion de Crises

---

## Sprint 1 — Infrastructure + Auth JWT
**Date :** 2026-03-07
**Branche :** develop

### Fichiers créés
- backend/database.py
- backend/models.py
- backend/schemas.py
- backend/auth.py
- backend/crud.py
- backend/main.py

### Décisions techniques
- Auth JWT HS256 + bcrypt
- RBAC Admin/User
- 6 tables PostgreSQL
- 5 départements initiaux (IT, Finance, RH, Logistique, Marketing)

### Comptes de test
- Admin : admin@crisis.com / Admin1234
- User IT : it@crisis.com / User1234

---

## Sprint 2 — NLP Pipeline
**Date :** 2026-03-07
**Branche :** develop

### Fichiers créés
- backend/nlp/cleaner.py
- backend/nlp/scoring.py
- backend/nlp/ner_engine.py
- backend/nlp/similarity.py
- backend/nlp/alert_engine.py

### Décisions techniques
- Modèle SpaCy : fr_core_news_md
- Embeddings : all-MiniLM-L6-v2
- Formule criticité v2.1 : score_final = score_brut + (Impact×Urgence)/25 × 0.5
- Alertes automatiques pour score > 4.6
- Pipeline intégré dans POST /reports

---

## Sprint 3 — Domino Engine
**Date :** 2026-03-07
**Branche :** develop

### Fichiers créés
- backend/nlp/domino.py

### Routes ajoutées
- GET /domino/summary
- GET /domino/simulate
- GET /domino/graph-html

### Décisions techniques
- Graphe NetworkX + visualisation PyVis
- Test validé : IT bloque Finance, RH, Logistique (score 4.7)

---

## Sprint 4 — Hugging Face + Résumé Exécutif
**Date :** 2026-03-07
**Branche :** develop

### Fichiers créés
- backend/nlp/summarizer.py

### Routes ajoutées
- POST /summaries/generate
- POST /summaries/regenerate

### Décisions techniques
- Modèle principal : Mistral-7B
- Fallback 1 : moussaKam/barthez-orangesum-abstract
- Fallback 2 : génération locale
- Cache PostgreSQL (table executive_summaries)

---

## Sprint 5 — Frontend Streamlit
**Date :** 2026-03-07
**Branche :** develop

### Fichiers créés
- frontend/app.py
- frontend/pages/0_Alertes.py
- frontend/pages/1_Dashboard_Global.py
- frontend/pages/2_Graphiques.py
- frontend/pages/3_Effet_Domino.py
- frontend/pages/4_Resume_IA.py
- frontend/pages/5_Mon_Departement.py
- frontend/pages/6_Admin_Gestion.py

### Fonctionnalités
- Login JWT + sidebar navigation RBAC
- 7 pages avec protection par rôle
- Dashboard global avec métriques
- Graphiques Altair (barres + camembert)
- Visualisation graphe domino PyVis
- Résumé exécutif Mistral-7B
- Formulaire soumission rapport
- Administration CRUD users/departments

---

## Corrections Sprint 5
**Date :** 2026-03-08
**Branche :** develop

### Priorité 1 — Route POST /analyze + Bouton IA temps réel
- Route POST /analyze ajoutée dans main.py
- Bouton "Analyser via IA" dans Page 5
- Admin et User ont accès
- Titre adapté selon le rôle

### Priorité 2 — Soft delete département
- Colonne is_active ajoutée dans models.py
- Archivage si utilisateurs ou rapports liés
- Suppression physique si aucune donnée liée
- Statut 🟢 Actif / 🔴 Archivé affiché dans Page 6

### Priorité 3 — Camembert par département
- Page 2 Graphiques corrigée
- Camembert affiche maintenant par département

### Priorité 4 — Export PDF
- fpdf2 intégré dans Page 4 Résumé IA
- Export depuis résumé généré
- Export depuis historique des résumés

---

## Sprint 6 — Docker + Tests
**Date :** 2026-03-08
**Branche :** develop

### Docker
- Dockerfile (FastAPI backend)
- Dockerfile.streamlit (Streamlit frontend)
- docker-compose.yml (3 services : db + api + web)
- frontend/requirements.txt mis à jour (fpdf2 ajouté)
- backend/requirements.txt mis à jour (fpdf2 ajouté)

### Tests pytest
- A faire

### État
- Docker build : en cours
- Tests pytest : à faire
- Livraison v1.0.0 : après rapport