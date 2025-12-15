# tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sports_tracker.main import create_app
from sports_tracker.db.base import Base
import sports_tracker.db.session as db_session_module


@pytest.fixture(scope="session")
def engine():
    # SQLite in-memory para tests. Rápido y sin dependencias externas.
    engine_ = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    return engine_


@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _patch_db_session(engine, TestingSessionLocal):
    """
    Parchea el módulo sports_tracker.session para que use SQLite en tests.
    Esto evita que intente conectar a Postgres por settings.DATABASE_URL.
    """
    db_session_module.engine = engine
    db_session_module.SessionLocal = TestingSessionLocal
    yield


@pytest.fixture(autouse=True)
def _create_tables(engine):
    # Crea y destruye tablas por test: simple y fiable.
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(TestingSessionLocal):
    app = create_app()

    # Override del get_db para usar la SessionLocal parcheada
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as c:
        yield c
