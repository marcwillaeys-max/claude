from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from tests.fixtures.rapports import construire_rapport, encoder


def _preparer_support(client: TestClient, entetes: dict[str, str]) -> dict:
    client_id = client.post(
        "/api/v1/clients", headers=entetes, json={"raison_sociale": "ACME"}
    ).json()["id"]
    lot_id = client.post(
        "/api/v1/lots", headers=entetes, json={"client_id": client_id, "date_reception": "2026-07-12"}
    ).json()["id"]
    support = client.post("/api/v1/supports", headers=entetes, json={"lot_id": lot_id}).json()
    support["client_id"] = client_id
    return support


def _uploader(client: TestClient, entetes: dict[str, str], rapport: dict):
    return client.post(
        "/api/v1/operations/import",
        headers=entetes,
        files={"fichier": ("rapport.json", encoder(rapport), "application/json")},
    )


def test_import_nominal_via_api(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    reponse = _uploader(client, entetes_technicien, construire_rapport(support["code_interne"]))
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["deja_importe"] is False
    assert corps["statut_support"] == "EFFACE_VERIFIE"
    assert corps["operation"]["methode"] == "nwipe_zero_fill"
    assert "log_brut" not in corps["operation"]

    fiche = client.get(f"/api/v1/supports/{support['id']}", headers=entetes_technicien).json()
    assert fiche["statut"] == "EFFACE_VERIFIE"


def test_import_sans_authentification_refuse(client: TestClient) -> None:
    reponse = client.post(
        "/api/v1/operations/import",
        files={"fichier": ("rapport.json", b"{}", "application/json")},
    )
    assert reponse.status_code == 401


def test_import_rapport_corrompu_rejete(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    rapport = construire_rapport(support["code_interne"], log_sha256="a" * 64)
    reponse = _uploader(client, entetes_technicien, rapport)
    assert reponse.status_code == 422
    assert "SHA-256" in reponse.json()["detail"]


def test_import_rapport_malforme_rejete(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    rapport = construire_rapport(support["code_interne"], format_version="9.9")
    reponse = _uploader(client, entetes_technicien, rapport)
    assert reponse.status_code == 422
    assert "malformé" in reponse.json()["detail"]


def test_import_support_inconnu(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    reponse = _uploader(client, entetes_technicien, construire_rapport("SUP-2026-424242"))
    assert reponse.status_code == 404
    assert "SUP-2026-424242" in reponse.json()["detail"]


def test_double_import_pas_de_doublon(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    rapport = construire_rapport(support["code_interne"])
    assert _uploader(client, entetes_technicien, rapport).status_code == 201
    second = _uploader(client, entetes_technicien, rapport)
    assert second.status_code == 201
    assert second.json()["deja_importe"] is True
    liste = client.get(
        "/api/v1/operations", headers=entetes_technicien, params={"support_id": support["id"]}
    ).json()
    assert len(liste) == 1


def test_liste_operations_filtres(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    log_echec = "erreur I/O secteur 7\n"
    _uploader(
        client,
        entetes_technicien,
        construire_rapport(
            support["code_interne"],
            operation={"resultat": "ECHEC", "debut": "2026-07-10T08:00:00Z"},
            verification={"faite": False, "ok": None},
            log_brut=log_echec,
            log_sha256=hashlib.sha256(log_echec.encode()).hexdigest(),
        ),
    )
    _uploader(client, entetes_technicien, construire_rapport(support["code_interne"]))

    def _lister(**params) -> list:
        return client.get("/api/v1/operations", headers=entetes_technicien, params=params).json()

    assert len(_lister(lot_id=support["lot_id"])) == 2
    assert len(_lister(client_id=support["client_id"])) == 2
    assert len(_lister(resultat="ECHEC")) == 1
    assert len(_lister(debut_min="2026-07-11T00:00:00Z")) == 1
    assert len(_lister(debut_max="2026-07-11T00:00:00Z")) == 1
    assert _lister(client_id=9999) == []


def test_detail_operation_contient_le_log(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    operation_id = _uploader(
        client, entetes_technicien, construire_rapport(support["code_interne"])
    ).json()["operation"]["id"]
    detail = client.get(f"/api/v1/operations/{operation_id}", headers=entetes_technicien).json()
    assert "nwipe" in detail["log_brut"]


def test_recherche_supports(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    support = _preparer_support(client, entetes_technicien)
    client.patch(
        f"/api/v1/supports/{support['id']}",
        headers=entetes_technicien,
        json={"numero_serie": "WD-WCC4E1234567", "modele": "WD10EZEX"},
    )

    def _rechercher(q: str) -> list:
        return client.get(
            "/api/v1/supports/recherche", headers=entetes_technicien, params={"q": q}
        ).json()

    assert len(_rechercher("WCC4E")) == 1  # numéro de série
    assert len(_rechercher(support["code_interne"])) == 1  # code interne
    assert len(_rechercher("EZEX")) == 1  # modèle
    assert _rechercher("INTROUVABLE") == []
