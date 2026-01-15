package config

/**
 * Конфигурация приложения с константами
 */
object Config {
    // OpenRouter API
    val OPENROUTER_API_KEY = "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"
    const val OPENROUTER_MODEL = "x-ai/grok-4.1-fast"
    const val OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    // GitHub
    val GITHUB_TOKEN = System.getenv("GITHUB_TOKEN") ?: ""
    val GITHUB_REPOSITORY = System.getenv("GITHUB_REPOSITORY") ?: ""

    // RAG настройки
    const val RAG_TOP_K = 10 // количество релевантных документов для поиска
    const val RAG_MIN_SIMILARITY = 0.01 // минимальное косинусное сходство для фильтрации

    // Поддерживаемые расширения файловсле
    val SUPPORTED_EXTENSIONS = setOf("kt", "java", "md")

    // Review limits
    const val REVIEW_MAX_FILES = 30 // максимум файлов для анализа
    const val REVIEW_MAX_LINES_PER_FILE = 500 // максимум строк на файл
}
