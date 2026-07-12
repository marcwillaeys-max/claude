"""Gestion des utilisateurs. Aucune suppression : désactivation uniquement."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import AuthentificationError, ConflitError, IntrouvableError
from app.models.utilisateur import ROLES, Utilisateur
from app.services import audit_service


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def creer(
    db: Session,
    acteur_id: int | None,
    identifiant: str,
    nom_complet: str,
    mot_de_passe: str,
    role: str,
) -> Utilisateur:
    if role not in ROLES:
        raise ConflitError(f"Rôle inconnu : {role}")
    existant = db.execute(
        select(Utilisateur).where(Utilisateur.identifiant == identifiant)
    ).scalar_one_or_none()
    if existant is not None:
        raise ConflitError(f"Identifiant déjà utilisé : {identifiant}")
    utilisateur = Utilisateur(
        identifiant=identifiant,
        nom_complet=nom_complet,
        mot_de_passe=security.hacher_mot_de_passe(mot_de_passe),
        role=role,
        actif=1,
        cree_le=_maintenant(),
    )
    db.add(utilisateur)
    db.flush()
    audit_service.enregistrer(
        db,
        acteur_id,
        "CREATE_UTILISATEUR",
        "utilisateurs",
        utilisateur.id,
        json.dumps({"identifiant": identifiant, "role": role}, sort_keys=True),
    )
    return utilisateur


def authentifier(db: Session, identifiant: str, mot_de_passe: str) -> Utilisateur:
    utilisateur = db.execute(
        select(Utilisateur).where(Utilisateur.identifiant == identifiant)
    ).scalar_one_or_none()
    if (
        utilisateur is None
        or not utilisateur.actif
        or not security.verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe)
    ):
        raise AuthentificationError("Identifiant ou mot de passe invalide")
    utilisateur.derniere_conn = _maintenant()
    audit_service.enregistrer(db, utilisateur.id, "LOGIN", "utilisateurs", utilisateur.id)
    return utilisateur


def lister(db: Session) -> list[Utilisateur]:
    return list(db.execute(select(Utilisateur).order_by(Utilisateur.id)).scalars().all())


def desactiver(db: Session, acteur_id: int, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise IntrouvableError(f"Utilisateur {utilisateur_id} introuvable")
    utilisateur.actif = 0
    audit_service.enregistrer(db, acteur_id, "DESACTIVE_UTILISATEUR", "utilisateurs", utilisateur.id)
    return utilisateur


def creer_admin_initial(db: Session, identifiant: str, nom_complet: str, mot_de_passe: str) -> Utilisateur | None:
    """Crée le premier administrateur si la table est vide. Sinon ne fait rien."""
    premier = db.execute(select(Utilisateur).limit(1)).scalar_one_or_none()
    if premier is not None:
        return None
    return creer(db, None, identifiant, nom_complet, mot_de_passe, "ADMINISTRATEUR")
