"""Journal d'audit chaîné par hash.

Chaque ligne contient :
    hash_courant = SHA-256(horodatage|utilisateur|action|entite|entite_id|details|hash_precedent)
La première ligne a hash_precedent = "0" * 64 (genesis).

TOUTE création/modification métier passe par enregistrer(). Aucune exception.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import Audit

HASH_GENESIS = "0" * 64


def _horodatage_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculer_hash(
    horodatage: str,
    utilisateur_id: int | None,
    action: str,
    entite: str,
    entite_id: int | None,
    details: str | None,
    hash_precedent: str,
) -> str:
    """Sérialisation canonique : champs None → chaîne vide, séparateur '|'."""
    contenu = "|".join(
        [
            horodatage,
            "" if utilisateur_id is None else str(utilisateur_id),
            action,
            entite,
            "" if entite_id is None else str(entite_id),
            details or "",
            hash_precedent,
        ]
    )
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def enregistrer(
    db: Session,
    utilisateur_id: int | None,
    action: str,
    entite: str,
    entite_id: int | None = None,
    details: str | None = None,
) -> Audit:
    """Ajoute une ligne chaînée au journal. Flush immédiat (même transaction que l'écriture métier)."""
    derniere = db.execute(select(Audit).order_by(Audit.id.desc()).limit(1)).scalar_one_or_none()
    hash_precedent = derniere.hash_courant if derniere is not None else HASH_GENESIS
    horodatage = _horodatage_utc()
    ligne = Audit(
        horodatage=horodatage,
        utilisateur_id=utilisateur_id,
        action=action,
        entite=entite,
        entite_id=entite_id,
        details=details,
        hash_precedent=hash_precedent,
        hash_courant=calculer_hash(
            horodatage, utilisateur_id, action, entite, entite_id, details, hash_precedent
        ),
    )
    db.add(ligne)
    db.flush()
    return ligne


@dataclass
class Rupture:
    audit_id: int
    raison: str


@dataclass
class ResultatVerification:
    valide: bool
    nb_lignes: int
    ruptures: list[Rupture] = field(default_factory=list)


def verifier_chaine(db: Session) -> ResultatVerification:
    """Recalcule toute la chaîne et retourne les ruptures détectées.

    Détecte : contenu modifié (hash recalculé ≠ hash stocké) et
    chaînon cassé (hash_precedent ≠ hash_courant de la ligne précédente,
    ce qui couvre aussi la suppression d'une ligne intermédiaire).
    """
    lignes = db.execute(select(Audit).order_by(Audit.id.asc())).scalars().all()
    ruptures: list[Rupture] = []
    hash_attendu = HASH_GENESIS
    for ligne in lignes:
        if ligne.hash_precedent != hash_attendu:
            ruptures.append(
                Rupture(audit_id=ligne.id, raison="hash_precedent ne correspond pas à la ligne précédente")
            )
        recalcule = calculer_hash(
            ligne.horodatage,
            ligne.utilisateur_id,
            ligne.action,
            ligne.entite,
            ligne.entite_id,
            ligne.details,
            ligne.hash_precedent,
        )
        if recalcule != ligne.hash_courant:
            ruptures.append(Rupture(audit_id=ligne.id, raison="contenu modifié (hash recalculé différent)"))
        hash_attendu = ligne.hash_courant
    return ResultatVerification(valide=not ruptures, nb_lignes=len(lignes), ruptures=ruptures)


def lister(db: Session, limite: int = 100, decalage: int = 0) -> list[Audit]:
    return list(
        db.execute(select(Audit).order_by(Audit.id.desc()).limit(limite).offset(decalage)).scalars().all()
    )
