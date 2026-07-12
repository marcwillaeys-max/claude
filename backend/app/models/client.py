from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint("archive IN (0,1)", name="ck_clients_archive"),
        Index("idx_clients_raison", "raison_sociale"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_client: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # ex: CLI-0001
    raison_sociale: Mapped[str] = mapped_column(Text, nullable=False)
    siret: Mapped[str | None] = mapped_column(Text)
    adresse: Mapped[str | None] = mapped_column(Text)
    code_postal: Mapped[str | None] = mapped_column(Text)
    ville: Mapped[str | None] = mapped_column(Text)
    contact_nom: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    contact_telephone: Mapped[str | None] = mapped_column(Text)
    commentaires: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[str] = mapped_column(Text, nullable=False)  # ISO-8601 UTC
    cree_par: Mapped[int] = mapped_column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    archive: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
