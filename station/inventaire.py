"""Inventaire d'un support : lsblk / smartctl / nvme-cli / hdparm → dict Python.

Détection HPA (hdparm -N), DCO (hdparm --dco-identify) et SED (auto-chiffrant).
Aucune de ces commandes ne modifie le disque : ce module est en lecture seule.
"""
from __future__ import annotations

import json
import re

from station import commandes


def _technologie(peripherique: str, rotationnel: bool | None, transport: str) -> str:
    base = peripherique.lower()
    if "nvme" in base:
        return "SSD_NVME"
    if transport == "sas":
        return "SAS"
    if "mmcblk" in base or transport == "mmc":
        return "SD"
    if transport == "usb":
        return "USB"
    if rotationnel is True:
        return "HDD_SATA"
    if rotationnel is False:
        return "SSD_SATA"
    return "INCONNU"


def inventorier_lsblk(peripherique: str) -> dict:
    resultat = commandes.executer(
        ["lsblk", "-J", "-b", "-d", "-o", "NAME,MODEL,SERIAL,SIZE,ROTA,TRAN,VENDOR", peripherique]
    )
    if not resultat.ok:
        return {}
    try:
        arbre = json.loads(resultat.sortie)
    except json.JSONDecodeError:
        return {}
    peripheriques = arbre.get("blockdevices", [])
    if not peripheriques:
        return {}
    disque = peripheriques[0]
    rota = disque.get("rota")
    return {
        "modele": (disque.get("model") or "").strip() or None,
        "numero_serie": (disque.get("serial") or "").strip() or None,
        "constructeur": (disque.get("vendor") or "").strip() or None,
        "capacite_octets": int(disque["size"]) if disque.get("size") else None,
        "interface": (disque.get("tran") or "").strip() or None,
        "_rotationnel": None if rota is None else bool(int(rota)) if str(rota).isdigit() else None,
        "_transport": (disque.get("tran") or "").strip().lower(),
    }


def inventorier_smart(peripherique: str) -> dict:
    """Lecture SMART via smartctl. Renvoie un sous-ensemble utile + santé globale."""
    resultat = commandes.executer(["smartctl", "-j", "-a", peripherique])
    # smartctl utilise un code de retour en bitmask ; la sortie JSON reste exploitable.
    if not resultat.sortie.strip():
        return {"sante": "INCONNU", "smart": {}}
    try:
        donnees = json.loads(resultat.sortie)
    except json.JSONDecodeError:
        return {"sante": "INCONNU", "smart": {}}

    passe = donnees.get("smart_status", {}).get("passed")
    sante = "OK" if passe is True else "DEFAILLANT" if passe is False else "INCONNU"

    smart: dict = {}
    temperature = donnees.get("temperature", {}).get("current")
    if temperature is not None:
        smart["temperature_c"] = temperature
    heures = donnees.get("power_on_time", {}).get("hours")
    if heures is not None:
        smart["power_on_hours"] = heures

    realloues = _attribut_smart(donnees, 5)  # 5 = Reallocated_Sector_Ct
    if realloues is not None:
        smart["reallocated_sectors"] = realloues
        if realloues > 0 and sante == "OK":
            sante = "DEGRADE"

    chiffrement = donnees.get("ata_security") or {}
    return {
        "sante": sante,
        "smart": smart,
        "_sed": _detecter_sed_smart(donnees),
        "_ata_security": chiffrement,
    }


def _attribut_smart(donnees: dict, identifiant: int) -> int | None:
    for attribut in donnees.get("ata_smart_attributes", {}).get("table", []):
        if attribut.get("id") == identifiant:
            brut = attribut.get("raw", {})
            valeur = brut.get("value")
            return int(valeur) if isinstance(valeur, int) else None
    return None


def _detecter_sed_smart(donnees: dict) -> bool:
    """SED / auto-chiffrant : présence d'un jeu de fonctions de sécurité TCG/Opal."""
    texte = json.dumps(donnees).lower()
    return any(marqueur in texte for marqueur in ("opal", "tcg", "self-encrypting", "trusted computing"))


def detecter_hpa(peripherique: str) -> dict:
    """HPA (Host Protected Area) via hdparm -N. Une zone HPA masque des secteurs
    au système d'exploitation, qui échapperaient alors à l'effacement."""
    resultat = commandes.executer(["hdparm", "-N", peripherique])
    sortie = resultat.sortie + resultat.erreur
    # Format : « max sectors = 12345/67890, HPA is enabled »
    correspondance = re.search(r"=\s*(\d+)/(\d+)", sortie)
    if correspondance:
        visibles, natifs = int(correspondance.group(1)), int(correspondance.group(2))
        actif = "hpa is enabled" in sortie.lower() or visibles < natifs
        return {"detecte": bool(actif), "secteurs_visibles": visibles, "secteurs_natifs": natifs}
    if "disabled" in sortie.lower():
        return {"detecte": False}
    # Doute → on signale « inconnu » plutôt que « absent ».
    return {"detecte": None}


def detecter_dco(peripherique: str) -> dict:
    """DCO (Device Configuration Overlay) via hdparm --dco-identify. Peut, comme
    HPA, dissimuler de la capacité."""
    resultat = commandes.executer(["hdparm", "--dco-identify", peripherique])
    sortie = (resultat.sortie + resultat.erreur).lower()
    if "real max sectors" in sortie:
        return {"detecte": True}
    if "sg_io" in sortie or "not supported" in sortie or "bad" in sortie:
        return {"detecte": None}
    return {"detecte": False}


def inventorier(peripherique: str) -> dict:
    """Inventaire complet. Ne modifie jamais le disque.

    Les champs `hpa_detecte`/`dco_detecte` valent True s'ils sont détectés,
    False s'ils sont explicitement absents, et True aussi par PRUDENCE si le
    statut est indéterminé (mieux vaut suspecter une zone masquée que l'ignorer).
    """
    base = inventorier_lsblk(peripherique)
    smart = inventorier_smart(peripherique)
    hpa = detecter_hpa(peripherique)
    dco = detecter_dco(peripherique)

    rotationnel = base.get("_rotationnel")
    transport = base.get("_transport", "")
    technologie = "SED" if smart.get("_sed") else _technologie(peripherique, rotationnel, transport)

    return {
        "peripherique": peripherique,
        "numero_serie": base.get("numero_serie"),
        "modele": base.get("modele"),
        "constructeur": base.get("constructeur"),
        "capacite_octets": base.get("capacite_octets"),
        "technologie": technologie,
        "interface": base.get("interface"),
        "sante": smart.get("sante", "INCONNU"),
        "hpa_detecte": _prudence(hpa.get("detecte")),
        "dco_detecte": _prudence(dco.get("detecte")),
        "smart": smart.get("smart", {}),
        "_ata_security": smart.get("_ata_security", {}),
        "_hpa_brut": hpa,
        "_dco_brut": dco,
    }


def _prudence(valeur: bool | None) -> bool:
    """None (statut indéterminé) est traité comme True : on suppose une zone masquée."""
    return True if valeur is None else bool(valeur)
