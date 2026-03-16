# 🚨 Outil Intelligent de Gestion de Crises et Priorisation des Problèmes

> Application web full-stack de gestion de crises organisationnelles avec pipeline NLP, scoring automatique et visualisation de l'effet domino.

---

## 📋 Table des matières

- [Description](#description)
- [Technologies](#technologies)
- [Architecture](#architecture)
- [Démarrage rapide Docker](#démarrage-rapide-docker)
- [Installation locale](#installation-locale)
- [Structure du projet](#structure-du-projet)
- [Routes API](#routes-api)
- [Comptes de test](#comptes-de-test)
- [Tests](#tests)
- [Fonctionnalités](#fonctionnalités)

---

## Description

L'**Outil Intelligent de Gestion de Crises** permet à une organisation de collecter, analyser et prioriser automatiquement les problèmes signalés par ses départements chaque semaine.

### Objectifs
- Remplacer les rapports manuels hebdomadaires par un système intelligent
- Calculer automatiquement un score de criticité pour chaque problème
- Détecter les effets domino entre départements
- Générer un résumé exécutif automatique via Mistral-7B
- Alerter la direction pour les problèmes critiques (score > 4.5)

---

## Technologies

### Backend
| Technologie | Rôle |
|---|---|
| FastAPI | API REST (30+ routes) |
| PostgreSQL | Base de données (6 tables) |
| SQLAlchemy | ORM Python |
| JWT + bcrypt | Authentification sécurisée |

### Intelligence Artificielle
| Technologie | Rôle |
|---|---|
| SpaCy (fr_core_news_md) | Nettoyage texte + NER français |
| Sentence-BERT (all-MiniLM-L6-v2) | Similarité sémantique |
| Mistral-7B (Hugging Face) | Génération résumé exécutif |
| NetworkX + PyVis | Graphe effet domino interactif |

### Frontend
| Technologie | Rôle |
|---|---|
| Streamlit | Dashboard 7 pages |
| Altair | Graphiques et visualisations |
| fpdf2 | Export PDF |

### Infrastructure
| Technologie | Rôle |
|---|---|
| Docker | 3 conteneurs |
| pytest | 80 tests, coverage 80% |
| GitHub | Versioning (develop → main) |

---

## Architecture

```
┌─────────────────────────────────────────┐
│           FRONTEND                       │
│        Streamlit :8501                   │
│   7 pages + authentification RBAC        │
└──────────────────┬──────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────┐
│           BACKEND                        │
│         FastAPI :8000                    │
│    30+ routes + pipeline NLP             │
└──────────────────┬──────────────────────┘
                   │ SQLAlchemy ORM
┌──────────────────▼──────────────────────┐
│         BASE DE DONNÉES                  │
│        PostgreSQL :5432                  │
│         6 tables                         │
└─────────────────────────────────────────┘
```

---

## 🐳 Démarrage rapide Docker

### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé
- [Git](https://git-scm.com/) installé

### Étape 1 — Cloner le projet

```bash
git clone https://github.com/othmaneboushabi/Outil-Intelligent-Gestion-Crises.git
cd Outil-Intelligent-Gestion-Crises
git checkout develop
```

### Étape 2 — Lancer les 3 conteneurs

```bash
docker-compose up --build
```

```
Résultat attendu :
─────────────────────────────────────────────
crisis_db  ✅ PostgreSQL :5432 démarré
crisis_api ✅ FastAPI    :8000 démarré
crisis_web ✅ Streamlit  :8501 démarré
```

> ⚠️ Le premier build télécharge SpaCy et les modèles IA — prévoir 5 à 10 minutes.

### Étape 3 — Initialiser les données

Ouvrez Swagger : **http://localhost:8000/docs**

**① Créer l'admin :**
```json
POST /auth/register
{
  "full_name": "Admin",
  "email": "admin@crisis.com",
  "password": "Admin1234",
  "role": "admin",
  "department_id": null
}
```

**② Se connecter et récupérer le token :**
```
POST /auth/login
username : admin@crisis.com
password : Admin1234
→ Copier access_token → Cliquer Authorize → Coller le token
```

**③ Créer les 5 départements :**
```json
POST /departments  →  { "name": "IT",         "description": "Informatique" }
POST /departments  →  { "name": "Finance",     "description": "Finance" }
POST /departments  →  { "name": "RH",          "description": "Ressources Humaines" }
POST /departments  →  { "name": "Logistique",  "description": "Logistique" }
POST /departments  →  { "name": "Marketing",   "description": "Marketing" }
```

**④ Créer les utilisateurs :**
```json
POST /users  →  { "full_name": "Chef IT",      "email": "it@crisis.com",      "password": "User1234", "role": "user", "department_id": 1 }
POST /users  →  { "full_name": "Chef Finance",  "email": "finance@crisis.com", "password": "User1234", "role": "user", "department_id": 2 }
POST /users  →  { "full_name": "Chef RH",       "email": "rh@crisis.com",      "password": "User1234", "role": "user", "department_id": 3 }
```

### Étape 4 — Tester le Dashboard

Ouvrez : **http://localhost:8501**

```
Admin  : admin@crisis.com  / Admin1234
User   : it@crisis.com     / User1234
```

### Commandes Docker utiles

```bash
# Arrêter les conteneurs (données conservées)
docker-compose down

# Arrêter + supprimer toutes les données
docker-compose down -v

# Voir les logs en temps réel
docker-compose logs -f

# Voir les logs d'un seul service
docker-compose logs -f api

# Redémarrer un seul service
docker-compose restart api

# Vérifier l'état des conteneurs
docker-compose ps
```

> 💡 Les données sont conservées dans le volume `postgres_data` entre les redémarrages.
> Pour repartir de zéro : `docker-compose down -v` puis `docker-compose up`.

---

## Installation locale

### Prérequis
- Python 3.11+
- PostgreSQL 15+
- Git

### Étapes

```bash
# 1. Cloner le projet
git clone https://github.com/othmaneboushabi/Outil-Intelligent-Gestion-Crises.git
cd Outil-Intelligent-Gestion-Crises
git checkout develop

# 2. Créer et activer le venv
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Linux/Mac

# 3. Installer les dépendances backend
cd backend
pip install -r requirements.txt

# 4. Installer le modèle SpaCy français
python -m spacy download fr_core_news_md

# 5. Créer la base de données PostgreSQL
# psql -U postgres -c "CREATE DATABASE crisis_db;"

# 6. Configurer les variables d'environnement
cp .env.example .env
# Modifier DATABASE_URL dans .env

# 7. Lancer l'API
uvicorn main:app --reload --port 8000

# 8. Lancer le frontend (nouveau terminal)
cd ../frontend
pip install -r requirements.txt
streamlit run app.py
```

### Accès local
- **API Swagger :** http://localhost:8000/docs
- **Dashboard :** http://localhost:8501

---

## Structure du projet

```
crisis_manager/
├── backend/
│   ├── main.py              # Routes FastAPI (30+)
│   ├── models.py            # Modèles SQLAlchemy (6 tables)
│   ├── schemas.py           # Schémas Pydantic
│   ├── crud.py              # Logique métier
│   ├── auth.py              # JWT + bcrypt
│   ├── database.py          # Connexion PostgreSQL
│   ├── nlp/
│   │   ├── cleaner.py       # Nettoyage texte SpaCy
│   │   ├── ner_engine.py    # Extraction entités NER
│   │   ├── scoring.py       # Formule criticité v2.1
│   │   ├── similarity.py    # Similarité Sentence-BERT
│   │   ├── domino.py        # Graphe effet domino
│   │   ├── summarizer.py    # Résumé Mistral-7B
│   │   └── alert_engine.py  # Déclenchement alertes
│   ├── tests/               # 80 tests pytest
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Page principale + auth
│   ├── pages/
│   │   ├── 0_Alertes.py     # Alertes actives
│   │   ├── 1_Dashboard_Global.py
│   │   ├── 2_Graphiques.py  # Barres + camemberts
│   │   ├── 3_Effet_Domino.py
│   │   ├── 4_Resume_IA.py   # Mistral-7B + PDF
│   │   ├── 5_Mon_Departement.py
│   │   └── 6_Admin_Gestion.py
│   └── requirements.txt
├── Dockerfile
├── Dockerfile.streamlit
├── docker-compose.yml
├── .env.example
├── README.md
└── JOURNAL.md
```

---

## Routes API

### Authentification
| Méthode | Route | Description |
|---|---|---|
| POST | /auth/register | Inscription |
| POST | /auth/login | Connexion → token JWT |
| GET | /auth/me | Profil utilisateur |

### Utilisateurs (Admin)
| Méthode | Route | Description |
|---|---|---|
| GET | /users | Lister tous les users |
| POST | /users | Créer un user |
| PUT | /users/{id} | Modifier un user |
| DELETE | /users/{id} | Désactiver un user |
| PATCH | /users/{id}/toggle | Activer/Désactiver |

### Départements
| Méthode | Route | Description |
|---|---|---|
| GET | /departments | Lister les départements |
| POST | /departments | Créer un département (Admin) |
| PUT | /departments/{id} | Modifier (Admin) |
| DELETE | /departments/{id} | Soft/Hard delete (Admin) |

### Rapports
| Méthode | Route | Description |
|---|---|---|
| GET | /reports | Lister les rapports |
| POST | /reports | Soumettre un rapport + NLP |
| GET | /reports/{id} | Récupérer un rapport |
| PUT | /reports/{id} | Modifier un rapport |

### NLP et Analyse
| Méthode | Route | Description |
|---|---|---|
| POST | /analyze | Analyse IA temps réel |
| GET | /problems/top | Top problèmes (Admin) |
| GET | /alerts/active | Alertes actives (Admin) |

### Domino
| Méthode | Route | Description |
|---|---|---|
| GET | /domino/summary | Résumé graphe domino |
| GET | /domino/simulate | Simulation déblocage |
| GET | /domino/graph-html | Graphe HTML interactif |

### Résumé Exécutif
| Méthode | Route | Description |
|---|---|---|
| GET | /summaries | Lister les résumés |
| POST | /summaries/generate | Générer résumé IA |
| POST | /summaries/regenerate | Régénérer résumé |

---

## Comptes de test

| Rôle | Email | Mot de passe |
|---|---|---|
| Admin | admin@crisis.com | Admin1234 |
| User IT | it@crisis.com | User1234 |
| User Finance | finance@crisis.com | User1234 |
| User RH | rh@crisis.com | User1234 |

---

## Tests

```bash
cd backend
pytest tests/ -v
```

### Résultats
```
80 passed, 0 failed
Coverage : 80%
Durée    : ~60 secondes
```

### Détail des tests
| Fichier | Tests | Description |
|---|---|---|
| test_auth.py | 9 | Login, register, token JWT |
| test_departments.py | 9 | CRUD + soft delete |
| test_users.py | 9 | CRUD + toggle |
| test_reports.py | 10 | Soumission + NLP |
| test_scoring.py | 13 | Formule criticité v2.1 |
| test_nlp.py | 14 | SpaCy + NER + scoring |
| test_domino.py | 8 | Graphe + simulation |
| test_alerts.py | 8 | Seuil + alertes |

---

## Fonctionnalités

### Formule de criticité v2.1
```
score_brut  = (impact × 0.4) + (urgency × 0.3)
            + (nb_deps × 0.2) + (repetitions × 0.1)
bonus       = (impact × urgency) / 25 × 0.5
score_final = min(score_brut + bonus, 5.0)
```

### Niveaux de criticité
| Score | Niveau | Action |
|---|---|---|
| > 4.5 | 🔴 Alerte Maximale | Escalade direction |
| 3.5 – 4.5 | 🟠 Critique | Action immédiate |
| 2.5 – 3.5 | 🟡 Élevé | Traiter cette semaine |
| 1.5 – 2.5 | 🟢 Modéré | Planifier une action |
| ≤ 1.5 | ⚪ Faible | Surveiller |

### Rôles utilisateurs
| Fonctionnalité | User | Admin |
|---|---|---|
| Soumettre rapport | ✅ | ✅ |
| Analyser via IA | ✅ | ✅ |
| Voir ses rapports | ✅ | ✅ |
| Voir tous les rapports | ❌ | ✅ |
| Alertes actives | ❌ | ✅ |
| Dashboard global | ❌ | ✅ |
| Effet domino | ❌ | ✅ |
| Résumé IA | ❌ | ✅ |
| Gérer users/depts | ❌ | ✅ |

---

## Auteur

**Othmane Boushabi**
Génie Informatique — Intelligence Artificielle
EMSI

---

## Licence

Projet académique — EMSI 2026