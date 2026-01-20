import chainlit as cl
from app.ollama_client import OllamaClient
from app.history import SessionHistory
import time
import os
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@cl.on_chat_start
async def on_chat_start():
    """Обработчик начала чата: подключение к Ollama и выбор модели."""
    try:
        client = OllamaClient(OLLAMA_HOST)
        models = client.list_models()

        if not models:
            await cl.Message(
                content=(
                    "❌ Модели не найдены.\n\n"
                    "Установите модель:\n"
                    "```bash\nollama pull gemma2:2b\n```\n\n"
                    "Или запустите Ollama:\n"
                    "```bash\nollama serve\n```"
                )
            ).send()
            return

        # Dropdown для выбора модели
        settings = await cl.ChatSettings(
            [
                cl.input_widget.Select(
                    id="model",
                    label="Выберите модель",
                    values=[m["name"] for m in models],
                    initial_index=0
                )
            ]
        ).send()

        model = settings["model"]
        history = SessionHistory()

        cl.user_session.set("model", model)
        cl.user_session.set("history", history)
        cl.user_session.set("client", client)

        await cl.Message(
            content=f"✅ Подключено к **{model}**\n\nОтправьте сообщение!"
        ).send()

    except requests.exceptions.ConnectionError:
        await cl.Message(
            content=(
                "❌ Ollama не запущен.\n\n"
                "Запустите Ollama:\n"
                "```bash\nollama serve\n```"
            )
        ).send()
    except Exception as e:
        await cl.Message(content=f"❌ Ошибка: {e}").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Обработчик сообщения пользователя: генерация ответа с метриками."""
    history = cl.user_session.get("history")
    client = cl.user_session.get("client")
    model = cl.user_session.get("model")

    history.add_user_message(message.content)

    start_time = time.time()
    response_content = ""

    msg = cl.Message(content="")
    await msg.send()

    try:
        for chunk in client.generate_stream(history.get_for_api(), model):
            if "message" in chunk:
                token = chunk["message"].get("content", "")
                response_content += token
                await msg.stream_token(token)

        duration = time.time() - start_time
        char_count = len(response_content)

        metrics = (
            f"\n\n---\n"
            f"⏱ {duration:.1f} сек • 🔢 {char_count} символов"
        )
        await msg.stream_token(metrics)

        history.add_assistant_message(response_content)

    except Exception as e:
        await msg.stream_token(f"\n\n❌ Ошибка: {e}")


@cl.on_chat_end
async def on_chat_end():
    """Обработчик окончания чата: очистка сессии."""
    history = cl.user_session.get("history")
    if history:
        history.clear()
