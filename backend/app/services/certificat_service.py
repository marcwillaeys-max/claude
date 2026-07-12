"""Génération et vérification des certificats d'effacement.

RÈGLE BLOQUANTE : un certificat n'est généré QUE si l'opération a
resultat = 'SUCCES' ET verification_ok = 1. Tout autre cas est refusé
avec un message explicite. Un support en ECHEC ou NON_EFFACABLE part en
destruction physique, jamais en certificat d'effacement.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import ConflitError, IntrouvableError, ValidationMetierError
from app.models.certificat import Certificat
from app.models.client import Client
from app.models.lot import Lot
from app.models.operation import Operation
from app.models.support import Support
from app.models.utilisateur import Utilisateur
from app.pdf import generator
from app.services import audit_service, signature_service


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prochain_numero(db: Session) -> str:
    annee = datetime.now(timezone.utc).year
    prefixe = f"CERT-{annee}-"
    dernier: str | None = db.execute(
        select(func.max(Certificat.numero_cert)).where(Certificat.numero_cert.like(f"{prefixe}%"))
    ).scalar_one_or_none()
    suivant = 1 if dernier is None else int(dernier.removeprefix(prefixe)) + 1
    return f"{prefixe}{suivant:06d}"


@dataclass
class ContexteCertificat:
    """Toutes les entités liées à une opération, chargées d'un coup."""

    operation: Operation
    support: Support
    lot: Lot
    client: Client
    technicien: Utilisateur


def _charger_contexte(db: Session, operation: Operation) -> ContexteCertificat:
    support = db.get(Support, operation.support_id)
    lot = db.get(Lot, support.lot_id)
    client = db.get(Client, lot.client_id)
    technicien = db.get(Utilisateur, operation.technicien_id)
    return ContexteCertificat(operation, support, lot, client, technicien)


def construire_donnees_certifiees(numero_cert: str, genere_le: str, ctx: ContexteCertificat) -> dict:
    """Données attestées par le certificat, reconstruites à l'identique lors de
    chaque vérification. Toute altération en base change le hash → signature invalide.
    """
    return {
        "numero_cert": numero_cert,
        "genere_le": genere_le,
        "client": {"numero": ctx.client.numero_client, "raison_sociale": ctx.client.raison_sociale},
        "lot": {"numero": ctx.lot.numero_lot, "date_reception": ctx.lot.date_reception},
        "support": {
            "code_interne": ctx.support.code_interne,
            "numero_serie": ctx.support.numero_serie,
            "modele": ctx.support.modele,
            "constructeur": ctx.support.constructeur,
            "capacite_octets": ctx.support.capacite_octets,
            "technologie": ctx.support.technologie,
        },
        "operation": {
            "methode": ctx.operation.methode,
            "norme_reference": ctx.operation.norme_reference,
            "nb_passes": ctx.operation.nb_passes,
            "debut": ctx.operation.debut,
            "fin": ctx.operation.fin,
            "duree_secondes": ctx.operation.duree_secondes,
            "resultat": ctx.operation.resultat,
            "verification_ok": ctx.operation.verification_ok,
            "verification_detail": ctx.operation.verification_detail,
            "log_sha256": ctx.operation.log_sha256,
            "outil_version": ctx.operation.outil_version,
        },
        "technicien": ctx.technicien.nom_complet,
    }


def _hash_donnees(donnees: dict) -> str:
    canonique = json.dumps(donnees, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonique.encode("utf-8")).hexdigest()


def verifier_eligibilite(operation: Operation, support: Support) -> None:
    """Lève ValidationMetierError si l'opération ne peut pas être certifiée."""
    if operation.resultat != "SUCCES":
        raise ValidationMetierError(
            f"Certificat refusé : le résultat de l'opération est {operation.resultat}, "
            "seul un effacement en SUCCES est certifiable"
        )
    if not operation.verification_faite or operation.verification_ok != 1:
        raise ValidationMetierError(
            "Certificat refusé : l'effacement n'a pas de vérification post-effacement positive. "
            "Un certificat atteste un résultat vérifié, pas une intention d'effacer."
        )
    # Spécification §1.6 : un support ECHEC ou NON_EFFACABLE (HPA/DCO non résolus)
    # ne génère JAMAIS de certificat d'effacement, même si un rapport dit SUCCES.
    if support.statut in ("ECHEC", "NON_EFFACABLE"):
        raise ValidationMetierError(
            f"Certificat refusé : le support {support.code_interne} est en statut {support.statut} "
            "→ circuit destruction physique, pas de certificat d'effacement"
        )


def generer(db: Session, acteur_id: int, operation_id: int) -> Certificat:
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise IntrouvableError(f"Opération {operation_id} introuvable")

    existant = db.execute(
        select(Certificat).where(Certificat.operation_id == operation_id)
    ).scalar_one_or_none()
    if existant is not None:
        raise ConflitError(
            f"Un certificat existe déjà pour cette opération : {existant.numero_cert}"
        )

    ctx = _charger_contexte(db, operation)
    verifier_eligibilite(operation, ctx.support)

    numero_cert = _prochain_numero(db)
    genere_le = _maintenant()
    token_verif = secrets.token_urlsafe(32)
    donnees = construire_donnees_certifiees(numero_cert, genere_le, ctx)
    contenu_sha256 = _hash_donnees(donnees)
    signature = signature_service.signer(contenu_sha256)

    repertoire = Path(get_settings().repertoire_certificats)
    repertoire.mkdir(parents=True, exist_ok=True)
    chemin_pdf = str(repertoire / f"{numero_cert}.pdf")

    certificat = Certificat(
        numero_cert=numero_cert,
        operation_id=operation_id,
        genere_le=genere_le,
        genere_par=acteur_id,
        contenu_sha256=contenu_sha256,
        signature=signature,
        cle_publique_id=signature_service.cle_publique_id(),
        chemin_pdf=chemin_pdf,
        token_verif=token_verif,
    )
    db.add(certificat)
    db.flush()

    generator.generer_pdf(chemin_pdf, donnees, certificat)

    audit_service.enregistrer(
        db,
        acteur_id,
        "GENERE_CERTIFICAT",
        "certificats",
        certificat.id,
        json.dumps(
            {"numero_cert": numero_cert, "operation_id": operation_id, "contenu_sha256": contenu_sha256},
            sort_keys=True,
        ),
    )
    return certificat


def obtenir(db: Session, certificat_id: int) -> Certificat:
    certificat = db.get(Certificat, certificat_id)
    if certificat is None:
        raise IntrouvableError(f"Certificat {certificat_id} introuvable")
    return certificat


def lister(db: Session) -> list[Certificat]:
    return list(db.execute(select(Certificat).order_by(Certificat.id)).scalars().all())


def regenerer_pdf(db: Session, certificat_id: int) -> Certificat:
    """Reproduit le PDF depuis les données signées (le fichier peut être perdu,
    les données non). Ne re-signe rien."""
    certificat = obtenir(db, certificat_id)
    operation = db.get(Operation, certificat.operation_id)
    ctx = _charger_contexte(db, operation)
    donnees = construire_donnees_certifiees(certificat.numero_cert, certificat.genere_le, ctx)
    generator.generer_pdf(certificat.chemin_pdf, donnees, certificat)
    return certificat


def masquer_numero_serie(numero_serie: str | None) -> str:
    if not numero_serie:
        return "non relevé"
    if len(numero_serie) <= 6:
        return numero_serie[0] + "*" * (len(numero_serie) - 1)
    return f"{numero_serie[:3]}{'*' * (len(numero_serie) - 6)}{numero_serie[-3:]}"


@dataclass
class ResultatVerificationPublique:
    """Ce que la page publique du QR a le droit de montrer. Rien de plus."""

    valide: bool
    raison: str | None = None
    numero_cert: str | None = None
    client: str | None = None
    date_operation: str | None = None
    genere_le: str | None = None
    numero_serie_masque: str | None = None
    methode: str | None = None
    resultat_verification: str | None = None


def verifier_token(db: Session, token: str) -> ResultatVerificationPublique:
    """Vérification publique : reconstruit les données certifiées depuis la base,
    recalcule le hash et vérifie la signature Ed25519 À CHAQUE APPEL.
    Une altération quelconque des données en base invalide le certificat.
    """
    certificat = db.execute(
        select(Certificat).where(Certificat.token_verif == token)
    ).scalar_one_or_none()
    if certificat is None:
        return ResultatVerificationPublique(valide=False, raison="Certificat introuvable")

    operation = db.get(Operation, certificat.operation_id)
    ctx = _charger_contexte(db, operation)
    donnees = construire_donnees_certifiees(certificat.numero_cert, certificat.genere_le, ctx)
    contenu_sha256 = _hash_donnees(donnees)

    coherent = contenu_sha256 == certificat.contenu_sha256
    signature_ok = signature_service.verifier(contenu_sha256, certificat.signature)
    if not (coherent and signature_ok):
        return ResultatVerificationPublique(
            valide=False,
            raison="Les données ne correspondent plus à la signature : certificat invalide",
            numero_cert=certificat.numero_cert,
        )

    return ResultatVerificationPublique(
        valide=True,
        numero_cert=certificat.numero_cert,
        client=ctx.client.raison_sociale,
        date_operation=operation.debut,
        genere_le=certificat.genere_le,
        numero_serie_masque=masquer_numero_serie(ctx.support.numero_serie),
        methode=operation.methode,
        resultat_verification="Effacement vérifié" if operation.verification_ok == 1 else "Non vérifié",
    )
