import json
import logging
import os
from itertools import count
from typing import Any, Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)


class MCPError(RuntimeError):
    pass


class MCPRemoteError(MCPError):
    def __init__(self, error_obj: Dict[str, Any]) -> None:
        super().__init__(f"MCP JSON-RPC error: {error_obj!r}")
        self.error_obj = error_obj


JsonRpcMsg = Dict[str, Any]
JsonRpcBatch = List[JsonRpcMsg]
JsonRpcBody = Union[JsonRpcMsg, JsonRpcBatch]


class MCPClient:
    """
    MCP client over Streamable HTTP transport.

    Endpoint example: http://localhost:1221/mcp
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        host_header: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or os.getenv("MCP_ENDPOINT", "http://localhost:1221/mcp")

        # Стартуем с "самого свежего" для клиента, но сервер может вернуть другой.
        self._protocol_version: str = os.getenv("MCP_PROTOCOL_VERSION", "2025-06-18")
        self._session_id: Optional[str] = None

        self._client_name = os.getenv("MCP_CLIENT_NAME", "kododel")
        self._client_version = os.getenv("MCP_CLIENT_VERSION", "1.0.0")

        self._id_seq = count(1)
        self._initialized = False

        self._api_key = api_key or os.getenv("MCP_API_KEY") or os.getenv("CONTEXT7_API_KEY")
        self._host_header = host_header or os.getenv("MCP_HOST_HEADER")

    async def ensure_initialized(self, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._initialized:
            return {
                "ok": True,
                "protocolVersion": self._protocol_version,
                "sessionId": self._session_id,
            }

        result = await self.initialize(capabilities=capabilities)
        self._initialized = True
        return result

    def _headers(self, accept: str) -> Dict[str, str]:
        h = {
            "Accept": accept,
            "Content-Type": "application/json",
        }
        # После init (и вообще по возможности) прокидываем версию протокола
        if self._protocol_version:
            h["MCP-Protocol-Version"] = self._protocol_version
        # Если сервер выдал session id — обязаны слать дальше
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        if self._api_key:
            h["CONTEXT7_API_KEY"] = self._api_key
        if self._host_header:
            h["Host"] = self._host_header
        return h

    async def _post_jsonrpc(self, body: JsonRpcBody, timeout: float = 60.0) -> Any:
        """
        POST JSON-RPC. Сервер может ответить либо application/json, либо text/event-stream (SSE).
        Возвращает распарсенный JSON (dict или list) *ответа*.
        """
        accept = "application/json, text/event-stream"

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # Важно: чтобы корректно обработать SSE-ответ, используем stream()
            async with client.stream(
                    "POST",
                    self.endpoint,
                    headers=self._headers(accept),
                    json=body,
            ) as resp:
                resp.raise_for_status()

                ctype = (resp.headers.get("Content-Type") or "").lower()
                # Session id может прийти в заголовке init-ответа
                if "mcp-session-id" in (k.lower() for k in resp.headers.keys()):
                    # В httpx заголовки case-insensitive, но значение достаем по "правильному" ключу тоже ок
                    self._session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")

                if ctype.startswith("application/json"):
                    content = await resp.aread()
                    if not content or content.strip() == b'':
                        return None
                    return json.loads(content)

                if ctype.startswith("text/event-stream"):
                    # SSE: читаем data: ... пока не получим JSON-RPC response(ы)
                    return await self._read_sse_as_json(resp)

                # Неожиданный тип - может быть пустой ответ для notification
                text = await resp.aread()
                if not text or text.strip() == b'':
                    return None
                raise MCPError(f"Unexpected Content-Type from MCP server: {ctype}. Body={text[:200]!r}")

    async def _read_sse_as_json(self, resp: httpx.Response) -> Any:
        """
        Парсим SSE поток. MCP обычно шлет JSON-RPC сообщения как `data: { ...json... }`.
        Возвращаем первый распарсенный JSON (dict или list), который выглядит как JSON-RPC response/batch.
        """
        data_lines: List[str] = []

        async for line in resp.aiter_lines():
            if not line:
                # пустая строка = конец события
                if data_lines:
                    payload = "\n".join(data_lines).strip()
                    data_lines = []
                    # иногда могут быть keep-alive/прочее
                    if not payload:
                        continue
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        logger.debug("Non-JSON SSE data payload: %r", payload[:200])
                        continue
                    # MCP может прислать batch (list) или одиночный dict
                    return obj
                continue

            if line.startswith(":"):
                # comment / keep-alive
                continue

            if line.startswith("data:"):
                data_lines.append(line[len("data:") :].lstrip())
                continue

            # event:, id: и т.п. — игнорируем
            continue

        raise MCPError("SSE stream closed before any JSON payload was received.")

    @staticmethod
    def _extract_response_for_id(obj: Any, req_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        if isinstance(obj, dict):
            return obj if obj.get("id") == req_id else None
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict) and item.get("id") == req_id:
                    return item
        return None

    async def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        req_id = next(self._id_seq)
        body: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            body["params"] = params

        obj = await self._post_jsonrpc(body)

        msg = self._extract_response_for_id(obj, req_id)
        if not msg:
            # Если сервер вернул не batch/не тот id — попробуем трактовать как одиночный ответ
            if isinstance(obj, dict) and ("result" in obj or "error" in obj):
                msg = obj
            else:
                raise MCPError(f"Did not receive JSON-RPC response for id={req_id}. Got: {obj!r}")

        if "error" in msg:
            raise MCPRemoteError(msg["error"])

        return msg.get("result")

    async def _notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        body: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params

        # Notification может вернуть 204/пусто или json/sse — не важно, просто убедимся что статус ок
        _ = await self._post_jsonrpc(body)

    async def initialize(self, capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        1) initialize request
        2) notifications/initialized
        """
        capabilities = capabilities or {}
        result = await self._request(
            "initialize",
            {
                "protocolVersion": self._protocol_version,
                "capabilities": capabilities,
                "clientInfo": {"name": self._client_name, "version": self._client_version},
            },
        )

        # Сервер может "снизить" версию; дальше используем согласованную
        if isinstance(result, dict) and result.get("protocolVersion"):
            self._protocol_version = str(result["protocolVersion"])

        await self._notify("notifications/initialized")
        logger.info("MCP initialized: endpoint=%s protocol=%s session=%s", self.endpoint, self._protocol_version, self._session_id)
        return result

    async def list_tools(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        return await self._request("tools/list", params)

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
