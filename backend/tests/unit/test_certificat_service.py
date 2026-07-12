from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import ConflitError, IntrouvableError, ValidationMetierError
from app.models.audit import Audit
from app.models.operation import Operation
from app.models.support import Support
from app.services import (
    certificat_service,
    client_service,
    import_service,
    lot_service,
    support_service,
    utilisateur_service,
)
from tests.fixtures.rapports import construire_rapport, encoder

ANNEE = datetime.now(timezone.utc).year


@pytest.fixture
def contexte(db: Session) -> tuple[int, Support]:
    technicien = utilisateur_service.creer(db, None, "tech", "Jean Dupont", "motdepasse-test", "TECHNICIEN")
    client = client_service.creer(db, technicien.id, {"raison_sociale": "Hopital Nord"})
    lot = lot_service.creer(db, technicien.id, client.id, "2026-07-12")
    support = support_service.creer(db, technicien.id, lot.id, {})
    return technicien.id, support


def _importer(db: Session, technicien_id: int, support: Support, **surcharges) -> Operation:
    rapport = construire_rapport(support.code_interne, **surcharges)
    return import_service.importer_rapport(db, technicien_id, encoder(rapport)).operation


def test_generation_nominale(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(db, technicien_id, support)

    certificat = certificat_service.generer(db, technicien_id, operation.id)

    assert re.fullmatch(rf"CERT-{ANNEE}-\d{{6}}", certificat.numero_cert)
    assert certificat.numero_cert.endswith("000001")
    assert len(certificat.token_verif) >= 32
    assert certificat.cle_publique_id
    # Le PDF existe et est bien un PDF.
    pdf = Path(certificat.chemin_pdf)
    assert pdf.exists()
    assert pdf.read_bytes()[:5] == b"%PDF-"
    assert pdf.stat().st_size > 2000
    # La génération est auditée.
    audits = db.execute(select(Audit).where(Audit.action == "GENERE_CERTIFICAT")).scalars().all()
    assert len(audits) == 1


def test_refus_operation_en_echec(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(
        db,
        technicien_id,
        support,
        operation={"resultat": "ECHEC"},
        verification={"faite": False, "ok": None},
    )
    with pytest.raises(ValidationMetierError, match="ECHEC"):
        certificat_service.generer(db, technicien_id, operation.id)


def test_refus_operation_interrompue(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(
        db,
        technicien_id,
        support,
        operation={"resultat": "INTERROMPU"},
        verification={"faite": False, "ok": None},
    )
    with pytest.raises(ValidationMetierError, match="INTERROMPU"):
        certificat_service.generer(db, technicien_id, operation.id)


def test_refus_sans_verification(db: Session, contexte: tuple[int, Support]) -> None:
    """SUCCES mais vérification non faite : on n'atteste pas une intention."""
    technicien_id, support = contexte
    operation = _importer(db, technicien_id, support, verification={"faite": False, "ok": None})
    with pytest.raises(ValidationMetierError, match="vérification"):
        certificat_service.generer(db, technicien_id, operation.id)


def test_refus_verification_negative(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(
        db,
        technicien_id,
        support,
        verification={"faite": True, "ok": False, "anomalies": ["secteur non vierge"]},
    )
    with pytest.raises(ValidationMetierError, match="vérification"):
        certificat_service.generer(db, technicien_id, operation.id)


def test_refus_operation_inexistante(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, _ = contexte
    with pytest.raises(IntrouvableError):
        certificat_service.generer(db, technicien_id, 999)


def test_refus_doublon(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(db, technicien_id, support)
    premier = certificat_service.generer(db, technicien_id, operation.id)
    with pytest.raises(ConflitError, match=premier.numero_cert):
        certificat_service.generer(db, technicien_id, operation.id)


def test_verifier_token_valide(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(db, technicien_id, support)
    certificat = certificat_service.generer(db, technicien_id, operation.id)

    resultat = certificat_service.verifier_token(db, certificat.token_verif)

    assert resultat.valide
    assert resultat.client == "Hopital Nord"
    assert resultat.numero_cert == certificat.numero_cert
    # Numéro de série partiellement masqué : jamais la valeur complète.
    assert resultat.numero_serie_masque != "WD-WCC4E1234567"
    assert resultat.numero_serie_masque.startswith("WD-")
    assert resultat.numero_serie_masque.endswith("567")
    assert "*" in resultat.numero_serie_masque


def test_verifier_token_inconnu(db: Session) -> None:
    resultat = certificat_service.verifier_token(db, "token-qui-n-existe-pas")
    assert not resultat.valide
    assert resultat.raison == "Certificat introuvable"


def test_alteration_des_donnees_invalide_le_certificat(
    db: Session, contexte: tuple[int, Support]
) -> None:
    technicien_id, support = contexte
    operation = _importer(db, technicien_id, support)
    certificat = certificat_service.generer(db, technicien_id, operation.id)
    assert certificat_service.verifier_token(db, certificat.token_verif).valide

    # Falsification a posteriori d'une donnée certifiée, directement en base.
    db.execute(
        update(Operation).where(Operation.id == operation.id).values(methode="methode_falsifiee")
    )
    db.expire_all()

    resultat = certificat_service.verifier_token(db, certificat.token_verif)
    assert not resultat.valide
    assert "invalide" in (resultat.raison or "")


def test_regeneration_pdf_depuis_les_donnees(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    operation = _importer(db, technicien_id, support)
    certificat = certificat_service.generer(db, technicien_id, operation.id)
    Path(certificat.chemin_pdf).unlink()  # le fichier peut être perdu, les données non

    certificat_service.regenerer_pdf(db, certificat.id)

    assert Path(certificat.chemin_pdf).read_bytes()[:5] == b"%PDF-"


def test_masquage_numero_serie() -> None:
    assert certificat_service.masquer_numero_serie(None) == "non relevé"
    assert certificat_service.masquer_numero_serie("") == "non relevé"
    assert certificat_service.masquer_numero_serie("ABC123") == "A*****"
    masque = certificat_service.masquer_numero_serie("WD-WCC4E1234567")
    assert masque == "WD-" + "*" * 9 + "567"
