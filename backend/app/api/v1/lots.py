from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.lot import Lot
from app.models.utilisateur import Utilisateur
from app.schemas.lot import LotCreation, LotModification, LotSortie
from app.services import lot_service

router = APIRouter(prefix="/api/v1/lots", tags=["lots"])


@router.post("", response_model=LotSortie, status_code=201)
def creer_lot(
    donnees: LotCreation,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Lot:
    return lot_service.creer(
        db,
        acteur.id,
        client_id=donnees.client_id,
        date_reception=donnees.date_reception,
        nb_supports_annonce=donnees.nb_supports_annonce,
        commentaires=donnees.commentaires,
    )


@router.get("", response_model=list[LotSortie])
def lister_lots(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
    client_id: int | None = None,
    statut: str | None = None,
) -> list[Lot]:
    return lot_service.lister(db, client_id=client_id, statut=statut)


@router.get("/{lot_id}", response_model=LotSortie)
def obtenir_lot(
    lot_id: int,
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Lot:
    return lot_service.obtenir(db, lot_id)


@router.patch("/{lot_id}", response_model=LotSortie)
def modifier_lot(
    lot_id: int,
    donnees: LotModification,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Lot:
    return lot_service.modifier(db, acteur.id, lot_id, donnees.model_dump(exclude_unset=True))


@router.post("/{lot_id}/cloturer", response_model=LotSortie)
def cloturer_lot(
    lot_id: int,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("RESPONSABLE"))],
) -> Lot:
    return lot_service.cloturer(db, acteur.id, lot_id)
