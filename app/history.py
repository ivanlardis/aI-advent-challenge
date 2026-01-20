from datetime import datetime
from typing import List, Dict


class SessionHistory:
    """Менеджер сессионной истории сообщений."""

    def __init__(self):
        self.messages: List[Dict] = []

    def add_user_message(self, content: str) -> None:
        """Добавляет сообщение пользователя в историю.

        Args:
            content: Текст сообщения
        """
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, content: str) -> None:
        """Добавляет ответ ассистента в историю.

        Args:
            content: Текст ответа
        """
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_for_api(self) -> List[Dict]:
        """Возвращает историю в формате Ollama API.

        Returns:
            Список сообщений с полями role и content
        """
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages
        ]

    def clear(self) -> None:
        """Очищает историю сообщений."""
        self.messages.clear()
