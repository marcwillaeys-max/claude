from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Resultat = Literal["SUCCES", "ECHEC", "INTERROMPU"]


class OperationSortie(BaseModel):
    """Sortie liste : sans log_brut (potentiellement volumineux)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    support_id: int
    technicien_id: int
    station: str | None
    methode: str
    norme_reference: str
    nb_passes: int | None
    debut: str
    fin: str | None
    duree_secondes: int | None
    resultat: Resultat
    verification_faite: int
    verification_ok: int | None
    verification_detail: str | None
    log_sha256: str
    outil_version: str | None
    importe_le: str


class OperationDetailSortie(OperationSortie):
    log_brut: str | None


class ResultatImportSortie(BaseModel):
    deja_importe: bool
    statut_support: str
    operation: OperationSortie
