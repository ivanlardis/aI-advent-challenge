import logging
import asyncio
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
            history.append({"role": "assistant", "content": step["output"]})

    cl.user_session.set("history", history)
    logger.info(f"Чат возобновлен, восстановлено {len(history)} сообщений")


@cl.on_message
async def on_message(message: cl.Message):
    """Обработка входящего сообщения пользователя."""
    client = cl.user_session.get("client")
    history = cl.user_session.get("history")

    messages = build_messages(
        user_input=message.content,
        history=history,
        system_prompt="Ты полезный AI ассистент."
    )

    response_data = await client.chat_completion(messages=messages)
    assistant_message = response_data["choices"][0]["message"]["content"]

    await cl.Message(content=assistant_message).send()

    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": assistant_message})
    cl.user_session.set("history", history)
