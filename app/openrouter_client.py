import json
import os
from typing import List, Dict, Any, Optional

import httpx


class OpenRouterClient:
    """HTTP-клиент для работы с OpenRouter API."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("Установите OPENROUTER_API_KEY, чтобы обратиться к OpenRouter.")

        self.model = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.temperature = 0.3

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Отправляет запрос к OpenRouter API и возвращает ответ.

        Args:
            messages: Список сообщений в формате [{"role": "user"|"assistant"|"system", "content": "..."}]
            response_format: Опциональный формат ответа (например, {"type": "json_object"})

        Returns:
            Словарь с ответом от API
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_completion_text(self, messages: List[Dict[str, str]]) -> str:
        """Получает текстовый ответ от модели."""
        result = await self.chat_completion(messages)
        return result["choices"][0]["message"]["content"]

    async def get_json_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Получает JSON-ответ от модели."""
        # Добавляем response_format для JSON
        result = await self.chat_completion(
            messages,
            response_format={"type": "json_object"}
        )
        content = result["choices"][0]["message"]["content"]

        # Парсим JSON из ответа
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Если не удалось распарсить, пытаемся извлечь JSON из текста
            # Ищем первую открывающую фигурную скобку
            json_start = content.find('{')
            if json_start != -1:
                # Ищем последнюю закрывающую фигурную скобку
                json_end = content.rfind('}')
                if json_end != -1:
                    json_str = content[json_start:json_end + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Не удалось распарсить JSON из ответа: {content}") from e

            raise ValueError(f"Не удалось найти JSON в ответе: {content}")


def build_nutrition_messages(user_input: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Создаёт список сообщений для диалога с нутрициологом.

    Args:
        user_input: Текущее сообщение пользователя
        history: История предыдущих сообщений

    Returns:
        Список сообщений для API
    """
    system_prompt = (
        "Ты — опытный нутрициолог, который собирает данные о пользователе для расчёта БЖУ (белки, жиры, углеводы).\n\n"
        "КРИТИЧЕСКИ ВАЖНО: Ты ОБЯЗАН возвращать ТОЛЬКО валидный JSON. Никакого текста до или после JSON.\n\n"
        "Твоя задача:\n"
        "1. Задать пользователю РОВНО 5 вопросов (по одному за раз):\n"
        "   - Ваш рост (в см)?\n"
        "   - Ваш вес (в кг)?\n"
        "   - Ваш возраст (в годах)?\n"
        "   - Ваш пол (мужской/женский)?\n"
        "   - Ваш уровень физической активности (минимальная/низкая/средняя/высокая/очень высокая)?\n"
        "2. Собирать ответы пользователя и запоминать их в collected_info\n"
        "3. Когда все 5 вопросов заданы и получены ответы — установи is_complete=true и рассчитай БЖУ\n\n"
        "ФОРМАТ ОТВЕТА (только валидный JSON):\n"
        "{\n"
        '  "is_complete": false,\n'
        '  "message": "ваш вопрос или сообщение",\n'
        '  "collected_info": {\n'
        '    "height": null,\n'
        '    "weight": null,\n'
        '    "age": null,\n'
        '    "gender": null,\n'
        '    "activity_level": null\n'
        "  },\n"
        '  "final_document": null\n'
        "}\n\n"
        "Правила:\n"
        "- Задавай вопросы СТРОГО по порядку, по одному за раз\n"
        "- Не переходи к следующему вопросу, пока не получишь ответ на текущий\n"
        "- Когда собраны все 5 ответов — рассчитай BMR, калорийность и БЖУ\n"
        "- ВСЕГДА возвращай ТОЛЬКО JSON, без дополнительного текста"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Добавляем историю
    messages.extend(history)

    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": user_input})

    return messages
