"""Vérification post-effacement : relecture d'échantillons (spécification §1.1).

On relit :
    - les 100 premiers Mo,
    - les 100 derniers Mo,
    - 1000 secteurs (512 o) tirés au hasard sur tout le disque,
et on vérifie que chaque octet correspond au motif attendu (0x00 après un
zero-fill). Toute divergence est une anomalie ; le rapport les liste.

Lecture seule via os.pread. Aucune écriture.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

CENT_MO = 100 * 1024 * 1024
TAILLE_SECTEUR = 512
NB_SECTEURS_ALEATOIRES = 1000
TAILLE_BLOC_LECTURE = 1024 * 1024  # 1 Mo


@dataclass
class ResultatVerification:
    faite: bool
    ok: bool
    secteurs_testes: int
    zones: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)


def _taille_peripherique(fd: int) -> int:
    return os.lseek(fd, 0, os.SEEK_END)


def _lire(fd: int, offset: int, taille: int) -> bytes:
    donnees = b""
    restant = taille
    position = offset
    while restant > 0:
        morceau = os.pread(fd, min(restant, TAILLE_BLOC_LECTURE), position)
        if not morceau:
            break
        donnees += morceau
        position += len(morceau)
        restant -= len(morceau)
    return donnees


def _controler_motif(donnees: bytes, motif: int) -> int:
    """Retourne le nombre d'octets NON conformes au motif attendu."""
    attendu = bytes([motif]) * len(donnees)
    if donnees == attendu:
        return 0
    return sum(1 for octet in donnees if octet != motif)


def verifier(peripherique: str, motif: int | None) -> ResultatVerification:
    """motif = octet attendu (0 pour zero-fill). Si motif est None (crypto-erase,
    motif non déterministe), la vérification par relecture n'est pas applicable :
    on renvoie faite=False plutôt que de prétendre à une vérification impossible."""
    if motif is None:
        return ResultatVerification(
            faite=False,
            ok=False,
            secteurs_testes=0,
            zones=[],
            anomalies=["Motif non déterministe (crypto-erase) : relecture non applicable."],
        )

    zones: list[str] = []
    anomalies: list[str] = []
    secteurs_testes = 0

    fd = os.open(peripherique, os.O_RDONLY)
    try:
        taille = _taille_peripherique(fd)

        # 100 premiers Mo.
        debut = _lire(fd, 0, min(CENT_MO, taille))
        non_conformes = _controler_motif(debut, motif)
        zones.append("premiers_100Mo")
        secteurs_testes += len(debut) // TAILLE_SECTEUR
        if non_conformes:
            anomalies.append(f"premiers_100Mo : {non_conformes} octet(s) non conformes")

        # 100 derniers Mo.
        if taille > CENT_MO:
            offset_fin = max(0, taille - CENT_MO)
            fin = _lire(fd, offset_fin, taille - offset_fin)
            non_conformes = _controler_motif(fin, motif)
            zones.append("derniers_100Mo")
            secteurs_testes += len(fin) // TAILLE_SECTEUR
            if non_conformes:
                anomalies.append(f"derniers_100Mo : {non_conformes} octet(s) non conformes")

        # 1000 secteurs aléatoires sur tout le disque.
        nb_secteurs_total = max(1, taille // TAILLE_SECTEUR)
        generateur = random.Random(secteurs_testes)  # reproductible pour un même disque
        secteurs_non_conformes = 0
        for _ in range(NB_SECTEURS_ALEATOIRES):
            index = generateur.randrange(nb_secteurs_total)
            secteur = _lire(fd, index * TAILLE_SECTEUR, TAILLE_SECTEUR)
            secteurs_testes += 1
            if _controler_motif(secteur, motif):
                secteurs_non_conformes += 1
        zones.append("aleatoire_1000_secteurs")
        if secteurs_non_conformes:
            anomalies.append(
                f"aleatoire_1000_secteurs : {secteurs_non_conformes} secteur(s) non conformes"
            )
    finally:
        os.close(fd)

    return ResultatVerification(
        faite=True,
        ok=not anomalies,
        secteurs_testes=secteurs_testes,
        zones=zones,
        anomalies=anomalies,
    )
