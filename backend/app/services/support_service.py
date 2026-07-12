"""CRUD supports. Un support appartient obligatoirement à un lot.

Ce service ne touche JAMAIS un périphérique : il ne manipule que des
métadonnées saisies ou importées.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import IntrouvableError, ValidationMetierError
from app.models.lot import Lot
from app.models.support import DESTINATIONS, SANTES, STATUTS_SUPPORT, TECHNOLOGIES, Support
from app.services import audit_service, numerotation_service

CHAMPS_MODIFIABLES = (
    "numero_serie",
    "modele",
    "constructeur",
    "capacite_octets",
    "technologie",
    "interface",
    "smart_json",
    "sante",
    "hpa_detecte",
    "dco_detecte",
    "destination",
)


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valider_enums(donnees: dict) -> None:
    if donnees.get("technologie") is not None and donnees["technologie"] not in TECHNOLOGIES:
        raise ValidationMetierError(f"Technologie invalide : {donnees['technologie']}")
    if donnees.get("sante") is not None and donnees["sante"] not in SANTES:
        raise ValidationMetierError(f"État de santé invalide : {donnees['sante']}")
    if donnees.get("destination") is not None and donnees["destination"] not in DESTINATIONS:
        raise ValidationMetierError(f"Destination invalide : {donnees['destination']}")


def creer(db: Session, acteur_id: int, lot_id: int, donnees: dict) -> Support:
    if db.get(Lot, lot_id) is None:
        raise IntrouvableError(f"Lot {lot_id} introuvable")
    _valider_enums(donnees)
    support = Support(
        lot_id=lot_id,
        code_interne=numerotation_service.prochain_code_interne(db),
        statut="EN_ATTENTE",
        cree_le=_maintenant(),
        **{champ: donnees.get(champ) for champ in CHAMPS_MODIFIABLES},
    )
    db.add(support)
    db.flush()
    audit_service.enregistrer(
        db,
        acteur_id,
        "CREATE_SUPPORT",
        "supports",
        support.id,
        json.dumps({"code_interne": support.code_interne, "lot_id": lot_id}, sort_keys=True),
    )
    return support


def obtenir(db: Session, support_id: int) -> Support:
    support = db.get(Support, support_id)
    if support is None:
        raise IntrouvableError(f"Support {support_id} introuvable")
    return support


def lister(db: Session, lot_id: int | None = None, statut: str | None = None) -> list[Support]:
    requete = select(Support).order_by(Support.id)
    if lot_id is not None:
        requete = requete.where(Support.lot_id == lot_id)
    if statut is not None:
        requete = requete.where(Support.statut == statut)
    return list(db.execute(requete).scalars().all())


def rechercher(db: Session, q: str) -> list[Support]:
    """Recherche dans numero_serie, code_interne et modele (sous-chaîne)."""
    motif = f"%{q}%"
    requete = (
        select(Support)
        .where(
            or_(
                Support.numero_serie.like(motif),
                Support.code_interne.like(motif),
                Support.modele.like(motif),
            )
        )
        .order_by(Support.id)
    )
    return list(db.execute(requete).scalars().all())


def modifier(db: Session, acteur_id: int, support_id: int, donnees: dict) -> Support:
    support = obtenir(db, support_id)
    _valider_enums(donnees)
    modifications: dict = {}
    for champ in CHAMPS_MODIFIABLES:
        if champ in donnees and getattr(support, champ) != donnees[champ]:
            modifications[champ] = donnees[champ]
            setattr(support, champ, donnees[champ])
    if modifications:
        audit_service.enregistrer(
            db, acteur_id, "UPDATE_SUPPORT", "supports", support.id, json.dumps(modifications, sort_keys=True)
        )
    return support


def changer_statut(db: Session, acteur_id: int, support_id: int, statut: str) -> Support:
    """Changement de statut manuel (ex: DETRUIT_PHYSIQUEMENT après broyage).

    Les statuts EFFACE_VERIFIE et EFFACE_NON_VERIFIE ne peuvent PAS être posés
    à la main : seuls les rapports de la station (LOT 2) en font foi.
    """
    if statut not in STATUTS_SUPPORT:
        raise ValidationMetierError(f"Statut de support invalide : {statut}")
    if statut in ("EFFACE_VERIFIE", "EFFACE_NON_VERIFIE"):
        raise ValidationMetierError(
            f"Le statut {statut} ne peut être posé que par l'import d'un rapport station"
        )
    support = obtenir(db, support_id)
    ancien = support.statut
    support.statut = statut
    audit_service.enregistrer(
        db,
        acteur_id,
        "STATUT_SUPPORT",
        "supports",
        support.id,
        json.dumps({"ancien": ancien, "nouveau": statut}, sort_keys=True),
    )
    return support
