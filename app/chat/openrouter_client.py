import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Простой HTTP-клиент для OpenRouter chat completions."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("Не задан OPENROUTER_API_KEY.")

        self.model = os.getenv("OPENROUTER_MODEL")
        if not self.model:
            raise RuntimeError("Не задан OPENROUTER_MODEL.")

        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        usage = data.get("usage", {}) or {}
        logger.info(
            "OpenRouter: model=%s prompt=%s completion=%s total=%s",
            payload["model"],
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )
        return data


def build_messages(
    user_input: str,
    history: List[Dict[str, str]],
    system_prompt: str = "",
) -> List[Dict[str, str]]:
    """Формирует список сообщений для API."""
    messages: List[Dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages
