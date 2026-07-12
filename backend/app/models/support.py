from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

TECHNOLOGIES = ("HDD_SATA", "SSD_SATA", "SSD_NVME", "SAS", "USB", "SD", "SED", "INCONNU")
SANTES = ("OK", "DEGRADE", "DEFAILLANT", "INCONNU")
STATUTS_SUPPORT = (
    "EN_ATTENTE",
    "EN_COURS",
    "EFFACE_VERIFIE",
    "EFFACE_NON_VERIFIE",
    "ECHEC",
    "NON_EFFACABLE",
    "DETRUIT_PHYSIQUEMENT",
)
DESTINATIONS = ("REEMPLOI", "DESTRUCTION", "VALORISATION")


class Support(Base):
    __tablename__ = "supports"
    __table_args__ = (
        CheckConstraint(
            "technologie IN ('HDD_SATA','SSD_SATA','SSD_NVME','SAS','USB','SD','SED','INCONNU')",
            name="ck_supports_technologie",
        ),
        CheckConstraint("sante IN ('OK','DEGRADE','DEFAILLANT','INCONNU')", name="ck_supports_sante"),
        CheckConstraint(
            "statut IN ('EN_ATTENTE','EN_COURS','EFFACE_VERIFIE',"
            "'EFFACE_NON_VERIFIE','ECHEC','NON_EFFACABLE','DETRUIT_PHYSIQUEMENT')",
            name="ck_supports_statut",
        ),
        CheckConstraint(
            "destination IN ('REEMPLOI','DESTRUCTION','VALORISATION')", name="ck_supports_destination"
        ),
        Index("idx_supports_lot", "lot_id"),
        Index("idx_supports_serie", "numero_serie"),  # recherche fréquente
        Index("idx_supports_statut", "statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False
    )
    # L'identifiant fiable est code_interne, généré par nous et collé sur le support.
    # numero_serie NON UNIQUE volontairement : absent sur disque HS, dupliqué sur contrefaçons.
    code_interne: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # ex: SUP-2026-000178
    numero_serie: Mapped[str | None] = mapped_column(Text)
    modele: Mapped[str | None] = mapped_column(Text)
    constructeur: Mapped[str | None] = mapped_column(Text)
    capacite_octets: Mapped[int | None] = mapped_column(Integer)
    technologie: Mapped[str | None] = mapped_column(Text)
    interface: Mapped[str | None] = mapped_column(Text)
    smart_json: Mapped[str | None] = mapped_column(Text)  # dump SMART brut (JSON)
    sante: Mapped[str | None] = mapped_column(Text)
    hpa_detecte: Mapped[int | None] = mapped_column(Integer, default=0, server_default="0")
    dco_detecte: Mapped[int | None] = mapped_column(Integer, default=0, server_default="0")
    statut: Mapped[str] = mapped_column(
        Text, nullable=False, default="EN_ATTENTE", server_default="EN_ATTENTE"
    )
    destination: Mapped[str | None] = mapped_column(Text)
    cree_le: Mapped[str] = mapped_column(Text, nullable=False)
