from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.support import Support
from app.models.utilisateur import Utilisateur
from app.schemas.support import (
    SupportChangementStatut,
    SupportCreation,
    SupportModification,
    SupportSortie,
)
from app.services import support_service

router = APIRouter(prefix="/api/v1/supports", tags=["supports"])


@router.post("", response_model=SupportSortie, status_code=201)
def creer_support(
    donnees: SupportCreation,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Support:
    corps = donnees.model_dump()
    lot_id = corps.pop("lot_id")
    return support_service.creer(db, acteur.id, lot_id, corps)


@router.get("", response_model=list[SupportSortie])
def lister_supports(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
    lot_id: int | None = None,
    statut: str | None = None,
) -> list[Support]:
    return support_service.lister(db, lot_id=lot_id, statut=statut)


@router.get("/{support_id}", response_model=SupportSortie)
def obtenir_support(
    support_id: int,
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Support:
    return support_service.obtenir(db, support_id)


@router.patch("/{support_id}", response_model=SupportSortie)
def modifier_support(
    support_id: int,
    donnees: SupportModification,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Support:
    return support_service.modifier(db, acteur.id, support_id, donnees.model_dump(exclude_unset=True))


@router.post("/{support_id}/statut", response_model=SupportSortie)
def changer_statut_support(
    support_id: int,
    donnees: SupportChangementStatut,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Support:
    return support_service.changer_statut(db, acteur.id, support_id, donnees.statut)
