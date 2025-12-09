import asyncio
import json
import os
import time
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
        self.default_temperature = 0.3

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None
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
            "model": model if model is not None else self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_completion_text(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None
    ) -> str:
        """Получает текстовый ответ от модели."""
        result = await self.chat_completion(messages, temperature=temperature)
        return result["choices"][0]["message"]["content"]

    async def get_json_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Получает JSON-ответ от модели."""
        # Добавляем response_format для JSON
        result = await self.chat_completion(
            messages,
            response_format={"type": "json_object"},
            temperature=temperature
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

    async def compare_models(
        self,
        messages: List[Dict[str, str]],
        models: List[str],
        temperature: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет запросы к нескольким моделям параллельно через asyncio.gather().

        Args:
            messages: Список сообщений для отправки всем моделям
            models: Список имён моделей для сравнения
            temperature: Температура для генерации (опционально)

        Returns:
            Список словарей с результатами для каждой модели:
            {
                "model": str,
                "response": str,
                "execution_time": float,
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int,
                "cost_usd": Optional[float],
                "error": Optional[str]
            }
        """

        async def query_single_model(model: str) -> Dict[str, Any]:
            """Запрашивает одну модель с замером времени и обработкой ошибок."""
            result = {
                "model": model,
                "response": None,
                "execution_time": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": None,
                "error": None
            }

            try:
                start_time = time.time()

                # Выполняем запрос с конкретной моделью
                api_response = await self.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    model=model
                )

                end_time = time.time()
                result["execution_time"] = round(end_time - start_time, 2)

                # Извлекаем ответ
                result["response"] = api_response["choices"][0]["message"]["content"]

                # Извлекаем usage (если есть)
                usage = api_response.get("usage", {})
                result["prompt_tokens"] = usage.get("prompt_tokens", 0)
                result["completion_tokens"] = usage.get("completion_tokens", 0)
                result["total_tokens"] = usage.get("total_tokens", 0)

                # Извлекаем стоимость (если есть в data.cost)
                data = api_response.get("data", {})
                if "cost" in data:
                    result["cost_usd"] = data["cost"]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    result["error"] = "Rate limit exceeded"
                elif e.response.status_code == 404:
                    result["error"] = "Model not found"
                else:
                    result["error"] = f"HTTP {e.response.status_code}"
            except httpx.TimeoutException:
                result["error"] = "Request timeout"
            except Exception as e:
                result["error"] = str(e)

            return result

        # Параллельное выполнение запросов
        tasks = [query_single_model(model) for model in models]
        results = await asyncio.gather(*tasks)

        return results


def build_messages(user_input: str, history: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
    """
    Создаёт список сообщений для диалога с агентом.

    Args:
        user_input: Текущее сообщение пользователя
        history: История предыдущих сообщений
        system_prompt: System prompt для определения роли агента

    Returns:
        Список сообщений для API
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Добавляем историю
    messages.extend(history)

    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": user_input})

    return messages
