#!/usr/bin/env python3
"""Прогон двух задач (Day 1 фича, Day 2 bug-fix) на локальных моделях.

Отправляет запросы в Ollama HTTP API и сохраняет ответы + замеры времени
в docs/local-models/task-runs/. Результаты агрегирует в stats.json
для вставки в comparison.md.

Запуск:
    python3 docs/local-models/run_benchmark.py                 # все модели из MODELS
    python3 docs/local-models/run_benchmark.py gemma4:e4b      # только одна
    python3 docs/local-models/run_benchmark.py m1 m2 ...       # произвольный список

При указании моделей через argv stats.json мержится, а не перезаписывается —
можно добавить результаты новой модели, не теряя уже прогнанные.

Требует запущенную Ollama (`ollama serve`).
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
OUT_DIR = Path(__file__).parent / "task-runs"
OUT_DIR.mkdir(exist_ok=True)
STATS_PATH = OUT_DIR / "stats.json"

MODELS = ["qwen2.5:3b", "gemma3:1b", "qwen2.5:0.5b", "gemma4:e4b"]

SYSTEM_PROMPT_CHAT = """# lardis — правила проекта

Персональный AI-помощник. Chainlit чат-бот + OpenRouter LLM + профиль.

## Стек
Python 3.13, Chainlit, LangChain (ChatOpenAI), OpenRouter.

## Структура
- app.py — точка входа, хендлеры, команды
- lib/openrouter_client.py — клиент OpenRouter
- lib/analytics.py — статистика токенов
- lib/profile.py — парсинг профиля
- config/profile.md — профиль (gitignored)
- tests/ — pytest + Playwright smoke

## Можно
- Добавлять модули в lib/
- Добавлять команды /command в app.py
- Расширять system prompt
- Использовать cl.user_session для состояния

## Нельзя
- Создавать новые папки верхнего уровня (только lib/, config/, data/, tests/, docs/)
- Менять контракт OpenRouterClient
- Хранить секреты в коде — только .env
- Глобальное mutable-состояние (всё через cl.user_session)
- Выдумывать API (например @cl.page() не существует)
- Эмодзи в коде и строках

## Стиль
- Docstrings и комментарии на русском
- Async для хендлеров
- Типизация typing

## Паттерн команды в on_message
```
if cmd == "/mycommand":
    await handle_mycommand(...)
    return
```

Отвечай кратко на русском. Код — файл целиком с путём."""

SYSTEM_PROMPT_BUGFIX = """Ты — Bug Fix профиль. Получаешь баг, находишь причину, предлагаешь фикс.

Должен:
- Искать файлы и читать их
- Анализировать тесты и логи
- Проверять зависимости модулей

Не должен:
- Игнорировать тесты
- Делать правки на авось

Формат ответа:
## Что нашёл
<описание причины бага>
## Что починить
<диф или финальный код>
## Что проверить
<как убедиться что фикс работает>"""

APP_PY_SNIPPET = """# app.py (релевантный фрагмент)

async def handle_summary_command(usage_history: List[Dict]):
    if not usage_history:
        await cl.Message(content="Пока нет данных по токенам.").send()
        return
    total = sum(item.get("total", 0) for item in usage_history)
    lines = ["**Статистика токенов:**\\n", "| # | Сообщение | Токены |", "|---|-----------|--------|"]
    for idx, item in enumerate(usage_history, 1):
        preview = item.get("message", "")[:30]
        tokens = item.get("total", 0)
        lines.append(f"| {idx} | {preview}... | {tokens} |")
    lines.append(f"\\n**Всего:** {total} токенов")
    await cl.Message(content="\\n".join(lines)).send()

# lib/analytics.py — как пишется запись:
# record = {"total_tokens": prompt_tokens + completion_tokens, "input_preview": ...}
# analytics_list.append(record)
"""

TASK1_PROMPT = """Добавь в `app.py` новую команду `/history` — показывает последние 10 сообщений
пользователя из текущей сессии (хранение через `cl.user_session.get("history")`).
Следуй правилам CLAUDE.md из system prompt: паттерн команды, без эмодзи,
без новых папок, без выдуманных API. Верни полностью файл handler-функции
и строку регистрации команды в on_message.
"""

TASK2_PROMPT = f"""Пользователь жалуется: команда `/summary` всегда показывает 0 токенов,
хотя диалог идёт. Найди причину и предложи фикс.

Контекст кода:
```python
{APP_PY_SNIPPET}
```
"""


def ask(model: str, system: str, user: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "top_p": 0.9, "num_ctx": 8192},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    wall = time.time() - t0
    content = body["message"]["content"]
    eval_count = body.get("eval_count", 0)
    eval_duration_s = body.get("eval_duration", 1) / 1e9
    tok_per_s = eval_count / eval_duration_s if eval_duration_s else 0
    return {
        "content": content,
        "wall_s": round(wall, 2),
        "eval_count": eval_count,
        "tok_per_s": round(tok_per_s, 1),
    }


def save(task: str, model: str, out: dict, prompt: str) -> None:
    safe_model = model.replace(":", "_").replace("/", "_")
    path = OUT_DIR / f"{task}-{safe_model}.md"
    path.write_text(
        f"# {task} — {model}\n\n"
        f"- Время (wall): **{out['wall_s']}s**\n"
        f"- Токенов в ответе: **{out['eval_count']}**\n"
        f"- Скорость: **{out['tok_per_s']} tok/s**\n\n"
        f"## Промпт\n\n```\n{prompt.strip()}\n```\n\n"
        f"## Ответ модели\n\n{out['content']}\n",
        encoding="utf-8",
    )


def main() -> None:
    argv_models = sys.argv[1:]
    models = argv_models or MODELS

    if argv_models and STATS_PATH.exists():
        stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    else:
        stats = {"task1": {}, "task2": {}}

    for model in models:
        print(f"[{model}] task1 (feature)...", flush=True)
        r1 = ask(model, SYSTEM_PROMPT_CHAT, TASK1_PROMPT)
        save("day1", model, r1, TASK1_PROMPT)
        stats["task1"][model] = {k: v for k, v in r1.items() if k != "content"}
        print(f"  -> {r1['wall_s']}s, {r1['tok_per_s']} tok/s", flush=True)

        print(f"[{model}] task2 (bug-fix)...", flush=True)
        r2 = ask(model, SYSTEM_PROMPT_BUGFIX, TASK2_PROMPT)
        save("day2", model, r2, TASK2_PROMPT)
        stats["task2"][model] = {k: v for k, v in r2.items() if k != "content"}
        print(f"  -> {r2['wall_s']}s, {r2['tok_per_s']} tok/s", flush=True)

    STATS_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\nСохранено в {OUT_DIR}")


if __name__ == "__main__":
    main()
