# tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from src.sports_tracker.main import create_app
from src.sports_tracker.db.base import Base
# import src.sports_tracker.db.session as db_session_module
import sports_tracker.db.session as db_session_module

@pytest.fixture(scope="session")
def engine():
    # SQLite in-memory persistente durante la sesión de tests
    # (misma conexión gracias a StaticPool)
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
    Aislamiento robusto:
    - Transacción externa por test (rollback al final)
    - SAVEPOINT (begin_nested) para que los commit() del código no persistan
    """
    connection = engine.connect()
    outer_tx = connection.begin()

    TestingSessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    db: Session = TestingSessionLocal()

    # SAVEPOINT inicial
    db.begin_nested()

    # Si el código hace commit(), SQLAlchemy cierra el SAVEPOINT.
    # Este listener lo reabre para que el test siga pudiendo commitear sin “persistir”.
    @event.listens_for(db, "after_transaction_end")
    def _restart_savepoint(session, transaction):
        # Cuando termina el nested transaction, lo recreamos
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    try:
        yield db
    finally:
        db.close()
        outer_tx.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as c:
        yield c
