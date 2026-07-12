from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import exiger_role
from app.database import get_db
from app.models.support import Support
from app.models.utilisateur import Utilisateur
from app.schemas.support import SupportSortie
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class IndicateursSortie(BaseModel):
    supports_traites_jour: int
    supports_traites_semaine: int
    supports_traites_mois: int
    capacite_effacee_octets: int
    duree_moyenne_secondes: float | None
    taux_reussite: float | None
    nb_operations: int
    repartition_technologie: dict[str, int]
    repartition_statut: dict[str, int]


@router.get("", response_model=IndicateursSortie)
def indicateurs(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> IndicateursSortie:
    resultat = dashboard_service.indicateurs(db)
    return IndicateursSortie(**resultat.__dict__)


@router.get("/a-traiter", response_model=list[SupportSortie])
def supports_a_traiter(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("TECHNICIEN"))],
) -> list[Support]:
    return dashboard_service.supports_a_traiter(db)
