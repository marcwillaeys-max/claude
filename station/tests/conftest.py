"""Garde-fou de test : subprocess est neutralisé pour TOUTE la suite.

Aucun test ne doit pouvoir lancer une vraie commande système, même par erreur.
On remplace station.commandes.executer par une fausse implémentation pilotée
par chaque test (fixture `commandes_simulees`).
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable

import pytest

from station import commandes


@pytest.fixture(autouse=True)
def interdire_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Filet de sécurité : si un test oublie de mocker, subprocess.run explose
    au lieu de toucher la machine."""

    def _interdit(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("subprocess.run appelé dans un test — INTERDIT (mock manquant)")

    monkeypatch.setattr(subprocess, "run", _interdit)


class Simulateur:
    """Enregistre des réponses par nom de commande et journalise les appels."""

    def __init__(self) -> None:
        self.reponses: dict[str, commandes.Resultat] = {}
        self.par_defaut = commandes.Resultat(code=0, sortie="", erreur="")
        self.appels: list[list[str]] = []
        self._regles: list[tuple[Callable[[list[str]], bool], commandes.Resultat]] = []

    def repondre(self, cle: str, sortie: str = "", code: int = 0, erreur: str = "") -> None:
        self.reponses[cle] = commandes.Resultat(code=code, sortie=sortie, erreur=erreur)

    def repondre_si(
        self, predicat: Callable[[list[str]], bool], sortie: str = "", code: int = 0, erreur: str = ""
    ) -> None:
        self._regles.append((predicat, commandes.Resultat(code=code, sortie=sortie, erreur=erreur)))

    def executer(self, commande: list[str], entree: str | None = None, timeout: int = 120):
        self.appels.append(commande)
        for predicat, resultat in self._regles:
            if predicat(commande):
                return resultat
        jointure = " ".join(commande)
        for cle, resultat in self.reponses.items():
            if cle in jointure:
                return resultat
        return self.par_defaut


@pytest.fixture
def commandes_simulees(monkeypatch: pytest.MonkeyPatch) -> Simulateur:
    simulateur = Simulateur()
    monkeypatch.setattr(commandes, "executer", simulateur.executer)
    # Rediriger aussi les références déjà importées dans les modules.
    for module in ("securite", "inventaire", "effacement"):
        import importlib

        mod = importlib.import_module(f"station.{module}")
        if hasattr(mod, "commandes"):
            monkeypatch.setattr(mod.commandes, "executer", simulateur.executer)
    return simulateur
