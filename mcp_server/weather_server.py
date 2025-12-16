from typing import Any
import contextlib

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("time", stateless_http=True, json_response=True)
WORLD_TIME_API = "http://worldtimeapi.org/api"

async def _fetch_time_endpoint(path: str) -> dict[str, Any] | None:
    url = f"{WORLD_TIME_API}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.json()}
        except Exception:
            return None

@mcp.tool()
async def get_current_time(timezone: str = "Etc/UTC") -> str:
    payload = await _fetch_time_endpoint(f"/timezone/{timezone}")
    if not payload:
        return "Не удалось получить время, попробуйте ещё раз позже."

    error = payload.get("error")
    if error:
        detail = error.get("detail") or error.get("message") or "неизвестная ошибка"
        return f"Ошибка получения времени: {detail}"

    datetime = payload.get("datetime")
    abbreviation = payload.get("abbreviation", "")
    utc_offset = payload.get("utc_offset", "")
    return f"{timezone}: {datetime} ({abbreviation} UTC{utc_offset})"

@mcp.tool()
async def list_timezones() -> str:
    payload = await _fetch_time_endpoint("/timezone")
    if not payload:
        return "Не удалось получить список часовых поясов."
    if isinstance(payload, dict) and payload.get("error"):
        return f"Ошибка списка: {payload['error'].get('detail')}"
    if isinstance(payload, list):
        return "\n".join(payload)
    return "Неожиданный формат данных."

# ВАЖНО: session_manager должен быть запущен, если вы хостите через ASGI
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield

# ASGI app для uvicorn
async def health(request):
    return JSONResponse({"status": "ok"})

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
