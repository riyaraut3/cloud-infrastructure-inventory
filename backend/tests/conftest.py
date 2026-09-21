import os
import tempfile

os.environ["API_KEY"] = "test-api-key"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LOCAL_UPLOAD_DIR"] = tempfile.mkdtemp(prefix="inventory-test-")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app import db
from app.main import app


@pytest.fixture()
def client(monkeypatch):
    # Isolated in-memory database per test.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    from app import main
    monkeypatch.setattr(main, "create_schema", db.create_schema)
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
