import asyncio
import json
import logging
from typing import Optional

import chainlit as cl
from chainlit.types import ThreadDict

from app.chat.openrouter_client import OpenRouterClient, build_messages
from app.db.database import get_data_layer, init_db

logger = logging.getLogger(__name__)

# Инициализируем таблицы при импорте модуля
try:
    asyncio.run(init_db())
except Exception as e:
    logger.error(f"Ошибка инициализации БД: {e}")

@cl.data_layer
def data_layer():
    """Регистрация SQLAlchemy Data Layer для Chainlit."""
    return get_data_layer()


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """Простая авторизация admin/1234."""
    if username == "admin" and password == "1234":
        return cl.User(identifier="admin", metadata={"role": "admin"})
    return None


@cl.on_chat_start
async def on_chat_start():
    """Инициализация нового чата."""
    await cl.Message(content="Привет! Я AI ассистент с доступом к инструментам напоминаний.").send()
    client = OpenRouterClient()
    cl.user_session.set("client", client)

    cl.user_session.set("history", [])

    logger.info("Новый чат начат")


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """Восстановление истории при возобновлении чата."""
    client = OpenRouterClient()
    cl.user_session.set("client", client)

    logger.info(f"Восстановление треда {thread.get('id')}, steps: {len(thread.get('steps', []))}")

    history = []
    for step in thread.get("steps", []):
        logger.info(f"Step type: {step.get('type')}, output: {step.get('output', '')[:50]}")
        if step["type"] == "user_message":
            history.append({"role": "user", "content": step["output"]})
        elif step["type"] == "assistant_message":
            metadata = step.get("metadata") or {}
            # Пропускаем служебные логи о вызове MCP, чтобы не кормить ими модель
            if metadata.get("mcp_log"):
                continue
            history.append({"role": "assistant", "content": step["output"]})

    cl.user_session.set("history", history)
    logger.info(f"Чат возобновлен, восстановлено {len(history)} сообщений")



@cl.on_message
async def on_message(message: cl.Message):
    """Обработка входящего сообщения пользователя."""
    client = cl.user_session.get("client")
    history = cl.user_session.get("history")

    system_prompt = """Ты полезный AI ассистент с доступом к инструментам управления напоминаниями и отправки email.

Когда пользователь просит суммировать напоминания и отправить на email:
1. Вызови инструмент 'list_reminders' чтобы получить все напоминания
2. Проанализируй текст каждого напоминания и определи важность:
   - ВЫСОКИЙ приоритет: содержит слова "срочно", "важно", "deadline", "критично", "ASAP"
   - СРЕДНИЙ приоритет: обычные задачи и события
   - НИЗКИЙ приоритет: информационные или отложенные напоминания
3. Сформируй JSON-массив напоминаний
4. Вызови инструмент 'send_reminders_summary' с:
   - reminders_json: полный список в формате JSON
   - analysis_notes: краткое резюме анализа приоритизации

Примечание: email адрес получателя устанавливается автоматически из настроек, не запрашивай его у пользователя."""

    messages = build_messages(
        user_input=message.content,
        history=history,
        system_prompt=system_prompt
    )

    response_data = await client.chat_completion(messages=messages)
    assistant_message = response_data["choices"][0]["message"]["content"]

    mcp_calls = response_data.get("_mcp_calls") or []
    for call in mcp_calls:
        name = call.get("name") or "unknown"
        args = call.get("arguments") or {}
        result = call.get("result")
        error = call.get("error")

        args_json = json.dumps(args, ensure_ascii=False)
        result_json = json.dumps(result, ensure_ascii=False) if result is not None else None

        content_lines = [
            f"Вызов MCP инструмента `{name}`",
            f"Аргументы: {args_json}",
        ]
        if error:
            content_lines.append(f"Ошибка: {error}")
        elif result_json is not None:
            content_lines.append(f"Ответ: {result_json}")

        await cl.Message(
            content="\n".join(content_lines),
            author="MCP",
            metadata={"mcp_log": True, "tool": name},
        ).send()

    await cl.Message(content=assistant_message).send()

    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": assistant_message})
    cl.user_session.set("history", history)
