"""Configuration de l'application (pydantic-settings).

Toutes les valeurs sont surchargables par variables d'environnement
préfixées ORALYSE_ (ex: ORALYSE_DATABASE_URL).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORALYSE_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./oralyse.db"

    # JWT — la valeur par défaut ne sert qu'au développement local.
    jwt_secret: str = "dev-secret-a-remplacer-en-production"
    jwt_algorithme: str = "HS256"
    jwt_duree_minutes: int = 480

    # Compte administrateur créé au premier démarrage si la base est vide.
    admin_initial_identifiant: str = "admin"
    admin_initial_mot_de_passe: str = "changez-moi"
    admin_initial_nom: str = "Administrateur initial"


@lru_cache
def get_settings() -> Settings:
    return Settings()
