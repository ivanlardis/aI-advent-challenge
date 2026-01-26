#!/usr/bin/env python3
"""
Личный AI-помощник
Работает с локальной LLM через Ollama
"""

import os
import re
import time
from pathlib import Path

import chainlit as cl
import requests


# ========================== КОНФИГУРАЦИЯ ==========================

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"


# ========================== ПЕРСОНАЛИЗАЦИЯ ==========================

def load_profile(profile_path: str = "config/profile.md") -> str:
    """Загружает профиль пользователя из MD файла.

    Args:
        profile_path: Путь к файлу профиля относительно app.py

    Returns:
        Содержимое профиля как строку, или пустую строку если файл не найден
    """
    current_dir = Path(__file__).parent
    full_path = current_dir / profile_path

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"✅ Профиль загружен: {full_path}")
            return content
    except FileNotFoundError:
        print(f"⚠️  Профиль не найден: {full_path}")
        print(f"   Создайте профиль на основе шаблона: {profile_path}.example.md")
        return ""
    except Exception as e:
        print(f"⚠️  Ошибка загрузки профиля: {e}")
        return ""


def extract_name(profile_content: str) -> str:
    """Извлекает имя пользователя из профиля.

    Args:
        profile_content: Содержимое профиля

    Returns:
        Имя пользователя или "Пользователь" если не найдено
    """
    match = re.search(r'- \*\*Имя:\*\*\s*(.+)', profile_content)
    if match:
        return match.group(1).strip()
    return "Пользователь"


# Загрузка профиля при старте приложения
USER_PROFILE = load_profile()
USER_NAME = extract_name(USER_PROFILE)


# ========================== OLLAMA ==========================

def check_ollama_health() -> bool:
    """Проверяет доступность Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """Отправляет запрос к Ollama и возвращает ответ"""
    try:
        # Формируем полный промпт
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "Не удалось получить ответ")
        else:
            return f"Ошибка Ollama API: {response.status_code}"

    except requests.exceptions.Timeout:
        return "⏱️ Запрос превысил время ожидания"
    except Exception as e:
        return f"❌ Ошибка при обращении к Ollama: {str(e)}"


# ========================== SYSTEM PROMPT ==========================

def get_system_prompt() -> str:
    """Формирует system prompt с учетом профиля пользователя"""

    base_prompt = """Ты — личный AI-помощник. Твоя задача — помогать пользователю достигать его целей, поддерживать и мотивировать.

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

Учитывай эту информацию при общении. Обращайся к пользователю по имени: {USER_NAME}."""

    return base_prompt


# ========================== CHAINLIT HANDLERS ==========================

@cl.on_chat_start
async def start():
    """Инициализация чата"""

    # Проверяем Ollama
    if not check_ollama_health():
        error_msg = """❌ **Ollama недоступна!**

Пожалуйста, запустите Ollama:
```bash
ollama serve
```

Затем перезагрузите страницу."""

        await cl.Message(content=error_msg).send()
        return

    # Персонализированное приветствие
    if USER_PROFILE:
        greeting = f"👋 Привет, **{USER_NAME}**! "
    else:
        greeting = "👋 Привет! "

    welcome_msg = f"""{greeting}Я — твой личный AI-помощник.

Я здесь, чтобы помочь тебе достигать целей и поддержать на пути к ним.

**Что я могу:**
- 💬 Общаться и поддерживать
- 🎯 Помогать с целями (триатлон, вес, проекты)
- 💪 Мотивировать и напоминать о важном
- 📝 Отвечать на вопросы

**Как общаться:**
- Просто пиши мне как другу
- Задавай вопросы о своих целях
- Делись прогрессом и трудностями
- Проси советы или мотивацию

"""

    if not USER_PROFILE:
        welcome_msg += "💡 *Создай `config/profile.md` для персонализации (используй `config/profile.example.md` как шаблон).*\n\n"

    await cl.Message(content=welcome_msg).send()


@cl.on_message
async def main(message: cl.Message):
    """Обработка сообщений пользователя"""

    # Формируем system prompt
    system_prompt = get_system_prompt()

    # Показываем что думаем
    msg = cl.Message(content="")
    await msg.send()

    # Отправляем запрос в Ollama
    response = call_ollama(message.content, system_prompt)

    # Отправляем ответ
    await msg.stream_token(response)
