import json
import os

import chainlit as cl
from app.langchain_client import build_chain


@cl.on_chat_start
async def on_chat_start():
    try:
        chain = build_chain()
    except Exception as exc:
        await cl.Message(content=f"Не удалось инициализировать LLM: {exc}").send()
        return

    cl.user_session.set("chain", chain)

    model_name = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    await cl.Message(
        content=(
            "🎄 AI Advent Challenge — Задание 2\n\n"
            "**Анализ настроения с структурированным выводом**\n\n"
            "Напишите любой текст — я проанализирую настроение и верну результат в JSON-формате.\n\n"
            f"_Модель: {model_name}_"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    chain = cl.user_session.get("chain")
    if not chain:
        await cl.Message(
            content="LLM не инициализирован. Перезапустите чат после установки API-ключа."
        ).send()
        return

    try:
        # JsonOutputParser уже вернёт dict, а не строку!
        data = await chain.ainvoke({"input": message.content})

        # Форматируем для красивого отображения в чате
        emoji_map = {
            "positive": "😊",
            "negative": "😞",
            "neutral": "😐"
        }
        emoji = emoji_map.get(data.get('sentiment'), "🤔")

        formatted_response = (
            f"## Анализ настроения {emoji}\n\n"
            f"**Настроение:** {data.get('sentiment', 'N/A')}\n"
            f"**Уверенность:** {data.get('confidence', 0):.0%}\n"
            f"**Ключевые слова:** {', '.join(data.get('keywords', []))}\n\n"
            f"_{data.get('summary', 'Нет описания')}_\n\n"
            f"---\n"
            f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"
        )

        await cl.Message(content=formatted_response).send()

    except Exception as e:
        # JsonOutputParser бросит ошибку, если JSON невалидный
        await cl.Message(
            content=f"❌ Ошибка обработки ответа: {e}\n\nПопробуйте переформулировать запрос."
        ).send()
