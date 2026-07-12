from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.audit import Audit
from app.services import audit_service
from app.services.audit_service import HASH_GENESIS, calculer_hash


def test_premiere_ligne_genesis(db: Session) -> None:
    ligne = audit_service.enregistrer(db, None, "TEST", "clients", 1, '{"a":1}')
    assert ligne.hash_precedent == HASH_GENESIS
    assert ligne.hash_courant == calculer_hash(
        ligne.horodatage, None, "TEST", "clients", 1, '{"a":1}', HASH_GENESIS
    )


def test_chainage_des_lignes(db: Session) -> None:
    l1 = audit_service.enregistrer(db, None, "A1", "clients", 1)
    l2 = audit_service.enregistrer(db, None, "A2", "lots", 2, '{"x":true}')
    l3 = audit_service.enregistrer(db, None, "A3", "supports", None)
    assert l2.hash_precedent == l1.hash_courant
    assert l3.hash_precedent == l2.hash_courant


def test_verifier_chaine_valide(db: Session) -> None:
    for i in range(5):
        audit_service.enregistrer(db, None, f"ACTION_{i}", "clients", i)
    resultat = audit_service.verifier_chaine(db)
    assert resultat.valide
    assert resultat.nb_lignes == 5
    assert resultat.ruptures == []


def test_verifier_chaine_vide(db: Session) -> None:
    resultat = audit_service.verifier_chaine(db)
    assert resultat.valide
    assert resultat.nb_lignes == 0


def test_detection_modification_contenu(db: Session) -> None:
    audit_service.enregistrer(db, None, "A1", "clients", 1)
    cible = audit_service.enregistrer(db, None, "A2", "clients", 2, '{"avant":1}')
    audit_service.enregistrer(db, None, "A3", "clients", 3)

    # Altération directe en base, comme le ferait un attaquant avec un éditeur SQLite.
    db.execute(update(Audit).where(Audit.id == cible.id).values(details='{"falsifie":1}'))
    db.expire_all()

    resultat = audit_service.verifier_chaine(db)
    assert not resultat.valide
    assert any(r.audit_id == cible.id and "modifié" in r.raison for r in resultat.ruptures)


def test_detection_suppression_ligne(db: Session) -> None:
    audit_service.enregistrer(db, None, "A1", "clients", 1)
    milieu = audit_service.enregistrer(db, None, "A2", "clients", 2)
    suivante = audit_service.enregistrer(db, None, "A3", "clients", 3)

    db.execute(delete(Audit).where(Audit.id == milieu.id))
    db.expire_all()

    resultat = audit_service.verifier_chaine(db)
    assert not resultat.valide
    assert any(r.audit_id == suivante.id for r in resultat.ruptures)


def test_detection_reecriture_coherente_sans_recalcul_aval(db: Session) -> None:
    """Un attaquant qui réécrit une ligne ET son hash_courant casse le chaînon suivant."""
    cible = audit_service.enregistrer(db, None, "A1", "clients", 1)
    audit_service.enregistrer(db, None, "A2", "clients", 2)

    faux_hash = calculer_hash(cible.horodatage, None, "A1_FALSIFIE", "clients", 1, None, cible.hash_precedent)
    db.execute(
        update(Audit).where(Audit.id == cible.id).values(action="A1_FALSIFIE", hash_courant=faux_hash)
    )
    db.expire_all()

    resultat = audit_service.verifier_chaine(db)
    assert not resultat.valide


def test_lister_ordre_decroissant(db: Session) -> None:
    for i in range(3):
        audit_service.enregistrer(db, None, f"ACTION_{i}", "clients", i)
    lignes = audit_service.lister(db, limite=2)
    assert len(lignes) == 2
    assert lignes[0].action == "ACTION_2"
