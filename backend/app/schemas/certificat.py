from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CertificatCreation(BaseModel):
    operation_id: int


class CertificatSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_cert: str
    operation_id: int
    genere_le: str
    genere_par: int
    contenu_sha256: str
    signature: str
    cle_publique_id: str
    token_verif: str


class ClePubliqueSortie(BaseModel):
    cle_publique_id: str
    pem: str
