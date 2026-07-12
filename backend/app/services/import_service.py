"""Import des rapports produits par la station d'effacement.

Règles non négociables :
- validation stricte : un rapport malformé est REJETÉ, jamais importé partiellement ;
- le support doit déjà exister (rattachement par code_interne) — on ne crée
  jamais un support à l'aveugle ;
- intégrité : SHA-256(log_brut) doit égaler log_sha256 annoncé, sinon REJET ;
- idempotence : réimporter le même rapport ne crée pas de doublon ;
- chaque import (et chaque rejet pour hash invalide) est journalisé dans l'audit.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import IntrouvableError, ValidationMetierError
from app.models.operation import Operation
from app.models.support import Support
from app.schemas.rapport import RapportStation
from app.services import audit_service


@dataclass
class ResultatImport:
    operation: Operation
    deja_importe: bool
    statut_support: str


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def parser_rapport(contenu: bytes) -> RapportStation:
    """Décode et valide un rapport. Toute anomalie de forme → ValidationMetierError."""
    try:
        brut = json.loads(contenu.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationMetierError(f"Rapport illisible : JSON invalide ({exc})") from exc
    try:
        return RapportStation.model_validate(brut)
    except ValidationError as exc:
        problemes = "; ".join(
            f"{'.'.join(str(p) for p in erreur['loc'])}: {erreur['msg']}" for erreur in exc.errors()
        )
        raise ValidationMetierError(f"Rapport malformé, import refusé : {problemes}") from exc


def determiner_statut_support(rapport: RapportStation) -> str:
    """Transition de statut du support, règles strictes de la spécification.

    HPA/DCO non résolus priment sur tout : des zones du disque ont pu échapper
    à l'effacement → NON_EFFACABLE, circuit destruction physique.
    Une vérification faite mais négative, ou une opération INTERROMPUE,
    est traitée comme un ECHEC : jamais de statut « effacé » sans preuve.
    """
    if rapport.support.hpa_detecte or rapport.support.dco_detecte:
        return "NON_EFFACABLE"
    if rapport.operation.resultat == "SUCCES":
        if not rapport.verification.faite:
            return "EFFACE_NON_VERIFIE"
        if rapport.verification.ok:
            return "EFFACE_VERIFIE"
        return "ECHEC"
    return "ECHEC"


def _enrichir_support(support: Support, rapport: RapportStation) -> None:
    """Reporte sur le support les constats matériels de la station.

    hpa/dco/smart/sante sont toujours mis à jour (constat le plus récent) ;
    les champs descriptifs ne sont remplis que s'ils étaient vides — la saisie
    faite à la réception n'est jamais écrasée silencieusement.
    """
    support.hpa_detecte = 1 if rapport.support.hpa_detecte else 0
    support.dco_detecte = 1 if rapport.support.dco_detecte else 0
    if rapport.support.smart is not None:
        support.smart_json = json.dumps(rapport.support.smart, sort_keys=True, ensure_ascii=False)
    if rapport.support.sante is not None:
        support.sante = rapport.support.sante
    for champ in ("numero_serie", "modele", "constructeur", "capacite_octets", "technologie", "interface"):
        if getattr(support, champ) is None and getattr(rapport.support, champ) is not None:
            setattr(support, champ, getattr(rapport.support, champ))


def importer_rapport(db: Session, acteur_id: int, contenu: bytes) -> ResultatImport:
    rapport = parser_rapport(contenu)

    support = db.execute(
        select(Support).where(Support.code_interne == rapport.support.code_interne)
    ).scalar_one_or_none()
    if support is None:
        raise IntrouvableError(
            f"Support {rapport.support.code_interne} inconnu : créez le support dans son lot "
            "avant d'importer son rapport (aucune création à l'aveugle)"
        )

    hash_calcule = hashlib.sha256(rapport.log_brut.encode("utf-8")).hexdigest()
    if hash_calcule != rapport.log_sha256.lower():
        # Pas d'écriture d'audit ici : l'exception fait annuler la transaction,
        # rien ne doit être persisté d'un rapport corrompu.
        raise ValidationMetierError(
            "Intégrité du rapport invalide : le SHA-256 du log ne correspond pas "
            f"(annoncé {rapport.log_sha256}, calculé {hash_calcule}). Import refusé."
        )

    # Idempotence : même support + même hash de log = même rapport.
    existante = db.execute(
        select(Operation).where(
            Operation.support_id == support.id, Operation.log_sha256 == hash_calcule
        )
    ).scalar_one_or_none()
    if existante is not None:
        return ResultatImport(operation=existante, deja_importe=True, statut_support=support.statut)

    statut = determiner_statut_support(rapport)
    operation = Operation(
        support_id=support.id,
        technicien_id=acteur_id,
        station=rapport.station,
        methode=rapport.operation.methode,
        norme_reference=rapport.operation.norme_reference,
        nb_passes=rapport.operation.nb_passes,
        debut=rapport.operation.debut,
        fin=rapport.operation.fin,
        duree_secondes=rapport.operation.duree_secondes,
        resultat=rapport.operation.resultat,
        verification_faite=1 if rapport.verification.faite else 0,
        verification_ok=(None if rapport.verification.ok is None else (1 if rapport.verification.ok else 0)),
        verification_detail=json.dumps(
            {
                "secteurs_testes": rapport.verification.secteurs_testes,
                "zones": rapport.verification.zones,
                "anomalies": rapport.verification.anomalies,
            },
            sort_keys=True,
            ensure_ascii=False,
        ),
        log_brut=rapport.log_brut,
        log_sha256=hash_calcule,
        outil_version=f"{rapport.outil.nom} {rapport.outil.version}",
        importe_le=_maintenant(),
    )
    db.add(operation)

    ancien_statut = support.statut
    support.statut = statut
    _enrichir_support(support, rapport)
    db.flush()

    audit_service.enregistrer(
        db,
        acteur_id,
        "IMPORT_OPERATION",
        "operations",
        operation.id,
        json.dumps(
            {
                "code_interne": support.code_interne,
                "log_sha256": hash_calcule,
                "resultat": rapport.operation.resultat,
                "statut_avant": ancien_statut,
                "statut_apres": statut,
            },
            sort_keys=True,
        ),
    )
    return ResultatImport(operation=operation, deja_importe=False, statut_support=statut)
