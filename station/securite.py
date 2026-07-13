"""Les trois garde-fous avant tout effacement. Refus par défaut.

Toute fonction de ce module qui a le moindre doute REFUSE. Il vaut mille fois
mieux refuser d'effacer un disque effaçable que d'effacer un disque système.
"""
from __future__ import annotations

import json
import os

from station import commandes


class RefusSecurite(Exception):
    """Levée dès qu'un garde-fou refuse. L'effacement ne doit jamais continuer."""


# ── Garde-fou 1 : le périphérique ne doit pas porter le système ──────────────

# Points de montage dont le disque porteur ne doit JAMAIS être effacé.
POINTS_CRITIQUES = ("/", "/boot", "/boot/efi", "/etc", "/usr", "/var", "/home")


def _disque_parent(peripherique: str) -> str:
    """Ramène une partition à son disque parent : /dev/sda3 → /dev/sda,
    /dev/nvme0n1p2 → /dev/nvme0n1. Utilise lsblk, avec repli syntaxique."""
    resultat = commandes.executer(["lsblk", "-no", "pkname", peripherique])
    if resultat.ok and resultat.sortie.strip():
        # pkname peut renvoyer plusieurs lignes (partition → disque) : on prend la racine.
        parent = resultat.sortie.strip().splitlines()[-1].strip()
        return f"/dev/{parent}"
    return _disque_parent_syntaxique(peripherique)


def _disque_parent_syntaxique(peripherique: str) -> str:
    nom = peripherique
    # nvme0n1p3 → nvme0n1 ; mmcblk0p2 → mmcblk0
    for marqueur in ("p",):
        base = os.path.basename(nom)
        if ("nvme" in base or "mmcblk" in base) and marqueur in base:
            racine, _, suffixe = base.rpartition(marqueur)
            if suffixe.isdigit():
                return f"/dev/{racine}"
    # sda3 → sda
    base = os.path.basename(nom)
    return "/dev/" + base.rstrip("0123456789")


def _disques_systeme() -> set[str]:
    """Ensemble des disques parents portant un point de montage critique.

    Croisement de deux sources : findmnt (montages actifs) et lsblk
    (arborescence complète). Si une source échoue, on ne baisse pas la garde :
    l'autre source seule suffit à refuser.
    """
    disques: set[str] = set()

    findmnt = commandes.executer(["findmnt", "-rno", "SOURCE,TARGET"])
    if findmnt.ok:
        for ligne in findmnt.sortie.splitlines():
            morceaux = ligne.split()
            if len(morceaux) < 2:
                continue
            source, cible = morceaux[0], morceaux[1]
            if cible in POINTS_CRITIQUES and source.startswith("/dev/"):
                disques.add(_disque_parent(source))

    lsblk = commandes.executer(["lsblk", "-J", "-o", "NAME,MOUNTPOINT,PATH,PKNAME"])
    if lsblk.ok:
        try:
            arbre = json.loads(lsblk.sortie)
        except json.JSONDecodeError:
            arbre = {"blockdevices": []}
        for disque in arbre.get("blockdevices", []):
            _collecter_disques_montes(disque, None, disques)

    return disques


def _collecter_disques_montes(noeud: dict, disque_racine: str | None, accumulateur: set[str]) -> None:
    chemin = noeud.get("path") or f"/dev/{noeud.get('name', '')}"
    racine = disque_racine or chemin  # le premier niveau est le disque
    point = noeud.get("mountpoint")
    if point in POINTS_CRITIQUES:
        accumulateur.add(racine)
    for enfant in noeud.get("children", []) or []:
        _collecter_disques_montes(enfant, racine, accumulateur)


def verifier_non_systeme(peripherique: str) -> None:
    """Garde-fou 1. Refuse si le périphérique (ou son disque parent) porte le système."""
    cible = _disque_parent(peripherique) if _est_partition(peripherique) else peripherique
    systeme = _disques_systeme()
    if cible in systeme or peripherique in systeme:
        raise RefusSecurite(
            f"REFUS : {peripherique} (disque {cible}) porte le système, /boot ou un montage "
            f"critique. Périphériques système détectés : {sorted(systeme)}."
        )
    # Refus supplémentaire si le périphérique EST la source d'un montage critique direct.
    if _porte_montage_critique_direct(peripherique):
        raise RefusSecurite(f"REFUS : {peripherique} porte directement un montage critique.")


def _est_partition(peripherique: str) -> bool:
    base = os.path.basename(peripherique)
    if "nvme" in base or "mmcblk" in base:
        return "p" in base and base[-1].isdigit()
    return base[-1:].isdigit()


def _porte_montage_critique_direct(peripherique: str) -> bool:
    findmnt = commandes.executer(["findmnt", "-rno", "SOURCE,TARGET"])
    if not findmnt.ok:
        return False
    for ligne in findmnt.sortie.splitlines():
        morceaux = ligne.split()
        if len(morceaux) >= 2 and morceaux[0] == peripherique and morceaux[1] in POINTS_CRITIQUES:
            return True
    return False


# ── Garde-fou 2 : whitelist explicite ───────────────────────────────────────


def verifier_peripherique_bloc(peripherique: str) -> None:
    """Garde-fou 2. Le périphérique doit être un chemin /dev/* explicite, existant,
    de type bloc. On n'accepte jamais un motif, un dossier, ni une découverte auto."""
    if not peripherique.startswith("/dev/"):
        raise RefusSecurite(f"REFUS : {peripherique!r} n'est pas un chemin /dev/ explicite.")
    if any(caractere in peripherique for caractere in "*?[] "):
        raise RefusSecurite(f"REFUS : {peripherique!r} ressemble à un motif, pas à un périphérique unique.")
    if not os.path.exists(peripherique):
        raise RefusSecurite(f"REFUS : {peripherique} n'existe pas.")
    import stat

    mode = os.stat(peripherique).st_mode
    if not stat.S_ISBLK(mode):
        raise RefusSecurite(f"REFUS : {peripherique} n'est pas un périphérique de type bloc.")


# ── Garde-fou 3 : confirmation par saisie manuelle du numéro de série ────────

REPONSES_INTERDITES = {"oui", "o", "y", "yes", "ok", "1", "true", "vrai"}


def confirmer_numero_serie(
    numero_serie_attendu: str,
    saisie: str,
) -> None:
    """Garde-fou 3. La saisie doit être EXACTEMENT le numéro de série complet.
    Une confirmation « oui/o/y » est explicitement refusée."""
    attendu = (numero_serie_attendu or "").strip()
    if not attendu:
        raise RefusSecurite(
            "REFUS : numéro de série du disque inconnu ou illisible. Confirmation manuelle "
            "impossible → traiter le support par destruction physique."
        )
    saisie_nettoyee = saisie.strip()
    if saisie_nettoyee.lower() in REPONSES_INTERDITES:
        raise RefusSecurite(
            "REFUS : une confirmation « oui/o/y » est interdite. Saisir le numéro de série COMPLET."
        )
    if saisie_nettoyee != attendu:
        raise RefusSecurite(
            "REFUS : le numéro de série saisi ne correspond pas exactement au disque cible."
        )


def demander_confirmation_interactive(numero_serie_attendu: str, cible: str) -> None:
    """Invite interactive (utilisée par l'orchestrateur, jamais dans les tests)."""
    print(f"\n⚠️  EFFACEMENT IRRÉVERSIBLE du périphérique {cible}")
    print("Pour confirmer, saisissez le NUMÉRO DE SÉRIE COMPLET du disque cible.")
    print("(une réponse oui/o/y est refusée)")
    saisie = input("Numéro de série : ")
    confirmer_numero_serie(numero_serie_attendu, saisie)
