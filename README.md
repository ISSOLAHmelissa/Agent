# 🎫 E-mails → Ticket Jira

Interface chatbot qui transforme **un ou plusieurs échanges d'e-mails** (déposés
en pièce jointe) en un **ticket Jira pré-rempli**. L'analyse est faite par un LLM
**Groq**, orchestré avec **LangGraph** et des **tools LangChain**.

> Pas d'accès à l'API Jira : le résultat est un **formulaire éditable** + un
> export JSON du ticket.

## Fonctionnement

```
Chat (Streamlit)                LangGraph (create_react_agent)
┌──────────────────┐            ┌───────────────────────────────────┐
│ bouton +  (PJ)   │  e-mails   │ 1. lecture du fil                 │
│ bouton Envoyer   │ ─────────▶ │ 2. tools LangChain :              │
│                  │            │    - detecter_signaux_urgence     │
│                  │            │    - evaluer_complexite_thread    │
│  formulaire Jira │ ◀───────── │ 3. sortie structurée JiraTicket   │
└──────────────────┘  ticket    └───────────────────────────────────┘
```

Le LLM :
- **résume** l'échange pour proposer un **titre** et une **description** ;
- **détecte la priorité** à partir du ton/contenu (via l'outil d'urgence) ;
- **estime l'effort** en points (via l'outil de complexité) ;
- remplit les autres champs (type, labels, composants, critères d'acceptation…).

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis renseignez GROQ_API_KEY
```

> Sur macOS, utilisez `python3` pour créer le venv. Une fois `.venv` activé,
> les commandes `python` / `pip` / `streamlit` sont disponibles.

Obtenez une clé sur https://console.groq.com/keys

## Lancement

```bash
streamlit run app.py
```

1. Cliquez sur le bouton **+** pour ajouter les e-mails (`.eml`, `.txt`, `.pdf`, `.md`).
2. Cliquez sur **Envoyer**.
3. Ajustez le **formulaire du ticket Jira** puis **Validez** / téléchargez le JSON.

## Jeux de test

Des fils d'e-mails réalistes sont fournis pour tester l'analyse. **Chaque fichier
contient toute la conversation empilée** (plusieurs échanges « Répondre à tous »
dans un seul mail), comme un `.msg` Outlook exporté :

```bash
python3 generer_exemples.py    # (re)génère les .eml dans exemples/
```

| Fichier | Scénario | Résultat attendu |
|---|---|---|
| `exemples/A_incident_paiement.eml` | Incident production CB (4 échanges empilés) | **Bug**, priorité **Highest** |
| `exemples/B_export_comptable.eml` | Demande fonctionnelle longue (3 échanges) | **Story**, priorité **Medium-High**, estimation élevée |
| `exemples/C_filtre_recherche.eml` | Amélioration UX (3 échanges) | **Task/Story**, priorité **Low-Medium** |

Dans l'app, cliquez sur **+** et déposez **un fichier** (= un fil complet).

> **Format `.msg` Outlook** : accepté directement en lecture (paquet
> `extract-msg`) — déposez vos vrais exports Outlook tels quels. Les fichiers
> d'exemple sont au format standard `.eml` car le `.msg` (binaire propriétaire)
> ne peut pas être généré en Python ; il est lu à l'identique par l'application.

## Structure

| Fichier | Rôle |
|---|---|
| `app.py` | Interface chatbot Streamlit (chat + formulaire) |
| `src/graph.py` | Agent LangGraph + modèle Groq + sortie structurée |
| `src/tools.py` | Tools LangChain (urgence, complexité) |
| `src/schema.py` | Schéma Pydantic du ticket Jira |
| `src/email_parser.py` | Lecture/normalisation des pièces jointes |

## Configuration

- `GROQ_API_KEY` *(requis)* : clé API Groq.
- `GROQ_MODEL` *(optionnel)* : modèle, défaut `llama-3.3-70b-versatile`. Doit
  supporter le **tool-calling** (ex. `openai/gpt-oss-120b`).
