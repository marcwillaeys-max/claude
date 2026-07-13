from __future__ import annotations

import json

from station import inventaire
from station.tests.conftest import Simulateur

LSBLK = json.dumps(
    {
        "blockdevices": [
            {
                "name": "sdb",
                "model": "WDC WD10EZEX-08WN4A0",
                "serial": "WD-WCC4E1234567",
                "size": 1000204886016,
                "rota": 1,
                "tran": "sata",
                "vendor": "ATA",
            }
        ]
    }
)

SMART_OK = json.dumps(
    {
        "smart_status": {"passed": True},
        "temperature": {"current": 34},
        "power_on_time": {"hours": 21455},
        "ata_smart_attributes": {"table": [{"id": 5, "raw": {"value": 0}}]},
    }
)


def test_inventaire_hdd_nominal(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk", sortie=LSBLK)
    commandes_simulees.repondre_si(lambda c: c[0] == "smartctl", sortie=SMART_OK)
    commandes_simulees.repondre_si(
        lambda c: c[0] == "hdparm" and "-N" in c, sortie="max sectors = 1953525168/1953525168, HPA is disabled"
    )
    commandes_simulees.repondre_si(
        lambda c: c[0] == "hdparm" and "--dco-identify" in c, sortie="DCO not supported", code=1
    )

    resultat = inventaire.inventorier("/dev/sdb")

    assert resultat["numero_serie"] == "WD-WCC4E1234567"
    assert resultat["modele"] == "WDC WD10EZEX-08WN4A0"
    assert resultat["capacite_octets"] == 1000204886016
    assert resultat["technologie"] == "HDD_SATA"
    assert resultat["sante"] == "OK"
    assert resultat["hpa_detecte"] is False
    # DCO indéterminé (not supported) → prudence → True.
    assert resultat["dco_detecte"] is True
    assert resultat["smart"]["temperature_c"] == 34


def test_detection_hpa_active(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(
        lambda c: "-N" in c, sortie="max sectors = 1000000000/1953525168, HPA is enabled"
    )
    hpa = inventaire.detecter_hpa("/dev/sdb")
    assert hpa["detecte"] is True
    assert hpa["secteurs_visibles"] < hpa["secteurs_natifs"]


def test_prudence_hpa_indetermine() -> None:
    # None (statut illisible) est traité comme True côté inventaire complet.
    assert inventaire._prudence(None) is True
    assert inventaire._prudence(False) is False
    assert inventaire._prudence(True) is True


def test_technologie_nvme(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(
        lambda c: c[0] == "lsblk",
        sortie=json.dumps(
            {"blockdevices": [{"name": "nvme0n1", "serial": "S1", "size": 512110190592, "rota": 0, "tran": "nvme"}]}
        ),
    )
    commandes_simulees.repondre_si(lambda c: c[0] == "smartctl", sortie=SMART_OK)
    commandes_simulees.repondre_si(lambda c: c[0] == "hdparm", sortie="", code=1)
    resultat = inventaire.inventorier("/dev/nvme0n1")
    assert resultat["technologie"] == "SSD_NVME"


def test_detection_sed(commandes_simulees: Simulateur) -> None:
    smart_sed = json.dumps({"smart_status": {"passed": True}, "trusted_computing": {"opal": True}})
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk", sortie=LSBLK)
    commandes_simulees.repondre_si(lambda c: c[0] == "smartctl", sortie=smart_sed)
    commandes_simulees.repondre_si(lambda c: c[0] == "hdparm", sortie="", code=1)
    resultat = inventaire.inventorier("/dev/sdb")
    assert resultat["technologie"] == "SED"


def test_smart_secteurs_realloues_degrade(commandes_simulees: Simulateur) -> None:
    smart = json.dumps(
        {
            "smart_status": {"passed": True},
            "ata_smart_attributes": {"table": [{"id": 5, "raw": {"value": 12}}]},
        }
    )
    commandes_simulees.repondre_si(lambda c: c[0] == "smartctl", sortie=smart)
    resultat = inventaire.inventorier_smart("/dev/sdb")
    assert resultat["sante"] == "DEGRADE"
    assert resultat["smart"]["reallocated_sectors"] == 12


def test_lsblk_illisible_ne_plante_pas(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk", sortie="pas du json", code=0)
    assert inventaire.inventorier_lsblk("/dev/sdb") == {}
