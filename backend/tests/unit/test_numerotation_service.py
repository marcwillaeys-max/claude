from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.lot import Lot
from app.models.support import Support
from app.models.utilisateur import Utilisateur
from app.services import numerotation_service

ANNEE = datetime.now(timezone.utc).year


def _creer_utilisateur(db: Session) -> Utilisateur:
    utilisateur = Utilisateur(
        identifiant="u", nom_complet="U", mot_de_passe="x", role="TECHNICIEN", actif=1, cree_le="2026"
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def test_numero_client_initial_et_increment(db: Session) -> None:
    assert numerotation_service.prochain_numero_client(db) == "CLI-0001"
    utilisateur = _creer_utilisateur(db)
    db.add(
        Client(numero_client="CLI-0041", raison_sociale="X", cree_le="2026", cree_par=utilisateur.id)
    )
    db.flush()
    assert numerotation_service.prochain_numero_client(db) == "CLI-0042"


def test_numero_lot_par_annee(db: Session) -> None:
    assert numerotation_service.prochain_numero_lot(db) == f"LOT-{ANNEE}-0001"
    utilisateur = _creer_utilisateur(db)
    client = Client(numero_client="CLI-0001", raison_sociale="X", cree_le="2026", cree_par=utilisateur.id)
    db.add(client)
    db.flush()
    # Un lot d'une année passée n'influence pas la séquence de l'année courante.
    db.add(
        Lot(
            numero_lot="LOT-2020-0099",
            client_id=client.id,
            date_reception="2020-01-01",
            technicien_id=utilisateur.id,
            cree_le="2020",
        )
    )
    db.flush()
    assert numerotation_service.prochain_numero_lot(db) == f"LOT-{ANNEE}-0001"


def test_code_interne_support(db: Session) -> None:
    assert numerotation_service.prochain_code_interne(db) == f"SUP-{ANNEE}-000001"
    utilisateur = _creer_utilisateur(db)
    client = Client(numero_client="CLI-0001", raison_sociale="X", cree_le="2026", cree_par=utilisateur.id)
    db.add(client)
    db.flush()
    lot = Lot(
        numero_lot=f"LOT-{ANNEE}-0001",
        client_id=client.id,
        date_reception="2026-01-01",
        technicien_id=utilisateur.id,
        cree_le="2026",
    )
    db.add(lot)
    db.flush()
    db.add(Support(lot_id=lot.id, code_interne=f"SUP-{ANNEE}-000177", cree_le="2026"))
    db.flush()
    assert numerotation_service.prochain_code_interne(db) == f"SUP-{ANNEE}-000178"
