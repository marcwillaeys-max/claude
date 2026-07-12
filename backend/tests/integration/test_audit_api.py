from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from app.models.audit import Audit


def test_toute_ecriture_metier_est_auditee(
    client: TestClient, entetes_technicien: dict[str, str], entetes_responsable: dict[str, str]
) -> None:
    client_id = client.post(
        "/api/v1/clients", headers=entetes_technicien, json={"raison_sociale": "ACME"}
    ).json()["id"]
    client.patch(f"/api/v1/clients/{client_id}", headers=entetes_technicien, json={"ville": "Lyon"})

    journal = client.get("/api/v1/audit", headers=entetes_responsable).json()
    actions = [ligne["action"] for ligne in journal]
    assert "CREATE_CLIENT" in actions
    assert "UPDATE_CLIENT" in actions
    assert "CREATE_UTILISATEUR" in actions
    assert "LOGIN" in actions


def test_journal_refuse_au_technicien(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    assert client.get("/api/v1/audit", headers=entetes_technicien).status_code == 403
    assert client.get("/api/v1/audit/verify", headers=entetes_technicien).status_code == 403


def test_verify_chaine_intacte(
    client: TestClient, entetes_technicien: dict[str, str], entetes_responsable: dict[str, str]
) -> None:
    client.post("/api/v1/clients", headers=entetes_technicien, json={"raison_sociale": "ACME"})
    resultat = client.get("/api/v1/audit/verify", headers=entetes_responsable).json()
    assert resultat["valide"] is True
    assert resultat["nb_lignes"] > 0
    assert resultat["ruptures"] == []


def test_verify_detecte_falsification(
    client: TestClient,
    entetes_responsable: dict[str, str],
    sessionmaker_test: sessionmaker,
) -> None:
    # Falsification directe en base, hors API.
    session = sessionmaker_test()
    session.execute(update(Audit).where(Audit.id == 1).values(action="ACTION_FALSIFIEE"))
    session.commit()
    session.close()

    resultat = client.get("/api/v1/audit/verify", headers=entetes_responsable).json()
    assert resultat["valide"] is False
    assert any(r["audit_id"] == 1 for r in resultat["ruptures"])
