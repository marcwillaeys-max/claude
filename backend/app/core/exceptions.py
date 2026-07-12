"""Exceptions métier — levées par les services, traduites en HTTP par l'API.

Les services ne connaissent pas HTTP : ils lèvent ces exceptions,
et app.main enregistre les handlers qui les convertissent en réponses.
"""
from __future__ import annotations


class ErreurMetier(Exception):
    """Base de toutes les erreurs métier."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class IntrouvableError(ErreurMetier):
    """L'entité demandée n'existe pas."""


class ConflitError(ErreurMetier):
    """Violation d'unicité ou état incompatible (ex: identifiant déjà pris)."""


class ValidationMetierError(ErreurMetier):
    """Donnée refusée par une règle métier."""


class AuthentificationError(ErreurMetier):
    """Identifiants invalides ou jeton invalide/expiré."""


class AutorisationError(ErreurMetier):
    """Utilisateur authentifié mais rôle insuffisant."""
