"""Agent LangGraph (Groq) qui analyse un fil d'e-mails et remplit un ticket Jira.

On utilise `create_react_agent` (LangGraph) avec :
- un modèle Groq (ChatGroq),
- les tools LangChain de `tools.py`,
- une sortie structurée `JiraTicket` (response_format).

Le graphe exécuté est : agent -> tools -> agent -> ... -> sortie structurée.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from .schema import JiraTicket
from .tools import OUTILS

MODELE_DEFAUT = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Dossier des prompts, à la racine du projet (à côté de src/).
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def charger_prompt(chemin_relatif: str) -> str:
    """Charge un prompt Markdown depuis le dossier `prompts/`."""
    return (PROMPTS / chemin_relatif).read_text(encoding="utf-8")


SYSTEM_PROMPT = charger_prompt("use_cases/email_to_jira.md")


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
