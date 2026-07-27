import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base
from app.models.model_version import ModelVersion
from app.models.rate_table import RateTable

settings = get_settings()

# Tests must never hit the Gemini API. Forcing mock mode makes the Stage 2b embedding
# room-classifier escalation a no-op (returns None -> keyword result stands), so
# classification stays deterministic and offline regardless of what .env has enabled.
# It also keeps the QBQ chat orchestrator on its offline keyword parser.
settings.GEMINI_MOCK_MODE = True

# Likewise for sign-in: a developer with real Google/GitHub credentials in .env
# must not have the suite start negotiating with live OAuth providers.
settings.OAUTH_MOCK_MODE = True

_RATE_TABLE_SEED = json.loads(
    (Path(__file__).resolve().parents[1] / "app" / "seed_data" / "rate_table_seed.json").read_text()
)

_TEST_DB_NAME = "boq_test_db"


def _test_database_url() -> str:
    """Isolated test database in the same Postgres container — never the dev DB
    (boq_db), so running tests can never wipe manually-created dev/demo data."""
    base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    return f"{base_url}/{_TEST_DB_NAME}"


def _ensure_test_database_exists() -> None:
    admin_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": _TEST_DB_NAME}
        ).scalar()
        if not exists:
            conn.execute(text(f"CREATE DATABASE {_TEST_DB_NAME}"))
    admin_engine.dispose()


_ensure_test_database_exists()
_engine = create_engine(_test_database_url())
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=_engine)
    session = _TestSessionLocal()
    try:
        # Mirror the Alembic 0002 data migration so tests see the same rate_table /
        # model_versions baseline as dev — otherwise /calculate silently produces
        # total_cost=0.0 in tests (no rate found for any material), which looks like
        # an app bug but is really just an unseeded test fixture.
        for row in _RATE_TABLE_SEED:
            session.add(RateTable(**row))
        session.add(ModelVersion(model_version="fallback-constant-1.0", status="active"))
        session.commit()

        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)
