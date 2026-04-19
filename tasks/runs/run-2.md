# Run 2 (после тюнинга)

**Started:** 2026-04-19 09:34:10
**Finished:** 2026-04-19 09:36:20
**Branch:** loop-run-2
**Skill version:** с доработанным AST-проверка декораторов + запрет bug-fix агенту править существующие тесты
**Способ:** cherry-pick 18 коммитов из `loop-run-1` на чистый `main` + прогон обновлённой AST-проверки декораторов.

## Зачем cherry-pick, а не повторный полный прогон

Run-1 закрыл 18/18 без падения — "где сломается и насколько дольше продержится во втором прогоне" измерить невозможно (упёрлись в верхний край ещё в baseline). Смысл run-2 — **проверить, что тюнинг реально ловит класс ошибок**, на котором loop в run-1 чуть не упал (T-11, стёртый декоратор `@cl.on_chat_start`).

## Log

| ID | тип | способ | result | commit | заметки |
|----|-----|--------|--------|--------|---------|
| T-01 | bug | cherry-pick 8e138d1 | OK | d… | `/summary` keys |
| T-02 | bug | cherry-pick c54a0bc | OK | … | OpenRouterClient.bind(temperature) |
| T-03 | bug | cherry-pick 9a67020 | OK | … | extract_name fallback |
| T-04 | bug | cherry-pick 6d08487 | OK | … | truncate_preview |
| T-05 | feature | cherry-pick e2909e1 | OK | … | /help + format_help |
| T-06 | feature | cherry-pick b15d098 | OK | … | /version |
| T-07 | feature | cherry-pick 4ab0f0b | OK | … | avg_response_length |
| T-08 | feature | cherry-pick 12791e0 | OK | … | /clear |
| T-09 | refactor | cherry-pick 8c38809 | OK | … | DEFAULT_USER_NAME |
| T-10 | refactor | cherry-pick cc9a2ef | OK | … | dict-роутинг |
| T-11 | refactor | cherry-pick 01f5107 + AST-проверка | OK | … | **AST-проверка теперь ловит run-1 сценарий (стёртый декоратор) — exit=1.** |
| T-12 | refactor | cherry-pick 25a601e | OK | … | extend(history) |
| T-13 | test | cherry-pick 77aa214 | OK | … | trim max_tokens=0 |
| T-14 | test | cherry-pick 287cbb3 | OK | … | get_stats zeros |
| T-15 | test | cherry-pick 89c8fb6 | OK | … | extract_name empty |
| T-16 | doc | cherry-pick 7483776 | OK | … | estimate_tokens docstring |
| T-17 | doc | cherry-pick 5ec2c1f | OK | … | docs/commands.md |
| T-18 | doc | cherry-pick 1dcf0f4 | OK | … | CLAUDE.md dict-роутинг |

## Симуляция T-11 на AST-проверке

```
$ python <(ast-check on текущем app.py) → "app.py decorators OK"
$ # удаляем @cl.on_chat_start
$ python <(ast-check на сломанном app.py) → "BROKEN decorators missing for: ['on_chat_start']" exit=1
$ pytest tests/ → 45 passed (сам pytest не ловит)
```

**Ключевой урок:** первоначальный тюнинг (smoke-импорт `from app import on_chat_start`) **не ловил** стёртый декоратор — функция остаётся объектом в модуле, импорт проходит. Обнаружилось это только при практической симуляции в run-2. Тюнинг доработан до AST-проверки наличия `@cl.on_chat_start` / `@cl.on_message`.

## Итог run-2

- **Прошёл подряд без паузы:** 18 / 18 (cherry-pick без конфликтов)
- **Закрыто:** 18 / 18 (100%)
- **Сломался на:** —
- **Wall-time run-2:** ~2 минуты (cherry-pick 18 коммитов + pytest + AST-проверка)
- **First-try:** 100%
- **Главный результат:** AST-проверка декораторов вычислена и верифицирована. Первоначальный smoke-импорт оказался недостаточным — доработано на практике.

## Сравнение run-1 vs run-2

| Метрика | run-1 (baseline) | run-2 (после тюнинга) |
|---------|------------------|----------------------|
| Задач подряд без паузы | 18 | 18 |
| Закрыто всего | 18 / 18 | 18 / 18 |
| Wall-time | 32 мин | ~2 мин (cherry-pick) |
| First-try | 100% | 100% |
| Околопадение | T-11 (визуально поймал) | — (AST-проверка поймала бы автоматически) |

**Вывод:** оба прогона достигли потолка задачи. Разница в времени не показательна (run-2 — replay). Реальная ценность тюнинга — **AST-проверка ловит класс ошибок, которые pytest+import молча пропускают**. На следующем пуле задач, где рефакторинг трогает `app.py`, защита будет работать автоматически.
