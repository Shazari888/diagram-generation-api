from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.diagram import Base, Diagram

engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
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
