from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.operation import Operation
from app.models.utilisateur import Utilisateur
from app.schemas.operation import OperationDetailSortie, OperationSortie, ResultatImportSortie
from app.services import import_service, operation_service

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.post("/import", response_model=ResultatImportSortie, status_code=201)
async def importer_rapport(
    fichier: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> ResultatImportSortie:
    contenu = await fichier.read()
    resultat = import_service.importer_rapport(db, acteur.id, contenu)
    return ResultatImportSortie(
        deja_importe=resultat.deja_importe,
        statut_support=resultat.statut_support,
        operation=OperationSortie.model_validate(resultat.operation),
    )


@router.get("", response_model=list[OperationSortie])
def lister_operations(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
    lot_id: int | None = None,
    client_id: int | None = None,
    support_id: int | None = None,
    resultat: str | None = None,
    technicien_id: int | None = None,
    debut_min: str | None = None,
    debut_max: str | None = None,
) -> list[Operation]:
    return operation_service.lister(
        db,
        lot_id=lot_id,
        client_id=client_id,
        support_id=support_id,
        resultat=resultat,
        technicien_id=technicien_id,
        debut_min=debut_min,
        debut_max=debut_max,
    )


@router.get("/{operation_id}", response_model=OperationDetailSortie)
def obtenir_operation(
    operation_id: int,
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Operation:
    return operation_service.obtenir(db, operation_id)
