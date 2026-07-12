"""Consultation des opérations importées (lecture seule : une opération
ne se modifie jamais, c'est une preuve)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import IntrouvableError
from app.models.lot import Lot
from app.models.operation import Operation
from app.models.support import Support


def obtenir(db: Session, operation_id: int) -> Operation:
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise IntrouvableError(f"Opération {operation_id} introuvable")
    return operation


def lister(
    db: Session,
    lot_id: int | None = None,
    client_id: int | None = None,
    support_id: int | None = None,
    resultat: str | None = None,
    technicien_id: int | None = None,
    debut_min: str | None = None,
    debut_max: str | None = None,
) -> list[Operation]:
    requete = select(Operation).order_by(Operation.id)
    if lot_id is not None or client_id is not None:
        requete = requete.join(Support, Operation.support_id == Support.id)
        if lot_id is not None:
            requete = requete.where(Support.lot_id == lot_id)
        if client_id is not None:
            requete = requete.join(Lot, Support.lot_id == Lot.id).where(Lot.client_id == client_id)
    if support_id is not None:
        requete = requete.where(Operation.support_id == support_id)
    if resultat is not None:
        requete = requete.where(Operation.resultat == resultat)
    if technicien_id is not None:
        requete = requete.where(Operation.technicien_id == technicien_id)
    # Les dates ISO-8601 UTC se comparent lexicographiquement.
    if debut_min is not None:
        requete = requete.where(Operation.debut >= debut_min)
    if debut_max is not None:
        requete = requete.where(Operation.debut <= debut_max)
    return list(db.execute(requete).scalars().all())
