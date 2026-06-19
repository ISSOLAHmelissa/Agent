"""Génère des fils d'e-mails de test dans le dossier `exemples/`.

Chaque scénario = UN SEUL fichier .eml contenant toute la conversation empilée
(les « Répondre à tous » successifs cités dans le corps), comme un .msg Outlook
exporté après plusieurs échanges :

  A. Incident production critique  -> attendu : Bug / priorité Highest
  B. Demande fonctionnelle longue  -> attendu : Story / priorité Medium-High
  C. Amélioration UX               -> attendu : Task/Story / priorité Low-Medium

Usage :
    python3 generer_exemples.py
Puis, dans l'app, déposez via le bouton "+" UN fichier .eml (= un fil complet).

NB : le .msg étant un format binaire propriétaire Outlook non générable en
Python, les exemples sont au format .eml (lu à l'identique par l'application).
Vos vrais .msg Outlook sont, eux, acceptés directement.
"""

from __future__ import annotations

import os
import shutil
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from datetime import datetime, timedelta, timezone

RACINE = os.path.join(os.path.dirname(__file__), "exemples")


def _citer(texte: str, niveau: int = 1) -> str:
    prefixe = ">" * niveau + " "
    return "\n".join(prefixe + ligne for ligne in texte.strip().splitlines())


def construire_thread(nom_fichier, objet, messages):
    """Construit UN e-mail unique empilant tous les échanges.

    messages = liste de (expediteur, dest, dt, corps), du plus ANCIEN au plus
    RÉCENT. Le fichier produit reprend le dernier message en tête, suivi de
    l'historique cité (comme un fil Outlook « Répondre à tous »).
    """
    # On empile progressivement : chaque nouveau message cite tout le bloc
    # précédent (qui contient déjà ses propres citations).
    corps_empile = ""
    exp_prec = dt_prec = None
    for exp, dest, dt, corps in messages:
        if corps_empile:
            entete = f"\nLe {dt_prec:%d/%m/%Y à %H:%M}, {exp_prec} a écrit :\n"
            corps_empile = corps.strip() + "\n" + entete + _citer(corps_empile)
        else:
            corps_empile = corps.strip()
        exp_prec, dt_prec = exp, dt

    dernier_exp, dernier_dest, dernier_dt, _ = messages[-1]
    msg = EmailMessage()
    msg["From"] = dernier_exp
    msg["To"] = dernier_dest
    msg["Subject"] = f"RE: {objet}" if len(messages) > 1 else objet
    msg["Date"] = format_datetime(dernier_dt)
    msg["Message-ID"] = make_msgid(domain="exemple.fr")
    msg.set_content(corps_empile)

    os.makedirs(RACINE, exist_ok=True)
    chemin = os.path.join(RACINE, nom_fichier)
    with open(chemin, "wb") as f:
        f.write(msg.as_bytes())
    return chemin


def base_dt():
    return datetime(2026, 6, 15, 8, 30, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Scénario A — Incident production critique (paiement)
# --------------------------------------------------------------------------- #
def scenario_a():
    t0 = base_dt()
    msgs = [
        (
            "Sophie Marchand <sophie.marchand@retailcorp.fr>",
            "Support Technique <support@plateforme-paiement.fr>",
            t0,
            """Bonjour,

Nous avons un PROBLÈME CRITIQUE en production depuis ce matin 7h45 : la totalité
des paiements par carte bancaire échoue sur notre site marchand (environ 1 200
transactions perdues à l'heure). Les clients reçoivent le message « Erreur
technique, réessayez plus tard » au moment de valider leur panier.

C'est BLOQUANT, nous perdons du chiffre d'affaires en temps réel et notre service
client est submergé. Nous avons besoin d'une intervention immédiate.

Contexte :
- Aucun déploiement de notre côté depuis 4 jours.
- Les paiements PayPal et virement fonctionnent normalement.
- Seul le tunnel carte bancaire (3D Secure) est touché.
- Les logs côté front affichent un timeout sur l'appel à votre API
  /v2/payments/authorize après 30 secondes.

Pouvez-vous regarder en urgence ? Je reste joignable au téléphone toute la
journée. Merci de me tenir informée très régulièrement.

Bien cordialement,
Sophie Marchand
Responsable e-commerce — RetailCorp""",
        ),
        (
            "Support Technique <support@plateforme-paiement.fr>",
            "Sophie Marchand <sophie.marchand@retailcorp.fr>",
            t0 + timedelta(minutes=22),
            """Bonjour Madame Marchand,

Nous prenons en charge votre incident en priorité absolue (ticket interne ouvert).
Nous confirmons observer un taux d'erreur anormal sur l'autorisation 3D Secure
pour plusieurs marchands depuis ~7h40. Notre hypothèse actuelle : un certificat
expiré sur la passerelle de l'un de nos partenaires bancaires.

Pour avancer, pourriez-vous nous préciser :
- l'identifiant de 2 ou 3 transactions échouées (referenceId) ?
- la plage horaire exacte du premier échec constaté ?

Nos équipes infrastructure sont mobilisées. Nous revenons vers vous d'ici 30 min.""",
        ),
        (
            "Sophie Marchand <sophie.marchand@retailcorp.fr>",
            "Support Technique <support@plateforme-paiement.fr>",
            t0 + timedelta(minutes=35),
            """Merci pour la réactivité.

Voici 3 références échouées : TX-8841920, TX-8841977, TX-8842013.
Premier échec constaté à 07:43 précisément (notre monitoring le confirme).

Je précise que l'impact s'aggrave : nous sommes maintenant à plus de 2 000
transactions en échec. La direction me demande un délai de rétablissement.
Pouvez-vous nous donner une estimation, même approximative ?""",
        ),
        (
            "Support Technique <support@plateforme-paiement.fr>",
            "Sophie Marchand <sophie.marchand@retailcorp.fr>",
            t0 + timedelta(minutes=58),
            """Confirmation : le certificat TLS de la passerelle 3DS partenaire a expiré
ce matin à 07:42, ce qui provoque le timeout que vous observez. Le renouvellement
est en cours de déploiement.

Rétablissement estimé : sous 45 minutes. Nous mettrons en place un correctif
définitif (supervision automatique de l'expiration des certificats) pour éviter
toute récidive. Un post-mortem détaillé vous sera transmis.

Nous vous confirmons dès que les paiements repassent au vert.""",
        ),
    ]
    construire_thread(
        "A_incident_paiement.eml",
        "Paiements CB en échec en production - URGENT",
        msgs,
    )


# --------------------------------------------------------------------------- #
# Scénario B — Demande fonctionnelle longue (export comptable multi-devises)
# --------------------------------------------------------------------------- #
def scenario_b():
    t0 = base_dt() - timedelta(days=2)
    msgs = [
        (
            "Karim Benali <karim.benali@financeplus.fr>",
            "Équipe Produit <produit@notre-saas.fr>",
            t0,
            """Bonjour l'équipe Produit,

Dans le cadre de notre clôture trimestrielle, plusieurs de nos clients grands
comptes (dont 3 groupes internationaux) nous remontent un besoin récurrent que
notre outil ne couvre pas encore : un export comptable consolidé multi-devises.

Le besoin en détail :
1. Pouvoir exporter l'ensemble des écritures sur une période donnée (mois,
   trimestre, exercice) dans un fichier unique.
2. Gérer plusieurs devises sources (EUR, USD, GBP, CHF, MAD) avec conversion
   automatique vers une devise de consolidation paramétrable.
3. Appliquer le taux de change à la date de l'opération (et non un taux unique
   de fin de période) — c'est une exigence réglementaire pour certains de nos
   clients.
4. Produire au minimum deux formats : CSV (pour import dans Sage/Cegid) et un
   format FEC conforme à l'administration fiscale française.
5. Inclure une ligne de réconciliation avec les écarts de change.

Côté volumétrie, certains clients ont plus de 400 000 écritures par trimestre,
il faudra donc que l'export soit asynchrone (génération en arrière-plan +
notification quand le fichier est prêt), sinon le navigateur va expirer.

Ce sujet devient prioritaire commercialement : deux renouvellements de contrat
en dépendent pour le trimestre prochain. Pouvez-vous estimer la faisabilité et
nous dire ce qui est envisageable ?

Merci d'avance,
Karim Benali
Customer Success Manager""",
        ),
        (
            "Équipe Produit <produit@notre-saas.fr>",
            "Karim Benali <karim.benali@financeplus.fr>",
            t0 + timedelta(hours=5),
            """Bonjour Karim,

Merci pour ce besoin très bien cadré. Quelques questions pour affiner :

- Pour les taux de change historiques : avez-vous une source de référence
  imposée par les clients (BCE, OANDA, taux interne) ? Cela impacte
  l'intégration d'une API de taux.
- Le format FEC : doit-il être strictement conforme à l'arrêté de 2013, ou une
  variante adaptée suffit-elle dans un premier temps ?
- La devise de consolidation est-elle définie au niveau du compte client, ou
  doit-elle être choisie au moment de l'export ?

De notre côté, l'export asynchrone et la conversion multi-devises sont
réalisables, mais le FEC conforme et la gestion des taux historiques
représentent une charge non négligeable. Nous penchons pour un découpage en
plusieurs lots de livraison.""",
        ),
        (
            "Karim Benali <karim.benali@financeplus.fr>",
            "Équipe Produit <produit@notre-saas.fr>",
            t0 + timedelta(days=1, hours=2),
            """Merci pour le retour, réponses ci-dessous :

- Source des taux : la BCE est acceptée par tous les clients concernés. Un
  client demande OANDA mais peut s'adapter à la BCE dans un premier temps.
- FEC : la conformité stricte à l'arrêté de 2013 est nécessaire, c'est un point
  dur — sans cela l'export n'a pas de valeur pour eux en cas de contrôle fiscal.
- Devise de consolidation : à définir au niveau du compte client (paramètre),
  avec possibilité de surcharger ponctuellement au moment de l'export.

Le découpage en lots me convient. Idéalement, une première version avec
CSV + conversion à la date d'opération + export asynchrone pour la prochaine
clôture, puis le FEC conforme dans un second temps. Est-ce tenable ?""",
        ),
    ]
    construire_thread(
        "B_export_comptable.eml",
        "Besoin : export comptable consolidé multi-devises",
        msgs,
    )


# --------------------------------------------------------------------------- #
# Scénario C — Amélioration UX (filtre de recherche)
# --------------------------------------------------------------------------- #
def scenario_c():
    t0 = base_dt() - timedelta(days=5)
    msgs = [
        (
            "Laura Petit <laura.petit@notre-saas.fr>",
            "Équipe Front <front@notre-saas.fr>",
            t0,
            """Salut l'équipe,

Petit retour d'usage remonté par plusieurs utilisateurs (et que je partage)
sur la page de recherche du catalogue : ce n'est pas urgent, mais ce serait un
vrai confort.

Aujourd'hui, quand on applique des filtres (catégorie, prix, disponibilité),
la liste se recharge mais on perd le scroll et les filtres ne sont pas
mémorisés si on quitte la page puis qu'on revient. Du coup les utilisateurs
refont leur recherche à chaque fois.

Suggestions :
- mémoriser les filtres dans l'URL (paramètres de requête) pour pouvoir
  partager/recharger une recherche ;
- conserver la position de scroll ;
- afficher un petit récapitulatif des filtres actifs avec une croix pour les
  retirer un par un.

Rien de bloquant, à caler quand vous aurez de la place. Merci !""",
        ),
        (
            "Thomas Roy <thomas.roy@notre-saas.fr>",
            "Laura Petit <laura.petit@notre-saas.fr>",
            t0 + timedelta(hours=3),
            """Hello Laura,

Bonne idée, c'est un classique. La mémorisation des filtres dans l'URL est
simple et apporte beaucoup (partage de lien, retour arrière). Le récap des
filtres actifs avec suppression unitaire est faisable aussi.

La conservation du scroll est un peu plus délicate selon la pagination
(infinie vs pages), mais gérable. Je propose qu'on le mette dans le prochain
sprint « confort UX ». Tu as des maquettes ou je pars de l'existant ?""",
        ),
        (
            "Laura Petit <laura.petit@notre-saas.fr>",
            "Thomas Roy <thomas.roy@notre-saas.fr>",
            t0 + timedelta(hours=6),
            """Pas de maquette, pars de l'existant, le composant de filtres actuel est
déjà bien. L'essentiel pour les utilisateurs c'est : URL partageable + récap
des filtres actifs. Le scroll, c'est bonus si c'est trop coûteux.

Merci Thomas, je te laisse estimer.""",
        ),
    ]
    construire_thread(
        "C_filtre_recherche.eml",
        "Amélioration : mémoriser les filtres de recherche",
        msgs,
    )


if __name__ == "__main__":
    # On repart propre (supprime l'ancienne structure multi-fichiers)
    if os.path.isdir(RACINE):
        shutil.rmtree(RACINE)
    scenario_a()
    scenario_b()
    scenario_c()
    print(f"Fichiers .eml générés dans : {RACINE}")
    for f in sorted(os.listdir(RACINE)):
        chemin = os.path.join(RACINE, f)
        print(f"  - exemples/{f}  ({os.path.getsize(chemin)} octets)")
