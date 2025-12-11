import json
import os
import time
import logging
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


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

        start_time = time.time()
        logger.info(
            "Sending chat completion: model=%s messages=%d temp=%s",
            payload["model"],
            len(messages),
            payload["temperature"],
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                logger.warning(
                    "OpenRouter error: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
            response.raise_for_status()
            elapsed = round(time.time() - start_time, 2)
            data = response.json()
            usage = data.get("usage", {})
            logger.info(
                "Received response: model=%s time=%ss prompt_tokens=%s completion_tokens=%s total=%s",
                payload["model"],
                elapsed,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )
            return data

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
        temperature: Optional[float] = None,
        return_usage: bool = False
    ) -> Any:
        """Получает JSON-ответ от модели.

        Если `return_usage=True`, возвращает кортеж (parsed_json, usage_dict).
        """
        # Добавляем response_format для JSON
        result = await self.chat_completion(
            messages,
            response_format={"type": "json_object"},
            temperature=temperature
        )
        usage = result.get("usage", {})
        content = result["choices"][0]["message"]["content"]

        # Парсим JSON из ответа
        try:
            parsed = json.loads(content)
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
                        parsed = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Не удалось распарсить JSON из ответа: {content}") from e

            raise ValueError(f"Не удалось найти JSON в ответе: {content}")

        if return_usage:
            return parsed, usage

        return parsed

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
    messages: List[Dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Добавляем историю
    messages.extend(history)

    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": user_input})

    return messages
