from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.client import Client
from app.models.utilisateur import Utilisateur
from app.schemas.client import ClientCreation, ClientModification, ClientSortie
from app.services import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.post("", response_model=ClientSortie, status_code=201)
def creer_client(
    donnees: ClientCreation,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Client:
    return client_service.creer(db, acteur.id, donnees.model_dump())


@router.get("", response_model=list[ClientSortie])
def lister_clients(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
    recherche: str | None = None,
    inclure_archives: bool = False,
) -> list[Client]:
    return client_service.lister(db, recherche=recherche, inclure_archives=inclure_archives)


@router.get("/{client_id}", response_model=ClientSortie)
def obtenir_client(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Client:
    return client_service.obtenir(db, client_id)


@router.patch("/{client_id}", response_model=ClientSortie)
def modifier_client(
    client_id: int,
    donnees: ClientModification,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Client:
    return client_service.modifier(db, acteur.id, client_id, donnees.model_dump(exclude_unset=True))


@router.post("/{client_id}/archiver", response_model=ClientSortie)
def archiver_client(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("RESPONSABLE"))],
) -> Client:
    return client_service.archiver(db, acteur.id, client_id)
