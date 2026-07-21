from collections.abc import AsyncGenerator
from uuid import UUID
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.diagram import Base, Diagram

log = logging.getLogger(__name__)

# Lazy engine/session creation so startup can recover if DATABASE_URL is unreachable.
_engine = None
_SessionLocal = None


def _create_engine(url: str):
    return create_async_engine(url)


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _create_engine(settings.database_url)
        _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db() -> None:
    """Initialize DB. If the configured DATABASE_URL fails to connect, fall back to a local sqlite file.

    This keeps local development simple when Postgres isn't available.
    """
    global _engine, _SessionLocal
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        log.warning('Database initialization failed with %s; falling back to sqlite. Error: %s', type(exc).__name__, exc)
        # Fallback to sqlite in the repo folder
        sqlite_url = 'sqlite+aiosqlite:///./test.db'
        _engine = _create_engine(sqlite_url)
        _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    global _SessionLocal
    if _SessionLocal is None:
        # ensure engine/session factory exists
        get_engine()
    async with _SessionLocal() as session:
        yield session


async def create_diagram(
    session: AsyncSession,
    *,
    prompt: str,
    source: str,
    diagram_type: str,
) -> Diagram:
    diagram = Diagram(prompt=prompt, source=source, diagram_type=diagram_type)
    session.add(diagram)
    await session.commit()
    await session.refresh(diagram)
    return diagram


async def get_diagram(session: AsyncSession, diagram_id: UUID) -> Diagram | None:
    result = await session.execute(select(Diagram).where(Diagram.id == diagram_id))
    return result.scalar_one_or_none()
