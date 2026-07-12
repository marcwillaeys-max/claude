"""CRUD clients. Pas de suppression : archivage uniquement."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import IntrouvableError
from app.models.client import Client
from app.services import audit_service, numerotation_service

CHAMPS_MODIFIABLES = (
    "raison_sociale",
    "siret",
    "adresse",
    "code_postal",
    "ville",
    "contact_nom",
    "contact_email",
    "contact_telephone",
    "commentaires",
)


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def creer(db: Session, acteur_id: int, donnees: dict) -> Client:
    client = Client(
        numero_client=numerotation_service.prochain_numero_client(db),
        cree_le=_maintenant(),
        cree_par=acteur_id,
        archive=0,
        **{champ: donnees.get(champ) for champ in CHAMPS_MODIFIABLES},
    )
    db.add(client)
    db.flush()
    audit_service.enregistrer(
        db,
        acteur_id,
        "CREATE_CLIENT",
        "clients",
        client.id,
        json.dumps({"numero_client": client.numero_client}, sort_keys=True),
    )
    return client


def obtenir(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise IntrouvableError(f"Client {client_id} introuvable")
    return client


def lister(db: Session, recherche: str | None = None, inclure_archives: bool = False) -> list[Client]:
    requete = select(Client).order_by(Client.id)
    if not inclure_archives:
        requete = requete.where(Client.archive == 0)
    if recherche:
        requete = requete.where(Client.raison_sociale.like(f"%{recherche}%"))
    return list(db.execute(requete).scalars().all())


def modifier(db: Session, acteur_id: int, client_id: int, donnees: dict) -> Client:
    client = obtenir(db, client_id)
    modifications: dict[str, str | None] = {}
    for champ in CHAMPS_MODIFIABLES:
        if champ in donnees and getattr(client, champ) != donnees[champ]:
            modifications[champ] = donnees[champ]
            setattr(client, champ, donnees[champ])
    if modifications:
        audit_service.enregistrer(
            db, acteur_id, "UPDATE_CLIENT", "clients", client.id, json.dumps(modifications, sort_keys=True)
        )
    return client


def archiver(db: Session, acteur_id: int, client_id: int) -> Client:
    """Seule « suppression » autorisée : le client reste en base, marqué archivé."""
    client = obtenir(db, client_id)
    client.archive = 1
    audit_service.enregistrer(db, acteur_id, "ARCHIVE_CLIENT", "clients", client.id)
    return client
