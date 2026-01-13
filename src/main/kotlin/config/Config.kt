package config

/**
 * Конфигурация приложения с константами
 */
object Config {
    // OpenRouter API
    val OPENROUTER_API_KEY = System.getenv("OPENROUTER_API_KEY")
        ?: "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"
    const val OPENROUTER_MODEL = "x-ai/grok-4.1-fast"
    const val OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    // GitHub
    val GITHUB_TOKEN = System.getenv("GITHUB_TOKEN") ?: ""
    val GITHUB_REPOSITORY = System.getenv("GITHUB_REPOSITORY") ?: ""

    // RAG настройки
    const val RAG_TOP_K = 10 // количество релевантных документов для поиска
    const val RAG_MIN_SIMILARITY = 0.01 // минимальное косинусное сходство для фильтрации

    // Поддерживаемые расширения файлов
    val SUPPORTED_EXTENSIONS = setOf("kt", "java", "md")

    // Review limits
    const val REVIEW_MAX_FILES = 30 // максимум файлов для анализа
    const val REVIEW_MAX_LINES_PER_FILE = 500 // максимум строк на файл

    const val ТЕСТ_пр_ai_КОДЕ_ресью = 50011
}
