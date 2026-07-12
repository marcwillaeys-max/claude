from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StatutLot = Literal["OUVERT", "EN_COURS", "TERMINE", "CLOTURE"]


class LotCreation(BaseModel):
    client_id: int
    date_reception: str = Field(description="ISO-8601")
    nb_supports_annonce: int | None = Field(default=None, ge=0)
    commentaires: str | None = None


class LotModification(BaseModel):
    date_reception: str | None = None
    nb_supports_annonce: int | None = Field(default=None, ge=0)
    commentaires: str | None = None
    statut: StatutLot | None = None


class LotSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_lot: str
    client_id: int
    date_reception: str
    technicien_id: int
    statut: StatutLot
    nb_supports_annonce: int | None
    commentaires: str | None
    cree_le: str
    cloture_le: str | None
