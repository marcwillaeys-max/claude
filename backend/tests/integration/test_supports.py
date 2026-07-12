from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

ANNEE = datetime.now(timezone.utc).year


def _creer_lot(client: TestClient, entetes: dict[str, str]) -> int:
    client_id = client.post(
        "/api/v1/clients", headers=entetes, json={"raison_sociale": "ACME"}
    ).json()["id"]
    return client.post(
        "/api/v1/lots",
        headers=entetes,
        json={"client_id": client_id, "date_reception": "2026-07-12"},
    ).json()["id"]


def _creer_support(client: TestClient, entetes: dict[str, str], lot_id: int, **extra) -> dict:
    reponse = client.post(
        "/api/v1/supports",
        headers=entetes,
        json={"lot_id": lot_id, "numero_serie": "WD-123", "technologie": "HDD_SATA", **extra},
    )
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def test_creation_avec_code_interne_auto(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    lot_id = _creer_lot(client, entetes_technicien)
    support = _creer_support(client, entetes_technicien, lot_id)
    assert support["code_interne"] == f"SUP-{ANNEE}-000001"
    assert support["statut"] == "EN_ATTENTE"
    assert _creer_support(client, entetes_technicien, lot_id)["code_interne"] == f"SUP-{ANNEE}-000002"


def test_support_exige_un_lot_existant(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    reponse = client.post("/api/v1/supports", headers=entetes_technicien, json={"lot_id": 999})
    assert reponse.status_code == 404


def test_technologie_invalide_refusee(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    lot_id = _creer_lot(client, entetes_technicien)
    reponse = client.post(
        "/api/v1/supports",
        headers=entetes_technicien,
        json={"lot_id": lot_id, "technologie": "DISQUETTE"},
    )
    assert reponse.status_code == 422


def test_liste_filtree_par_lot_et_statut(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    lot_id = _creer_lot(client, entetes_technicien)
    _creer_support(client, entetes_technicien, lot_id)
    assert (
        len(
            client.get(
                "/api/v1/supports", headers=entetes_technicien, params={"lot_id": lot_id}
            ).json()
        )
        == 1
    )
    assert (
        client.get(
            "/api/v1/supports", headers=entetes_technicien, params={"statut": "ECHEC"}
        ).json()
        == []
    )


def test_modification_metadonnees(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    lot_id = _creer_lot(client, entetes_technicien)
    support = _creer_support(client, entetes_technicien, lot_id)
    reponse = client.patch(
        f"/api/v1/supports/{support['id']}",
        headers=entetes_technicien,
        json={"modele": "WD10EZEX", "capacite_octets": 1000204886016, "sante": "OK"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["modele"] == "WD10EZEX"
    assert reponse.json()["code_interne"] == support["code_interne"]


def test_statut_manuel_destruction_physique(
    client: TestClient, entetes_technicien: dict[str, str]
) -> None:
    lot_id = _creer_lot(client, entetes_technicien)
    support = _creer_support(client, entetes_technicien, lot_id)
    reponse = client.post(
        f"/api/v1/supports/{support['id']}/statut",
        headers=entetes_technicien,
        json={"statut": "DETRUIT_PHYSIQUEMENT"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "DETRUIT_PHYSIQUEMENT"


def test_statut_efface_interdit_a_la_main(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    """EFFACE_VERIFIE ne peut venir que d'un rapport station (LOT 2), jamais d'une saisie."""
    lot_id = _creer_lot(client, entetes_technicien)
    support = _creer_support(client, entetes_technicien, lot_id)
    for statut in ("EFFACE_VERIFIE", "EFFACE_NON_VERIFIE"):
        reponse = client.post(
            f"/api/v1/supports/{support['id']}/statut",
            headers=entetes_technicien,
            json={"statut": statut},
        )
        assert reponse.status_code == 422, statut
