from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AuditSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    horodatage: str
    utilisateur_id: int | None
    action: str
    entite: str
    entite_id: int | None
    details: str | None
    hash_precedent: str
    hash_courant: str


class RuptureSortie(BaseModel):
    audit_id: int
    raison: str


class VerificationChaineSortie(BaseModel):
    valide: bool
    nb_lignes: int
    ruptures: list[RuptureSortie]
