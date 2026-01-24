#!/usr/bin/env python3
"""
Автоматическое тестирование Chainlit UI через Playwright
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

CHAINLIT_URL = "http://localhost:8000"
TEST_FILE = "/Users/ivanlardis/IdeaProjects/lardis/ai-advent/day28/test_data/test_small.txt"
TEST_QUESTION = "Сколько ошибок ERROR?"


async def test_chainlit():
    async with async_playwright() as p:
        # Запуск браузера
        browser = await p.chromium.launch(headless=False)  # headless=False чтобы видеть
        context = await browser.new_context()
        page = await context.new_page()

        print("🚀 Открываю Chainlit...")

        # Переход на страницу
        await page.goto(CHAINLIT_URL)
        await page.wait_for_load_state("networkidle")
        print("✅ Страница загружена")

        # Ждём появления интерфейса
        await asyncio.sleep(2)

        # Ищем input для файла или drag-drop зону
        print("📁 Ищу способ загрузки файла...")

        # Попробуем найти file input
        file_input = await page.query_selector('input[type="file"]')

        if file_input:
            print("✅ Найден file input")
            await file_input.set_input_files(TEST_FILE)
            print("✅ Файл загружен")
        else:
            print("❌ File input не найден, пробуем drag-drop...")

            # Попробуем найти textarea или другое поле для ввода
            textarea = await page.query_selector('textarea[placeholder*="задайте вопрос" i], textarea[placeholder*="ask" i]')

            if not textarea:
                # Ищем любую textarea
                textarea = await page.query_selector('textarea')

            if textarea:
                print("✅ Найдена textarea, пытаемся вставить путь к файлу")
                await textarea.fill(f"Файл: {TEST_FILE}")
                await asyncio.sleep(1)

                # Имитируем нажатие Enter
                await textarea.press("Enter")
                print("✅ Отправлено")

        # Ждём загрузки файла
        await asyncio.sleep(3)

        # Делаем скриншот после загрузки файла
        await page.screenshot(path="screenshot_after_upload.png")
        print("📸 Скриншот сохранён: screenshot_after_upload.png")

        # Читаем ответ системы о загрузке
        messages = await page.query_selector_all('.markdown, .cl-Message, [class*="message"]')
        print(f"\n💬 Сообщений в чате: {len(messages)}")

        for i, msg in enumerate(messages[-3:], 1):  # Последние 3 сообщения
            try:
                text = await msg.inner_text()
                print(f"\nСообщение {i}:")
                print(text[:200])
            except:
                pass

        # Теперь ищем поле для ввода вопроса
        print(f"\n❓ Отправляю вопрос: {TEST_QUESTION}")

        # Ищем chat-input div (contenteditable)
        chat_input = await page.query_selector('#chat-input')

        if chat_input:
            await chat_input.click()
            await chat_input.fill(TEST_QUESTION)
            await asyncio.sleep(0.5)

            # Ищем кнопку submit
            submit_button = await page.query_selector('#chat-submit')

            if submit_button:
                await submit_button.click()
                print("✅ Вопрос отправлен через кнопку submit")
            else:
                # Пробуем нажать Enter
                await chat_input.press("Enter")
                print("✅ Вопрос отправлен через Enter")
        else:
            print("❌ Chat input не найден")

        # Ждём ответа от LLM
        print("⏳ Ожидаю ответа от LLM...")

        # Ждём появления нового сообщения
        await asyncio.sleep(30)  # Даём время на обработку

        # Делаем финальный скриншот
        await page.screenshot(path="screenshot_final.png")
        print("📸 Финальный скриншот: screenshot_final.png")

        # Читаем все сообщения
        messages = await page.query_selector_all('.markdown, .cl-Message, [class*="message"]')
        print(f"\n💬 Всего сообщений в чате: {len(messages)}")

        # Читаем последние 5 сообщений
        print("\n" + "="*60)
        print("ПОСЛЕДНИЕ СООБЩЕНИЯ:")
        print("="*60)

        for i, msg in enumerate(messages[-5:], 1):
            try:
                text = await msg.inner_text()
                print(f"\n--- Сообщение {i} ---")
                print(text)
            except Exception as e:
                print(f"Ошибка чтения сообщения: {e}")

        # Сохраняем HTML страницы для отладки
        html_content = await page.content()
        with open("page_content.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n📄 HTML страницы сохранён: page_content.html")

        # Не закрываем браузер сразу, даём посмотреть
        print("\n⏸️ Браузер открыт 30 секунд для визуальной проверки...")
        await asyncio.sleep(30)

        await browser.close()
        print("\n✅ Тест завершён")


if __name__ == "__main__":
    print("🎭 Запуск автоматического тестирования Chainlit UI")
    print("="*60)
    asyncio.run(test_chainlit())
