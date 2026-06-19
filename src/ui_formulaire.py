"""Composant UI réutilisable : formulaire éditable d'un ticket Jira (Streamlit).

Découplé de l'application : ce module ne connaît ni l'agent, ni le client Jira,
ni l'export. Il fait UNE chose — afficher le formulaire d'un ticket et renvoyer
le ticket édité sous forme de `dict` quand l'utilisateur valide.

    ticket_final = formulaire_ticket(ticket, attachments)
    if ticket_final is not None:        # l'utilisateur a cliqué « Valider »
        ...                              # à toi de créer/exporter ensuite

Ainsi le même formulaire peut servir dans n'importe quelle app Streamlit, et la
décision de « quoi faire après validation » (créer dans Jira, exporter…) reste
à l'appelant.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

PRIORITES = ["Highest", "High", "Medium", "Low", "Lowest"]
TYPES = ["Story", "Bug", "Task", "Epic", "Sub-task"]

# Type d'une pièce jointe : (nom_fichier, octets)
PieceJointe = Tuple[str, bytes]


def formulaire_ticket(
    ticket: Any,
    attachments: Optional[List[PieceJointe]] = None,
    *,
    cle_formulaire: str = "formulaire_ticket",
) -> Optional[Dict[str, Any]]:
    """Affiche le formulaire éditable d'un ticket Jira.

    `ticket` : un objet `JiraTicket` (ou tout objet exposant les mêmes
    attributs : summary, description, issue_type, priority, ...).
    `attachments` : liste de (nom, octets) affichée comme pièces jointes.

    Retourne le dict du ticket édité si l'utilisateur a cliqué « Valider »,
    sinon `None`.
    """
    attachments = attachments or []

    with st.form(cle_formulaire):
        summary = st.text_input("Résumé (titre)", value=ticket.summary)
        col1, col2, col3 = st.columns(3)
        with col1:
            issue_type = st.selectbox("Type", TYPES, index=TYPES.index(ticket.issue_type))
        with col2:
            priority = st.selectbox("Priorité", PRIORITES, index=PRIORITES.index(ticket.priority))
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

        if attachments:
            noms_pj = ", ".join(n for n, _ in attachments)
            st.markdown(f"**📎 E-mail(s) joint(s) au ticket :** {noms_pj}")
        else:
            st.caption("Aucun fichier e-mail à joindre (analyse de texte saisi).")

        valider = st.form_submit_button("💾 Valider le ticket")

    if not valider:
        return None

    return {
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
        "pieces_jointes": [n for n, _ in attachments],
    }
