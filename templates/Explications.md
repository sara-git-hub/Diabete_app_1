# Explication Technique - Diabète Predictor

## Architecture

L'application suit une architecture MVC (Modèle-Vue-Contrôleur) avec :

- **Modèles** : Définis dans `models/database.py` avec SQLAlchemy
- **Vues** : Templates Jinja2 dans le dossier `templates/`
- **Contrôleurs** : Routes FastAPI dans `main.py`

## Fonctionnement clé

### 1. Authentification

- **Inscription** : Hash bcrypt du mot de passe
- **Connexion** : Vérification des identifiants + création de session
- **Sécurité** : Middleware de session avec clé secrète

### 2. Gestion des Patients

- **Ajout** : Formulaire avec prédiction en temps réel
- **Liste** : Filtrage et tri dynamique
- **Suppression** : Avec confirmation

### 3. Prédiction du Diabète

Le modèle ML (`model.pkl`) utilise 5 caractéristiques :
1. Glucose (mg/dL)
2. Pression artérielle
3. IMC
4. Pedigree diabète
5. Âge

La prédiction retourne :
- Résultat (0: Non diabétique, 1: Diabétique)
- Niveau de confiance (%)