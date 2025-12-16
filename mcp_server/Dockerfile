FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 1221
CMD ["uvicorn", "weather_server:app", "--host", "0.0.0.0", "--port", "1221"]