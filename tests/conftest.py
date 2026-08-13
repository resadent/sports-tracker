# tests/conftest.py
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sports_tracker.db.base import Base
from sports_tracker.main import app
from sports_tracker.db.session import get_db

# Tests run against an isolated SQLite database by default, so they work without
# Docker/Postgres and can never wipe a real dev database. Point TEST_DATABASE_URL
# at a Postgres instance to run against Postgres instead (e.g. in CI).
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

_engine_kwargs: dict = {}
if TEST_DATABASE_URL == "sqlite://":
    # In-memory SQLite: share one connection for the whole session and allow the
    # TestClient's worker thread to use it.
    _engine_kwargs = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }


@pytest.fixture(scope="session")
def db_engine():
    """
    Fixture for a test database engine.
    It creates all tables at the start of the test session and drops them at the end.
    """
    engine = create_engine(TEST_DATABASE_URL, **_engine_kwargs)
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