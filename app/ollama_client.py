import requests
import json
from typing import List, Dict, Iterator


class OllamaClient:
    """HTTP клиент для Ollama API."""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.session = requests.Session()

    def list_models(self) -> List[Dict]:
        """Возвращает список доступных моделей.

        Returns:
            Список словарей с информацией о моделях

        Raises:
            requests.RequestException: При ошибке подключения
        """
        response = self.session.get(f"{self.host}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])

    def generate_stream(self, messages: List[Dict], model: str) -> Iterator[Dict]:
        """Генерирует ответ в streaming режиме.

        Args:
            messages: История сообщений в формате Ollama API
            model: Название модели

        Yields:
            Чанки ответа от Ollama API

        Raises:
            requests.RequestException: При ошибке генерации
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        response = self.session.post(
            f"{self.host}/api/chat",
            json=payload,
            stream=True
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                yield json.loads(line)
