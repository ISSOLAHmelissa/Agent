"""Agent LangGraph (Groq) qui analyse un fil d'e-mails et remplit un ticket Jira.

On utilise `create_react_agent` (LangGraph) avec :
- un modèle Groq (ChatGroq),
- les tools LangChain de `tools.py`,
- une sortie structurée `JiraTicket` (response_format).

Le graphe exécuté est : agent -> tools -> agent -> ... -> sortie structurée.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from .schema import JiraTicket
from .tools import OUTILS

MODELE_DEFAUT = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """Tu es un assistant qui transforme des échanges d'e-mails en \
tickets Jira prêts à l'emploi, pour une équipe francophone.

Méthode à suivre, dans l'ordre :
1. Lis attentivement l'intégralité du fil d'e-mails fourni.
2. Appelle l'outil `detecter_signaux_urgence` pour identifier le niveau \
d'urgence à partir du contenu, puis `evaluer_complexite_thread` pour estimer \
l'effort.
3. Rédige ensuite le ticket en français :
   - un titre (summary) court et explicite,
   - une description qui RÉSUME l'échange (contexte, problème/besoin, attendu) \
sans recopier les e-mails,
   - le type de ticket le plus adapté,
   - la priorité (en t'appuyant sur les signaux d'urgence) avec sa \
justification,
   - une estimation en points (en t'appuyant sur la complexité) avec sa \
justification,
   - les labels, composants et critères d'acceptation déductibles,
   - le demandeur (reporter) et une éventuelle échéance si mentionnée.

Sois fidèle au contenu : n'invente pas d'informations absentes. Si un champ \
n'est pas déductible, laisse-le vide ou null."""


def build_agent(model_name: Optional[str] = None):
    """Construit l'agent LangGraph avec sortie structurée JiraTicket."""
    modele = ChatGroq(
        model=model_name or MODELE_DEFAUT,
        temperature=0,
        max_tokens=4096,
    )
    return create_react_agent(
        modele,
        tools=OUTILS,
        prompt=SYSTEM_PROMPT,
        response_format=JiraTicket,
    )


def analyser_emails(
    texte_fil: str, model_name: Optional[str] = None
) -> Tuple[JiraTicket, list]:
    """Lance l'agent sur un fil d'e-mails et renvoie (ticket, messages bruts)."""
    agent = build_agent(model_name)
    resultat = agent.invoke(
        {"messages": [("human", f"Voici le fil d'e-mails à analyser :\n\n{texte_fil}")]}
    )
    ticket: JiraTicket = resultat["structured_response"]
    return ticket, resultat["messages"]
