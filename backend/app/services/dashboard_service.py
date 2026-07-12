"""Agrégations pour le tableau de bord — tout en SQL, rien en Python
sur des milliers de lignes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.operation import Operation
from app.models.support import Support

STATUTS_EFFACES = ("EFFACE_VERIFIE", "EFFACE_NON_VERIFIE")
STATUTS_A_TRAITER = ("ECHEC", "NON_EFFACABLE")


def _debut_periode(jours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=jours)).isoformat()


@dataclass
class Indicateurs:
    supports_traites_jour: int
    supports_traites_semaine: int
    supports_traites_mois: int
    capacite_effacee_octets: int
    duree_moyenne_secondes: float | None
    taux_reussite: float | None
    nb_operations: int
    repartition_technologie: dict[str, int]
    repartition_statut: dict[str, int]


def indicateurs(db: Session) -> Indicateurs:
    def _traites_depuis(jours: int) -> int:
        # Un support ne compte comme « effacé » que si son statut FINAL l'atteste :
        # un rapport SUCCES sur un support NON_EFFACABLE (HPA/DCO) ne compte pas.
        return int(
            db.execute(
                select(func.count(func.distinct(Operation.support_id)))
                .join(Support, Operation.support_id == Support.id)
                .where(
                    Operation.resultat == "SUCCES",
                    Operation.importe_le >= _debut_periode(jours),
                    Support.statut.in_(STATUTS_EFFACES),
                )
            ).scalar_one()
        )

    capacite = db.execute(
        select(func.coalesce(func.sum(Support.capacite_octets), 0)).where(
            Support.statut.in_(STATUTS_EFFACES)
        )
    ).scalar_one()

    duree_moyenne = db.execute(
        select(func.avg(Operation.duree_secondes)).where(Operation.resultat == "SUCCES")
    ).scalar_one()

    nb_operations, nb_succes = db.execute(
        select(
            func.count(Operation.id),
            func.coalesce(func.sum(case((Operation.resultat == "SUCCES", 1), else_=0)), 0),
        )
    ).one()

    technologies = db.execute(
        select(func.coalesce(Support.technologie, "INCONNU"), func.count(Support.id)).group_by(
            Support.technologie
        )
    ).all()

    statuts = db.execute(select(Support.statut, func.count(Support.id)).group_by(Support.statut)).all()

    return Indicateurs(
        supports_traites_jour=_traites_depuis(1),
        supports_traites_semaine=_traites_depuis(7),
        supports_traites_mois=_traites_depuis(30),
        capacite_effacee_octets=int(capacite),
        duree_moyenne_secondes=float(duree_moyenne) if duree_moyenne is not None else None,
        taux_reussite=(nb_succes / nb_operations) if nb_operations else None,
        nb_operations=int(nb_operations),
        repartition_technologie={tech: int(nb) for tech, nb in technologies},
        repartition_statut={statut: int(nb) for statut, nb in statuts},
    )


def supports_a_traiter(db: Session) -> list[Support]:
    """Les ECHEC et NON_EFFACABLE — visibles, jamais cachés (spécification LOT 4)."""
    return list(
        db.execute(
            select(Support).where(Support.statut.in_(STATUTS_A_TRAITER)).order_by(Support.id.desc())
        )
        .scalars()
        .all()
    )
