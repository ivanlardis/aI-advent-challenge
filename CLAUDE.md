# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Команды разработки

### Сборка и запуск
```bash
# Полная сборка с созданием fat JAR
./gradlew clean build shadowJar

# Запуск в dev режиме
./gradlew run --args="--home /path/to/project"

# Запуск тестов
./gradlew test

# Запуск собранного JAR
java -jar build/libs/project-assistant-1.0.0.jar --home /path/to/project

# PR Review локально
export OPENROUTER_API_KEY="your-key"
export GITHUB_TOKEN="your-github-token"
java -jar build/libs/project-assistant-*.jar review-pr --pr-number=123
```

### Требования
- JDK 17+
- Gradle 8.x

## Архитектура проекта

### Два основных режима

**1. RAG Assistant** (интерактивный CLI)
- Запускается по умолчанию через `AssistantCommand`
- Индексирует документацию проекта (.kt, .java, .md файлы)
- Отвечает на вопросы с использованием RAG (Retrieval Augmented Generation)

**2. PR Review** (анализ Pull Request)
- Запускается через `review-pr` команду: `java -jar app.jar review-pr --pr-number=N`
- Автоматически запускается через GitHub Actions
- Анализирует изменения в PR и публикует комментарии

### RAG Pipeline

```
DocumentIndexer → OnnxEmbeddingVectorizer → InMemoryVectorStore → RagService
       ↓                    ↓                          ↓                ↓
  Парсинг файлов      Векторизация ONNX         Поиск по схожести   Поиск контекста
  (.kt, .java, .md)   (Sentence Transformers)   (косинусное)       для LLM
```

**Ключевые компоненты:**
- `rag/DocumentIndexer` - сканирует файлы и разбивает на чанки
- `rag/embeddings/OnnxEmbeddingVectorizer` - векторизация через ONNX Runtime
- `rag/InMemoryVectorStore` - in-memory хранилище векторов с поиском
- `rag/RagService` - оркестрация поиска релевантных документов
- `parser/` - специализированные парсеры (KotlinParser, JavaParser, MarkdownParser)

### PR Review Pipeline

```
GitDiffExtractor → PRAnalysisService → ReviewPromptBuilder → LLM → GitHubCommentPublisher
       ↓                  ↓                    ↓                ↓            ↓
  gh CLI diff       Анализ изменений    Формирование      Генерация    Публикация
                    с лимитами          промпта           ревью        комментария
```

**Ключевые компоненты:**
- `review/GitDiffExtractor` - получает diff через GitHub CLI (`gh pr diff`)
- `review/PRAnalysisService` - основная логика анализа с лимитами
- `review/ReviewPromptBuilder` - формирует структурированный промпт для LLM
- `review/GitHubCommentPublisher` - публикует результат в PR через `gh` CLI

### LLM Integration

**OpenRouter Client:**
- `llm/OpenRouterClient` - HTTP клиент (Ktor)
- Использует модель `x-ai/grok-4.1-fast`
- Базовый URL: `https://openrouter.ai/api/v1`

## Конфигурация

**Файл:** `src/main/kotlin/config/Config.kt`

**Ключевые параметры:**
```kotlin
// OpenRouter API
OPENROUTER_API_KEY = "sk-or-v1-..."  // 🔴 ИЗМЕНИТЬ ПЕРЕД КОММИТОМ!
OPENROUTER_MODEL = "x-ai/grok-4.1-fast"

// RAG настройки
RAG_TOP_K = 10                    // количество релевантных документов
RAG_MIN_SIMILARITY = 0.01         // минимальное косинусное сходство

// Review лимиты
REVIEW_MAX_FILES = 30                    // максимум файлов для анализа
REVIEW_MAX_LINES_PER_FILE = 500          // максимум строк на файл

// Поддерживаемые расширения
SUPPORTED_EXTENSIONS = setOf("kt", "java", "md")
```

**Переменные окружения (для PR Review):**
- `OPENROUTER_API_KEY` - API ключ OpenRouter
- `GITHUB_TOKEN` - GitHub токен для публикации комментариев
- `GITHUB_REPOSITORY` - репозиторий в формате owner/repo

## CI/CD

**Файл:** `.github/workflows/pr-review.yml`

- Триггеры: PR events (opened, synchronize, reopened)
- Сборка JAR → запуск PR Review → публикация комментария
- Требуется секрет `OPENROUTER_API_KEY` в GitHub repository settings

## Структура пакетов

```
src/main/kotlin/
├── Main.kt                    # Точка входа (роутинг команд)
├── config/
│   └── Config.kt              # Центральная конфигурация
├── cli/
│   ├── AssistantCommand.kt    # Интерактивный RAG режим
│   └── ReviewCommand.kt       # CLI для PR Review
├── rag/                       # RAG система
├── review/                    # PR Review модуль
├── llm/                       # LLM клиенты
├── parser/                    # Парсеры файлов
├── mcp/                       # MCP интеграция
└── resources/models/          # ONNX модели (Sentence Transformers)
```

## Важные файлы

**Основной код:**
- `Main.kt:7-15` - роутинг между AssistantCommand и ReviewCommand
- `config/Config.kt:6-26` - все константы конфигурации
- `rag/RagService.kt:9-24` - оркестрация RAG поиска
- `review/PRAnalysisService.kt:19-68` - основной цикл анализа PR

**Сборка:**
- `build.gradle.kts` - зависимости и конфигурация Shadow JAR
- `settings.gradle.kts` - имя проекта

**CI/CD:**
- `.github/workflows/pr-review.yml` - GitHub Actions workflow
