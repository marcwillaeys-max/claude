"""En traçabilité, rien ne se supprime. Ces tests le garantissent.

1. L'API n'expose AUCUNE méthode DELETE.
2. Même en contournant l'API, les clés étrangères ON DELETE RESTRICT
   bloquent la suppression d'une entité référencée.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.models.client import Client
from app.models.lot import Lot
from app.services import client_service, lot_service, support_service, utilisateur_service


def test_aucune_route_delete_declaree() -> None:
    methodes = {
        methode
        for route in app.routes
        for methode in getattr(route, "methods", set()) or set()
    }
    assert "DELETE" not in methodes


def test_delete_http_refuse_partout(client: TestClient, entetes_admin: dict[str, str]) -> None:
    for chemin in ("/api/v1/clients/1", "/api/v1/lots/1", "/api/v1/supports/1", "/api/v1/audit"):
        reponse = client.delete(chemin, headers=entetes_admin)
        assert reponse.status_code == 405, chemin


def _peupler(db: Session) -> tuple[int, int]:
    utilisateur = utilisateur_service.creer(db, None, "tech", "Tech", "motdepasse-test", "TECHNICIEN")
    client_ = client_service.creer(db, utilisateur.id, {"raison_sociale": "ACME"})
    lot = lot_service.creer(db, utilisateur.id, client_.id, "2026-07-12")
    support_service.creer(db, utilisateur.id, lot.id, {})
    db.commit()
    return client_.id, lot.id


def test_restrict_bloque_suppression_client_avec_lots(sessionmaker_test: sessionmaker) -> None:
    session = sessionmaker_test()
    client_id, _ = _peupler(session)
    with pytest.raises(IntegrityError):
        session.execute(delete(Client).where(Client.id == client_id))
        session.flush()
    session.rollback()
    session.close()


def test_restrict_bloque_suppression_lot_avec_supports(sessionmaker_test: sessionmaker) -> None:
    session = sessionmaker_test()
    _, lot_id = _peupler(session)
    with pytest.raises(IntegrityError):
        session.execute(delete(Lot).where(Lot.id == lot_id))
        session.flush()
    session.rollback()
    session.close()
