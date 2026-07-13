"""Tests de l'orchestrateur : l'ordre des garde-fous et les refus priment."""
from __future__ import annotations

import json
import stat

import pytest

from station import securite, station
from station.tests.conftest import Simulateur

LSBLK_HDD = json.dumps(
    {
        "blockdevices": [
            {
                "name": "sdb",
                "model": "WDC WD10EZEX",
                "serial": "WD-WCC4E1234567",
                "size": 8 * 1024 * 1024,
                "rota": 1,
                "tran": "sata",
                "vendor": "ATA",
            }
        ]
    }
)
SMART_OK = json.dumps({"smart_status": {"passed": True}, "temperature": {"current": 30}})


@pytest.fixture
def disque_propre(commandes_simulees: Simulateur, monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Simule un /dev/sdb sain, non système, HDD, effacement + vérif OK.
    Le vrai fichier tmp sert de cible pour la relecture de vérification."""
    faux_disque = tmp_path / "sdb"
    faux_disque.write_bytes(b"\x00" * (8 * 1024 * 1024))

    # Garde-fou 2 : faire croire que c'est un périphérique bloc existant.
    vrai_stat = station.securite.os.stat
    vrai_exists = station.securite.os.path.exists

    class FauxStat:
        st_mode = stat.S_IFBLK | 0o660

    monkeypatch.setattr(securite.os.path, "exists", lambda p: p == "/dev/sdb" or vrai_exists(p))
    monkeypatch.setattr(
        securite.os, "stat", lambda p, **k: FauxStat() if p == "/dev/sdb" else vrai_stat(p, **k)
    )
    # La vérification lit le vrai fichier tmp au lieu de /dev/sdb.
    import station.verification as modv

    vrai_open = modv.os.open
    monkeypatch.setattr(
        modv.os, "open", lambda p, f: vrai_open(str(faux_disque), f) if p == "/dev/sdb" else vrai_open(p, f)
    )

    # Inventaire : lsblk -J -b -d -o NAME,MODEL,SERIAL,... (le -d distingue de la
    # requête sécurité qui n'a pas -d).
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk" and "-d" in c, sortie=LSBLK_HDD)
    commandes_simulees.repondre_si(lambda c: c[0] == "smartctl", sortie=SMART_OK)
    commandes_simulees.repondre_si(lambda c: "-N" in c, sortie="max sectors = 100/100, HPA is disabled")
    commandes_simulees.repondre_si(lambda c: "--dco-identify" in c, sortie="not supported", code=1)
    # Non système : findmnt et lsblk -J (sans -d) ne rapportent que /dev/sda.
    commandes_simulees.repondre_si(lambda c: c[0] == "findmnt", sortie="/dev/sda1 /\n")
    commandes_simulees.repondre_si(
        lambda c: c[0] == "lsblk" and "-J" in c and "-d" not in c,
        sortie='{"blockdevices":[{"name":"sda","path":"/dev/sda","mountpoint":"/"}]}',
    )
    # DCO not supported → prudence → dco_detecte True. On l'autorise dans les tests
    # « chemin heureux » via autoriser_hpa_dco, sauf test dédié.
    commandes_simulees.repondre_si(lambda c: c[0] == "nwipe" and "--version" not in c, sortie="ok")
    commandes_simulees.repondre_si(lambda c: "--version" in c, sortie="nwipe 0.36")
    return commandes_simulees, str(tmp_path / "rapport.json")


def test_refus_avant_tout_si_confirmation_oui(disque_propre) -> None:
    _, chemin = disque_propre
    with pytest.raises(securite.RefusSecurite, match="interdite"):
        station.executer_station(
            "/dev/sdb", "SUP-2026-000001", "oui", chemin, autoriser_hpa_dco=True
        )


def test_refus_si_mauvais_numero_serie(disque_propre) -> None:
    _, chemin = disque_propre
    with pytest.raises(securite.RefusSecurite, match="ne correspond pas"):
        station.executer_station(
            "/dev/sdb", "SUP-2026-000001", "MAUVAIS-NUMERO", chemin, autoriser_hpa_dco=True
        )


def test_refus_hpa_dco_avant_effacement(disque_propre) -> None:
    commandes, chemin = disque_propre
    # DCO reste détecté (not supported → prudence) et on N'autorise PAS → refus,
    # AVANT toute confirmation ou effacement.
    with pytest.raises(securite.RefusSecurite, match="NON EFFAÇABLE"):
        station.executer_station(
            "/dev/sdb", "SUP-2026-000001", "WD-WCC4E1234567", chemin, autoriser_hpa_dco=False
        )
    # Aucun nwipe n'a été lancé.
    assert not any(c[0] == "nwipe" and "--version" not in c for c in commandes.appels)


def test_parcours_complet_succes(disque_propre) -> None:
    _, chemin = disque_propre
    rapport = station.executer_station(
        "/dev/sdb", "SUP-2026-000042", "WD-WCC4E1234567", chemin, autoriser_hpa_dco=True
    )
    assert rapport["format_version"] == "1.0"
    assert rapport["support"]["code_interne"] == "SUP-2026-000042"
    assert rapport["support"]["numero_serie"] == "WD-WCC4E1234567"
    assert rapport["operation"]["resultat"] == "SUCCES"
    assert rapport["operation"]["methode"] == "nwipe_zero_fill"
    assert rapport["verification"]["faite"] is True
    assert rapport["verification"]["ok"] is True
    # log_sha256 cohérent avec log_brut.
    import hashlib

    assert rapport["log_sha256"] == hashlib.sha256(rapport["log_brut"].encode()).hexdigest()
    # Rapport écrit sur disque.
    with open(chemin, encoding="utf-8") as fichier:
        assert json.load(fichier)["support"]["code_interne"] == "SUP-2026-000042"


def test_rapport_importable_par_le_backend(disque_propre) -> None:
    """Le rapport produit doit passer la validation stricte du LOT 2."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from app.schemas.rapport import RapportStation  # noqa: E402

    _, chemin = disque_propre
    rapport = station.executer_station(
        "/dev/sdb", "SUP-2026-000042", "WD-WCC4E1234567", chemin, autoriser_hpa_dco=True
    )
    # Ne lève pas : le contrat d'interface est respecté.
    valide = RapportStation.model_validate(rapport)
    assert valide.support.code_interne == "SUP-2026-000042"
    assert valide.operation.resultat == "SUCCES"
