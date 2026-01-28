"""MCP клиент для context7."""

import os
import httpx
from typing import Optional, Dict, Any


class MCPClient:
    """Клиент для работы с MCP серверами."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.endpoint = endpoint or os.getenv(
            "CONTEXT7_MCP_ENDPOINT",
            "https://mcp.context7.com/mcp"
        )
        self.api_key = api_key or os.getenv("CONTEXT7_API_KEY", "")
        self._initialized = False
        self._session_id: Optional[str] = None

    async def ensure_initialized(self):
        """Инициализирует сессию с MCP сервером."""
        if self._initialized:
            return

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "god-agent",
                            "version": "1.0.0"
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                }
            )
            response.raise_for_status()
            data = response.json()

            if "result" in data:
                self._initialized = True
                self._session_id = data.get("result", {}).get("sessionId")

    async def list_tools(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Получает список доступных инструментов."""
        await self.ensure_initialized()

        params = {}
        if cursor:
            params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": params
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                }
            )
            response.raise_for_status()
            data = response.json()

            return data.get("result", {"tools": []})


async def get_mcp_tools_info() -> str:
    """Получает информацию о доступных MCP инструментах."""
    endpoint = os.getenv("CONTEXT7_MCP_ENDPOINT", "https://mcp.context7.com/mcp")
    api_key = os.getenv("CONTEXT7_API_KEY", "")

    client = MCPClient(endpoint=endpoint, api_key=api_key)

    output = []

    try:
        output.append("=== MCP Инструменты (context7) ===\n")
        await client.ensure_initialized()

        all_tools = []
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            tools = page.get("tools") or []
            all_tools.extend(tools)
            cursor = page.get("nextCursor")
            if not cursor:
                break

        output.append(f"Доступные инструменты ({len(all_tools)}):")

        for tool in all_tools[:10]:  # Ограничиваем вывод
            output.append(f"\n  {tool.get('name', '(no name)')}")
            desc = tool.get('description', '')[:100]
            if desc:
                output.append(f"     {desc}...")

    except Exception as e:
        output.append(f"Ошибка подключения к MCP: {e}")

    return "\n".join(output)
