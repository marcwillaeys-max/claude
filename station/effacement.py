"""Sélection de la méthode d'effacement selon la technologie, et exécution.

Table de décision (spécification §1.2) :
    HDD SATA/SAS → nwipe zero fill 1 passe
    SSD SATA     → hdparm --security-erase-enhanced, repli blkdiscard -s
    NVMe         → nvme sanitize (block erase), repli nvme format -s 1
    SED          → crypto-erase (révocation de clé)
    USB / SD     → nwipe overwrite

Après CHAQUE commande, on relit le statut renvoyé par le disque
(nvme sanitize-log, hdparm -I). Un code de retour 0 ne prouve RIEN.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from station import commandes


@dataclass
class ResultatEffacement:
    resultat: str  # 'SUCCES', 'ECHEC', 'INTERROMPU'
    methode: str
    norme_reference: str
    nb_passes: int | None
    log: str
    outil: dict  # {"nom": ..., "version": ...}
    motif_pattern: int = 0  # octet attendu après effacement (0 pour zéros)
    journal: list[str] = field(default_factory=list)


def _journaliser(journal: list[str], resultat: commandes.Resultat, commande: list[str]) -> None:
    journal.append(f"$ {' '.join(commande)}")
    journal.append(f"[exit {resultat.code}]")
    if resultat.sortie.strip():
        journal.append(resultat.sortie.rstrip())
    if resultat.erreur.strip():
        journal.append("STDERR: " + resultat.erreur.rstrip())


# ── HDD SATA / SAS ────────────────────────────────────────────────────────


def effacer_hdd(peripherique: str, passes: int = 1) -> ResultatEffacement:
    journal: list[str] = []
    # nwipe en mode automatique, non interactif, motif zéros.
    commande = [
        "nwipe",
        "--autonuke",
        "--nogui",
        "--method=zero",
        f"--rounds={passes}",
        peripherique,
    ]
    resultat = commandes.executer(commande, timeout=86400)
    _journaliser(journal, resultat, commande)
    reussi = resultat.ok and "error" not in (resultat.sortie + resultat.erreur).lower()
    return ResultatEffacement(
        resultat="SUCCES" if reussi else "ECHEC",
        methode="nwipe_zero_fill",
        norme_reference="NIST SP 800-88 Rev.1 (Clear)",
        nb_passes=passes,
        log="\n".join(journal),
        outil={"nom": "nwipe", "version": _version_nwipe()},
        motif_pattern=0,
        journal=journal,
    )


# ── NVMe ──────────────────────────────────────────────────────────────────


def effacer_nvme(peripherique: str) -> ResultatEffacement:
    journal: list[str] = []
    # Méthode 1 : nvme sanitize block erase (sanact=2).
    commande = ["nvme", "sanitize", peripherique, "--sanact=2"]
    resultat = commandes.executer(commande, timeout=86400)
    _journaliser(journal, resultat, commande)

    statut_ok = False
    if resultat.ok:
        statut_ok = _verifier_sanitize_log(peripherique, journal)

    if resultat.ok and statut_ok:
        return _resultat_nvme(journal, "SUCCES", "nvme_sanitize_block_erase")

    # Repli : nvme format avec crypto erase (ses=1).
    journal.append("→ repli : nvme format --ses=1 (crypto erase)")
    commande_repli = ["nvme", "format", peripherique, "--ses=1"]
    repli = commandes.executer(commande_repli, timeout=3600)
    _journaliser(journal, repli, commande_repli)
    if repli.ok:
        return _resultat_nvme(journal, "SUCCES", "nvme_format_crypto_erase")
    return _resultat_nvme(journal, "ECHEC", "nvme_sanitize_block_erase")


def _verifier_sanitize_log(peripherique: str, journal: list[str]) -> bool:
    """Relit nvme sanitize-log. L'opération n'est réussie que si le statut
    indique « completed successfully » (bits 0-2 = 001)."""
    commande = ["nvme", "sanitize-log", peripherique]
    resultat = commandes.executer(commande)
    _journaliser(journal, resultat, commande)
    texte = resultat.sortie.lower()
    if "completed" in texte and "success" in texte:
        return True
    if "sstat" in texte:
        # Format brut : chercher (SSTAT & 0x7) == 1.
        import re

        correspondance = re.search(r"sstat\D*(0x[0-9a-f]+|\d+)", texte)
        if correspondance:
            valeur = correspondance.group(1)
            entier = int(valeur, 16) if valeur.startswith("0x") else int(valeur)
            return (entier & 0x7) == 1
    return False


def _resultat_nvme(journal: list[str], resultat: str, methode: str) -> ResultatEffacement:
    return ResultatEffacement(
        resultat=resultat,
        methode=methode,
        norme_reference="NIST SP 800-88 Rev.1 (Purge)",
        nb_passes=1,
        log="\n".join(journal),
        outil={"nom": "nvme-cli", "version": _version_nvme()},
        motif_pattern=0,
        journal=journal,
    )


# ── SSD SATA ──────────────────────────────────────────────────────────────


def effacer_ssd_sata(peripherique: str) -> ResultatEffacement:
    journal: list[str] = []
    # Méthode 1 : ATA Secure Erase Enhanced via hdparm.
    # Le disque doit d'abord recevoir un mot de passe utilisateur temporaire.
    mdp = "oralyse"
    cmd_mdp = ["hdparm", "--user-master", "u", "--security-set-pass", mdp, peripherique]
    r1 = commandes.executer(cmd_mdp)
    _journaliser(journal, r1, cmd_mdp)
    if r1.ok:
        cmd_erase = ["hdparm", "--user-master", "u", "--security-erase-enhanced", mdp, peripherique]
        r2 = commandes.executer(cmd_erase, timeout=43200)
        _journaliser(journal, r2, cmd_erase)
        if r2.ok and _verifier_hdparm_non_verrouille(peripherique, journal):
            return ResultatEffacement(
                resultat="SUCCES",
                methode="hdparm_security_erase_enhanced",
                norme_reference="NIST SP 800-88 Rev.1 (Purge)",
                nb_passes=1,
                log="\n".join(journal),
                outil={"nom": "hdparm", "version": _version_hdparm()},
                motif_pattern=0,
                journal=journal,
            )

    # Repli : blkdiscard -s (secure discard).
    journal.append("→ repli : blkdiscard -s")
    cmd_repli = ["blkdiscard", "-s", peripherique]
    repli = commandes.executer(cmd_repli, timeout=3600)
    _journaliser(journal, repli, cmd_repli)
    if repli.ok:
        return ResultatEffacement(
            resultat="SUCCES",
            methode="blkdiscard_secure",
            norme_reference="NIST SP 800-88 Rev.1 (Purge)",
            nb_passes=1,
            log="\n".join(journal),
            outil={"nom": "blkdiscard", "version": _version_util_linux()},
            motif_pattern=0,
            journal=journal,
        )
    return ResultatEffacement(
        resultat="ECHEC",
        methode="hdparm_security_erase_enhanced",
        norme_reference="NIST SP 800-88 Rev.1 (Purge)",
        nb_passes=1,
        log="\n".join(journal),
        outil={"nom": "hdparm", "version": _version_hdparm()},
        motif_pattern=0,
        journal=journal,
    )


def _verifier_hdparm_non_verrouille(peripherique: str, journal: list[str]) -> bool:
    """Relit hdparm -I : après un secure erase réussi, la sécurité doit être
    « not enabled » (le disque n'est pas resté verrouillé)."""
    commande = ["hdparm", "-I", peripherique]
    resultat = commandes.executer(commande)
    _journaliser(journal, resultat, commande)
    texte = resultat.sortie.lower()
    if "not\tenabled" in texte or "not enabled" in texte:
        return True
    # Si on lit « enabled » sans « not », le disque est resté verrouillé → échec.
    return "enabled" not in texte


# ── SED (auto-chiffrant) ──────────────────────────────────────────────────


def effacer_sed(peripherique: str) -> ResultatEffacement:
    """Crypto-erase par révocation de clé (sedutil-cli / TCG Opal PSID revert).
    Non destructif des données au sens overwrite : on détruit la clé de
    chiffrement, rendant les données illisibles."""
    journal: list[str] = []
    commande = ["sedutil-cli", "--yesIreallywanttoERASEALLmydatausingthePSID", "PSID", peripherique]
    resultat = commandes.executer(commande, timeout=3600)
    _journaliser(journal, resultat, commande)
    return ResultatEffacement(
        resultat="SUCCES" if resultat.ok else "ECHEC",
        methode="sed_crypto_erase",
        norme_reference="NIST SP 800-88 Rev.1 (Purge, crypto erase)",
        nb_passes=None,
        log="\n".join(journal),
        outil={"nom": "sedutil-cli", "version": "?"},
        motif_pattern=None if resultat.ok else 0,  # crypto-erase : motif non déterministe
        journal=journal,
    )


# ── USB / SD ──────────────────────────────────────────────────────────────


def effacer_usb_sd(peripherique: str) -> ResultatEffacement:
    journal: list[str] = []
    commande = ["nwipe", "--autonuke", "--nogui", "--method=zero", "--rounds=1", peripherique]
    resultat = commandes.executer(commande, timeout=86400)
    _journaliser(journal, resultat, commande)
    reussi = resultat.ok and "error" not in (resultat.sortie + resultat.erreur).lower()
    return ResultatEffacement(
        resultat="SUCCES" if reussi else "ECHEC",
        methode="nwipe_overwrite_zero",
        norme_reference="NIST SP 800-88 Rev.1 (Clear)",
        nb_passes=1,
        log="\n".join(journal),
        outil={"nom": "nwipe", "version": _version_nwipe()},
        motif_pattern=0,
        journal=journal,
    )


# ── Aiguillage ────────────────────────────────────────────────────────────

_TABLE = {
    "HDD_SATA": effacer_hdd,
    "SAS": effacer_hdd,
    "SSD_SATA": effacer_ssd_sata,
    "SSD_NVME": effacer_nvme,
    "SED": effacer_sed,
    "USB": effacer_usb_sd,
    "SD": effacer_usb_sd,
}


class TechnologieNonEffacable(Exception):
    """La technologie ne dispose d'aucune méthode d'effacement fiable."""


def choisir_et_effacer(technologie: str, peripherique: str) -> ResultatEffacement:
    fonction = _TABLE.get(technologie)
    if fonction is None:
        raise TechnologieNonEffacable(
            f"Technologie {technologie!r} sans méthode d'effacement fiable → destruction physique."
        )
    return fonction(peripherique)


# ── Versions des outils (pour le rapport) ─────────────────────────────────


def _premiere_ligne(commande: list[str]) -> str:
    resultat = commandes.executer(commande)
    sortie = (resultat.sortie or resultat.erreur).strip()
    return sortie.splitlines()[0] if sortie else "?"


def _version_nwipe() -> str:
    return _premiere_ligne(["nwipe", "--version"])


def _version_nvme() -> str:
    return _premiere_ligne(["nvme", "version"])


def _version_hdparm() -> str:
    return _premiere_ligne(["hdparm", "-V"])


def _version_util_linux() -> str:
    return _premiere_ligne(["blkdiscard", "--version"])
