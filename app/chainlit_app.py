import os

import chainlit as cl
from app.openrouter_client import OpenRouterClient, build_nutrition_messages


@cl.on_chat_start
async def on_chat_start():
    # Простой список для истории сообщений
    cl.user_session.set("history", [])

    try:
        client = OpenRouterClient()
    except Exception as exc:
        await cl.Message(content=f"Не удалось инициализировать OpenRouter клиент: {exc}").send()
        return

    cl.user_session.set("client", client)

    model_name = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    await cl.Message(
        content=(
            "🎄 AI Advent Challenge — Задание 3\n\n"
            "**Расчёт БЖУ (белки, жиры, углеводы)**\n\n"
            "Я — нутрициолог. Задам вам 5 вопросов о вашем здоровье и активности, "
            "после чего рассчитаю вашу суточную норму калорий и БЖУ.\n\n"
            "Начнём?\n\n"
            f"_Модель: {model_name}_"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    client = cl.user_session.get("client")
    if not client:
        await cl.Message(
            content="OpenRouter клиент не инициализирован. Перезапустите чат после установки API-ключа."
        ).send()
        return

    # Получаем историю
    history = cl.user_session.get("history", [])

    try:
        # Формируем сообщения для API
        messages = build_nutrition_messages(message.content, history)

        # Получаем JSON-ответ от модели
        data = await client.get_json_completion(messages)

        # Проверяем, завершён ли сбор требований
        is_complete = data.get("is_complete", False)
        message_text = data.get("message") or ""
        final_document = data.get("final_document")

        if is_complete and final_document:
            # Модель завершила сбор данных — показываем расчёт БЖУ
            formatted_response = (
                f"✅ **Расчёт завершён!**\n\n"
                f"{final_document}"
            )
        else:
            # Продолжаем диалог — показываем только вопрос
            formatted_response = message_text or "Продолжаем..."

        # Отправляем ответ только если есть что отправить
        if formatted_response:
            await cl.Message(content=formatted_response).send()

        # Сохраняем сообщения в историю (только если message_text валидный)
        if message_text:
            history.append({"role": "user", "content": message.content})
            history.append({"role": "assistant", "content": message_text})
            cl.user_session.set("history", history)

    except Exception as e:
        # Обработка ошибок парсинга JSON или API
        await cl.Message(
            content=f"❌ Ошибка обработки ответа: {e}\n\nПопробуйте переформулировать запрос."
        ).send()
