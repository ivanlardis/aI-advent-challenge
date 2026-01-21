FROM python:3.9

# Установка зависимостей для Ollama
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Установка Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Копирование Python кода
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY chainlit.md .

# Скачивание модели gemma2:2b во время сборки
RUN ollama serve & sleep 5 && ollama pull gemma2:2b && pkill ollama

# Экспозиция порта
EXPOSE 8000

# Запуск Ollama в фоне и Chainlit на переднем плане
CMD sh -c 'ollama serve > /dev/null 2>&1 & cd /app && PYTHONPATH=/app chainlit run app/chainlit_app.py --host 0.0.0.0 --port 8000'
