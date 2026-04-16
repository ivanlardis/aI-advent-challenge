#!/usr/bin/env python3
"""
God Agent - Личный AI-помощник
Chainlit + OpenRouter (Claude 3.5 Sonnet)
"""

import os
import re
from pathlib import Path
from typing import List, Dict

import chainlit as cl
from dotenv import load_dotenv

from lib.openrouter_client import OpenRouterClient, build_messages

# Загружаем переменные окружения
load_dotenv()


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

def get_system_prompt() -> str:
    """Формирует system prompt с учетом профиля."""
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

    return base_prompt


# ========================== КОМАНДЫ ==========================

async def handle_compress_command(client: OpenRouterClient, history: List[Dict]):
    """Сжимает историю диалога."""
    if not history:
        await cl.Message(content="История пуста — сжимать нечего.").send()
        return []

    await cl.Message(content="Сжимаю историю диалога...").send()

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
    try:
        client = OpenRouterClient()
        cl.user_session.set("client", client)
    except Exception as e:
        await cl.Message(content=f"Ошибка OpenRouter: {e}").send()
        return

    cl.user_session.set("history", [])
    cl.user_session.set("usage_history", [])

    greeting = f"Привет, **{USER_NAME}**! " if USER_PROFILE else "Привет! "

    welcome = f"""{greeting}Я — **God Agent**, твой личный AI-помощник.

**Команды:**
- `/compress` — сжатие истории диалога
- `/summary` — статистика токенов

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

    user_text = message.content.strip()

    # Обработка команд
    if user_text.startswith("/"):
        cmd = user_text.split()[0].lower()

        if cmd == "/compress":
            new_history = await handle_compress_command(client, history)
            cl.user_session.set("history", new_history)
            return

        elif cmd == "/summary":
            await handle_summary_command(usage_history)
            return

    # Формируем промпт и отправляем запрос
    system_prompt = get_system_prompt()
    messages = build_messages(user_text, history, system_prompt)

    msg = cl.Message(content="")
    await msg.send()

    full_response = ""

    try:
        async for chunk in client.stream_completion(messages):
            full_response += chunk
            await msg.stream_token(chunk)
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
        "total": len(user_text) + len(full_response)
    })
    cl.user_session.set("usage_history", usage_history)


if __name__ == "__main__":
    print("Запустите: chainlit run app.py")
