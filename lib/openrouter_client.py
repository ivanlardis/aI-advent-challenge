"""OpenRouter API клиент для God Agent."""

import os
from typing import List, Dict, Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class OpenRouterClient:
    """Клиент для работы с OpenRouter API."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY не установлен")

        self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.3,
            streaming=True,
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Отправляет запрос и возвращает полный ответ."""
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        response = await self.llm.ainvoke(lc_messages)

        return {
            "choices": [{"message": {"content": response.content}}],
            "usage": getattr(response, "usage_metadata", {})
        }

    async def get_completion_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3
    ) -> str:
        """Возвращает только текст ответа."""
        result = await self.chat_completion(messages, temperature)
        return result["choices"][0]["message"]["content"]

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3
    ):
        """Генератор для streaming ответов."""
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        async for chunk in self.llm.astream(lc_messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content


def build_messages(
    user_input: str,
    history: List[Dict[str, str]],
    system_prompt: str = ""
) -> List[Dict[str, str]]:
    """Собирает список сообщений для API."""
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for item in history:
        messages.append(item)

    messages.append({"role": "user", "content": user_input})

    return messages
