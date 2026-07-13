"""Produit le rapport JSON au format d'interface (spécification §4).

Ce fichier est le SEUL point de contact avec le logiciel métier. Son format
est figé : format_version 1.0. Le log_sha256 est calculé ici sur le log brut.
"""
from __future__ import annotations

import hashlib
import json
import socket
from datetime import datetime, timezone

from station.effacement import ResultatEffacement
from station.verification import ResultatVerification

FORMAT_VERSION = "1.0"


def _maintenant() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def construire_rapport(
    code_interne: str,
    inventaire: dict,
    effacement: ResultatEffacement,
    verification: ResultatVerification,
    debut: str,
    fin: str,
    duree_secondes: int,
    station: str | None = None,
) -> dict:
    log_brut = effacement.log
    return {
        "format_version": FORMAT_VERSION,
        "station": station or socket.gethostname(),
        "outil": effacement.outil,
        "support": {
            "code_interne": code_interne,
            "numero_serie": inventaire.get("numero_serie"),
            "modele": inventaire.get("modele"),
            "constructeur": inventaire.get("constructeur"),
            "capacite_octets": inventaire.get("capacite_octets"),
            "technologie": inventaire.get("technologie"),
            "interface": inventaire.get("interface"),
            "sante": inventaire.get("sante"),
            "hpa_detecte": bool(inventaire.get("hpa_detecte")),
            "dco_detecte": bool(inventaire.get("dco_detecte")),
            "smart": inventaire.get("smart", {}),
        },
        "operation": {
            "methode": effacement.methode,
            "norme_reference": effacement.norme_reference,
            "nb_passes": effacement.nb_passes,
            "debut": debut,
            "fin": fin,
            "duree_secondes": duree_secondes,
            "resultat": effacement.resultat,
        },
        "verification": {
            "faite": verification.faite,
            "ok": verification.ok if verification.faite else None,
            "secteurs_testes": verification.secteurs_testes,
            "zones": verification.zones,
            "anomalies": verification.anomalies,
        },
        "log_brut": log_brut,
        "log_sha256": hashlib.sha256(log_brut.encode("utf-8")).hexdigest(),
    }


def ecrire_rapport(rapport: dict, chemin: str) -> None:
    with open(chemin, "w", encoding="utf-8") as fichier:
        json.dump(rapport, fichier, ensure_ascii=False, indent=2)


def horodatage_iso() -> str:
    return _maintenant()
