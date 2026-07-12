from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

ANNEE = datetime.now(timezone.utc).year


def _creer_client(client: TestClient, entetes: dict[str, str]) -> int:
    return client.post(
        "/api/v1/clients", headers=entetes, json={"raison_sociale": "ACME"}
    ).json()["id"]


def _creer_lot(client: TestClient, entetes: dict[str, str], client_id: int) -> dict:
    reponse = client.post(
        "/api/v1/lots",
        headers=entetes,
        json={"client_id": client_id, "date_reception": "2026-07-12", "nb_supports_annonce": 10},
    )
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def test_creation_avec_numero_auto(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    client_id = _creer_client(client, entetes_technicien)
    lot = _creer_lot(client, entetes_technicien, client_id)
    assert lot["numero_lot"] == f"LOT-{ANNEE}-0001"
    assert lot["statut"] == "OUVERT"
    assert _creer_lot(client, entetes_technicien, client_id)["numero_lot"] == f"LOT-{ANNEE}-0002"


def test_creation_client_inexistant(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    reponse = client.post(
        "/api/v1/lots",
        headers=entetes_technicien,
        json={"client_id": 999, "date_reception": "2026-07-12"},
    )
    assert reponse.status_code == 404


def test_liste_filtree(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    client_id = _creer_client(client, entetes_technicien)
    _creer_lot(client, entetes_technicien, client_id)
    assert (
        len(client.get("/api/v1/lots", headers=entetes_technicien, params={"client_id": client_id}).json())
        == 1
    )
    assert (
        client.get("/api/v1/lots", headers=entetes_technicien, params={"statut": "CLOTURE"}).json() == []
    )


def test_modification_et_statut(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    client_id = _creer_client(client, entetes_technicien)
    lot = _creer_lot(client, entetes_technicien, client_id)
    reponse = client.patch(
        f"/api/v1/lots/{lot['id']}", headers=entetes_technicien, json={"statut": "EN_COURS"}
    )
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "EN_COURS"


def test_cloture_par_responsable_puis_gel(
    client: TestClient, entetes_technicien: dict[str, str], entetes_responsable: dict[str, str]
) -> None:
    client_id = _creer_client(client, entetes_technicien)
    lot = _creer_lot(client, entetes_technicien, client_id)
    cloture = client.post(f"/api/v1/lots/{lot['id']}/cloturer", headers=entetes_responsable)
    assert cloture.status_code == 200
    assert cloture.json()["statut"] == "CLOTURE"
    assert cloture.json()["cloture_le"] is not None
    # Un lot clôturé est figé.
    regel = client.patch(
        f"/api/v1/lots/{lot['id']}", headers=entetes_technicien, json={"statut": "OUVERT"}
    )
    assert regel.status_code == 422


def test_cloture_refusee_au_technicien(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    client_id = _creer_client(client, entetes_technicien)
    lot = _creer_lot(client, entetes_technicien, client_id)
    assert (
        client.post(f"/api/v1/lots/{lot['id']}/cloturer", headers=entetes_technicien).status_code == 403
    )
