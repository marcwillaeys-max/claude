from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ROLES = ("TECHNICIEN", "RESPONSABLE", "ADMINISTRATEUR")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    __table_args__ = (
        CheckConstraint("role IN ('TECHNICIEN','RESPONSABLE','ADMINISTRATEUR')", name="ck_utilisateurs_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifiant: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    nom_complet: Mapped[str] = mapped_column(Text, nullable=False)
    mot_de_passe: Mapped[str] = mapped_column(Text, nullable=False)  # argon2id
    role: Mapped[str] = mapped_column(Text, nullable=False)
    actif: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    cree_le: Mapped[str] = mapped_column(Text, nullable=False)
    derniere_conn: Mapped[str | None] = mapped_column(Text, nullable=True)
