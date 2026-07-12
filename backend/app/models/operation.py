from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

RESULTATS = ("SUCCES", "ECHEC", "INTERROMPU")


class Operation(Base):
    """Une tentative d'effacement, importée depuis un rapport de la station.

    Plusieurs opérations possibles par support (échec → nouvelle tentative).
    L'historique conserve TOUTES les tentatives, y compris les échecs.
    """

    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint("resultat IN ('SUCCES','ECHEC','INTERROMPU')", name="ck_operations_resultat"),
        Index("idx_operations_support", "support_id"),
        Index("idx_operations_debut", "debut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    support_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("supports.id", ondelete="RESTRICT"), nullable=False
    )
    technicien_id: Mapped[int] = mapped_column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    station: Mapped[str | None] = mapped_column(Text)  # hostname de la station
    methode: Mapped[str] = mapped_column(Text, nullable=False)  # ex: nvme_sanitize_block_erase
    norme_reference: Mapped[str] = mapped_column(
        Text, nullable=False, default="NIST SP 800-88 Rev.1", server_default="NIST SP 800-88 Rev.1"
    )
    nb_passes: Mapped[int | None] = mapped_column(Integer)
    debut: Mapped[str] = mapped_column(Text, nullable=False)
    fin: Mapped[str | None] = mapped_column(Text)
    duree_secondes: Mapped[int | None] = mapped_column(Integer)
    resultat: Mapped[str] = mapped_column(Text, nullable=False)
    verification_faite: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    verification_ok: Mapped[int | None] = mapped_column(Integer)  # NULL si non faite
    verification_detail: Mapped[str | None] = mapped_column(Text)  # JSON : secteurs testés, résultats
    log_brut: Mapped[str | None] = mapped_column(Text)  # sortie complète nwipe
    log_sha256: Mapped[str] = mapped_column(Text, nullable=False)  # hash du log brut
    outil_version: Mapped[str | None] = mapped_column(Text)  # ex: nwipe 0.36
    importe_le: Mapped[str] = mapped_column(Text, nullable=False)
