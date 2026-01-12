package llm

import rag.SearchResult

/**
 * Построение промптов с контекстом из RAG
 */
object PromptBuilder {
    /**
     * Построить список сообщений для LLM с контекстом из RAG
     */
    fun buildMessages(query: String, ragResults: List<SearchResult>): List<Message> {
        val context = if (ragResults.isEmpty()) {
            "Контекст из проекта не найден."
        } else {
            ragResults.joinToString("\n\n") { result ->
                """
                Файл: ${result.document.filePath}
                Релевантность: ${"%.2f".format(result.score)}

                ${result.document.content.take(1000)}
                """.trimIndent()
            }
        }

        return listOf(
            Message(
                role = "system",
                content = """
                Ты - ассистент для разработчика. Отвечай на вопросы по проекту на основе предоставленного контекста.

                Контекст из проекта:
                $context

                Отвечай четко, по существу. Если контекст не содержит информации для ответа, так и скажи.
                """.trimIndent()
            ),
            Message(
                role = "user",
                content = query
            )
        )
    }
}
