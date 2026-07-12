from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Technologie = Literal["HDD_SATA", "SSD_SATA", "SSD_NVME", "SAS", "USB", "SD", "SED", "INCONNU"]
Sante = Literal["OK", "DEGRADE", "DEFAILLANT", "INCONNU"]
StatutSupport = Literal[
    "EN_ATTENTE",
    "EN_COURS",
    "EFFACE_VERIFIE",
    "EFFACE_NON_VERIFIE",
    "ECHEC",
    "NON_EFFACABLE",
    "DETRUIT_PHYSIQUEMENT",
]
Destination = Literal["REEMPLOI", "DESTRUCTION", "VALORISATION"]


class SupportCreation(BaseModel):
    lot_id: int
    numero_serie: str | None = None
    modele: str | None = None
    constructeur: str | None = None
    capacite_octets: int | None = Field(default=None, ge=0)
    technologie: Technologie | None = None
    interface: str | None = None
    smart_json: str | None = None
    sante: Sante | None = None
    hpa_detecte: int | None = Field(default=0, ge=0, le=1)
    dco_detecte: int | None = Field(default=0, ge=0, le=1)
    destination: Destination | None = None


class SupportModification(BaseModel):
    numero_serie: str | None = None
    modele: str | None = None
    constructeur: str | None = None
    capacite_octets: int | None = Field(default=None, ge=0)
    technologie: Technologie | None = None
    interface: str | None = None
    smart_json: str | None = None
    sante: Sante | None = None
    hpa_detecte: int | None = Field(default=None, ge=0, le=1)
    dco_detecte: int | None = Field(default=None, ge=0, le=1)
    destination: Destination | None = None


class SupportChangementStatut(BaseModel):
    statut: StatutSupport


class SupportSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_id: int
    code_interne: str
    numero_serie: str | None
    modele: str | None
    constructeur: str | None
    capacite_octets: int | None
    technologie: Technologie | None
    interface: str | None
    smart_json: str | None
    sante: Sante | None
    hpa_detecte: int | None
    dco_detecte: int | None
    statut: StatutSupport
    destination: Destination | None
    cree_le: str
