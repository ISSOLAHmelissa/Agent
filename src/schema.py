"""Schéma Pydantic décrivant les champs d'un ticket Jira.

Les descriptions de chaque champ sont LUES par le LLM pour savoir quoi remplir :
elles font donc partie intégrante du prompt. À soigner.
"""

from __future__ import annotations

from typing import List, Optional
from typing import Literal

from pydantic import BaseModel, Field


IssueType = Literal["Story", "Bug", "Task", "Epic", "Sub-task"]
Priority = Literal["Highest", "High", "Medium", "Low", "Lowest"]


class JiraTicket(BaseModel):
    """Ticket Jira reconstruit à partir de l'analyse d'un ou plusieurs e-mails."""

    summary: str = Field(
        ...,
        description=(
            "Titre court et explicite du ticket (max ~120 caractères), "
            "rédigé en français, qui résume la demande principale."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "Description du ticket en français, au format Markdown. Il s'agit "
            "d'un RÉSUMÉ synthétique de l'échange d'e-mails : contexte, problème "
            "ou besoin, et ce qui est attendu. Ne pas recopier les e-mails, "
            "les reformuler de façon concise."
        ),
    )
    issue_type: IssueType = Field(
        ...,
        description=(
            "Type de ticket déduit du contenu : 'Bug' pour une anomalie, "
            "'Story' pour un besoin fonctionnel utilisateur, 'Task' pour une "
            "tâche technique, 'Epic' pour un grand chantier, 'Sub-task' pour "
            "une sous-tâche."
        ),
    )

    priority: Priority = Field(
        ...,
        description=(
            "Priorité détectée à partir du ton et du contenu des e-mails. "
            "'Highest' = bloquant/production en panne/urgent, jusqu'à 'Lowest' "
            "= simple amélioration sans urgence. S'appuyer sur l'outil de "
            "détection des signaux d'urgence."
        ),
    )
    priority_justification: str = Field(
        ...,
        description="Phrase justifiant le niveau de priorité choisi (indices relevés dans les e-mails).",
    )

    story_points: int = Field(
        ...,
        description=(
            "Estimation de l'effort en points (échelle de Fibonacci : "
            "1, 2, 3, 5, 8, 13, 21). S'appuyer sur l'outil d'évaluation de "
            "complexité du fil de discussion."
        ),
    )
    estimate_hours: Optional[float] = Field(
        None,
        description="Estimation indicative en heures de travail, si pertinent.",
    )
    estimate_justification: str = Field(
        ...,
        description="Phrase justifiant l'estimation (complexité, nombre d'inconnues, ampleur).",
    )

    labels: List[str] = Field(
        default_factory=list,
        description="Étiquettes pertinentes (mots-clés courts, sans espaces), ex: ['authentification', 'mobile'].",
    )
    components: List[str] = Field(
        default_factory=list,
        description="Composants applicatifs concernés, ex: ['Backend', 'API Paiement'].",
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Critères d'acceptation déduits de l'échange (liste de conditions à vérifier).",
    )

    assignee_suggestion: Optional[str] = Field(
        None,
        description="Personne suggérée pour traiter le ticket si l'e-mail le laisse deviner, sinon null.",
    )
    reporter: Optional[str] = Field(
        None,
        description="Auteur de la demande (expéditeur principal de l'e-mail), sinon null.",
    )
    due_date: Optional[str] = Field(
        None,
        description="Date d'échéance au format AAAA-MM-JJ si une échéance est mentionnée, sinon null.",
    )
