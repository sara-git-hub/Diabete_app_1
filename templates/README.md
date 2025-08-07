# Diabète Predictor

Une application web pour prédire le risque de diabète chez les patients, avec système d'authentification pour les médecins.

## Fonctionnalités

- 🏥 Système complet d'authentification (inscription/connexion)
- 👨‍⚕️ Gestion des patients avec historique
- 🔍 Filtrage et tri des patients
- 📊 Tableau de bord avec statistiques
- 🤖 Modèle de prédiction du diabète intégré
- 🗑️ Suppression des patients

## Technologies

- Backend: Python avec FastAPI
- Base de données: PostgreSQL
- Modèle ML: Scikit-learn (fichier model.pkl)
- Templates: Jinja2
- Authentification: JWT + sessions

## 📂 Structure des Fichiers

diabete-predictor/
├── main.py            # Point d'entrée de l'application

├── models/            # Modèles de base de données

│   └── database.py

├── templates/         # Templates HTML

│   ├── base.html

│   ├── index.html

│   ├── login.html

│   ├── register.html

│   ├── patients.html

│   └── add_patient.html

└── model.pkl          # Modèle de prédiction

  - Jira: https://sarabouabid.atlassian.net/jira/software/projects/MFLP/boards/34
 