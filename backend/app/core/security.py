"""Mots de passe (argon2id) et jetons JWT + dépendances FastAPI de contrôle de rôle."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import AuthentificationError, AutorisationError
from app.database import get_db
from app.models.utilisateur import Utilisateur

# argon2-cffi utilise argon2id par défaut.
_hasher = PasswordHasher()

# Hiérarchie des rôles : chaque niveau inclut les droits des niveaux inférieurs.
_NIVEAUX: dict[str, int] = {"TECHNICIEN": 1, "RESPONSABLE": 2, "ADMINISTRATEUR": 3}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, empreinte: str) -> bool:
    try:
        return _hasher.verify(empreinte, mot_de_passe)
    except VerifyMismatchError:
        return False


def creer_jeton(utilisateur: Utilisateur) -> str:
    settings = get_settings()
    expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_duree_minutes)
    payload = {"sub": utilisateur.identifiant, "uid": utilisateur.id, "role": utilisateur.role, "exp": expiration}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithme)


def decoder_jeton(jeton: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(jeton, settings.jwt_secret, algorithms=[settings.jwt_algorithme])
    except jwt.PyJWTError as exc:
        raise AuthentificationError("Jeton invalide ou expiré") from exc


def get_current_user(
    jeton: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Utilisateur:
    payload = decoder_jeton(jeton)
    utilisateur = db.get(Utilisateur, payload.get("uid"))
    if utilisateur is None or not utilisateur.actif:
        raise AuthentificationError("Utilisateur inconnu ou désactivé")
    return utilisateur


def exiger_role(role_minimum: str):
    """Dépendance FastAPI : refuse l'accès sous le rôle minimum demandé."""

    def _dependance(utilisateur: Annotated[Utilisateur, Depends(get_current_user)]) -> Utilisateur:
        if _NIVEAUX[utilisateur.role] < _NIVEAUX[role_minimum]:
            raise AutorisationError(f"Rôle {role_minimum} minimum requis")
        return utilisateur

    return _dependance
