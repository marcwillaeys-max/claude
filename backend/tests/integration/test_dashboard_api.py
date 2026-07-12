from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from tests.fixtures.rapports import construire_rapport, encoder


def _importer(client: TestClient, entetes: dict[str, str], code: str, **surcharges) -> None:
    rapport = construire_rapport(code, **surcharges)
    reponse = client.post(
        "/api/v1/operations/import",
        headers=entetes,
        files={"fichier": ("rapport.json", encoder(rapport), "application/json")},
    )
    assert reponse.status_code == 201, reponse.text


def _preparer_supports(client: TestClient, entetes: dict[str, str], nombre: int) -> list[dict]:
    client_id = client.post(
        "/api/v1/clients", headers=entetes, json={"raison_sociale": "ACME"}
    ).json()["id"]
    lot_id = client.post(
        "/api/v1/lots", headers=entetes, json={"client_id": client_id, "date_reception": "2026-07-12"}
    ).json()["id"]
    return [
        client.post(
            "/api/v1/supports",
            headers=entetes,
            json={"lot_id": lot_id, "capacite_octets": 1_000_000_000_000, "technologie": "HDD_SATA"},
        ).json()
        for _ in range(nombre)
    ]


def test_indicateurs(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    supports = _preparer_supports(client, entetes_technicien, 3)
    # 2 succès vérifiés + 1 échec.
    _importer(client, entetes_technicien, supports[0]["code_interne"])
    _importer(
        client,
        entetes_technicien,
        supports[1]["code_interne"],
        log_brut="log 2\n",
        log_sha256=hashlib.sha256(b"log 2\n").hexdigest(),
    )
    _importer(
        client,
        entetes_technicien,
        supports[2]["code_interne"],
        operation={"resultat": "ECHEC"},
        verification={"faite": False, "ok": None},
        log_brut="erreur\n",
        log_sha256=hashlib.sha256(b"erreur\n").hexdigest(),
    )

    corps = client.get("/api/v1/dashboard", headers=entetes_technicien).json()
    assert corps["supports_traites_jour"] == 2
    assert corps["supports_traites_mois"] == 2
    # La capacité effacée ne compte QUE les supports effacés, pas l'échec.
    assert corps["capacite_effacee_octets"] == 2_000_000_000_000
    assert corps["nb_operations"] == 3
    assert abs(corps["taux_reussite"] - 2 / 3) < 1e-9
    assert corps["duree_moyenne_secondes"] == 9229.0
    assert corps["repartition_technologie"] == {"HDD_SATA": 3}
    assert corps["repartition_statut"]["EFFACE_VERIFIE"] == 2
    assert corps["repartition_statut"]["ECHEC"] == 1


def test_indicateurs_base_vide(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    corps = client.get("/api/v1/dashboard", headers=entetes_technicien).json()
    assert corps["nb_operations"] == 0
    assert corps["taux_reussite"] is None
    assert corps["duree_moyenne_secondes"] is None
    assert corps["capacite_effacee_octets"] == 0


def test_supports_a_traiter_visibles(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    supports = _preparer_supports(client, entetes_technicien, 2)
    _importer(
        client,
        entetes_technicien,
        supports[0]["code_interne"],
        operation={"resultat": "ECHEC"},
        verification={"faite": False, "ok": None},
        log_brut="erreur\n",
        log_sha256=hashlib.sha256(b"erreur\n").hexdigest(),
    )
    _importer(client, entetes_technicien, supports[1]["code_interne"], support={"hpa_detecte": True})

    a_traiter = client.get("/api/v1/dashboard/a-traiter", headers=entetes_technicien).json()
    assert {s["statut"] for s in a_traiter} == {"ECHEC", "NON_EFFACABLE"}
    assert len(a_traiter) == 2
