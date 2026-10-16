"""Database engine, session, and base class.

Works with SQLite locally (zero setup) and Postgres in production. The DB URL
comes from the DATABASE_URL env var; Neon/Fly often hand out a `postgres://`
URL, which we normalise to the SQLAlchemy + psycopg v3 form.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _normalise(url: str) -> str:
    # Heroku/Neon style -> SQLAlchemy + psycopg v3 driver
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DB_URL = _normalise(settings.database_url)

if DB_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(DB_URL, connect_args=connect_args, echo=False)
else:
    # Postgres: pre-ping avoids stale connections after the host sleeps/wakes.
    engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=300, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
