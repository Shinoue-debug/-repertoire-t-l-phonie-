# Gestion de Contacts — Application Monolithique (Python + Flask)

Même application que la version PHP, réécrite en Python avec Flask : authentification, logique métier et accès aux données restent réunis dans **un seul projet**, déployé comme **un seul bloc** — c'est le principe d'une architecture monolithique, indépendamment du langage utilisé.

## Fonctionnalités

- Connexion / déconnexion (session Flask, mot de passe haché avec `werkzeug.security`)
- CRUD complet sur les contacts : lister, ajouter, modifier, supprimer
- Tags pour distinguer et classer les contacts
- Exportation des contacts au format CSV
- Importation de contacts depuis un fichier CSV
- Notification par e-mail lors de l’ajout d’un contact (si une configuration SMTP est fournie)
- Base de données SQLite (fichier unique, aucune installation de serveur nécessaire)

## Structure du projet

```
app-monolithe-py/
├── app.py                 # toutes les routes (login, CRUD) + logique métier
├── database.py            # connexion SQLite + création des tables
├── creer_admin.py         # script à lancer une fois pour créer le 1er compte
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── index.html
│   └── form.html          # formulaire partagé ajout/modification
└── static/
    └── style.css
```

## Installation

```bash
python -m venv venv
source venv/bin/activate      # sous Windows : venv\Scripts\activate
pip install -r requirements.txt

python creer_admin.py         # crée le compte admin / changeMoi123
python app.py                 # lance l'appli sur http://127.0.0.1:5000
```

Va ensuite sur `http://127.0.0.1:5000/login` et connecte-toi.

## Pourquoi c'est un monolithe ?

- **Un seul dépôt de code** : routes, logique et accès aux données vivent dans `app.py`.
- **Un seul processus / une seule commande** : `python app.py` lance toute l'application.
- **Une seule base de données** (SQLite) partagée par toutes les routes.
- Aucune séparation en services indépendants : la route `/` appelle directement la base de données, sans passer par une API interne séparée.

Pour l'exposé : si le projet grossissait (plusieurs équipes, forte charge), on pourrait extraire l'authentification et la gestion des contacts en deux services séparés communiquant par API — c'est la transition vers une architecture microservices.
