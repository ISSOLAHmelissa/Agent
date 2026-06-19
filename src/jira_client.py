"""Client Jira — création de ticket.

⚠️ Pas d'accès à une instance Jira réelle dans ce projet : la fonction
`creer_ticket_jira` **simule** l'appel à l'API REST Jira Cloud
(`POST /rest/api/3/issue`). Elle construit le *payload* exactement comme le
ferait un vrai appel, puis renvoie une réponse réaliste (clé du ticket, URL,
code HTTP 201…).

Pour passer en réel, il suffit de remplacer le bloc « SIMULATION » par l'appel
`requests.post(...)` commenté plus bas — le reste (payload, gestion d'erreurs)
ne change pas.
"""

from __future__ import annotations

import os
import random
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# Map priorité interne -> nom de priorité Jira (souvent identiques par défaut).
_PRIORITE_JIRA = {
    "Highest": "Highest",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
    "Lowest": "Lowest",
}


@dataclass
class ResultatCreation:
    """Réponse (simulée) d'une création de ticket Jira."""

    ok: bool
    key: Optional[str] = None
    id: Optional[str] = None
    url: Optional[str] = None
    status_code: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    simule: bool = True


def construire_payload(ticket: Dict[str, Any], project_key: str) -> Dict[str, Any]:
    """Transforme le ticket interne en *payload* attendu par l'API Jira Cloud.

    Format `POST /rest/api/3/issue` (champs `fields`). La description utilise le
    Markdown brut ici par simplicité ; une vraie intégration la convertirait en
    document ADF (Atlassian Document Format).
    """
    fields: Dict[str, Any] = {
        "project": {"key": project_key},
        "summary": ticket.get("summary", ""),
        "issuetype": {"name": ticket.get("issue_type", "Task")},
        "description": ticket.get("description", ""),
        "labels": ticket.get("labels", []),
        "priority": {"name": _PRIORITE_JIRA.get(ticket.get("priority", "Medium"), "Medium")},
    }

    composants = ticket.get("components") or []
    if composants:
        fields["components"] = [{"name": c} for c in composants]

    if ticket.get("due_date"):
        fields["duedate"] = ticket["due_date"]

    # Critères d'acceptation : pas de champ standard -> ajoutés à la description.
    criteres = ticket.get("acceptance_criteria") or []
    if criteres:
        lignes = "\n".join(f"- [ ] {c}" for c in criteres)
        fields["description"] += f"\n\n## Critères d'acceptation\n{lignes}"

    return {"fields": fields}


def creer_ticket_jira(
    ticket: Dict[str, Any],
    *,
    project_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ResultatCreation:
    """Crée (en simulation) un ticket Jira et renvoie le résultat.

    Lit `JIRA_BASE_URL` / `JIRA_PROJECT_KEY` dans l'environnement si non fournis.
    """
    project_key = project_key or os.getenv("JIRA_PROJECT_KEY", "PROJ")
    base_url = (base_url or os.getenv("JIRA_BASE_URL", "https://votre-domaine.atlassian.net")).rstrip("/")

    payload = construire_payload(ticket, project_key)

    # Validation minimale, comme le ferait l'API (renvoie 400 sinon).
    if not payload["fields"]["summary"].strip():
        return ResultatCreation(
            ok=False,
            status_code=400,
            payload=payload,
            error="Le champ 'summary' est obligatoire.",
        )

    # ----------------------------------------------------------------------- #
    # SIMULATION de l'appel réseau.
    #
    # ➜ Pour brancher la vraie API Jira, remplacer ce bloc par :
    #
    #   import requests
    #   resp = requests.post(
    #       f"{base_url}/rest/api/3/issue",
    #       json=payload,
    #       auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
    #       headers={"Accept": "application/json", "Content-Type": "application/json"},
    #       timeout=15,
    #   )
    #   resp.raise_for_status()
    #   data = resp.json()  # {"id": ..., "key": ..., "self": ...}
    # ----------------------------------------------------------------------- #
    numero = random.randint(100, 9999)
    key = f"{project_key}-{numero}"
    issue_id = "".join(random.choices(string.digits, k=6))
    url = f"{base_url}/browse/{key}"

    reponse_api = {
        "id": issue_id,
        "key": key,
        "self": f"{base_url}/rest/api/3/issue/{issue_id}",
        "created": datetime.now(timezone.utc).isoformat(),
    }

    return ResultatCreation(
        ok=True,
        key=key,
        id=issue_id,
        url=url,
        status_code=201,
        payload=payload,
        response=reponse_api,
        simule=True,
    )
