from __future__ import annotations

from fastapi.testclient import TestClient


def _creer_client(client: TestClient, entetes: dict[str, str], raison: str = "ACME Recyclage") -> dict:
    reponse = client.post("/api/v1/clients", headers=entetes, json={"raison_sociale": raison})
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def test_creation_avec_numero_auto(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    premier = _creer_client(client, entetes_technicien)
    second = _creer_client(client, entetes_technicien, "Autre SARL")
    assert premier["numero_client"] == "CLI-0001"
    assert second["numero_client"] == "CLI-0002"
    assert premier["archive"] == 0


def test_lecture_et_liste(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    cree = _creer_client(client, entetes_technicien)
    fiche = client.get(f"/api/v1/clients/{cree['id']}", headers=entetes_technicien)
    assert fiche.status_code == 200
    assert fiche.json()["raison_sociale"] == "ACME Recyclage"
    liste = client.get("/api/v1/clients", headers=entetes_technicien)
    assert [c["id"] for c in liste.json()] == [cree["id"]]


def test_recherche_par_raison_sociale(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    _creer_client(client, entetes_technicien, "Hopital Nord")
    _creer_client(client, entetes_technicien, "Mairie de Lyon")
    resultat = client.get("/api/v1/clients", headers=entetes_technicien, params={"recherche": "Lyon"})
    assert [c["raison_sociale"] for c in resultat.json()] == ["Mairie de Lyon"]


def test_client_introuvable(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    assert client.get("/api/v1/clients/999", headers=entetes_technicien).status_code == 404


def test_modification(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    cree = _creer_client(client, entetes_technicien)
    reponse = client.patch(
        f"/api/v1/clients/{cree['id']}",
        headers=entetes_technicien,
        json={"ville": "Lyon", "contact_email": "contact@acme.fr"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["ville"] == "Lyon"
    # Le numéro et la date de création ne bougent pas.
    assert reponse.json()["numero_client"] == cree["numero_client"]


def test_archivage_par_responsable(
    client: TestClient, entetes_technicien: dict[str, str], entetes_responsable: dict[str, str]
) -> None:
    cree = _creer_client(client, entetes_technicien)
    reponse = client.post(f"/api/v1/clients/{cree['id']}/archiver", headers=entetes_responsable)
    assert reponse.status_code == 200
    assert reponse.json()["archive"] == 1
    # Exclu de la liste par défaut, toujours accessible avec inclure_archives.
    assert client.get("/api/v1/clients", headers=entetes_technicien).json() == []
    avec_archives = client.get(
        "/api/v1/clients", headers=entetes_technicien, params={"inclure_archives": True}
    )
    assert len(avec_archives.json()) == 1


def test_archivage_refuse_au_technicien(
    client: TestClient, entetes_technicien: dict[str, str]
) -> None:
    cree = _creer_client(client, entetes_technicien)
    assert (
        client.post(f"/api/v1/clients/{cree['id']}/archiver", headers=entetes_technicien).status_code
        == 403
    )
