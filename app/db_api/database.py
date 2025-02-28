import contextlib
import os
import sys
from contextlib import contextmanager
from typing import Any, AsyncIterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from common.utils import load_env

env_vars = load_env()  # Load environment variables from .env file

DATABASE_URL = (
    env_vars["DB_URL"] if env_vars["USE_PROD"] == "true" else env_vars["DEV_DB_URL"]
)
DATABASE_URL = DATABASE_URL.replace("asyncmy", "pymysql")
ASYNC_DATABASE_URL = DATABASE_URL.replace("pymysql", "asyncmy")
print(f"USE_PROD: {env_vars['USE_PROD']}")
print(f"DB URL: {DATABASE_URL.split('@')[1]}")


if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not set")

Base = declarative_base()


engine = create_engine(
    DATABASE_URL,
    pool_size=30,  # Increase pool size
    max_overflow=10,  # Increase maximum overflow
    pool_recycle=600,  # Recycle connections after 10 minutes
    pool_timeout=60,  # Increase timeout to 60 seconds
)
SessionLocal = sessionmaker(autoflush=False, bind=engine)


@contextmanager
def get_db_ctx():
    with SessionLocal.begin() as session:
        yield session


@contextmanager
def get_db_ctx_manual():
    with SessionLocal() as session:
        yield session


def get_db_gen():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AsyncDatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async_sessionmanager = AsyncDatabaseSessionManager(
    ASYNC_DATABASE_URL,
    engine_kwargs=dict(
        pool_size=30,  # Increase pool size
        max_overflow=10,  # Increase maximum overflow
        pool_recycle=600,  # Recycle connections after 10 minutes
        pool_timeout=60,  # Increase timeout to 60 seconds)
    ),
)


async def async_get_db_session():
    async with async_sessionmanager.session() as session:
        yield session


@contextlib.asynccontextmanager
async def async_get_db_session_ctx():
    async with async_sessionmanager.session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
