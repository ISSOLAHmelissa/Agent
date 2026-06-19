"""Interface chatbot Streamlit : déposer des e-mails -> obtenir un ticket Jira.

Lancement :
    streamlit run app.py

Le `st.chat_input` fournit nativement le bouton "Envoyer" et le bouton "+"
(trombone) pour ajouter des pièces jointes.
"""

from __future__ import annotations

import io
import json
import os
import zipfile

import streamlit as st
from dotenv import load_dotenv

from src.email_parser import construire_fil_emails
from src.graph import MODELE_DEFAUT, analyser_emails
from src.jira_client import creer_ticket_jira
from src.schema import JiraTicket
from src.ui_formulaire import formulaire_ticket

load_dotenv()

st.set_page_config(page_title="E-mails → Ticket Jira", page_icon="🎫", layout="centered")


# --------------------------------------------------------------------------- #
# Barre latérale
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️ Configuration")
    modele = st.text_input("Modèle Groq", value=MODELE_DEFAUT)
    cle_ok = bool(os.getenv("GROQ_API_KEY"))
    if cle_ok:
        st.success("Clé GROQ_API_KEY détectée")
    else:
        st.error("GROQ_API_KEY manquante (.env)")
    st.caption(
        "Déposez un ou plusieurs e-mails Outlook (.msg, .eml, .txt) via le bouton **+** "
        "de la zone de saisie, puis **Envoyer**. Le LLM analyse l'échange et "
        "pré-remplit un ticket Jira."
    )
    if st.button("🗑️ Réinitialiser"):
        st.session_state.clear()
        st.rerun()


# --------------------------------------------------------------------------- #
# État
# --------------------------------------------------------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = []  # historique affiché [(role, contenu)]
if "ticket" not in st.session_state:
    st.session_state.ticket = None  # JiraTicket courant
if "attachments" not in st.session_state:
    st.session_state.attachments = []  # [(nom, octets)] des mails déposés

st.title("🎫 Des e-mails au ticket Jira")

# Historique de conversation
for role, contenu in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(contenu)


# --------------------------------------------------------------------------- #
# Saisie : bouton Envoyer + bouton "+" (pièces jointes)
# --------------------------------------------------------------------------- #
saisie = st.chat_input(
    "Décrivez le besoin ou ajoutez les e-mails en pièce jointe…",
    accept_file="multiple",
    file_type=["msg", "eml", "txt", "md"],
)

if saisie:
    texte_libre = (saisie.text or "").strip()
    fichiers = [(f.name, f.getvalue()) for f in (saisie.files or [])]
    # On conserve les mails bruts pour pouvoir les joindre au ticket final.
    st.session_state.attachments = fichiers

    # Bulle utilisateur
    noms = ", ".join(n for n, _ in fichiers) if fichiers else "aucune pièce jointe"
    bulle_user = (texte_libre or "_(analyse des pièces jointes)_") + f"\n\n📎 {noms}"
    st.session_state.messages.append(("user", bulle_user))
    with st.chat_message("user"):
        st.markdown(bulle_user)

    if not (texte_libre or fichiers):
        st.stop()

    if not os.getenv("GROQ_API_KEY"):
        st.error("Impossible d'analyser : la variable GROQ_API_KEY n'est pas définie.")
        st.stop()

    fil = construire_fil_emails(fichiers, texte_libre)

    with st.chat_message("assistant"):
        with st.spinner("Analyse du fil d'e-mails par le LLM…"):
            try:
                ticket, _ = analyser_emails(fil, model_name=modele)
                st.session_state.ticket = ticket
                resume = (
                    f"✅ Analyse terminée à partir de **{len(fichiers) or 1}** "
                    f"élément(s).\n\n"
                    f"- **Titre proposé** : {ticket.summary}\n"
                    f"- **Type** : {ticket.issue_type}\n"
                    f"- **Priorité détectée** : {ticket.priority} "
                    f"({ticket.priority_justification})\n"
                    f"- **Estimation** : {ticket.story_points} points "
                    f"({ticket.estimate_justification})\n\n"
                    "Le formulaire du ticket est éditable ci-dessous."
                )
            except Exception as exc:  # noqa: BLE001
                st.session_state.ticket = None
                resume = f"❌ Erreur pendant l'analyse : `{exc}`"
        st.markdown(resume)
    st.session_state.messages.append(("assistant", resume))


# --------------------------------------------------------------------------- #
# Formulaire de ticket Jira (éditable)
# --------------------------------------------------------------------------- #
ticket: JiraTicket | None = st.session_state.ticket
if ticket is not None:
    st.divider()
    st.subheader("📝 Formulaire du ticket Jira")

    # Formulaire extrait dans un composant réutilisable (src/ui_formulaire.py).
    ticket_final = formulaire_ticket(ticket, st.session_state.attachments)

    if ticket_final is not None:
        # --- Appel (simulé) à l'API Jira pour CRÉER le ticket --------------- #
        with st.spinner("Création du ticket dans Jira…"):
            resultat = creer_ticket_jira(ticket_final)

        if resultat.ok:
            st.success(
                f"✅ Ticket créé dans Jira : **{resultat.key}** "
                f"(HTTP {resultat.status_code})."
                + (" — _réponse simulée, pas d'instance Jira réelle._" if resultat.simule else "")
            )
            st.markdown(f"🔗 [Ouvrir le ticket {resultat.key}]({resultat.url})")
            with st.expander("Détails de l'appel API Jira (payload + réponse)"):
                st.caption(f"POST {os.getenv('JIRA_BASE_URL', 'https://votre-domaine.atlassian.net').rstrip('/')}/rest/api/3/issue")
                st.markdown("**Payload envoyé :**")
                st.json(resultat.payload)
                st.markdown("**Réponse de l'API :**")
                st.json(resultat.response)
        else:
            st.error(
                f"❌ Échec de la création du ticket Jira (HTTP {resultat.status_code}) : "
                f"{resultat.error}"
            )

        st.divider()
        st.markdown("**Ticket validé (export local) :**")
        st.json(ticket_final)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Ticket seul (JSON)",
                data=json.dumps(ticket_final, ensure_ascii=False, indent=2),
                file_name="ticket_jira.json",
                mime="application/json",
            )
        with col_dl2:
            # Paquet ZIP = ticket + e-mails d'origine en pièces jointes.
            tampon = io.BytesIO()
            with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    "ticket_jira.json",
                    json.dumps(ticket_final, ensure_ascii=False, indent=2),
                )
                for nom, data in st.session_state.attachments:
                    zf.writestr(f"pieces_jointes/{nom}", data)
            st.download_button(
                "⬇️ Ticket + e-mails (ZIP)",
                data=tampon.getvalue(),
                file_name="ticket_jira.zip",
                mime="application/zip",
                disabled=not st.session_state.attachments,
                help="Contient le ticket JSON et les e-mails d'origine joints.",
            )
