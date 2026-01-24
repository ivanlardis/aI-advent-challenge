#!/usr/bin/env python3
"""
Прямой тест запроса к Ollama
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import requests

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:0.5b"

def call_ollama(prompt: str) -> str:
    """Отправляет запрос к Ollama и возвращает ответ"""
    try:
        print(f"\n📤 ПРОМПТ ДЛЯ OLLAMA:")
        print("="*60)
        print(prompt[:500])  # Первые 500 символов
        if len(prompt) > 500:
            print(f"... (всего {len(prompt)} символов)")
        print("="*60)

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "Не удалось получить ответ")
            print(f"\n📥 ОТВЕТ ОТ OLLAMA:")
            print("="*60)
            print(answer)
            print("="*60)
            return answer
        else:
            error = f"Ошибка Ollama API: {response.status_code}"
            print(f"❌ {error}")
            return error

    except requests.exceptions.Timeout:
        error = "⏱️ Запрос превысил время ожидания (60 сек)"
        print(f"❌ {error}")
        return error
    except Exception as e:
        error = f"❌ Ошибка при обращении к Ollama: {str(e)}"
        print(f"❌ {error}")
        return error


# Тестовый промпт с лог-данными
test_prompt = """Ты — аналитик данных. Отвечай на вопросы пользователя на основе предоставленных данных.
Будь точным и конкретным. Если не можешь ответить на вопрос — честно скажи об этом.
Отвечай на том же языке, на котором задан вопрос.

ДАННЫЕ:
Лог-файл (10 строк):

2024-01-20 10:00:00 INFO Application started
2024-01-20 10:00:05 ERROR Failed to connect to DB: Connection timeout
2024-01-20 10:05:01 ERROR Failed to connect to DB: Connection timeout
2024-01-20 10:05:10 INFO Retrying DB connection
2024-01-20 10:05:15 INFO DB connection established
2024-01-20 10:10:00 WARN High memory usage: 85%
2024-01-20 10:15:00 INFO User login: user_id=2
2024-01-20 10:20:00 ERROR API request failed: 404 Not Found
2024-01-20 10:25:00 WARN Cache miss for key: user_session_123

ЗАДАЧА:
Проанализируй данные выше и ответь на вопрос пользователя.

ВОПРОС:
Сколько ошибок ERROR в логе?"""

if __name__ == "__main__":
    print("🧪 ПРЯМОЙ ТЕСТ OLLAMA")
    print("="*60)

    answer = call_ollama(test_prompt)

    print("\n📊 ИТОГ:")
    print(f"Получен ответ длиной: {len(answer)} символов")
