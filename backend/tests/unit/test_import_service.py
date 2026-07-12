from __future__ import annotations

import hashlib
import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import IntrouvableError, ValidationMetierError
from app.models.audit import Audit
from app.models.operation import Operation
from app.models.support import Support
from app.services import client_service, import_service, lot_service, support_service, utilisateur_service
from tests.fixtures.rapports import construire_rapport, encoder


@pytest.fixture
def contexte(db: Session) -> tuple[int, Support]:
    """Un technicien, un client, un lot et un support EN_ATTENTE."""
    technicien = utilisateur_service.creer(db, None, "tech", "Tech", "motdepasse-test", "TECHNICIEN")
    client = client_service.creer(db, technicien.id, {"raison_sociale": "ACME"})
    lot = lot_service.creer(db, technicien.id, client.id, "2026-07-12")
    support = support_service.creer(db, technicien.id, lot.id, {})
    return technicien.id, support


def test_import_nominal(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    rapport = construire_rapport(support.code_interne)

    resultat = import_service.importer_rapport(db, technicien_id, encoder(rapport))

    assert not resultat.deja_importe
    assert resultat.statut_support == "EFFACE_VERIFIE"
    operation = resultat.operation
    assert operation.support_id == support.id
    assert operation.methode == "nwipe_zero_fill"
    assert operation.resultat == "SUCCES"
    assert operation.verification_faite == 1
    assert operation.verification_ok == 1
    assert operation.outil_version == "nwipe 0.36"
    assert operation.log_sha256 == rapport["log_sha256"]
    # Le support est passé au bon statut et enrichi des constats de la station.
    assert support.statut == "EFFACE_VERIFIE"
    assert support.numero_serie == "WD-WCC4E1234567"
    assert support.smart_json is not None
    # L'import est audité.
    audits = db.execute(select(Audit).where(Audit.action == "IMPORT_OPERATION")).scalars().all()
    assert len(audits) == 1
    assert json.loads(audits[0].details)["statut_apres"] == "EFFACE_VERIFIE"


def test_enrichissement_n_ecrase_pas_la_saisie(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    support_service.modifier(db, technicien_id, support.id, {"numero_serie": "SAISI-A-LA-MAIN"})
    import_service.importer_rapport(db, technicien_id, encoder(construire_rapport(support.code_interne)))
    assert support.numero_serie == "SAISI-A-LA-MAIN"


def test_hash_corrompu_rejete(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    rapport = construire_rapport(support.code_interne, log_sha256="0" * 64)

    with pytest.raises(ValidationMetierError, match="SHA-256"):
        import_service.importer_rapport(db, technicien_id, encoder(rapport))

    # Rien n'a été importé, le support n'a pas bougé.
    assert db.execute(select(Operation)).scalars().all() == []
    assert support.statut == "EN_ATTENTE"


def test_json_illisible_rejete(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, _ = contexte
    with pytest.raises(ValidationMetierError, match="JSON invalide"):
        import_service.importer_rapport(db, technicien_id, b"pas du json {")


@pytest.mark.parametrize(
    "casse",
    [
        {"format_version": "2.0"},  # version de format inconnue
        {"operation": {"resultat": "PEUT_ETRE"}},  # résultat hors énumération
        {"log_sha256": "pas-un-hash"},  # hash mal formé
        {"champ_inconnu": True},  # champ non prévu au contrat → refus strict
        {"verification": {"faite": True, "ok": None}},  # incohérence faite/ok
    ],
)
def test_rapport_malforme_rejete(db: Session, contexte: tuple[int, Support], casse: dict) -> None:
    technicien_id, support = contexte
    rapport = construire_rapport(support.code_interne, **casse)
    with pytest.raises(ValidationMetierError, match="malformé"):
        import_service.importer_rapport(db, technicien_id, encoder(rapport))
    assert db.execute(select(Operation)).scalars().all() == []


def test_champ_obligatoire_manquant_rejete(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    rapport = construire_rapport(support.code_interne)
    del rapport["operation"]["methode"]
    with pytest.raises(ValidationMetierError, match="malformé"):
        import_service.importer_rapport(db, technicien_id, encoder(rapport))


def test_support_inexistant_erreur_explicite(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, _ = contexte
    rapport = construire_rapport("SUP-2026-999999")
    with pytest.raises(IntrouvableError, match="SUP-2026-999999"):
        import_service.importer_rapport(db, technicien_id, encoder(rapport))
    assert db.execute(select(Operation)).scalars().all() == []


def test_double_import_idempotent(db: Session, contexte: tuple[int, Support]) -> None:
    technicien_id, support = contexte
    contenu = encoder(construire_rapport(support.code_interne))

    premier = import_service.importer_rapport(db, technicien_id, contenu)
    second = import_service.importer_rapport(db, technicien_id, contenu)

    assert not premier.deja_importe
    assert second.deja_importe
    assert second.operation.id == premier.operation.id
    assert len(db.execute(select(Operation)).scalars().all()) == 1


def test_nouvelle_tentative_apres_echec_conserve_l_historique(
    db: Session, contexte: tuple[int, Support]
) -> None:
    technicien_id, support = contexte
    echec = construire_rapport(
        support.code_interne,
        operation={"resultat": "ECHEC"},
        verification={"faite": False, "ok": None},
        log_brut="tentative 1 : erreur I/O\n",
        log_sha256=__import__("hashlib").sha256(b"tentative 1 : erreur I/O\n").hexdigest(),
    )
    import_service.importer_rapport(db, technicien_id, encoder(echec))
    assert support.statut == "ECHEC"

    succes = construire_rapport(support.code_interne)
    import_service.importer_rapport(db, technicien_id, encoder(succes))
    assert support.statut == "EFFACE_VERIFIE"
    # Les DEUX tentatives restent en base.
    assert len(db.execute(select(Operation)).scalars().all()) == 2


@pytest.mark.parametrize(
    ("surcharges", "statut_attendu"),
    [
        # SUCCES + vérification OK → EFFACE_VERIFIE
        ({}, "EFFACE_VERIFIE"),
        # SUCCES sans vérification → EFFACE_NON_VERIFIE
        ({"verification": {"faite": False, "ok": None}}, "EFFACE_NON_VERIFIE"),
        # ECHEC → ECHEC
        (
            {"operation": {"resultat": "ECHEC"}, "verification": {"faite": False, "ok": None}},
            "ECHEC",
        ),
        # INTERROMPU : pas de preuve d'effacement → ECHEC
        (
            {"operation": {"resultat": "INTERROMPU"}, "verification": {"faite": False, "ok": None}},
            "ECHEC",
        ),
        # SUCCES annoncé mais vérification NÉGATIVE → ECHEC, jamais « effacé »
        ({"verification": {"faite": True, "ok": False, "anomalies": ["secteur 42 non vierge"]}}, "ECHEC"),
        # HPA non résolu → NON_EFFACABLE, même si l'effacement dit SUCCES
        ({"support": {"hpa_detecte": True}}, "NON_EFFACABLE"),
        # DCO non résolu → NON_EFFACABLE
        ({"support": {"dco_detecte": True}}, "NON_EFFACABLE"),
    ],
)
def test_transitions_de_statut(
    db: Session, contexte: tuple[int, Support], surcharges: dict, statut_attendu: str
) -> None:
    technicien_id, support = contexte
    rapport = construire_rapport(support.code_interne, **surcharges)
    resultat = import_service.importer_rapport(db, technicien_id, encoder(rapport))
    assert resultat.statut_support == statut_attendu
    assert support.statut == statut_attendu
