from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

# Doit être défini AVANT tout import de l'application : le moteur global
# est créé à l'import de app.database, et les settings sont mis en cache.
_REPERTOIRE_TEST = tempfile.mkdtemp()
os.environ.setdefault("ORALYSE_DATABASE_URL", f"sqlite:///{_REPERTOIRE_TEST}/oralyse-test-global.db")
os.environ.setdefault("ORALYSE_CLE_PRIVEE_CHEMIN", f"{_REPERTOIRE_TEST}/cles/ed25519_prive.pem")
os.environ.setdefault("ORALYSE_REPERTOIRE_CERTIFICATS", f"{_REPERTOIRE_TEST}/certificats")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import _activer_foreign_keys, get_db
from app.main import app
from app.models import Base
from app.services import utilisateur_service


@pytest.fixture
def sessionmaker_test() -> Iterator[sessionmaker]:
    """Base SQLite en mémoire, isolée par test, clés étrangères actives."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _activer_foreign_keys)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(sessionmaker_test: sessionmaker) -> Iterator[Session]:
    session = sessionmaker_test()
    yield session
    session.close()


@pytest.fixture
def client(sessionmaker_test: sessionmaker) -> Iterator[TestClient]:
    def _get_db_test() -> Iterator[Session]:
        session = sessionmaker_test()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db_test
    yield TestClient(app)
    app.dependency_overrides.clear()


def _creer_utilisateur(sessionmaker_test: sessionmaker, identifiant: str, role: str) -> None:
    session = sessionmaker_test()
    try:
        utilisateur_service.creer(session, None, identifiant, f"Test {role}", "motdepasse-test", role)
        session.commit()
    finally:
        session.close()


def _jeton(client: TestClient, identifiant: str) -> str:
    reponse = client.post(
        "/api/v1/auth/login", data={"username": identifiant, "password": "motdepasse-test"}
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["access_token"]


@pytest.fixture
def entetes_admin(client: TestClient, sessionmaker_test: sessionmaker) -> dict[str, str]:
    _creer_utilisateur(sessionmaker_test, "admin-test", "ADMINISTRATEUR")
    return {"Authorization": f"Bearer {_jeton(client, 'admin-test')}"}


@pytest.fixture
def entetes_responsable(client: TestClient, sessionmaker_test: sessionmaker) -> dict[str, str]:
    _creer_utilisateur(sessionmaker_test, "resp-test", "RESPONSABLE")
    return {"Authorization": f"Bearer {_jeton(client, 'resp-test')}"}


@pytest.fixture
def entetes_technicien(client: TestClient, sessionmaker_test: sessionmaker) -> dict[str, str]:
    _creer_utilisateur(sessionmaker_test, "tech-test", "TECHNICIEN")
    return {"Authorization": f"Bearer {_jeton(client, 'tech-test')}"}
