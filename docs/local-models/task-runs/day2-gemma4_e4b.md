# day2 — gemma4:e4b

- Время (wall): **20.05s**
- Токенов в ответе: **1270**
- Скорость: **66.6 tok/s**

## Промпт

```
Пользователь жалуется: команда `/summary` всегда показывает 0 токенов,
хотя диалог идёт. Найди причину и предложи фикс.

Контекст кода:
```python
# app.py (релевантный фрагмент)

async def handle_summary_command(usage_history: List[Dict]):
    if not usage_history:
        await cl.Message(content="Пока нет данных по токенам.").send()
        return
    total = sum(item.get("total", 0) for item in usage_history)
    lines = ["**Статистика токенов:**\n", "| # | Сообщение | Токены |", "|---|-----------|--------|"]
    for idx, item in enumerate(usage_history, 1):
        preview = item.get("message", "")[:30]
        tokens = item.get("total", 0)
        lines.append(f"| {idx} | {preview}... | {tokens} |")
    lines.append(f"\n**Всего:** {total} токенов")
    await cl.Message(content="\n".join(lines)).send()

# lib/analytics.py — как пишется запись:
# record = {"total_tokens": prompt_tokens + completion_tokens, "input_preview": ...}
# analytics_list.append(record)

```
```

## Ответ модели

## Что нашёл
Причина бага кроется в несоответствии ключей, используемых для хранения и извлечения данных о токенах.

В файле `lib/analytics.py` (или там, где происходит запись истории), данные о суммарном количестве токенов сохраняются под ключом `"total_tokens"`:
```python
# record = {"total_tokens": prompt_tokens + completion_tokens, "input_preview": ...}
```

Однако в функции `handle_summary_command` в `app.py` код пытается извлечь это значение, используя ключ `"total"`:
```python
# total = sum(item.get("total", 0) for item in usage_history) # Ищет "total"
# ...
# tokens = item.get("total", 0) # Ищет "total"
```
Поскольку ключ `"total"` отсутствует в словаре `item`, метод `.get("total", 0)` всегда возвращает значение по умолчанию, то есть `0`, что и приводит к отображению нулевой статистики.

## Что починить
Необходимо обновить все обращения к ключу токенов в `app.py` с `"total"` на `"total_tokens"`.

**app.py (диф):**

```diff
--- a/app.py
+++ b/app.py
@@ -2,11 +2,11 @@
 
 async def handle_summary_command(usage_history: List[Dict]):
     if not usage_history:
         await cl.Message(content="Пока нет данных по токенам.").send()
-    total = sum(item.get("total", 0) for item in usage_history)
+    total = sum(item.get("total_tokens", 0) for item in usage_history)
     lines = ["**Статистика токенов:**\n", "| # | Сообщение | Токены |", "|---|-----------|--------|"]
     for idx, item in enumerate(usage_history, 1):
         preview = item.get("message", "")[:30]
-        tokens = item.get("total", 0)
+        tokens = item.get("total_tokens", 0)
         lines.append(f"| {idx} | {preview}... | {tokens} |")
     lines.append(f"\n**Всего:** {total} токенов")
     await cl.Message(content="\n".join(lines)).send()
```

## Что проверить
1.  **Проверка данных:** Убедитесь, что в тестовом диалоге, который вы используете для тестирования `/summary`, действительно были записаны данные с ключом `"total_tokens"` (например, 100, 50 и т.д.).
2.  **Тестирование:** Выполните команду `/summary` после проведения диалога. Ожидаемый результат — отображение корректных, ненулевых значений токенов для каждой записи и правильная сумма в итоговой строке.
3.  **Проверка зависимостей:** Проверьте, что в коде, который записывает историю (в `lib/analytics.py`), ключ действительно называется `"total_tokens"`, и что этот ключ всегда присутствует при записи.
