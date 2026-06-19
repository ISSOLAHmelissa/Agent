"""Lecture et normalisation des pièces jointes (e-mails) déposées dans le chat.

Formats gérés :
- .eml          : e-mail RFC822 (extraction En-têtes + corps texte)
- .txt / .md    : texte brut
- .pdf          : texte extrait via pypdf (si installé)
- autres        : tentative de décodage UTF-8
"""

from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser
from typing import List, Tuple

SEPARATEUR = "\n\n===== E-MAIL SUIVANT =====\n\n"


def _strip_html(html: str) -> str:
    """Nettoyage très basique du HTML quand aucun corps texte n'est disponible."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    texte = re.sub(r"<[^>]+>", " ", html)
    texte = re.sub(r"&nbsp;", " ", texte)
    texte = re.sub(r"[ \t]+", " ", texte)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", texte).strip()


def _parse_eml(data: bytes, nom: str) -> str:
    msg = BytesParser(policy=policy.default).parsebytes(data)

    entetes = [
        f"De      : {msg.get('From', '?')}",
        f"À       : {msg.get('To', '?')}",
        f"Date    : {msg.get('Date', '?')}",
        f"Objet   : {msg.get('Subject', '?')}",
    ]

    corps = ""
    try:
        partie = msg.get_body(preferencelist=("plain", "html"))
        if partie is not None:
            contenu = partie.get_content()
            if partie.get_content_type() == "text/html":
                corps = _strip_html(contenu)
            else:
                corps = contenu.strip()
    except Exception:
        corps = "(corps de l'e-mail illisible)"

    return f"--- Fichier : {nom} ---\n" + "\n".join(entetes) + "\n\n" + corps


def _parse_msg(data: bytes, nom: str) -> str:
    """Lecture d'un e-mail Outlook .msg (nécessite le paquet `extract-msg`)."""
    try:
        import os as _os
        import tempfile

        import extract_msg

        with tempfile.NamedTemporaryFile(suffix=".msg", delete=False) as tmp:
            tmp.write(data)
            chemin = tmp.name
        try:
            msg = extract_msg.openMsg(chemin)
            entetes = [
                f"De      : {msg.sender or '?'}",
                f"À       : {msg.to or '?'}",
                f"Date    : {msg.date or '?'}",
                f"Objet   : {msg.subject or '?'}",
            ]
            corps = (msg.body or "").strip()
            return f"--- Fichier : {nom} (Outlook .msg) ---\n" + "\n".join(entetes) + "\n\n" + corps
        finally:
            _os.unlink(chemin)
    except ModuleNotFoundError:
        return (
            f"--- Fichier : {nom} (.msg non lu : installez `extract-msg` "
            "via `pip install extract-msg`) ---"
        )
    except Exception as exc:  # fichier .msg corrompu / illisible
        return f"--- Fichier : {nom} (.msg non extrait : {exc}) ---"


def _parse_pdf(data: bytes, nom: str) -> str:
    try:
        import io

        from pypdf import PdfReader

        lecteur = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in lecteur.pages]
        return f"--- Fichier : {nom} (PDF) ---\n" + "\n".join(pages).strip()
    except Exception as exc:  # pypdf absent ou PDF non lisible
        return f"--- Fichier : {nom} (PDF non extrait : {exc}) ---"


def parse_uploaded_file(nom: str, data: bytes) -> str:
    """Convertit une pièce jointe (nom + octets) en texte normalisé."""
    ext = nom.lower().rsplit(".", 1)[-1] if "." in nom else ""
    if ext == "eml":
        return _parse_eml(data, nom)
    if ext == "msg":
        return _parse_msg(data, nom)
    if ext == "pdf":
        return _parse_pdf(data, nom)
    # txt, md, et tout le reste -> décodage texte
    return f"--- Fichier : {nom} ---\n" + data.decode("utf-8", errors="replace").strip()


def construire_fil_emails(fichiers: List[Tuple[str, bytes]], texte_libre: str = "") -> str:
    """Assemble toutes les pièces jointes (+ éventuel texte tapé) en un seul fil.

    `fichiers` : liste de tuples (nom_fichier, octets).
    `texte_libre` : message éventuellement saisi par l'utilisateur dans le chat.
    """
    blocs = [parse_uploaded_file(nom, data) for nom, data in fichiers]
    if texte_libre.strip():
        blocs.insert(0, f"--- Message de l'utilisateur ---\n{texte_libre.strip()}")
    return SEPARATEUR.join(blocs)
