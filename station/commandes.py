"""Enveloppe unique autour de subprocess.

TOUT appel système passe par ici. Les tests monkeypatchent `executer`,
ce qui garantit qu'aucun test ne peut lancer une vraie commande.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class Resultat:
    code: int
    sortie: str
    erreur: str

    @property
    def ok(self) -> bool:
        return self.code == 0


def executer(commande: list[str], entree: str | None = None, timeout: int = 120) -> Resultat:
    """Lance une commande et capture sa sortie. Ne lève jamais sur code != 0 :
    l'appelant DOIT inspecter le code ET la sortie (un exit 0 ne prouve rien).
    """
    try:
        processus = subprocess.run(
            commande,
            input=entree,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return Resultat(code=127, sortie="", erreur=f"commande introuvable : {commande[0]}")
    except subprocess.TimeoutExpired:
        return Resultat(code=124, sortie="", erreur=f"délai dépassé : {' '.join(commande)}")
    return Resultat(code=processus.returncode, sortie=processus.stdout, erreur=processus.stderr)
