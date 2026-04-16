---
name: test-full-cycle
description: Полный цикл тестирования проекта — прогнать pytest и UI smoke через Playwright MCP, собрать единый отчёт. Использовать после PR / большого изменения / деплоя фичи, или когда пользователь просит "прогони все тесты".
---

# test-full-cycle

Один скилл — два уровня тестов и один отчёт.

## Когда триггерить
- После PR / мержа / большого изменения.
- Пользователь просит "прогони все тесты" / "прогоняй код-тесты и smoke".
- После "задеплоил фичу" — перед этим обнови smoke-сценарии (см. ниже).

## Шаги

### 1. Код-тесты (pytest)

```bash
cd /Users/ivanlardis/IdeaProjects/lardis
source venv/bin/activate
pytest tests/ -v --tb=short
```

- Зафиксируй: сколько passed / failed, список упавших тестов.
- Если всё зелёное — идём дальше.
- Если красное — зафиксируй трассировку, НЕ пропускай smoke, но пометь в отчёте.

### 2. Запусти Chainlit

```bash
cd /Users/ivanlardis/IdeaProjects/lardis && source venv/bin/activate && \
  nohup chainlit run app.py --headless --port 8000 > /tmp/chainlit.log 2>&1 &
sleep 4
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000
```

- Жди HTTP 200. Если нет — читай `/tmp/chainlit.log` и репорти.

### 3. Smoke через Playwright MCP

Читай сценарии из `tests/smoke/scenarios.md`. Для каждого:
1. `mcp__playwright__browser_navigate` / `_type` с `submit: true`
2. `mcp__playwright__browser_take_screenshot` → `0N-имя.png` (MCP сохраняет в рабочую папку)
3. Проверь через `mcp__playwright__browser_snapshot`, что ожидаемый текст присутствует
4. Фикси: PASS / FAIL + что увидел

После прогона — `mcp__playwright__browser_close` и перенеси скриншоты в `tests/smoke/screenshots/`.

### 4. Останови Chainlit

```bash
pkill -f "chainlit run app.py"
```

### 5. Единый отчёт

Запиши в `tests/smoke/report.md` таблицу:

```markdown
# Smoke-отчёт (YYYY-MM-DD)

## Код-тесты (pytest)
- Прошло: N / M
- Упало: список

## UI smoke
| # | Сценарий | Статус | Скриншот | Примечание |
|---|----------|--------|----------|------------|
...

**Итог:** X/Y прошли. [Что сломалось + где искать]
```

### 6. Если что-то упало — диагностика

- `pytest ... -v --tb=long` на упавших тестах.
- Для smoke — прочитай `.playwright-mcp/console-*.log` последней даты.
- Предложи гипотезу: в каком файле искать проблему.

## Правила
- Код-тесты прогоняются всегда, даже если smoke не нужен.
- Если `tests/smoke/scenarios.md` обновлён — сначала перечитай, потом гоняй.
- Не мокай LLM в интеграционных smoke — либо гоняй сценарии без обращения к LLM (команды), либо явно помечай "требует OPENROUTER_API_KEY".
- Скриншоты всегда кладутся под `tests/smoke/screenshots/0N-имя.png`.

## Контракт отчёта
Вход: ничего (читает сценарии из репо).
Выход: `tests/smoke/report.md` + код-выход `0` если всё прошло, `1` иначе.
