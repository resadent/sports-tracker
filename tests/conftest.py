# tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.sports_tracker.main import create_app
from src.sports_tracker.db.base import Base
import src.sports_tracker.db.session as db_session_module


@pytest.fixture(scope="session")
def engine():
    # OJO: sqlite in-memory se reinicia por conexión, por eso usamos pool StaticPool
    from sqlalchemy.pool import StaticPool

    engine_ = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine_


@pytest.fixture(scope="session", autouse=True)
def create_schema(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(engine) -> Session:
    """
    Transacción por test: empieza, corre, y rollback al final.
    Aísla completamente los tests entre sí.
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as c:
        yield c
