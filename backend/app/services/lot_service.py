"""CRUD lots. Un lot se clôture, il ne se supprime pas."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import IntrouvableError, ValidationMetierError
from app.models.client import Client
from app.models.lot import STATUTS_LOT, Lot
from app.services import audit_service, numerotation_service

CHAMPS_MODIFIABLES = ("date_reception", "nb_supports_annonce", "commentaires")


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def creer(
    db: Session,
    acteur_id: int,
    client_id: int,
    date_reception: str,
    nb_supports_annonce: int | None = None,
    commentaires: str | None = None,
) -> Lot:
    if db.get(Client, client_id) is None:
        raise IntrouvableError(f"Client {client_id} introuvable")
    lot = Lot(
        numero_lot=numerotation_service.prochain_numero_lot(db),
        client_id=client_id,
        date_reception=date_reception,
        technicien_id=acteur_id,
        statut="OUVERT",
        nb_supports_annonce=nb_supports_annonce,
        commentaires=commentaires,
        cree_le=_maintenant(),
    )
    db.add(lot)
    db.flush()
    audit_service.enregistrer(
        db,
        acteur_id,
        "CREATE_LOT",
        "lots",
        lot.id,
        json.dumps({"numero_lot": lot.numero_lot, "client_id": client_id}, sort_keys=True),
    )
    return lot


def obtenir(db: Session, lot_id: int) -> Lot:
    lot = db.get(Lot, lot_id)
    if lot is None:
        raise IntrouvableError(f"Lot {lot_id} introuvable")
    return lot


def lister(db: Session, client_id: int | None = None, statut: str | None = None) -> list[Lot]:
    requete = select(Lot).order_by(Lot.id)
    if client_id is not None:
        requete = requete.where(Lot.client_id == client_id)
    if statut is not None:
        requete = requete.where(Lot.statut == statut)
    return list(db.execute(requete).scalars().all())


def modifier(db: Session, acteur_id: int, lot_id: int, donnees: dict) -> Lot:
    lot = obtenir(db, lot_id)
    modifications: dict = {}
    for champ in CHAMPS_MODIFIABLES:
        if champ in donnees and getattr(lot, champ) != donnees[champ]:
            modifications[champ] = donnees[champ]
            setattr(lot, champ, donnees[champ])
    if "statut" in donnees and donnees["statut"] != lot.statut:
        changer_statut(db, acteur_id, lot, donnees["statut"])
    elif modifications:
        audit_service.enregistrer(
            db, acteur_id, "UPDATE_LOT", "lots", lot.id, json.dumps(modifications, sort_keys=True)
        )
    return lot


def changer_statut(db: Session, acteur_id: int, lot: Lot, statut: str) -> Lot:
    if statut not in STATUTS_LOT:
        raise ValidationMetierError(f"Statut de lot invalide : {statut}")
    if lot.statut == "CLOTURE":
        raise ValidationMetierError("Un lot clôturé ne peut plus changer de statut")
    ancien = lot.statut
    lot.statut = statut
    if statut == "CLOTURE":
        lot.cloture_le = _maintenant()
    audit_service.enregistrer(
        db,
        acteur_id,
        "STATUT_LOT",
        "lots",
        lot.id,
        json.dumps({"ancien": ancien, "nouveau": statut}, sort_keys=True),
    )
    return lot


def cloturer(db: Session, acteur_id: int, lot_id: int) -> Lot:
    return changer_statut(db, acteur_id, obtenir(db, lot_id), "CLOTURE")
