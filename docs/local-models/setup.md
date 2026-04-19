# Local Boost — установка локального ассистента

Стек: **PyCharm + Continue.dev + Ollama** на MacBook Pro M3 Max 48GB.

> **PyCharm Community работает.** Continue.dev официально поддерживает всю IntelliJ Platform, включая Community Edition — платить за Professional не нужно.

> **История прогонов.**
> - Первый прогон Day 4 — при слабом интернете, на generalist-моделях ≤3B (`qwen2.5:3b`, `gemma3:1b`, `qwen2.5:0.5b`). Ни одна не справилась.
> - Апдейт — после апгрейда канала докачана **`gemma4:e4b`** (9.6 GB, Gemma 4 E4B, мобильный edge-стандарт от Google, апрель 2026, multimodal, заявлена как «new standard for local agentic intelligence»). Теперь это основная чат-модель в конфиге. Coder-модели семейства Qwen2.5-Coder решил не качать — Gemma 4 E4B покрывает те же задачи при меньшем размере и более свежем обучении.

## 1. Ollama

Нужна Ollama ≥ 0.20 (для Gemma 4). Проверить:

```bash
ollama --version
ollama serve &      # если ещё не запущена
ollama list
```

## 2. Модели — фактический набор

```bash
ollama pull gemma4:e4b        # 9.6 GB — основной чат (Gemma 4 E4B, edge, multimodal)
ollama pull qwen2.5:3b        # 1.9 GB — baseline для сравнения
ollama pull gemma3:1b         # 0.8 GB — альтернатива (плохо себя показала)
ollama pull qwen2.5:0.5b      # 0.4 GB — быстрый draft / autocomplete
```

Итого ~13 GB. Gemma 4 E4B — основной чат; остальные три остались для честного сравнения в `comparison.md`.

## 3. Опциональный coder-набор

```bash
# Раскомментировать если на реальных задачах станет видно, что coder-specialized
# объективно лучше generalist Gemma 4:
# ollama pull qwen2.5-coder:7b          # ~4.5 GB — быстрый coder-чат
# ollama pull qwen2.5-coder:7b-base     # ~4.5 GB — FIM-автокомплит
```

Секция TARGET в `.continue/config.yaml` на эти модели лежит закомментированной.

## 4. Continue.dev в PyCharm

1. PyCharm → Settings → Plugins → Marketplace → найти **Continue** → Install → Restart.
2. Continue появится в правой боковой панели.
3. Конфиг лежит в репо: `.continue/config.yaml`. Continue подхватит его автоматически при открытии проекта (не надо копировать в `~/.continue/`).

## 5. Параметры генерации

Для всех чат-моделей:
- `temperature: 0.2` — низкая, детерминированный код
- `topP: 0.9` — отсечь маловероятные токены
- `contextLength: 16384` (Gemma 4 E4B), 8192 (для 3B), 4096 (для 1B)
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
  "model": "gemma4:e4b",
  "messages": [{"role":"user","content":"Привет"}],
  "stream": false
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message']['content'])"
```

Должен вернуть короткий осмысленный ответ за 1-5 сек.

В PyCharm → Continue → чат → выбрать модель → «Привет, проверка». Ответ за 2-5 сек.

## 9. Benchmark-прогон (воспроизведение таблиц comparison.md)

```bash
python3 docs/local-models/run_benchmark.py                  # все модели из MODELS
python3 docs/local-models/run_benchmark.py gemma4:e4b       # только одна — мерж в stats.json
```

Прогоняет 2 задачи (Day 1 фича, Day 2 bug-fix), пишет ответы в `docs/local-models/task-runs/<task>-<model>.md` и агрегат в `stats.json`. При передаче моделей через argv `stats.json` мержится — можно добавить строку новой модели, не теряя прежние замеры.
