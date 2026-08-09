"""
Script à lancer UNE SEULE FOIS pour créer le premier compte utilisateur.
Exécution : python creer_admin.py
"""
from werkzeug.security import generate_password_hash
from database import get_connexion, initialiser_bdd

NOM_UTILISATEUR = "admin"
MOT_DE_PASSE_CLAIR = "changeMoi123"  # change ce mot de passe avant utilisation réelle !

initialiser_bdd()

hash_mdp = generate_password_hash(MOT_DE_PASSE_CLAIR)

conn = get_connexion()
conn.execute(
    "INSERT INTO utilisateurs (nom_utilisateur, mot_de_passe) VALUES (?, ?)",
    (NOM_UTILISATEUR, hash_mdp)
)
conn.commit()
conn.close()

print(f"Utilisateur '{NOM_UTILISATEUR}' créé avec succès.")
