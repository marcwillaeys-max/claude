from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

STATUTS_LOT = ("OUVERT", "EN_COURS", "TERMINE", "CLOTURE")


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("statut IN ('OUVERT','EN_COURS','TERMINE','CLOTURE')", name="ck_lots_statut"),
        Index("idx_lots_client", "client_id"),
        Index("idx_lots_statut", "statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_lot: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # ex: LOT-2026-0042
    # ON DELETE RESTRICT : on n'efface jamais un client qui a des lots.
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    date_reception: Mapped[str] = mapped_column(Text, nullable=False)
    technicien_id: Mapped[int] = mapped_column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    statut: Mapped[str] = mapped_column(Text, nullable=False, default="OUVERT", server_default="OUVERT")
    nb_supports_annonce: Mapped[int | None] = mapped_column(Integer)
    commentaires: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[str] = mapped_column(Text, nullable=False)
    cloture_le: Mapped[str | None] = mapped_column(Text)
