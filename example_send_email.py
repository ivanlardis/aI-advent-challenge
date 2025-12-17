"""
Пример использования модуля отправки email через Mailtrap
"""
import os
from dotenv import load_dotenv
from app.email_sender import EmailSender, send_simple_email

# Загружаем переменные окружения
load_dotenv()


def example_simple_send():
    """Пример простой отправки текстового email"""
    print("📧 Отправка простого текстового email...")

    try:
        response = send_simple_email(
            to_email=os.getenv('SUMMARY_EMAIL_TO', 'ivan24031993@gmail.com'),
            subject="Тестовое письмо от Lardis Bot",
            text="Привет! Это тестовое письмо, отправленное через Mailtrap API.",
            category="Test"
        )
        print(f"✅ Email отправлен успешно! Ответ: {response}")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")


def example_html_send():
    """Пример отправки HTML email"""
    print("\n📧 Отправка HTML email...")

    sender = EmailSender()

    html_content = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h1 style="color: #4CAF50;">Привет от Lardis Bot!</h1>
            <p>Это <strong>HTML письмо</strong>, отправленное через Mailtrap.</p>
            <ul>
                <li>✅ Интеграция работает</li>
                <li>✅ Email доставлен</li>
                <li>✅ Все отлично!</li>
            </ul>
            <hr>
            <p style="color: #999; font-size: 12px;">
                Отправлено автоматически через Mailtrap API
            </p>
        </body>
    </html>
    """

    try:
        response = sender.send_email(
            to_email=os.getenv('SUMMARY_EMAIL_TO', 'ivan24031993@gmail.com'),
            subject="HTML письмо от Lardis Bot",
            text="Это текстовая версия письма для клиентов без поддержки HTML",
            html=html_content,
            category="Test HTML"
        )
        print(f"✅ HTML Email отправлен! Ответ: {response}")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")


def example_multiple_recipients():
    """Пример отправки письма нескольким получателям"""
    print("\n📧 Отправка письма нескольким получателям...")

    sender = EmailSender()

    recipients = [
        os.getenv('SUMMARY_EMAIL_TO', 'ivan24031993@gmail.com'),
        # Можно добавить дополнительных получателей
    ]

    try:
        response = sender.send_to_multiple(
            to_emails=recipients,
            subject="Рассылка от Lardis Bot",
            text="Это письмо отправлено нескольким получателям одновременно!",
            category="Broadcast"
        )
        print(f"✅ Рассылка отправлена! Ответ: {response}")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Примеры отправки email через Mailtrap")
    print("=" * 60)

    # Проверяем наличие токена
    if not os.getenv('MAILTRAP_API_TOKEN'):
        print("❌ ОШИБКА: MAILTRAP_API_TOKEN не установлен в .env файле!")
        print("\n📝 Инструкция:")
        print("1. Зарегистрируйтесь на https://mailtrap.io")
        print("2. Получите API Token в Settings → API Tokens")
        print("3. Добавьте токен в .env файл:")
        print("   MAILTRAP_API_TOKEN=ваш_токен_здесь")
        exit(1)

    # Запускаем примеры
    example_simple_send()
    example_html_send()
    example_multiple_recipients()

    print("\n" + "=" * 60)
    print("✅ Все примеры выполнены!")
    print("=" * 60)
