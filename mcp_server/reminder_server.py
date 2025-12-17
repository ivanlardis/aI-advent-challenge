import asyncio
import contextlib
import logging
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Optional

import aiosqlite
import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.fastmcp import FastMCP

# Конфигурация
DB_PATH = Path("/data/reminders.db")
mcp = FastMCP("reminders", stateless_http=True, json_response=True)

# Mailtrap API config (token-based)
MAILTRAP_API_TOKEN = os.getenv("MAILTRAP_API_TOKEN")
MAILTRAP_API_URL = os.getenv("MAILTRAP_API_URL", "https://send.api.mailtrap.io/api/send")
MAILTRAP_SENDER_EMAIL = os.getenv("MAILTRAP_SENDER_EMAIL")
MAILTRAP_SENDER_NAME = os.getenv("MAILTRAP_SENDER_NAME", "Reminders Bot")
DEFAULT_EMAIL_TO = os.getenv("SUMMARY_EMAIL_TO") or os.getenv("EMAIL_TO")

# Авторассылка раз в сутки (время HH:MM по локальному времени контейнера)
AUTO_SUMMARY_ENABLED = os.getenv("SUMMARY_EMAIL_AUTO", "false").lower() == "true"
AUTO_SUMMARY_TIME = os.getenv("SUMMARY_EMAIL_TIME", "09:00")
AUTO_CHECK_INTERVAL_SEC = int(os.getenv("SUMMARY_EMAIL_CHECK_INTERVAL", "60"))

# Сохраняем дату последней отправки, чтобы не слать несколько раз в сутки
_last_auto_send: Optional[date] = None
_auto_task: Optional[asyncio.Task] = None

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


async def _fetch_all_reminders() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, text, timestamp, created_at FROM reminders ORDER BY timestamp ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {"id": row[0], "text": row[1], "timestamp": row[2], "created_at": row[3]}
                for row in rows
            ]


def _render_summary(reminders: list[dict[str, Any]]) -> str:
    if not reminders:
        return "Напоминаний нет."
    lines = ["Список напоминаний:"]
    for r in reminders:
        lines.append(f"- #{r['id']} @ {r['timestamp']}: {r['text']}")
    return "\n".join(lines)


async def _send_email(subject: str, body: str, *, to_email: Optional[str]) -> dict[str, Any]:
    """
    Отправка письма через Mailtrap Send API (по токену).
    """
    if not MAILTRAP_API_TOKEN:
        return {"error": "MAILTRAP_API_TOKEN не задан"}
    if not to_email:
        return {"error": "Не указан адрес получателя (передайте email_to или SUMMARY_EMAIL_TO)."}
    if not MAILTRAP_SENDER_EMAIL:
        return {"error": "MAILTRAP_SENDER_EMAIL не задан"}

    payload = {
        "from": {"email": MAILTRAP_SENDER_EMAIL, "name": MAILTRAP_SENDER_NAME},
        "to": [{"email": to_email}],
        "subject": subject,
        "text": body,
    }
    headers = {
        "Authorization": f"Bearer {MAILTRAP_API_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(MAILTRAP_API_URL, json=payload, headers=headers)
        if resp.status_code >= 300:
            return {"error": f"Mailtrap API error {resp.status_code}: {resp.text[:200]}"}

    logger.info("Email sent to %s via Mailtrap API", to_email)
    return {"success": True, "to": to_email}


@mcp.tool()
async def send_summary_email(email_to: str | None = None) -> dict[str, Any]:
    """
    Отправляет на email текстовую сводку всех напоминаний.

    Args:
        email_to: адрес получателя. Если не указан, берется SUMMARY_EMAIL_TO.
    """
    target_email = email_to or DEFAULT_EMAIL_TO
    reminders = await _fetch_all_reminders()
    summary_text = _render_summary(reminders)
    result = await _send_email("Reminders summary", summary_text, to_email=target_email)
    if "error" in result:
        return result
    result.update({"sent_reminders": len(reminders)})
    return result


def _parse_time_str(hhmm: str) -> time:
    try:
        hour, minute = hhmm.split(":")
        return time(hour=int(hour), minute=int(minute))
    except Exception as exc:
        raise ValueError(f"Неверный формат времени SUMMARY_EMAIL_TIME: {hhmm}") from exc


async def _auto_summary_loop():
    """Раз в сутки отправляет email cо сводкой, если включено AUTO_SUMMARY_ENABLED."""
    global _last_auto_send
    target_time = _parse_time_str(AUTO_SUMMARY_TIME)

    while True:
        now = datetime.now()
        if (
            AUTO_SUMMARY_ENABLED
            and DEFAULT_EMAIL_TO
            and (_last_auto_send != now.date())
            and (now.time().hour > target_time.hour or (now.time().hour == target_time.hour and now.time().minute >= target_time.minute))
        ):
            try:
                reminders = await _fetch_all_reminders()
                summary_text = _render_summary(reminders)
                result = await _send_email("Reminders summary", summary_text, to_email=DEFAULT_EMAIL_TO)
                if "error" in result:
                    logger.warning("Auto summary send failed: %s", result["error"])
                else:
                    _last_auto_send = now.date()
            except Exception as exc:
                # не падаем из-за ошибок почты
                logger.warning("Auto summary send failed: %s", exc)

        await asyncio.sleep(AUTO_CHECK_INTERVAL_SEC)


# ASGI app
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    await init_database()
    # Автопочта — фоновая задача
    global _auto_task
    if AUTO_SUMMARY_ENABLED:
        _auto_task = asyncio.create_task(_auto_summary_loop())
    async with mcp.session_manager.run():
        yield
    if _auto_task:
        _auto_task.cancel()
        with contextlib.suppress(Exception):
            await _auto_task


async def health(request):
    return JSONResponse({"status": "ok", "service": "reminder-mcp-server"})


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
