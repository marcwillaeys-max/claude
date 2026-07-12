from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ClientCreation(BaseModel):
    raison_sociale: str = Field(min_length=1, max_length=256)
    siret: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    contact_nom: str | None = None
    contact_email: str | None = None
    contact_telephone: str | None = None
    commentaires: str | None = None


class ClientModification(BaseModel):
    raison_sociale: str | None = Field(default=None, min_length=1, max_length=256)
    siret: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    contact_nom: str | None = None
    contact_email: str | None = None
    contact_telephone: str | None = None
    commentaires: str | None = None


class ClientSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_client: str
    raison_sociale: str
    siret: str | None
    adresse: str | None
    code_postal: str | None
    ville: str | None
    contact_nom: str | None
    contact_email: str | None
    contact_telephone: str | None
    commentaires: str | None
    cree_le: str
    cree_par: int
    archive: int
