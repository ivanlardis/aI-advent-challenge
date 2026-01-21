import chainlit as cl
from app.ollama_client import OllamaClient
import time
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@cl.on_message
async def on_message(message: cl.Message):
    """Обработчик сообщения пользователя: генерация ответа."""
    # Создаём клиент для каждого сообщения
    client = OllamaClient(OLLAMA_HOST)

    # Получаем список моделей и выбираем первую
    models = client.list_models()
    if not models:
        await cl.Message(content="❌ Модели не найдены").send()
        return

    model = models[0]["name"]

    start_time = time.time()
    response_content = ""

    msg = cl.Message(content="")
    await msg.send()

    try:
        # Генерируем ответ без истории (контекст только текущего сообщения)
        messages = [{"role": "user", "content": message.content}]

        for chunk in client.generate_stream(messages, model):
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

    except Exception as e:
        await msg.stream_token(f"\n\n❌ Ошибка: {e}")
