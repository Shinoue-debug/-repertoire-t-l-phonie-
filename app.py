import csv
import io
import os
import re
import smtplib
from email.message import EmailMessage
from functools import wraps

from flask import Flask, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connexion, initialiser_bdd

app = Flask(__name__)
app.secret_key = "change-cette-cle-secrete"  # à remplacer par une vraie clé secrète

# Toute l'application (routes, logique métier, accès aux données, rendu HTML)
# vit dans ce seul fichier / ce seul projet Flask : c'est ça, un monolithe.


def connexion_requise(fonction):
    """Décorateur qui protège une route : redirige vers /login si non connecté."""
    @wraps(fonction)
    def wrapper(*args, **kwargs):
        if "utilisateur_id" not in session:
            return redirect(url_for("login"))
        return fonction(*args, **kwargs)
    return wrapper


def normaliser_tags(texte):
    """Convertit une chaîne de tags en liste propre et sans doublons."""
    if not texte:
        return []

    tags = []
    for morceau in re.split(r"[,;\n]+", texte):
        tag = morceau.strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def enregistrer_tags(conn, contact_id, tags):
    """Associe un contact à ses tags, en remplaçant les anciennes associations."""
    conn.execute("DELETE FROM contact_tags WHERE contact_id = ?", (contact_id,))
    for nom_tag in tags:
        tag = conn.execute("SELECT id FROM tags WHERE nom = ?", (nom_tag,)).fetchone()
        if tag is None:
            cursor = conn.execute("INSERT INTO tags (nom) VALUES (?)", (nom_tag,))
            tag_id = cursor.lastrowid
        else:
            tag_id = tag["id"]
        conn.execute(
            "INSERT INTO contact_tags (contact_id, tag_id) VALUES (?, ?)",
            (contact_id, tag_id),
        )


def importer_contacts_depuis_rows(conn, rows):
    """Importe une liste de dictionnaires en base de données."""
    contacts_importes = []
    for row in rows:
        nom = (row.get("nom") or "").strip()
        prenom = (row.get("prenom") or "").strip()
        if not nom or not prenom:
            continue

        telephone = (row.get("telephone") or "").strip()
        email = (row.get("email") or "").strip()
        notes = (row.get("notes") or "").strip()
        tags = normaliser_tags(row.get("tags") or row.get("tag") or "")

        cursor = conn.execute(
            "INSERT INTO contacts (nom, prenom, telephone, email, notes) VALUES (?, ?, ?, ?, ?)",
            (nom, prenom, telephone, email, notes),
        )
        contact_id = cursor.lastrowid
        enregistrer_tags(conn, contact_id, tags)
        contacts_importes.append({"id": contact_id, "nom": nom, "prenom": prenom})
    conn.commit()
    return contacts_importes


def envoyer_email_contact_ajoute(contact_email, nom, prenom):
    """Envoie un e-mail de notification si la configuration SMTP est présente."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "no-reply@example.com")
    smtp_to = contact_email or os.getenv("SMTP_TO")

    if not smtp_host or not smtp_to:
        return False

    msg = EmailMessage()
    msg["Subject"] = "Nouveau contact ajouté"
    msg["From"] = smtp_from
    msg["To"] = smtp_to
    msg.set_content(
        f"Bonjour,\n\nLe contact {prenom} {nom} a bien été ajouté à la base.\n\n"
        "Ceci est un message automatique."
    )

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False


@app.route("/login", methods=["GET", "POST"])
def login():
    erreur = ""
    if request.method == "POST":
        nom_utilisateur = request.form.get("nom_utilisateur", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")

        conn = get_connexion()
        utilisateur = conn.execute(
            "SELECT * FROM utilisateurs WHERE nom_utilisateur = ?",
            (nom_utilisateur,)
        ).fetchone()
        conn.close()

        if utilisateur and check_password_hash(utilisateur["mot_de_passe"], mot_de_passe):
            session.clear()
            session["utilisateur_id"] = utilisateur["id"]
            session["nom_utilisateur"] = utilisateur["nom_utilisateur"]
            return redirect(url_for("index"))
        else:
            erreur = "Identifiants incorrects."

    return render_template("login.html", erreur=erreur)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@connexion_requise
def index():
    conn = get_connexion()
    contacts_db = conn.execute("SELECT * FROM contacts ORDER BY date_ajout DESC").fetchall()
    contacts = []
    for contact in contacts_db:
        tags = conn.execute(
            """
            SELECT t.nom
            FROM tags t
            JOIN contact_tags ct ON ct.tag_id = t.id
            WHERE ct.contact_id = ?
            ORDER BY t.nom
            """,
            (contact["id"],),
        ).fetchall()
        contact_data = dict(contact)
        contact_data["tags"] = [tag["nom"] for tag in tags]
        contacts.append(contact_data)
    conn.close()
    return render_template("index.html", contacts=contacts)


@app.route("/ajouter", methods=["GET", "POST"])
@connexion_requise
def ajouter_contact():
    erreur = ""
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        telephone = request.form.get("telephone", "").strip()
        email = request.form.get("email", "").strip()
        notes = request.form.get("notes", "").strip()
        tags = normaliser_tags(request.form.get("tags", ""))

        if not nom or not prenom:
            erreur = "Le nom et le prénom sont obligatoires."
        else:
            conn = get_connexion()
            cursor = conn.execute(
                "INSERT INTO contacts (nom, prenom, telephone, email, notes) VALUES (?, ?, ?, ?, ?)",
                (nom, prenom, telephone, email, notes)
            )
            enregistrer_tags(conn, cursor.lastrowid, tags)
            conn.commit()
            conn.close()
            envoyer_email_contact_ajoute(email, nom, prenom)
            return redirect(url_for("index"))

    return render_template("form.html", contact=None, erreur=erreur, contact_tags=[])


@app.route("/modifier/<int:id>", methods=["GET", "POST"])
@connexion_requise
def modifier_contact(id):
    conn = get_connexion()
    contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (id,)).fetchone()

    if not contact:
        conn.close()
        return redirect(url_for("index"))

    erreur = ""
    contact_tags = []
    tags = conn.execute(
        """
        SELECT t.nom
        FROM tags t
        JOIN contact_tags ct ON ct.tag_id = t.id
        WHERE ct.contact_id = ?
        ORDER BY t.nom
        """,
        (id,),
    ).fetchall()
    contact_tags = [tag["nom"] for tag in tags]

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        telephone = request.form.get("telephone", "").strip()
        email = request.form.get("email", "").strip()
        notes = request.form.get("notes", "").strip()
        tags = normaliser_tags(request.form.get("tags", ""))

        if not nom or not prenom:
            erreur = "Le nom et le prénom sont obligatoires."
        else:
            conn.execute(
                "UPDATE contacts SET nom=?, prenom=?, telephone=?, email=?, notes=? WHERE id=?",
                (nom, prenom, telephone, email, notes, id)
            )
            enregistrer_tags(conn, id, tags)
            conn.commit()
            conn.close()
            return redirect(url_for("index"))

    conn.close()
    return render_template("form.html", contact=contact, erreur=erreur, contact_tags=contact_tags)


@app.route("/supprimer/<int:id>")
@connexion_requise
def supprimer_contact(id):
    conn = get_connexion()
    conn.execute("DELETE FROM contacts WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/exporter")
@connexion_requise
def exporter_contacts():
    conn = get_connexion()
    contacts = conn.execute("SELECT * FROM contacts ORDER BY date_ajout DESC").fetchall()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["nom", "prenom", "telephone", "email", "notes", "tags"])
    writer.writeheader()

    for contact in contacts:
        tags = conn.execute(
            """
            SELECT t.nom
            FROM tags t
            JOIN contact_tags ct ON ct.tag_id = t.id
            WHERE ct.contact_id = ?
            ORDER BY t.nom
            """,
            (contact["id"],),
        ).fetchall()
        writer.writerow({
            "nom": contact["nom"],
            "prenom": contact["prenom"],
            "telephone": contact["telephone"],
            "email": contact["email"],
            "notes": contact["notes"],
            "tags": ", ".join(tag["nom"] for tag in tags),
        })

    conn.close()
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=contacts.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


@app.route("/importer", methods=["GET", "POST"])
@connexion_requise
def importer_contacts():
    erreur = ""
    if request.method == "POST":
        fichier = request.files.get("fichier")
        if not fichier or fichier.filename == "":
            erreur = "Sélectionne un fichier CSV à importer."
        else:
            contenu = fichier.stream.read().decode("utf-8-sig")
            lecteur = csv.DictReader(io.StringIO(contenu))
            rows = [row for row in lecteur if any((value or "").strip() for value in row.values())]
            if not rows:
                erreur = "Le fichier ne contient aucune donnée exploitable."
            else:
                conn = get_connexion()
                importer_contacts_depuis_rows(conn, rows)
                conn.close()
                return redirect(url_for("index"))

    return render_template("importer.html", erreur=erreur)


if __name__ == "__main__":
    initialiser_bdd()
    app.run(debug=True)
