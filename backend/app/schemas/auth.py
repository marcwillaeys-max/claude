from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["TECHNICIEN", "RESPONSABLE", "ADMINISTRATEUR"]


class JetonSortie(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UtilisateurCreation(BaseModel):
    identifiant: str = Field(min_length=2, max_length=64)
    nom_complet: str = Field(min_length=1, max_length=128)
    mot_de_passe: str = Field(min_length=8, max_length=128)
    role: Role


class UtilisateurSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identifiant: str
    nom_complet: str
    role: Role
    actif: int
    cree_le: str
    derniere_conn: str | None
