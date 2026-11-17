"""PostgreSQL fixtures for the configured, dedicated SBOA test database."""
from types import SimpleNamespace

import pytest

from sboa.datamodel.base import Session, engine as database
from sboa.engine.engine import Engine
from sboa.engine.query import Query


@pytest.fixture
def store():
    engine = Engine()
    query = Query()
    try:
        query.clear_db()
        yield SimpleNamespace(engine=engine, query=query, database=database, factory=Session)
    finally:
        engine.close_session()
        query.close_session()
