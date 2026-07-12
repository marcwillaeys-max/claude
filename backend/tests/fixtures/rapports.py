"""Fabrique de rapports station valides pour les tests.

`construire_rapport` produit un rapport nominal (SUCCES + vérification OK)
dont le log_sha256 est correct ; chaque test le déforme ensuite selon son besoin.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

LOG_NOMINAL = "nwipe 0.36 démarré\n[ok] passe 1/1 zéros\n[ok] vérification 1024 secteurs\nterminé sans erreur\n"


def construire_rapport(code_interne: str, **surcharges: Any) -> dict:
    """Rapport nominal. Les surcharges s'appliquent par section, ex:
    construire_rapport("SUP-...", operation={"resultat": "ECHEC"}, verification={"faite": False}).
    """
    rapport: dict = {
        "format_version": "1.0",
        "station": "oralyse-station-01",
        "outil": {"nom": "nwipe", "version": "0.36"},
        "support": {
            "code_interne": code_interne,
            "numero_serie": "WD-WCC4E1234567",
            "modele": "WDC WD10EZEX-08WN4A0",
            "constructeur": "Western Digital",
            "capacite_octets": 1000204886016,
            "technologie": "HDD_SATA",
            "interface": "SATA 3.0 6.0 Gb/s",
            "sante": "OK",
            "hpa_detecte": False,
            "dco_detecte": False,
            "smart": {"temperature_c": 34, "power_on_hours": 21455, "reallocated_sectors": 0},
        },
        "operation": {
            "methode": "nwipe_zero_fill",
            "norme_reference": "NIST SP 800-88 Rev.1 (Clear)",
            "nb_passes": 1,
            "debut": "2026-07-12T09:14:03Z",
            "fin": "2026-07-12T11:47:52Z",
            "duree_secondes": 9229,
            "resultat": "SUCCES",
        },
        "verification": {
            "faite": True,
            "ok": True,
            "secteurs_testes": 1024,
            "zones": ["premiers_100Mo", "derniers_100Mo", "aleatoire_1000_secteurs"],
            "anomalies": [],
        },
        "log_brut": LOG_NOMINAL,
        "log_sha256": hashlib.sha256(LOG_NOMINAL.encode()).hexdigest(),
    }
    rapport = copy.deepcopy(rapport)
    for cle, valeur in surcharges.items():
        if isinstance(valeur, dict) and isinstance(rapport.get(cle), dict):
            rapport[cle].update(valeur)
        else:
            rapport[cle] = valeur
    return rapport


def encoder(rapport: dict) -> bytes:
    return json.dumps(rapport, ensure_ascii=False).encode("utf-8")
