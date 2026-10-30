"""Database engine/session helpers (sync SQLAlchemy + psycopg)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings, load_settings

_ENGINE: Engine | None = None
_FACTORY: sessionmaker | None = None


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, future=True)


def get_engine(settings: Settings | None = None) -> Engine:
    global _ENGINE, _FACTORY
    if _ENGINE is None:
        settings = settings or load_settings()
        _ENGINE = make_engine(settings.database_url)
        _FACTORY = sessionmaker(bind=_ENGINE, expire_on_commit=False, future=True)
    return _ENGINE


def get_session_factory(settings: Settings | None = None) -> sessionmaker:
    get_engine(settings)
    assert _FACTORY is not None
    return _FACTORY


def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    global _ENGINE, _FACTORY
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _FACTORY = None


def database_ready(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            value = connection.execute(
                text("SELECT to_regclass('erratascope.projects') IS NOT NULL")
            ).scalar()
            return bool(value)
    except Exception:
        return False
