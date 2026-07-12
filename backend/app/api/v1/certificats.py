from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.certificat import Certificat
from app.models.utilisateur import Utilisateur
from app.schemas.certificat import CertificatCreation, CertificatSortie, ClePubliqueSortie
from app.services import certificat_service, signature_service

router = APIRouter(prefix="/api/v1/certificats", tags=["certificats"])


@router.post("", response_model=CertificatSortie, status_code=201)
def generer_certificat(
    donnees: CertificatCreation,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Certificat:
    return certificat_service.generer(db, acteur.id, donnees.operation_id)


@router.get("", response_model=list[CertificatSortie])
def lister_certificats(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> list[Certificat]:
    return certificat_service.lister(db)


@router.get("/cle-publique", response_model=ClePubliqueSortie)
def cle_publique() -> ClePubliqueSortie:
    """Clé publique Ed25519 du poste — publiée pour permettre la vérification externe."""
    return ClePubliqueSortie(
        cle_publique_id=signature_service.cle_publique_id(), pem=signature_service.cle_publique_pem()
    )


@router.get("/{certificat_id}", response_model=CertificatSortie)
def obtenir_certificat(
    certificat_id: int,
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> Certificat:
    return certificat_service.obtenir(db, certificat_id)


@router.get("/{certificat_id}/pdf")
def telecharger_pdf(
    certificat_id: int,
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> FileResponse:
    certificat = certificat_service.regenerer_pdf(db, certificat_id)
    return FileResponse(
        certificat.chemin_pdf,
        media_type="application/pdf",
        filename=f"{certificat.numero_cert}.pdf",
    )
