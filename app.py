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
from src.schema import JiraTicket

load_dotenv()

st.set_page_config(page_title="E-mails → Ticket Jira", page_icon="🎫", layout="centered")

PRIORITES = ["Highest", "High", "Medium", "Low", "Lowest"]
TYPES = ["Story", "Bug", "Task", "Epic", "Sub-task"]


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
        "Déposez un ou plusieurs e-mails (.eml, .txt, .pdf) via le bouton **+** "
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
    file_type=["eml", "msg", "txt", "md", "pdf"],
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

    with st.form("formulaire_ticket"):
        summary = st.text_input("Résumé (titre)", value=ticket.summary)
        col1, col2, col3 = st.columns(3)
        with col1:
            issue_type = st.selectbox(
                "Type", TYPES, index=TYPES.index(ticket.issue_type)
            )
        with col2:
            priority = st.selectbox(
                "Priorité", PRIORITES, index=PRIORITES.index(ticket.priority)
            )
        with col3:
            story_points = st.number_input(
                "Points", min_value=0, value=int(ticket.story_points), step=1
            )

        description = st.text_area("Description", value=ticket.description, height=200)

        st.caption(f"💡 Priorité — {ticket.priority_justification}")
        st.caption(f"💡 Estimation — {ticket.estimate_justification}")

        col4, col5 = st.columns(2)
        with col4:
            labels = st.text_input("Labels (séparés par des virgules)", value=", ".join(ticket.labels))
            reporter = st.text_input("Demandeur", value=ticket.reporter or "")
            estimate_hours = st.text_input(
                "Estimation (heures)",
                value="" if ticket.estimate_hours is None else str(ticket.estimate_hours),
            )
        with col5:
            components = st.text_input("Composants (séparés par des virgules)", value=", ".join(ticket.components))
            assignee = st.text_input("Assigné(e) suggéré(e)", value=ticket.assignee_suggestion or "")
            due_date = st.text_input("Échéance (AAAA-MM-JJ)", value=ticket.due_date or "")

        criteres = st.text_area(
            "Critères d'acceptation (un par ligne)",
            value="\n".join(ticket.acceptance_criteria),
            height=120,
        )

        if st.session_state.attachments:
            noms_pj = ", ".join(n for n, _ in st.session_state.attachments)
            st.markdown(f"**📎 E-mail(s) joint(s) au ticket :** {noms_pj}")
        else:
            st.caption("Aucun fichier e-mail à joindre (analyse de texte saisi).")

        valider = st.form_submit_button("💾 Valider le ticket")

    if valider:
        pieces_jointes = [n for n, _ in st.session_state.attachments]
        ticket_final = {
            "summary": summary,
            "issue_type": issue_type,
            "priority": priority,
            "story_points": int(story_points),
            "estimate_hours": float(estimate_hours) if estimate_hours.strip() else None,
            "description": description,
            "labels": [l.strip() for l in labels.split(",") if l.strip()],
            "components": [c.strip() for c in components.split(",") if c.strip()],
            "acceptance_criteria": [c.strip() for c in criteres.splitlines() if c.strip()],
            "reporter": reporter or None,
            "assignee_suggestion": assignee or None,
            "due_date": due_date or None,
            "pieces_jointes": pieces_jointes,
        }
        st.success("Ticket validé. (Pas d'API Jira : exportez le ticket ci-dessous.)")
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
