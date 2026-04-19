#!/usr/bin/env python3
"""Локальный прогон backlog Day 5 на gemma4:e4b через Ollama API.

Парсит tasks/backlog.md, для каждой из 18 задач собирает промпт
(системный = правила lardis + контракт «одна задача»; пользовательский =
тип + описание + acceptance + содержимое релевантных файлов), шлёт в модель,
сохраняет ответ в tasks/runs/run-local/T-NN.md с замерами.

Контекст: исходники app.py + lib/*.py + tests/*.py даются целиком — это
аналог сценария «в IDE открыты рабочие файлы». Никаких диффов не применяется,
никаких коммитов не делается: это оценочный прогон качества генерации.

Запуск:
    python3 tasks/run_local_loop.py              # все 18 задач
    python3 tasks/run_local_loop.py T-01 T-05    # подмножество

Требует `ollama serve` и `ollama pull gemma4:e4b` (9.6 GB).
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG_PATH = ROOT / "tasks" / "backlog.md"
OUT_DIR = ROOT / "tasks" / "runs" / "run-local"
STATS_PATH = OUT_DIR / "stats.json"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:e4b"

CODE_FILES = [
    "app.py",
    "lib/__init__.py",
    "lib/analytics.py",
    "lib/history.py",
    "lib/openrouter_client.py",
    "lib/profile.py",
    "tests/test_analytics.py",
    "tests/test_app_commands.py",
    "tests/test_history.py",
    "tests/test_openrouter_client.py",
    "tests/test_profile.py",
]

SYSTEM_PROMPT = """Ты — код-ассистент в проекте lardis (Python 3.13, Chainlit, OpenRouter).

## Правила проекта
- app.py — точка входа, хендлеры on_chat_start / on_message, команды (/compress, /summary, /reset, ...)
- lib/ — openrouter_client, analytics, profile, history
- tests/ — pytest
- Async для хендлеров, типизация typing, docstrings и комментарии на русском
- Нельзя: новые папки верхнего уровня, выдуманные API (типа @cl.page()), эмодзи в коде, global mutable state
- Паттерн команды в on_message:
```python
if cmd == "/mycommand":
    await handle_mycommand(...)
    return
```

## Твоя работа
Ты получаешь ОДНУ задачу из backlog с чётким acceptance-критерием и содержимое релевантных файлов.
Выдай минимальный корректный фикс/код.

## Формат ответа
1. **Причина / что поменяется** (1-3 строки).
2. **Полный финальный код** — каждый изменённый файл отдельным блоком с путём-заголовком:
   ```
   # lib/profile.py
   <полный новый текст функции или блока>
   ```
3. **Как проверить** — 1-2 строки (какой pytest или grep).

Не добавляй лишних сущностей вне acceptance. Не выдумывай API. Отвечай на русском.
"""

TASK_LINE_RE = re.compile(
    r"^- \[[ x]\] (T-\d+) \| (\w+) \| (.+?) — \*\*Acceptance:\*\* (.+)$"
)


def load_code_context() -> str:
    parts = []
    for rel in CODE_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        parts.append(f"### {rel}\n```python\n{path.read_text(encoding='utf-8')}\n```")
    return "\n\n".join(parts)


def parse_backlog() -> list[dict]:
    tasks = []
    for line in BACKLOG_PATH.read_text(encoding="utf-8").splitlines():
        m = TASK_LINE_RE.match(line)
        if not m:
            continue
        tid, ttype, desc, acc = m.groups()
        tasks.append({"id": tid, "type": ttype, "desc": desc, "acceptance": acc})
    return tasks


def build_user_prompt(task: dict, code_ctx: str) -> str:
    return (
        f"# Задача {task['id']} ({task['type']})\n\n"
        f"## Описание\n{task['desc']}\n\n"
        f"## Acceptance\n{task['acceptance']}\n\n"
        f"## Контекст проекта (текущий код)\n\n{code_ctx}\n"
    )


def ask(model: str, system: str, user: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "top_p": 0.9, "num_ctx": 32768},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as resp:
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


def save_task(task: dict, out: dict, prompt: str) -> None:
    path = OUT_DIR / f"{task['id']}.md"
    path.write_text(
        f"# {task['id']} — {task['type']}\n\n"
        f"**Описание:** {task['desc']}\n\n"
        f"**Acceptance:** {task['acceptance']}\n\n"
        f"- Модель: **{MODEL}**\n"
        f"- Время (wall): **{out['wall_s']}s**\n"
        f"- Токенов в ответе: **{out['eval_count']}**\n"
        f"- Скорость: **{out['tok_per_s']} tok/s**\n\n"
        f"## Ответ модели\n\n{out['content']}\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_tasks = parse_backlog()
    argv_ids = {a for a in sys.argv[1:] if a.startswith("T-")}
    tasks = [t for t in all_tasks if not argv_ids or t["id"] in argv_ids]
    if not tasks:
        print("Нет задач для прогона.", file=sys.stderr)
        sys.exit(1)

    code_ctx = load_code_context()
    print(f"Контекст проекта: {len(code_ctx)} символов", flush=True)

    if STATS_PATH.exists():
        stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    else:
        stats = {"model": MODEL, "tasks": {}}

    total_wall = 0.0
    for t in tasks:
        prompt = build_user_prompt(t, code_ctx)
        print(f"[{t['id']}] {t['type']}...", flush=True)
        try:
            r = ask(MODEL, SYSTEM_PROMPT, prompt)
        except Exception as exc:
            stats["tasks"][t["id"]] = {"error": str(exc)}
            print(f"  ERROR: {exc}", flush=True)
            continue
        save_task(t, r, prompt)
        stats["tasks"][t["id"]] = {
            "type": t["type"],
            "wall_s": r["wall_s"],
            "eval_count": r["eval_count"],
            "tok_per_s": r["tok_per_s"],
        }
        total_wall += r["wall_s"]
        print(
            f"  -> {r['wall_s']}s, {r['tok_per_s']} tok/s, tokens={r['eval_count']}",
            flush=True,
        )
        STATS_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"\nИтого: {len(tasks)} задач, wall={round(total_wall, 1)}s ({round(total_wall/60, 1)} мин)")
    print(f"Артефакты: {OUT_DIR}")


if __name__ == "__main__":
    main()
