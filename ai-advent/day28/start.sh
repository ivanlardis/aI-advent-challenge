#!/bin/bash
# Стартовый скрипт для Локального аналитика данных

cd "$(dirname "$0")"

echo "🔍 Проверка зависимостей..."
if ! python3 -c "import chainlit" 2>/dev/null; then
    echo "❌ Chainlit не установлен"
    echo "Установите зависимости: pip install -r requirements.txt"
    exit 1
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo "❌ Requests не установлен"
    echo "Установите зависимости: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Все зависимости установлены"
echo ""
echo "🚀 Запуск приложения..."
echo "Откройте в браузере: http://localhost:8000"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

python3 -m chainlit run app.py -h
