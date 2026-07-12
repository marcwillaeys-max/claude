"""Point d'entrée FastAPI d'Oralyse Wipe.

Ce logiciel ne touche JAMAIS un périphérique de stockage : il gère des
données et importe des rapports produits par la station d'effacement.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import audit, auth, clients, lots, operations, supports
from app.config import get_settings
from app.core.exceptions import (
    AuthentificationError,
    AutorisationError,
    ConflitError,
    ErreurMetier,
    IntrouvableError,
    ValidationMetierError,
)
from app.database import SessionLocal
from app.services import utilisateur_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Premier démarrage : crée l'administrateur initial si la base est vide.
    settings = get_settings()
    db = SessionLocal()
    try:
        cree = utilisateur_service.creer_admin_initial(
            db,
            settings.admin_initial_identifiant,
            settings.admin_initial_nom,
            settings.admin_initial_mot_de_passe,
        )
        db.commit()
        if cree is not None and settings.admin_initial_mot_de_passe == "changez-moi":
            import logging

            logging.getLogger("oralyse").warning(
                "Administrateur initial créé avec le mot de passe PAR DÉFAUT. "
                "Définissez ORALYSE_ADMIN_INITIAL_MOT_DE_PASSE avant la mise en production."
            )
    finally:
        db.close()
    yield


def creer_application() -> FastAPI:
    app = FastAPI(
        title="Oralyse Wipe",
        description="Traçabilité et certification d'effacement sécurisé — logiciel métier (aucun accès disque)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(auth.router)
    app.include_router(clients.router)
    app.include_router(lots.router)
    app.include_router(supports.router)
    app.include_router(operations.router)
    app.include_router(audit.router)

    _STATUTS_HTTP: list[tuple[type[ErreurMetier], int]] = [
        (IntrouvableError, 404),
        (ConflitError, 409),
        (ValidationMetierError, 422),
        (AuthentificationError, 401),
        (AutorisationError, 403),
    ]

    for classe, statut in _STATUTS_HTTP:

        def _handler(_request: Request, exc: ErreurMetier, _statut: int = statut) -> JSONResponse:
            entetes = {"WWW-Authenticate": "Bearer"} if _statut == 401 else None
            return JSONResponse(status_code=_statut, content={"detail": exc.message}, headers=entetes)

        app.add_exception_handler(classe, _handler)  # type: ignore[arg-type]

    return app


app = creer_application()
