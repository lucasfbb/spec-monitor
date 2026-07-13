"""Config de testes: SQLite em arquivo temporário e settings de teste via env."""

import os
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="spec-monitor-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "senha-de-teste-123"
os.environ["GITHUB_WEBHOOK_SECRET"] = "segredo-webhook-teste"
os.environ["ENV"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app, seed_admin  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    # TestClient dispara o lifespan (cria schema + seeda admin); o poller
    # criado é cancelado ao sair do contexto.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client(client):
    resp = client.post(
        "/login",
        data={"email": "admin@test.local", "password": "senha-de-teste-123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    return client


__all__ = ["seed_admin"]
