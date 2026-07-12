from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Audit(Base):
    """Journal d'audit chaîné : chaque ligne embarque le SHA-256 de la précédente.

    La première ligne a hash_precedent = '0'*64 (genesis).
    Toute modification/suppression d'une ligne rompt la chaîne → détectable.
    """

    __tablename__ = "audit"
    __table_args__ = (
        Index("idx_audit_horodatage", "horodatage"),
        Index("idx_audit_entite", "entite", "entite_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horodatage: Mapped[str] = mapped_column(Text, nullable=False)
    utilisateur_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("utilisateurs.id"))
    action: Mapped[str] = mapped_column(Text, nullable=False)  # CREATE_CLIENT, IMPORT_OP, ...
    entite: Mapped[str] = mapped_column(Text, nullable=False)  # table concernée
    entite_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text)  # JSON
    hash_precedent: Mapped[str] = mapped_column(Text, nullable=False)
    hash_courant: Mapped[str] = mapped_column(Text, nullable=False)
