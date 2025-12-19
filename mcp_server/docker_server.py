import contextlib
import logging
from typing import Any

import docker
from docker.errors import DockerException, NotFound, APIError
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.fastmcp import FastMCP

# Конфигурация
mcp = FastMCP("docker", stateless_http=True, json_response=True)

logger = logging.getLogger(__name__)


def get_docker_client():
    """Получает Docker клиент через Unix socket."""
    try:
        return docker.from_env()
    except DockerException as e:
        logger.error(f"Failed to connect to Docker: {e}")
        raise


@mcp.tool()
async def list_containers(all: bool = False) -> dict[str, Any]:
    """
    Возвращает список Docker контейнеров.

    Args:
        all: Если True - показывает все контейнеры (включая остановленные),
             если False - только работающие

    Returns:
        {
            "containers": [
                {
                    "id": str,
                    "name": str,
                    "status": str,  # running, exited, etc.
                    "image": str,
                    "created": str
                }
            ],
            "count": int
        }
    """
    try:
        client = get_docker_client()
        containers = client.containers.list(all=all)

        result = []
        for container in containers:
            result.append({
                "id": container.short_id,
                "full_id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "created": container.attrs.get("Created", "unknown")
            })

        return {
            "containers": result,
            "count": len(result)
        }
    except DockerException as e:
        return {"error": f"Docker error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


@mcp.tool()
async def start_container(container: str) -> dict[str, Any]:
    """
    Запускает остановленный контейнер.

    Args:
        container: Имя или ID контейнера

    Returns:
        {"success": bool, "message": str, "container": str, "status": str}
    """
    try:
        client = get_docker_client()
        cont = client.containers.get(container)

        # Проверка статуса
        if cont.status == "running":
            return {
                "success": False,
                "message": f"Контейнер '{container}' уже запущен",
                "container": cont.name,
                "status": cont.status
            }

        cont.start()
        cont.reload()  # Обновляем статус

        return {
            "success": True,
            "message": f"Контейнер '{container}' успешно запущен",
            "container": cont.name,
            "status": cont.status
        }
    except NotFound:
        return {
            "success": False,
            "error": f"Контейнер '{container}' не найден"
        }
    except APIError as e:
        return {
            "success": False,
            "error": f"Docker API error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@mcp.tool()
async def stop_container(container: str, timeout: int = 10) -> dict[str, Any]:
    """
    Останавливает работающий контейнер.

    Args:
        container: Имя или ID контейнера
        timeout: Тайм-аут в секундах перед принудительным завершением (default: 10)

    Returns:
        {"success": bool, "message": str, "container": str, "status": str}
    """
    try:
        client = get_docker_client()
        cont = client.containers.get(container)

        # Проверка статуса
        if cont.status != "running":
            return {
                "success": False,
                "message": f"Контейнер '{container}' не запущен (статус: {cont.status})",
                "container": cont.name,
                "status": cont.status
            }

        cont.stop(timeout=timeout)
        cont.reload()  # Обновляем статус

        return {
            "success": True,
            "message": f"Контейнер '{container}' успешно остановлен",
            "container": cont.name,
            "status": cont.status
        }
    except NotFound:
        return {
            "success": False,
            "error": f"Контейнер '{container}' не найден"
        }
    except APIError as e:
        return {
            "success": False,
            "error": f"Docker API error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@mcp.tool()
async def get_container_logs(
    container: str,
    tail: int = 100,
    timestamps: bool = False
) -> dict[str, Any]:
    """
    Получает логи контейнера.

    Args:
        container: Имя или ID контейнера
        tail: Количество последних строк для вывода (default: 100)
        timestamps: Добавлять ли временные метки (default: False)

    Returns:
        {
            "container": str,
            "logs": str,
            "lines_count": int
        }
    """
    try:
        client = get_docker_client()
        cont = client.containers.get(container)

        logs = cont.logs(
            tail=tail,
            timestamps=timestamps,
            stdout=True,
            stderr=True
        ).decode('utf-8', errors='replace')

        lines = logs.strip().split('\n') if logs else []

        return {
            "container": cont.name,
            "logs": logs,
            "lines_count": len(lines),
            "status": cont.status
        }
    except NotFound:
        return {
            "error": f"Контейнер '{container}' не найден"
        }
    except APIError as e:
        return {
            "error": f"Docker API error: {str(e)}"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}"
        }


# ASGI app
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    # Проверка доступности Docker при старте
    try:
        client = get_docker_client()
        info = client.info()
        logger.info(f"Docker MCP Server connected to Docker Engine (version: {info.get('ServerVersion')})")
    except DockerException as e:
        logger.error(f"Failed to connect to Docker: {e}")
        # Не падаем, позволяем серверу запуститься, но операции будут возвращать ошибки

    async with mcp.session_manager.run():
        yield


async def health(request):
    """Health check эндпоинт."""
    try:
        client = get_docker_client()
        client.ping()
        return JSONResponse({
            "status": "ok",
            "service": "docker-mcp-server",
            "docker_connection": "ok"
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "service": "docker-mcp-server",
            "docker_connection": "failed",
            "error": str(e)
        }, status_code=503)


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
