# Smoke-отчёт (Day 3)

**Дата прогона:** 2026-04-16
**Среда:** Chainlit `http://localhost:8000`, headless, Playwright MCP
**Агент:** Claude Code (этот репо)

| # | Сценарий          | Статус | Скриншот                        | Примечание                                         |
|---|-------------------|:------:|---------------------------------|----------------------------------------------------|
| 1 | Welcome           | PASS   | `screenshots/01-welcome.png`    | «Привет, Иван!» + список из 5 команд              |
| 2 | /dashboard        | PASS   | `screenshots/02-dashboard.png`  | «Дашборд статистики», нет данных                   |
| 3 | /summary          | PASS   | `screenshots/03-summary.png`    | «Пока нет данных по токенам»                       |
| 4 | /profile (new)    | PASS   | `screenshots/04-profile.png`    | «Профиль: Иван», 4 секции                          |
| 5 | /reset (new)      | PASS   | `screenshots/05-reset.png`      | «Сброшено. История и статистика очищены»           |

**Итог:** 5/5 сценариев прошли с первого прогона. Консоль браузера — 0 ошибок.
