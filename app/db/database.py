import os
import logging
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

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Извлекаем параметры подключения из URL
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(database_url)
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
