import chainlit as cl
from app.ollama_client import OllamaClient
import time
import os
import httpx
import asyncio
from typing import Optional, List
from dataclasses import dataclass

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
REQUEST_TIMEOUT = 10.0  # Таймаут на один запрос

# === Усложнённый тестовый датасет ===
TEST_DATA = [
    # POSITIVE - явные (5)
    ("Отличный товар, очень доволен покупкой!", "positive"),
    ("Рекомендую всем, лучшее соотношение цена-качество", "positive"),
    ("Превзошёл все мои ожидания!", "positive"),
    ("Качество на высоте, буду заказывать ещё", "positive"),
    ("Прекрасный сервис и отличный продукт", "positive"),

    # POSITIVE - сложные (3)
    ("Сначала сомневался, но в итоге не пожалел о покупке", "positive"),
    ("Несмотря на высокую цену, товар того стоит", "positive"),
    ("Долго выбирал между аналогами, и этот оказался лучшим", "positive"),

    # NEGATIVE - явные (5)
    ("Ужасное качество, деньги на ветер", "negative"),
    ("Не рекомендую, полное разочарование", "negative"),
    ("Сломался через два дня использования", "negative"),
    ("Худшая покупка в моей жизни", "negative"),
    ("Поддержка не отвечает, проблему не решили", "negative"),

    # NEGATIVE - сложные/сарказм (3)
    ("Ну да, конечно, супер качество... если вам нравится мусор", "negative"),
    ("Спасибо за потраченное время и нервы", "negative"),
    ("Отличный способ выбросить деньги", "negative"),

    # NEUTRAL - явные (4)
    ("Товар соответствует описанию", "neutral"),
    ("Обычный товар, ничего особенного", "neutral"),
    ("Доставили вовремя", "neutral"),
    ("Нормальное качество за свою цену", "neutral"),

    # NEUTRAL - сложные/смешанные (4)
    ("Есть плюсы и минусы, в целом нормально", "neutral"),
    ("Качество хорошее, но цена завышена", "neutral"),
    ("Работает как заявлено, не больше и не меньше", "neutral"),
    ("Ожидал большего, но и не разочарован", "neutral"),
]

# === Варианты промптов ===
PROMPTS = {
    "baseline": None,
    "zero-shot": """Ты — классификатор тональности текста.
Определи тональность текста: positive, negative или neutral.
Ответь ТОЛЬКО одним словом: positive, negative или neutral.""",
    "few-shot": """Ты — классификатор тональности отзывов.
Определи тональность: positive, negative или neutral.

Примеры:
- "Отличный товар!" → positive
- "Сначала сомневался, но не пожалел" → positive
- "Ужасное качество" → negative
- "Ну да, супер... если любите мусор" → negative (сарказм)
- "Товар как в описании" → neutral
- "Есть плюсы и минусы" → neutral

Ответь ТОЛЬКО одним словом: positive, negative или neutral.""",
}


@dataclass
class ExperimentResult:
    model: str
    prompt_type: str
    correct: int
    total: int
    avg_time: float

    @property
    def accuracy(self) -> float:
        return self.correct / self.total * 100 if self.total > 0 else 0


async def get_available_models(host: str) -> List[str]:
    """Получает список доступных моделей (async)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{host}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
    except Exception as e:
        print(f"Ошибка получения моделей: {e}")
        return []


async def generate_async(
    host: str,
    prompt: str,
    model: str,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    num_ctx: Optional[int] = None,
) -> tuple[str, float]:
    """Асинхронная генерация ответа."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    if options:
        payload["options"] = options

    start_time = time.time()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(f"{host}/api/chat", json=payload)
        response.raise_for_status()

    elapsed = time.time() - start_time
    data = response.json()
    content = data.get("message", {}).get("content", "")
    return content.strip(), elapsed


def parse_sentiment(response: str) -> Optional[str]:
    """Извлекает sentiment из ответа."""
    response_lower = response.lower().strip()
    if response_lower in ("positive", "negative", "neutral"):
        return response_lower
    for sentiment in ("positive", "negative", "neutral"):
        if sentiment in response_lower:
            return sentiment
    return None


async def run_experiment(
    msg: cl.Message,
    model: str,
    prompt_type: str,
    system_prompt: Optional[str],
) -> ExperimentResult:
    """Запускает один эксперимент (модель + промпт)."""
    correct = 0
    times = []

    temp = 0.0 if prompt_type != "baseline" else None
    ctx = 2048 if prompt_type != "baseline" else None

    for i, (text, expected) in enumerate(TEST_DATA, 1):
        try:
            response, elapsed = await generate_async(
                host=OLLAMA_HOST,
                prompt=text,
                model=model,
                system=system_prompt,
                temperature=temp,
                num_ctx=ctx,
            )
            times.append(elapsed)
            predicted = parse_sentiment(response)

            if predicted is None:
                status = "❓"
            elif predicted == expected:
                correct += 1
                status = "✅"
            else:
                status = "❌"

            short_text = text[:25] + "..." if len(text) > 25 else text
            await msg.stream_token(f"`[{i:2}]` {status} {expected:8} → {response[:12]:12} | {short_text}\n")

        except httpx.TimeoutException:
            await msg.stream_token(f"`[{i:2}]` ⏱️ Таймаут!\n")
        except Exception as e:
            await msg.stream_token(f"`[{i:2}]` ⚠️ {str(e)[:30]}\n")

    avg_time = sum(times) / len(times) if times else 0

    return ExperimentResult(
        model=model,
        prompt_type=prompt_type,
        correct=correct,
        total=len(TEST_DATA),
        avg_time=avg_time,
    )


async def run_benchmark(msg: cl.Message):
    """Запускает полный бенчмарк: все модели × все промпты."""

    models = await get_available_models(OLLAMA_HOST)
    if not models:
        await msg.stream_token("❌ Модели не найдены!\n")
        return

    total_experiments = len(models) * len(PROMPTS)

    await msg.stream_token("# 🧪 Бенчмарк: Модели × Промпты\n\n")
    await msg.stream_token(f"**Модели:** {', '.join(models)}\n")
    await msg.stream_token(f"**Промпты:** {', '.join(PROMPTS.keys())}\n")
    await msg.stream_token(f"**Тестов:** {len(TEST_DATA)} × {total_experiments} = {len(TEST_DATA) * total_experiments}\n\n")

    results: List[ExperimentResult] = []
    exp_num = 0

    for model in models:
        await msg.stream_token(f"---\n# 📦 Модель: `{model}`\n\n")

        # Прогрев модели (первый запрос загружает модель в память)
        await msg.stream_token("⏳ Загрузка модели...\n")
        try:
            await generate_async(OLLAMA_HOST, "Hi", model, temperature=0.0, num_ctx=512)
            await msg.stream_token("✅ Модель загружена\n\n")
        except Exception as e:
            await msg.stream_token(f"⚠️ Ошибка загрузки: {e}\n\n")

        for prompt_type, system_prompt in PROMPTS.items():
            exp_num += 1
            await msg.stream_token(f"## [{exp_num}/{total_experiments}] {prompt_type}\n\n")

            result = await run_experiment(msg, model, prompt_type, system_prompt)
            results.append(result)

            await msg.stream_token(f"\n**Accuracy: {result.accuracy:.0f}%** ({result.correct}/{result.total})")
            await msg.stream_token(f" • Время: {result.avg_time:.2f}s\n\n")

    # === СВОДНАЯ ТАБЛИЦА ===
    await msg.stream_token("---\n# 📊 Сводная таблица\n\n")

    header = "| Модель |"
    separator = "|--------|"
    for pt in PROMPTS.keys():
        header += f" {pt} |"
        separator += "--------|"
    await msg.stream_token(header + "\n")
    await msg.stream_token(separator + "\n")

    for model in models:
        row = f"| {model} |"
        for prompt_type in PROMPTS.keys():
            r = next((x for x in results if x.model == model and x.prompt_type == prompt_type), None)
            if r:
                row += f" {r.accuracy:.0f}% |"
            else:
                row += " - |"
        await msg.stream_token(row + "\n")

    # === ЛУЧШИЕ РЕЗУЛЬТАТЫ ===
    await msg.stream_token("\n---\n# 🏆 Лучшие результаты\n\n")

    best = max(results, key=lambda r: r.accuracy)
    await msg.stream_token(f"**🥇 Лучшая комбинация:** `{best.model}` + `{best.prompt_type}` = **{best.accuracy:.0f}%**\n\n")

    model_avg = {}
    for model in models:
        model_results = [r for r in results if r.model == model]
        model_avg[model] = sum(r.accuracy for r in model_results) / len(model_results)

    best_model = max(model_avg, key=model_avg.get)
    await msg.stream_token(f"**📦 Лучшая модель (avg):** `{best_model}` = **{model_avg[best_model]:.0f}%**\n\n")

    prompt_avg = {}
    for pt in PROMPTS.keys():
        pt_results = [r for r in results if r.prompt_type == pt]
        prompt_avg[pt] = sum(r.accuracy for r in pt_results) / len(pt_results)

    best_prompt = max(prompt_avg, key=prompt_avg.get)
    await msg.stream_token(f"**📝 Лучший промпт (avg):** `{best_prompt}` = **{prompt_avg[best_prompt]:.0f}%**\n\n")

    # Улучшение от baseline к few-shot
    await msg.stream_token("---\n# 📈 Улучшение от оптимизации\n\n")
    await msg.stream_token("| Модель | baseline → few-shot | Прирост |\n")
    await msg.stream_token("|--------|---------------------|--------|\n")

    for model in models:
        baseline = next((r for r in results if r.model == model and r.prompt_type == "baseline"), None)
        fewshot = next((r for r in results if r.model == model and r.prompt_type == "few-shot"), None)
        if baseline and fewshot:
            improvement = fewshot.accuracy - baseline.accuracy
            await msg.stream_token(f"| {model} | {baseline.accuracy:.0f}% → {fewshot.accuracy:.0f}% | **+{improvement:.0f}%** |\n")


@cl.on_message
async def on_message(message: cl.Message):
    """Обработчик сообщения пользователя."""
    client = OllamaClient(OLLAMA_HOST)

    if message.content.strip().lower() == "/benchmark":
        msg = cl.Message(content="")
        await msg.send()
        await run_benchmark(msg)
        return

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
        messages = [{"role": "user", "content": message.content}]

        for chunk in client.generate_stream(messages, model):
            if "message" in chunk:
                token = chunk["message"].get("content", "")
                response_content += token
                await msg.stream_token(token)

        duration = time.time() - start_time
        char_count = len(response_content)

        metrics = f"\n\n---\n⏱ {duration:.1f} сек • 🔢 {char_count} символов"
        await msg.stream_token(metrics)

    except Exception as e:
        await msg.stream_token(f"\n\n❌ Ошибка: {e}")
