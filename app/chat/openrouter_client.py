import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from app.chat.mcp_client import MCPClient
logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Простой HTTP-клиент для OpenRouter chat completions (+ MCP tools proxy)."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("Не задан OPENROUTER_API_KEY.")

        self.model = os.getenv("OPENROUTER_MODEL")
        if not self.model:
            raise RuntimeError("Не задан OPENROUTER_MODEL.")

        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        # MCP включаем всегда (endpoint по умолчанию localhost), но используем только если явно попросили use_mcp=True
        self.mcp = MCPClient()
        self._mcp_tools_cache: Optional[List[Dict[str, Any]]] = None

    async def _fetch_mcp_tools_as_openai_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        if self._mcp_tools_cache is not None and not force_refresh:
            return self._mcp_tools_cache

        await self.mcp.ensure_initialized()

        # Собираем все страницы tools/list
        tools: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            page = await self.mcp.list_tools(cursor=cursor)
            page_tools = page.get("tools", []) or []
            tools.extend(page_tools)
            cursor = page.get("nextCursor")
            if not cursor:
                break

        # MCP tool -> OpenAI tool schema
        openai_tools: List[Dict[str, Any]] = []
        for t in tools:
            name = t.get("name")
            if not name:
                continue
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": t.get("description") or "",
                        "parameters": t.get("inputSchema") or {"type": "object", "properties": {}},
                    },
                }
            )

        self._mcp_tools_cache = openai_tools
        logger.info("MCP tools loaded: %d", len(openai_tools))
        return openai_tools

    async def _or_post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
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
            payload.get("model"),
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )
        return data

    async def chat_completion(
            self,
            messages: List[Dict[str, Any]],
            temperature: Optional[float] = None,
            model: Optional[str] = None,
            *,
            use_mcp_tools: bool = True,
            max_tool_rounds: int = 8,
            mcp_force_refresh_tools: bool = False,
    ) -> Dict[str, Any]:
        """
        Если use_mcp_tools=True:
          - подтягиваем tools из MCP
          - отправляем их в OpenRouter
          - если модель запросит tool_calls, исполняем через MCP и продолжаем диалог
        Возвращаем ПОСЛЕДНИЙ ответ OpenRouter (как есть).
        """
        active_model = model or self.model
        working_messages: List[Dict[str, Any]] = list(messages)

        tools: Optional[List[Dict[str, Any]]] = None
        if use_mcp_tools:
            try:
                tools = await self._fetch_mcp_tools_as_openai_tools(force_refresh=mcp_force_refresh_tools)
            except Exception as exc:  # guard if MCP is unreachable
                logger.warning("MCP tools unavailable, falling back to pure chat: %s", exc)
                tools = None

        last_data: Optional[Dict[str, Any]] = None

        for round_idx in range(max_tool_rounds):
            payload: Dict[str, Any] = {
                "model": active_model,
                "messages": working_messages,
            }
            if temperature is not None:
                payload["temperature"] = temperature

            if tools is not None:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            data = await self._or_post(payload)
            last_data = data

            choice0 = (data.get("choices") or [{}])[0]
            msg = choice0.get("message") or {}

            tool_calls = msg.get("tool_calls") or []
            # Если нет tool_calls — это финал
            if not tool_calls:
                return data

            # Добавляем assistant message с tool_calls в историю как есть
            working_messages.append(
                {
                    "role": "assistant",
                    "content": msg.get("content"),
                    "tool_calls": tool_calls,
                }
            )

            # Выполняем каждый tool_call через MCP и добавляем tool messages
            for tc in tool_calls:
                tc_id = tc.get("id")
                fn = (tc.get("function") or {})
                name = fn.get("name")
                raw_args = fn.get("arguments") or "{}"

                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    # если модель вернула невалидный JSON, прокинем как строку
                    args = {"_raw": raw_args}

                try:
                    result = await self.mcp.call_tool(name=name, arguments=args)
                    content = json.dumps(result, ensure_ascii=False)
                except Exception as e:
                    # важно: инструмент может фейлиться, но LLM должна увидеть ошибку
                    content = json.dumps({"error": str(e), "tool": name, "arguments": args}, ensure_ascii=False)

                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": content,
                    }
                )

        # Если дошли сюда — уткнулись в лимит раундов, возвращаем последний ответ (с tool_calls)
        return last_data or {"choices": []}


def build_messages(
        user_input: str,
        history: List[Dict[str, Any]],
        system_prompt: str = "",
) -> List[Dict[str, Any]]:
    """Формирует список сообщений для API."""
    messages: List[Dict[str, Any]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages
