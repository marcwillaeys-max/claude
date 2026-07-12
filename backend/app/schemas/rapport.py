"""Contrat d'interface avec la station d'effacement (spécification §4).

Validation STRICTE : tout champ inconnu ou manquant rejette le rapport
entier. Un rapport n'est jamais importé partiellement.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.support import Sante, Technologie


class OutilRapport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    version: str


class SupportRapport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_interne: str = Field(min_length=1)
    numero_serie: str | None = None
    modele: str | None = None
    constructeur: str | None = None
    capacite_octets: int | None = Field(default=None, ge=0)
    technologie: Technologie | None = None
    interface: str | None = None
    sante: Sante | None = None
    hpa_detecte: bool = False
    dco_detecte: bool = False
    smart: dict | None = None


class OperationRapport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methode: str = Field(min_length=1)
    norme_reference: str = "NIST SP 800-88 Rev.1"
    nb_passes: int | None = Field(default=None, ge=1)
    debut: str
    fin: str | None = None
    duree_secondes: int | None = Field(default=None, ge=0)
    resultat: Literal["SUCCES", "ECHEC", "INTERROMPU"]


class VerificationRapport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faite: bool
    ok: bool | None = None
    secteurs_testes: int | None = Field(default=None, ge=0)
    zones: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherence(self) -> "VerificationRapport":
        if self.faite and self.ok is None:
            raise ValueError("verification.ok est obligatoire quand verification.faite est true")
        if not self.faite and self.ok is not None:
            raise ValueError("verification.ok doit être absent quand verification.faite est false")
        return self


class RapportStation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_version: Literal["1.0"]
    station: str | None = None
    outil: OutilRapport
    support: SupportRapport
    operation: OperationRapport
    verification: VerificationRapport
    log_brut: str
    log_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
