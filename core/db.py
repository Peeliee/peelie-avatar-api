from typing import Annotated, AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

class Base(DeclarativeBase):
    pass

def create_engine(dsn: str):
    return create_async_engine(
        dsn,
        echo=settings.DEBUG,
    )

def create_session_factory(async_engine: AsyncEngine):
    return async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )

engine = create_engine(settings.DATABASE_URL)
async_session_factory = create_session_factory(engine)

async def use_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

DbSessionDep = Annotated[AsyncSession, Depends(use_session)]