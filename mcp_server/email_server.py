import contextlib
import os
import logging
from typing import Any
import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("email", stateless_http=True, json_response=True)

MAILTRAP_API_TOKEN = os.getenv("MAILTRAP_API_TOKEN")
MAILTRAP_API_URL = os.getenv("MAILTRAP_API_URL", "https://send.api.mailtrap.io/api/send")
MAILTRAP_SENDER_EMAIL = os.getenv("MAILTRAP_SENDER_EMAIL")
MAILTRAP_SENDER_NAME = os.getenv("MAILTRAP_SENDER_NAME", "Lardis Bot")

logger = logging.getLogger(__name__)


@mcp.tool()
async def send_simple_email(
    subject: str,
    body: str,
    email_to: str
) -> dict[str, Any]:
    """
    Отправляет простое текстовое письмо через Mailtrap API.

    Args:
        subject: Тема письма
        body: Текст письма
        email_to: Email получателя

    Returns:
        {"success": bool, "to": str} или {"error": str}
    """
    if not MAILTRAP_API_TOKEN:
        return {"error": "MAILTRAP_API_TOKEN не задан"}
    if not email_to or not email_to.strip():
        return {"error": "email_to обязателен"}
    if not MAILTRAP_SENDER_EMAIL:
        return {"error": "MAILTRAP_SENDER_EMAIL не задан"}

    payload = {
        "from": {"email": MAILTRAP_SENDER_EMAIL, "name": MAILTRAP_SENDER_NAME},
        "to": [{"email": email_to.strip()}],
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

    logger.info("Email sent to %s", email_to)
    return {"success": True, "to": email_to}


@mcp.tool()
async def send_reminders_summary(
    reminders_json: str,
    analysis_notes: str = ""
) -> dict[str, Any]:
    """
    Собирает и отправляет сводку напоминаний на email.

    Args:
        reminders_json: JSON-строка с массивом напоминаний
                       [{"id": int, "text": str, "timestamp": str}, ...]
        analysis_notes: Заметки о приоритизации (например: "1 высокий, 2 средний")

    Returns:
        {"success": bool, "to": str, "message": str} или {"error": str}
    """
    import json
    from datetime import datetime

    summary_email_to = os.getenv("SUMMARY_EMAIL_TO")
    if not summary_email_to or not summary_email_to.strip():
        return {"error": "SUMMARY_EMAIL_TO не задан в .env"}

    if not MAILTRAP_API_TOKEN:
        return {"error": "MAILTRAP_API_TOKEN не задан"}

    try:
        reminders = json.loads(reminders_json)
    except json.JSONDecodeError as e:
        return {"error": f"Невалидный JSON в reminders_json: {e}"}

    if not isinstance(reminders, list):
        return {"error": "reminders_json должен быть массивом"}

    # Форматируем письмо
    body_lines = [
        "Сводка напоминаний",
        "=" * 50,
        ""
    ]

    if analysis_notes:
        body_lines.append(f"Анализ: {analysis_notes}")
        body_lines.append("")

    body_lines.append(f"Всего напоминаний: {len(reminders)}\n")

    for idx, reminder in enumerate(reminders, 1):
        text = reminder.get("text", "[нет текста]")
        timestamp = reminder.get("timestamp", "[нет времени]")
        body_lines.append(f"{idx}. {text}")
        body_lines.append(f"   Время: {timestamp}\n")

    body_lines.append("=" * 50)
    body_lines.append(f"Сформировано: {datetime.now().isoformat()}")

    body = "\n".join(body_lines)

    # Отправляем
    payload = {
        "from": {"email": MAILTRAP_SENDER_EMAIL, "name": MAILTRAP_SENDER_NAME},
        "to": [{"email": summary_email_to.strip()}],
        "subject": f"Сводка напоминаний ({len(reminders)} шт.)",
        "text": body,
    }
    headers = {
        "Authorization": f"Bearer {MAILTRAP_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(MAILTRAP_API_URL, json=payload, headers=headers)
            if resp.status_code >= 300:
                return {"error": f"Mailtrap API error {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"Ошибка отправки: {str(e)}"}

    logger.info("Reminders summary sent to %s", summary_email_to)
    return {
        "success": True,
        "to": summary_email_to,
        "message": f"Сводка из {len(reminders)} напоминаний отправлена"
    }


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


async def health(request):
    return JSONResponse({"status": "ok", "service": "email-mcp-server"})


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
