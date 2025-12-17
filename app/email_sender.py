"""
Модуль для отправки email через Mailtrap API
"""
import os
from typing import Optional, List
import mailtrap as mt


class EmailSender:
    """Класс для отправки email через Mailtrap"""

    def __init__(self):
        """Инициализация клиента Mailtrap из переменных окружения"""
        self.api_token = os.getenv('MAILTRAP_API_TOKEN')
        self.sender_email = os.getenv('MAILTRAP_SENDER_EMAIL', 'hello@demomailtrap.com')
        self.sender_name = os.getenv('MAILTRAP_SENDER_NAME', 'Lardis Bot')

        if not self.api_token:
            raise ValueError("MAILTRAP_API_TOKEN не установлен в .env файле")

        self.client = mt.MailtrapClient(token=self.api_token)

    def send_email(
        self,
        to_email: str,
        subject: str,
        text: Optional[str] = None,
        html: Optional[str] = None,
        category: str = "General"
    ) -> dict:
        """
        Отправить email через Mailtrap

        Args:
            to_email: Email получателя
            subject: Тема письма
            text: Текстовое содержимое (опционально)
            html: HTML содержимое (опционально)
            category: Категория письма для аналитики

        Returns:
            Ответ от Mailtrap API
        """
        mail = mt.Mail(
            sender=mt.Address(email=self.sender_email, name=self.sender_name),
            to=[mt.Address(email=to_email)],
            subject=subject,
            text=text,
            html=html,
            category=category,
        )

        response = self.client.send(mail)
        return response

    def send_to_multiple(
        self,
        to_emails: List[str],
        subject: str,
        text: Optional[str] = None,
        html: Optional[str] = None,
        category: str = "General"
    ) -> dict:
        """
        Отправить email нескольким получателям

        Args:
            to_emails: Список email получателей
            subject: Тема письма
            text: Текстовое содержимое (опционально)
            html: HTML содержимое (опционально)
            category: Категория письма

        Returns:
            Ответ от Mailtrap API
        """
        mail = mt.Mail(
            sender=mt.Address(email=self.sender_email, name=self.sender_name),
            to=[mt.Address(email=email) for email in to_emails],
            subject=subject,
            text=text,
            html=html,
            category=category,
        )

        response = self.client.send(mail)
        return response


# Удобная функция для быстрой отправки
def send_simple_email(to_email: str, subject: str, text: str, category: str = "General") -> dict:
    """
    Быстрая отправка простого текстового email

    Args:
        to_email: Email получателя
        subject: Тема письма
        text: Текст письма
        category: Категория письма

    Returns:
        Ответ от Mailtrap API
    """
    sender = EmailSender()
    return sender.send_email(to_email, subject, text=text, category=category)
