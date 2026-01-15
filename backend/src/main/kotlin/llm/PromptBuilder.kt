package llm

import rag.SearchResult

/**
 * Построение промптов с контекстом из RAG
 */
object PromptBuilder {
    /**
     * Построить список сообщений для LLM с контекстом из RAG
     */
    fun buildMessages(
        query: String,
        ragResults: List<SearchResult>,
        extraContext: String? = null
    ): List<Message> {
        val toolInstructions = """
            Доступные MCP-инструменты (вызывай, если это помогает ответу):

            Git инструменты:
            - git_info: вернуть базовую информацию о git (ветка, последний коммит, статус).
            - git_uncommitted: вернуть незакоммиченные/неотслеживаемые файлы.

            CRM инструменты:
            - crm_list_users: получить список всех пользователей.
            - crm_get_user: получить информацию о пользователе (требует email или ID).
            - crm_get_user_tickets: получить тикеты пользователя (требует userId).
            - crm_get_ticket: получить информацию о тикете (требует ticketId).
            - crm_get_user_subscriptions: получить подписки пользователя (требует userId).

            Как вызвать инструмент:
            - Без аргументов: {"tool":"git_info"}
            - С аргументами: {"tool":"crm_get_user", "args":"ivan@example.com"}

            Ответь единственным JSON без лишнего текста. После этого ты получишь результат и должен выдать финальный ответ.
        """.trimIndent()

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
        } + (if (!extraContext.isNullOrBlank()) "\n\nДополнительный контекст (MCP):\n$extraContext" else "")

        return listOf(
            Message(
                role = "system",
                content = """
                Ты - ассистент для разработчика. Отвечай на вопросы по проекту на основе предоставленного контекста.

                Контекст из проекта:
                $context

                $toolInstructions

                Отвечай четко, по существу. Если контекст не содержит информации для ответа, так и скажи. Если инструмент не нужен, отвечай сразу.
                """.trimIndent()
            ),
            Message(
                role = "user",
                content = query
            )
        )
    }
}
