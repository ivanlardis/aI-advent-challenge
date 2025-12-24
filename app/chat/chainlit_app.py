import asyncio
import json
import logging
import os
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
        # Названия городов пользователя
        "москва", "санкт-петербург", "волгоград", "самара",
        "зеленогдар", "орск", "батино",
        "тула", "брянск", "казань", "новосибирск", "екатеринбург"
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


async def display_rag_results(
    all_results: List[Dict[str, Any]],
    filtered_results: List[Dict[str, Any]],
    filter_applied: bool,
    min_score: float
):
    """
    Визуализирует результаты RAG-поиска с информацией о фильтрации.

    Показывает:
    - Количество результатов до/после фильтрации
    - Отфильтрованные документы с причиной отклонения
    - Принятые документы с preview
    """
    lines = []

    # Заголовок
    if filter_applied:
        lines.append(
            f"**[RAG] Найдено {len(all_results)} документов, "
            f"прошло фильтр: {len(filtered_results)} "
            f"(порог: {min_score:.2f})**\n"
        )
    else:
        lines.append(f"**[RAG] Найдено {len(all_results)} документов**\n")

    # Отфильтрованные результаты
    if filter_applied:
        rejected = [r for r in all_results if r not in filtered_results]
        if rejected:
            lines.append("**❌ Отклонено (низкая релевантность):**")
            for r in rejected:
                city = r.get("city", "Неизвестно")
                score = r.get("score", 0.0)
                lines.append(f"- {city} (score: {score:.3f} < {min_score:.2f})")
            lines.append("")

    # Принятые результаты
    if filtered_results:
        lines.append("**✅ Принято:**")
        for i, result in enumerate(filtered_results, 1):
            city = result.get("city", "Неизвестно")
            text = result.get("text", "")
            score = result.get("score", 0.0)
            preview = text[:100] + "..." if len(text) > 100 else text

            lines.append(
                f"{i}. **{city}** (релевантность: {score:.3f})\n"
                f"   _{preview}_"
            )

    # Отправка сообщения
    content = "\n".join(lines)
    await cl.Message(content=content).send()


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

    # Сохраняем начальное значение в сессии
    cl.user_session.set("use_rag", True)

    # Инициализация настроек RAG фильтра
    rag_filter_enabled = os.getenv("RAG_FILTER_ENABLED", "true").lower() == "true"
    rag_min_score = float(os.getenv("RAG_MIN_SCORE", "0.7"))

    cl.user_session.set("use_rag_filter", rag_filter_enabled)
    cl.user_session.set("rag_min_score", rag_min_score)

    # Создаем приветственное сообщение с кнопками управления RAG
    actions = [
        cl.Action(name="enable_rag", payload={"action": "enable"}, label="✅ Включить RAG"),
        cl.Action(name="disable_rag", payload={"action": "disable"}, label="❌ Выключить RAG"),
        cl.Action(name="enable_filter", payload={"action": "enable"}, label="🔍 Включить фильтр"),
        cl.Action(name="disable_filter", payload={"action": "disable"}, label="🔓 Выключить фильтр"),
    ]

    filter_status = "✅" if rag_filter_enabled else "❌"

    await cl.Message(
        content=f"""Привет! Я AI ассистент с доступом к базе знаний о городах России.

**Текущие настройки:**
• RAG: ✅ ВКЛЮЧЕН
• Фильтр релевантности: {filter_status} (порог: {rag_min_score:.2f})

**Команды управления:**
• `/rag on|off` - включить/выключить RAG
• `/filter on|off` - включить/выключить фильтр
• `/filter set 0.75` - установить порог релевантности

Попробуй спросить о городах: Москва, Волгоград, Тверь и других!""",
        actions=actions
    ).send()
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


@cl.action_callback("enable_rag")
async def on_enable_rag(action: cl.Action):
    """Включить RAG."""
    cl.user_session.set("use_rag", True)
    await cl.Message(content="✅ **RAG ВКЛЮЧЕН**. Теперь буду использовать базу знаний о городах!").send()

@cl.action_callback("disable_rag")
async def on_disable_rag(action: cl.Action):
    """Выключить RAG."""
    cl.user_session.set("use_rag", False)
    await cl.Message(content="❌ **RAG ВЫКЛЮЧЕН**. Буду отвечать без базы знаний!").send()


@cl.action_callback("enable_filter")
async def on_enable_filter(action: cl.Action):
    """Включает фильтр релевантности."""
    cl.user_session.set("use_rag_filter", True)
    min_score = cl.user_session.get("rag_min_score", 0.7)
    await cl.Message(
        content=f"🔍 **Фильтр релевантности ВКЛЮЧЕН** (порог: {min_score:.2f})\n\n"
                f"Результаты с score < {min_score:.2f} будут отбрасываться."
    ).send()


@cl.action_callback("disable_filter")
async def on_disable_filter(action: cl.Action):
    """Выключает фильтр релевантности."""
    cl.user_session.set("use_rag_filter", False)
    await cl.Message(
        content="🔓 **Фильтр релевантности ВЫКЛЮЧЕН**\n\nПоказываю все результаты поиска."
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Обработка входящего сообщения пользователя."""
    # Обработка команд управления RAG
    if message.content.strip().lower() == "/rag on":
        cl.user_session.set("use_rag", True)
        await cl.Message(content="✅ **RAG ВКЛЮЧЕН**. Теперь буду использовать базу знаний о городах!").send()
        return
    elif message.content.strip().lower() == "/rag off":
        cl.user_session.set("use_rag", False)
        await cl.Message(content="❌ **RAG ВЫКЛЮЧЕН**. Буду отвечать без базы знаний!").send()
        return

    # Команды управления фильтром
    if message.content.strip().lower() == "/filter on":
        cl.user_session.set("use_rag_filter", True)
        min_score = cl.user_session.get("rag_min_score", 0.7)
        await cl.Message(
            content=f"🔍 **Фильтр ВКЛЮЧЕН** (порог: {min_score:.2f})"
        ).send()
        return
    elif message.content.strip().lower() == "/filter off":
        cl.user_session.set("use_rag_filter", False)
        await cl.Message(
            content="🔓 **Фильтр ВЫКЛЮЧЕН**"
        ).send()
        return
    elif message.content.strip().lower().startswith("/filter set "):
        try:
            new_threshold = float(message.content.split()[-1])
            if 0.0 <= new_threshold <= 1.0:
                cl.user_session.set("rag_min_score", new_threshold)
                await cl.Message(
                    content=f"🔍 **Порог фильтра изменен на {new_threshold:.2f}**"
                ).send()
            else:
                await cl.Message(
                    content="❌ Порог должен быть между 0.0 и 1.0"
                ).send()
        except ValueError:
            await cl.Message(
                content="❌ Неверный формат. Используй: `/filter set 0.75`"
            ).send()
        return

    client = cl.user_session.get("client")
    history = cl.user_session.get("history")

    # RAG-поиск если нужно
    rag_context = ""
    use_rag = cl.user_session.get("use_rag", True)
    if RAG_INDEX and use_rag and should_use_rag(message.content):
        try:
            # Получаем параметры фильтрации
            use_filter = cl.user_session.get("use_rag_filter", True)
            min_score = cl.user_session.get("rag_min_score", 0.7)

            logger.info(
                f"RAG-поиск: query='{message.content[:50]}' | "
                f"filter={use_filter} | min_score={min_score}"
            )

            # Вызываем search с параметрами фильтрации
            search_data = RAG_INDEX.search(
                message.content,
                k=3,
                min_score=min_score if use_filter else None,
                apply_filter=use_filter
            )

            # Извлекаем данные
            all_results = search_data["all_results"]
            filtered_results = search_data["filtered_results"]
            filter_applied = search_data["filter_applied"]

            # Обработка случая, когда все результаты отфильтрованы
            if filter_applied and not filtered_results and all_results:
                logger.warning(
                    "Все результаты отклонены фильтром, возвращаю топ-1 с предупреждением"
                )
                filtered_results = [all_results[0]]
                await cl.Message(
                    content=f"⚠️ **Предупреждение:** Нет результатов выше порога {min_score:.2f}, "
                            f"показываю лучший результат (score: {all_results[0]['score']:.2f})"
                ).send()

            if filtered_results:
                # Формируем контекст для промпта
                rag_context = format_rag_context(filtered_results)

                # Визуализация результатов
                await display_rag_results(
                    all_results=all_results,
                    filtered_results=filtered_results,
                    filter_applied=filter_applied,
                    min_score=min_score
                )
        except Exception as e:
            logger.error(f"Ошибка RAG-поиска: {e}", exc_info=True)
            await cl.Message(content=f"**[RAG]** ❌ Ошибка поиска: {e}").send()

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
