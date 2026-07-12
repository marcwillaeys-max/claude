from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.audit import Audit
from app.models.utilisateur import Utilisateur
from app.schemas.audit import AuditSortie, RuptureSortie, VerificationChaineSortie
from app.services import audit_service

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditSortie])
def lister_audit(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("RESPONSABLE"))],
    limite: int = 100,
    decalage: int = 0,
) -> list[Audit]:
    return audit_service.lister(db, limite=limite, decalage=decalage)


@router.get("/verify", response_model=VerificationChaineSortie)
def verifier_chaine(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("RESPONSABLE"))],
) -> VerificationChaineSortie:
    resultat = audit_service.verifier_chaine(db)
    return VerificationChaineSortie(
        valide=resultat.valide,
        nb_lignes=resultat.nb_lignes,
        ruptures=[RuptureSortie(audit_id=r.audit_id, raison=r.raison) for r in resultat.ruptures],
    )
