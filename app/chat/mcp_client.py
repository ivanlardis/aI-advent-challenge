import asyncio

import httpx

class MCPClient:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.client = httpx.AsyncClient()
        self.request_id = 0

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "CONTEXT7_API_KEY": self.api_key
        }

    async def list_tools(self) -> list[dict]:
        """Получить список доступных инструментов"""
        self.request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list"
        }

        result = await self._send_request(payload)
        return result.get("result", {}).get("tools", [])

    async def _send_request(self, payload: dict) -> dict:
        """Отправить запрос"""
        try:
            response = await self.client.post(
                self.server_url,
                json=payload,
                headers=self._get_headers()
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.text}")
                return {}

        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def close(self):
        await self.client.aclose()


async def main():
    api_key = "ctx7sk-70ea9a0d-53d5-4055-94b5-29235d60cd08"
    client = MCPClient("https://mcp.context7.com/mcp", api_key)


    try:
        # Получаем список инструментов
        print("=== Получаем список инструментов ===\n")
        tools = await client.list_tools()

        print(f"\nДоступные инструменты ({len(tools)}):")
        for tool in tools:
            print(f"\n  📌 {tool['name']}")
            print(f"     Заголовок: {tool.get('title', '')}")
            print(f"     Описание: {tool.get('description', '')[:200]}...")

            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                props = schema.get('properties', {})
                required = schema.get('required', [])

                print(f"     Параметры:")
                for prop_name, prop_schema in props.items():
                    req_marker = "✓" if prop_name in required else "○"
                    print(f"       {req_marker} {prop_name}: {prop_schema.get('description', '')[:100]}")

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())