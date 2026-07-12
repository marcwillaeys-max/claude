from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from app.models.operation import Operation
from tests.fixtures.rapports import construire_rapport, encoder


def _preparer_operation(client: TestClient, entetes: dict[str, str], **surcharges) -> dict:
    """Client + lot + support + rapport importé. Retourne {operation_id, token si généré...}."""
    client_id = client.post(
        "/api/v1/clients", headers=entetes, json={"raison_sociale": "Hopital Nord"}
    ).json()["id"]
    lot_id = client.post(
        "/api/v1/lots", headers=entetes, json={"client_id": client_id, "date_reception": "2026-07-12"}
    ).json()["id"]
    support = client.post("/api/v1/supports", headers=entetes, json={"lot_id": lot_id}).json()
    rapport = construire_rapport(support["code_interne"], **surcharges)
    reponse = client.post(
        "/api/v1/operations/import",
        headers=entetes,
        files={"fichier": ("rapport.json", encoder(rapport), "application/json")},
    )
    assert reponse.status_code == 201, reponse.text
    return reponse.json()["operation"]


def test_generation_telechargement_et_verification_publique(
    client: TestClient, entetes_technicien: dict[str, str]
) -> None:
    operation = _preparer_operation(client, entetes_technicien)

    creation = client.post(
        "/api/v1/certificats", headers=entetes_technicien, json={"operation_id": operation["id"]}
    )
    assert creation.status_code == 201, creation.text
    certificat = creation.json()
    assert certificat["numero_cert"].startswith("CERT-")

    # Téléchargement du PDF.
    pdf = client.get(f"/api/v1/certificats/{certificat['id']}/pdf", headers=entetes_technicien)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"

    # Vérification publique : AUCUNE authentification.
    page = client.get(f"/verif/{certificat['token_verif']}")
    assert page.status_code == 200
    html = page.text
    assert "CERTIFICAT VALIDE" in html
    assert "Hopital Nord" in html
    # Le numéro de série complet ne fuit jamais sur la page publique.
    assert "WD-WCC4E1234567" not in html
    assert "WD-*********567" in html


def test_generation_refusee_operation_en_echec(
    client: TestClient, entetes_technicien: dict[str, str]
) -> None:
    operation = _preparer_operation(
        client,
        entetes_technicien,
        operation={"resultat": "ECHEC"},
        verification={"faite": False, "ok": None},
        log_brut="erreur\n",
        log_sha256=hashlib.sha256(b"erreur\n").hexdigest(),
    )
    reponse = client.post(
        "/api/v1/certificats", headers=entetes_technicien, json={"operation_id": operation["id"]}
    )
    assert reponse.status_code == 422
    assert "ECHEC" in reponse.json()["detail"]


def test_generation_refusee_sans_verification(
    client: TestClient, entetes_technicien: dict[str, str]
) -> None:
    operation = _preparer_operation(
        client, entetes_technicien, verification={"faite": False, "ok": None}
    )
    reponse = client.post(
        "/api/v1/certificats", headers=entetes_technicien, json={"operation_id": operation["id"]}
    )
    assert reponse.status_code == 422


def test_generation_operation_inexistante(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    reponse = client.post(
        "/api/v1/certificats", headers=entetes_technicien, json={"operation_id": 999}
    )
    assert reponse.status_code == 404


def test_doublon_refuse(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    operation = _preparer_operation(client, entetes_technicien)
    corps = {"operation_id": operation["id"]}
    assert client.post("/api/v1/certificats", headers=entetes_technicien, json=corps).status_code == 201
    assert client.post("/api/v1/certificats", headers=entetes_technicien, json=corps).status_code == 409


def test_token_invalide_page_introuvable(client: TestClient) -> None:
    page = client.get("/verif/token-bidon")
    assert page.status_code == 404
    assert "INVALIDE" in page.text


def test_alteration_rend_la_page_invalide(
    client: TestClient, entetes_technicien: dict[str, str], sessionmaker_test: sessionmaker
) -> None:
    operation = _preparer_operation(client, entetes_technicien)
    certificat = client.post(
        "/api/v1/certificats", headers=entetes_technicien, json={"operation_id": operation["id"]}
    ).json()

    session = sessionmaker_test()
    session.execute(
        update(Operation).where(Operation.id == operation["id"]).values(log_sha256="f" * 64)
    )
    session.commit()
    session.close()

    page = client.get(f"/verif/{certificat['token_verif']}")
    assert page.status_code == 200
    assert "CERTIFICAT INVALIDE" in page.text
    # La page invalide ne montre aucune donnée métier.
    assert "Hopital Nord" not in page.text


def test_cle_publique_exposee(client: TestClient) -> None:
    reponse = client.get("/api/v1/certificats/cle-publique")
    assert reponse.status_code == 200
    assert reponse.json()["pem"].startswith("-----BEGIN PUBLIC KEY-----")


def test_certificats_exiges_authentifies(client: TestClient) -> None:
    assert client.post("/api/v1/certificats", json={"operation_id": 1}).status_code == 401
    assert client.get("/api/v1/certificats").status_code == 401
