import os

import chainlit as cl
from app.openrouter_client import OpenRouterClient, build_messages

# Предустановленные system prompts для тестирования
SYSTEM_PROMPTS = {
    "strict_teacher": (
        "Ты — строгий преподаватель по Python. Твой стиль:\n"
        "- Отвечаешь кратко и по существу\n"
        "- Задаёшь наводящие вопросы вместо прямых ответов\n"
        "- В конце каждого ответа даёшь мини-проверку (вопрос или задачу)\n"
        "- Используешь формальный тон\n"
        "- Не приводишь готовые решения, а помогаешь додуматься самостоятельно\n\n"
        "ФОРМАТ ОТВЕТА (только валидный JSON):\n"
        "{\n"
        '  "is_complete": false,\n'
        '  "message": "твой ответ или вопрос",\n'
        '  "collected_info": {},\n'
        '  "final_document": null\n'
        "}"
    ),
    "friendly_mentor": (
        "Ты — дружелюбный наставник для начинающих программистов. Твой стиль:\n"
        "- Объясняешь простым языком, избегая сложных терминов\n"
        "- Приводишь много примеров и аналогий из жизни\n"
        "- Не задаёшь сложных вопросов, поддерживаешь ученика\n"
        "- Используешь неформальный, дружеский тон\n"
        "- Поощряешь любые попытки и прогресс\n\n"
        "ФОРМАТ ОТВЕТА (только валидный JSON):\n"
        "{\n"
        '  "is_complete": false,\n'
        '  "message": "твой ответ с примерами и объяснениями",\n'
        '  "collected_info": {},\n'
        '  "final_document": null\n'
        "}"
    ),
    "code_reviewer": (
        "Ты — критичный код-ревьюер. Твой стиль:\n"
        "- Внимательно анализируешь код на наличие багов, уязвимостей и плохих практик\n"
        "- Указываешь на проблемы с производительностью и читаемостью\n"
        "- Предлагаешь конкретные улучшения с примерами\n"
        "- Используешь профессиональный, но конструктивный тон\n"
        "- Объясняешь, почему конкретное решение лучше\n\n"
        "ФОРМАТ ОТВЕТА (только валидный JSON):\n"
        "{\n"
        '  "is_complete": false,\n'
        '  "message": "твой детальный анализ кода",\n'
        '  "collected_info": {},\n'
        '  "final_document": null\n'
        "}"
    ),
}

async def handle_experiment_command(message: cl.Message):
    """Обрабатывает команду /experiment для сравнения температур."""
    client = cl.user_session.get("client")
    if not client:
        await cl.Message(content="OpenRouter клиент не инициализирован.").send()
        return

    # Парсинг команды: /experiment <ваш промпт>
    parts = message.content.strip().split(maxsplit=1)

    if len(parts) < 2:
        await cl.Message(
            content="❌ Укажите промпт для эксперимента.\n\n"
                    "Пример: `/experiment Объясни что такое рекурсия`"
        ).send()
        return

    prompt_text = parts[1]

    # Температуры для эксперимента
    temperatures = [0.1, 1.0, 1.5, 1.9]
    # Показываем, что начался эксперимент
    await cl.Message(
        content=f"🧪 **Запускаю эксперимент с температурой**\n\n"
                f"**Запрос:** \"{prompt_text}\"\n\n"
                f"Ожидайте результаты для трёх температур {temperatures}"
    ).send()



    # Запуск запросов с разными температурами
    for temp in temperatures:
        try:
            # Простое сообщение без истории для чистоты эксперимента
            messages = [
                {"role": "system", "content": "Отвечай кратко, 5 предложений. Не размышляй ответь быстро не думая"},
                {"role": "user", "content": prompt_text}]

            # Получаем ответ с конкретной температурой
            response = await client.get_completion_text(messages, temperature=temp)

            await cl.Message(
                content=f"---\n\n### **Temperature = {temp}\n\n{response}"
            ).send()

        except Exception as e:
            await cl.Message(
                content=f"❌ Ошибка при температуре {temp}: {e}"
            ).send()


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

    # Устанавливаем system prompt по умолчанию
    cl.user_session.set("system_prompt_key", "strict_teacher")

    # Настраиваем интерфейс выбора system prompt
    await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="SystemPrompt",
                label="System Prompt (роль агента)",
                values=["strict_teacher", "friendly_mentor", "code_reviewer"],
                initial_value="strict_teacher",
            ),
        ]
    ).send()

    model_name = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    await cl.Message(
        content=(
            "🎄 AI Advent Challenge — Задание 5\n\n"
            "**Эксперимент с температурой**\n\n"
            "Вы можете:\n"
            "1. Изменить роль агента в настройках (⚙️)\n"
            "2. Запустить эксперимент с температурой:\n"
            "   `/experiment <ваш промпт>`\n\n"
            "Эксперимент запускает ваш промпт с разными температурам:\n"
            "**Пример:** `/experiment Как Пушкин умер от туберкулеза`\n\n"
            f"_Модель: {model_name}_"
        )
    ).send()


@cl.on_settings_update
async def on_settings_update(settings):
    """Вызывается при изменении настроек пользователем."""
    system_prompt_key = settings["SystemPrompt"]
    cl.user_session.set("system_prompt_key", system_prompt_key)

    prompt_names = {
        "strict_teacher": "Строгий преподаватель",
        "friendly_mentor": "Дружелюбный наставник",
        "code_reviewer": "Код-ревьюер",
    }

    await cl.Message(
        content=f"✅ System prompt изменён на: **{prompt_names.get(system_prompt_key, system_prompt_key)}**\n\n"
                f"История диалога сохранена. Продолжайте общение!"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    # Проверка на команду /experiment
    if message.content.strip().startswith("/experiment"):
        await handle_experiment_command(message)
        return

    client = cl.user_session.get("client")
    if not client:
        await cl.Message(
            content="OpenRouter клиент не инициализирован. Перезапустите чат после установки API-ключа."
        ).send()
        return

    # Получаем историю и текущий system prompt
    history = cl.user_session.get("history", [])
    system_prompt_key = cl.user_session.get("system_prompt_key", "strict_teacher")
    system_prompt = SYSTEM_PROMPTS.get(system_prompt_key, SYSTEM_PROMPTS["strict_teacher"])

    try:
        # Формируем сообщения для API с актуальным system prompt
        messages = build_messages(message.content, history, system_prompt)

        # Получаем JSON-ответ от модели
        data = await client.get_json_completion(messages)

        # Проверяем, завершён ли сбор требований
        is_complete = data.get("is_complete", False)
        message_text = data.get("message") or ""
        final_document = data.get("final_document")

        if is_complete and final_document:
            # Модель завершила сбор данных — показываем финальный результат
            formatted_response = (
                f"✅ **Задача завершена!**\n\n"
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
