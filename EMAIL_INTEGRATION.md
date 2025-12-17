# Интеграция Mailtrap для отправки Email

## Описание

Проект интегрирован с [Mailtrap](https://mailtrap.io) для отправки email сообщений через API.

## Настройка

### 1. Получение API токена

1. Зарегистрируйтесь на [mailtrap.io](https://mailtrap.io)
2. Перейдите в **Settings → API Tokens**
3. Скопируйте токен (или создайте новый)

### 2. Конфигурация .env

Добавьте следующие переменные в файл `.env`:

```env
# Mailtrap API
MAILTRAP_API_TOKEN=ваш_токен_здесь
MAILTRAP_SENDER_EMAIL=hello@demomailtrap.com
MAILTRAP_SENDER_NAME=Lardis Bot
SUMMARY_EMAIL_TO=получатель@example.com
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

## Использование

### Простая отправка текстового email

```python
from app.email_sender import send_simple_email

send_simple_email(
    to_email="recipient@example.com",
    subject="Привет!",
    text="Это тестовое письмо",
    category="Test"
)
```

### Отправка HTML email

```python
from app.email_sender import EmailSender

sender = EmailSender()

html_content = """
<html>
    <body>
        <h1>Привет!</h1>
        <p>Это HTML письмо</p>
    </body>
</html>
"""

sender.send_email(
    to_email="recipient@example.com",
    subject="HTML письмо",
    text="Текстовая версия",
    html=html_content,
    category="HTML Email"
)
```

### Отправка нескольким получателям

```python
from app.email_sender import EmailSender

sender = EmailSender()

recipients = [
    "user1@example.com",
    "user2@example.com",
    "user3@example.com"
]

sender.send_to_multiple(
    to_emails=recipients,
    subject="Рассылка",
    text="Сообщение для всех",
    category="Broadcast"
)
```

## Запуск примеров

В проекте есть готовый файл с примерами:

```bash
python3 example_send_email.py
```

Этот скрипт демонстрирует:
- Отправку простого текстового письма
- Отправку HTML письма
- Рассылку нескольким получателям

## Структура модуля

### `app/email_sender.py`

Основной модуль содержит:

- **`EmailSender`** — класс для отправки email
  - `send_email()` — отправка одному получателю
  - `send_to_multiple()` — отправка нескольким получателям

- **`send_simple_email()`** — удобная функция для быстрой отправки

## Категории email

Категории используются для аналитики в Mailtrap:

- `"General"` — общие письма
- `"Test"` — тестовые письма
- `"Broadcast"` — массовые рассылки
- `"Notification"` — уведомления
- Любые другие категории по вашему усмотрению

## Обработка ошибок

```python
from app.email_sender import EmailSender

sender = EmailSender()

try:
    response = sender.send_email(
        to_email="test@example.com",
        subject="Test",
        text="Test message"
    )
    print(f"Email отправлен: {response}")
except ValueError as e:
    print(f"Ошибка конфигурации: {e}")
except Exception as e:
    print(f"Ошибка отправки: {e}")
```

## Ограничения Mailtrap

- **Free plan**: до 1000 писем/месяц
- **Sandbox**: для тестирования (письма не доставляются реально)
- **Production**: для реальной отправки требуется настройка домена

Подробнее на [Mailtrap Pricing](https://mailtrap.io/pricing/)

## Полезные ссылки

- [Документация Mailtrap API](https://api-docs.mailtrap.io/)
- [Python библиотека Mailtrap](https://github.com/railsware/mailtrap-python)
- [Dashboard Mailtrap](https://mailtrap.io/inboxes)
