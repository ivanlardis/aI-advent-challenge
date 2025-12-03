import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI


def build_chain():
    """Создает LangChain-цепочку для сбора данных и расчёта БЖУ."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Установите OPENROUTER_API_KEY, чтобы обратиться к OpenRouter.")

    model = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
        model_kwargs={
            "reasoning_effort": "none"
        }
    )

    # Создаём JSON parser
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Ты — опытный нутрициолог, который собирает данные о пользователе для расчёта БЖУ (белки, жиры, углеводы).\n\n"
                "КРИТИЧЕСКИ ВАЖНО: Ты ОБЯЗАН возвращать ТОЛЬКО валидный JSON. Никакого текста до или после JSON.\n\n"
                "{format_instructions}\n\n"
                "Твоя задача:\n"
                "1. Задать пользователю РОВНО 5 вопросов (по одному за раз):\n"
                "   - Ваш рост (в см)?\n"
                "   - Ваш вес (в кг)?\n"
                "   - Ваш возраст (в годах)?\n"
                "   - Ваш пол (мужской/женский)?\n"
                "   - Ваш уровень физической активности (минимальная/низкая/средняя/высокая/очень высокая)?\n"
                "2. Собирать ответы пользователя и запоминать их в collected_info\n"
                "3. Когда все 5 вопросов заданы и получены ответы — установи is_complete=true и рассчитай БЖУ\n\n"
                "ФОРМАТ ОТВЕТА (только валидный JSON):\n"
                "{{\n"
                '  "is_complete": false,\n'
                '  "message": "ваш вопрос или сообщение",\n'
                '  "collected_info": {{\n'
                '    "height": null,\n'
                '    "weight": null,\n'
                '    "age": null,\n'
                '    "gender": null,\n'
                '    "activity_level": null\n'
                "  }},\n"
                '  "final_document": null\n'
                "}}\n\n"
                "Правила:\n"
                "- Задавай вопросы СТРОГО по порядку, по одному за раз\n"
                "- Не переходи к следующему вопросу, пока не получишь ответ на текущий\n"
                "- Когда собраны все 5 ответов — рассчитай BMR, калорийность и БЖУ\n"
                "- ВСЕГДА возвращай ТОЛЬКО JSON, без дополнительного текста"
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    # Цепочка с JSON-парсером
    return prompt | llm | parser
