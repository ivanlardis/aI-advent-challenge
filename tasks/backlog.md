# Backlog — Day 5 Execution Loop

Пул из 18 задач для автономного прогона. Микс: 4 bug / 4 feature / 4 refactor / 3 test / 3 doc.
Критерий "сделано": по задаче есть коммит в git, acceptance выполнен.

Формат строки: `- [ ] T-NN | тип | описание — **Acceptance:** <критерий>`

## Bug (4)

- [x] T-01 | bug | `handle_summary_command` читает ключ `"total"`, а `Analytics.record_usage` пишет `"total_tokens"` — таблица `/summary` всегда показывает 0. Починить в `app.py`. — **Acceptance:** после фикса все `item.get("total", 0)` в `app.py` заменены на `item.get("total_tokens", 0)`; если есть тесты на `handle_summary_command` — проходят; если нет — добавить минимальный unit-тест парсинга usage_history.
- [x] T-02 | bug | `OpenRouterClient.chat_completion` и `stream_completion` принимают параметр `temperature`, но не передают его в LangChain-клиент (используется температура из `__init__`, фиксированная). — **Acceptance:** вызов `chat_completion(msgs, temperature=0.7)` реально применяет 0.7 (через `self.llm.bind(temperature=temperature).ainvoke(...)` или эквивалент); юнит-тест с моком проверяет что переданная температура достигает клиента; `pytest tests/` зелёный.
- [x] T-03 | bug | `extract_name` в `lib/profile.py` при пустом значении поля (`- **Имя:** ` — пробел после двоеточия без имени) возвращает пустую строку, а должен — `"Пользователь"`. — **Acceptance:** `extract_name("- **Имя:** \n")` → `"Пользователь"`; юнит-тест добавлен в `tests/test_profile.py`; `pytest tests/test_profile.py` зелёный.
- [x] T-04 | bug | `handle_compress_command` в `app.py` обрезает контент сообщения через `[:200]` без индикатора многоточия — если сообщение длиннее 200 символов, пользователь не видит что было обрезано. — **Acceptance:** добавить суффикс `"..."` при обрезке; простой unit-тест на helper-функцию обрезки (если выделять) или проверка через `format`-строку.

## Feature (4)

- [x] T-05 | feature | Команда `/help` — выводит список всех команд в виде таблицы (markdown). Должна работать в любой момент после `on_chat_start`. — **Acceptance:** команда зарегистрирована в `on_message`; хендлер `handle_help_command` в `app.py`; в welcome-сообщении `/help` упомянут; тест в `test_app_commands.py` проверяет факт экспорта хендлера.
- [x] T-06 | feature | Команда `/version` — возвращает имя модели из переменной окружения `OPENROUTER_MODEL` (fallback: `anthropic/claude-3.5-sonnet`). — **Acceptance:** `/version` отвечает `Модель: <имя>` через `cl.Message`; хендлер `handle_version_command`; тест на факт экспорта.
- [x] T-07 | feature | В `Analytics.format_dashboard` добавить строку "Средняя длина ответа (символов): `<число>`" после "Среднее на сообщение". — **Acceptance:** в output `format_dashboard` есть эта строка; существующие тесты `test_analytics.py` зелёные; один новый тест на эту строку.
- [x] T-08 | feature | Команда `/clear` — алиас для `/reset` (делает то же самое). — **Acceptance:** `/clear` в `on_message` вызывает `handle_reset_command`; тест проверяет что `/clear` распарсится и попадёт в ту же ветку.

## Refactor (4)

- [x] T-09 | refactor | Вынести константу `DEFAULT_USER_NAME = "Пользователь"` в `lib/profile.py` на уровень модуля. Заменить все литералы `"Пользователь"` в этом модуле на константу. — **Acceptance:** константа объявлена; литералов в теле модуля не осталось; существующие тесты зелёные.
- [x] T-10 | refactor | В `app.py` роутинг команд через dict: `COMMANDS = {"/compress": handle_compress_command, "/summary": handle_summary_command, ...}` вместо каскада `if/elif`. — **Acceptance:** dict создан на уровне модуля; ветка команд в `on_message` использует `if cmd in COMMANDS: await COMMANDS[cmd](...)`; поведение не изменилось; `pytest tests/` зелёный.
- [x] T-11 | refactor | Вынести welcome-текст из `on_chat_start` в функцию `build_welcome_message(user_name: str, profile_loaded: bool) -> str` в `app.py` или в `lib/welcome.py`. — **Acceptance:** функция существует, юнит-тест на неё (без вызова Chainlit); `on_chat_start` использует её.
- [ ] T-12 | refactor | В `lib/openrouter_client.py:build_messages` упростить сборку списка: заменить `for item in history: messages.append(item)` на `messages.extend(history)`. — **Acceptance:** замена выполнена, существующие тесты зелёные.

## Test (3)

- [ ] T-13 | test | Добавить тест `test_trim_keeps_system_when_max_tokens_zero` в `tests/test_history.py` — проверяет, что `trim_history` с `max_tokens=0` сохраняет сообщения роли `"system"` и удаляет остальное. — **Acceptance:** тест написан; `pytest tests/test_history.py -v` зелёный.
- [ ] T-14 | test | В `tests/test_analytics.py` добавить тест `test_get_stats_empty_list` — `Analytics.get_stats([])` возвращает словарь с `message_count=0` и `total_tokens=0`. Если похожий тест уже есть — зафиксировать acceptance как "выполнено, тест существует". — **Acceptance:** тест существует и зелёный.
- [ ] T-15 | test | В `tests/test_profile.py` добавить тест `test_extract_name_empty_profile` — `extract_name("")` возвращает `"Пользователь"`. — **Acceptance:** тест написан; `pytest tests/test_profile.py -v` зелёный.

## Doc (3)

- [ ] T-16 | doc | В `lib/history.py` docstring функции `estimate_tokens` дописать примечание: "Очень грубая оценка, завышает для русского текста (слово ≠ токен для кириллицы)." — **Acceptance:** docstring обновлён; модуль импортируется без ошибок.
- [ ] T-17 | doc | Создать `docs/commands.md` — справочник команд: таблица `команда | описание | пример вывода`. Для всех команд приложения. — **Acceptance:** файл существует, содержит таблицу минимум для 5 базовых команд.
- [ ] T-18 | doc | В `CLAUDE.md` lardis в секции "Паттерн команды" обновить пример — добавить упоминание dict-роутинга (если T-10 сделана) или оставить текущий пример как fallback. — **Acceptance:** секция существует и не противоречит текущему коду `app.py`.
