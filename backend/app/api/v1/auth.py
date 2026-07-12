from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import creer_jeton, exiger_role, get_current_user
from app.database import get_db
from app.models.utilisateur import Utilisateur
from app.schemas.auth import JetonSortie, UtilisateurCreation, UtilisateurSortie
from app.services import utilisateur_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=JetonSortie)
def login(
    formulaire: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> JetonSortie:
    utilisateur = utilisateur_service.authentifier(db, formulaire.username, formulaire.password)
    return JetonSortie(access_token=creer_jeton(utilisateur))


@router.get("/me", response_model=UtilisateurSortie)
def me(utilisateur: Annotated[Utilisateur, Depends(get_current_user)]) -> Utilisateur:
    return utilisateur


@router.post("/utilisateurs", response_model=UtilisateurSortie, status_code=201)
def creer_utilisateur(
    donnees: UtilisateurCreation,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("ADMINISTRATEUR"))],
) -> Utilisateur:
    return utilisateur_service.creer(
        db, acteur.id, donnees.identifiant, donnees.nom_complet, donnees.mot_de_passe, donnees.role
    )


@router.get("/utilisateurs", response_model=list[UtilisateurSortie])
def lister_utilisateurs(
    db: Annotated[Session, Depends(get_db)],
    _acteur: Annotated[Utilisateur, Depends(exiger_role("ADMINISTRATEUR"))],
) -> list[Utilisateur]:
    return utilisateur_service.lister(db)


@router.post("/utilisateurs/{utilisateur_id}/desactiver", response_model=UtilisateurSortie)
def desactiver_utilisateur(
    utilisateur_id: int,
    db: Annotated[Session, Depends(get_db)],
    acteur: Annotated[Utilisateur, Depends(exiger_role("ADMINISTRATEUR"))],
) -> Utilisateur:
    return utilisateur_service.desactiver(db, acteur.id, utilisateur_id)
