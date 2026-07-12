from __future__ import annotations

from fastapi.testclient import TestClient


def test_login_ok_et_me(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    reponse = client.get("/api/v1/auth/me", headers=entetes_technicien)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["identifiant"] == "tech-test"
    assert corps["role"] == "TECHNICIEN"
    assert "mot_de_passe" not in corps


def test_login_mauvais_mot_de_passe(client: TestClient, entetes_technicien: dict[str, str]) -> None:
    reponse = client.post("/api/v1/auth/login", data={"username": "tech-test", "password": "faux"})
    assert reponse.status_code == 401


def test_acces_sans_jeton_refuse(client: TestClient) -> None:
    assert client.get("/api/v1/clients").status_code == 401


def test_jeton_invalide_refuse(client: TestClient) -> None:
    reponse = client.get("/api/v1/clients", headers={"Authorization": "Bearer n-importe-quoi"})
    assert reponse.status_code == 401


def test_admin_cree_un_utilisateur(client: TestClient, entetes_admin: dict[str, str]) -> None:
    reponse = client.post(
        "/api/v1/auth/utilisateurs",
        headers=entetes_admin,
        json={
            "identifiant": "nouveau",
            "nom_complet": "Nouveau Technicien",
            "mot_de_passe": "motdepasse-test",
            "role": "TECHNICIEN",
        },
    )
    assert reponse.status_code == 201
    assert reponse.json()["identifiant"] == "nouveau"


def test_identifiant_duplique_refuse(client: TestClient, entetes_admin: dict[str, str]) -> None:
    donnees = {
        "identifiant": "doublon",
        "nom_complet": "D",
        "mot_de_passe": "motdepasse-test",
        "role": "TECHNICIEN",
    }
    assert client.post("/api/v1/auth/utilisateurs", headers=entetes_admin, json=donnees).status_code == 201
    assert client.post("/api/v1/auth/utilisateurs", headers=entetes_admin, json=donnees).status_code == 409


def test_technicien_ne_cree_pas_d_utilisateur(
    client: TestClient, entetes_technicien: dict[str, str]
) -> None:
    reponse = client.post(
        "/api/v1/auth/utilisateurs",
        headers=entetes_technicien,
        json={
            "identifiant": "intrus",
            "nom_complet": "Intrus",
            "mot_de_passe": "motdepasse-test",
            "role": "ADMINISTRATEUR",
        },
    )
    assert reponse.status_code == 403


def test_utilisateur_desactive_ne_se_connecte_plus(
    client: TestClient, entetes_admin: dict[str, str]
) -> None:
    creation = client.post(
        "/api/v1/auth/utilisateurs",
        headers=entetes_admin,
        json={
            "identifiant": "sortant",
            "nom_complet": "S",
            "mot_de_passe": "motdepasse-test",
            "role": "TECHNICIEN",
        },
    )
    uid = creation.json()["id"]
    assert (
        client.post(f"/api/v1/auth/utilisateurs/{uid}/desactiver", headers=entetes_admin).status_code
        == 200
    )
    reconnexion = client.post(
        "/api/v1/auth/login", data={"username": "sortant", "password": "motdepasse-test"}
    )
    assert reconnexion.status_code == 401
