# local-llm-cli

Простой CLI-клиент на Kotlin для взаимодействия с локальной LLM через Ollama API.

## Требования

- Ollama запущена на `localhost:11434`
- Java/JDK 17+

## Сборка

```bash
./gradlew jar
```

JAR будет создан в `build/libs/local-llm-cli.jar`

## Использование

```bash
# Запрос с первой доступной моделью
java -jar build/libs/local-llm-cli.jar "Составь список из 5 идей для ужина."

# Запрос с конкретной моделью
java -jar build/libs/local-llm-cli.jar "Кто написал Войну и мир?" -m gemma3:1b

# Список доступных моделей
java -jar build/libs/local-llm-cli.jar -l

# Справка
java -jar build/libs/local-llm-cli.jar -h
```

## Структура проекта

```
.
├── build.gradle.kts          # Конфигурация Gradle
├── settings.gradle.kts       # Настройки проекта
├── src/main/kotlin/Main.kt  # Основной код (один файл)
└── SPEC.md                   # Спецификация
```

## API Ollama

### GET /api/tags
Возвращает список доступных моделей.

### POST /api/generate
Генерирует ответ на запрос. Тело запроса:
```json
{
  "model": "gemma3:1b",
  "prompt": "Вопрос",
  "stream": false
}
```

## Зависимости

- Kotlin 1.9.22
- Ktor Client 2.3.7
- kotlinx-serialization-json 1.6.0
