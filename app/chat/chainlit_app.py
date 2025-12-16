import logging
import asyncio
import os
from typing import Optional

import chainlit as cl
from chainlit.types import ThreadDict

from app.chat.mcp_client import MCPClient
from app.chat.openrouter_client import OpenRouterClient, build_messages
from app.db.database import get_data_layer, init_db

logger = logging.getLogger(__name__)

# Инициализируем таблицы при импорте модуля
try:
    asyncio.run(init_db())
except Exception as e:
    logger.error(f"Ошибка инициализации БД: {e}")

CONTEXT7_TRIGGER = "/context7"
CONTEXT7_MCP_ENDPOINT = os.getenv("CONTEXT7_MCP_ENDPOINT", "https://mcp.context7.com/mcp")
CONTEXT7_API_KEY = os.getenv(
    "CONTEXT7_API_KEY",
    "ctx7sk-70ea9a0d-53d5-4055-94b5-29235d60cd08",
)


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
    await cl.Message(content=f"Общение или узнать тулзы у mcp1 {CONTEXT7_TRIGGER}").send()
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

    if CONTEXT7_TRIGGER in message.content:
        tools_info = await get_tools_info()
        await cl.Message(content=tools_info).send()
    else:
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


async def get_tools_info() -> str:
    client = MCPClient(endpoint=CONTEXT7_MCP_ENDPOINT, api_key=CONTEXT7_API_KEY)

    output = []

    try:
        output.append("=== Получаем список инструментов ===\n")
        await client.ensure_initialized()

        all_tools = []
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            tools = page.get("tools") or []
            all_tools.extend(tools)
            cursor = page.get("nextCursor")
            if not cursor:
                break

        output.append(f"Доступные инструменты ({len(all_tools)}):")

        for tool in all_tools:
            output.append(f"\n  📌 {tool.get('name', '(no name)')}")
            output.append(f"     Заголовок: {tool.get('title', '')}")
            output.append(f"     Описание: {tool.get('description', '')[:200]}...")

            schema = tool.get("inputSchema")
            if isinstance(schema, dict):
                props = schema.get('properties', {})
                required = schema.get('required', [])

                output.append(f"     Параметры:")
                for prop_name, prop_schema in props.items():
                    req_marker = "✓" if prop_name in required else "○"
                    output.append(f"       {req_marker} {prop_name}: {prop_schema.get('description', '')[:100]}")

    except Exception as e:
        output.append(f"Ошибка: {e}")
        import traceback
        output.append(traceback.format_exc())

    return "\n".join(output)
