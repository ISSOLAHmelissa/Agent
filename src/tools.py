"""Tools LangChain utilisés par l'agent LangGraph pour ancrer son analyse.

Ces outils renvoient des SIGNAUX déterministes (mots-clés, métriques de
complexité) que le LLM consulte pour justifier la priorité et l'estimation,
plutôt que de les "deviner" sans appui.
"""

from __future__ import annotations

import re
from typing import Dict, List

from langchain_core.tools import tool

# Mots-clés -> niveau d'urgence suggéré (du plus fort au plus faible)
MOTS_URGENCE: Dict[str, List[str]] = {
    "Highest": [
        "bloquant", "bloqué", "production", "prod down", "panne", "incident",
        "critique", "urgent", "asap", "immédiat", "ne fonctionne plus",
        "down", "rupture de service", "p1",
    ],
    "High": [
        "dès que possible", "rapidement", "prioritaire", "important",
        "deadline", "échéance", "relance", "client mécontent", "p2",
    ],
    "Low": [
        "quand vous aurez le temps", "pas urgent", "amélioration",
        "suggestion", "idée", "nice to have", "p4",
    ],
}

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


@tool
def detecter_signaux_urgence(texte_email: str) -> dict:
    """Analyse le texte d'un e-mail ou d'un fil d'e-mails et renvoie les signaux
    d'urgence détectés (mots-clés bloquants, mentions de production, ponctuation
    insistante). Sert à déterminer la priorité du ticket Jira."""
    texte = texte_email.lower()
    trouves: Dict[str, List[str]] = {}
    for niveau, mots in MOTS_URGENCE.items():
        presents = [m for m in mots if m in texte]
        if presents:
            trouves[niveau] = presents

    nb_exclamations = texte.count("!")
    nb_majuscules_mots = len(re.findall(r"\b[A-ZÀ-Ÿ]{3,}\b", texte_email))

    if "Highest" in trouves:
        suggestion = "Highest"
    elif "High" in trouves or nb_exclamations >= 3:
        suggestion = "High"
    elif "Low" in trouves:
        suggestion = "Low"
    else:
        suggestion = "Medium"

    return {
        "mots_cles_par_niveau": trouves,
        "nb_points_exclamation": nb_exclamations,
        "nb_mots_majuscules": nb_majuscules_mots,
        "priorite_suggeree": suggestion,
    }


@tool
def evaluer_complexite_thread(texte_email: str) -> dict:
    """Évalue la complexité d'un fil d'e-mails (nombre de messages, de
    participants, longueur, questions ouvertes) afin de proposer une estimation
    en points (échelle de Fibonacci) pour le ticket Jira."""
    nb_messages = max(1, texte_email.count("===== E-MAIL SUIVANT =====") + 1)
    participants = sorted(set(RE_EMAIL.findall(texte_email)))
    nb_questions = texte_email.count("?")
    nb_mots = len(texte_email.split())

    score = nb_messages + len(participants) + nb_questions // 2 + nb_mots // 200
    if score <= 3:
        points = 2
    elif score <= 6:
        points = 3
    elif score <= 10:
        points = 5
    elif score <= 16:
        points = 8
    else:
        points = 13

    return {
        "nb_messages": nb_messages,
        "nb_participants": len(participants),
        "participants": participants,
        "nb_questions": nb_questions,
        "nb_mots": nb_mots,
        "points_suggeres": points,
    }


OUTILS = [detecter_signaux_urgence, evaluer_complexite_thread]
