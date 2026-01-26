#!/usr/bin/env python3
"""
Простой голосовой чат с AI
FastAPI + WebSocket + Whisper + Ollama
"""

import re
import tempfile
from pathlib import Path
from typing import List

import requests
import whisper
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# ========================== КОНФИГУРАЦИЯ ==========================

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"

# Загрузка Whisper модели
print("🎤 Загрузка Whisper модели...")
WHISPER_MODEL = whisper.load_model("base")
print("✅ Whisper готов")

# ========================== ПЕРСОНАЛИЗАЦИЯ ==========================

def load_profile(profile_path: str = "config/profile.md") -> str:
    """Загружает профиль пользователя из MD файла"""
    current_dir = Path(__file__).parent
    full_path = current_dir / profile_path

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"✅ Профиль загружен: {full_path}")
            return content
    except FileNotFoundError:
        print(f"⚠️  Профиль не найден: {full_path}")
        return ""
    except Exception as e:
        print(f"⚠️  Ошибка загрузки профиля: {e}")
        return ""


def extract_name(profile_content: str) -> str:
    """Извлекает имя пользователя из профиля"""
    match = re.search(r'- \*\*Имя:\*\*\s*(.+)', profile_content)
    if match:
        return match.group(1).strip()
    return "Пользователь"


# Загрузка профиля при старте
USER_PROFILE = load_profile()
USER_NAME = extract_name(USER_PROFILE)

# ========================== OLLAMA ==========================

def check_ollama_health() -> bool:
    """Проверяет доступность Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """Отправляет запрос к Ollama и возвращает ответ"""
    try:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "Не удалось получить ответ")
        else:
            return f"Ошибка Ollama API: {response.status_code}"

    except requests.exceptions.Timeout:
        return "⏱️ Запрос превысил время ожидания"
    except Exception as e:
        return f"❌ Ошибка при обращении к Ollama: {str(e)}"


def get_system_prompt() -> str:
    """Формирует system prompt с учетом профиля пользователя"""
    base_prompt = """Ты — личный AI-помощник. Твоя задача — помогать пользователю достигать его целей, поддерживать и мотивировать.

Отвечай:
- По-русски
- Дружелюбно и с заботой
- Кратко (5-7 предложений, если не нужен код)
- С учетом контекста о пользователе
"""

    if USER_PROFILE:
        base_prompt += f"""

## КОНТЕКСТ О ПОЛЬЗОВАТЕЛЕ:
{USER_PROFILE}

Учитывай эту информацию при общении. Обращайся к пользователю по имени: {USER_NAME}."""

    return base_prompt

# ========================== WHISPER ==========================

def transcribe_audio(audio_path: str) -> str:
    """Распознает речь из аудио файла через Whisper"""
    try:
        result = WHISPER_MODEL.transcribe(
            audio_path,
            language="ru",
            fp16=False
        )
        return result["text"].strip()
    except Exception as e:
        return f"❌ Ошибка распознавания: {str(e)}"

# ========================== FASTAPI ==========================

# Создаём FastAPI приложение
app = FastAPI(title="Голосовой AI Чат")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")


class ConnectionManager:
    """Менеджер WebSocket подключений"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def get_chat():
    """Главная страница с чатом"""
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    ollama_ok = check_ollama_health()
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama": "ok" if ollama_ok else "unavailable"
    }


@app.post("/api/voice")
async def process_voice(file: UploadFile = File(...)):
    """API endpoint для обработки голосовых записей"""
    # Сохраняем файл временно
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Распознаём текст
        text = transcribe_audio(tmp_path)

        if text.startswith("❌"):
            return JSONResponse({"error": text}, status_code=400)

        # Получаем ответ от LLM
        system_prompt = get_system_prompt()
        response = call_ollama(text, system_prompt)

        return JSONResponse({
            "transcribed": text,
            "response": response
        })

    finally:
        # Удаляем временный файл
        Path(tmp_path).unlink(missing_ok=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для чата"""
    await manager.connect(websocket)

    # Отправляем приветствие
    greeting = f"👋 Привет, **{USER_NAME}**! " if USER_PROFILE else "👋 Привет! "
    await manager.send_message({
        "type": "system",
        "content": greeting + "Я твой AI помощник. Пиши текстом или записывай голос (кнопка 🎤)."
    }, websocket)

    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_json()

            message_type = data.get("type")
            content = data.get("content", "")

            if message_type == "message":
                # Обычное текстовое сообщение
                system_prompt = get_system_prompt()
                response = call_ollama(content, system_prompt)

                await manager.send_message({
                    "type": "response",
                    "content": response
                }, websocket)

            elif message_type == "ping":
                # Поддержание соединения
                await manager.send_message({
                    "type": "pong"
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket ошибка: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    print("🚀 Запуск голосового AI чата...")
    print("   📡 http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
