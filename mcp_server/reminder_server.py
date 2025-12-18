import contextlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.fastmcp import FastMCP

# Конфигурация
DB_PATH = Path("/data/reminders.db")
mcp = FastMCP("reminders", stateless_http=True, json_response=True)

logger = logging.getLogger(__name__)


async def init_database():
    """Создает таблицу при первом запуске."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


def validate_timestamp(timestamp: str) -> bool:
    """Проверяет ISO 8601 формат (2025-12-17T15:30:00Z)."""
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


@mcp.tool()
async def create_reminder(text: str, timestamp: str) -> dict[str, Any]:
    """
    Создает новое напоминание.

    Args:
        text: Текст напоминания
        timestamp: Время срабатывания в ISO 8601 (например: 2025-12-17T15:30:00Z)

    Returns:
        {"id": int, "text": str, "timestamp": str, "created_at": str}
        {"error": str} в случае ошибки
    """
    if not text.strip():
        return {"error": "Текст напоминания не может быть пустым"}

    if not validate_timestamp(timestamp):
        return {"error": "Неверный формат времени. Используйте ISO 8601: YYYY-MM-DDTHH:MM:SSZ"}

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (text, timestamp) VALUES (?, ?)",
            (text, timestamp)
        )
        await db.commit()
        reminder_id = cursor.lastrowid

        # Получаем created_at
        async with db.execute(
            "SELECT text, timestamp, created_at FROM reminders WHERE id = ?",
            (reminder_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return {
                "id": reminder_id,
                "text": row[0],
                "timestamp": row[1],
                "created_at": row[2]
            }


@mcp.tool()
async def list_reminders() -> list[dict[str, Any]]:
    """
    Возвращает список всех напоминаний, отсортированных по времени срабатывания.

    Returns:
        [{"id": int, "text": str, "timestamp": str, "created_at": str}, ...]
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, text, timestamp, created_at FROM reminders ORDER BY timestamp ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "text": row[1],
                    "timestamp": row[2],
                    "created_at": row[3]
                }
                for row in rows
            ]


@mcp.tool()
async def delete_reminder(id: int) -> dict[str, Any]:
    """
    Удаляет напоминание по ID.

    Args:
        id: ID напоминания для удаления

    Returns:
        {"success": bool, "message": str}
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем существование
        async with db.execute("SELECT id FROM reminders WHERE id = ?", (id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"success": False, "message": f"Напоминание с ID {id} не найдено"}

        # Удаляем
        await db.execute("DELETE FROM reminders WHERE id = ?", (id,))
        await db.commit()
        return {"success": True, "message": f"Напоминание {id} удалено"}


@mcp.tool()
async def update_reminder(
    id: int,
    text: str | None = None,
    timestamp: str | None = None
) -> dict[str, Any]:
    """
    Обновляет текст и/или время напоминания.

    Args:
        id: ID напоминания
        text: Новый текст (необязательно)
        timestamp: Новое время в ISO 8601 (необязательно)

    Returns:
        {"id": int, "text": str, "timestamp": str, "created_at": str}
        {"error": str} в случае ошибки
    """
    if text is None and timestamp is None:
        return {"error": "Укажите хотя бы одно поле для обновления: text или timestamp"}

    if timestamp and not validate_timestamp(timestamp):
        return {"error": "Неверный формат времени. Используйте ISO 8601: YYYY-MM-DDTHH:MM:SSZ"}

    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем существование
        async with db.execute("SELECT text, timestamp FROM reminders WHERE id = ?", (id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"error": f"Напоминание с ID {id} не найдено"}

        # Формируем UPDATE запрос
        updates = []
        params = []
        if text is not None:
            updates.append("text = ?")
            params.append(text)
        if timestamp is not None:
            updates.append("timestamp = ?")
            params.append(timestamp)
        params.append(id)

        query = f"UPDATE reminders SET {', '.join(updates)} WHERE id = ?"
        await db.execute(query, tuple(params))
        await db.commit()

        # Возвращаем обновленную запись
        async with db.execute(
            "SELECT text, timestamp, created_at FROM reminders WHERE id = ?",
            (id,)
        ) as cursor:
            row = await cursor.fetchone()
            return {
                "id": id,
                "text": row[0],
                "timestamp": row[1],
                "created_at": row[2]
            }


# ASGI app
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    await init_database()
    async with mcp.session_manager.run():
        yield


async def health(request):
    return JSONResponse({"status": "ok", "service": "reminder-mcp-server"})


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
