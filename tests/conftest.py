# tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sports_tracker.db.base import Base
from sports_tracker.settings import settings

# These imports assume your FastAPI app instance is named `app` in `src/sports_tracker/main.py`
# and your DB session dependency is `get_db` in `src/sports_tracker/db/session.py`.
# You may need to adjust these paths to match your project structure.
from sports_tracker.main import app
from sports_tracker.db.session import get_db


@pytest.fixture(scope="session")
def db_engine():
    """
    Fixture for a test database engine.
    It creates all tables at the start of the test session and drops them at the end.
    """
    engine = create_engine(str(settings.settings.DATABASE_URL))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Fixture for a transactional database session for each test.
    It starts a transaction, yields a session, and rolls back the transaction after the test.
    This ensures test isolation.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Get a TestClient instance that uses the transactional database session.
    This fixture overrides the `get_db` dependency for the duration of a test.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db]