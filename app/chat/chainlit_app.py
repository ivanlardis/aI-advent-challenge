import asyncio
import json
import logging
from typing import Optional, List, Dict, Any

import chainlit as cl
from chainlit.types import ThreadDict

from app.chat.openrouter_client import OpenRouterClient, build_messages
from app.db.database import get_data_layer, init_db
from app.rag.rag_service import CityRAG

logger = logging.getLogger(__name__)

# Глобальная переменная для RAG индекса
RAG_INDEX: Optional[CityRAG] = None

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


def should_use_rag(user_input: str) -> bool:
    """Определяет необходимость RAG-поиска по ключевым словам."""
    keywords = [
        "город", "города", "городе", "городов", "городах",
        "федеральный округ", "регион", "область",
        "расположен", "находится", "где",
        # Примеры названий городов
        "москва", "санкт-петербург", "тула", "брянск", "казань",
        "новосибирск", "екатеринбург", "иркутск", "челябинск"
    ]
    user_input_lower = user_input.lower()
    return any(keyword in user_input_lower for keyword in keywords)


def format_rag_context(results: List[Dict[str, Any]]) -> str:
    """Форматирует результаты RAG-поиска для промпта."""
    if not results:
        return ""

    parts = ["Найденная информация о городах из базы знаний:\n"]
    for i, result in enumerate(results, 1):
        city = result.get("city", "Неизвестно")
        text = result.get("text", "")
        score = result.get("score", 0.0)
        parts.append(f"{i}. {city}: {text} (релевантность: {score:.2f})")

    return "\n".join(parts)


@cl.on_chat_start
async def on_chat_start():
    """Инициализация нового чата."""
    global RAG_INDEX

    # Инициализация RAG индекса (один раз для всего приложения)
    if RAG_INDEX is None:
        await cl.Message(content="🔄 Загружаю базу знаний городов России...").send()
        try:
            RAG_INDEX = CityRAG(
                data_file="rag_example_cities_ru.txt",
                index_dir="data/faiss_index",
                model_name="paraphrase-multilingual-MiniLM-L12-v2",  # Лёгкая модель 420 МБ
                deduplicate=True
            )
            await RAG_INDEX.initialize()
            stats = RAG_INDEX.get_stats()
            await cl.Message(
                content=f"✅ База знаний готова! Загружено {stats.get('total_documents', 0)} документов."
            ).send()
        except Exception as e:
            logger.error(f"Ошибка инициализации RAG: {e}")
            await cl.Message(
                content=f"⚠️ Не удалось загрузить базу знаний городов: {e}"
            ).send()

    await cl.Message(content="Привет! Я AI ассистент с доступом к инструментам напоминаний и базе знаний о городах России.").send()
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

    # RAG-поиск если нужно
    rag_context = ""
    if RAG_INDEX and should_use_rag(message.content):
        try:
            logger.info(f"Выполняю RAG-поиск для запроса: {message.content[:50]}...")
            search_results = RAG_INDEX.search(message.content, k=3)

            if search_results:
                rag_context = format_rag_context(search_results)
                logger.info(f"Найдено {len(search_results)} релевантных документов")

                # Формируем сообщение с деталями найденных документов
                details_lines = [f"**[RAG] Найдено {len(search_results)} релевантных документов:**\n"]
                for i, result in enumerate(search_results, 1):
                    city = result.get("city", "Неизвестно")
                    text = result.get("text", "")
                    score = result.get("score", 0.0)
                    preview = text[:100] + "..." if len(text) > 100 else text
                    details_lines.append(
                        f"{i}. **{city}** (релевантность: {score:.2f})\n   _{preview}_"
                    )

                # Отправляем сообщение с результатами
                msg_content = "\n\n".join(details_lines)
                logger.info(f"[DEBUG] Отправляю RAG-сообщение в Chainlit, длина: {len(msg_content)}")
                msg = cl.Message(content=msg_content)
                await msg.send()
                logger.info(f"[DEBUG] RAG-сообщение отправлено, ID: {msg.id}")
        except Exception as e:
            logger.error(f"Ошибка RAG-поиска: {e}", exc_info=True)
            try:
                await cl.Message(content=f"**[RAG]** ❌ Ошибка поиска: {e}").send()
            except Exception as e2:
                logger.error(f"Ошибка отправки сообщения об ошибке: {e2}", exc_info=True)

    # Базовый промпт
    base_prompt = """Ты полезный AI ассистент с доступом к инструментам управления напоминаниями и отправки email.

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

    # Добавляем RAG-контекст если есть
    if rag_context:
        system_prompt = f"""{base_prompt}

{rag_context}

Используй найденную информацию для ответа на вопрос пользователя о городах.
Если информация не найдена в базе, честно скажи об этом."""
    else:
        system_prompt = base_prompt

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
