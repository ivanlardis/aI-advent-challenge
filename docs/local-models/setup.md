# Local Boost — установка локального ассистента

Стек: **PyCharm + Continue.dev + Ollama** на MacBook Pro M3 Max 48GB.

> **PyCharm Community работает.** Continue.dev официально поддерживает всю IntelliJ Platform, включая Community Edition — платить за Professional не нужно.

> **Важно про сеть.** Этот прогон (Day 4) делался при слабом интернете, 26 GB целевых coder-моделей не вытянулись. Поэтому фактически гонял 3 уже скачанные модели (`qwen2.5:3b`, `gemma3:1b`, `qwen2.5:0.5b`). Раздел «Target-набор» ниже остаётся планом после апгрейда канала.

## 1. Ollama

Уже установлена (`/usr/local/bin/ollama`). Проверить:

```bash
ollama --version
ollama serve &      # если ещё не запущена
ollama list
```

## 2. Модели — фактический набор (то, что реально гонялось)

```bash
ollama pull qwen2.5:3b        # 1.9 GB — основной чат
ollama pull gemma3:1b         # 0.8 GB — альтернатива
ollama pull qwen2.5:0.5b      # 0.4 GB — быстрый draft / autocomplete
```

Итого ~3 GB. Ни одна из них не специализированная coder-модель — это честное ограничение текущего прогона.

## 3. Target-набор (когда интернет позволит)

```bash
ollama pull qwen2.5-coder:14b         # ~9 GB   — основной чат (HumanEval 89%)
ollama pull gemma3:12b                # ~7 GB   — альтернатива
ollama pull qwen2.5-coder:7b          # ~4.5 GB — быстрый чат
ollama pull qwen2.5-coder:7b-base     # ~4.5 GB — FIM-автокомплит
```

После загрузки — раскомментировать секцию TARGET в `.continue/config.yaml`.

## 4. Continue.dev в PyCharm

1. PyCharm → Settings → Plugins → Marketplace → найти **Continue** → Install → Restart.
2. Continue появится в правой боковой панели.
3. Конфиг лежит в репо: `.continue/config.yaml`. Continue подхватит его автоматически при открытии проекта (не надо копировать в `~/.continue/`).

## 5. Параметры генерации

Для всех чат-моделей:
- `temperature: 0.2` — низкая, детерминированный код
- `topP: 0.9` — отсечь маловероятные токены
- `contextLength: 8192` (для 3B), 4096 (для 1B)
- `maxTokens: 1024` — ответ до 1K токенов

Для автокомплита:
- `temperature: 0.1` — ещё ниже, inline должно быть предсказуемым
- `contextLength: 2048-4096`
- `maxTokens: 128-256`

## 6. System prompt

У основной чат-модели — полный `CLAUDE.md` в `systemMessage`. У лёгких (1B/0.5B) — короткая выжимка, иначе они забивают контекст системкой.

## 7. Контекст-провайдеры

Подключены: `code`, `diff`, `folder`, `codebase`, `file`, `open`, `terminal`. В чате: `@code`, `@file app.py`, `@folder lib` — подмешивает нужное.

## 8. Проверка

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:3b",
  "messages": [{"role":"user","content":"Привет"}],
  "stream": false
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message']['content'])"
```

Должен вернуть короткий осмысленный ответ за 1-3 сек.

В PyCharm → Continue → чат → выбрать модель → «Привет, проверка». Ответ за 2-5 сек.

## 9. Benchmark-прогон (воспроизведение таблиц comparison.md)

```bash
python3 docs/local-models/run_benchmark.py
```

Прогоняет 2 задачи (Day 1 фича, Day 2 bug-fix) на всех моделях из `MODELS`, пишет ответы в `docs/local-models/task-runs/<task>-<model>.md` и агрегат в `stats.json`.
