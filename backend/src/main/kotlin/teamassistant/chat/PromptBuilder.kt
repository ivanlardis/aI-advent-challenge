package teamassistant.chat

/**
 * Builds prompts for the LLM based on user message, context, and chat history.
 */
object PromptBuilder {

    /**
     * Build a complete prompt for the LLM.
     */
    fun build(
        userMessage: String,
        context: String?,
        history: List<ChatMessage>
    ): String {
        val sb = StringBuilder()

        // System prompt
        sb.appendLine(SYSTEM_PROMPT)
        sb.appendLine()

        // Context (if available)
        if (!context.isNullOrBlank()) {
            sb.appendLine("## Контекст проекта")
            sb.appendLine(context)
            sb.appendLine()
        }

        // Chat history (last 3 messages for context to reduce token usage)
        if (history.isNotEmpty()) {
            sb.appendLine("## История диалога")
            history.takeLast(3).forEach { msg ->
                val role = when (msg.role) {
                    "user" -> "Пользователь"
                    "assistant" -> "Ассистент"
                    else -> msg.role
                }
                sb.appendLine("$role: ${msg.content}")
            }
            sb.appendLine()
        }

        // Current request
        sb.appendLine("## Текущий запрос")
        sb.appendLine(userMessage)

        return sb.toString()
    }

    /**
     * System prompt that defines the assistant's behavior.
     */
    private val SYSTEM_PROMPT = """
Ты - Team Assistant, AI-помощник для разработки программного обеспечения.

У тебя есть доступ к:
1. Документации проекта (через RAG)
2. GitHub Issues (чтение и создание)
3. Системе приоритизации задач

Твои возможности:
- Отвечать на вопросы о коде, архитектуре, документации проекта
- Анализировать текущие задачи и их приоритеты
- Создавать новые задачи в GitHub по запросу пользователя
- Рекомендовать следующие шаги

Формат ответа:
- Используй Markdown для форматирования
- Для кода используй ```язык
- Будь кратким и по существу
- Если создаёшь задачу, укажи это явно: "✅ Создана задача: #123"

Примеры запросов:
- "Как работает RAG в этом проекте?"
- "Какие задачи сейчас наиболее приоритетны?"
- "Создай задачу: добавить логирование в UserService"
- "Что нужно сделать следующим?"
""".trimIndent()
}
