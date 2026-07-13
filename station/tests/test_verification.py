"""Tests de vérification. On utilise un vrai fichier temporaire comme
« périphérique » : os.pread/os.open fonctionnent sur un fichier régulier,
ce qui permet de tester la logique de relecture sans aucun disque."""
from __future__ import annotations

from station import verification


def _ecrire(tmp_path, contenu: bytes) -> str:
    fichier = tmp_path / "faux_disque"
    fichier.write_bytes(contenu)
    return str(fichier)


def test_disque_entierement_a_zero_est_conforme(tmp_path) -> None:
    chemin = _ecrire(tmp_path, b"\x00" * (5 * 1024 * 1024))
    resultat = verification.verifier(chemin, motif=0)
    assert resultat.faite is True
    assert resultat.ok is True
    assert resultat.anomalies == []
    assert "premiers_100Mo" in resultat.zones
    assert "aleatoire_1000_secteurs" in resultat.zones
    assert resultat.secteurs_testes > 0


def test_disque_non_efface_detecte_anomalie(tmp_path) -> None:
    # Données non nulles : la relecture doit trouver des octets non conformes.
    chemin = _ecrire(tmp_path, b"DONNEES CLIENT NON EFFACEES " * 100000)
    resultat = verification.verifier(chemin, motif=0)
    assert resultat.faite is True
    assert resultat.ok is False
    assert len(resultat.anomalies) >= 1


def test_debut_efface_mais_fin_intacte(tmp_path) -> None:
    # 100 premiers Mo à zéro, mais des données non nulles à la fin.
    contenu = bytearray(verification.CENT_MO + 2 * 1024 * 1024)
    contenu[verification.CENT_MO :] = b"\xff" * (2 * 1024 * 1024)
    chemin = _ecrire(tmp_path, bytes(contenu))
    resultat = verification.verifier(chemin, motif=0)
    assert resultat.ok is False
    assert any("derniers_100Mo" in a for a in resultat.anomalies)


def test_motif_non_deterministe_non_applicable(tmp_path) -> None:
    chemin = _ecrire(tmp_path, b"\x00" * 1024)
    resultat = verification.verifier(chemin, motif=None)
    assert resultat.faite is False
    assert resultat.ok is False
    assert "crypto-erase" in resultat.anomalies[0]


def test_petit_disque_sans_zone_de_fin(tmp_path) -> None:
    # Disque plus petit que 100 Mo : pas de zone « derniers_100Mo » distincte.
    chemin = _ecrire(tmp_path, b"\x00" * (1024 * 1024))
    resultat = verification.verifier(chemin, motif=0)
    assert resultat.ok is True
    assert "premiers_100Mo" in resultat.zones
