"""Génération des identifiants métier : CLI-0001, LOT-2026-0001, SUP-2026-000001.

Les séquences LOT et SUP repartent à 1 chaque année civile (UTC).
La séquence est déduite du dernier numéro existant — jamais d'un compteur
en mémoire — pour rester correcte après redémarrage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.lot import Lot
from app.models.support import Support


def _annee_courante() -> int:
    return datetime.now(timezone.utc).year


def _prochain_numero(db: Session, colonne, prefixe: str) -> int:
    dernier: str | None = db.execute(
        select(func.max(colonne)).where(colonne.like(f"{prefixe}%"))
    ).scalar_one_or_none()
    if dernier is None:
        return 1
    return int(dernier.removeprefix(prefixe)) + 1


def prochain_numero_client(db: Session) -> str:
    return f"CLI-{_prochain_numero(db, Client.numero_client, 'CLI-'):04d}"


def prochain_numero_lot(db: Session) -> str:
    annee = _annee_courante()
    return f"LOT-{annee}-{_prochain_numero(db, Lot.numero_lot, f'LOT-{annee}-'):04d}"


def prochain_code_interne(db: Session) -> str:
    annee = _annee_courante()
    return f"SUP-{annee}-{_prochain_numero(db, Support.code_interne, f'SUP-{annee}-'):06d}"
