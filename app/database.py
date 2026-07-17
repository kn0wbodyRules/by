from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> None:
    """Raises immediately with a clear error if the DB is unreachable, instead of
    letting the app hang or fail confusingly on the first request."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


__all__ = ["Base", "engine", "SessionLocal", "get_db", "check_db_connection"]
