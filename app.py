#!/usr/bin/env python3
"""
God Agent - Личный AI-помощник
Объединяет все Chainlit-реализации из AI Advent Challenge
"""

import csv
import io
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import chainlit as cl
from dotenv import load_dotenv

from lib.openrouter_client import OpenRouterClient, build_messages
from lib.mcp_client import get_mcp_tools_info
from lib.rag_service import SimpleRAG, format_rag_context, format_sources

# Загружаем переменные окружения
load_dotenv()

# ========================== КОНФИГУРАЦИЯ ==========================

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Глобальный RAG индекс
RAG_INDEX: Optional[SimpleRAG] = None


# ========================== ПЕРСОНАЛИЗАЦИЯ ==========================

def load_profile(profile_path: str = "config/profile.md") -> str:
    """Загружает профиль пользователя из MD файла."""
    current_dir = Path(__file__).parent
    full_path = current_dir / profile_path

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Профиль загружен: {full_path}")
            return content
    except FileNotFoundError:
        print(f"Профиль не найден: {full_path}")
        return ""
    except Exception as e:
        print(f"Ошибка загрузки профиля: {e}")
        return ""


def extract_name(profile_content: str) -> str:
    """Извлекает имя пользователя из профиля."""
    match = re.search(r'- \*\*Имя:\*\*\s*(.+)', profile_content)
    if match:
        return match.group(1).strip()
    return "Пользователь"


# Загрузка профиля при старте
USER_PROFILE = load_profile()
USER_NAME = extract_name(USER_PROFILE)


# ========================== SYSTEM PROMPT ==========================

def get_system_prompt(rag_context: str = "") -> str:
    """Формирует system prompt с учетом профиля и RAG контекста."""
    base_prompt = """Ты — God Agent, личный AI-помощник. Твоя задача — помогать пользователю, поддерживать и мотивировать.

Отвечай:
- По-русски
- Дружелюбно и с заботой
- Кратко (5-7 предложений, если не нужен код)
- С учетом контекста о пользователе
"""

    if USER_PROFILE:
        base_prompt += f"""

## КОНТЕКСТ О ПОЛЬЗОВАТЕЛЕ:
{USER_PROFILE}

Обращайся к пользователю по имени: {USER_NAME}."""

    if rag_context:
        base_prompt += f"""

## ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:
{rag_context}

Используй эту информацию для ответа, если она релевантна вопросу."""

    return base_prompt


# ========================== ФАЙЛОВЫЙ АНАЛИТИК ==========================

def detect_file_type(filename: str, content: bytes) -> str:
    """Определяет тип файла."""
    ext = Path(filename).suffix.lower()

    if ext == ".csv":
        return "csv"
    elif ext == ".json":
        return "json"
    elif ext in [".log", ".txt"]:
        return "text"

    # Пытаемся определить по содержимому
    try:
        text = content.decode("utf-8")
        if text.strip().startswith("{") or text.strip().startswith("["):
            return "json"
        if "," in text.split("\n")[0]:
            return "csv"
    except:
        pass

    return "text"


def parse_file_content(filename: str, content: bytes) -> Dict[str, Any]:
    """Парсит содержимое файла."""
    file_type = detect_file_type(filename, content)
    text = content.decode("utf-8", errors="ignore")

    result = {
        "type": file_type,
        "filename": filename,
        "size": len(content),
        "data": None,
        "preview": "",
        "row_count": 0
    }

    try:
        if file_type == "csv":
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            result["data"] = rows
            result["row_count"] = len(rows)
            result["preview"] = f"CSV: {len(rows)} строк, столбцы: {', '.join(reader.fieldnames or [])}"

        elif file_type == "json":
            data = json.loads(text)
            result["data"] = data
            if isinstance(data, list):
                result["row_count"] = len(data)
                result["preview"] = f"JSON массив: {len(data)} элементов"
            else:
                result["preview"] = f"JSON объект с ключами: {', '.join(list(data.keys())[:5])}"

        else:
            lines = text.split("\n")
            result["data"] = lines
            result["row_count"] = len(lines)
            result["preview"] = f"Текст: {len(lines)} строк, {len(text)} символов"

    except Exception as e:
        result["preview"] = f"Ошибка парсинга: {e}"
        result["data"] = text[:5000]

    return result


def format_file_for_prompt(parsed: Dict[str, Any], max_chars: int = 4000) -> str:
    """Форматирует файл для промпта."""
    file_type = parsed["type"]
    data = parsed["data"]

    if file_type == "csv" and isinstance(data, list):
        # Для CSV берём первые N строк
        sample = data[:50]
        return json.dumps(sample, ensure_ascii=False, indent=2)[:max_chars]

    elif file_type == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)[:max_chars]

    else:
        if isinstance(data, list):
            return "\n".join(data[:100])[:max_chars]
        return str(data)[:max_chars]


# ========================== КОМАНДЫ ==========================

async def handle_compress_command(client: OpenRouterClient, history: List[Dict]):
    """Сжимает историю диалога."""
    if not history:
        await cl.Message(content="История пуста — сжимать нечего.").send()
        return []

    await cl.Message(content="Сжимаю историю диалога...").send()

    # Форматируем историю
    formatted = []
    for idx, item in enumerate(history, 1):
        role = "Пользователь" if item["role"] == "user" else "Ассистент"
        formatted.append(f"{idx}. {role}: {item['content'][:200]}")

    compression_prompt = (
        "Сделай краткую сводку диалога ниже в 5-7 предложений. "
        "Сохрани ключевые факты, вопросы и решения.\n\n"
        + "\n".join(formatted)
    )

    messages = [{"role": "user", "content": compression_prompt}]

    try:
        summary = await client.get_completion_text(messages, temperature=0.2)

        compressed = [{
            "role": "assistant",
            "content": f"[Сводка предыдущего диалога] {summary.strip()}"
        }]

        await cl.Message(
            content=f"История сжата!\n\n**Сводка:**\n{summary}"
        ).send()

        return compressed

    except Exception as e:
        await cl.Message(content=f"Ошибка сжатия: {e}").send()
        return history


async def handle_summary_command(usage_history: List[Dict]):
    """Выводит статистику токенов."""
    if not usage_history:
        await cl.Message(content="Пока нет данных по токенам.").send()
        return

    total = sum(item.get("total", 0) for item in usage_history)

    lines = [
        "**Статистика токенов:**\n",
        "| # | Сообщение | Токены |",
        "|---|-----------|--------|"
    ]

    for idx, item in enumerate(usage_history, 1):
        preview = item.get("message", "")[:30]
        tokens = item.get("total", 0)
        lines.append(f"| {idx} | {preview}... | {tokens} |")

    lines.append(f"\n**Всего:** {total} токенов")

    await cl.Message(content="\n".join(lines)).send()


# ========================== CHAINLIT HANDLERS ==========================

@cl.on_chat_start
async def on_chat_start():
    """Инициализация чата."""
    global RAG_INDEX

    # RAG инициализируется лениво при первом использовании
    cl.user_session.set("rag_initialized", False)

    # Инициализация клиента
    try:
        client = OpenRouterClient()
        cl.user_session.set("client", client)
    except Exception as e:
        await cl.Message(content=f"Ошибка OpenRouter: {e}").send()
        return

    # Инициализация сессии
    cl.user_session.set("history", [])
    cl.user_session.set("usage_history", [])
    cl.user_session.set("rag_enabled", True)
    cl.user_session.set("current_file", None)

    # Приветствие
    greeting = f"Привет, **{USER_NAME}**! " if USER_PROFILE else "Привет! "

    welcome = f"""{greeting}Я — **God Agent**, твой личный AI-помощник.

**Возможности:**
- Общение и помощь с любыми вопросами
- RAG
- Анализ файлов (CSV, JSON, LOG) — просто перетащи файл
- MCP
- Профиль пользователя

**Команды:**
- `/compress` — сжатие истории диалога
- `/summary` — статистика токенов
- `/rag on|off` — вкл/выкл RAG
- `/mcp` — инструменты MCP

Чем могу помочь?"""

    await cl.Message(content=welcome).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Обработка сообщений."""
    client = cl.user_session.get("client")
    if not client:
        await cl.Message(content="Клиент не инициализирован. Перезагрузите страницу.").send()
        return

    history = cl.user_session.get("history", [])
    usage_history = cl.user_session.get("usage_history", [])
    rag_enabled = cl.user_session.get("rag_enabled", True)

    user_text = message.content.strip()

    # Обработка файлов
    if message.elements:
        for element in message.elements:
            if hasattr(element, "path") and element.path:
                file_path = Path(element.path)
                if file_path.exists():
                    content = file_path.read_bytes()

                    if len(content) > MAX_FILE_SIZE_BYTES:
                        await cl.Message(
                            content=f"Файл слишком большой (>{MAX_FILE_SIZE_MB}MB)"
                        ).send()
                        return

                    parsed = parse_file_content(element.name, content)
                    cl.user_session.set("current_file", parsed)

                    await cl.Message(
                        content=f"Файл загружен: {parsed['preview']}\n\nЗадай вопрос по данным!"
                    ).send()
                    return

    # Обработка команд
    if user_text.startswith("/"):
        cmd_parts = user_text.split()
        cmd = cmd_parts[0].lower()

        if cmd == "/compress":
            new_history = await handle_compress_command(client, history)
            cl.user_session.set("history", new_history)
            return

        elif cmd == "/summary":
            await handle_summary_command(usage_history)
            return

        elif cmd == "/rag":
            if len(cmd_parts) > 1:
                arg = cmd_parts[1].lower()
                if arg == "on":
                    cl.user_session.set("rag_enabled", True)
                    await cl.Message(content="RAG включен").send()
                elif arg == "off":
                    cl.user_session.set("rag_enabled", False)
                    await cl.Message(content="RAG выключен").send()
            else:
                status = "включен" if rag_enabled else "выключен"
                await cl.Message(content=f"RAG сейчас {status}. Используй `/rag on` или `/rag off`").send()
            return

        elif cmd == "/mcp":
            await cl.Message(content="Получаю список MCP инструментов...").send()
            try:
                tools_info = await get_mcp_tools_info()
                await cl.Message(content=tools_info).send()
            except Exception as e:
                await cl.Message(content=f"Ошибка MCP: {e}").send()
            return

    # RAG поиск
    rag_context = ""
    rag_sources = []

    if rag_enabled:
        global RAG_INDEX
        # Ленивая инициализация RAG
        if RAG_INDEX is None:
            try:
                print("Инициализация RAG...")
                RAG_INDEX = SimpleRAG(
                    data_file="data/rag_example_cities_ru.txt",
                    index_dir="data/faiss_index"
                )
                await RAG_INDEX.initialize()
                print(f"RAG готов: {len(RAG_INDEX.documents)} документов")
            except Exception as e:
                print(f"RAG init error: {e}")
                RAG_INDEX = None

        if RAG_INDEX and RAG_INDEX._initialized:
            try:
                results = await RAG_INDEX.search(user_text, top_k=3, min_score=0.3)
                print(f"RAG: найдено {len(results)} результатов")
                if results:
                    rag_context = format_rag_context(results)
                    rag_sources = results
            except Exception as e:
                print(f"RAG search error: {e}")

    # Контекст файла
    file_context = ""
    current_file = cl.user_session.get("current_file")
    if current_file:
        file_data = format_file_for_prompt(current_file)
        file_context = f"\n\nАнализируемый файл ({current_file['preview']}):\n```\n{file_data}\n```"

    # Формируем промпт
    system_prompt = get_system_prompt(rag_context)
    if file_context:
        system_prompt += file_context

    messages = build_messages(user_text, history, system_prompt)

    # Отправляем запрос со streaming
    msg = cl.Message(content="")
    await msg.send()

    full_response = ""

    try:
        async for chunk in client.stream_completion(messages):
            full_response += chunk
            await msg.stream_token(chunk)

        # Добавляем источники RAG
        if rag_sources:
            sources = format_sources(rag_sources)
            await msg.stream_token(sources)
            full_response += sources

    except Exception as e:
        await msg.stream_token(f"\n\nОшибка: {e}")
        return

    # Сохраняем историю
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("history", history)

    # Сохраняем статистику (примерная)
    usage_history.append({
        "message": user_text[:50],
        "total": len(user_text) + len(full_response)  # Примерно
    })
    cl.user_session.set("usage_history", usage_history)


if __name__ == "__main__":
    print("Запустите: chainlit run app.py")
