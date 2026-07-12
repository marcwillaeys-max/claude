from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Certificat(Base):
    """Certificat d'effacement sécurisé.

    UNIQUE sur operation_id : un certificat par opération, pas de doublon.
    Un certificat ne peut être généré que si operations.resultat = 'SUCCES'
    ET verification_ok = 1 → contrainte applicative (certificat_service), testée.
    La signature porte sur le SHA-256 des données certifiées, pas sur le PDF :
    le PDF peut être régénéré, les données non.
    """

    __tablename__ = "certificats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_cert: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # ex: CERT-2026-000341
    operation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("operations.id"), nullable=False, unique=True
    )
    genere_le: Mapped[str] = mapped_column(Text, nullable=False)
    genere_par: Mapped[int] = mapped_column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    contenu_sha256: Mapped[str] = mapped_column(Text, nullable=False)  # hash des données certifiées
    signature: Mapped[str] = mapped_column(Text, nullable=False)  # Ed25519, base64
    cle_publique_id: Mapped[str] = mapped_column(Text, nullable=False)  # quelle clé a signé
    chemin_pdf: Mapped[str] = mapped_column(Text, nullable=False)
    token_verif: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # cible du QR code
