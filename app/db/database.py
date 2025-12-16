import os
import logging
from urllib.parse import urlparse, urlunparse

import asyncpg
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

logger = logging.getLogger(__name__)

CHAINLIT_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    identifier TEXT UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    "createdAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT,
    "updatedAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT
);

CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    name TEXT,
    "userId" TEXT REFERENCES users(id) ON DELETE SET NULL,
    "userIdentifier" TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    "createdAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT,
    "updatedAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT,
    "deletedAt" TEXT
);

CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    "threadId" TEXT REFERENCES threads(id) ON DELETE CASCADE,
    "parentId" TEXT,
    input TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    name TEXT,
    output TEXT,
    type TEXT NOT NULL,
    "start" TEXT,
    "end" TEXT,
    "showInput" TEXT,
    "isError" BOOLEAN DEFAULT FALSE,
    streaming BOOLEAN DEFAULT FALSE,
    "waitForAnswer" BOOLEAN DEFAULT FALSE,
    generation TEXT,
    "defaultOpen" BOOLEAN DEFAULT FALSE,
    tags TEXT[],
    language TEXT,
    "createdAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT,
    CONSTRAINT steps_parent_fkey FOREIGN KEY ("parentId") REFERENCES steps(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    "threadId" TEXT REFERENCES threads(id) ON DELETE CASCADE,
    "stepId" TEXT REFERENCES steps(id) ON DELETE SET NULL,
    "forId" TEXT,
    type TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    mime TEXT,
    name TEXT,
    "objectKey" TEXT,
    url TEXT,
    "chainlitKey" TEXT,
    display TEXT,
    size BIGINT,
    language TEXT,
    page INTEGER,
    "autoPlay" BOOLEAN,
    "playerConfig" JSONB,
    props JSONB DEFAULT '{}'::jsonb,
    "createdAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT
);

CREATE TABLE IF NOT EXISTS feedbacks (
    id TEXT PRIMARY KEY,
    "forId" TEXT,
    "stepId" TEXT REFERENCES steps(id) ON DELETE CASCADE,
    name TEXT,
    value DOUBLE PRECISION,
    comment TEXT,
    "createdAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT,
    "updatedAt" TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_thread_user_id ON threads ("userId");
CREATE INDEX IF NOT EXISTS idx_thread_created_at ON threads ("createdAt");
CREATE INDEX IF NOT EXISTS idx_step_thread_id ON steps ("threadId");
CREATE INDEX IF NOT EXISTS idx_element_thread_id ON elements ("threadId");
"""


async def init_db() -> None:
    """Инициализация таблиц Chainlit в БД."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL env var is not set")

    asyncpg_url = _normalize_for_asyncpg(database_url)
    await _ensure_database_exists(asyncpg_url)

    conn = await asyncpg.connect(asyncpg_url)
    try:
        await conn.execute(CHAINLIT_TABLES_SQL)
        logger.info("Таблицы Chainlit созданы/проверены")
    finally:
        await conn.close()


def get_data_layer() -> SQLAlchemyDataLayer:
    """Возвращает SQLAlchemy Data Layer для Chainlit."""
    database_url = os.getenv("DATABASE_URL")

    # Chainlit требует asyncpg драйвер
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return SQLAlchemyDataLayer(conninfo=database_url)


def _normalize_for_asyncpg(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def _ensure_database_exists(dsn: str) -> None:
    parsed = urlparse(dsn)
    target_db = parsed.path.lstrip("/") or "postgres"
    if target_db == "postgres":
        return

    admin_parsed = parsed._replace(path="/postgres")
    admin_dsn = urlunparse(admin_parsed)

    try:
        admin_conn = await asyncpg.connect(admin_dsn)
    except asyncpg.InvalidCatalogNameError:
        admin_parsed = parsed._replace(path="/template1")
        admin_dsn = urlunparse(admin_parsed)
        admin_conn = await asyncpg.connect(admin_dsn)

    try:
        exists = await admin_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname=$1",
            target_db,
        )
        if not exists:
            safe_name = target_db.replace('"', '""')
            await admin_conn.execute(f'CREATE DATABASE "{safe_name}"')
            logger.info("Создана база данных %s", target_db)
    finally:
        await admin_conn.close()
